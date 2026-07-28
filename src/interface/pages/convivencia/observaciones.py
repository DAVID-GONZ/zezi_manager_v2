"""
src/interface/pages/convivencia/observaciones.py
================================================
Página de observaciones de periodo — ZECI Manager v2.0.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Los DTOs se acceden a través del módulo de servicios.
  Solo usa Container (servicios) e imports de la capa de interfaz.

Flujo:
  1. Guard de autenticación → redirige a /login si no hay sesión.
  2. _cargar_estado() obtiene estudiantes del grupo y periodos.
  3. Selectores de estudiante y periodo filtran las observaciones.
  4. aggrid muestra observaciones: Estudiante, Texto, Visibilidad, Fecha.
  5. Botón "Nueva observación" abre form_dialog con campos primitivos.
  6. Toggle visibilidad: invierte es_publica vía registrar_observacion (upsert).
  7. Eliminar: confirm_dialog antes de llamar al servicio.

Refreshables:
  _contenido()  — re-renderiza todo el cuerpo de la página.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    confirm_dialog,
    empty_state,
    form_dialog,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_danger, btn_ghost, btn_primary, btn_secondary
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.services.convivencia_service import NuevaObservacionDTO

logger = logging.getLogger("OBSERVACIONES")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "estudiantes":       [],   # list[Estudiante]
        "periodos":          [],   # list[Periodo]
        "observaciones":     [],   # list[ObservacionPeriodo]
        "sel_estudiante_id": None,
        "sel_periodo_id":    None,
        "plantilla_id":      None, # ID de plantilla usada al crear (convivencia_12)
    }


def _cargar_estado(ctx: SessionContext, _s: dict) -> None:
    """Carga estudiantes del grupo y periodos activos desde los servicios."""
    # Estudiantes del grupo
    try:
        if ctx.grupo_id:
            _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(ctx.grupo_id)
        else:
            _s["estudiantes"] = []
    except Exception as exc:
        logger.error("Error cargando estudiantes: %s", exc)
        _s["estudiantes"] = []

    # Preselectar primer estudiante si no hay selección
    if _s["estudiantes"] and _s["sel_estudiante_id"] is None:
        _s["sel_estudiante_id"] = getattr(_s["estudiantes"][0], "id", None)

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

    # Preselectar periodo del contexto
    if ctx.periodo_id and _s["sel_periodo_id"] is None:
        _s["sel_periodo_id"] = ctx.periodo_id

    # Cargar observaciones iniciales
    _cargar_observaciones(_s, ctx)


def _cargar_observaciones(_s: dict, ctx: SessionContext) -> None:
    """Recarga observaciones según los filtros seleccionados."""
    est_id = _s["sel_estudiante_id"]
    periodo_id = _s["sel_periodo_id"]

    if not est_id:
        _s["observaciones"] = []
        return

    try:
        observaciones = Container.convivencia_service().listar_observaciones(
            estudiante_id=int(est_id),
            periodo_id=int(periodo_id) if periodo_id else None,
            solo_publicas=False,
            usuario_id=ctx.usuario_id,
            usuario_rol=ctx.usuario_rol,
        )
        _s["observaciones"] = observaciones
    except Exception as exc:
        logger.error("Error cargando observaciones: %s", exc)
        _s["observaciones"] = []


def _cargar_categorias() -> dict:
    """Carga las categorías activas de observación para el selector del formulario."""
    try:
        categorias = Container.convivencia_service().listar_categorias(solo_activas=True)
        return {
            getattr(c, "id", None): getattr(c, "nombre", "")
            for c in categorias
        }
    except Exception as exc:
        logger.warning("Error cargando categorías: %s", exc)
        return {}


def _cargar_plantillas(categoria_id: int | None = None, limite: int = 20) -> list:
    """Carga las plantillas sugeridas (más usadas), opcionalmente filtradas por categoría."""
    try:
        return Container.convivencia_service().listar_plantillas_sugeridas(
            categoria_id=categoria_id, limite=limite
        )
    except Exception as exc:
        logger.warning("Error cargando plantillas: %s", exc)
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nombre_estudiante(_s: dict, est_id: int | None) -> str:
    for est in _s["estudiantes"]:
        if getattr(est, "id", None) == est_id:
            return f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
    return "—"


def _texto_truncado(texto: str, max_chars: int = 80) -> str:
    if not texto:
        return ""
    return texto[:max_chars] + "..." if len(texto) > max_chars else texto


def _construir_filas(_s: dict) -> list[dict]:
    filas = []
    for obs in _s["observaciones"]:
        obs_id = getattr(obs, "id", None)
        est_id = getattr(obs, "estudiante_id", None)
        texto = getattr(obs, "texto", "")
        es_publica = getattr(obs, "es_publica", True)
        fecha = getattr(obs, "fecha_registro", None)
        fecha_str = ""
        if fecha is not None:
            try:
                fecha_str = str(fecha)[:10]
            except Exception:
                fecha_str = str(fecha)
        filas.append({
            "id":            obs_id,
            "estudiante_id": est_id,
            "asignacion_id": getattr(obs, "asignacion_id", None),
            "periodo_id":    getattr(obs, "periodo_id", None),
            "categoria_id":  getattr(obs, "categoria_id", None),
            "estudiante":    _nombre_estudiante(_s, est_id),
            "texto":         _texto_truncado(texto),
            "texto_completo": texto,
            "visibilidad":   "Pública" if es_publica else "Privada",
            "es_publica":    es_publica,
            "fecha":         fecha_str,
        })
    return filas


def _nueva_observacion_dto(datos: dict) -> object:
    """Construye NuevaObservacionDTO desde primitivos del formulario."""
    return NuevaObservacionDTO(**datos)


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def observaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _cargar_estado(ctx, _s)

    # ── Handlers ───────────────────────────────────────────────────────────

    def on_context_change() -> None:
        nuevo_ctx = SessionContext.desde_storage()
        if nuevo_ctx:
            _cargar_estado(nuevo_ctx, _s)
        _contenido.refresh()

    def on_estudiante_change(valor) -> None:
        _s["sel_estudiante_id"] = valor
        ctx_actual = SessionContext.desde_storage() or ctx
        _cargar_observaciones(_s, ctx_actual)
        _contenido.refresh()

    def on_periodo_change(valor) -> None:
        _s["sel_periodo_id"] = valor
        ctx_actual = SessionContext.desde_storage() or ctx
        _cargar_observaciones(_s, ctx_actual)
        _contenido.refresh()

    def _crear_observacion(datos: dict) -> bool | None:
        """Crea una observación con los datos del form_dialog."""
        ctx_actual = SessionContext.desde_storage() or ctx
        est_id = datos.get("estudiante_id")
        periodo_id = datos.get("periodo_id")
        texto = str(datos.get("texto", "")).strip()
        es_publica = bool(datos.get("es_publica", True))
        categoria_id = datos.get("categoria_id")

        if not texto:
            toast_warning("El texto de la observación es requerido.")
            return False
        if not est_id or not periodo_id:
            toast_warning("Selecciona un estudiante y periodo.")
            return False
        if not categoria_id:
            toast_warning("Selecciona una categoría para la observación.")
            return False
        if not ctx_actual.asignacion_id:
            toast_warning("Contexto incompleto: falta asignación académica.")
            return False

        try:
            dto = _nueva_observacion_dto({
                "estudiante_id": int(est_id),
                "asignacion_id": ctx_actual.asignacion_id,
                "periodo_id":    int(periodo_id),
                "texto":         texto,
                "categoria_id":  int(categoria_id),
                "es_publica":    es_publica,
            })
            svc = Container.convivencia_service()
            plantilla_id = _s.get("plantilla_id")
            if plantilla_id:
                svc.registrar_observacion_desde_plantilla(
                    dto, plantilla_id, ctx_actual.usuario_id, ctx_actual.usuario_rol
                )
                _s["plantilla_id"] = None
            else:
                svc.registrar_observacion(dto, ctx_actual.usuario_id, ctx_actual.usuario_rol)
            toast_success("Observación guardada.")
            _cargar_observaciones(_s, ctx_actual)
            _contenido.refresh()
            return None
        except PermissionError as exc:
            toast_warning(f"Sin permiso: {exc}")
            return False
        except ValueError as exc:
            toast_warning(f"Error de validación: {exc}")
            return False
        except Exception as exc:
            logger.error("Error creando observación: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _abrir_crear_observacion(
        texto_prefill: str = "",
        categoria_id_prefill: int | None = None,
    ) -> None:
        opciones_est = {
            getattr(e, "id", None): f"{getattr(e, 'apellido', '')} {getattr(e, 'nombre', '')}".strip()
            for e in _s["estudiantes"]
        }
        opciones_per = {
            getattr(p, "id", None): getattr(p, "nombre", f"Periodo {getattr(p, 'id', '')}")
            for p in _s["periodos"]
        }
        opciones_cat = _cargar_categorias()
        campos = [
            {
                "key":      "estudiante_id",
                "label":    "Estudiante",
                "tipo":     "select",
                "opciones": opciones_est,
                "valor":    _s["sel_estudiante_id"],
                "requerido": True,
            },
            {
                "key":      "periodo_id",
                "label":    "Periodo",
                "tipo":     "select",
                "opciones": opciones_per,
                "valor":    _s["sel_periodo_id"],
                "requerido": True,
            },
            {
                "key":      "categoria_id",
                "label":    "Categoría",
                "tipo":     "select",
                "opciones": opciones_cat,
                "valor":    categoria_id_prefill,
                "requerido": True,
            },
            {
                "key":         "texto",
                "label":       "Texto de la observación",
                "tipo":        "textarea",
                "placeholder": "Máximo 2000 caracteres...",
                "valor":       texto_prefill,
                "requerido":   True,
            },
            {
                "key":   "es_publica",
                "label": "¿Pública? (aparece en boletín)",
                "tipo":  "checkbox",
                "valor": True,
            },
        ]
        form_dialog(
            titulo="Nueva observación",
            campos=campos,
            on_submit=_crear_observacion,
            texto_submit="Guardar",
            max_width="max-w-lg",
        )

    def _abrir_selector_plantilla() -> None:
        """Abre el selector de plantillas (form_dialog) para pre-llenar el form de observación."""
        todas_plantillas = _cargar_plantillas(None)
        if not todas_plantillas:
            toast_warning("No hay plantillas disponibles.")
            return

        opciones_plt = {
            getattr(p, "id", None): getattr(p, "texto", "")
            for p in todas_plantillas
        }

        campos = [
            {
                "key":      "plantilla_id",
                "label":    "Seleccionar plantilla",
                "tipo":     "select",
                "opciones": opciones_plt,
                "requerido": True,
            },
        ]

        def _on_submit_plantilla(datos: dict) -> bool | None:
            plantilla_id = datos.get("plantilla_id")
            if not plantilla_id:
                toast_warning("Selecciona una plantilla.")
                return False
            plantilla = next(
                (p for p in todas_plantillas if getattr(p, "id", None) == plantilla_id),
                None,
            )
            if plantilla is None:
                toast_warning("Plantilla no encontrada.")
                return False
            _s["plantilla_id"] = getattr(plantilla, "id", None)
            _abrir_crear_observacion(
                texto_prefill=getattr(plantilla, "texto", ""),
                categoria_id_prefill=getattr(plantilla, "categoria_id", None),
            )
            return None

        form_dialog(
            titulo="Usar plantilla",
            campos=campos,
            on_submit=_on_submit_plantilla,
            texto_submit="Usar plantilla",
            max_width="max-w-lg",
        )

    def _toggle_visibilidad(obs_id: int, es_publica_actual: bool, fila: dict) -> None:
        """Invierte la visibilidad de una observación (upsert via registrar_observacion)."""
        ctx_actual = SessionContext.desde_storage() or ctx
        asignacion_id = fila.get("asignacion_id") or getattr(ctx_actual, "asignacion_id", None)
        categoria_id = fila.get("categoria_id")
        if categoria_id is None:
            toast_warning("Esta observación no tiene categoría asignada. Edítala primero.")
            return
        try:
            dto = _nueva_observacion_dto({
                "estudiante_id": int(fila["estudiante_id"]),
                "asignacion_id": asignacion_id,
                "periodo_id":    int(fila["periodo_id"]),
                "texto":         fila["texto_completo"],
                "categoria_id":  int(categoria_id),
                "es_publica":    not es_publica_actual,
            })
            Container.convivencia_service().registrar_observacion(dto, ctx_actual.usuario_id)
            toast_success("Visibilidad actualizada.")
            _cargar_observaciones(_s, ctx_actual)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error cambiando visibilidad: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")

    def _promover_a_plantilla(obs_id: int) -> None:
        """Promueve una observación a plantilla del catálogo (solo director/coordinador)."""
        def _ejecutar() -> None:
            ctx_actual = SessionContext.desde_storage() or ctx
            try:
                Container.convivencia_service().promover_observacion_a_plantilla(
                    obs_id,
                    usuario_id=ctx_actual.usuario_id,
                    usuario_rol=ctx_actual.usuario_rol,
                )
                toast_success("Observación guardada como plantilla.")
            except PermissionError as exc:
                toast_warning(f"Sin permiso: {exc}")
            except Exception as exc:
                logger.error("Error promoviendo observación %s: %s", obs_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Promover a plantilla",
            mensaje="¿Deseas guardar esta observación como plantilla del catálogo?",
            on_confirm=_ejecutar,
            variante="info",
        )

    def _eliminar_observacion(obs_id: int) -> None:
        def _ejecutar() -> None:
            ctx_actual = SessionContext.desde_storage() or ctx
            try:
                Container.convivencia_service().eliminar_observacion(obs_id)
                toast_success("Observación eliminada.")
                _cargar_observaciones(_s, ctx_actual)
                _contenido.refresh()
            except Exception as exc:
                logger.error("Error eliminando observación %s: %s", obs_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Eliminar observación",
            mensaje="¿Confirmas la eliminación de esta observación? Esta acción no se puede deshacer.",
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Refreshable ────────────────────────────────────────────────────────

    @ui.refreshable
    def _contenido() -> None:
        ctx_actual = SessionContext.desde_storage() or ctx
        opciones_est = {
            getattr(e, "id", None): f"{getattr(e, 'apellido', '')} {getattr(e, 'nombre', '')}".strip()
            for e in _s["estudiantes"]
        }
        opciones_per = {
            getattr(p, "id", None): getattr(p, "nombre", f"Periodo {getattr(p, 'id', '')}")
            for p in _s["periodos"]
        }
        filas = _construir_filas(_s)

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):
                # Barra de filtros y acción
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes("panel-toolbar"):
                        ui.select(
                            options=opciones_est,
                            label="Estudiante",
                            value=_s["sel_estudiante_id"],
                            on_change=lambda e: on_estudiante_change(e.value),
                        ).classes("andes-input input-min-lg").props("outlined dense")

                        ui.select(
                            options=opciones_per,
                            label="Periodo",
                            value=_s["sel_periodo_id"],
                            on_change=lambda e: on_periodo_change(e.value),
                        ).classes("andes-input input-min-sm").props("outlined dense")

                        ui.element("div").classes("panel-toolbar-spacer")
                        btn_ghost(
                            "Usar plantilla",
                            on_click=_abrir_selector_plantilla,
                            icon="description",
                        )
                        btn_primary(
                            "Nueva observación",
                            on_click=_abrir_crear_observacion,
                            icon=Icons.ADD,
                        )

                # Tabla de observaciones
                with ui.element("div").classes("panel-card"):
                    if not filas:
                        empty_state(
                            icono="sticky_note_2",
                            titulo="Sin observaciones",
                            descripcion="No hay observaciones para los filtros seleccionados.",
                            cta_label="Nueva observación",
                            cta_on_click=_abrir_crear_observacion,
                            cta_icono="add",
                        )
                    else:
                        col_defs = [
                            {"headerName": "Estudiante",  "field": "estudiante",  "flex": 1, "sortable": True},
                            {"headerName": "Texto",       "field": "texto",       "flex": 2},
                            {"headerName": "Visibilidad", "field": "visibilidad", "width": 120},
                            {"headerName": "Fecha",       "field": "fecha",       "width": 120, "sortable": True},
                        ]
                        ui.aggrid({
                            "columnDefs":        col_defs,
                            "rowData":           filas,
                            "defaultColDef":     {"resizable": True},
                            "suppressCellFocus": True,
                            "rowSelection":      "single",
                        }).classes("w-full")

                        # Acciones por fila (bajo la tabla aggrid)
                        with ui.element("div").classes("row-actions"):
                            for fila in filas:
                                with ui.row().classes("row-actions-item"):
                                    ui.label(fila["estudiante"]).classes("row-actions-name")
                                    ui.label(fila["texto"]).classes("row-actions-text")
                                    ui.label(fila["visibilidad"]).classes("row-actions-status")
                                    btn_ghost(
                                        "Hacer privada" if fila["es_publica"] else "Hacer pública",
                                        on_click=lambda f=fila: _toggle_visibilidad(
                                            f["id"], f["es_publica"], f
                                        ),
                                        size="sm",
                                    )
                                    if ctx_actual.usuario_rol in ("director", "coordinador"):
                                        btn_secondary(
                                            "Promover a plantilla",
                                            on_click=lambda oid=fila["id"]: _promover_a_plantilla(oid),
                                            icon="upload",
                                            size="sm",
                                        )
                                    btn_danger(
                                        "Eliminar",
                                        on_click=lambda oid=fila["id"]: _eliminar_observacion(oid),
                                        size="sm",
                                    )

        app_layout(
            ctx_actual, contenido_pagina,
            page_titulo="Observaciones",
            on_context_change=on_context_change,
        )

    _contenido()


__all__ = ["observaciones_page"]
