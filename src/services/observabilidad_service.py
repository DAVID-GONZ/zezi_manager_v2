"""
src/services/observabilidad_service.py
=========================================
Servicio de observabilidad de plataforma (obs_13).

Compone el estado operativo del sistema: salud, log de seguridad, alertas de IP
y KPIs de uso diario. Solo lectura: no muta nada.

Regla de capas:
  - Importa de src/domain/ (modelos, puertos, políticas).
  - NO abre archivos directamente: delega en ILogReader.
  - NO cuenta en Python: usa resumen SQL vía IAuditoriaRepository.
  - NO importa nicegui, sqlite3, pandas.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.domain.models.observabilidad import (
    AlertaIPDTO,
    EntradaLogDTO,
    PuntoUsoDTO,
    SaludDTO,
)
from src.domain.policies.alerta_ip import alertas_activas
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.ports.log_reader import ILogReader
from src.infrastructure.db.connection import verify_db_integrity

if TYPE_CHECKING:
    pass


class ObservabilidadService:
    """
    Compone el estado operativo del sistema. Solo lectura.

    Depende de:
      - IAuditoriaRepository — para uso_diario (GROUP BY SQL).
      - ILogReader — para leer el log de seguridad.
      - Importa verify_db_integrity lazy para salud (no en constructor).
    """

    def __init__(
        self,
        auditoria_repo: IAuditoriaRepository,
        log_reader: ILogReader,
    ) -> None:
        self._auditoria_repo = auditoria_repo
        self._log_reader = log_reader

    # ── API pública ────────────────────────────────────────────────────────────

    def salud(self) -> SaludDTO:
        """
        Veredicto de integridad, versión, uptime, tamaño de base y último backup.

        Reutiliza verify_db_integrity() — el mismo criterio que /health, no uno
        paralelo (R2). Devuelve ultimo_backup=None si no hay backup conocido (R3).
        """
        from config import settings

        # Integridad — reutiliza el mismo criterio que /health (no duplicar)
        try:
            integra = verify_db_integrity()
        except Exception:
            integra = False

        # Uptime: tiempo transcurrido desde el arranque del proceso
        try:
            import main as _main
            uptime = time.monotonic() - _main.INICIADO_EN
        except Exception:
            uptime = 0.0

        # Tamaño de la base de datos
        try:
            tamanio = settings.DATABASE_PATH.stat().st_size
        except Exception:
            tamanio = 0

        # Último backup — mientras no exista tooling, inspeccionamos el directorio
        ultimo_backup = self._ultimo_backup()

        return SaludDTO(
            integra=integra,
            version=settings.APP_VERSION,
            uptime_segundos=uptime,
            tamanio_db_bytes=tamanio,
            ultimo_backup=ultimo_backup,
        )

    def eventos_seguridad(
        self,
        n: int = 200,
        *,
        nivel: str | None = None,
        tipo_evento: str | None = None,
    ) -> list[EntradaLogDTO]:
        """
        Últimas ``n`` entradas del log de seguridad.

        El log se lee a través de ILogReader (R5). Los campos se filtran
        contra _CAMPOS_PERMITIDOS (R8). Un archivo ausente devuelve [] (R7).
        """
        entradas_crudas = self._log_reader.leer_ultimos(
            n,
            nivel=nivel,
            tipo_evento=tipo_evento,
        )
        resultado: list[EntradaLogDTO] = []
        for raw in entradas_crudas:
            try:
                resultado.append(EntradaLogDTO(**{
                    k: v for k, v in raw.items()
                    if k in EntradaLogDTO.model_fields
                }))
            except Exception:
                continue  # línea ilegible → descartar
        return resultado

    def log_disponible(self) -> bool:
        """True si el archivo de log existe y es legible (R7)."""
        return self._log_reader.disponible()

    def alertas_ip(self) -> list[AlertaIPDTO]:
        """
        IPs con fallos dentro de la ventana vigente (R9).

        Delegado a alertas_activas() de la política de dominio — que NO muta
        el estado (R9).
        """
        vivas = alertas_activas()
        return [
            AlertaIPDTO(ip=ip, fallos=fallos, segundos_restantes=restante)
            for ip, fallos, restante in vivas
        ]

    def uso_diario(self, dias: int = 14) -> list[PuntoUsoDTO]:
        """
        Serie diaria de uso en la ventana de ``dias`` días (R12).

        GROUP BY date(fecha_hora) en SQL — sin conteo en Python.
        Los días sin actividad se incluyen con ceros (T9).
        """
        filas = self._auditoria_repo.uso_diario(dias=dias)
        return [
            PuntoUsoDTO(
                fecha=r.get("fecha", ""),
                logins=int(r.get("logins", 0)),
                denegados=int(r.get("denegados", 0)),
            )
            for r in filas
        ]

    # ── Helpers internos ────────────────────────────────────────────────────────

    @staticmethod
    def _ultimo_backup():
        """
        Inspecciona el directorio de archivos de auditoría para encontrar
        el backup más reciente.

        Mientras no exista tooling de backup, devuelve None (R3).
        None es la respuesta correcta: mentir con un cero sería peor.
        """
        try:
            from pathlib import Path
            from config import settings
            from datetime import datetime

            archivo_dir_str = settings.AUDITORIA_ARCHIVO_DIR
            archivo_dir = Path(archivo_dir_str)
            if not archivo_dir.is_absolute():
                from config import settings as _s
                archivo_dir = Path(__file__).parent.parent / archivo_dir_str

            if not archivo_dir.exists():
                return None

            archivos = sorted(
                archivo_dir.glob("*.jsonl"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if not archivos:
                return None

            mtime = archivos[0].stat().st_mtime
            return datetime.fromtimestamp(mtime)
        except Exception:
            return None


__all__ = ["ObservabilidadService"]
