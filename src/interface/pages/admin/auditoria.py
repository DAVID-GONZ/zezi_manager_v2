"""
src/interface/pages/admin/auditoria.py
=======================================
Vista de auditoría (solo lectura).
Ruta: /admin/auditoria
Acceso: admin (rol de plataforma — auditor de lectura global).

Dos secciones:
 - Cambios:  operaciones CRUD del audit_log (tabla, acción, timestamp).
 - Sesiones: eventos de autenticación/acceso (login, logout, accesos denegados).

Solo lectura: no expone acciones de escritura. La escritura de auditoría
la realizan otros servicios vía IAuditoriaRepository.
"""
from __future__ import annotations

import logging
from datetime import datetime

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_icon
from src.interface.design.components import (
    data_table,
    date_range_input,
    empty_state,
    toast_error,
)
from src.services.auditoria_service import (
    AccionCambio,
    FiltroAuditoriaDTO,
    TipoEventoSesion,
)

logger = logging.getLogger("ADMIN.AUDITORIA")

# Opciones de filtro derivadas de los enums del dominio (re-exportados por el
# service layer). Se construyen como dicts {valor_str: etiqueta} para los
# selects; el valor None representa "todos".
_ACCIONES_OPCIONES = {a.value: a.value.capitalize() for a in AccionCambio}
_EVENTOS_OPCIONES = {t.value: t.value.replace("_", " ").capitalize() for t in TipoEventoSesion}

_POR_PAGINA = 100


