"""
src/interface/pages/convivencia/seguimiento.py
==============================================
Página de alertas de seguimiento — ZECI Manager v2.0.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Solo usa Container (servicios) e imports de la capa de interfaz.

Flujo:
  1. Guard: solo director/coordinador tienen acceso a crear alertas;
     director_de_grupo puede consultar las recibidas. Otros → /inicio.
  2. _cargar_estado() carga estudiantes del grupo y docentes disponibles.
  3. Sección "Crear alerta de seguimiento" visible solo para
     director / coordinador: selector estudiante, selector profesor
     destinatario, descripción, nivel, botón "Enviar alerta".
  4. Sección "Alertas enviadas" muestra alertas SEGUIMIENTO_REQUERIDO
     del estudiante seleccionado.

Refreshables:
  _contenido() — re-renderiza todo el cuerpo de la página.
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
    stat_card,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_ghost, btn_primary
from src.interface.design.components.inline_selectors import inline_periodo_grupo_asignatura
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.services.convivencia_service import NuevaAlertaSeguimientoDTO

logger = logging.getLogger("SEGUIMIENTO")

_ROLES_CREAR = ("director", "coordinador")
_ROLES_VER   = ("director", "coordinador", "director_de_grupo")

_NIVEL_DISPLAY: dict[str, str] = {
    "advertencia": "Advertencia",
    "critica":     "Crítica",
    "info":        "Información",
}


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "estudiantes":       [],   # list[Estudiante]
        "docentes":          [],   # list[DocenteInfo] o similar
        "alertas":           [],   # list[Alerta]
        "periodos":          [],   # list[Periodo] — ya no se carga aquí, conservado por compatibilidad
        "sel_estudiante_id": None,
        "sel_periodo_id":    None,
        "sel_grupo_id":          None,
        "sel_grupo_nombre":      "",
        "sel_asignacion_id":     None,
        "sel_asignacion_nombre": "",
        "resultado_360":     None, # Seguimiento360DTO | None
    }


def _cargar_estado(ctx: SessionContext, _s: dict) -> None:
    """Carga docentes disponibles y alertas actuales."""
    # Docentes disponibles para el selector de destinatario
    try:
        _s["docentes"] = Container.usuario_service().listar_docentes()
    except Exception as exc:
        logger.warning("No se pudieron cargar docentes: %s", exc)
        _s["docentes"] = []

    # Alertas de seguimiento del estudiante seleccionado
    _cargar_alertas(_s)


def _cargar_alertas(_s: dict) -> None:
    """Carga alertas SEGUIMIENTO_REQUERIDO del estudiante seleccionado."""
    est_id = _s["sel_estudiante_id"]
    if not est_id:
        _s["alertas"] = []
        return
    try:
        from src.services.alerta_service import FiltroAlertasDTO, TipoAlerta
        filtro = FiltroAlertasDTO(
            estudiante_id=int(est_id),
            tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO,
            solo_pendientes=False,
        )
        _s["alertas"] = Container.alerta_service().listar_alertas(filtro)
    except Exception as exc:
        logger.error("Error cargando alertas de seguimiento: %s", exc)
        _s["alertas"] = []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nombre_estudiante(_s: dict, est_id: int | None) -> str:
    for est in _s["estudiantes"]:
        if getattr(est, "id", None) == est_id:
            return f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
    return str(est_id) if est_id else "—"


def _nombre_docente(_s: dict, docente_id: int | None) -> str:
    for d in _s["docentes"]:
        if getattr(d, "id", None) == docente_id:
            return (
                f"{getattr(d, 'apellido', '')} {getattr(d, 'nombre', '')}".strip()
                or getattr(d, "email", str(docente_id))
            )
    return str(docente_id) if docente_id else "—"


def _construir_filas_alertas(_s: dict) -> list[dict]:
    filas = []
    for alerta in _s["alertas"]:
        nivel_raw = str(getattr(alerta, "nivel", "")).lower()
        if "." in nivel_raw:
            nivel_raw = nivel_raw.split(".")[-1]
        filas.append({
            "id":             getattr(alerta, "id", None),
            "fecha":          str(getattr(alerta, "fecha_generacion", ""))[:10],
            "estudiante":     _nombre_estudiante(_s, getattr(alerta, "estudiante_id", None)),
            "descripcion":    str(getattr(alerta, "descripcion", "")),
            "nivel_raw":      nivel_raw,
            "nivel_display":  _NIVEL_DISPLAY.get(nivel_raw, nivel_raw),
            "destinatario":   _nombre_docente(_s, getattr(alerta, "usuario_destino_id", None)),
            "estado":         "Resuelta" if getattr(alerta, "resuelta", False) else "Pendiente",
        })
    return filas


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (convivencia_16)
def seguimiento_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    # Guard de rol: solo director/coordinador/director_de_grupo acceden
    if ctx.usuario_rol not in _ROLES_VER:
        ui.navigate.to("/inicio")
        return

    puede_crear = ctx.usuario_rol in _ROLES_CREAR

    _s = _estado_inicial()
    _cargar_estado(ctx, _s)

    # ── Handlers ───────────────────────────────────────────────────────────

    def on_estudiante_change(valor) -> None:
        _s["sel_estudiante_id"] = valor
        _s["resultado_360"] = None
        _cargar_alertas(_s)
        if _s["sel_estudiante_id"] and _s["sel_periodo_id"]:
            _ver_360()
        else:
            _contenido.refresh()

    def _ver_360() -> None:
        est_id = _s["sel_estudiante_id"]
        per_id = _s["sel_periodo_id"]
        if not est_id:
            toast_warning("Selecciona un estudiante.")
            return
        if not per_id:
            toast_warning("Selecciona un periodo.")
            return
        try:
            _s["resultado_360"] = Container.convivencia_service().vista_360(
                estudiante_id=int(est_id),
                periodo_id=int(per_id),
                usuario_id=ctx.usuario_id,
                usuario_rol=ctx.usuario_rol,
            )
            _contenido.refresh()
        except PermissionError as exc:
            toast_error(f"Sin permiso: {exc}")
        except Exception as exc:
            logger.error("Error en vista 360°: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")

    def _enviar_alerta(datos: dict) -> bool | None:
        est_id      = datos.get("estudiante_id")
        docente_id  = datos.get("usuario_destino_id")
        descripcion = str(datos.get("descripcion", "")).strip()
        nivel_str   = datos.get("nivel", "advertencia")

        if not est_id:
            toast_warning("Selecciona un estudiante.")
            return False
        if not docente_id:
            toast_warning("Selecciona el profesor destinatario.")
            return False
        if not descripcion:
            toast_warning("La descripción es requerida.")
            return False

        def _ejecutar() -> None:
            try:
                dto = NuevaAlertaSeguimientoDTO(
                    estudiante_id=int(est_id),
                    usuario_destino_id=int(docente_id),
                    descripcion=descripcion,
                    nivel=nivel_str,
                )
                Container.convivencia_service().crear_alerta_seguimiento_manual(
                    dto,
                    usuario_id=ctx.usuario_id,
                    usuario_rol=ctx.usuario_rol,
                )
                toast_success("Alerta de seguimiento enviada.")
                _cargar_alertas(_s)
                _contenido.refresh()
            except PermissionError as exc:
                toast_error(f"Sin permiso: {exc}")
            except Exception as exc:
                logger.error("Error creando alerta de seguimiento: %s", exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Enviar alerta de seguimiento",
            mensaje=(
                "¿Confirmas el envío de la alerta de seguimiento "
                "al profesor seleccionado?"
            ),
            on_confirm=_ejecutar,
        )
        return None

    def _abrir_crear_alerta() -> None:
        opciones_est = {
            getattr(e, "id", None): f"{getattr(e, 'apellido', '')} {getattr(e, 'nombre', '')}".strip()
            for e in _s["estudiantes"]
        }
        opciones_doc = {
            getattr(d, "id", None): (
                f"{getattr(d, 'apellido', '')} {getattr(d, 'nombre', '')}".strip()
                or getattr(d, "email", str(getattr(d, "id", "")))
            )
            for d in _s["docentes"]
        }
        opciones_nivel = {
            "advertencia": "Advertencia",
            "critica":     "Crítica",
        }

        campos = [
            {
                "key":      "estudiante_id",
                "label":    "Estudiante",
                "tipo":     "select",
                "opciones": opciones_est,
                "requerido": True,
                "valor":    _s["sel_estudiante_id"],
            },
            {
                "key":      "usuario_destino_id",
                "label":    "Profesor destinatario",
                "tipo":     "select",
                "opciones": opciones_doc,
                "requerido": True,
            },
            {
                "key":         "descripcion",
                "label":       "Descripción",
                "tipo":        "textarea",
                "placeholder": "Describe el motivo del seguimiento...",
                "requerido":   True,
            },
            {
                "key":      "nivel",
                "label":    "Nivel de alerta",
                "tipo":     "select",
                "opciones": opciones_nivel,
                "valor":    "advertencia",
            },
        ]
        form_dialog(
            titulo="Nueva alerta de seguimiento",
            campos=campos,
            on_submit=_enviar_alerta,
            texto_submit="Enviar alerta",
            max_width="max-w-lg",
        )

    # ── Refreshable ────────────────────────────────────────────────────────

    @ui.refreshable
    def _contenido() -> None:
        def on_sel_change(s: dict) -> None:
            _s["sel_periodo_id"]    = s["sel_periodo_id"]
            _s["sel_grupo_id"]      = s["sel_grupo_id"]
            _s["sel_asignacion_id"] = s["sel_asignacion_id"]
            _s["resultado_360"]     = None
            if s["sel_grupo_id"]:
                try:
                    _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(
                        s["sel_grupo_id"]
                    )
                except Exception as exc:
                    logger.error("Error cargando estudiantes: %s", exc)
                    _s["estudiantes"] = []
            else:
                _s["estudiantes"] = []
            if _s["estudiantes"] and _s["sel_estudiante_id"] is None:
                _s["sel_estudiante_id"] = getattr(_s["estudiantes"][0], "id", None)
            _cargar_alertas(_s)
            if _s["sel_estudiante_id"] and _s["sel_periodo_id"]:
                _ver_360()
            else:
                _contenido.refresh()

        inline_periodo_grupo_asignatura(
            _s, on_sel_change,
            usuario_id=ctx.usuario_id,
            institucion_id=ctx.institucion_id,
            usuario_rol=ctx.usuario_rol,
            preselect_periodo=True,
        )

        filas = _construir_filas_alertas(_s)

        opciones_estudiantes = {
            getattr(e, "id", None): f"{getattr(e, 'apellido', '')} {getattr(e, 'nombre', '')}".strip()
            for e in _s["estudiantes"]
        }

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):

                # Toolbar: selector de estudiante + nueva alerta (solo director/coordinador)
                if puede_crear:
                    with ui.element("div").classes("panel-card"):
                        with ui.element("div").classes("panel-toolbar"):
                            ui.select(
                                options=opciones_estudiantes,
                                label="Estudiante",
                                value=_s["sel_estudiante_id"],
                                on_change=lambda e: on_estudiante_change(e.value),
                            ).classes("andes-input input-min-sm").props("outlined dense")

                            ui.element("div").classes("panel-toolbar-spacer")

                            btn_primary(
                                "Nueva alerta",
                                on_click=_abrir_crear_alerta,
                                icon=Icons.ADD,
                            )

                    if not _s["estudiantes"]:
                        with ui.element("div").classes("panel-card"):
                            empty_state(
                                titulo="Sin grupo asignado",
                                descripcion="Selecciona un grupo en el contexto para gestionar alertas.",
                            )
                        return

                # T3: Two-column layout
                with ui.element("div").classes("page-body"):

                    # ── Main column: Alertas ──────────────────────────────
                    with ui.element("div").classes("page-col-main"):
                        with ui.element("div").classes("panel-card"):
                            ui.label("Alertas de seguimiento").classes("panel-title")
                            if not filas:
                                empty_state(
                                    titulo="Sin alertas",
                                    descripcion="No hay alertas de seguimiento para este estudiante.",
                                )
                            else:
                                # T4: Colored alert cards instead of ag-Grid
                                for fila in filas:
                                    nivel_raw = fila["nivel_raw"]
                                    with ui.element("div").classes(f"alerta-item alerta-{nivel_raw}"):
                                        ui.label(fila["fecha"]).classes("text-xs-meta")
                                        ui.label(fila["descripcion"]).classes("alerta-item-text")
                                        ui.label(fila["destinatario"]).classes("text-xs-meta")
                                        badge_var = "badge-success" if fila["estado"] == "Resuelta" else "badge-warning"
                                        ui.label(fila["estado"]).classes(f"badge {badge_var}")

                    # ── Side column: Vista 360° ───────────────────────────
                    with ui.element("div").classes("page-col-side"):
                        with ui.element("div").classes("panel-card"):
                            ui.label("Vista 360° del estudiante").classes("panel-title")
                            with ui.element("div").classes("panel-toolbar"):
                                # Selector de estudiante visible solo para roles sin panel arriba
                                if not puede_crear:
                                    ui.select(
                                        options=opciones_estudiantes,
                                        label="Estudiante",
                                        value=_s["sel_estudiante_id"],
                                        on_change=lambda e: on_estudiante_change(e.value),
                                    ).classes("andes-input input-min-sm").props("outlined dense")

                                btn_ghost("Actualizar 360°", on_click=_ver_360, icon="refresh")

                            # T5: Improved 360° view
                            res = _s.get("resultado_360")
                            if res is None:
                                empty_state(
                                    titulo="Sin datos de seguimiento",
                                    descripcion=(
                                        "Selecciona un estudiante y periodo "
                                        "para cargar la vista 360°."
                                    ),
                                )
                            else:
                                _tiene_datos = (
                                    res.nota_comportamiento is not None
                                    or res.promedio_notas is not None
                                    or res.observaciones
                                    or res.alertas_activas
                                )
                                if not _tiene_datos:
                                    empty_state(
                                        titulo="Sin datos de seguimiento",
                                        descripcion="No hay datos registrados para este estudiante en el periodo.",
                                    )
                                else:
                                    # Stat cards
                                    with ui.element("div").classes("form-row-inline"):
                                        if res.nota_comportamiento is not None:
                                            stat_card(
                                                "Nota comportamiento",
                                                res.nota_comportamiento,
                                                "grade",
                                                subtitulo=res.nivel_comportamiento or "",
                                                variante="primary",
                                            )
                                        if res.promedio_notas is not None:
                                            stat_card(
                                                "Promedio académico",
                                                res.promedio_notas,
                                                "bar_chart",
                                                variante="info",
                                            )
                                        if res.concepto:
                                            with ui.element("div").classes("stat-card-wrapper info"):
                                                ui.label("Concepto").classes("stat-card-label")
                                                ui.label(res.concepto).classes("stat-card-value")

                                    # Observaciones as config-list-row
                                    if res.observaciones:
                                        ui.label("Observaciones del periodo").classes("panel-title")
                                        for obs_txt in res.observaciones:
                                            with ui.element("div").classes("config-list-row"):
                                                ui.label(obs_txt).classes("config-col-name")

                                    # Alertas activas as alerta-item cards
                                    if res.alertas_activas:
                                        ui.label("Alertas activas").classes("panel-title")
                                        for alerta_txt in res.alertas_activas:
                                            with ui.element("div").classes("alerta-item alerta-advertencia"):
                                                ui.label(alerta_txt).classes("alerta-item-text")

        app_layout(
            ctx, contenido_pagina,
            page_titulo="Seguimiento",
        )

    _contenido()


__all__ = ["seguimiento_page"]
