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
from src.interface.design.components.buttons import btn_primary, btn_ghost, btn_icon
from src.services.configuracion_service import ActualizarInfoInstitucionalDTO
from src.interface.design.components import (
    empty_state,
    toast_error,
    toast_success,
    toast_warning,
)

logger = logging.getLogger("ADMIN.CONFIG_INSTITUCION")


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def configuracion_institucion_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
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
        # Fuente única: la configuración del año activo ya contiene todos los
        # campos institucionales editables. No se usa get_info_institucional()
        # aquí porque ese DTO es para boletines y rechaza años incompletos.
        try:
            config = Container.configuracion_service().get_activa(ctx.institucion_id)
        except ValueError:
            logger.warning("Sin año lectivo activo configurado")
            return
        _s["anio_id"]               = config.id
        _s["anio_label"]            = str(config.anio)
        _s["nombre_institucion"]    = config.nombre_institucion or ""
        _s["dane_code"]             = config.dane_code or ""
        _s["rector"]                = config.rector or ""
        _s["direccion"]             = config.direccion or ""
        _s["municipio"]             = config.municipio or ""
        _s["telefono_institucion"]  = config.telefono_institucion or ""
        _s["logo_path"]             = config.logo_path or ""
        _s["resolucion_aprobacion"] = config.resolucion_aprobacion or ""

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _guardar_info() -> None:
        if not _s["anio_id"]:
            toast_warning("No hay un año lectivo activo configurado")
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
            toast_success("Información institucional actualizada")
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al guardar info institucional: %s", exc)
            toast_error("Error al guardar la información")

    def _recargar() -> None:
        _cargar_estado()
        formulario.refresh()

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def formulario() -> None:
        if not _s["anio_id"]:
            empty_state(
                icono="event_busy",
                titulo="Sin año lectivo activo",
                descripcion="Configura un año lectivo en la sección de Configuración SIE.",
                cta_label="Ir a Configuración SIE",
                cta_on_click=lambda: ui.navigate.to("/admin/configuracion"),
            )
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
            btn_ghost("Recargar datos", on_click=_recargar, icon="refresh")
            btn_primary("Guardar cambios", on_click=_guardar_info, icon="save")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):
                btn_icon("arrow_back", on_click=lambda: ui.navigate.to("/admin/configuracion"), tooltip="Volver a Configuración SIE").classes("ml-auto")

                ui.label(
                    "Estos datos aparecen en los boletines e informes académicos."
                ).classes("text-sm text-muted mb-4")

                formulario()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Información Institucional",
        page_subtitulo = "Datos básicos y generales de la institución educativa",
        page_icono     = "business",
        mostrar_contexto = False,
    )


__all__ = ["configuracion_institucion_page"]
