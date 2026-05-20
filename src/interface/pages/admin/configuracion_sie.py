"""
src/interface/pages/admin/configuracion_sie.py
================================================
Página de configuración académica (SIE).
Ruta: /admin/configuracion
Acceso: admin, director

Muestra el año lectivo activo y permite crear un nuevo año.
La información institucional se gestiona en configuracion_institucion.py.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_ghost, btn_icon
from src.interface.design.components import page_header, badge_estado_general
from src.services.configuracion_service import NuevaConfiguracionAnioDTO

logger = logging.getLogger("ADMIN.CONFIG_SIE")


@ui.page("/admin/configuracion")
def configuracion_sie_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
        return

    logger.info("Config SIE: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "config_activa": None,
        "nuevo_anio":    2026,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            _s["config_activa"] = Container.configuracion_service().get_activa()
        except Exception as exc:
            logger.warning("Sin configuración activa: %s", exc)
            _s["config_activa"] = None

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _crear_anio() -> None:
        try:
            anio = int(_s["nuevo_anio"])
            dto  = NuevaConfiguracionAnioDTO(anio=anio)
            Container.configuracion_service().crear_anio(dto)
            ui.notify(f"Año lectivo {anio} creado", type="positive")
            _cargar_estado()
            panel_anio.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al crear año: %s", exc)
            ui.notify("Error al crear el año lectivo", type="negative")

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def panel_anio() -> None:
        config = _s["config_activa"]

        if config:
            with ui.element("div").classes("panel-card"):
                ui.label("Año lectivo activo").classes("eyebrow-label mb-2")
                with ui.row().classes("items-center gap-4"):
                    ui.label(str(config.anio)).classes("text-4xl font-bold")
                    badge_estado_general(True)

                with ui.element("div").classes("mt-3 grid grid-cols-2 gap-3"):
                    _dato("Nota mínima aprobación", f"{config.nota_minima_aprobacion:.1f}")
                    _dato(
                        "Inicio clases",
                        config.fecha_inicio_clases.strftime("%d/%m/%Y")
                        if config.fecha_inicio_clases else "No definida",
                    )
                    _dato(
                        "Fin clases",
                        config.fecha_fin_clases.strftime("%d/%m/%Y")
                        if config.fecha_fin_clases else "No definida",
                    )
                    if config.duracion_semanas:
                        _dato("Duración", f"{config.duracion_semanas} semanas")

                ui.separator().classes("my-4")
                ui.label(
                    "Para cambiar el año activo, crea un nuevo año lectivo."
                ).classes("text-sm text-grey-6")
        else:
            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("flex-col items-center gap-2"):
                    ThemeManager.icono("event_busy", size=36, color="var(--color-warning)")
                    ui.label("Sin año lectivo activo").classes("text-lg font-semibold mt-2")
                    ui.label(
                        "Crea un año lectivo para comenzar a operar."
                    ).classes("text-sm text-grey-6")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            page_header(
                titulo    = "Configuración del SIE",
                subtitulo = "Periodos académicos y configuración del año escolar",
                icono     = "settings",
            )

            with ui.element("div").classes("panel-card"):
                btn_icon("refresh", on_click=lambda: (_cargar_estado(), panel_anio.refresh()), tooltip="Recargar").classes("ml-auto")

            panel_anio()

            # Crear nuevo año
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Crear nuevo año lectivo").classes("text-base font-semibold mb-3")
                ui.label(
                    "Al crear un nuevo año, este se convierte en el activo. "
                    "Los datos históricos del año anterior se conservan."
                ).classes("text-sm text-grey-6 mb-4")
                with ui.row().classes("gap-3 items-end"):
                    ui.number(
                        "Año *",
                        value=_s["nuevo_anio"],
                        min=2000,
                        max=2100,
                        step=1,
                    ).classes("w-32").bind_value(_s, "nuevo_anio")
                    btn_primary("Crear año lectivo", on_click=_crear_anio, icon="add_circle")

            # Enlace a info institucional
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-3"):
                    ThemeManager.icono("business", size=20, color="var(--color-info)")
                    with ui.element("div").classes("flex-1"):
                        ui.label("Información institucional").classes("font-semibold")
                        ui.label(
                            "Nombre, DANE, rector y datos para boletines."
                        ).classes("text-sm text-grey-6")
                    btn_ghost("Gestionar", on_click=lambda: ui.navigate.to("/admin/configuracion-institucion"), icon="arrow_forward")

    app_layout(
        titulo_pagina="Administración · Configuración SIE",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/admin/configuracion",
        contenido=contenido,
        ctx=ctx,
    )


def _dato(label: str, valor: str) -> None:
    """Dato etiqueta-valor para el panel de información."""
    with ui.element("div").classes("flex-col"):
        ui.label(label).classes("text-xs text-grey-6")
        ui.label(valor).classes("text-sm font-medium")


__all__ = ["configuracion_sie_page"]
