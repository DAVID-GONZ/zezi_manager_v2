"""
historial_cambios.py — Línea temporal de cambios de un registro.

Componente de presentación puro: recibe lista de DetalleCambioDTO ya
resuelta por AuditoriaService.historial_de, no llama a Container ni servicios
(R6). Sigue la misma forma que activity_feed.py.

Clases usadas: section_panel (.panel-card), .badge-* para la acción,
.empty-state para el estado vacío, y las propias del timeline definidas en
styles/components/historial.css registradas en CLASS_CONTRACT.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nicegui import ui

from src.interface.design.components.empty_state import empty_state
from src.interface.design.components.section_panel import section_panel
from src.interface.design.components.status_badge import status_badge


@dataclass
class HistorialItem:
    """Una entrada del historial, ya resuelta. Sin dependencias de servicio.

    Construida a partir de un DetalleCambioDTO por la página antes de
    invocar a historial_cambios().
    """

    fecha: str
    actor: str
    accion: str                    # CREATE | UPDATE | DELETE | READ
    campos: list = field(default_factory=list)   # list[CampoDiffDTO]


# Mapa accion → variante de badge semántico
_ACCION_BADGE: dict[str, str] = {
    "CREATE": "success",
    "UPDATE": "info",
    "DELETE": "error",
    "READ": "neutral",
}

# Mapa accion → etiqueta legible en español
_ACCION_LABEL: dict[str, str] = {
    "CREATE": "Creación",
    "UPDATE": "Edición",
    "DELETE": "Eliminación",
    "READ": "Lectura",
}


def historial_cambios(
    items: list[HistorialItem],
    *,
    titulo: str = "Historial de cambios",
    icono: str = "manage_history",
) -> None:
    """Línea temporal de cambios de un registro. Presentación pura (R6).

    Args:
        items:  Lista de entradas del historial, ya resueltas a HistorialItem.
        titulo: Texto del encabezado del panel.
        icono:  Icono del encabezado del panel.
    """
    with section_panel(titulo, icono):
        if not items:
            empty_state(
                icono="history",
                titulo="Sin historial disponible",
                descripcion="Este registro no tiene cambios auditados.",
                variante="default",
            )
            return

        with ui.element("div").classes("historial-timeline"):
            for item in items:
                _render_item(item)


def _render_item(item: HistorialItem) -> None:
    """Renderiza una entrada individual del historial."""
    accion_upper = (item.accion or "").upper()
    badge_variante = _ACCION_BADGE.get(accion_upper, "neutral")
    accion_label = _ACCION_LABEL.get(accion_upper, item.accion)

    with ui.element("div").classes("historial-item"):
        # Encabezado: fecha, actor y badge de acción
        with ui.element("div").classes("historial-meta"):
            ui.label(item.fecha).classes("historial-fecha")
            ui.label(item.actor).classes("historial-actor")
            status_badge(accion_label, badge_variante)

        # Diff campo a campo (si hay campos)
        campos_visibles = list(item.campos or [])
        if campos_visibles:
            with ui.element("div").classes("historial-campos"):
                for campo in campos_visibles:
                    _render_campo(campo)


def _render_campo(campo) -> None:
    """Renderiza un campo del diff."""
    nombre = getattr(campo, "nombre", "")
    oculto = getattr(campo, "oculto", False)
    valor_anterior = getattr(campo, "valor_anterior", None)
    valor_nuevo = getattr(campo, "valor_nuevo", None)
    tipo = str(getattr(campo, "tipo", "")).lower()

    with ui.element("div").classes("historial-campo"):
        ui.label(nombre).classes("historial-campo-nombre")

        if oculto:
            ui.label("(campo protegido)").classes("historial-valor historial-valor--oculto")
        elif tipo == "sin_cambio":
            pass  # no renderizar campos sin cambio
        elif tipo == "anadido":
            ui.label(str(valor_nuevo) if valor_nuevo is not None else "—").classes(
                "historial-valor historial-valor--nuevo"
            )
        elif tipo == "eliminado":
            ui.label(str(valor_anterior) if valor_anterior is not None else "—").classes(
                "historial-valor historial-valor--anterior"
            )
        else:
            # modificado
            with ui.element("div").classes("historial-valor-par"):
                ui.label(str(valor_anterior) if valor_anterior is not None else "—").classes(
                    "historial-valor historial-valor--anterior"
                )
                ui.icon("arrow_forward", size="xs").classes("historial-valor-flecha")
                ui.label(str(valor_nuevo) if valor_nuevo is not None else "—").classes(
                    "historial-valor historial-valor--nuevo"
                )


__all__ = ["HistorialItem", "historial_cambios"]
