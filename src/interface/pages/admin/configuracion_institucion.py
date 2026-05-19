"""
src/interface/pages/admin/configuracion_institucion.py
========================================================
Página de información institucional.
Ruta: /admin/configuracion-institucion
Acceso: admin, director

Permite editar los datos que aparecen en boletines e informes:
nombre, NIT/DANE, rector, dirección, municipio, lema.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.services.configuracion_service import ActualizarInfoInstitucionalDTO

logger = logging.getLogger("ADMIN.CONFIG_INSTITUCION")


@ui.page("/admin/configuracion-institucion")
def configuracion_institucion_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
        return

    logger.info("Config institución: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "anio_id":              None,
        "anio_label":           "—",
        # campos del formulario
        "nombre_institucion":   "",
        "dane_code":            "",
        "rector":               "",
        "direccion":            "",
        "municipio":            "",
        "telefono_institucion": "",
        "logo_path":            "",
        "resolucion_aprobacion": "",
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            if not config:
                logger.warning("Sin configuración activa")
                return
            _s["anio_id"]    = config.id
            _s["anio_label"] = str(config.anio)

            info = Container.configuracion_service().get_info_institucional(config.id)
            # get_info_institucional puede retornar ConfiguracionAnio o InformacionInstitucionalDTO
            # usamos getattr para ser resilientes a cualquier tipo
            _s["nombre_institucion"]    = str(getattr(info, "nombre_institucion", config.nombre_institucion) or "")
            _s["dane_code"]             = str(getattr(info, "dane_code", config.dane_code) or "")
            _s["rector"]                = str(getattr(info, "rector", config.rector) or "")
            _s["direccion"]             = str(getattr(info, "direccion", config.direccion) or "")
            _s["municipio"]             = str(getattr(info, "municipio", config.municipio) or "")
            _s["telefono_institucion"]  = str(getattr(info, "telefono_institucion", config.telefono_institucion) or "")
            _s["logo_path"]             = str(getattr(info, "logo_path", config.logo_path) or "")
            _s["resolucion_aprobacion"] = str(getattr(info, "resolucion_aprobacion", config.resolucion_aprobacion) or "")
        except Exception as exc:
            logger.error("Error al cargar info institucional: %s", exc)

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _guardar_info() -> None:
        if not _s["anio_id"]:
            ui.notify("No hay un año lectivo activo configurado", type="warning")
            return
        try:
            dto = ActualizarInfoInstitucionalDTO(
                nombre_institucion    = _s["nombre_institucion"].strip() or None,
                dane_code             = _s["dane_code"].strip() or None,
                rector                = _s["rector"].strip() or None,
                direccion             = _s["direccion"].strip() or None,
                municipio             = _s["municipio"].strip() or None,
                telefono_institucion  = _s["telefono_institucion"].strip() or None,
                logo_path             = _s["logo_path"].strip() or None,
                resolucion_aprobacion = _s["resolucion_aprobacion"].strip() or None,
            )
            Container.configuracion_service().actualizar_info_institucional(_s["anio_id"], dto)
            ui.notify("Información institucional actualizada", type="positive")
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al guardar info institucional: %s", exc)
            ui.notify("Error al guardar la información", type="negative")

    def _recargar() -> None:
        _cargar_estado()
        formulario.refresh()

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def formulario() -> None:
        if not _s["anio_id"]:
            with ui.element("div").classes("flex-col items-center gap-2 p-8"):
                ThemeManager.icono("event_busy", size=36, color="var(--color-warning)")
                ui.label("Sin año lectivo activo").classes("text-lg font-semibold mt-2")
                ui.label(
                    "Configura un año lectivo en la sección de Configuración SIE."
                ).classes("text-sm text-grey-6")
                ui.button(
                    "Ir a Configuración SIE",
                    on_click=lambda: ui.navigate.to("/admin/configuracion"),
                    color="primary",
                ).classes("mt-4")
            return

        ui.label(f"Año lectivo: {_s['anio_label']}").classes("eyebrow-label mb-4")

        with ui.grid(columns=2).classes("w-full gap-4"):
            ui.input(
                "Nombre de la institución *",
                placeholder="Institución Educativa...",
            ).classes("col-span-2").bind_value(_s, "nombre_institucion")

            ui.input("Código DANE", placeholder="000000000000").bind_value(_s, "dane_code")
            ui.input("NIT / Resolución", placeholder="No. de resolución").bind_value(
                _s, "resolucion_aprobacion"
            )
            ui.input("Rector(a)", placeholder="Nombre del rector").bind_value(_s, "rector")
            ui.input("Teléfono", placeholder="(123) 456-7890").bind_value(
                _s, "telefono_institucion"
            )
            ui.input("Dirección", placeholder="Calle 1 # 2-3").bind_value(_s, "direccion")
            ui.input("Municipio", placeholder="Ciudad, Departamento").bind_value(_s, "municipio")
            ui.input(
                "URL del escudo/logo",
                placeholder="https://... o ruta local",
            ).classes("col-span-2").bind_value(_s, "logo_path")

        with ui.row().classes("gap-2 mt-6 justify-end"):
            ui.button(
                "Recargar datos",
                icon="refresh",
                on_click=_recargar,
            ).props("flat")
            ui.button(
                "Guardar cambios",
                icon="save",
                on_click=_guardar_info,
                color="primary",
            )

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ThemeManager.icono("business", size=22, color="var(--color-primary)")
                    ui.label("Información Institucional").classes("text-xl font-bold")
                    ui.button(
                        icon="arrow_back",
                        on_click=lambda: ui.navigate.to("/admin/configuracion"),
                    ).props("flat round dense").tooltip("Volver a Configuración SIE").classes("ml-auto")

                ui.label(
                    "Estos datos aparecen en los boletines e informes académicos."
                ).classes("text-sm text-grey-6 mb-4")

                formulario()

    app_layout(
        titulo_pagina="Administración · Información Institucional",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/admin/configuracion",
        contenido=contenido,
    )


__all__ = ["configuracion_institucion_page"]