@ui.page("/admin/auditoria")
def auditoria_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol != "admin":
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    logger.info("Auditoría: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # Rango del periodo activo (para el preset "Periodo activo" del componente
    # de fecha). Se obtiene en la página y se inyecta como primitivos; el
    # componente no consulta servicios.
    _periodo_desde: str | None = None
    _periodo_hasta: str | None = None
    try:
        _cfg = Container.configuracion_service().get_activa()
        if _cfg.fecha_inicio_clases:
            _periodo_desde = _cfg.fecha_inicio_clases.isoformat()
        if _cfg.fecha_fin_clases:
            _periodo_hasta = _cfg.fecha_fin_clases.isoformat()
    except Exception as exc:
        logger.warning("No se pudo obtener el periodo activo: %s", exc)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        # filtros comunes
        "desde":        None,   # str "YYYY-MM-DD" o None
        "hasta":        None,
        "usuario_id":   None,   # int o None
        "pagina":       1,
        # filtros específicos de Cambios
        "tabla":        None,
        "accion":       None,   # str enum value o None
        # filtros específicos de Sesiones
        "tipo_evento":  None,   # str enum value o None
        # datos cargados
        "cambios":      [],
        "sesiones":     [],
    }

    # ── Helpers de filtro ──────────────────────────────────────────────────────
    def _parsear_fecha(valor: str | None, fin_de_dia: bool = False) -> "datetime | None":
        if not valor:
            return None
        try:
            base = datetime.strptime(valor, "%Y-%m-%d")
        except ValueError:
            return None
        if fin_de_dia:
            return base.replace(hour=23, minute=59, second=59)
        return base

    def _construir_filtro() -> FiltroAuditoriaDTO:
        return FiltroAuditoriaDTO(
            usuario_id  = _s["usuario_id"],
            tabla       = _s["tabla"] or None,
            accion      = _s["accion"] or None,
            tipo_evento = _s["tipo_evento"] or None,
            desde       = _parsear_fecha(_s["desde"]),
            hasta       = _parsear_fecha(_s["hasta"], fin_de_dia=True),
            pagina      = _s["pagina"],
            por_pagina  = _POR_PAGINA,
        )

    # ── Carga de datos ──────────────────────────────────────────────────────────
    def _cargar_cambios() -> None:
        try:
            _s["cambios"] = Container.auditoria_service().listar_cambios(_construir_filtro())
        except Exception as exc:
            logger.error("Error al cargar cambios de auditoría: %s", exc)
            _s["cambios"] = []

    def _cargar_sesiones() -> None:
        try:
            _s["sesiones"] = Container.auditoria_service().listar_eventos_sesion(_construir_filtro())
        except Exception as exc:
            logger.error("Error al cargar eventos de sesión: %s", exc)
            _s["sesiones"] = []

    def _cargar_todo() -> None:
        _cargar_cambios()
        _cargar_sesiones()

    _cargar_todo()

    # ── Refrescos ────────────────────────────────────────────────────────────────
    def _on_filtros_cambio() -> None:
        _s["pagina"] = 1
        _cargar_todo()
        tabla_cambios.refresh()
        tabla_sesiones.refresh()

    # ── Tablas (refreshable, solo lectura) ─────────────────────────────────────
    @ui.refreshable
    def tabla_cambios() -> None:
        cambios = _s["cambios"]
        if not cambios:
            empty_state(
                variante="search",
                icono="history",
                titulo="No hay cambios registrados",
                descripcion="Ajusta el rango de fechas, la tabla o la acción para ver más resultados.",
            )
            return

        columnas = [
            {"name": "timestamp", "label": "Fecha y hora", "field": "timestamp", "sortable": True},
            {"name": "accion",    "label": "Acción",       "field": "accion",    "sortable": True},
            {"name": "tabla",     "label": "Tabla",        "field": "tabla",     "sortable": True},
            {"name": "registro",  "label": "Registro",     "field": "registro"},
            {"name": "usuario",   "label": "Usuario ID",   "field": "usuario"},
        ]
        filas = [
            {
                "timestamp": c.timestamp_display,
                "accion":    c.accion.value if hasattr(c.accion, "value") else str(c.accion),
                "tabla":     c.tabla,
                "registro":  c.registro_id if c.registro_id is not None else "—",
                "usuario":   c.usuario_id if c.usuario_id is not None else "—",
            }
            for c in cambios
        ]
        data_table(columnas, filas, titulo="Cambios (audit_log)", filas_por_pagina=15)

    @ui.refreshable
    def tabla_sesiones() -> None:
        sesiones = _s["sesiones"]
        if not sesiones:
            empty_state(
                variante="search",
                icono="history",
                titulo="No hay eventos de sesión",
                descripcion="Ajusta el rango de fechas, el usuario o el tipo de evento para ver más resultados.",
            )
            return

        columnas = [
            {"name": "fecha",       "label": "Fecha y hora", "field": "fecha",       "sortable": True},
            {"name": "tipo_evento", "label": "Tipo",         "field": "tipo_evento", "sortable": True},
            {"name": "usuario",     "label": "Usuario",      "field": "usuario",     "sortable": True},
            {"name": "ip",          "label": "IP",           "field": "ip"},
            {"name": "detalles",    "label": "Detalles",     "field": "detalles"},
        ]
        filas = [
            {
                "fecha":       e.fecha_display,
                "tipo_evento": e.tipo_evento.value if hasattr(e.tipo_evento, "value") else str(e.tipo_evento),
                "usuario":     e.usuario,
                "ip":          e.ip_address or "—",
                "detalles":    e.detalles or "—",
            }
            for e in sesiones
        ]
        data_table(columnas, filas, titulo="Sesiones (auditoría)", filas_por_pagina=15)

    # ── Filtros comunes (rango de fechas + usuario) ─────────────────────────────
    def _on_rango_cambio(desde: "str | None", hasta: "str | None") -> None:
        _s["desde"] = desde
        _s["hasta"] = hasta
        _on_filtros_cambio()

    def _render_filtros_comunes() -> None:
        with ui.row().classes("gap-4 items-end flex-wrap mb-4"):
            date_range_input(
                desde=_s["desde"],
                hasta=_s["hasta"],
                on_change=_on_rango_cambio,
                periodo_desde=_periodo_desde,
                periodo_hasta=_periodo_hasta,
            )
            ui.input(
                label="Usuario ID",
                placeholder="(opcional)",
                on_change=lambda e: (
                    _s.__setitem__("usuario_id", _a_int(e.value)),
                    _on_filtros_cambio(),
                ),
            ).props("dense outlined").classes("w-32")
            btn_icon("refresh", on_click=_on_filtros_cambio, tooltip="Recargar")

    def _a_int(valor) -> "int | None":
        try:
            v = str(valor).strip()
            return int(v) if v else None
        except (TypeError, ValueError):
            return None

    # ── Contenido principal ──────────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-2"):
                    ThemeManager.icono("history", size=22, color="var(--color-primary)")
                    ui.label("Registro de auditoría").classes("text-xl font-bold")
                    ui.label("Solo lectura").classes("text-sm text-secondary ml-2")

                _render_filtros_comunes()

                with ui.tabs().classes("w-full") as tabs:
                    ui.tab("cambios",  label="Cambios",  icon="edit_note")
                    ui.tab("sesiones", label="Sesiones", icon="login")

                with ui.tab_panels(tabs, value="cambios").classes("w-full mt-0"):

                    # ── Tab Cambios ───────────────────────────────────────────
                    with ui.tab_panel("cambios"):
                        with ui.row().classes("gap-4 items-center flex-wrap mb-4"):
                            ui.label("Filtros:").classes("text-sm font-semibold")
                            ui.input(
                                label="Tabla",
                                placeholder="(todas)",
                                on_change=lambda e: (
                                    _s.__setitem__("tabla", (e.value or "").strip() or None),
                                    _on_filtros_cambio(),
                                ),
                            ).props("dense outlined").classes("w-44")
                            accion_opts = {None: "Todas las acciones"}
                            accion_opts.update(_ACCIONES_OPCIONES)
                            ui.select(
                                accion_opts,
                                value=None,
                                label="Acción",
                                on_change=lambda e: (
                                    _s.__setitem__("accion", e.value),
                                    _on_filtros_cambio(),
                                ),
                            ).classes("w-44")
                        tabla_cambios()

                    # ── Tab Sesiones ──────────────────────────────────────────
                    with ui.tab_panel("sesiones"):
                        with ui.row().classes("gap-4 items-center flex-wrap mb-4"):
                            ui.label("Filtros:").classes("text-sm font-semibold")
                            evento_opts = {None: "Todos los eventos"}
                            evento_opts.update(_EVENTOS_OPCIONES)
                            ui.select(
                                evento_opts,
                                value=None,
                                label="Tipo de evento",
                                on_change=lambda e: (
                                    _s.__setitem__("tipo_evento", e.value),
                                    _on_filtros_cambio(),
                                ),
                            ).classes("w-56")
                        tabla_sesiones()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Auditoría",
        page_subtitulo = "Registro de cambios y eventos de sesión (solo lectura)",
        page_icono     = "history",
    )


__all__ = ["auditoria_page"]
