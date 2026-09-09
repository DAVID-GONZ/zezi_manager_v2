"""
contexto_actor.py — Identidad del actor que ejecuta la operación.
==================================================================

Mecanismo neutral (sin dependencias de interfaz/infra) que expone el
`usuario_id` del actor real de la sesión actual, espejando el patrón de
`contexto_tenant.py`. Sirve de choke point para que los helpers de
auditoría resuelvan quién realizó cada cambio, sin que los servicios
tengan que recibir el ID por parámetro.

Diseño (obs_01_huella_actor):
  - El estado vive en un `contextvars.ContextVar[int | None]` privado,
    default `None`. Cada página y cada handler de NiceGUI corren en su
    propia task y releen el contexto al inicio.
  - El choke point de activación es `SessionContext.desde_storage()`
    (capa de interfaz), que llama `activar_actor(actor_id)` con la
    REGLA DE IMPERSONACIÓN:
        actor_id = admin_real_id  si impersonando=True
        actor_id = usuario_id     en otro caso
    Así la huella pertenece al admin real, no al suplantado.
  - `None` => el actor es desconocido (arranque sin sesión / seed / tests
    que no precisan auditoría).
  - `usar_actor(id)` es un context manager para seed/scripts/tests.

Regla de capas: este módulo NO importa interfaz ni infraestructura.
"""

from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Iterator

# Estado privado. Default None → actor desconocido.
_actor_actual: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "zeci_actor_actual", default=None
)


def activar_actor(usuario_id: int | None) -> None:
    """Fija el actor activo del contexto actual (None = desconocido)."""
    _actor_actual.set(usuario_id)


def actor_actual() -> int | None:
    """
    Retorna el usuario_id del actor activo del contexto actual.

    `None` significa que no hay sesión activa (arranque sin sesión,
    seed, o tests que no necesitan auditoría).
    """
    return _actor_actual.get()


def limpiar_actor() -> None:
    """Restablece el actor a None (desconocido)."""
    _actor_actual.set(None)


@contextlib.contextmanager
def usar_actor(usuario_id: int | None) -> Iterator[None]:
    """
    Context manager que fija el actor activo y lo restaura al salir.

    Pensado para seed/scripts/tests que no tienen sesión de interfaz:

        with usar_actor(42):
            servicio.hacer_algo()   # auditado como actor #42
        # fuera del bloque, el actor vuelve a su valor anterior
    """
    token = _actor_actual.set(usuario_id)
    try:
        yield
    finally:
        _actor_actual.reset(token)


__all__ = [
    "activar_actor",
    "actor_actual",
    "limpiar_actor",
    "usar_actor",
]
