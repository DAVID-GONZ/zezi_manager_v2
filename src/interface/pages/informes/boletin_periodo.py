"""
src/interface/pages/informes/boletin_periodo.py
===============================================
Página de boletines individuales por periodo.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.

Flujo:
  1. Filtros: grupo + periodo.
  2. Al confirmar → carga lista de estudiantes del grupo.
  3. Por estudiante: botón "PDF" → InformeService.generar_boletin_periodo() → ui.download().
  4. "Generar todos" → itera la lista completa.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_ghost, btn_icon

logger = logging.getLogger("BOLETIN_PERIODO")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "grupo_id":    None,
        "periodo_id":  None,
        "grupos":      [],
        "periodos":    [],
        "estudiantes": [],
        "cargado":     False,
    }


def _cargar_grupos(_s: dict) -> None:
    try:
        _s["grupos"] = Container.infraestructura_service().listar_grupos()
    except Exception as exc:
        logger.error("Error cargando grupos: %s", exc)
        _s["grupos"] = []


def _cargar_periodos(ctx: SessionContext, _s: dict) -> None:
    try:
        anio_id = ctx.anio_id
        _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id) if anio_id else []
    except Exception as exc:
        logger.error("Error cargando periodos: %s", exc)
        _s["periodos"] = []


def _cargar_estudiantes(_s: dict) -> None:
    if not _s["grupo_id"]:
        _s["estudiantes"] = []
        return
    try:
        _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(_s["grupo_id"])
        _s["cargado"] = True
    except Exception as exc:
        logger.error("Error cargando estudiantes: %s", exc)
        _s["estudiantes"] = []


# ── Helpers de descarga ───────────────────────────────────────────────────────

def _descargar_boletin(estudiante_id: int, nombre: str, grupo_id: int, periodo_id: int) -> None:
    try:
        svc = Container.informe_service()
        contenido = svc.generar_boletin_periodo(estudiante_id, grupo_id, periodo_id, "pdf")
        filename = f"boletin_{nombre.replace(' ', '_')}_p{periodo_id}.pdf"
        ui.download(content=contenido, filename=filename)
    except ValueError as exc:
        ui.notify(f"Exportador no disponible: {exc}", type="negative")
    except Exception as exc:
        logger.error("Error generando boletín de %s: %s", nombre, exc, exc_info=True)
        ui.notify(f"Error al generar boletín de {nombre}.", type="negative")


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/informes/boletin-periodo")
def boletin_periodo_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _s["grupo_id"] = ctx.grupo_id
    _s["periodo_id"] = ctx.periodo_id
    _cargar_grupos(_s)
    _cargar_periodos(ctx, _s)
    if _s["grupo_id"]:
        _cargar_estudiantes(_s)

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.element("div").classes("andes-card q-mb-md"):
            ui.label("Seleccionar grupo y periodo").classes("text-subtitle1 text-weight-medium q-mb-md")

            with ui.element("div").classes("form-grid-2"):
                grupos_opts = {g.id: getattr(g, "nombre", str(g.id)) for g in _s["grupos"]}
                ui.select(
                    label="Grupo",
                    options=grupos_opts,
                    value=_s["grupo_id"],
                    on_change=lambda e: on_grupo_change(e.value),
                ).classes("w-full")

                per_opts = {p.id: getattr(p, "nombre", str(p.id)) for p in _s["periodos"]}
                ui.select(
                    label="Periodo",
                    options=per_opts,
                    value=_s["periodo_id"],
                    on_change=lambda e: on_periodo_change(e.value),
                ).classes("w-full")

    @ui.refreshable
    def lista_refreshable() -> None:
        if not _s["grupo_id"] or not _s["periodo_id"]:
            with ui.element("div").classes("andes-card text-center q-pa-xl"):
                ui.label("Selecciona un grupo y periodo para ver los estudiantes.").classes("text-caption")
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
                        tooltip="Descargar PDF",
                        on_click=lambda e, eid=est.id, en=nombre: _descargar_boletin(
                            eid, en, _s["grupo_id"], _s["periodo_id"]
                        ),
                    )

    def on_grupo_change(grupo_id) -> None:
        _s["grupo_id"] = grupo_id
        _cargar_estudiantes(_s)
        filtros_refreshable.refresh()
        lista_refreshable.refresh()

    def on_periodo_change(periodo_id) -> None:
        _s["periodo_id"] = periodo_id
        lista_refreshable.refresh()

    def on_generar_todos() -> None:
        if not _s["periodo_id"]:
            ui.notify("Selecciona un periodo.", type="warning")
            return
        for est in _s["estudiantes"]:
            nombre = f"{est.nombre} {est.apellido}"
            _descargar_boletin(est.id, nombre, _s["grupo_id"], _s["periodo_id"])

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            filtros_refreshable()
            lista_refreshable()

    app_layout(
        titulo_pagina="Boletines por Periodo",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/informes/boletin-periodo",
        contenido=contenido,
        ctx=ctx,
    )


__all__ = ["boletin_periodo_page"]
