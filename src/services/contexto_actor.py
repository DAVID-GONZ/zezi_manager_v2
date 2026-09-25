"""
contexto_actor.py — Identidad del actor que ejecuta la operación.
==================================================================

Mecanismo neutral (sin dependencias de interfaz/infra) que expone el
`usuario_id`, `username` e `ip` del actor real de la sesión actual,
espejando el patrón de `contexto_tenant.py`. Sirve de choke point para
que los helpers de auditoría resuelvan quién realizó cada cambio, sin que
los servicios tengan que recibir estos datos por parámetro.

Diseño (obs_01_huella_actor / obs_06_identidad_y_ip):
  - El estado vive en un `contextvars.ContextVar[ActorContexto]` privado,
    default `ActorContexto()`. Cada página y cada handler de NiceGUI corren
    en su propia task y releen el contexto al inicio.
  - El choke point de activación es `SessionContext.desde_storage()`
    (capa de interfaz), que llama `activar_actor(actor_id, username, ip)`
    con la REGLA DE IMPERSONACIÓN:
        actor_id = admin_real_id  si impersonando=True
        actor_id = usuario_id     en otro caso
    Así la huella pertenece al admin real, no al suplantado.
  - `ActorContexto()` (campos None) => el actor es desconocido
    (arranque sin sesión / seed / tests que no precisan auditoría).
  - `usar_actor(id)` es un context manager para seed/scripts/tests.

Regla de capas: este módulo NO importa interfaz ni infraestructura.
"""

from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class ActorContexto:
    """Identidad completa del actor de la petición en curso."""

    usuario_id: int | None = None
    username: str | None = None
    ip: str | None = None


# Estado privado. Default ActorContexto() → actor desconocido.
_actor_actual: contextvars.ContextVar[ActorContexto] = contextvars.ContextVar(
    "zeci_actor_actual", default=ActorContexto()
)


def activar_actor(
    usuario_id: int | None,
    username: str | None = None,  # NUEVO — opcional: las llamadas de 1 arg siguen válidas
    ip: str | None = None,        # NUEVO
) -> None:
    """Fija el actor activo del contexto actual (None = desconocido)."""
    _actor_actual.set(ActorContexto(usuario_id, username, ip))


def actor_actual() -> int | None:
    """
    Retorna el usuario_id del actor activo del contexto actual.

    Firma conservada: compatible con los ~137 callers existentes.
    `None` significa que no hay sesión activa (arranque sin sesión,
    seed, o tests que no necesitan auditoría).
    """
    return _actor_actual.get().usuario_id


def actor_username() -> str | None:
    """Retorna el username del actor activo, o None si no está disponible."""
    return _actor_actual.get().username


def actor_ip() -> str | None:
    """Retorna la IP del actor activo, o None si no está disponible."""
    return _actor_actual.get().ip


def limpiar_actor() -> None:
    """Restablece el actor a desconocido (todos los campos None)."""
    _actor_actual.set(ActorContexto())


@contextlib.contextmanager
def usar_actor(
    usuario_id: int | None,
    username: str | None = None,
    ip: str | None = None,
) -> Iterator[None]:
    """
    Context manager que fija el actor activo y lo restaura al salir.

    Pensado para seed/scripts/tests que no tienen sesión de interfaz:

        with usar_actor(42, "jperez", "127.0.0.1"):
            servicio.hacer_algo()   # auditado como actor #42
        # fuera del bloque, el actor vuelve a su valor anterior
    """
    token = _actor_actual.set(ActorContexto(usuario_id, username, ip))
    try:
        yield
    finally:
        _actor_actual.reset(token)


__all__ = [
    "ActorContexto",
    "activar_actor",
    "actor_actual",
    "actor_ip",
    "actor_username",
    "limpiar_actor",
    "usar_actor",
]
