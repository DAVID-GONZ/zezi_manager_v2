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
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_primary
from src.interface.design.components.inline_selectors import (
    inline_periodo_grupo_asignatura,
)
from src.interface.design.components.status_badge import status_badge
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.interface.pages.convivencia._shared_observacion_form import (
    abrir_crear_observacion_dialog,
)
from src.services.convivencia_service import (
    FiltroConvivenciaDTO,
    NuevaNotaComportamientoDTO,
)

logger = logging.getLogger("NOTAS_CONVIVENCIA")

# Aviso de autorización por objeto (convivencia_04). Mismo texto que comportamiento.
_MSG_NO_AUTORIZADO = (
    "Solo el director de grupo, la coordinación o la dirección pueden "
    "gestionar el comportamiento de este grupo."
)

# Strings de tipo para RegistroComportamiento (sin importar TipoRegistro del dominio)
_TIPOS_DISPLAY: dict[str, str] = {
    "fortaleza": "Fortaleza",
    "dificultad": "Dificultad",
    "compromiso": "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo": "Descargo",
}

# Variantes de badge por tipo de registro (clases convivencia del design system)
_TIPO_BADGE_VARIANTE: dict[str, str] = {
    "fortaleza": "fortaleza",
    "dificultad": "dificultad",
    "compromiso": "compromiso",
    "citacion_acudiente": "citacion",
    "descargo": "descargo",
}


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
    except Exception as exc:
        logger.warning("No se pudo resolver autorización de notas: %s", exc)
        return False


# -- Estado --------------------------------------------------------------------


def _estado_inicial() -> dict:
    return {
        "estudiantes": [],
        "periodos": [],
        "notas": [],
        "sel_estudiante_ids": [],
        "sel_estudiante_id": None,  # único seleccionado; None si 0 o >1
        "observaciones_estudiante": [],
        "registros_estudiante": [],
        "asignaciones_grupo": [],
        "sel_periodo_id": None,
        "sel_grupo_id": None,
        "sel_grupo_nombre": "",
        "sel_asignacion_id": None,
        "sel_asignacion_nombre": "",
        "periodo_cerrado": False,
        "cambios_pendientes": {},
        "nota_min_escala": 0.0,
        "nota_max_escala": 100.0,
    }


def _cargar_periodos(_s: dict) -> None:
    try:
        config = Container.configuracion_service().get_activa()
        anio_id = getattr(config, "id", None) if config else None
        if anio_id:
            _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id)
        else:
            _s["periodos"] = []
        _s["nota_min_escala"] = getattr(config, "nota_minima_escala", 0.0) if config else 0.0
        _s["nota_max_escala"] = getattr(config, "nota_maxima_escala", 100.0) if config else 100.0
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


