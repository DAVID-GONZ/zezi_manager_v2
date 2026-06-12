"""
src/interface/pages/academico/horario_generar.py
=====================================================
Página de generación de horarios.
Ruta: /academico/generar-horario
Acceso: admin, director, coordinador

Secciones:
  1. Selección de configuración de generación
  2. Creación de nueva configuración
  3. Ejecución del motor de generación
  4. Vista previa del escenario generado
  5. Activación del escenario generado

Reglas de capas:
  - Solo usa Container.*
  - No importa repositorios ni src.db.
  - Todo estilo se define con clases CSS, salvo valores DYNAMIC.
"""
from __future__ import annotations

import logging
from typing import Any

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_secondary
from src.interface.design.components import (
    empty_state,
    form_dialog,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.pages.academico.parrilla_widget import render_parrilla

logger = logging.getLogger("GENERADOR_HORARIO")


@ui.page("/academico/generar-horario")
def horario_generar_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director", "coordinador"):
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    if not ctx.anio_id or not ctx.periodo_id:
        toast_warning("Selecciona primero un año lectivo y un periodo activo")
        ui.navigate.to("/inicio")
        return

    _s: dict[str, Any] = {
        "configs": [],
        "config_sel": None,
        "plantillas": [],
        "grupos": [],
        "resultado": None,
        "datos_preview": None,
    }

    def _cargar_plantillas() -> None:
        try:
            _s["plantillas"] = Container.infraestructura_service().listar_plantillas()
        except Exception as exc:
            logger.error("Error cargando plantillas: %s", exc)
            _s["plantillas"] = []

    def _cargar_grupos() -> None:
        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error cargando grupos: %s", exc)
            _s["grupos"] = []

    def _cargar_configs() -> None:
        try:
            _s["configs"] = Container.infraestructura_service().listar_configs_generacion(
                ctx.periodo_id
            )
        except Exception as exc:
            logger.error("Error cargando configuraciones de generación: %s", exc)
            _s["configs"] = []

    def _seleccionar_config(config_id: int | None) -> None:
        if config_id is None:
            _s["config_sel"] = None
            _s["resultado"] = None
            _s["datos_preview"] = None
            contenido_refreshable.refresh()
            return
        config = next((c for c in _s["configs"] if c.id == config_id), None)
        _s["config_sel"] = config
        _s["resultado"] = None
        _s["datos_preview"] = None
        contenido_refreshable.refresh()

    def _crear_config_dialog() -> None:
        if not _s["plantillas"]:
            toast_warning("No hay plantillas disponibles para crear una configuración")
            return

        plantilla_opts = {p.id: p.nombre for p in _s["plantillas"] if p.id is not None}
        grupo_opts = {g.id: g.codigo for g in _s["grupos"]}

        def _guardar(datos: dict) -> "bool | None":
            nombre = str(datos.get("nombre", "") or "").strip()
            plantilla_id = datos.get("plantilla_id")
            grupos = datos.get("grupos") or []
            if not nombre:
                toast_warning("El nombre de la configuración es obligatorio")
                return False
            if not plantilla_id:
                toast_warning("Selecciona una plantilla")
                return False

            try:
                Container.infraestructura_service().crear_config_generacion(
                    nombre=nombre,
                    periodo_id=ctx.periodo_id,
                    anio_id=ctx.anio_id,
                    plantilla_id=plantilla_id,
                    grupos=grupos if grupos else None,
                )
                toast_success("Configuración creada")
                _cargar_configs()
                contenido_refreshable.refresh()
            except Exception as exc:
                logger.error("Error creando configuración de generación: %s", exc)
                toast_error("No se pudo crear la configuración")
                return False

        form_dialog(
            titulo="Nueva configuración de generación",
            campos=[
                {"key": "nombre", "label": "Nombre", "tipo": "text", "requerido": True},
                {"key": "plantilla_id", "label": "Plantilla", "tipo": "select",
                 "opciones": plantilla_opts, "requerido": True},
                {"key": "grupos", "label": "Grupos", "tipo": "select",
                 "opciones": grupo_opts, "valor": [], "multiple": True},
            ],
            on_submit=_guardar,
            texto_submit="Crear",
            max_width="max-w-lg",
            columnas=1,
        )

    def _cargar_preview() -> None:
        resultado = _s.get("resultado")
        if not resultado or not getattr(resultado, "escenario_id", None):
            _s["datos_preview"] = None
            return
        try:
            _s["datos_preview"] = Container.horario_service().datos_parrilla(
                resultado.escenario_id
            )
        except Exception as exc:
            logger.error("Error cargando datos de parrilla de vista previa: %s", exc)
            _s["datos_preview"] = None

    def _generar_config() -> None:
        config = _s.get("config_sel")
        if not config or config.id is None:
            toast_warning("Selecciona una configuración para generar")
            return
        try:
            resultado = Container.generador_horario_service().generar(
                config.id,
                crear_escenario=True,
                optimizar=True,
            )
            _s["resultado"] = resultado
            _cargar_configs()
            _cargar_preview()
            toast_success("Generación completada")
            contenido_refreshable.refresh()
        except Exception as exc:
            logger.error("Error ejecutando generador: %s", exc)
            toast_error("Error al generar el horario")

    def _activar_escenario(escenario_id: int) -> None:
        try:
            Container.infraestructura_service().activar_escenario(escenario_id)
            toast_success("Escenario activado")
            _cargar_configs()
            contenido_refreshable.refresh()
        except Exception as exc:
            logger.error("Error activando escenario: %s", exc)
            toast_error("No se pudo activar el escenario")

    _cargar_plantillas()
    _cargar_grupos()
    _cargar_configs()

    @ui.refreshable
    def contenido_refreshable() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center justify-between flex-wrap gap-2"):
                ui.label("Generar horario").classes("text-subtitle1 font-semibold")
                with ui.row().classes("gap-2 flex-wrap"):
                    btn_primary("Nueva configuración", icon="add", on_click=_crear_config_dialog)
                    btn_secondary("Recargar", icon="refresh", on_click=lambda: (_cargar_configs(), contenido_refreshable.refresh()))

            if not _s["configs"]:
                empty_state(
                    icono=Icons.AUTO_MODE,
                    titulo="Sin configuraciones de generación",
                    descripcion="Crea una configuración para generar un horario.",
                )
                return

            with ui.element("div").classes("q-mt-sm overflow-auto"):
                with ui.element("table").classes("w-full border-collapse"):
                    with ui.element("thead"):
                        with ui.element("tr"):
                            for col in ("Nombre", "Plantilla", "Grupos", "Estado", "Acciones"):
                                ui.element("th").classes(
                                    "border px-3 py-2 text-left text-sm font-semibold bg-grey-2"
                                ).text = col
                    with ui.element("tbody"):
                        for config in _s["configs"]:
                            grupo_count = len(getattr(config, "grupos", []) or [])
                            plantilla_nombre = getattr(config, "plantilla_id", "N/A")
                            estado = getattr(config, "estado", "borrador")
                            with ui.element("tr"):
                                ui.element("td").classes("border px-3 py-2").text = getattr(config, "nombre", "")
                                ui.element("td").classes("border px-3 py-2").text = str(plantilla_nombre)
                                ui.element("td").classes("border px-3 py-2").text = (
                                    str(grupo_count) if grupo_count else "Todos"
                                )
                                ui.element("td").classes("border px-3 py-2").text = estado.title()
                                with ui.element("td").classes("border px-3 py-2"):
                                    btn_secondary(
                                        "Seleccionar",
                                        on_click=lambda _, c=config: _seleccionar_config(c.id),
                                        icon="check",
                                    )

        if _s["config_sel"]:
            config = _s["config_sel"]
            with ui.element("div").classes("panel-card q-mt-md"):
                with ui.row().classes("items-center justify-between flex-wrap gap-2"):
                    ui.label(f"Configuración: {getattr(config, 'nombre', '')}").classes(
                        "text-subtitle2 font-semibold"
                    )
                    with ui.row().classes("gap-2 flex-wrap"):
                        btn_primary("Generar horario", icon="play_arrow", on_click=_generar_config)
                        if getattr(config, "escenario_destino_id", None):
                            btn_secondary(
                                "Activar escenario",
                                icon="check_circle",
                                on_click=lambda: _activar_escenario(getattr(config, "escenario_destino_id")),
                            )

                with ui.element("div").classes("q-mt-sm grid gap-3 grid-cols-3"):
                    ui.label(f"Estado: {getattr(config, 'estado', 'borrador').title()}")
                    ui.label(f"Periodo ID: {getattr(config, 'periodo_id', '')}")
                    ui.label(f"Plantilla ID: {getattr(config, 'plantilla_id', '')}")

                if _s["resultado"]:
                    resultado = _s["resultado"]
                    with ui.element("div").classes("q-mt-sm grid gap-3 grid-cols-3"):
                        ui.label(f"Bloques generados: {getattr(resultado, 'colocados', 0)}")
                        ui.label(f"No colocados: {getattr(resultado, 'no_colocados', 0)}")
                        ui.label(f"Incidencias: {len(getattr(resultado, 'incidencias', []) or [])}")
                    if resultado.incidencias:
                        with ui.element("div").classes("q-mt-sm"):
                            ui.label("Incidencias:").classes("font-semibold")
                            for texto in resultado.incidencias:
                                ui.label(f"• {texto}").classes("text-sm text-grey-7")

                if _s["datos_preview"]:
                    with ui.element("div").classes("panel-card q-mt-sm"):
                        ui.label("Vista previa del escenario generado").classes("text-subtitle2 font-semibold")
                        render_parrilla(
                            datos=_s["datos_preview"],
                            perspectiva="Grupo",
                            eje_sel=None,
                            dias_filtro=None,
                            areas_filtro=None,
                        )

    app_layout(
        ctx,
        contenido_refreshable,
        page_titulo="Generar horario",
        page_subtitulo="Configura y ejecuta el generador de horarios",
        page_icono=Icons.AUTO_MODE,
    )


__all__ = ["horario_generar_page"]
