"""
src/interface/pages/academico/parrilla_widget.py
===============================================
Helper compartido para renderizar una parrilla de horario en la capa de
interfaz. Permite reutilizar el mismo renderizado desde varias páginas.

Dos renderizadores:
  • render_parrilla         — vista "Por entidad" (Grupo/Docente/Sala),
                              días × franjas para un único eje seleccionado.
  • render_tablero_maestro  — vista "Tablero maestro": grupos en columnas,
                              franjas en filas, para un único día.

Ambos comparten el diseño de celda (acento de color por área en el borde
izquierdo, texto legible) y la lógica de clic/edición integrada.
"""
from __future__ import annotations

from typing import Callable

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


def _grupos_presentes(datos: dict) -> dict:
    """Mapa {grupo_id: grupo_codigo} ordenado por código."""
    opts: dict = {}
    for c in datos["celdas"]:
        opts.setdefault(c["grupo_id"], c["grupo_codigo"])
    return dict(sorted(opts.items(), key=lambda kv: str(kv[1])))


def _render_celda_ocupada(
    bloques: list[dict],
    perspectiva: str,
    on_celda_click: Callable[[dict], None] | None,
    puede_editar: bool,
) -> None:
    """Pinta una celda con uno o más bloques (acento de área + clic opcional)."""
    conflicto = len(bloques) > 1
    primero = bloques[0]

    celda_cls = "parrilla-celda"
    if conflicto:
        celda_cls += " parrilla-conflicto"

    clicable = bool(puede_editar and on_celda_click)
    if clicable:
        celda_cls += " parrilla-celda-click"

    color = primero.get("area_color")
    if color:
        celda = ui.element("div").classes(celda_cls)
        celda.style(f"border-left-color:{color}")  # DYNAMIC: color por área de conocimiento
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

    if clicable:
        ctx = {"tipo": "ocupada", "celda": primero}
        celda.on("click", lambda _, c=ctx: on_celda_click(c))


def _render_celda_vacia(
    dia: str,
    hora_inicio: str,
    grupo_id: int | None,
    on_celda_click: Callable[[dict], None] | None,
    puede_editar: bool,
) -> None:
    """Pinta una celda vacía; clicable solo si hay un grupo_id inequívoco."""
    clicable = bool(puede_editar and on_celda_click and grupo_id is not None)
    cls = "parrilla-celda parrilla-hueco"
    if clicable:
        cls += " parrilla-celda-click"
    celda = ui.element("div").classes(cls)
    if clicable:
        ctx = {
            "tipo": "vacia",
            "grupo_id": grupo_id,
            "dia": dia,
            "hora_inicio": hora_inicio,
        }
        celda.on("click", lambda _, c=ctx: on_celda_click(c))


