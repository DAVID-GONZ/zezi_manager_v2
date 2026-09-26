"""
src/domain/models/observabilidad.py
=====================================
DTOs de observabilidad de plataforma (obs_13).

Cuatro DTOs de solo lectura:
  SaludDTO       — estado de salud del sistema (integridad, versión, uptime, BD, backup).
  EntradaLogDTO  — una entrada del log de seguridad estructurado.
  AlertaIPDTO    — alerta de IP activa con conteo y tiempo restante.
  PuntoUsoDTO    — punto de la serie diaria de uso (logins + denegados por día).

Regla de capas: solo stdlib + pydantic.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.models.base import DTODominio


class SaludDTO(DTODominio):
    """
    Estado de salud del sistema.

    R2: veredicto de integridad, versión, uptime, tamaño de base y último backup.
    R3: ultimo_backup es None cuando no existe registro de backup.
    """

    integra: bool
    """True si verify_db_integrity() pasó."""

    version: str
    """Versión de la aplicación (settings.APP_VERSION)."""

    uptime_segundos: float
    """Segundos transcurridos desde el arranque del proceso (monotonic)."""

    tamanio_db_bytes: int
    """Tamaño del archivo de base de datos en bytes."""

    ultimo_backup: Optional[datetime] = None
    """Fecha/hora del último backup conocido. None → sin backup registrado (R3)."""


class EntradaLogDTO(DTODominio):
    """
    Una entrada del log de seguridad estructurado (R8).

    Solo incluye campos de la whitelist _CAMPOS_PERMITIDOS del security_logger.
    Los campos ausentes en la línea original quedan como None.
    """

    timestamp: Optional[str] = None
    usuario: Optional[str] = None
    ip: Optional[str] = None
    rol: Optional[str] = None
    institucion_id: Optional[int] = None
    tipo_evento: Optional[str] = None
    motivo: Optional[str] = None
    recurso: Optional[str] = None
    objetivo: Optional[str] = None


class AlertaIPDTO(DTODominio):
    """
    Alerta de IP activa (R9, R10).

    Una IP con fallos dentro de la ventana vigente.
    """

    ip: str
    """IP normalizada (stripped)."""

    fallos: int
    """Número de fallos registrados en la ventana."""

    segundos_restantes: float
    """Segundos que quedan en la ventana. > 0 garantizado (solo se incluyen activas)."""


class PuntoUsoDTO(DTODominio):
    """
    Un punto de la serie diaria de uso (R12).

    Un punto por día de la ventana, incluidos los días sin actividad (ceros).
    """

    fecha: str
    """Fecha ISO-8601 (YYYY-MM-DD)."""

    logins: int = 0
    """Número de LOGIN_EXITOSO en ese día."""

    denegados: int = 0
    """Número de ACCESO_DENEGADO en ese día."""


__all__ = [
    "AlertaIPDTO",
    "EntradaLogDTO",
    "PuntoUsoDTO",
    "SaludDTO",
]