def _cargar_asignaciones_grupo(_s: dict) -> None:
    """Carga las asignaciones del grupo activo; usado para el dropdown de asignatura."""
    grupo_id = _s["sel_grupo_id"]
    if not grupo_id:
        _s["asignaciones_grupo"] = []
        return
    try:
        _s["asignaciones_grupo"] = Container.asignacion_service().listar_por_grupo(int(grupo_id))
    except Exception as exc:
        logger.warning("Error cargando asignaciones del grupo: %s", exc)
        _s["asignaciones_grupo"] = []


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
        filas.append(
            {
                "estudiante_id": est_id,
                "nombre_completo": nombre,
                "nota": valor,  # None = celda vacía; "" rompe numericColumn
                "observacion_boletin": observacion or "",
            }
        )
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

    # -- Handlers para notas ---------------------------------------------------

    def on_cell_value_changed(e) -> None:
        """Guarda nota u observación inmediatamente al salir de la celda (on_change)."""
        try:
            data = e.args
            if not isinstance(data, dict):
                return
            row = data.get("data", {})
            est_id = row.get("estudiante_id")
            campo = data.get("colId") or data.get("column", {}).get("colId")
            nuevo_val = data.get("newValue")
            if est_id is None:
                return

            if campo == "nota":
                # Guarda nota + observacion actual de la fila
                observacion = row.get("observacion_boletin") or ""
                _guardar_nota_estudiante(est_id, nuevo_val, str(observacion))

            elif campo == "observacion_boletin":
                # Guarda observacion + nota actual de la fila; si no hay nota, pendiente
                valor_actual = row.get("nota")
                if valor_actual is not None and valor_actual != "":
                    _guardar_nota_estudiante(
                        est_id, valor_actual, str(nuevo_val) if nuevo_val else ""
                    )
                else:
                    _s["cambios_pendientes"].setdefault(est_id, {})
                    _s["cambios_pendientes"][est_id]["observacion"] = nuevo_val

        except Exception as exc:
            logger.warning("Error en cellValueChanged: %s", exc)

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
                dto,
                ctx.usuario_id,
                usuario_rol=ctx.usuario_rol,
            )
            _s["cambios_pendientes"].pop(est_id, None)
            toast_success("Nota guardada.")
            _cargar_notas(_s)
        except ValueError as exc:
            toast_warning(f"Error de validación: {exc}")
        except Exception as exc:
            logger.error("Error guardando nota: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")

    # -- Helpers de convivencia del estudiante ----------------------------------

    def _cargar_convivencia_estudiante(_s: dict) -> None:
        """Carga observaciones y registros de comportamiento del estudiante activo."""
        est_id = _s["sel_estudiante_id"]
        periodo_id = _s["sel_periodo_id"]
        if not est_id or not periodo_id:
            _s["observaciones_estudiante"] = []
            _s["registros_estudiante"] = []
            return
        svc = Container.convivencia_service()
        try:
            _s["observaciones_estudiante"] = svc.listar_observaciones(
                int(est_id),
                int(periodo_id),
                usuario_id=ctx.usuario_id,
                usuario_rol=ctx.usuario_rol,
            )
        except Exception as exc:
            logger.error("Error cargando observaciones est=%s: %s", est_id, exc)
            _s["observaciones_estudiante"] = []
        try:
            _s["registros_estudiante"] = svc.listar_registros(
                FiltroConvivenciaDTO(
                    estudiante_id=int(est_id),
                    periodo_id=int(periodo_id),
                )
            )
        except Exception as exc:
            logger.error("Error cargando registros est=%s: %s", est_id, exc)
            _s["registros_estudiante"] = []

    def _abrir_crear_observacion_est() -> None:
        """Abre el diálogo express de creación de observación para el estudiante seleccionado."""
        est_id = _s["sel_estudiante_id"]
        if not est_id:
            toast_warning("Selecciona un estudiante en el grid.")
            return
        periodo_id = _s.get("sel_periodo_id")
        if not periodo_id:
            toast_warning("Selecciona un periodo.")
            return

        nombre = next(
            (
                f"{getattr(e, 'apellido', '')} {getattr(e, 'nombre', '')}".strip()
                for e in _s["estudiantes"]
                if getattr(e, "id", None) == est_id
            ),
            None,
        )

        def _on_exito(exitos: int, errores: int) -> None:
            _cargar_convivencia_estudiante(_s)
            panel_convivencia.refresh()

        abrir_crear_observacion_dialog(
            ctx=ctx,
            estudiante_ids=[int(est_id)],
            periodo_id=int(periodo_id),
            asignaciones=_s.get("asignaciones_grupo", []),
            on_success=_on_exito,
            nombre_unico=nombre,
        )

    # -- Refreshable: panel del estudiante seleccionado ------------------------

    @ui.refreshable
    def panel_convivencia() -> None:
        """
        Panel de dos sub-secciones para el estudiante seleccionado en el grid:
          1. Observaciones individuales (ObservacionPeriodo) — solo lectura.
          2. Historial de convivencia (RegistroComportamiento) — solo lectura.
        Con botón "Nueva observación" gated a selección única.
        """
        est_id = _s["sel_estudiante_id"]
        obs_list = _s["observaciones_estudiante"]
        reg_list = _s["registros_estudiante"]

        # Nombre legible del estudiante seleccionado
        nombre_est = ""
        if est_id:
            for est in _s["estudiantes"]:
                if getattr(est, "id", None) == est_id:
                    nombre_est = (
                        f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
                    )
                    break

        # Mapa de categorías para nombres de display
        try:
            cats = Container.convivencia_service().listar_categorias(solo_activas=True)
            opciones_cat = {getattr(c, "id", None): getattr(c, "nombre", "") for c in cats}
        except Exception:
            opciones_cat = {}

        # Sub-sección 1: Observaciones individuales
        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("panel-header"):
                titulo_obs = "Observaciones individuales"
                if nombre_est:
                    titulo_obs += f" — {nombre_est}"
                ui.label(titulo_obs).classes("panel-title")
                ui.element("div").classes("panel-toolbar-spacer")
                if est_id:
                    status_badge(str(len(obs_list)), variante="info")
                    btn_primary(
                        "Nueva observación",
                        on_click=_abrir_crear_observacion_est,
                        icon=Icons.ADD,
                        size="sm",
                    )
                else:
                    btn_primary(
                        "Nueva observación",
                        disabled=True,
                        icon=Icons.ADD,
                        size="sm",
                    )

            if not est_id:
                empty_state(
                    icono="person",
                    titulo="Selecciona un estudiante",
                    descripcion="Haz clic en una fila del grid para ver sus observaciones.",
                )
            elif not obs_list:
                empty_state(
                    icono="speaker_notes",
                    titulo="Sin observaciones",
                    descripcion="No hay observaciones registradas para este periodo.",
                )
            else:
                for obs in obs_list:
                    cat_id = getattr(obs, "categoria_id", None)
                    cat_nombre = opciones_cat.get(cat_id, "Sin categoría")
                    es_publica = getattr(obs, "es_publica", True)
                    fecha = getattr(obs, "fecha_registro", None)
                    fecha_str = str(fecha)[:10] if fecha is not None else ""
                    texto = getattr(obs, "texto", "")

                    with ui.element("div").classes("panel-card u-mt-sm"):
                        with ui.element("div").classes("form-row-between"):
                            ui.label(texto).classes("text-secondary")
                            if es_publica:
                                status_badge("Pública", variante="success")
                            else:
                                status_badge("Privada", variante="neutral")
                        with ui.element("div").classes("form-row-inline"):
                            status_badge(cat_nombre, variante="info")
                            if fecha_str:
                                ui.label(fecha_str).classes("text-secondary")

        # Sub-sección 2: Historial de convivencia
        with ui.element("div").classes("panel-card u-mt-sm"):
            with ui.element("div").classes("panel-header"):
                ui.label("Historial de convivencia").classes("panel-title")
                if est_id:
                    ui.element("div").classes("panel-toolbar-spacer")
                    status_badge(str(len(reg_list)), variante="neutral")

            if not est_id:
                empty_state(
                    icono="history",
                    titulo="Selecciona un estudiante",
                    descripcion="Haz clic en una fila del grid para ver el historial.",
                )
            elif not reg_list:
                empty_state(
                    icono="event_note",
                    titulo="Sin registros",
                    descripcion="No hay registros de comportamiento en este periodo.",
                )
            else:
                for reg in reg_list:
                    tipo_str = str(getattr(reg, "tipo", "")).replace("TipoRegistro.", "")
                    tipo_label = _TIPOS_DISPLAY.get(tipo_str, tipo_str.capitalize())
                    variante = _TIPO_BADGE_VARIANTE.get(tipo_str, "neutral")
                    fecha_reg = getattr(reg, "fecha", None)
                    fecha_str = str(fecha_reg) if fecha_reg is not None else ""
                    descripcion = getattr(reg, "descripcion", "")

                    with ui.element("div").classes("panel-card u-mt-sm"):
                        with ui.element("div").classes("form-row-inline"):
                            if fecha_str:
                                ui.label(fecha_str).classes("text-secondary")
                            status_badge(tipo_label, variante=variante)
                        ui.label(descripcion).classes("text-secondary")

    # -- Refreshable (patron sibling, selector FUERA) --------------------------

    @ui.refreshable
    def panel_grid() -> None:
        autorizado = _autorizado_para_grupo(ctx, _s["sel_grupo_id"])
        editable = (not _s["periodo_cerrado"]) and autorizado

        col_defs = [
            {
                "headerName": "",
                "field": "check",
                "checkboxSelection": True,
                "headerCheckboxSelection": True,
                "width": 50,
                "sortable": False,
                "filter": False,
            },
            {
                "headerName": "Estudiante",
                "field": "nombre_completo",
                "flex": 1,
                "sortable": True,
                "filter": True,
                "pinned": "left",
            },
            {
                "headerName": f"Nota ({_s['nota_min_escala']:g}–{_s['nota_max_escala']:g})",
                "field": "nota",
                "width": 130,
                "editable": editable,
                "type": "numericColumn",
            },
            {
                "headerName": "Observación General (Boletín)",
                "field": "observacion_boletin",
                "flex": 2,
                "editable": editable,
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

            if editable:
                with ui.element("div").classes("panel-toolbar"):
                    ui.element("div").classes("panel-toolbar-spacer")
                    ui.label("Las notas se guardan automáticamente al salir de la celda.").classes(
                        "text-secondary"
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
                    grid = ui.aggrid(
                        {
                            "columnDefs": col_defs,
                            "rowData": grid_rows,
                            "rowSelection": "multiple",
                            "defaultColDef": {"resizable": True},
                            "suppressCellFocus": False,
                            "stopEditingWhenCellsLoseFocus": True,
                            "pagination": True,
                            "paginationPageSize": 20,
                        }
                    ).classes("w-full")
                _refs["grid"] = grid
                grid.on("cellValueChanged", on_cell_value_changed)

                async def on_grid_selection(_e, _grid=grid) -> None:
                    rows = await _grid.get_selected_rows()
                    _s["sel_estudiante_ids"] = [r["estudiante_id"] for r in rows]
                    nuevo_id = rows[0]["estudiante_id"] if len(rows) == 1 else None
                    if nuevo_id != _s["sel_estudiante_id"]:
                        _s["sel_estudiante_id"] = nuevo_id
                        _cargar_convivencia_estudiante(_s)
                        panel_convivencia.refresh()

                grid.on("selectionChanged", on_grid_selection)

    # -- Contenido principal (selector FUERA del refreshable) ------------------

    def contenido() -> None:
        def on_sel_change(s: dict) -> None:
            _s["sel_periodo_id"] = s["sel_periodo_id"]
            _s["sel_grupo_id"] = s["sel_grupo_id"]
            _s["sel_asignacion_id"] = s["sel_asignacion_id"]
            _s["sel_asignacion_nombre"] = s.get("sel_asignacion_nombre", "")
            _s["sel_estudiante_ids"] = []
            _s["sel_estudiante_id"] = None
            _s["observaciones_estudiante"] = []
            _s["registros_estudiante"] = []
            _s["cambios_pendientes"] = {}
            _verificar_periodo(_s)
            if s["sel_grupo_id"]:
                try:
                    _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(
                        s["sel_grupo_id"]
                    )
                except Exception as exc:
                    logger.warning("Error cargando estudiantes: %s", exc)
                    _s["estudiantes"] = []
                _cargar_asignaciones_grupo(_s)
            else:
                _s["estudiantes"] = []
                _s["asignaciones_grupo"] = []
            _cargar_notas(_s)
            panel_grid.refresh()
            panel_convivencia.refresh()

        inline_periodo_grupo_asignatura(
            _s,
            on_sel_change,
            usuario_id=ctx.usuario_id,
            institucion_id=ctx.institucion_id,
            usuario_rol=ctx.usuario_rol,
            preselect_periodo=True,
        )

        with ui.element("div").classes("page-stack"):
            panel_grid()
            panel_convivencia()

    app_layout(ctx, contenido, page_titulo="Notas de convivencia")


__all__ = ["notas_convivencia_page"]
