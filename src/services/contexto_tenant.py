"""
contexto_tenant.py — Scope de institución central de la capa de servicios.
===========================================================================

Mecanismo neutral (sin dependencias de interfaz/infra) que expone la
institución activa de la sesión actual, espejando el patrón de
`solo_lectura.py`. Sirve de "choke point" para que los servicios
tenant-aware resuelvan el `institucion_id` que pasan a los repos
parametrizados, sin cablear el filtro página por página.

Diseño (decisión de David — frente C multi-tenant):
  - El estado vive en un `contextvars.ContextVar[int | None]` privado,
    default `None`. Cada página y cada handler de NiceGUI corren en su
    propia task y releen el contexto al inicio, de modo que el scope queda
    propagado dentro de la task del handler.
  - El choke point de activación es `SessionContext` (capa de interfaz),
    que llama `activar_institucion(scope)` con la REGLA DE SCOPE:
        scope = None  si el rol efectivo de la sesión es "admin"
        scope = institucion_id  en otro caso (director, profesor, ...)
    Durante "Ver como" el rol efectivo es el del usuario objetivo, así que
    el scope queda en la institución del objetivo; al salir vuelve a None
    (admin real).
  - `None` ⇒ los servicios NO auto-filtran (admin opera cross-tenant /
    filtra explícito). Un entero ⇒ los servicios scopean a esa institución.
  - `usar_institucion(id)` es un context manager para seed/scripts/tests
    que no tienen sesión: setea el scope y lo restaura al salir.

Regla de capas: este módulo NO importa interfaz ni infraestructura. Los
repos siguen recibiendo `institucion_id` por parámetro (no importan de
services); el scope se resuelve en el servicio.
"""
from __future__ import annotations

import contextlib
import contextvars
from typing import Iterator

# Estado privado. Default None → sin scope (admin / arranque sin sesión).
_institucion_actual: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "zeci_institucion_actual", default=None
)


def activar_institucion(institucion_id: int | None) -> None:
    """Fija la institución activa del contexto actual (None = sin scope)."""
    _institucion_actual.set(institucion_id)


def institucion_actual() -> int | None:
    """
    Retorna la institución activa del contexto actual.

    `None` significa "sin scope" (admin opera cross-tenant o arranque sin
    sesión); un entero es el tenant al que los servicios deben acotarse.
    """
    return _institucion_actual.get()


class OperacionFueraDeInstitucionError(PermissionError):
    """
    Se intentó operar (leer/mutar por id) sobre un objeto que NO pertenece a
    la institución activa de la sesión.

    Cierra la dimensión multi-tenant de la seguridad del enrutado (hallazgo E,
    paso_36): el scope filtra listados, pero las operaciones por `id` también
    deben verificar que el objeto leído del repo sea del tenant del usuario.
    """


def verificar_pertenencia(institucion_id_objeto: int | None) -> None:
    """
    Verifica que un objeto pertenezca a la institución activa de la sesión.

    Regla de scope (espejo de los demás helpers tenant-aware):
      - `institucion_actual()` es None (admin de plataforma / seed / arranque
        sin sesión) → NO hace nada (cross-tenant permitido por diseño).
      - en otro caso → lanza `OperacionFueraDeInstitucionError` si
        `institucion_id_objeto` difiere de la institución activa.

    CRÍTICO: `institucion_id_objeto` debe ser el `institucion_id` del registro
    LEÍDO DEL REPO por su id, nunca el que pasó el caller (podría venir forjado
    para coincidir con el del atacante).
    """
    scope = _institucion_actual.get()
    if scope is None:
        return
    if institucion_id_objeto != scope:
        raise OperacionFueraDeInstitucionError(
            "La operación afecta a un objeto que no pertenece a tu institución."
        )


@contextlib.contextmanager
def usar_institucion(institucion_id: int | None) -> Iterator[None]:
    """
    Context manager que fija la institución activa y la restaura al salir.

    Pensado para seed/scripts/tests que no tienen sesión de interfaz:

        with usar_institucion(2):
            servicio.hacer_algo()   # scopeado a la institución #2
        # fuera del bloque, el scope vuelve a su valor anterior
    """
    token = _institucion_actual.set(institucion_id)
    try:
        yield
    finally:
        _institucion_actual.reset(token)


__all__ = [
    "activar_institucion",
    "institucion_actual",
    "usar_institucion",
    "verificar_pertenencia",
    "OperacionFueraDeInstitucionError",
]
