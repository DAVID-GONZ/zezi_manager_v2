"""
Interceptor global de eventos NiceGUI — aislamiento multi-tenant (Fase 1A).

NiceGUI despacha cada event handler (click, filtro, submit) en una task asyncio
distinta a la del HTTP request que renderizó la página. Los ContextVars de Python
no se propagan entre tasks, por lo que _institucion_actual y _solo_lectura
vuelven a None en cada handler, desactivando el scope de tenant en los servicios.

instalar_interceptor_tenant() envuelve Client.handle_event una sola vez para que
cada evento re-sincronice los ContextVars desde app.storage.user antes de
despachar al elemento.
"""

from __future__ import annotations

from nicegui.client import Client

_original_handle_event = None


def instalar_interceptor_tenant() -> None:
    """Instala el wrapper de tenant en Client.handle_event. Idempotente."""
    global _original_handle_event

    if _original_handle_event is not None:
        return

    _original_handle_event = Client.handle_event

    def _wrapper(self: Client, msg: dict) -> None:
        from src.interface.context.session_context import SessionContext  # noqa: PLC0415
        try:
            SessionContext.desde_storage()
        except RuntimeError as exc:
            if "can only be used within a UI context" not in str(exc):
                raise
        _original_handle_event(self, msg)

    Client.handle_event = _wrapper
