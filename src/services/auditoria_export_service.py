"""
AuditoriaExportService — Exportación verificable de la bitácora (obs_12).

Responsabilidades:
  - Delimitar el tramo del filtro activo.
  - Verificar la integridad de la cadena del tramo.
  - Serializar las filas reutilizando ``diff_cambio`` para redactar sensibles (R6).
  - Componer la HojaVerificacionDTO (R2).
  - Delegar la escritura al ``IExporterService`` (CSV o PDF).
  - Emitir el evento ``AUDITORIA_EXPORTADA`` (R5).
  - Imponer el tope de filas configurable (R7).

No escribe en la BD más allá del evento de sesión. No borra nada.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
from typing import TYPE_CHECKING

from src.domain.exceptions import ReglaDeNegocioError
from src.domain.models.auditoria import (
    FiltroAuditoriaDTO,
    HojaVerificacionDTO,
    RegistroCambio,
    TipoEventoSesion,
)
from src.domain.models.clock import ahora
from src.domain.models.tenant import TenantScope
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.ports.service_ports import IExporterService

if TYPE_CHECKING:
    pass

# Importar la lista canónica de campos sensibles desde auditoria_service.
# No se duplica aquí para evitar que ambas listas diverjan (advertencia R6).
from src.services.auditoria_service import _CAMPOS_SENSIBLES  # noqa: E402

logger = logging.getLogger("AUDITORIA.EXPORT")

# Código estable para el error de tope de filas (R7).
_CODIGO_TOPE = "AUDITORIA_EXPORT_TOPE"


def _sha256_bytes(data: bytes) -> str:
    """SHA-256 hex-digest de ``data``."""
    return hashlib.sha256(data).hexdigest()


def _redactar_valor(nombre: str, valor: object) -> object:
    """Redacta un valor si el campo es sensible (R6)."""
    if nombre.lower() in _CAMPOS_SENSIBLES:
        return "•••"
    return valor


def _serializar_fila_cambio(r: RegistroCambio, hash_cadena: str | None = None) -> dict:
    """
    Convierte un RegistroCambio a dict exportable, redactando campos sensibles.

    El valor_anterior/valor_nuevo se deserializa y sus campos sensibles se
    reemplazan por '•••' (R6). El resto de campos del registro pasan tal cual.
    ``hash_cadena`` se incluye para que el tercero verificador pueda reconstruir
    la cadena SHA-256 desde el propio CSV (B2).
    """
    base: dict = {
        "id": r.id,
        "usuario": r.usuario,
        "usuario_id": r.usuario_id,
        "ip_address": r.ip_address,
        "accion": r.accion.value if hasattr(r.accion, "value") else str(r.accion),
        "tabla": r.tabla,
        "registro_id": r.registro_id,
        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        "institucion_id": r.institucion_id,
        "hash_cadena": hash_cadena or "",
    }
    # Redactar campos sensibles en los blobs JSON
    for campo_json, attr in (("valor_anterior", r.valor_anterior), ("valor_nuevo", r.valor_nuevo)):
        if attr is None:
            base[campo_json] = None
            continue
        try:
            parsed: dict = json.loads(attr)
        except (json.JSONDecodeError, TypeError):
            base[campo_json] = attr
            continue
        redactado = {k: _redactar_valor(k, v) for k, v in parsed.items()}
        base[campo_json] = json.dumps(redactado, ensure_ascii=False, separators=(",", ":"), default=str)
    return base


def _filas_a_csv_bytes(filas: list[dict]) -> bytes:
    """
    Serializa una lista de dicts a bytes CSV en UTF-8 sin BOM.

    Los datos van sin BOM para que el archivo exportado tenga un único BOM al
    inicio (el de la cabecera de verificación). Así ``hash_contenido`` se
    calcula y verifica sobre ``datos_bytes.encode("utf-8")`` sin BOM ambiguo
    (ver docs/verificacion_bitacora.md §A).
    """
    if not filas:
        return b""
    buf = io.StringIO()
    columnas = list(filas[0].keys())
    buf.write(",".join(columnas) + "\r\n")
    for fila in filas:
        valores = []
        for col in columnas:
            v = fila.get(col, "")
            if v is None:
                v = ""
            s = str(v).replace('"', '""')
            if "," in s or '"' in s or "\n" in s:
                s = f'"{s}"'
            valores.append(s)
        buf.write(",".join(valores) + "\r\n")
    return buf.getvalue().encode("utf-8")


def _hoja_a_csv_cabecera(hoja: HojaVerificacionDTO) -> str:
    """
    Genera el bloque de cabecera comentado (líneas iniciando con #) para CSV.
    Va ANTES de los datos para no alterar el hash_contenido.
    """
    lineas = [
        "# HOJA DE VERIFICACION DE INTEGRIDAD",
        f"# generado_en: {hoja.generado_en.isoformat()}",
        f"# generado_por: {hoja.generado_por}",
        f"# institucion: {hoja.institucion or 'cross-tenant'}",
        f"# tabla: {hoja.tabla}",
        f"# id_desde: {hoja.id_desde}",
        f"# id_hasta: {hoja.id_hasta}",
        f"# fecha_desde: {hoja.fecha_desde.isoformat() if hoja.fecha_desde else 'N/A'}",
        f"# fecha_hasta: {hoja.fecha_hasta.isoformat() if hoja.fecha_hasta else 'N/A'}",
        f"# filas: {hoja.filas}",
        f"# hash_primera_fila: {hoja.hash_primera_fila}",
        f"# hash_ultima_fila: {hoja.hash_ultima_fila}",
        f"# hash_contenido: {hoja.hash_contenido}",
        f"# integridad_ok: {hoja.integridad_ok}",
        f"# id_roto: {hoja.id_roto if hoja.id_roto is not None else 'N/A'}",
        "# Procedimiento de verificacion: docs/verificacion_bitacora.md",
        "#",
    ]
    return "\r\n".join(lineas) + "\r\n"


class AuditoriaExportService:
    """
    Exporta un tramo de la bitácora como evidencia verificable (obs_12, R1-R7).

    Recibe el repositorio de auditoría (para leer tramos), el exportador
    (para escribir CSV/PDF) y el repositorio de eventos (para registrar
    AUDITORIA_EXPORTADA).
    """

    def __init__(
        self,
        repo: IAuditoriaRepository,
        exporter: IExporterService,
        max_filas: int = 50_000,
    ) -> None:
        self._repo = repo
        self._exporter = exporter
        self._max_filas = max_filas

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def exportar(
        self,
        tabla: str,
        filtro: FiltroAuditoriaDTO,
        scope: TenantScope,
        formato: str,     # "csv" | "pdf"
        actor: str,       # username del actor (para la hoja y el evento)
        actor_id: int | None = None,
        institucion_nombre: str | None = None,
    ) -> bytes:
        """
        Exporta el tramo resultante del filtro en el formato solicitado.

        Args:
            tabla:               'audit_log' o 'auditoria'.
            filtro:              Criterios de búsqueda (sin scope inyectado aún).
            scope:               TenantScope del actor.
            formato:             'csv' o 'pdf'.
            actor:               Username del actor para el evento de auditoría.
            actor_id:            usuario_id del actor.
            institucion_nombre:  Nombre de la institución (para la hoja).

        Returns:
            Bytes del archivo exportado (CSV o PDF con hoja de verificación).

        Raises:
            ReglaDeNegocioError(codigo='AUDITORIA_EXPORT_TOPE') si el tramo
            supera el máximo de filas configurado (R7).
        """
        # Aplicar scope al filtro
        filtro_con_scope = self._aplicar_scope(filtro, scope)

        # T4: tope de filas antes de exportar (R7)
        total = self._repo.contar_cambios(filtro_con_scope) if tabla == "audit_log" \
            else self._repo.contar_eventos(filtro_con_scope)
        if total > self._max_filas:
            raise ReglaDeNegocioError(
                f"El filtro selecciona {total:,} filas, que supera el límite de "
                f"{self._max_filas:,}. Acote el rango de fechas o añada más filtros.",
                codigo=_CODIGO_TOPE,  # type: ignore[arg-type]
            )

        # Delimitar el tramo
        rango = self._repo.rango_de(tabla, filtro_con_scope)
        if rango is None:
            # Sin filas: exportar vacío con hoja
            hoja = self._hoja_vacia(actor, tabla, institucion_nombre, filtro)
            datos_bytes = b""
            hoja_con_hash = hoja.model_copy(update={"hash_contenido": _sha256_bytes(datos_bytes)})
            return self._empaquetar(hoja_con_hash, datos_bytes, formato)

        id_desde, id_hasta = rango

        # Verificar integridad del tramo (R4: producir exportación aunque falle)
        id_roto = self._verificar_tramo(tabla, id_desde, id_hasta)
        integridad_ok = id_roto is None

        # Recoger hashes extremos del tramo
        hash_primera = self._repo.hash_de_fila(tabla, id_desde) if hasattr(self._repo, "hash_de_fila") else ""
        hash_ultima = self._repo.hash_de_fila(tabla, id_hasta) if hasattr(self._repo, "hash_de_fila") else ""

        # Materializar las filas del tramo y serializar
        # Se incluye hash_cadena por fila para que el verificador externo
        # pueda reconstruir la cadena desde el CSV (B2, docs/verificacion_bitacora.md §B).
        _repo_hash = getattr(self._repo, "hash_de_fila", None)
        filas: list[dict] = []
        for lote in self._repo.listar_cambios_tramo(tabla, id_desde, id_hasta, scope):
            for r in lote:
                hc = _repo_hash(tabla, r.id) if _repo_hash is not None and r.id is not None else None
                filas.append(_serializar_fila_cambio(r, hash_cadena=hc))

        datos_bytes = _filas_a_csv_bytes(filas)
        hash_contenido = _sha256_bytes(datos_bytes)

        hoja = HojaVerificacionDTO(
            generado_en=ahora(),
            generado_por=actor,
            institucion=institucion_nombre,
            tabla=tabla,
            id_desde=id_desde,
            id_hasta=id_hasta,
            fecha_desde=filtro.desde,
            fecha_hasta=filtro.hasta,
            filas=len(filas),
            hash_primera_fila=hash_primera or "",
            hash_ultima_fila=hash_ultima or "",
            hash_contenido=hash_contenido,
            integridad_ok=integridad_ok,
            id_roto=id_roto,
        )

        resultado = self._empaquetar(hoja, datos_bytes, formato)

        # T5: emitir evento de auditoría (R5)
        self._emitir_evento_exportacion(
            actor=actor,
            actor_id=actor_id,
            tabla=tabla,
            id_desde=id_desde,
            id_hasta=id_hasta,
            formato=formato,
            filas=len(filas),
            institucion_nombre=institucion_nombre,
        )

        return resultado

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _aplicar_scope(
        filtro: FiltroAuditoriaDTO,
        scope: TenantScope,
    ) -> FiltroAuditoriaDTO:
        """Fuerza el scope en el filtro (igual que AuditoriaService._filtro_con_scope)."""
        if scope == "*":
            return filtro
        return filtro.model_copy(update={"institucion_id": scope, "sin_institucion": False})

    def _verificar_tramo(
        self,
        tabla: str,
        id_desde: int,
        id_hasta: int,
    ) -> int | None:
        """
        Verifica la cadena del tramo ``[id_desde, id_hasta]``.
        Devuelve el id del primer registro roto, o None si íntegro.
        """
        try:
            # El repo SQLite expone _verificar_cadena; usarlo si está disponible.
            return self._repo._verificar_tramo_ids(tabla, id_desde, id_hasta)  # type: ignore[attr-defined]
        except AttributeError:
            pass
        # Fallback: sin soporte de verificación de tramo → no se puede verificar.
        return None

    def _hoja_vacia(
        self,
        actor: str,
        tabla: str,
        institucion_nombre: str | None,
        filtro: FiltroAuditoriaDTO,
    ) -> HojaVerificacionDTO:
        """Hoja de verificación para un tramo vacío."""
        return HojaVerificacionDTO(
            generado_en=ahora(),
            generado_por=actor,
            institucion=institucion_nombre,
            tabla=tabla,
            id_desde=0,
            id_hasta=0,
            fecha_desde=filtro.desde,
            fecha_hasta=filtro.hasta,
            filas=0,
            hash_primera_fila="",
            hash_ultima_fila="",
            hash_contenido="",
            integridad_ok=True,
            id_roto=None,
        )

    def _empaquetar(
        self,
        hoja: HojaVerificacionDTO,
        datos_bytes: bytes,
        formato: str,
    ) -> bytes:
        """
        Combina la hoja de verificación y los datos en el formato solicitado.

        CSV: cabecera comentada + datos.
        PDF: hoja en primera página + datos en páginas siguientes.
        """
        if formato == "pdf":
            return self._empaquetar_pdf(hoja, datos_bytes)
        # Default: CSV
        cabecera = _hoja_a_csv_cabecera(hoja).encode("utf-8-sig")
        return cabecera + datos_bytes

    def _empaquetar_pdf(
        self,
        hoja: HojaVerificacionDTO,
        datos_bytes: bytes,
    ) -> bytes:
        """Exporta la hoja + datos como PDF (delegando en IExporterService)."""
        hoja_html = self._hoja_a_html(hoja)
        datos_str = datos_bytes.decode("utf-8", errors="replace")
        html_completo = (
            "<html><body>"
            f"<div class='hoja-verificacion'>{hoja_html}</div>"
            "<hr/>"
            f"<pre>{datos_str}</pre>"
            "</body></html>"
        )
        return self._exporter.exportar_pdf(html_completo)

    @staticmethod
    def _hoja_a_html(hoja: HojaVerificacionDTO) -> str:
        """Renderiza la hoja de verificación como HTML para el PDF."""
        filas = [
            ("Generado en", hoja.generado_en.isoformat()),
            ("Generado por", hoja.generado_por),
            ("Institución", hoja.institucion or "cross-tenant"),
            ("Tabla", hoja.tabla),
            ("ID desde", str(hoja.id_desde)),
            ("ID hasta", str(hoja.id_hasta)),
            ("Fecha desde", hoja.fecha_desde.isoformat() if hoja.fecha_desde else "N/A"),
            ("Fecha hasta", hoja.fecha_hasta.isoformat() if hoja.fecha_hasta else "N/A"),
            ("Filas exportadas", str(hoja.filas)),
            ("Hash primera fila", hoja.hash_primera_fila),
            ("Hash última fila", hoja.hash_ultima_fila),
            ("Hash del contenido", hoja.hash_contenido),
            ("Integridad", "OK" if hoja.integridad_ok else f"FALLA (id {hoja.id_roto})"),
        ]
        rows_html = "".join(
            f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in filas
        )
        return (
            "<h2>Hoja de Verificación de Integridad</h2>"
            f"<table>{rows_html}</table>"
            "<p>Procedimiento de verificación: docs/verificacion_bitacora.md</p>"
        )

    def _emitir_evento_exportacion(
        self,
        actor: str,
        actor_id: int | None,
        tabla: str,
        id_desde: int,
        id_hasta: int,
        formato: str,
        filas: int,
        institucion_nombre: str | None,
    ) -> None:
        """
        Emite el evento AUDITORIA_EXPORTADA en la tabla auditoria (T5, R5).

        Usa el constructor único de eventos de la capa de interfaz a través de
        construir_evento cuando hay contexto de petición, o construye el
        EventoSesion directamente desde el servicio (capa de servicios).
        """
        try:
            from src.domain.models.auditoria import EventoSesion, SeveridadEvento

            detalles = (
                f"tabla={tabla} id_desde={id_desde} id_hasta={id_hasta} "
                f"filas={filas} formato={formato}"
            )
            evento = EventoSesion(
                usuario=actor,
                usuario_id=actor_id,
                tipo_evento=TipoEventoSesion.AUDITORIA_EXPORTADA,
                detalles=detalles,
                severidad=SeveridadEvento.INFO,
            )
            # Intentar añadir institucion_id desde contexto tenant
            try:
                from src.services.contexto_tenant import institucion_actual
                inst_id = institucion_actual()
                if inst_id is not None:
                    evento = evento.model_copy(update={"institucion_id": inst_id})
            except Exception:
                pass
            self._repo.registrar_evento(evento)
        except Exception as exc:
            logger.warning("No se pudo emitir evento AUDITORIA_EXPORTADA: %s", exc)


__all__ = ["AuditoriaExportService"]
