from __future__ import annotations

from src.interface.context.session_context import SessionContext
from src.interface.design.components.context_selector import abrir_selector


def context_bar(
    ctx: SessionContext,
    on_change=None,
    mostrar_asignatura: bool = True,
) -> None:
    """Compatibilidad ligera para `context_bar`.

    Este helper expone una API mínima para auditorías de componentes que
    esperan `context_bar` existiendo en el package.
    """
    abrir_selector(ctx=ctx, on_change=on_change, mostrar_asignatura=mostrar_asignatura)
