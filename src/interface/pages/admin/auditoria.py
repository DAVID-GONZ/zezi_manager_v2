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

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    data_table,
    date_range_input,
    empty_state,
    status_badge,
    toast_error,
    toast_success,
)
from src.interface.design.components.buttons import btn_icon, btn_secondary
from src.interface.design.components.form_fields import filter_input, filter_select
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.presenters.admin.auditoria_presenter import AuditoriaPresenter
from src.services.auditoria_service import (
    AccionCambio,
    TipoEventoSesion,
)

logger = logging.getLogger("ADMIN.AUDITORIA")

# Opciones de filtro derivadas de los enums del dominio (re-exportados por el
# service layer). Se construyen como dicts {valor_str: etiqueta} para los
# selects; el valor None representa "todos".
_ACCIONES_OPCIONES = {a.value: a.value.capitalize() for a in AccionCambio}
_EVENTOS_OPCIONES = {t.value: t.value.replace("_", " ").capitalize() for t in TipoEventoSesion}

_POR_PAGINA = 100


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def auditoria_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
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

    # ── Estado mutable (view-model en el presenter) ───────────────────────────
    presenter = AuditoriaPresenter()
    _s = presenter.estado  # misma referencia: los refreshables leen el estado del presenter

    # ── Carga de datos ──────────────────────────────────────────────────────────
    def _cargar_cambios() -> None:
        try:
            presenter.set_cambios(
                Container.auditoria_service().listar_cambios(
                    presenter.construir_filtro(_POR_PAGINA)
                )
            )
        except Exception as exc:
            logger.error("Error al cargar cambios de auditoría: %s", exc)
            presenter.set_cambios([])

    def _cargar_sesiones() -> None:
        try:
            presenter.set_sesiones(
                Container.auditoria_service().listar_eventos_sesion(
                    presenter.construir_filtro(_POR_PAGINA)
                )
            )
        except Exception as exc:
            logger.error("Error al cargar eventos de sesión: %s", exc)
            presenter.set_sesiones([])

    def _cargar_todo() -> None:
        _cargar_cambios()
        _cargar_sesiones()

    _cargar_todo()

    # ── Refrescos ────────────────────────────────────────────────────────────────
    def _on_filtros_cambio() -> None:
        presenter.reset_pagina()
        _cargar_todo()
        tabla_cambios.refresh()
        tabla_sesiones.refresh()

    # ── Integridad de la bitácora (read-only) ──────────────────────────────────
    @ui.refreshable
    def badge_integridad() -> None:
        estado = _s["integridad"]
        if estado is None:
            status_badge("Sin verificar", variante="neutral")
            return
        ok = estado["eventos_ok"] and estado["cambios_ok"]
        if ok:
            status_badge("Íntegra", variante="success")
            return
        # Reportar el primer registro roto de cada cadena alterada.
        rotos = []
        if not estado["eventos_ok"] and estado["evento_roto_id"] is not None:
            rotos.append(f"sesión #{estado['evento_roto_id']}")
        if not estado["cambios_ok"] and estado["cambio_roto_id"] is not None:
            rotos.append(f"cambio #{estado['cambio_roto_id']}")
        detalle = ", ".join(rotos) if rotos else "registro desconocido"
        status_badge(f"Alterada ({detalle})", variante="error")

    def _verificar_integridad() -> None:
        try:
            _s["integridad"] = Container.auditoria_service().verificar_integridad()
        except Exception as exc:
            logger.error("Error al verificar integridad de auditoría: %s", exc)
            _s["integridad"] = None
            toast_error("No se pudo verificar la integridad")
            badge_integridad.refresh()
            return
        badge_integridad.refresh()
        estado = _s["integridad"]
        if estado["eventos_ok"] and estado["cambios_ok"]:
            toast_success("Bitácora íntegra: la cadena de hashes cuadra")

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
            {"name": "accion", "label": "Acción", "field": "accion", "sortable": True},
            {"name": "tabla", "label": "Tabla", "field": "tabla", "sortable": True},
            {"name": "registro", "label": "Registro", "field": "registro"},
            {"name": "usuario", "label": "Usuario ID", "field": "usuario"},
        ]
        filas = [
            {
                "timestamp": c.timestamp_display,
                "accion": c.accion.value if hasattr(c.accion, "value") else str(c.accion),
                "tabla": c.tabla,
                "registro": c.registro_id if c.registro_id is not None else "—",
                "usuario": c.usuario_id if c.usuario_id is not None else "—",
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
            {"name": "fecha", "label": "Fecha y hora", "field": "fecha", "sortable": True},
            {"name": "tipo_evento", "label": "Tipo", "field": "tipo_evento", "sortable": True},
            {"name": "usuario", "label": "Usuario", "field": "usuario", "sortable": True},
            {"name": "ip", "label": "IP", "field": "ip"},
            {"name": "detalles", "label": "Detalles", "field": "detalles"},
        ]
        filas = [
            {
                "fecha": e.fecha_display,
                "tipo_evento": e.tipo_evento.value
                if hasattr(e.tipo_evento, "value")
                else str(e.tipo_evento),
                "usuario": e.usuario,
                "ip": e.ip_address or "—",
                "detalles": e.detalles or "—",
            }
            for e in sesiones
        ]
        data_table(columnas, filas, titulo="Sesiones (auditoría)", filas_por_pagina=15)

    # ── Filtros comunes (rango de fechas + usuario) ─────────────────────────────
    def _on_rango_cambio(desde: str | None, hasta: str | None) -> None:
        presenter.set_rango(desde, hasta)
        _on_filtros_cambio()

    def _render_filtros_comunes() -> None:
        with ui.row().classes("form-row-inline u-mb-lg"):
            date_range_input(
                desde=_s["desde"],
                hasta=_s["hasta"],
                on_change=_on_rango_cambio,
                periodo_desde=_periodo_desde,
                periodo_hasta=_periodo_hasta,
            )
            filter_input(
                label="Usuario ID",
                placeholder="Opcional",
                on_change=lambda e: (
                    presenter.set_usuario(e.value),
                    _on_filtros_cambio(),
                ),
                cls_extra="w-32",
            )
            btn_icon("refresh", on_click=_on_filtros_cambio, tooltip="Recargar")

    # ── Contenido principal ──────────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("form-row-center u-mb-sm"):
                    ThemeManager.icono("history", size=22, color="var(--color-primary)")
                    ui.label("Registro de auditoría").classes("text-xl font-bold")
                    ui.label("Solo lectura").classes("text-sm text-secondary ml-2")
                    with ui.row().classes("form-row-center ml-auto"):
                        btn_secondary(
                            "Verificar integridad",
                            on_click=_verificar_integridad,
                            icon="verified",
                            size="sm",
                        )
                        badge_integridad()

                _render_filtros_comunes()

                with ui.tabs().classes("w-full") as tabs:
                    ui.tab("cambios", label="Cambios", icon="edit_note")
                    ui.tab("sesiones", label="Sesiones", icon="login")

                with ui.tab_panels(tabs, value="cambios").classes("w-full mt-0"):
                    # ── Tab Cambios ───────────────────────────────────────────
                    with ui.tab_panel("cambios"):
                        with ui.row().classes("form-row-center-md u-mb-lg"):
                            ui.label("Filtros:").classes("text-sm font-semibold")
                            filter_input(
                                label="Tabla",
                                placeholder="Todas",
                                on_change=lambda e: (
                                    presenter.set_tabla(e.value),
                                    _on_filtros_cambio(),
                                ),
                                cls_extra="w-40",
                            )
                            accion_opts = {None: "Todas las acciones"}
                            accion_opts.update(_ACCIONES_OPCIONES)
                            filter_select(
                                label="Acción",
                                options=accion_opts,
                                value=None,
                                on_change=lambda e: (
                                    presenter.set_accion(e.value),
                                    _on_filtros_cambio(),
                                ),
                                cls_extra="w-40",
                            )
                        tabla_cambios()

                    # ── Tab Sesiones ──────────────────────────────────────────
                    with ui.tab_panel("sesiones"):
                        with ui.row().classes("form-row-center-md u-mb-lg"):
                            ui.label("Filtros:").classes("text-sm font-semibold")
                            evento_opts = {None: "Todos los eventos"}
                            evento_opts.update(_EVENTOS_OPCIONES)
                            filter_select(
                                label="Tipo de evento",
                                options=evento_opts,
                                value=None,
                                on_change=lambda e: (
                                    presenter.set_tipo_evento(e.value),
                                    _on_filtros_cambio(),
                                ),
                                cls_extra="w-48",
                            )
                        tabla_sesiones()

    app_layout(
        ctx,
        contenido,
        page_titulo="Auditoría",
        page_subtitulo="Registro de cambios y eventos de sesión (solo lectura)",
        page_icono="history",
    )


__all__ = ["auditoria_page"]
