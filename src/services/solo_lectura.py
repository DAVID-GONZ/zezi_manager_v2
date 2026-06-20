"""
solo_lectura.py — Modo de solo lectura central de la capa de servicios.
========================================================================

Mecanismo neutral (sin dependencias de interfaz) que permite bloquear las
operaciones de MUTACIÓN de todos los servicios de aplicación durante una
sesión de impersonación "Ver como" del administrador.

Diseño (decisión de David):
  - El bloqueo es CENTRAL en la capa de servicios, no página por página.
  - El estado vive en un `contextvars.ContextVar[bool]` privado, default `False`.
    Esto garantiza que el comportamiento normal y los tests existentes NO
    cambian (el flag arranca apagado en cada contexto/task nuevo).
  - Los servicios llaman `verificar_escritura()` (o usan el decorador
    `requiere_escritura`) al INICIO de cada método de mutación. Los métodos
    de LECTURA no se tocan.
  - El choke point de activación es `SessionContext.desde_storage()` (capa de
    interfaz), que llama `activar_solo_lectura(self.solo_lectura)`. Como
    NiceGUI ejecuta cada página y cada handler en su propia task y el contexto
    se relee al inicio, el flag queda correctamente propagado dentro de la
    task del handler de escritura.

Regla de capas: este módulo NO importa interfaz ni infraestructura.
"""
from __future__ import annotations

import contextvars
import functools
from typing import Callable, TypeVar

# Estado privado. Default False → comportamiento normal sin impersonación.
_solo_lectura: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "zeci_solo_lectura", default=False
)


class OperacionSoloLecturaError(PermissionError):
    """
    Se lanza cuando se intenta una operación de escritura mientras la sesión
    está en modo solo lectura (impersonación "Ver como").

    Hereda de PermissionError para que el código que ya captura permisos
    la trate de forma coherente.
    """

    def __init__(self, mensaje: str | None = None) -> None:
        super().__init__(
            mensaje
            or "Sesión en modo solo lectura (Ver como): no se permiten cambios."
        )


def activar_solo_lectura(valor: bool) -> None:
    """Activa o desactiva el modo solo lectura para el contexto actual."""
    _solo_lectura.set(bool(valor))


def es_solo_lectura() -> bool:
    """Indica si el contexto actual está en modo solo lectura."""
    return _solo_lectura.get()


def verificar_escritura() -> None:
    """
    Punto de control para métodos de mutación.

    Lanza `OperacionSoloLecturaError` si el contexto actual está en modo
    solo lectura. No hace nada en el modo normal (default).
    """
    if _solo_lectura.get():
        raise OperacionSoloLecturaError()


F = TypeVar("F", bound=Callable[..., object])


def requiere_escritura(func: F) -> F:
    """
    Decorador equivalente a llamar `verificar_escritura()` al inicio del método.

    Útil para anotar métodos de mutación sin tocar su cuerpo:

        @requiere_escritura
        def crear_usuario(self, dto): ...
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        verificar_escritura()
        return func(*args, **kwargs)

    return _wrapper  # type: ignore[return-value]


__all__ = [
    "OperacionSoloLecturaError",
    "activar_solo_lectura",
    "es_solo_lectura",
    "verificar_escritura",
    "requiere_escritura",
]
