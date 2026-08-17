"""
period_status.py — Tarjeta de estado del periodo activo.

Componente de presentación puro: recibe un PeriodData,
no llama servicios ni Container.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from nicegui import ui

from src.interface.design.components.status_badge import status_badge


@dataclass
class PeriodData:
    """Datos del periodo activo para renderizar la tarjeta."""
    nombre: str
    fecha_inicio: date | None
    fecha_fin: date | None
    cerrado: bool


def _clase_periodo_bar(progreso: float) -> str:
    if progreso < 60:
        return ""
    if progreso < 85:
        return "warning"
    return "error"


def _clase_period_days(dias_restantes: int) -> str:
    if dias_restantes < 7:
        return "period-days period-days-danger"
    if dias_restantes < 15:
        return "period-days period-days-warn"
    return "period-days period-days-ok"


def period_status_card(periodo: PeriodData) -> None:
    """Tarjeta con nombre del periodo, barra de progreso y estado.

    Args:
        periodo: Datos del periodo activo.
    """
    with ui.element("div").classes("panel-card period-status-card"):
        ui.label("Periodo activo").classes("eyebrow-label")
        ui.label(periodo.nombre).classes("period-name")

        hoy = date.today()
        if periodo.fecha_inicio and periodo.fecha_fin:
            total_dias = (periodo.fecha_fin - periodo.fecha_inicio).days
            dias_pasados = (hoy - periodo.fecha_inicio).days
            dias_rest = (periodo.fecha_fin - hoy).days
            progreso = min(100, max(0,
                dias_pasados / total_dias * 100 if total_dias > 0 else 0
            ))
            clase_bar = _clase_periodo_bar(progreso)

            with ui.element("div").classes("period-dates-row"):
                ui.label(periodo.fecha_inicio.strftime("%d %b")).classes("text-xs-meta")
                ui.label(periodo.fecha_fin.strftime("%d %b")).classes("text-xs-meta")

            with ui.element("div").classes("period-bar-track"):
                ui.element("div").classes(
                    f"period-bar-fill {clase_bar}"
                ).style(f"width:{progreso:.0f}%")  # DYNAMIC: valor calculado

            ui.label(
                f"{max(0, dias_rest)} días restantes · {progreso:.0f}% transcurrido"
            ).classes(_clase_period_days(dias_rest))

        if periodo.cerrado:
            status_badge("Cerrado", "neutral")
        else:
            status_badge("Activo", "success")


__all__ = ["PeriodData", "period_status_card"]
