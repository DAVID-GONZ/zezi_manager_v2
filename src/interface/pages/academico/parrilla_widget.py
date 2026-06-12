"""
src/interface/pages/academico/parrilla_widget.py
===============================================
Helper compartido para renderizar una parrilla de horario en la capa de
interfaz. Permite reutilizar el mismo renderizado desde varias páginas.
"""
from __future__ import annotations

from nicegui import ui

from src.interface.design.tokens import Icons
from src.interface.design.components import empty_state


def _clave_eje(celda: dict, perspectiva: str):
    if perspectiva == "Grupo":
        return celda["grupo_id"]
    if perspectiva == "Docente":
        return celda["usuario_id"]
    return celda["sala"]


def _opciones_eje(datos: dict, perspectiva: str) -> dict:
    opts: dict = {}
    for c in datos["celdas"]:
        if perspectiva == "Grupo":
            opts.setdefault(c["grupo_id"], c["grupo_codigo"])
        elif perspectiva == "Docente":
            opts.setdefault(c["usuario_id"], c["docente_nombre"])
        else:
            opts.setdefault(c["sala"], c["sala"])
    return dict(sorted(opts.items(), key=lambda kv: str(kv[1])))


def render_parrilla(
    datos: dict,
    perspectiva: str,
    eje_sel: int | str | None,
    dias_filtro: set[str] | None = None,
    areas_filtro: set[int] | None = None,
) -> None:
    """Renderiza la grilla de horario para la página de horarios.

    Args:
        datos:       Diccionario con las claves "dias", "franjas" y "celdas".
        perspectiva: "Grupo", "Docente" o "Sala".
        eje_sel:     Identificador del eje seleccionado (grupo_id, usuario_id o sala).
        dias_filtro: Conjunto de días a mostrar, o None para mostrar todos.
        areas_filtro: Conjunto de area_id a mostrar, o None para mostrar todas.
    """
    if not datos.get("celdas") or not datos.get("franjas"):
        empty_state(
            icono=Icons.SCHEDULE,
            titulo="Sin bloques para mostrar",
            descripcion="La parrilla no tiene bloques de horario para el criterio seleccionado.",
        )
        return

    dias_activos = datos.get("dias") or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    if dias_filtro is not None:
        dias = [d for d in dias_activos if d in dias_filtro]
    else:
        dias = dias_activos
    if not dias:
        dias = dias_activos

    eje_opts = _opciones_eje(datos, perspectiva)
    if eje_sel not in eje_opts:
        eje_sel = next(iter(eje_opts), None)

    if eje_sel is None:
        empty_state(
            icono=Icons.SCHEDULE,
            titulo="Sin eje seleccionado",
            descripcion="Selecciona una perspectiva con bloques existentes para ver la parrilla.",
        )
        return

    # Indexar celdas por día/hora aplicando filtros de eje y área.
    idx: dict[tuple[str, str], list[dict]] = {}
    for c in datos["celdas"]:
        if _clave_eje(c, perspectiva) != eje_sel:
            continue
        if areas_filtro is not None and c.get("area_id") not in areas_filtro:
            continue
        idx.setdefault((c["dia_semana"], c["hora_inicio"]), []).append(c)

    with ui.element("div").classes("parrilla-grid").style(
        f"grid-template-columns: 160px repeat({len(dias)}, minmax(120px, 1fr))"
    ):
        ui.element("div").classes("parrilla-encabezado").text = "Hora"
        for dia in dias:
            ui.element("div").classes("parrilla-encabezado").text = dia

        for fr in datos["franjas"]:
            lectiva = fr.get("lectiva", True)
            label_cls = "parrilla-franja-label" + ("" if lectiva else " parrilla-franja-nolectiva")
            etiqueta = fr.get("etiqueta") or f"{fr['hora_inicio']}–{fr['hora_fin']}"
            ui.element("div").classes(label_cls).text = etiqueta

            for dia in dias:
                if not lectiva:
                    ui.element("div").classes("parrilla-celda parrilla-hueco")
                    continue

                bloques = idx.get((dia, fr["hora_inicio"]), [])
                if not bloques:
                    ui.element("div").classes("parrilla-celda parrilla-hueco")
                    continue

                conflicto = len(bloques) > 1
                primero = bloques[0]
                celda_cls = "parrilla-celda"
                if conflicto:
                    celda_cls += " parrilla-conflicto"

                color = primero.get("area_color")
                if color:
                    celda = ui.element("div").classes(celda_cls)
                    celda.style(f"background-color:{color}")  # DYNAMIC: color por área de conocimiento
                else:
                    area_id = primero.get("area_id") or 0
                    celda_cls += f" parrilla-area-{area_id % 10}"
                    celda = ui.element("div").classes(celda_cls)

                with celda:
                    ui.label(primero["asignatura_nombre"]).classes("parrilla-celda-titulo")
                    if perspectiva == "Grupo":
                        ui.label(primero["docente_nombre"]).classes("parrilla-celda-sub")
                    elif perspectiva == "Docente":
                        ui.label(primero["grupo_codigo"]).classes("parrilla-celda-sub")
                    else:
                        ui.label(
                            f"{primero['grupo_codigo']} · {primero['docente_nombre']}"
                        ).classes("parrilla-celda-sub")


__all__ = ["render_parrilla"]
