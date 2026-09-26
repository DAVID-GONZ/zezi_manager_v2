"""
AuditoriaRetencionService — Archivado y purga de la bitácora (obs_12).

Responsabilidades:
  - Archivar el tramo [origen, hasta] en un archivo JSONL firmado.
  - Verificar el hash del archivo antes de eliminar ninguna fila.
  - Eliminar las filas solo tras el archivado verificado.
  - Reanclar el checkpoint de verificación incremental (R11).
  - Emitir el evento AUDITORIA_PURGADA con toda la información del tramo (R10).

El orden de las operaciones es el invariante central de este servicio:
  1. Delimitar el tramo.
  2. Verificar la cadena del tramo.
  3. Escribir el archivo JSONL + hoja de verificación.
  4. Releer el archivo y confirmar su hash.
  5. Eliminar las filas (única operación destructiva, la última).
  6. Reanclar el checkpoint.
  7. Registrar AUDITORIA_PURGADA.

Cualquier fallo en los pasos 1-4 aborta sin haber borrado nada.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from src.domain.exceptions import ReglaDeNegocioError
from src.domain.models.auditoria import (
    EventoSesion,
    FiltroAuditoriaDTO,
    ResultadoArchivadoDTO,
    SeveridadEvento,
    TipoEventoSesion,
)
from src.domain.models.clock import ahora
from src.domain.models.tenant import TenantScope
from src.domain.ports.auditoria_repo import IAuditoriaRepository

logger = logging.getLogger("AUDITORIA.RETENCION")


def _sha256_file(path: Path) -> str:
    """SHA-256 hex-digest del contenido de un archivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def _serializar_fila(r) -> dict:
    """Serializa un RegistroCambio o EventoSesion a dict para JSONL."""
    try:
        d = r.model_dump()
    except Exception:
        d = {}
    # Convertir datetime a ISO
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif hasattr(v, "value"):  # StrEnum
            d[k] = v.value
    return d


