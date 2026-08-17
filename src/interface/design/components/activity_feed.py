"""
activity_feed.py — Feed de actividad reciente con timeline vertical.

Componente de presentación puro: recibe lista de ActivityItem,
no llama servicios ni Container.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nicegui import ui

from src.interface.design.components.section_panel import section_panel


@dataclass
class ActivityItem:
    """Un registro de actividad para el feed."""
    etiqueta: str
    categoria: str
    timestamp: datetime | str | None


def _tiempo_relativo(ts: datetime | str | None) -> str:
    """Calcula tiempo relativo humanizado desde un timestamp."""
    try:
        if ts is None:
            return "—"
        fecha = (
            datetime.fromisoformat(ts) if isinstance(ts, str) and "T" in ts
            else datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S") if isinstance(ts, str)
            else ts
        )
        delta = datetime.now() - fecha
        if delta.days > 0:
            return f"Hace {delta.days}d"
        h = delta.seconds // 3600
        if h > 0:
            return f"Hace {h}h"
        m = delta.seconds // 60
        return f"Hace {m}m" if m > 0 else "Ahora"
    except Exception:
        return "—"


def activity_feed(
    items: list[ActivityItem],
    *,
    titulo: str = "Actividad reciente",
    icono: str = "history",
) -> None:
    """Feed de actividad reciente con dot-timeline.

    Args:
        items:  Lista de registros de actividad.
        titulo: Texto del encabezado del panel.
        icono:  Icono del encabezado.
    """
    with section_panel(titulo, icono):
        if not items:
            ui.label("Sin actividad reciente").classes("empty-state-lg")
            return

        for item in items:
            tiempo = _tiempo_relativo(item.timestamp)
            with ui.element("div").classes("activity-feed-item"):
                ui.element("div").classes("activity-dot")
                with ui.element("div").classes("feed-text-col"):
                    ui.label(item.etiqueta).classes("feed-label")
                    ui.label(item.categoria).classes("feed-meta")
                ui.label(tiempo).classes("feed-time")


__all__ = ["ActivityItem", "activity_feed"]
