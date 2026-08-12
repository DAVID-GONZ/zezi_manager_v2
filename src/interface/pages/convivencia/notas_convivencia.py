"""
src/interface/pages/convivencia/notas_convivencia.py
====================================================
Notas de comportamiento por periodo — ZECI Manager v2.0.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Los DTOs se acceden a través del módulo de servicios.
  Solo usa Container (servicios) e imports de la capa de interfaz.

Patrón de selector (igual que observaciones / planilla_notas):
  El inline_periodo_grupo_asignatura va FUERA del @ui.refreshable.
  on_sel_change actualiza _s y llama panel_grid.refresh().
  El refreshable nunca re-renderiza el selector.

Flujo:
  1. Guard de autenticación -> redirige a /login si no hay sesión.
  2. inline_periodo_grupo_asignatura pre-selecciona periodo, grupo y asignatura.
  3. on_sel_change carga estudiantes del grupo y sus notas.
  4. panel_grid renderiza ag-Grid de estudiantes con selección múltiple (checkbox),
     columnas editables de nota y observación de boletín.
  5. Periodo cerrado -> editable: false y botones de guardado ocultos.

Refreshables:
  panel_grid() — grilla de estudiantes con notas editables.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    empty_state,
    toast_error,
    toast_info,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_ghost, btn_primary
from src.interface.design.components.inline_selectors import inline_periodo_grupo_asignatura
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.services.convivencia_service import NuevaNotaComportamientoDTO

logger = logging.getLogger("NOTAS_CONVIVENCIA")

# Aviso de autorización por objeto (convivencia_04). Mismo texto que comportamiento.
_MSG_NO_AUTORIZADO = (
    "Solo el director de grupo, la coordinación o la dirección pueden "
    "gestionar el comportamiento de este grupo."
)


def _autorizado_para_grupo(ctx: SessionContext, grupo_id: int | None) -> bool:
    """Autorización por objeto: puede el usuario gestionar las notas de
    comportamiento del grupo activo? Delega en CatalogoAcademicoService
    (directivo siempre; profesor solo si dirige el grupo; admin False). Pasa
    primitivos; la página no importa dominio. Sin grupo -> False."""
    if not grupo_id:
        return False
    try:
        return Container.catalogo_academico_service().puede_gestionar_comportamiento_en_grupo(
            ctx.usuario_rol, ctx.usuario_id, int(grupo_id)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo resolver autorización de notas: %s", exc)
        return False


# -- Estado --------------------------------------------------------------------

def _estado_inicial() -> dict:
    return {
        "estudiantes":           [],
        "periodos":              [],
        "notas":                 [],
        "sel_estudiante_ids":    [],
        "sel_periodo_id":        None,
        "sel_grupo_id":          None,
        "sel_grupo_nombre":      "",
        "sel_asignacion_id":     None,
        "sel_asignacion_nombre": "",
        "periodo_cerrado":       False,
        "cambios_pendientes":    {},
    }


def _cargar_periodos(_s: dict) -> None:
    try:
        config = Container.configuracion_service().get_activa()
        anio_id = getattr(config, "id", None) if config else None
        if anio_id:
            _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id)
        else:
            _s["periodos"] = []
    except Exception as exc:
        logger.warning("Error cargando periodos: %s", exc)
        _s["periodos"] = []


def _verificar_periodo(_s: dict) -> None:
    """Verifica si el periodo está cerrado."""
    periodo_id = _s["sel_periodo_id"]
    if not periodo_id:
        _s["periodo_cerrado"] = False
        return
    try:
        periodo = Container.periodo_service().get_by_id(int(periodo_id))
        _s["periodo_cerrado"] = bool(getattr(periodo, "cerrado", False))
    except Exception as exc:
        logger.warning("No se pudo verificar cierre del periodo: %s", exc)
        _s["periodo_cerrado"] = False


def _cargar_notas(_s: dict) -> None:
    """Carga las notas de comportamiento del grupo y periodo activos."""
    grupo_id = _s["sel_grupo_id"]
    periodo_id = _s["sel_periodo_id"]
    if not grupo_id or not periodo_id:
        _s["notas"] = []
        return
    try:
        _s["notas"] = Container.convivencia_service().listar_notas_grupo(
            int(grupo_id), int(periodo_id)
        )
    except Exception as exc:
        logger.error("Error cargando notas: %s", exc)
        _s["notas"] = []


# -- Helpers -------------------------------------------------------------------

def _construir_filas_grid(_s: dict) -> list[dict]:
    """Combina estudiantes con sus notas de comportamiento."""
    notas_por_est = {getattr(n, "estudiante_id", None): n for n in _s["notas"]}

    filas = []
    for est in _s["estudiantes"]:
        est_id = getattr(est, "id", None)
        nombre = f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
        nota_obj = notas_por_est.get(est_id)
        cambio = _s["cambios_pendientes"].get(est_id, {})
        valor = cambio.get("valor", getattr(nota_obj, "valor", None) if nota_obj else None)
        observacion = cambio.get(
            "observacion", getattr(nota_obj, "observacion", "") if nota_obj else ""
        )
        filas.append({
            "estudiante_id":       est_id,
            "nombre_completo":     nombre,
            "nota":                valor if valor is not None else "",
            "observacion_boletin": observacion or "",
        })
    return filas


# -- Página --------------------------------------------------------------------

# page-delegate: ruta y guard de rol registrados en main.py
def notas_convivencia_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _cargar_periodos(_s)
    _refs: dict = {}

    def _actualizar_datos_en_sitio() -> None:
        """Recarga notas y actualiza el grid sin destruir la selección."""
        _cargar_notas(_s)
        grid = _refs.get("grid")
        if grid:
            grid.options["rowData"] = _construir_filas_grid(_s)
            grid.update()

    # -- Handlers para notas ---------------------------------------------------

    def on_cell_value_changed(e) -> None:
        """Captura cambios de celdas en la grilla y actualiza cambios_pendientes."""
        try:
            data = e.args
            if isinstance(data, dict):
                est_id = data.get("estudiante_id") or data.get("data", {}).get("estudiante_id")
                campo = data.get("colId") or data.get("column", {}).get("colId")
                nuevo_val = data.get("newValue")
                if est_id is not None:
                    if est_id not in _s["cambios_pendientes"]:
                        _s["cambios_pendientes"][est_id] = {}
                    if campo == "nota":
                        _s["cambios_pendientes"][est_id]["valor"] = nuevo_val
                    elif campo == "observacion_boletin":
                        _s["cambios_pendientes"][est_id]["observacion"] = nuevo_val
        except Exception as exc:
            logger.warning("Error procesando cellValueChanged: %s", exc)

    def _guardar_nota_estudiante(est_id, valor, observacion) -> None:
        """Guarda la nota de un estudiante individual."""
        if _s["periodo_cerrado"]:
            toast_error("El periodo está cerrado.")
            return
        if not _s["sel_grupo_id"] or not _s["sel_periodo_id"]:
            toast_warning("Selecciona un grupo y periodo.")
            return
        try:
            valor_float = float(valor) if valor not in (None, "", "--") else None
        except (TypeError, ValueError):
            toast_warning("El valor debe ser un número.")
            return
        if valor_float is None:
            toast_warning("Ingresa un valor de nota.")
            return
        try:
            dto = NuevaNotaComportamientoDTO(
                estudiante_id=est_id,
                grupo_id=int(_s["sel_grupo_id"]),
                periodo_id=int(_s["sel_periodo_id"]),
                valor=valor_float,
                observacion=observacion if observacion else None,
            )
            Container.convivencia_service().registrar_nota_comportamiento(
                dto, ctx.usuario_id, usuario_rol=ctx.usuario_rol,
            )
            _s["cambios_pendientes"].pop(est_id, None)
            toast_success("Nota guardada.")
            _cargar_notas(_s)
        except ValueError as exc:
            toast_warning(f"Error de validación: {exc}")
        except Exception as exc:
            logger.error("Error guardando nota: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")

    def _guardar_seleccionado() -> None:
        grid = _refs.get("grid")
        if grid is None:
            toast_warning("No hay grilla disponible.")
            return

        async def _do_guardar():
            rows = await grid.get_selected_rows()
            if not rows:
                toast_warning("Selecciona al menos una fila.")
                return
            for fila in rows:
                est_id = fila.get("estudiante_id")
                if est_id is None:
                    continue
                cambio = _s["cambios_pendientes"].get(est_id, {})
                valor = cambio.get("valor", fila.get("nota"))
                observacion = cambio.get("observacion", fila.get("observacion_boletin", ""))
                _guardar_nota_estudiante(est_id, valor, str(observacion))
            grid_ref = _refs.get("grid")
            if grid_ref:
                grid_ref.options["rowData"] = _construir_filas_grid(_s)
                grid_ref.update()

        ui.timer(0, _do_guardar, once=True)

    def _guardar_todo() -> None:
        """Guarda todos los cambios pendientes."""
        if _s["periodo_cerrado"]:
            toast_error("El periodo está cerrado.")
            return
        if not _s["cambios_pendientes"]:
            toast_info("Sin cambios pendientes.")
            return
        exitos = 0
        errores = 0
        for est_id, cambio in list(_s["cambios_pendientes"].items()):
            try:
                dto = NuevaNotaComportamientoDTO(
                    estudiante_id=est_id,
                    grupo_id=int(_s["sel_grupo_id"]),
                    periodo_id=int(_s["sel_periodo_id"]),
                    valor=float(cambio["valor"]),
                    observacion=cambio.get("observacion") or None,
                )
                Container.convivencia_service().registrar_nota_comportamiento(
                    dto, ctx.usuario_id, usuario_rol=ctx.usuario_rol,
                )
                _s["cambios_pendientes"].pop(est_id, None)
                exitos += 1
            except Exception as exc:
                logger.error("Error guardando nota est=%s: %s", est_id, exc)
                errores += 1
        _cargar_notas(_s)
        grid = _refs.get("grid")
        if grid:
            grid.options["rowData"] = _construir_filas_grid(_s)
            grid.update()
        if errores == 0:
            toast_success(f"Se guardaron {exitos} nota(s) correctamente.")
        else:
            toast_warning(f"Guardadas: {exitos}. Errores: {errores}.")

    # -- Refreshable (patron sibling, selector FUERA) --------------------------

    @ui.refreshable
    def panel_grid() -> None:
        autorizado = _autorizado_para_grupo(ctx, _s["sel_grupo_id"])
        editable = (not _s["periodo_cerrado"]) and autorizado

        col_defs = [
            {
                "headerName":              "",
                "field":                   "check",
                "checkboxSelection":       True,
                "headerCheckboxSelection": True,
                "width":                   50,
                "sortable":                False,
                "filter":                  False,
            },
            {
                "headerName": "Estudiante",
                "field":      "nombre_completo",
                "flex":       1,
                "sortable":   True,
                "filter":     True,
                "pinned":     "left",
            },
            {
                "headerName": "Nota (0-100)",
                "field":      "nota",
                "width":      130,
                "editable":   editable,
                "type":       "numericColumn",
            },
            {
                "headerName": "Observación boletín",
                "field":      "observacion_boletin",
                "flex":       2,
                "editable":   editable,
            },
        ]
        grid_rows = _construir_filas_grid(_s)

        with ui.element("div").classes("panel-card"):
            if _s["periodo_cerrado"]:
                with ui.element("div").classes("alert alert--warning"):
                    ui.label("Periodo cerrado — solo lectura.")

            if _s["sel_grupo_id"] and not autorizado:
                with ui.element("div").classes("alert alert--warning"):
                    ui.label(_MSG_NO_AUTORIZADO)

            with ui.element("div").classes("panel-toolbar"):
                ui.element("div").classes("panel-toolbar-spacer")
                if editable:
                    btn_ghost(
                        "Guardar seleccionado",
                        on_click=_guardar_seleccionado,
                        size="sm",
                    )
                    btn_primary(
                        "Guardar todo",
                        on_click=_guardar_todo,
                        icon=Icons.SAVE,
                    )

            if not _s.get("sel_grupo_id"):
                empty_state(
                    icono="group",
                    titulo="Selecciona un grupo",
                    descripcion="Elige periodo, grupo y asignatura para ver los estudiantes.",
                )
            elif not grid_rows:
                empty_state(
                    icono="person_search",
                    titulo="Sin estudiantes",
                    descripcion="No hay estudiantes registrados en este grupo.",
                )
            else:
                with ui.element("div").classes("aggrid-vh"):
                    grid = ui.aggrid({
                        "columnDefs":  col_defs,
                        "rowData":     grid_rows,
                        "rowSelection": "multiple",
                        "defaultColDef": {"resizable": True},
                        "suppressCellFocus": False,
                        "stopEditingWhenCellsLoseFocus": True,
                    }).classes("w-full")
                _refs["grid"] = grid
                grid.on("cellValueChanged", on_cell_value_changed)

                async def on_grid_selection(_e, _grid=grid) -> None:
                    rows = await _grid.get_selected_rows()
                    _s["sel_estudiante_ids"] = [r["estudiante_id"] for r in rows]

                grid.on("selectionChanged", on_grid_selection)

    # -- Contenido principal (selector FUERA del refreshable) ------------------

    def contenido() -> None:
        def on_sel_change(s: dict) -> None:
            _s["sel_periodo_id"]        = s["sel_periodo_id"]
            _s["sel_grupo_id"]          = s["sel_grupo_id"]
            _s["sel_asignacion_id"]     = s["sel_asignacion_id"]
            _s["sel_asignacion_nombre"] = s.get("sel_asignacion_nombre", "")
            _s["sel_estudiante_ids"]    = []
            _s["cambios_pendientes"]    = {}
            _verificar_periodo(_s)
            if s["sel_grupo_id"]:
                try:
                    _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(
                        s["sel_grupo_id"]
                    )
                except Exception as exc:
                    logger.warning("Error cargando estudiantes: %s", exc)
                    _s["estudiantes"] = []
            else:
                _s["estudiantes"] = []
            _cargar_notas(_s)
            panel_grid.refresh()

        inline_periodo_grupo_asignatura(
            _s, on_sel_change,
            usuario_id=ctx.usuario_id,
            institucion_id=ctx.institucion_id,
            usuario_rol=ctx.usuario_rol,
            preselect_periodo=True,
        )

        with ui.element("div").classes("page-stack"):
            panel_grid()

    app_layout(ctx, contenido, page_titulo="Notas de convivencia")


__all__ = ["notas_convivencia_page"]