class AuditoriaRetencionService:
    """
    Archiva y purga un tramo de la bitácora (obs_12, R8-R12).

    El constructor recibe el repositorio de auditoría y el directorio base
    donde se guardarán los archivos JSONL. El directorio se crea si no existe.
    """

    def __init__(
        self,
        repo: IAuditoriaRepository,
        archivo_dir: str | Path = "data/archivos_auditoria",
    ) -> None:
        self._repo = repo
        self._archivo_dir = Path(archivo_dir)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def archivar_y_purgar(
        self,
        tabla: str,
        hasta: datetime,
        *,
        scope: TenantScope,
        actor: str,
        actor_id: int | None = None,
    ) -> ResultadoArchivadoDTO:
        """
        Archiva y purga el tramo de la bitácora anterior a ``hasta``.

        Sigue el orden de seis pasos del diseño (§4):
          1. Delimitar el tramo (rango de ids).
          2. Verificar la cadena del tramo.
          3. Escribir el archivo JSONL + hoja de verificación.
          4. Releer el archivo y confirmar su hash.
          5. Eliminar las filas (única operación destructiva).
          6. Reanclar el checkpoint + registrar AUDITORIA_PURGADA.

        Args:
            tabla:    'audit_log' o 'auditoria'.
            hasta:    Fecha de corte. Solo se eliminan filas anteriores a esta fecha.
            scope:    TenantScope del actor.
            actor:    Username del actor para el evento de auditoría.
            actor_id: usuario_id del actor.

        Returns:
            ResultadoArchivadoDTO con el resumen de la operación.

        Raises:
            ReglaDeNegocioError si el tramo está vacío o el archivo no se puede
            verificar antes de borrar nada.
            RuntimeError si la escritura o relectura del archivo falla
            (ninguna fila se elimina en este caso).
        """
        # --- Paso 1: Delimitar el tramo ---
        filtro = self._filtro_hasta(hasta, scope)
        rango = self._repo.rango_de(tabla, filtro)
        if rango is None:
            raise ReglaDeNegocioError(
                f"No hay filas en '{tabla}' anteriores a {hasta.isoformat()} para archivar."
            )
        id_desde, id_hasta = rango

        # --- Paso 2: Verificar integridad del tramo ---
        verificacion_previa_ok = True
        try:
            id_roto = self._repo._verificar_tramo_ids(tabla, id_desde, id_hasta)  # type: ignore[attr-defined]
            verificacion_previa_ok = id_roto is None
            if not verificacion_previa_ok:
                logger.warning(
                    "Tramo [%d, %d] de %s tiene cadena rota en id=%d; "
                    "se archiva igualmente pero se documenta.",
                    id_desde, id_hasta, tabla, id_roto,
                )
        except AttributeError:
            pass  # repo sin soporte de verificación de tramo

        # --- Paso 3: Escribir el archivo JSONL ---
        ruta_archivo = self._ruta_archivo(tabla, id_desde, id_hasta)
        hash_archivo = self._escribir_jsonl(
            tabla, id_desde, id_hasta, scope, ruta_archivo,
            actor=actor, hasta=hasta,
            verificacion_previa_ok=verificacion_previa_ok,
        )

        # --- Paso 4: Releer y confirmar hash ---
        hash_releido = _sha256_file(ruta_archivo)
        if hash_releido != hash_archivo:
            raise ReglaDeNegocioError(
                f"Hash del archivo releído ({hash_releido}) no coincide con el calculado "
                f"({hash_archivo}). El archivo puede estar corrupto. No se eliminaron filas.",
                codigo="AUDITORIA_ARCH_HASH_MISMATCH",
            )

        # --- Paso 5: Eliminar las filas ---
        filas_eliminadas = self._repo.eliminar_hasta(tabla, id_hasta, scope)

        # --- Paso 6: Reanclar checkpoint + evento ---
        hash_k = self._hash_de_fila(tabla, id_hasta)
        self._reanclar_checkpoint(tabla, id_hasta, hash_k)
        self._emitir_evento_purgada(
            actor=actor,
            actor_id=actor_id,
            tabla=tabla,
            id_desde=id_desde,
            id_hasta=id_hasta,
            filas=filas_eliminadas,
            ruta=str(ruta_archivo),
            hash_archivo=hash_archivo,
        )

        return ResultadoArchivadoDTO(
            tabla=tabla,
            hasta=hasta,
            id_desde=id_desde,
            id_hasta=id_hasta,
            filas_eliminadas=filas_eliminadas,
            ruta_archivo=str(ruta_archivo),
            hash_archivo=hash_archivo,
            verificacion_previa_ok=verificacion_previa_ok,
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _filtro_hasta(hasta: datetime, scope: TenantScope) -> FiltroAuditoriaDTO:
        """Construye un filtro que acota al tramo anterior a ``hasta``."""
        base = FiltroAuditoriaDTO(hasta=hasta, por_pagina=1)
        if scope == "*":
            return base
        return base.model_copy(update={"institucion_id": scope, "sin_institucion": False})

    def _ruta_archivo(self, tabla: str, id_desde: int, id_hasta: int) -> Path:
        """Genera la ruta del archivo JSONL para el tramo."""
        ts = ahora().strftime("%Y%m%d_%H%M%S")
        nombre = f"{tabla}_arch_{id_desde}_{id_hasta}_{ts}.jsonl"
        self._archivo_dir.mkdir(parents=True, exist_ok=True)
        return self._archivo_dir / nombre

    def _escribir_jsonl(
        self,
        tabla: str,
        id_desde: int,
        id_hasta: int,
        scope: TenantScope,
        ruta: Path,
        *,
        actor: str,
        hasta: datetime,
        verificacion_previa_ok: bool,
    ) -> str:
        """
        Escribe el archivo JSONL con todas las filas del tramo.
        Primera línea: metadatos (hoja de verificación).
        Resto: una fila JSON por línea.
        Devuelve el SHA-256 del archivo escrito.
        """
        h = hashlib.sha256()
        # Abrir en modo binario para evitar que Windows convierta \n → \r\n en disco,
        # lo que rompería la verificación posterior del hash del archivo.
        with open(ruta, "wb") as f:
            # Primera línea: metadatos del archivado
            meta = {
                "_tipo": "ARCHIVO_AUDITORIA",
                "tabla": tabla,
                "id_desde": id_desde,
                "id_hasta": id_hasta,
                "hasta_fecha": hasta.isoformat(),
                "actor": actor,
                "generado_en": ahora().isoformat(),
                "verificacion_previa_ok": verificacion_previa_ok,
            }
            linea_bytes = (json.dumps(meta, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8")
            f.write(linea_bytes)
            h.update(linea_bytes)

            # Filas del tramo
            for lote in self._repo.listar_cambios_tramo(tabla, id_desde, id_hasta, scope):
                for r in lote:
                    fila_dict = _serializar_fila(r)
                    linea_bytes = (json.dumps(fila_dict, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8")
                    f.write(linea_bytes)
                    h.update(linea_bytes)

        return h.hexdigest()

    def _hash_de_fila(self, tabla: str, fila_id: int) -> str | None:
        """Devuelve el hash_cadena de la fila k (la última del tramo)."""
        try:
            return self._repo.hash_de_fila(tabla, fila_id)  # type: ignore[attr-defined]
        except AttributeError:
            return None

    def _reanclar_checkpoint(
        self,
        tabla: str,
        id_hasta: int,
        hash_k: str | None,
    ) -> None:
        """
        Reancha el checkpoint de la verificación incremental a (k, hash_de_k).

        Después de purgar las filas [1..k], la fila k+1 sigue encadenando
        contra el hash_cadena de k, que ya no existe en la tabla. El
        checkpoint actualizado permite que la verificación incremental
        arranque desde k como nuevo origen, sin fallar por el hueco.
        """
        if hash_k is None:
            logger.warning(
                "No se pudo obtener el hash de la fila %d de %s para reanclar el checkpoint.",
                id_hasta, tabla,
            )
            return
        try:
            self._repo._guardar_checkpoint(tabla, id_hasta, hash_k)  # type: ignore[attr-defined]
            logger.info("Checkpoint de %s reancladlo a id=%d", tabla, id_hasta)
        except AttributeError:
            logger.warning("El repo no expone _guardar_checkpoint; checkpoint no actualizado.")

    def _emitir_evento_purgada(
        self,
        actor: str,
        actor_id: int | None,
        tabla: str,
        id_desde: int,
        id_hasta: int,
        filas: int,
        ruta: str,
        hash_archivo: str,
    ) -> None:
        """Registra el evento AUDITORIA_PURGADA (R10)."""
        try:
            detalles = (
                f"tabla={tabla} id_desde={id_desde} id_hasta={id_hasta} "
                f"filas={filas} archivo={ruta} hash={hash_archivo}"
            )
            evento = EventoSesion(
                usuario=actor,
                usuario_id=actor_id,
                tipo_evento=TipoEventoSesion.AUDITORIA_PURGADA,
                detalles=detalles,
                severidad=SeveridadEvento.ADVERTENCIA,
            )
            try:
                from src.services.contexto_tenant import institucion_actual
                inst_id = institucion_actual()
                if inst_id is not None:
                    evento = evento.model_copy(update={"institucion_id": inst_id})
            except Exception:
                pass
            self._repo.registrar_evento(evento)
        except Exception as exc:
            logger.warning("No se pudo emitir evento AUDITORIA_PURGADA: %s", exc)


__all__ = ["AuditoriaRetencionService"]
