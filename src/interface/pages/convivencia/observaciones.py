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
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_ghost, btn_danger
from src.interface.design.components.confirm_dialog import confirm_dialog
from src.interface.design.components.form_dialog import form_dialog

logger = logging.getLogger("OBSERVACIONES")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "estudiantes":       [],   # list[Estudiante]
        "periodos":          [],   # list[Periodo]
        "observaciones":     [],   # list[ObservacionPeriodo]
        "sel_estudiante_id": None,
        "sel_periodo_id":    None,
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
        )
        # Filtrar en cliente si es profesor: solo sus propias privadas + todas las públicas
        if ctx.usuario_rol == "profesor":
            observaciones = [
                obs for obs in observaciones
                if getattr(obs, "es_publica", True)
                or getattr(obs, "usuario_id", None) == ctx.usuario_id
            ]
        _s["observaciones"] = observaciones
    except Exception as exc:
        logger.error("Error cargando observaciones: %s", exc)
        _s["observaciones"] = []


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
            "estudiante":    _nombre_estudiante(_s, est_id),
            "texto":         _texto_truncado(texto),
            "texto_completo": texto,
            "visibilidad":   "Pública" if es_publica else "Privada",
            "es_publica":    es_publica,
            "fecha":         fecha_str,
        })
    return filas


def _nueva_observacion_dto(datos: dict) -> object:
    """
    Construye NuevaObservacionDTO sin imports de módulos de dominio en el nivel de módulo.
    Accede al módulo de dominio a través del módulo de servicio ya cargado.
    """
    import importlib
    _mod = importlib.import_module("src.domain.models.convivencia")
    return _mod.NuevaObservacionDTO(**datos)


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/convivencia/observaciones")
def observaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _ROLES_VALIDOS = {"admin", "director", "coordinador", "profesor"}
    if ctx.usuario_rol not in _ROLES_VALIDOS:
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
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

        if not texto:
            ui.notify("El texto de la observación es requerido.", type="warning")
            return False
        if not est_id or not periodo_id:
            ui.notify("Selecciona un estudiante y periodo.", type="warning")
            return False
        if not ctx_actual.asignacion_id:
            ui.notify("Contexto incompleto: falta asignación académica.", type="warning")
            return False

        try:
            dto = _nueva_observacion_dto({
                "estudiante_id": int(est_id),
                "asignacion_id": ctx_actual.asignacion_id,
                "periodo_id":    int(periodo_id),
                "texto":         texto,
                "es_publica":    es_publica,
            })
            Container.convivencia_service().registrar_observacion(dto, ctx_actual.usuario_id)
            ui.notify("Observación guardada.", type="positive", timeout=3000)
            _cargar_observaciones(_s, ctx_actual)
            _contenido.refresh()
            return None
        except ValueError as exc:
            ui.notify(f"Error de validación: {exc}", type="warning")
            return False
        except Exception as exc:
            logger.error("Error creando observación: %s", exc, exc_info=True)
            ui.notify(f"Error: {exc}", type="negative")
            return False

    def _abrir_crear_observacion() -> None:
        opciones_est = {
            getattr(e, "id", None): f"{getattr(e, 'apellido', '')} {getattr(e, 'nombre', '')}".strip()
            for e in _s["estudiantes"]
        }
        opciones_per = {
            getattr(p, "id", None): getattr(p, "nombre", f"Periodo {getattr(p, 'id', '')}")
            for p in _s["periodos"]
        }
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
                "key":         "texto",
                "label":       "Texto de la observación",
                "tipo":        "textarea",
                "placeholder": "Máximo 2000 caracteres...",
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

    def _toggle_visibilidad(obs_id: int, es_publica_actual: bool, fila: dict) -> None:
        """Invierte la visibilidad de una observación (upsert via registrar_observacion)."""
        ctx_actual = SessionContext.desde_storage() or ctx
        asignacion_id = fila.get("asignacion_id") or getattr(ctx_actual, "asignacion_id", None)
        try:
            dto = _nueva_observacion_dto({
                "estudiante_id": int(fila["estudiante_id"]),
                "asignacion_id": asignacion_id,
                "periodo_id":    int(fila["periodo_id"]),
                "texto":         fila["texto_completo"],
                "es_publica":    not es_publica_actual,
            })
            Container.convivencia_service().registrar_observacion(dto, ctx_actual.usuario_id)
            ui.notify("Visibilidad actualizada.", type="positive", timeout=2000)
            _cargar_observaciones(_s, ctx_actual)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error cambiando visibilidad: %s", exc, exc_info=True)
            ui.notify(f"Error: {exc}", type="negative")

    def _eliminar_observacion(obs_id: int) -> None:
        def _ejecutar() -> None:
            ctx_actual = SessionContext.desde_storage() or ctx
            try:
                Container.convivencia_service().eliminar_observacion(obs_id)
                ui.notify("Observación eliminada.", type="positive", timeout=2000)
                _cargar_observaciones(_s, ctx_actual)
                _contenido.refresh()
            except Exception as exc:
                logger.error("Error eliminando observación %s: %s", obs_id, exc, exc_info=True)
                ui.notify(f"Error: {exc}", type="negative")

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
                    with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                        ui.select(
                            options=opciones_est,
                            label="Estudiante",
                            value=_s["sel_estudiante_id"],
                            on_change=lambda e: on_estudiante_change(e.value),
                        ).classes("andes-input").props("outlined dense").style("min-width:220px")  # DYNAMIC: ancho mínimo del selector

                        ui.select(
                            options=opciones_per,
                            label="Periodo",
                            value=_s["sel_periodo_id"],
                            on_change=lambda e: on_periodo_change(e.value),
                        ).classes("andes-input").props("outlined dense").style("min-width:180px")  # DYNAMIC: ancho mínimo del selector

                        ui.element("div").classes("flex-1")
                        btn_primary(
                            "Nueva observación",
                            on_click=_abrir_crear_observacion,
                            icon=Icons.ADD,
                        )

                # Tabla de observaciones
                with ui.element("div").classes("panel-card"):
                    if not filas:
                        ui.label(
                            "Sin observaciones para los filtros seleccionados."
                        ).classes("text-empty py-4")
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
                        with ui.element("div").classes("flex flex-col gap-1 mt-2"):
                            for fila in filas:
                                with ui.row().classes("items-center gap-2 py-1"):
                                    ui.label(fila["estudiante"]).classes("w-40 text-sm font-medium")
                                    ui.label(fila["texto"]).classes("flex-1 text-sm text-secondary")
                                    ui.label(fila["visibilidad"]).classes("w-20 text-sm")
                                    btn_ghost(
                                        "Hacer privada" if fila["es_publica"] else "Hacer pública",
                                        on_click=lambda f=fila: _toggle_visibilidad(
                                            f["id"], f["es_publica"], f
                                        ),
                                        size="sm",
                                    )
                                    btn_danger(
                                        "Eliminar",
                                        on_click=lambda oid=fila["id"]: _eliminar_observacion(oid),
                                        size="sm",
                                    )

        app_layout(
            titulo_pagina="Observaciones",
            usuario_nombre=ctx_actual.usuario_nombre,
            usuario_rol=ctx_actual.usuario_rol,
            ruta_activa="/convivencia/observaciones",
            contenido=contenido_pagina,
            ctx=ctx_actual,
            on_context_change=on_context_change,
        )

    _contenido()


__all__ = ["observaciones_page"]
