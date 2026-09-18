"""
security_logger.py — Implementación del puerto ISecurityLogger (obs_03).
=========================================================================

Logger estructurado en JSON rotado para eventos de seguridad.

Diseño de seguridad (R2/R7):
  - _CAMPOS_PERMITIDOS es la única fuente de verdad de qué campos pueden
    aparecer en el JSON serializado.
  - _JsonSecurityFormatter itera solo sobre esa whitelist; cualquier
    atributo del LogRecord fuera de ella se descarta silenciosamente.
  - Los métodos de SecurityLogger NO aceptan **kwargs libres.

Configuración:
  - settings.SECURITY_LOG_FILE:      Path al archivo rotado (None → NullHandler).
  - settings.SECURITY_LOG_MAX_BYTES: Tamaño máximo por archivo (default 10 MB).
  - settings.SECURITY_LOG_BACKUP_COUNT: Número de archivos de respaldo (default 30).

El logger `zeci.security` NO propaga al root logger (evita duplicados en consola).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from config import settings
from src.domain.ports.security_logger import ISecurityLogger

# ---------------------------------------------------------------------------
# Whitelist de campos permitidos en el JSON de seguridad (R7)
# ---------------------------------------------------------------------------
_CAMPOS_PERMITIDOS: frozenset[str] = frozenset({
    "usuario",
    "ip",
    "timestamp",
    "rol",
    "institucion_id",
    "tipo_evento",
    "motivo",
    "recurso",
})


# ---------------------------------------------------------------------------
# Formatter JSON con whitelist
# ---------------------------------------------------------------------------

class _JsonSecurityFormatter(logging.Formatter):
    """
    Serializa un LogRecord como JSON incluyendo solo los campos de
    _CAMPOS_PERMITIDOS.

    `timestamp` se calcula desde `record.created` (epoch float → ISO-8601 UTC).
    El resto de campos se leen como atributos del record (los `extra` dict
    se convierten en atributos del record al pasar por logging.Logger.info/etc.).
    Cualquier campo no listado —incluyendo passwords, tokens o datos personales—
    se descarta sin error.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        doc: dict = {"timestamp": ts}

        for campo in _CAMPOS_PERMITIDOS:
            if campo == "timestamp":
                continue
            val = getattr(record, campo, None)
            if val is not None:
                doc[campo] = val

        return json.dumps(doc, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Construcción del handler al importar el módulo (una sola vez)
# ---------------------------------------------------------------------------

def _construir_handler() -> logging.Handler:
    """Construye el handler de archivo rotado o NullHandler según config."""
    if settings.SECURITY_LOG_FILE is not None:
        settings.SECURITY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            settings.SECURITY_LOG_FILE,
            maxBytes=settings.SECURITY_LOG_MAX_BYTES,
            backupCount=settings.SECURITY_LOG_BACKUP_COUNT,
            encoding="utf-8",
            delay=True,
        )
    else:
        handler = logging.NullHandler()

    handler.setFormatter(_JsonSecurityFormatter())
    return handler


_logger = logging.getLogger("zeci.security")
# Nivel explícito: sin esto, getEffectiveLevel() caminaría hasta el root
# (WARNING por defecto) filtrando los INFO del logger. El logger gestiona
# su propio destino (RotatingFile/Null); no necesita la jerarquía de root.
_logger.setLevel(logging.DEBUG)
# Añadir handler solo si no se ha añadido previamente (guard para re-imports en tests)
if not _logger.handlers:
    _logger.addHandler(_construir_handler())
_logger.propagate = False


# ---------------------------------------------------------------------------
# Implementación del puerto
# ---------------------------------------------------------------------------

class SecurityLogger(ISecurityLogger):
    """
    Implementación concreta de ISecurityLogger sobre el logger `zeci.security`.

    Emite registros JSON serializados mediante _JsonSecurityFormatter.
    Solo los campos en _CAMPOS_PERMITIDOS aparecen en cada registro.
    """

    def login_exitoso(
        self,
        usuario: str,
        ip: str,
        rol: str,
        institucion_id: int,
    ) -> None:
        """Registra un login exitoso (INFO)."""
        _logger.info(
            "login_exitoso",
            extra={
                "usuario": usuario,
                "ip": ip,
                "rol": rol,
                "institucion_id": institucion_id,
                "tipo_evento": "LOGIN_EXITOSO",
            },
        )

    def login_fallido(self, usuario: str, ip: str, motivo: str) -> None:
        """Registra un login fallido (WARNING)."""
        _logger.warning(
            "login_fallido",
            extra={
                "usuario": usuario,
                "ip": ip,
                "motivo": motivo,
                "tipo_evento": "LOGIN_FALLIDO",
            },
        )

    def logout(self, usuario: str, ip: str) -> None:
        """Registra un logout (INFO)."""
        _logger.info(
            "logout",
            extra={
                "usuario": usuario,
                "ip": ip,
                "tipo_evento": "LOGOUT",
            },
        )

    def acceso_denegado(self, usuario: str, ip: str, recurso: str) -> None:
        """Registra un acceso denegado (WARNING)."""
        _logger.warning(
            "acceso_denegado",
            extra={
                "usuario": usuario,
                "ip": ip,
                "recurso": recurso,
                "tipo_evento": "ACCESO_DENEGADO",
            },
        )

    def ver_como(self, admin: str, objetivo: str, accion: str) -> None:
        """Registra inicio/fin de impersonación (INFO)."""
        _logger.info(
            "ver_como",
            extra={
                "usuario": admin,
                "tipo_evento": accion,
            },
        )

    def gestion_usuario(self, actor: str, objetivo: str, operacion: str) -> None:
        """Registra una operación de gestión de usuario (INFO)."""
        _logger.info(
            "gestion_usuario",
            extra={
                "usuario": actor,
                "tipo_evento": operacion,
            },
        )


__all__ = [
    "SecurityLogger",
    "_JsonSecurityFormatter",
    "_CAMPOS_PERMITIDOS",
]
