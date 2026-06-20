"""
src/interface/pages/academico/plantilla_editor_widget.py
========================================================
Helpers de interfaz reutilizables para gestionar plantillas de franja horaria
desde cualquier página (generador de horarios y, opcionalmente, admin).

Funciones públicas:
  • plantilla_form_dialog   — diálogo crear plantilla (nombre/jornada/días).
  • franja_form_dialog      — diálogo crear/editar una franja (horas/tipo/etiqueta).
  • render_franjas_editor   — tabla de franjas de una plantilla + acciones.
  • render_plantilla_preview — rejilla visual franjas × días activos.

La lógica de dominio (validaciones de solape, orden de horas, persistencia) vive
en `infraestructura_service`; estos helpers solo capturan los datos y delegan a
los callbacks que la página provee. Sin imports de servicios ni de `src.db`.
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.interface.design.tokens import Icons
from src.interface.design.components import empty_state
from src.interface.design.components.buttons import (
    btn_primary, btn_secondary, btn_ghost, btn_icon,
)

# Opciones de catálogo (misma fuente que el dominio: TIPOS_FRANJA / JORNADAS_VALIDAS).
JORNADA_OPTS = {"UNICA": "Única", "AM": "Mañana", "PM": "Tarde"}
TIPO_FRANJA_OPTS = {"lectiva": "Lectiva", "descanso": "Descanso", "almuerzo": "Almuerzo"}
DIAS_VALIDOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]


def _tipo_str(tipo) -> str:
    return tipo if isinstance(tipo, str) else getattr(tipo, "value", str(tipo))


def _input_hora(label: str, value: str):
    """Campo de hora amigable: máscara HH:MM + selector de reloj emergente.

    El usuario puede escribir (la máscara inserta el «:» y limita a dígitos) o
    pulsar el icono de reloj para elegir la hora en un selector visual de 24 h.
    Devuelve el `ui.input` para leer su `.value` ("HH:MM").
    """
    with ui.input(label, placeholder="07:00", value=value).classes("w-full") as inp:
        inp.props('mask="##:##"')
        with inp.add_slot("append"):
            btn_icon("schedule", on_click=lambda: menu.open())
        with ui.menu() as menu:
            ui.time().bind_value(inp).props("format24h")
    return inp


def plantilla_form_dialog(on_submit: Callable[[dict], None]) -> None:
    """Diálogo de creación de plantilla. `on_submit` recibe {nombre, jornada, dias}."""
    with ui.dialog() as dlg, ui.card().classes("andes-card form-dialog-card max-w-md"):
        ui.label("Nueva plantilla").classes("font-h3 form-dialog-title")

        in_nombre = ui.input(
            "Nombre *", placeholder="Ej: Plantilla Jornada Mañana",
        ).classes("w-full")
        sel_jornada = ui.select(
            list(JORNADA_OPTS.keys()), label="Jornada", value="UNICA",
        ).classes("w-full")
        sel_dias = ui.select(
            DIAS_VALIDOS, label="Días activos", value=[], multiple=True,
        ).classes("w-full")

        def _guardar() -> None:
            datos = {
                "nombre": str(in_nombre.value or "").strip(),
                "jornada": sel_jornada.value or "UNICA",
                "dias": list(sel_dias.value or []),
            }
            # La página decide si cierra el diálogo (devolviendo None) o no.
            if on_submit(datos) is not False:
                dlg.close()

        with ui.row().classes("gap-2 justify-end mt-4"):
            btn_ghost("Cancelar", on_click=dlg.close)
            btn_primary("Guardar", on_click=_guardar, icon="save")

    dlg.open()


def franja_form_dialog(
    franja,
    on_submit: Callable[[dict], None],
) -> None:
    """Diálogo crear (franja=None) o editar una franja.

    `on_submit` recibe {orden, hora_inicio, hora_fin, tipo, etiqueta}; orden es
    None en creación (la página asigna el siguiente).
    """
    es_edicion = franja is not None
    ini_inicio = getattr(franja, "hora_inicio", "") if es_edicion else ""
    ini_fin = getattr(franja, "hora_fin", "") if es_edicion else ""
    ini_tipo = _tipo_str(getattr(franja, "tipo", "lectiva")) if es_edicion else "lectiva"
    ini_etiqueta = (getattr(franja, "etiqueta", "") or "") if es_edicion else ""

    with ui.dialog() as dlg, ui.card().classes("andes-card form-dialog-card max-w-sm"):
        ui.label("Editar franja" if es_edicion else "Añadir franja").classes(
            "font-h3 form-dialog-title"
        )
        in_inicio = _input_hora("Hora inicio *", ini_inicio)
        in_fin = _input_hora("Hora fin *", ini_fin)
        sel_tipo = ui.select(
            list(TIPO_FRANJA_OPTS.keys()), label="Tipo", value=ini_tipo,
        ).classes("w-full")
        in_etiqueta = ui.input(
            "Etiqueta (opcional)", placeholder="Ej: Período 1", value=ini_etiqueta,
        ).classes("w-full")

        def _guardar() -> None:
            datos = {
                "orden": getattr(franja, "orden", None) if es_edicion else None,
                "hora_inicio": str(in_inicio.value or "").strip(),
                "hora_fin": str(in_fin.value or "").strip(),
                "tipo": str(sel_tipo.value or "lectiva"),
                "etiqueta": str(in_etiqueta.value or "").strip() or None,
            }
            if on_submit(datos) is not False:
                dlg.close()

        with ui.row().classes("gap-2 justify-end mt-4"):
            btn_ghost("Cancelar", on_click=dlg.close)
            btn_primary("Guardar", on_click=_guardar, icon="save")

    dlg.open()


def render_franjas_editor(
    franjas: list,
    on_add: Callable[[], None] | None = None,
    on_edit: Callable[[int], None] | None = None,
    on_delete: Callable[[int], None] | None = None,
    puede_editar: bool = True,
) -> None:
    """Tabla de franjas (ordenadas) con acciones editar/eliminar y botón añadir."""
    with ui.row().classes("items-center justify-between u-mb-sm"):
        ui.label("Franjas de la plantilla").classes("text-subtitle2 font-semibold")
        if puede_editar and on_add:
            btn_secondary("Añadir franja", icon="add", on_click=on_add)

    if not franjas:
        empty_state(
            icono=Icons.SCHEDULE,
            titulo="Sin franjas",
            descripcion="Añade franjas (lectivas y de descanso) para definir la rejilla.",
        )
        return

    ordenadas = sorted(franjas, key=lambda f: f.orden)
    with ui.element("div").classes("overflow-auto"):
        with ui.element("table").classes("w-full border-collapse text-sm"):
            with ui.element("thead"):
                with ui.element("tr"):
                    for col in ("#", "Inicio", "Fin", "Tipo", "Etiqueta", "Acciones"):
                        with ui.element("th").classes(
                            "border px-3 py-2 text-left font-semibold bg-surface-alt"
                        ):
                            ui.label(str(col))
            with ui.element("tbody"):
                for f in ordenadas:
                    with ui.element("tr"):
                        with ui.element("td").classes("border px-3 py-2"):
                            ui.label(str(f.orden))
                        with ui.element("td").classes("border px-3 py-2"):
                            ui.label(str(f.hora_inicio))
                        with ui.element("td").classes("border px-3 py-2"):
                            ui.label(str(f.hora_fin))
                        with ui.element("td").classes("border px-3 py-2"):
                            ui.label(TIPO_FRANJA_OPTS.get(_tipo_str(f.tipo), _tipo_str(f.tipo)))
                        with ui.element("td").classes("border px-3 py-2"):
                            ui.label(str(f.etiqueta or "—"))
                        with ui.element("td").classes("border px-3 py-2"):
                            if puede_editar:
                                with ui.row().classes("gap-1"):
                                    if on_edit:
                                        btn_icon("edit", on_click=lambda _, o=f.orden: on_edit(o))
                                    if on_delete:
                                        btn_icon("delete", on_click=lambda _, o=f.orden: on_delete(o))


def render_plantilla_preview(plantilla, franjas: list) -> None:
    """Rejilla visual: franjas (filas) × días activos (columnas)."""
    dias = list(getattr(plantilla, "dias_activos", None) or [])
    if not dias:
        empty_state(
            icono=Icons.SCHEDULE,
            titulo="Sin días activos",
            descripcion="Esta plantilla no tiene días activos configurados.",
        )
        return
    if not franjas:
        empty_state(
            icono=Icons.SCHEDULE,
            titulo="Sin franjas",
            descripcion="Añade franjas para ver la rejilla.",
        )
        return

    ordenadas = sorted(franjas, key=lambda f: f.orden)
    with ui.element("div").classes("parrilla-scroll"):
        with ui.element("div").classes("parrilla-grid").style(
            # DYNAMIC: nº de columnas depende de los días activos
            f"grid-template-columns: 160px repeat({len(dias)}, minmax(100px, 1fr))"
        ):
            with ui.element("div").classes("parrilla-encabezado parrilla-esquina"):
                ui.label("Hora")
            for dia in dias:
                with ui.element("div").classes("parrilla-encabezado"):
                    ui.label(str(dia))

            for f in ordenadas:
                lectiva = (_tipo_str(f.tipo) == "lectiva")
                label_cls = "parrilla-franja-label" + ("" if lectiva else " parrilla-franja-nolectiva")
                etiqueta = f.etiqueta or f"{f.hora_inicio}–{f.hora_fin}"
                with ui.element("div").classes(label_cls):
                    ui.label(str(etiqueta))
                for _dia in dias:
                    if lectiva:
                        with ui.element("div").classes("parrilla-celda parrilla-hueco"):
                            ui.label(f"{f.hora_inicio}–{f.hora_fin}").classes("parrilla-celda-sub")
                    else:
                        with ui.element("div").classes(
                            "parrilla-celda parrilla-hueco parrilla-nolectiva-celda"
                        ):
                            ui.label(
                                TIPO_FRANJA_OPTS.get(_tipo_str(f.tipo), "Descanso")
                            ).classes("parrilla-nolectiva-texto")


__all__ = [
    "plantilla_form_dialog",
    "franja_form_dialog",
    "render_franjas_editor",
    "render_plantilla_preview",
]
