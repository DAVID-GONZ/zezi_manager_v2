"""
src/interface/pages/convivencia/notas_convivencia.py
====================================================
Página de notas de comportamiento por periodo — ZECI Manager v2.0.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Solo usa Container (servicios) e imports de la capa de interfaz.

Flujo:
  1. Guard de autenticación → redirige a /login si no hay sesión.
  2. _cargar_estado() carga periodos y notas del grupo.
  3. Verifica si el periodo está cerrado → modo solo lectura en aggrid.
  4. aggrid con columnas Estudiante, Nota (editable), Observación (editable).
  5. cellValueChanged actualiza cambios_pendientes.
  6. "Guardar seleccionado" guarda la fila seleccionada.
  7. "Guardar todo" itera cambios_pendientes y guarda cada uno.
  8. Periodo cerrado → editable: false y botones ocultos.

Refreshables:
  _contenido() — re-renderiza todo el cuerpo de la página.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_ghost
from src.interface.design.theme import ThemeManager
from src.interface.design.components import (
    empty_state, toast_error, toast_info, toast_success, toast_warning,
)
from src.services.convivencia_service import NuevaNotaComportamientoDTO

logger = logging.getLogger("NOTAS_CONVIVENCIA")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "grupo_id":          None,
        "periodo_id":        None,
        "estudiantes":       [],    # list[Estudiante]
        "periodos":          [],    # list[Periodo]
        "notas":             [],    # list[NotaComportamiento]
        "periodo_cerrado":   False,
        "cambios_pendientes": {},   # {estudiante_id: {"valor": float, "observacion": str}}
    }


def _cargar_estado(ctx: SessionContext, _s: dict) -> None:
    """Carga periodos, estudiantes y notas del grupo activo."""
    # Prefiltros del contexto
    if ctx.grupo_id:
        _s["grupo_id"] = ctx.grupo_id
    if ctx.periodo_id:
        _s["periodo_id"] = ctx.periodo_id

    # Periodos del año activo
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

    # Verificar cierre del periodo
    _verificar_periodo(_s)

    # Estudiantes del grupo
    try:
        if _s["grupo_id"]:
            _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(_s["grupo_id"])
        else:
            _s["estudiantes"] = []
    except Exception as exc:
        logger.warning("Error cargando estudiantes: %s", exc)
        _s["estudiantes"] = []

    # Notas del grupo y periodo
    _cargar_notas(_s)


def _verificar_periodo(_s: dict) -> None:
    """Verifica si el periodo está cerrado."""
    periodo_id = _s["periodo_id"]
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
    grupo_id = _s["grupo_id"]
    periodo_id = _s["periodo_id"]

    if not grupo_id or not periodo_id:
        _s["notas"] = []
        return

    try:
        _s["notas"] = Container.convivencia_service().listar_notas_grupo(
            int(grupo_id), int(periodo_id)
        )
    except Exception as exc:
        logger.error("Error cargando notas de convivencia: %s", exc)
        _s["notas"] = []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nombre_estudiante(_s: dict, est_id: int | None) -> str:
    for est in _s["estudiantes"]:
        if getattr(est, "id", None) == est_id:
            return f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
    return str(est_id) if est_id else "—"


def _construir_filas(_s: dict) -> list[dict]:
    """Combina estudiantes con sus notas (None si no tiene nota aún)."""
    notas_por_est: dict[int, object] = {
        getattr(n, "estudiante_id", None): n for n in _s["notas"]
    }
    filas = []
    for est in _s["estudiantes"]:
        est_id = getattr(est, "id", None)
        nota = notas_por_est.get(est_id)
        cambio = _s["cambios_pendientes"].get(est_id, {})
        valor = cambio.get("valor", getattr(nota, "valor", None) if nota else None)
        observacion = cambio.get(
            "observacion", getattr(nota, "observacion", "") if nota else ""
        )
        filas.append({
            "estudiante_id": est_id,
            "estudiante":    _nombre_estudiante(_s, est_id),
            "nota":          valor if valor is not None else "",
            "observacion":   observacion or "",
        })
    return filas


def _nueva_nota_dto(datos: dict) -> object:
    """Construye NuevaNotaComportamientoDTO desde primitivos del formulario."""
    return NuevaNotaComportamientoDTO(**datos)


# ── Guardar ───────────────────────────────────────────────────────────────────

def _guardar_nota(
    _s: dict,
    ctx: SessionContext,
    estudiante_id: int,
    valor,
    observacion: str,
) -> None:
    """Guarda la nota de un estudiante individual."""
    if _s["periodo_cerrado"]:
        toast_error("El periodo está cerrado. No se pueden modificar notas.")
        return
    if not _s["grupo_id"] or not _s["periodo_id"]:
        toast_warning("Selecciona un grupo y periodo.")
        return

    try:
        valor_float = float(valor) if valor not in (None, "", "--") else None
    except (TypeError, ValueError):
        toast_warning("El valor de la nota debe ser un número.")
        return

    if valor_float is None:
        toast_warning("Ingresa un valor de nota.")
        return

    try:
        dto = _nueva_nota_dto({
            "estudiante_id": estudiante_id,
            "grupo_id":      int(_s["grupo_id"]),
            "periodo_id":    int(_s["periodo_id"]),
            "valor":         valor_float,
            "observacion":   observacion if observacion else None,
        })
        Container.convivencia_service().registrar_nota_comportamiento(dto, ctx.usuario_id)
        # Limpiar el cambio pendiente
        _s["cambios_pendientes"].pop(estudiante_id, None)
        toast_success("Nota guardada.")
        _cargar_notas(_s)
    except ValueError as exc:
        toast_warning(f"Error de validación: {exc}")
    except Exception as exc:
        logger.error("Error guardando nota: %s", exc, exc_info=True)
        toast_error(f"Error: {exc}")


def _guardar_todo(_s: dict, ctx: SessionContext) -> None:
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
            dto = _nueva_nota_dto({
                "estudiante_id": est_id,
                "grupo_id":      int(_s["grupo_id"]),
                "periodo_id":    int(_s["periodo_id"]),
                "valor":         float(cambio["valor"]),
                "observacion":   cambio.get("observacion") or None,
            })
            Container.convivencia_service().registrar_nota_comportamiento(dto, ctx.usuario_id)
            _s["cambios_pendientes"].pop(est_id, None)
            exitos += 1
        except Exception as exc:
            logger.error("Error guardando nota de estudiante %s: %s", est_id, exc)
            errores += 1

    _cargar_notas(_s)

    if errores == 0:
        toast_success(f"Se guardaron {exitos} nota(s) correctamente.")
    else:
        toast_warning(f"Guardadas: {exitos}. Errores: {errores}. Revisa el log para detalles.")


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/convivencia/notas")
def notas_convivencia_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _ROLES_VALIDOS = {"director", "coordinador", "profesor"}
    if ctx.usuario_rol not in _ROLES_VALIDOS:
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    _s = _estado_inicial()
    _cargar_estado(ctx, _s)
    _guardar_seleccionado_timer = ui.timer(0, lambda: None, active=False, once=True)

    # ── Handlers ───────────────────────────────────────────────────────────

    def on_context_change() -> None:
        nuevo_ctx = SessionContext.desde_storage()
        if nuevo_ctx:
            _s["cambios_pendientes"] = {}
            _cargar_estado(nuevo_ctx, _s)
        _contenido.refresh()

    def on_periodo_change(valor) -> None:
        _s["periodo_id"] = valor
        _s["cambios_pendientes"] = {}
        _verificar_periodo(_s)
        _cargar_notas(_s)
        _contenido.refresh()

    # ── Refreshable ────────────────────────────────────────────────────────

    @ui.refreshable
    def _contenido() -> None:
        ctx_actual = SessionContext.desde_storage() or ctx
        filas = _construir_filas(_s)
        editable = not _s["periodo_cerrado"]

        opciones_periodos = {
            getattr(p, "id", None): getattr(p, "nombre", f"Periodo {getattr(p, 'id', '')}")
            for p in _s["periodos"]
        }

        col_defs = [
            {
                "headerName": "Estudiante",
                "field":      "estudiante",
                "flex":       1,
                "sortable":   True,
                "editable":   False,
                "pinned":     "left",
            },
            {
                "headerName": "Nota (0–100)",
                "field":      "nota",
                "width":      130,
                "editable":   editable,
                "type":       "numericColumn",
            },
            {
                "headerName": "Observación",
                "field":      "observacion",
                "flex":       2,
                "editable":   editable,
            },
        ]

        grid_ref = {}  # almacena referencia al grid para get_selected_rows

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
                        elif campo == "observacion":
                            _s["cambios_pendientes"][est_id]["observacion"] = nuevo_val
            except Exception as exc:
                logger.warning("Error procesando cellValueChanged: %s", exc)

        def on_guardar_seleccionado() -> None:
            grid = grid_ref.get("grid")
            if grid is None:
                toast_warning("Selecciona una fila primero.")
                return

            async def _do_guardar():
                rows = await grid.get_selected_rows()
                if not rows:
                    toast_warning("Selecciona una fila primero.")
                    return
                fila = rows[0]
                est_id = fila.get("estudiante_id")
                if est_id is None:
                    toast_warning("No se pudo identificar el estudiante.")
                    return
                cambio = _s["cambios_pendientes"].get(est_id, {})
                valor = cambio.get("valor", fila.get("nota"))
                observacion = cambio.get("observacion", fila.get("observacion", ""))
                _guardar_nota(_s, ctx_actual, est_id, valor, str(observacion))
                _contenido.refresh()

            if _guardar_seleccionado_timer.active:
                _guardar_seleccionado_timer.cancel(with_current_invocation=False)
            _guardar_seleccionado_timer.callback = _do_guardar
            _guardar_seleccionado_timer.active = True

        def on_guardar_todo() -> None:
            _guardar_todo(_s, ctx_actual)
            _contenido.refresh()

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):
                # Periodo cerrado — banner
                if _s["periodo_cerrado"]:
                    with ui.element("div").classes("asis-banner-cerrado"):
                        ThemeManager.icono(Icons.CLOSE_PERIOD, size=16)
                        ui.label("Periodo cerrado — solo lectura.").classes("asis-banner-text")

                # Selector de periodo
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes("items-center gap-4 flex-wrap"):
                        ui.select(
                            options=opciones_periodos,
                            label="Periodo",
                            value=_s["periodo_id"],
                            on_change=lambda e: on_periodo_change(e.value),
                        ).classes("andes-input input-min-md").props("outlined dense")

                        if not _s["periodo_cerrado"]:
                            ui.element("div").classes("flex-1")
                            btn_ghost(
                                "Guardar seleccionado",
                                on_click=on_guardar_seleccionado,
                                size="sm",
                            )
                            btn_primary(
                                "Guardar todo",
                                on_click=on_guardar_todo,
                                icon=Icons.SAVE,
                            )

                # Grilla de notas
                with ui.element("div").classes("panel-card"):
                    if not filas:
                        empty_state(
                            titulo="Sin estudiantes",
                            descripcion="No hay estudiantes en el grupo o no hay periodo seleccionado.",
                        )
                    else:
                        grid = ui.aggrid({
                            "columnDefs":        col_defs,
                            "rowData":           filas,
                            "defaultColDef":     {"resizable": True},
                            "rowSelection":      "single",
                            "suppressCellFocus": False,
                            "stopEditingWhenCellsLoseFocus": True,
                        }).classes("w-full").on("cellValueChanged", on_cell_value_changed)

                        grid_ref["grid"] = grid

        app_layout(
            ctx_actual, contenido_pagina,
            page_titulo="Notas de convivencia",
            on_context_change=on_context_change,
        )

    _contenido()


__all__ = ["notas_convivencia_page"]
