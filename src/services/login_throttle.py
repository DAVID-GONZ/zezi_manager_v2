"""
login_throttle.py — Throttle/lockout de login en memoria (A1).
==============================================================

Mecanismo neutral (sin dependencias de interfaz ni de infraestructura) que
frena la fuerza bruta / credential stuffing sobre el login: tras
``MAX_INTENTOS`` fallos consecutivos por username, la cuenta queda bloqueada
``BLOQUEO_SEGUNDOS`` segundos. bcrypt (rounds=12) solo encarece cada intento;
este módulo lo *frena*.

Diseño (decisión de David):
  - Estado privado en un ``dict`` de PROCESO (no ContextVar): el bloqueo debe
    ser visible a todas las peticiones, no por task. Apropiado para el
    despliegue mono-proceso de NiceGUI.
  - La clave es el username NORMALIZADO (minúsculas, sin espacios al borde),
    espejo de la normalización del modelo ``Usuario``: así "Admin" y "admin"
    comparten contador y no se puede evadir el bloqueo cambiando el casing.
  - Los fallos se AUDITAN en la capa de interfaz (login.py) con el evento ya
    existente ``TipoEventoSesion.LOGIN_FALLIDO``; este módulo NO audita.

Regla de capas: este módulo NO importa interfaz ni infraestructura
(espejo de ``src/services/solo_lectura.py``). Solo stdlib.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

# Política de throttle. Tras MAX_INTENTOS fallos consecutivos → bloqueo.
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 300  # 5 minutos


@dataclass
class _Estado:
    """Contador de fallos y momento de bloqueo de un username."""
    fallos: int = 0
    bloqueado_hasta: float = field(default=0.0)  # epoch segundos; 0 = sin bloqueo


# Estado privado de PROCESO. username_normalizado → _Estado.
_estados: dict[str, _Estado] = {}


def _normalizar(usuario: str) -> str:
    """Normaliza el username igual que el modelo de dominio (minúsculas)."""
    return (usuario or "").strip().lower()


def registrar_fallo(usuario: str) -> None:
    """
    Registra un intento fallido para ``usuario``.

    Al alcanzar ``MAX_INTENTOS`` fallos consecutivos arranca una ventana de
    bloqueo de ``BLOQUEO_SEGUNDOS``. Un username vacío se ignora (no hay sujeto
    real al que contar).
    """
    clave = _normalizar(usuario)
    if not clave:
        return
    estado = _estados.setdefault(clave, _Estado())
    estado.fallos += 1
    if estado.fallos >= MAX_INTENTOS:
        estado.bloqueado_hasta = time.monotonic() + BLOQUEO_SEGUNDOS


def registrar_exito(usuario: str) -> None:
    """Limpia el contador de fallos y cualquier bloqueo de ``usuario``."""
    clave = _normalizar(usuario)
    if not clave:
        return
    _estados.pop(clave, None)


def estado_bloqueo(usuario: str) -> tuple[bool, int]:
    """
    Estado de bloqueo de ``usuario``.

    Returns:
        ``(bloqueado, segundos_restantes)``. ``segundos_restantes`` es 0 cuando
        no está bloqueado. Cuando la ventana de bloqueo expira, el contador se
        reinicia (el usuario vuelve a tener intentos limpios).
    """
    clave = _normalizar(usuario)
    estado = _estados.get(clave)
    if estado is None or estado.bloqueado_hasta <= 0.0:
        return (False, 0)
    restante = estado.bloqueado_hasta - time.monotonic()
    if restante <= 0.0:
        # La ventana expiró: limpiar para empezar de cero.
        _estados.pop(clave, None)
        return (False, 0)
    return (True, int(restante) + 1)


def reset_throttle() -> None:
    """Vacía todo el estado de throttle (uso exclusivo de tests)."""
    _estados.clear()


__all__ = [
    "MAX_INTENTOS",
    "BLOQUEO_SEGUNDOS",
    "registrar_fallo",
    "registrar_exito",
    "estado_bloqueo",
    "reset_throttle",
]
