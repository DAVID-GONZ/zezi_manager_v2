"""
src/interface/pages/informes/boletin_anual.py
=============================================
Página de boletines individuales anuales (consolidado de todos los periodos).

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.

Flujo:
  1. Filtros: grupo + año (role-aware: profesor ve solo sus grupos).
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
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_icon
from src.services.informe_service import merge_pdfs, merge_excels
from src.interface.design.components import skeleton_cards, toast_error, toast_warning

logger = logging.getLogger("BOLETIN_ANUAL")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "grupo_id":                   None,
        "anio_id":                    None,
        "grupos":                     [],
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


# ── Helpers de descarga ───────────────────────────────────────────────────────

def _boletin_pdf(estudiante_id: int, _s: dict) -> bytes:
    svc = Container.informe_service()
    return svc.generar_boletin_anual(
        estudiante_id,
        _s["grupo_id"],
        _s["anio_id"],
        "pdf",
        grupo_nombre=_grupo_nombre(_s),
    )


def _boletin_excel(estudiante_id: int, _s: dict) -> bytes:
    svc = Container.informe_service()
    return svc.generar_boletin_anual(
        estudiante_id,
        _s["grupo_id"],
        _s["anio_id"],
        "excel",
    )


def _descargar_pdf_individual(estudiante_id: int, nombre: str, _s: dict) -> None:
    try:
        contenido = _boletin_pdf(estudiante_id, _s)
        ui.download(src=contenido, filename=f"boletin_anual_{nombre.replace(' ', '_')}_{_s['anio_id']}.pdf")
    except ValueError as exc:
        toast_error(f"Sin datos o exportador no disponible: {exc}")
    except NotImplementedError:
        toast_warning("PDF no disponible. Instala weasyprint o reportlab.")
    except Exception as exc:
        logger.error("Error PDF %s: %s", nombre, exc, exc_info=True)
        toast_error(f"Error al generar boletín de {nombre}.")


def _descargar_excel_individual(estudiante_id: int, nombre: str, _s: dict) -> None:
    try:
        contenido = _boletin_excel(estudiante_id, _s)
        ui.download(src=contenido, filename=f"boletin_anual_{nombre.replace(' ', '_')}_{_s['anio_id']}.xlsx")
    except Exception as exc:
        logger.error("Error Excel %s: %s", nombre, exc, exc_info=True)
        toast_error(f"Error al exportar Excel de {nombre}.")


def _generar_todos_pdf(_s: dict) -> None:
    if not _s["anio_id"]:
        toast_warning("Ingresa un año lectivo.")
        return
    pdfs: list[bytes] = []
    errores: list[str] = []
    for est in _s["estudiantes"]:
        nombre = f"{est.nombre} {est.apellido}"
        try:
            pdfs.append(_boletin_pdf(est.id, _s))
        except Exception as exc:
            logger.error("Error PDF %s: %s", nombre, exc)
            errores.append(nombre)
    if not pdfs:
        toast_error("No se pudo generar ningún boletín.")
        return
    try:
        merged   = merge_pdfs(pdfs)
        grupo    = _grupo_nombre(_s)
        filename = f"boletines_anual_{grupo}_{_s['anio_id']}.pdf".replace(" ", "_")
        ui.download(src=merged, filename=filename)
        if errores:
            toast_warning(f"Fusionado con errores en: {', '.join(errores)}")
    except Exception as exc:
        logger.error("Error fusionando PDFs: %s", exc, exc_info=True)
        toast_error(f"Error al fusionar PDFs: {exc}")


def _generar_todos_excel(_s: dict) -> None:
    if not _s["anio_id"]:
        toast_warning("Ingresa un año lectivo.")
        return
    hojas: list[tuple[str, bytes]] = []
    errores: list[str] = []
    for est in _s["estudiantes"]:
        nombre = f"{est.nombre} {est.apellido}"
        try:
            excel_bytes = _boletin_excel(est.id, _s)
            hoja = f"{est.apellido} {est.nombre}"[:31]
            hojas.append((hoja, excel_bytes))
        except Exception as exc:
            logger.error("Error Excel %s: %s", nombre, exc)
            errores.append(nombre)
    if not hojas:
        toast_error("No se pudo generar ningún boletín.")
        return
    try:
        merged   = merge_excels(hojas)
        grupo    = _grupo_nombre(_s)
        filename = f"boletines_anual_{grupo}_{_s['anio_id']}.xlsx".replace(" ", "_")
        ui.download(src=merged, filename=filename)
        if errores:
            toast_warning(f"Generado con errores en: {', '.join(errores)}")
    except Exception as exc:
        logger.error("Error fusionando Excels: %s", exc, exc_info=True)
        toast_error(f"Error al fusionar Excel: {exc}")


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/informes/boletin-anual")
def boletin_anual_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _ROLES_VALIDOS = {"admin", "director", "coordinador", "profesor"}
    if ctx.usuario_rol not in _ROLES_VALIDOS:
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    _s = _estado_inicial()
    _s["grupo_id"] = ctx.grupo_id
    _s["anio_id"]  = ctx.anio_id
    _cargar_grupos(ctx, _s)
    if _s["grupo_id"]:
        _cargar_estudiantes(_s)

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.element("div").classes("andes-card q-mb-md"):
            ui.label("Seleccionar grupo y año").classes("text-subtitle1 text-weight-medium q-mb-md")
            with ui.element("div").classes("form-grid-2"):
                grupos_opts = {str(g.id): g.nombre or g.codigo for g in _s["grupos"]}
                ui.select(
                    label="Grupo",
                    options=grupos_opts or {"": "Sin grupos"},
                    value=str(_s["grupo_id"]) if _s["grupo_id"] is not None else None,
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
        if _s.get("generando"):
            with ui.element("div").classes("andes-card q-pa-md"):
                skeleton_cards(count=4)
            return

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
                with ui.row().classes("items-center justify-between q-py-xs andes-table-row"):
                    ui.label(nombre).classes("text-body2")
                    with ui.row().classes("gap-1"):
                        btn_icon(
                            icono="picture_as_pdf",
                            tooltip="Descargar PDF anual",
                            on_click=lambda e, eid=est.id, en=nombre: _descargar_pdf_individual(eid, en, _s),
                        )
                        btn_icon(
                            icono="table_view",
                            tooltip="Descargar Excel anual",
                            on_click=lambda e, eid=est.id, en=nombre: _descargar_excel_individual(eid, en, _s),
                        )

    def on_grupo_change(grupo_id) -> None:
        _s["grupo_id"] = int(grupo_id) if grupo_id is not None else None
        _cargar_estudiantes(_s)
        filtros_refreshable.refresh()
        lista_refreshable.refresh()

    def on_anio_change(anio_id) -> None:
        _s["anio_id"] = anio_id
        lista_refreshable.refresh()

    def on_context_change() -> None:
        nuevo_ctx = SessionContext.desde_storage()
        if nuevo_ctx:
            _s["grupo_id"] = nuevo_ctx.grupo_id
            _s["anio_id"]  = nuevo_ctx.anio_id
            _cargar_grupos(nuevo_ctx, _s)
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
        page_titulo="Boletines Anuales",
        on_context_change=on_context_change,
    )


__all__ = ["boletin_anual_page"]