def render_parrilla(
    datos: dict,
    perspectiva: str,
    eje_sel: int | str | None,
    dias_filtro: set[str] | None = None,
    areas_filtro: set[int] | None = None,
    on_celda_click: Callable[[dict], None] | None = None,
    puede_editar: bool = False,
) -> None:
    """Renderiza la grilla de horario "Por entidad".

    Args:
        datos:        Diccionario con las claves "dias", "franjas" y "celdas".
        perspectiva:  "Grupo", "Docente" o "Sala".
        eje_sel:      Identificador del eje seleccionado (grupo_id, usuario_id o sala).
        dias_filtro:  Conjunto de días a mostrar, o None para mostrar todos.
        areas_filtro: Conjunto de area_id a mostrar, o None para mostrar todas.
        on_celda_click: Callback que recibe un dict de contexto al hacer clic.
        puede_editar:  Si True (y hay callback), las celdas son clicables.
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

    # En perspectiva Grupo, la celda vacía pertenece al grupo seleccionado.
    # En Docente/Sala el grupo es ambiguo → celdas vacías no clicables.
    grupo_vacia = eje_sel if perspectiva == "Grupo" else None

    # Indexar celdas por día/hora aplicando filtros de eje y área.
    idx: dict[tuple[str, str], list[dict]] = {}
    for c in datos["celdas"]:
        if _clave_eje(c, perspectiva) != eje_sel:
            continue
        if areas_filtro is not None and c.get("area_id") not in areas_filtro:
            continue
        idx.setdefault((c["dia_semana"], c["hora_inicio"]), []).append(c)

    with ui.element("div").classes("parrilla-scroll"):
        with ui.element("div").classes("parrilla-grid").style(
            f"grid-template-columns: 160px repeat({len(dias)}, minmax(120px, 1fr))"
        ):
            with ui.element("div").classes("parrilla-encabezado parrilla-esquina"):
                ui.label("Hora")
            for dia in dias:
                with ui.element("div").classes("parrilla-encabezado"):
                    ui.label(str(dia))

            for fr in datos["franjas"]:
                lectiva = fr.get("lectiva", True)
                label_cls = "parrilla-franja-label" + ("" if lectiva else " parrilla-franja-nolectiva")
                etiqueta = fr.get("etiqueta") or f"{fr['hora_inicio']}–{fr['hora_fin']}"
                with ui.element("div").classes(label_cls):
                    ui.label(str(etiqueta))

                for dia in dias:
                    if not lectiva:
                        with ui.element("div").classes("parrilla-celda parrilla-hueco parrilla-nolectiva-celda"):
                            ui.label(fr.get("etiqueta") or "Descanso").classes("parrilla-nolectiva-texto")
                        continue

                    bloques = idx.get((dia, fr["hora_inicio"]), [])
                    if not bloques:
                        _render_celda_vacia(
                            dia, fr["hora_inicio"], grupo_vacia,
                            on_celda_click, puede_editar,
                        )
                        continue

                    _render_celda_ocupada(bloques, perspectiva, on_celda_click, puede_editar)


def render_tablero_maestro(
    datos: dict,
    dia: str,
    areas_filtro: set[int] | None = None,
    on_celda_click: Callable[[dict], None] | None = None,
    puede_editar: bool = False,
) -> None:
    """Renderiza el tablero maestro: grupos en columnas, franjas en filas.

    Args:
        datos:        Diccionario con "dias", "franjas" y "celdas".
        dia:          Día a mostrar (las columnas son TODOS los grupos).
        areas_filtro: Conjunto de area_id a mostrar, o None para todas.
        on_celda_click: Callback de contexto al hacer clic.
        puede_editar:  Si True (y hay callback), las celdas son clicables.
    """
    if not datos.get("celdas") or not datos.get("franjas"):
        empty_state(
            icono=Icons.SCHEDULE,
            titulo="Sin bloques para mostrar",
            descripcion="La parrilla no tiene bloques de horario para el criterio seleccionado.",
        )
        return

    grupos = _grupos_presentes(datos)
    if not grupos:
        empty_state(
            icono=Icons.SCHEDULE,
            titulo="Sin grupos",
            descripcion="No hay grupos con bloques en este escenario.",
        )
        return

    # Índice por (grupo_id, dia, hora_inicio) → lista de bloques
    idx: dict[tuple[int, str, str], list[dict]] = {}
    for c in datos["celdas"]:
        if c["dia_semana"] != dia:
            continue
        if areas_filtro is not None and c.get("area_id") not in areas_filtro:
            continue
        idx.setdefault((c["grupo_id"], c["dia_semana"], c["hora_inicio"]), []).append(c)

    grupo_ids = list(grupos.keys())

    with ui.element("div").classes("parrilla-scroll"):
        with ui.element("div").classes("tablero-maestro").style(
            f"grid-template-columns: 160px repeat({len(grupo_ids)}, minmax(140px, 1fr))"
        ):
            with ui.element("div").classes("tablero-grupo-cabecera parrilla-esquina"):
                ui.label("Hora")
            for gid in grupo_ids:
                with ui.element("div").classes("tablero-grupo-cabecera"):
                    ui.label(str(grupos[gid]))

            for fr in datos["franjas"]:
                lectiva = fr.get("lectiva", True)
                label_cls = "parrilla-franja-label" + ("" if lectiva else " parrilla-franja-nolectiva")
                etiqueta = fr.get("etiqueta") or f"{fr['hora_inicio']}–{fr['hora_fin']}"
                with ui.element("div").classes(label_cls):
                    ui.label(str(etiqueta))

                for gid in grupo_ids:
                    if not lectiva:
                        with ui.element("div").classes("parrilla-celda parrilla-hueco parrilla-nolectiva-celda"):
                            ui.label(fr.get("etiqueta") or "Descanso").classes("parrilla-nolectiva-texto")
                        continue

                    bloques = idx.get((gid, dia, fr["hora_inicio"]), [])
                    if not bloques:
                        _render_celda_vacia(
                            dia, fr["hora_inicio"], gid,
                            on_celda_click, puede_editar,
                        )
                        continue

                    # En el tablero maestro el subtítulo útil es el docente.
                    _render_celda_ocupada(bloques, "Grupo", on_celda_click, puede_editar)


__all__ = ["render_parrilla", "render_tablero_maestro"]
