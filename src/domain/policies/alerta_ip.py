"""
alerta_ip.py — Política de alertas por IP (obs_03).
=====================================================

Detecta ráfagas de intentos de login fallido desde una misma IP en
una ventana de tiempo. Al superar el umbral emite una advertencia
al logger ``zeci.security`` para que el administrador pueda investigar.

Diseño (análogo a login_throttle.py):
  - Estado privado en un dict de PROCESO (no ContextVar): las alertas
    deben ser visibles a todas las peticiones del proceso.
  - La clave es la IP normalizada (strip).
  - No importa interfaz ni infraestructura. Solo stdlib.
  - No llama a ISecurityLogger (I/O circular): emite directamente a
    ``logging.getLogger("zeci.security")``, que es recogido por el
    handler configurado en infrastructure/logging/security_logger.py.

Regla de capas: solo stdlib.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Configuración de la política
# ---------------------------------------------------------------------------
MAX_FALLOS_IP: int = 5
VENTANA_SEGUNDOS: int = 300  # 5 minutos

_logger = logging.getLogger("zeci.security")


# ---------------------------------------------------------------------------
# Estado interno
# ---------------------------------------------------------------------------

@dataclass
class _EstadoIP:
    """Contador de fallos y timestamp del primer fallo en la ventana."""

    fallos: int = 0
    primer_fallo_en: float = field(default=0.0)  # epoch segundos; 0 = sin fallos


# Clave = IP normalizada → estado
_estados: dict[str, _EstadoIP] = {}


def _normalizar(ip: str) -> str:
    """Normaliza la IP (strip)."""
    return (ip or "").strip()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def registrar_fallo_ip(ip: str) -> None:
    """
    Registra un intento de login fallido desde ``ip``.

    Si la IP acumula ``MAX_FALLOS_IP`` fallos dentro de ``VENTANA_SEGUNDOS``
    segundos, emite una advertencia al logger ``zeci.security``.
    Una IP vacía se ignora.
    """
    clave = _normalizar(ip)
    if not clave:
        return

    ahora = time.monotonic()
    estado = _estados.setdefault(clave, _EstadoIP())

    # Si la ventana expiró, reiniciar
    if estado.primer_fallo_en > 0.0 and (ahora - estado.primer_fallo_en) > VENTANA_SEGUNDOS:
        estado.fallos = 0
        estado.primer_fallo_en = 0.0

    if estado.fallos == 0:
        estado.primer_fallo_en = ahora

    estado.fallos += 1

    if estado.fallos >= MAX_FALLOS_IP:
        _logger.warning(
            "ALERTA_IP: demasiados fallos desde %s",
            clave,
            extra={
                "tipo_evento": "ALERTA_IP",
                "ip": clave,
            },
        )


def reset_ip(ip: str) -> None:
    """Limpia el estado de alertas para una IP específica (util en tests)."""
    clave = _normalizar(ip)
    _estados.pop(clave, None)


def reset_all() -> None:
    """Vacía todo el estado de alertas (uso exclusivo de tests)."""
    _estados.clear()


__all__ = [
    "MAX_FALLOS_IP",
    "VENTANA_SEGUNDOS",
    "registrar_fallo_ip",
    "reset_ip",
    "reset_all",
]
