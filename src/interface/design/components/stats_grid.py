"""
stats_grid.py — Grid de stat_cards en layout responsivo.

Componente de presentación puro: recibe lista de StatItem,
no llama servicios ni Container.
"""
from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from src.interface.design.components.stat_card import stat_card


@dataclass
class StatItem:
    """Datos de un stat-card individual."""
    titulo: str
    valor: str
    icono: str
    subtitulo: str = ""
    variante: str = "primary"


def stats_grid(items: list[StatItem]) -> None:
    """Grid de stat-cards usando .stats-grid.

    Args:
        items: Lista de StatItem con los datos de cada tarjeta.
    """
    with ui.element("div").classes("stats-grid"):
        for item in items:
            stat_card(
                titulo=item.titulo,
                valor=item.valor,
                icono=item.icono,
                subtitulo=item.subtitulo,
                variante=item.variante,
            )


__all__ = ["StatItem", "stats_grid"]
