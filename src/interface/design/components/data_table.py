"""
data_table.py — Tabla de datos con búsqueda y paginación del design system.

Ajustes NiceGUI 3.x:
  - ui.table() usa argumentos únicamente por keyword (columns=, rows=, etc.)
  - Filtrado via tabla.bind_filter_from(search_input, 'value') en vez de
    slots Vue (que NiceGUI 3.x ya no expone de la misma forma).
  - on_row_click se conecta via tabla.on('row-click', handler).
  - El evento 'row-click' de NiceGUI pasa e.args como [evt, row, index];
    la fila se obtiene en e.args[1].
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui


def data_table(
    columnas: list[dict],
    filas: list[dict],
    titulo: str = "",
    buscable: bool = True,
    paginado: bool = True,
    filas_por_pagina: int = 15,
    on_row_click: Callable[[dict], None] | None = None,
) -> ui.table:
    """
    Tabla de datos estilizada con búsqueda global y paginación opcionales.

    Args:
        columnas:        Lista de dicts de columna al estilo NiceGUI/Quasar:
                         [{"name": "id", "label": "ID", "field": "id", "sortable": True}, ...]
        filas:           Lista de dicts con los datos. Cada clave debe coincidir
                         con el "field" de la columna correspondiente.
        titulo:          Título opcional mostrado sobre la tabla con búsqueda.
        buscable:        Si True, muestra un campo de búsqueda global.
        paginado:        Si True, activa la paginación en la tabla.
        filas_por_pagina: Número de filas por página cuando paginado=True.
        on_row_click:    Callback opcional llamado al hacer click en una fila.
                         Recibe el dict de la fila como único argumento.

    Returns:
        El elemento ui.table creado, por si se necesita acceso posterior.

    Ejemplo:
        columnas = [
            {"name": "nombre", "label": "Nombre", "field": "nombre", "sortable": True},
            {"name": "grado",  "label": "Grado",  "field": "grado"},
        ]
        filas = [{"nombre": "Ana García", "grado": "10A"}]
        data_table(columnas, filas, titulo="Estudiantes", on_row_click=ver_detalle)

    Nota sobre columnas con renders personalizados (badges, botones):
        Para renderizado personalizado por celda, usa el slot 'body-cell-{name}'
        de NiceGUI/Quasar directamente sobre el objeto tabla retornado.
    """
    with ui.column().classes("gap-3").style("width:100%"):

        # Cabecera: título + buscador
        if titulo or buscable:
            with ui.row().classes("items-center justify-between").style("width:100%"):
                if titulo:
                    ui.label(titulo).classes("font-h3").style(
                        "color:var(--color-text-primary);"
                    )
                else:
                    ui.element("div")  # spacer

                if buscable:
                    search = (
                        ui.input(placeholder="Buscar…")
                        .props('dense outlined clearable')
                        .classes("andes-input")
                        .style("max-width:280px;")
                    )
                else:
                    search = None
        else:
            search = None

        # Construcción de la tabla
        table_kwargs: dict = dict(
            columns=columnas,
            rows=filas,
            row_key="id" if any(c.get("field") == "id" for c in columnas) else columnas[0]["field"],
        )
        if paginado:
            table_kwargs["pagination"] = filas_por_pagina

        tabla = ui.table(**table_kwargs).classes("andes-table").style("width:100%;")

        # Vincular búsqueda al filtro interno de la tabla
        if search is not None:
            tabla.bind_filter_from(search, "value")

        # Cursor pointer + handler de click por fila
        if on_row_click is not None:
            tabla.style("cursor:pointer;")

            def _handle_row_click(e) -> None:
                # e.args en NiceGUI 3.x: [MouseEvent, row_dict, row_index]
                try:
                    fila = e.args[1]
                except (IndexError, TypeError):
                    return
                on_row_click(fila)

            tabla.on("row-click", _handle_row_click)

    return tabla


__all__ = ["data_table"]
