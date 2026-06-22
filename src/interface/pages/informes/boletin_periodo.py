"""
src/interface/pages/informes/boletin_periodo.py
===============================================
Página de boletines individuales por periodo.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.

Flujo:
  1. Filtros: grupo + periodo (role-aware: profesor ve solo sus grupos).
  2. Lista de estudiantes con descarga individual PDF / Excel.
  3. "Generar todos PDF" → un único PDF con todos los boletines fusionados.
  4. "Generar todos Excel" → un único libro con una hoja por estudiante.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_icon
from src.interface.design.components import empty_state, skeleton_cards, toast_error, toast_warning

logger = logging.getLogger("BOLETIN_PERIODO")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "grupo_id":                   None,
        "periodo_id":                 None,
        "grupos":                     [],
        "periodos":                   [],
        "estudiantes":                [],
        "todas_asignaciones_docente": [],
        "generando":                  False,
    }


def _cargar_grupos(ctx: SessionContext, _s: dict) -> None:
    if ctx.usuario_rol == "profesor":
        try:
            todas = Container.asignacion_service().listar_por_docente(ctx.usuario_id)
            _s["todas_asignaciones_docente"] = todas
            grupos_ids   = {a.grupo_id for a in todas}
            grupos_infra = Container.infraestructura_service().listar_grupos()
            _s["grupos"] = [g for g in grupos_infra if g.id in grupos_ids]
        except Exception as exc:
            logger.error("Error cargando grupos (profesor): %s", exc)
            _s["grupos"] = []
    else:
        _s["todas_asignaciones_docente"] = []
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
    except Exception as exc:
        logger.error("Error cargando estudiantes: %s", exc)
        _s["estudiantes"] = []


def _grupo_nombre(_s: dict) -> str:
    return next((g.nombre or g.codigo for g in _s["grupos"] if g.id == _s["grupo_id"]), "")


def _periodo_nombre(_s: dict) -> str:
    return next(
        (getattr(p, "nombre", str(p.id)) for p in _s["periodos"] if p.id == _s["periodo_id"]),
        "",
    )


# ── Helpers de descarga ───────────────────────────────────────────────────────

def _boletin_pdf(estudiante_id: int, _s: dict) -> bytes:
    svc = Container.informe_service()
    return svc.generar_boletin_periodo(
        estudiante_id,
        _s["grupo_id"],
        _s["periodo_id"],
        "pdf",
        grupo_nombre=_grupo_nombre(_s),
        periodo_nombre=_periodo_nombre(_s),
    )


def _boletin_excel(estudiante_id: int, _s: dict) -> bytes:
    svc = Container.informe_service()
    return svc.generar_boletin_periodo(
        estudiante_id,
        _s["grupo_id"],
        _s["periodo_id"],
        "excel",
    )


def _descargar_pdf_individual(estudiante_id: int, nombre: str, _s: dict) -> None:
    try:
        contenido = _boletin_pdf(estudiante_id, _s)
        ui.download(src=contenido, filename=f"boletin_{nombre.replace(' ', '_')}_p{_s['periodo_id']}.pdf")
    except NotImplementedError:
        toast_warning("PDF no disponible. Instala weasyprint o reportlab.")
    except Exception as exc:
        logger.error("Error PDF %s: %s", nombre, exc, exc_info=True)
        toast_error(f"Error al generar boletín de {nombre}.")


def _descargar_excel_individual(estudiante_id: int, nombre: str, _s: dict) -> None:
    try:
        contenido = _boletin_excel(estudiante_id, _s)
        ui.download(src=contenido, filename=f"boletin_{nombre.replace(' ', '_')}_p{_s['periodo_id']}.xlsx")
    except Exception as exc:
        logger.error("Error Excel %s: %s", nombre, exc, exc_info=True)
        toast_error(f"Error al exportar Excel de {nombre}.")


def _generar_todos(_s: dict, formato: str, ext: str) -> None:
    if not _s["periodo_id"]:
        toast_warning("Selecciona un periodo.")
        return
    try:
        resultado = Container.informe_service().generar_boletines_grupo(
            grupo_id=_s["grupo_id"],
            periodo_id=_s["periodo_id"],
            formato=formato,
            grupo_nombre=_grupo_nombre(_s),
            periodo_nombre=_periodo_nombre(_s),
        )
    except Exception as exc:
        logger.error("Error generando boletines (%s): %s", formato, exc, exc_info=True)
        toast_error(f"Error al generar boletines: {exc}")
        return
    if not resultado.contenido:
        toast_error("No se pudo generar ningún boletín.")
        return
    grupo = _grupo_nombre(_s)
    per   = _periodo_nombre(_s)
    filename = f"boletines_{grupo}_{per}_p{_s['periodo_id']}.{ext}".replace(" ", "_")
    ui.download(src=resultado.contenido, filename=filename)
    if resultado.errores:
        toast_warning(f"Generado con errores en: {', '.join(resultado.errores)}")


def _generar_todos_pdf(_s: dict) -> None:
    _generar_todos(_s, "pdf", "pdf")


def _generar_todos_excel(_s: dict) -> None:
    _generar_todos(_s, "excel", "xlsx")


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def boletin_periodo_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _s["grupo_id"]   = ctx.grupo_id
    _s["periodo_id"] = ctx.periodo_id
    _cargar_grupos(ctx, _s)
    _cargar_periodos(ctx, _s)
    if _s["grupo_id"]:
        _cargar_estudiantes(_s)

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.element("div").classes("andes-card u-mb-md"):
            ui.label("Seleccionar grupo y periodo").classes("text-subtitle1 text-weight-medium u-mb-md")
            with ui.element("div").classes("form-grid-2"):
                grupos_opts = {str(g.id): g.nombre or g.codigo for g in _s["grupos"]}
                ui.select(
                    label="Grupo",
                    options=grupos_opts or {"": "Sin grupos"},
                    value=str(_s["grupo_id"]) if _s["grupo_id"] is not None else None,
                    on_change=lambda e: on_grupo_change(e.value),
                ).classes("w-full")

                per_opts = {str(p.id): getattr(p, "nombre", str(p.id)) for p in _s["periodos"]}
                ui.select(
                    label="Periodo",
                    options=per_opts or {"": "Sin periodos"},
                    value=str(_s["periodo_id"]) if _s["periodo_id"] is not None else None,
                    on_change=lambda e: on_periodo_change(e.value),
                ).classes("w-full")

    @ui.refreshable
    def lista_refreshable() -> None:
        if _s.get("generando"):
            with ui.element("div").classes("andes-card u-pa-md"):
                skeleton_cards(count=4)
            return

        if not _s["grupo_id"] or not _s["periodo_id"]:
            empty_state(
                titulo="Selecciona grupo y periodo",
                descripcion="Elige un grupo y un periodo para ver los estudiantes.",
            )
            return

        if not _s["estudiantes"]:
            empty_state(
                titulo="Sin estudiantes",
                descripcion="No hay estudiantes activos en este grupo.",
            )
            return

        with ui.element("div").classes("andes-card"):
            with ui.row().classes("items-center justify-between u-mb-md"):
                ui.label(f"Estudiantes ({len(_s['estudiantes'])})").classes("text-subtitle1 text-weight-medium")
                with ui.row().classes("gap-2"):
                    async def _generar_pdf_masivo():
                        import asyncio
                        _s["generando"] = True
                        lista_refreshable.refresh()
                        await asyncio.sleep(0)
                        _generar_todos_pdf(_s)
                        _s["generando"] = False
                        lista_refreshable.refresh()

                    async def _generar_excel_masivo():
                        import asyncio
                        _s["generando"] = True
                        lista_refreshable.refresh()
                        await asyncio.sleep(0)
                        _generar_todos_excel(_s)
                        _s["generando"] = False
                        lista_refreshable.refresh()

                    btn_primary(
                        "Todos PDF",
                        icon="picture_as_pdf",
                        on_click=_generar_pdf_masivo,
                    )
                    btn_secondary(
                        "Todos Excel",
                        icon="table_view",
                        on_click=_generar_excel_masivo,
                    )

            for est in _s["estudiantes"]:
                nombre = f"{est.nombre} {est.apellido}"
                with ui.row().classes("items-center justify-between u-py-xs andes-table-row"):
                    ui.label(nombre).classes("text-body2")
                    with ui.row().classes("gap-1"):
                        btn_icon(
                            icono="picture_as_pdf",
                            tooltip="Descargar PDF",
                            on_click=lambda e, eid=est.id, en=nombre: _descargar_pdf_individual(eid, en, _s),
                        )
                        btn_icon(
                            icono="table_view",
                            tooltip="Descargar Excel",
                            on_click=lambda e, eid=est.id, en=nombre: _descargar_excel_individual(eid, en, _s),
                        )

    def on_grupo_change(grupo_id) -> None:
        _s["grupo_id"] = int(grupo_id) if grupo_id is not None else None
        _cargar_estudiantes(_s)
        filtros_refreshable.refresh()
        lista_refreshable.refresh()

    def on_periodo_change(periodo_id) -> None:
        _s["periodo_id"] = int(periodo_id) if periodo_id is not None else None
        lista_refreshable.refresh()

    def on_context_change() -> None:
        nuevo_ctx = SessionContext.desde_storage()
        if nuevo_ctx:
            _s["grupo_id"]   = nuevo_ctx.grupo_id
            _s["periodo_id"] = nuevo_ctx.periodo_id
            _cargar_grupos(nuevo_ctx, _s)
            _cargar_periodos(nuevo_ctx, _s)
            if _s["grupo_id"]:
                _cargar_estudiantes(_s)
        filtros_refreshable.refresh()
        lista_refreshable.refresh()

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            filtros_refreshable()
            lista_refreshable()

    app_layout(
        ctx, contenido,
        page_titulo="Boletines por Periodo",
        on_context_change=on_context_change,
    )


__all__ = ["boletin_periodo_page"]
