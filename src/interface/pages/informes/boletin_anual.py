"""
src/interface/pages/informes/boletin_anual.py
=============================================
Página de boletines individuales anuales (consolidado de todos los periodos).

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.

Flujo:
  1. Filtros: grupo + año (anio_id).
  2. Al confirmar → carga lista de estudiantes del grupo.
  3. Por estudiante: botón "PDF" → InformeService.generar_boletin_anual() → ui.download().
  4. "Generar todos" → itera la lista completa.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_icon

logger = logging.getLogger("BOLETIN_ANUAL")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "grupo_id":    None,
        "anio_id":     None,
        "grupos":      [],
        "estudiantes": [],
    }


def _cargar_grupos(_s: dict) -> None:
    try:
        _s["grupos"] = Container.infraestructura_service().listar_grupos()
    except Exception as exc:
        logger.error("Error cargando grupos: %s", exc)
        _s["grupos"] = []


def _cargar_estudiantes(_s: dict) -> None:
    if not _s["grupo_id"]:
        _s["estudiantes"] = []
        return
    try:
        _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(_s["grupo_id"])
    except Exception as exc:
        logger.error("Error cargando estudiantes: %s", exc)
        _s["estudiantes"] = []


# ── Helpers de descarga ───────────────────────────────────────────────────────

def _descargar_boletin(estudiante_id: int, nombre: str, grupo_id: int, anio_id: int) -> None:
    try:
        svc = Container.informe_service()
        contenido = svc.generar_boletin_anual(estudiante_id, grupo_id, anio_id, "pdf")
        filename = f"boletin_anual_{nombre.replace(' ', '_')}_{anio_id}.pdf"
        ui.download(content=contenido, filename=filename)
    except ValueError as exc:
        ui.notify(f"Exportador no disponible: {exc}", type="negative")
    except Exception as exc:
        logger.error("Error generando boletín anual de %s: %s", nombre, exc, exc_info=True)
        ui.notify(f"Error al generar boletín anual de {nombre}.", type="negative")


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/informes/boletin-anual")
def boletin_anual_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _s["grupo_id"] = ctx.grupo_id
    _s["anio_id"] = ctx.anio_id
    _cargar_grupos(_s)
    if _s["grupo_id"]:
        _cargar_estudiantes(_s)

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.element("div").classes("andes-card q-mb-md"):
            ui.label("Seleccionar grupo y año").classes("text-subtitle1 text-weight-medium q-mb-md")

            with ui.element("div").classes("form-grid-2"):
                grupos_opts = {g.id: getattr(g, "nombre", str(g.id)) for g in _s["grupos"]}
                ui.select(
                    label="Grupo",
                    options=grupos_opts,
                    value=_s["grupo_id"],
                    on_change=lambda e: on_grupo_change(e.value),
                ).classes("w-full")

                ui.number(
                    label="Año lectivo",
                    value=_s["anio_id"],
                    min=2000,
                    max=2099,
                    precision=0,
                    on_change=lambda e: on_anio_change(int(e.value) if e.value else None),
                ).classes("w-full")

    @ui.refreshable
    def lista_refreshable() -> None:
        if not _s["grupo_id"] or not _s["anio_id"]:
            with ui.element("div").classes("andes-card text-center q-pa-xl"):
                ui.label("Selecciona un grupo y año para ver los estudiantes.").classes("text-caption")
            return

        if not _s["estudiantes"]:
            with ui.element("div").classes("andes-card text-center q-pa-xl"):
                ui.label("No hay estudiantes activos en este grupo.").classes("text-caption")
            return

        with ui.element("div").classes("andes-card"):
            with ui.row().classes("items-center justify-between q-mb-md"):
                ui.label(f"Estudiantes ({len(_s['estudiantes'])})").classes("text-subtitle1 text-weight-medium")
                btn_primary(
                    "Generar todos",
                    icon=Icons.EXPORT,
                    on_click=on_generar_todos,
                )

            for est in _s["estudiantes"]:
                nombre = f"{est.nombre} {est.apellido}"
                with ui.row().classes("items-center justify-between q-py-xs andes-table-row"):
                    ui.label(nombre).classes("text-body2")
                    btn_icon(
                        icon=Icons.EXPORT,
                        tooltip="Descargar PDF anual",
                        on_click=lambda e, eid=est.id, en=nombre: _descargar_boletin(
                            eid, en, _s["grupo_id"], _s["anio_id"]
                        ),
                    )

    def on_grupo_change(grupo_id) -> None:
        _s["grupo_id"] = grupo_id
        _cargar_estudiantes(_s)
        filtros_refreshable.refresh()
        lista_refreshable.refresh()

    def on_anio_change(anio_id) -> None:
        _s["anio_id"] = anio_id
        lista_refreshable.refresh()

    def on_generar_todos() -> None:
        if not _s["anio_id"]:
            ui.notify("Ingresa un año lectivo.", type="warning")
            return
        for est in _s["estudiantes"]:
            nombre = f"{est.nombre} {est.apellido}"
            _descargar_boletin(est.id, nombre, _s["grupo_id"], _s["anio_id"])

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            filtros_refreshable()
            lista_refreshable()

    app_layout(
        titulo_pagina="Boletines Anuales",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/informes/boletin-anual",
        contenido=contenido,
        ctx=ctx,
    )


__all__ = ["boletin_anual_page"]
