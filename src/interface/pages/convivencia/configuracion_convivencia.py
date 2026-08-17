"""
src/interface/pages/convivencia/configuracion_convivencia.py
============================================================
Vista unificada de Configuración de convivencia — ZECI Manager v2.0.

Fusiona las anteriores páginas de Categorías y Plantillas en un layout
side-by-side. Categorías (izquierda, flex:2) solo es visible y editable
para director/coordinador. Plantillas (derecha, flex:3) es accesible a
todos los roles de aula; profesores pueden crear y editar plantillas pero
no desactivarlas ni gestionar categorías.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Los DTOs se acceden a través del módulo de servicios.
  Solo usa Container (servicios) e imports de la capa de interfaz.

RBAC (resumen):
  Categorías (CRUD completo)   → director, coordinador
  Plantillas (crear/editar)    → director, coordinador, profesor
  Plantillas (desactivar)      → director, coordinador

Flujo:
  1. Guard de sesión → /login si no autenticado.
  2. Layout side-by-side: col-side=categorías, col-main=plantillas.
  3. Categorías solo se renderiza si rol in (director, coordinador).
  4. Botón Desactivar en plantillas solo visible a dir/coord.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    confirm_dialog,
    empty_state,
    form_dialog,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_danger, btn_icon, btn_primary
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.services.convivencia_service import NuevaCategoriaDTO, NuevaPlantillaDTO

logger = logging.getLogger("CONFIG_CONVIVENCIA")

_ROLES_DIRECTIVOS = ("director", "coordinador")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "categorias":   [],   # list[CategoriaObservacion]
        "plantillas":   [],   # list[PlantillaObservacion]
        "editando_cat": None, # CategoriaObservacion | None
        "editando_plt": None, # PlantillaObservacion | None
        "sel_cat":      None, # dict | None — fila seleccionada en el grid
        "sel_plt":      None, # dict | None — fila seleccionada en el grid de plantillas
    }


def _cargar_estado(_s: dict) -> None:
    _s["sel_cat"] = None  # resetear selecciones al recargar datos
    _s["sel_plt"] = None
    svc = Container.convivencia_service()
    try:
        _s["categorias"] = svc.listar_categorias(solo_activas=False)
    except Exception as exc:
        logger.error("Error cargando categorías: %s", exc)
        _s["categorias"] = []
    try:
        _s["plantillas"] = svc.listar_todas_plantillas()
    except Exception as exc:
        logger.error("Error cargando plantillas: %s", exc)
        _s["plantillas"] = []


def _opciones_categorias(_s: dict) -> dict:
    """Construye {None: 'Sin categoría', cat_id: nombre} para el select de plantillas."""
    opts: dict = {None: "Sin categoría"}
    for cat in _s["categorias"]:
        if getattr(cat, "activa", True):
            cat_id = getattr(cat, "id", None)
            nombre = getattr(cat, "nombre", "")
            if cat_id is not None:
                opts[cat_id] = nombre
    return opts


def _cat_nombre_por_id(_s: dict) -> dict:
    return {getattr(c, "id", None): getattr(c, "nombre", "") for c in _s["categorias"]}


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (convivencia_33)
def configuracion_convivencia_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    rol = getattr(ctx, "usuario_rol", None)
    es_directivo = rol in _ROLES_DIRECTIVOS

    _s = _estado_inicial()
    _cargar_estado(_s)

    # ── Handlers: categorías (solo dir/coord) ─────────────────────────────────

    def _abrir_nueva_categoria() -> None:
        _s["editando_cat"] = None
        form_dialog(
            titulo="Nueva categoría",
            campos=[
                {"key": "nombre", "label": "Nombre", "tipo": "text", "requerido": True},
                {"key": "es_comportamental", "label": "¿Es comportamental?", "tipo": "checkbox", "valor": False},
            ],
            on_submit=_crear_categoria,
            texto_submit="Guardar",
        )

    def _abrir_editar_categoria(cat) -> None:
        _s["editando_cat"] = cat
        form_dialog(
            titulo="Editar categoría",
            campos=[
                {"key": "nombre", "label": "Nombre", "tipo": "text",
                 "valor": getattr(cat, "nombre", ""), "requerido": True},
                {"key": "es_comportamental", "label": "¿Es comportamental?", "tipo": "checkbox",
                 "valor": getattr(cat, "es_comportamental", False)},
            ],
            on_submit=_actualizar_categoria,
            texto_submit="Guardar cambios",
        )

    def _crear_categoria(datos: dict) -> bool | None:
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            toast_warning("El nombre de la categoría es requerido.")
            return False
        try:
            dto = NuevaCategoriaDTO(nombre=nombre, es_comportamental=bool(datos.get("es_comportamental", False)))
            Container.convivencia_service().crear_categoria(dto)
            toast_success("Categoría creada.")
            _cargar_estado(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error creando categoría: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _actualizar_categoria(datos: dict) -> bool | None:
        cat = _s.get("editando_cat")
        if cat is None:
            toast_error("No hay categoría seleccionada.")
            return False
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            toast_warning("El nombre de la categoría es requerido.")
            return False
        try:
            dto = NuevaCategoriaDTO(nombre=nombre, es_comportamental=bool(datos.get("es_comportamental", False)))
            Container.convivencia_service().actualizar_categoria(getattr(cat, "id"), dto)
            toast_success("Categoría actualizada.")
            _cargar_estado(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error actualizando categoría: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _desactivar_categoria(cat_id: int) -> None:
        def _ejecutar() -> None:
            try:
                Container.convivencia_service().desactivar_categoria(cat_id)
                toast_success("Categoría desactivada.")
                _cargar_estado(_s)
                _contenido.refresh()
            except Exception as exc:
                logger.error("Error desactivando categoría %s: %s", cat_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Desactivar categoría",
            mensaje="¿Confirmas la desactivación? Los registros históricos no se verán afectados.",
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Handlers: plantillas (todos los roles AULA) ───────────────────────────

    def _abrir_nueva_plantilla() -> None:
        _s["editando_plt"] = None
        form_dialog(
            titulo="Nueva plantilla",
            campos=[
                {"key": "texto", "label": "Texto", "tipo": "textarea", "requerido": True,
                 "placeholder": "Texto de la plantilla (máx. 2000 caracteres)"},
                {"key": "categoria_id", "label": "Categoría", "tipo": "select",
                 "opciones": _opciones_categorias(_s), "valor": None},
            ],
            on_submit=_crear_plantilla,
            texto_submit="Guardar",
        )

    def _abrir_editar_plantilla(plantilla) -> None:
        _s["editando_plt"] = plantilla
        form_dialog(
            titulo="Editar plantilla",
            campos=[
                {"key": "texto", "label": "Texto", "tipo": "textarea",
                 "valor": getattr(plantilla, "texto", ""), "requerido": True,
                 "placeholder": "Texto de la plantilla (máx. 2000 caracteres)"},
                {"key": "categoria_id", "label": "Categoría", "tipo": "select",
                 "opciones": _opciones_categorias(_s),
                 "valor": getattr(plantilla, "categoria_id", None)},
            ],
            on_submit=_actualizar_plantilla,
            texto_submit="Guardar cambios",
        )

    def _crear_plantilla(datos: dict) -> bool | None:
        texto = str(datos.get("texto", "")).strip()
        if not texto:
            toast_warning("El texto de la plantilla es requerido.")
            return False
        try:
            dto = NuevaPlantillaDTO(texto=texto, categoria_id=datos.get("categoria_id"))
            Container.convivencia_service().crear_plantilla(
                dto,
                usuario_id=getattr(ctx, "usuario_id", None),
                usuario_rol=getattr(ctx, "usuario_rol", None),
            )
            toast_success("Plantilla creada.")
            _cargar_estado(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error creando plantilla: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _actualizar_plantilla(datos: dict) -> bool | None:
        plt = _s.get("editando_plt")
        if plt is None:
            toast_error("No hay plantilla seleccionada.")
            return False
        texto = str(datos.get("texto", "")).strip()
        if not texto:
            toast_warning("El texto de la plantilla es requerido.")
            return False
        try:
            dto = NuevaPlantillaDTO(texto=texto, categoria_id=datos.get("categoria_id"))
            Container.convivencia_service().actualizar_plantilla(
                getattr(plt, "id"),
                dto,
                usuario_id=getattr(ctx, "usuario_id", None),
                usuario_rol=getattr(ctx, "usuario_rol", None),
            )
            toast_success("Plantilla actualizada.")
            _cargar_estado(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error actualizando plantilla: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _desactivar_plantilla(plantilla_id: int) -> None:
        def _ejecutar() -> None:
            try:
                Container.convivencia_service().desactivar_plantilla(
                    plantilla_id,
                    usuario_id=getattr(ctx, "usuario_id", None),
                    usuario_rol=getattr(ctx, "usuario_rol", None),
                )
                toast_success("Plantilla desactivada.")
                _cargar_estado(_s)
                _contenido.refresh()
            except Exception as exc:
                logger.error("Error desactivando plantilla %s: %s", plantilla_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Desactivar plantilla",
            mensaje="¿Confirmas la desactivación? Los registros históricos no se verán afectados.",
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Refreshable ───────────────────────────────────────────────────────────

    @ui.refreshable
    def _contenido() -> None:
        ctx_actual = SessionContext.desde_storage() or ctx
        categorias = _s["categorias"]
        plantillas = _s["plantillas"]
        nombres_cat = _cat_nombre_por_id(_s)

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):
                with ui.element("div").classes("page-body"):

                    # ── Columna izquierda: Categorías (solo dir/coord) ─────────
                    if es_directivo:
                        with ui.element("div").classes("page-col-side"):
                            with ui.element("div").classes("panel-card"):
                                with ui.row().classes("panel-toolbar"):
                                    ui.label("Categorías").classes("panel-title")
                                    ui.element("div").classes("panel-toolbar-spacer")
                                    btn_primary(
                                        "Nueva categoría",
                                        on_click=_abrir_nueva_categoria,
                                        icon=Icons.ADD,
                                        size="sm",
                                    )

                                if not categorias:
                                    empty_state(
                                        icono="category",
                                        titulo="Sin categorías",
                                        descripcion="No hay categorías de observación registradas.",
                                        cta_label="Nueva categoría",
                                        cta_on_click=_abrir_nueva_categoria,
                                        cta_icono="add",
                                    )
                                else:
                                    filas_cat = [
                                        {
                                            "id":     getattr(cat, "id", None),
                                            "nombre": getattr(cat, "nombre", ""),
                                            "tipo":   "Comportamental" if getattr(cat, "es_comportamental", False) else "General",
                                            "estado": "Activa" if getattr(cat, "activa", True) else "Inactiva",
                                            "activa": getattr(cat, "activa", True),
                                        }
                                        for cat in categorias
                                    ]
                                    cat_grid = ui.aggrid({
                                        "columnDefs": [
                                            {
                                                "headerName": "Nombre",
                                                "field":      "nombre",
                                                "flex":       1,
                                                "resizable":  True,
                                                "sortable":   True,
                                            },
                                            {
                                                "headerName": "Tipo",
                                                "field":      "tipo",
                                                "width":      140,
                                                "resizable":  False,
                                                "sortable":   True,
                                            },
                                            {
                                                "headerName": "Estado",
                                                "field":      "estado",
                                                "width":      100,
                                                "resizable":  False,
                                                "sortable":   True,
                                            },
                                        ],
                                        "rowData":      filas_cat,
                                        "rowSelection": "single",
                                        "domLayout":    "autoHeight",
                                    }).classes("w-full")

                                    async def _on_cat_sel() -> None:
                                        rows = await cat_grid.get_selected_rows()
                                        _s["sel_cat"] = rows[0] if rows else None

                                    cat_grid.on("selectionChanged", _on_cat_sel)

                                    with ui.row().classes("gap-sm"):
                                        def _on_editar_cat_btn() -> None:
                                            sel = _s.get("sel_cat")
                                            if not sel:
                                                toast_warning("Selecciona una categoría de la tabla.")
                                                return
                                            cat_obj = next(
                                                (c for c in _s["categorias"] if getattr(c, "id", None) == sel.get("id")),
                                                None,
                                            )
                                            if cat_obj:
                                                _abrir_editar_categoria(cat_obj)

                                        def _on_desactivar_cat_btn() -> None:
                                            sel = _s.get("sel_cat")
                                            if not sel:
                                                toast_warning("Selecciona una categoría de la tabla.")
                                                return
                                            if not sel.get("activa"):
                                                toast_warning("La categoría ya está inactiva.")
                                                return
                                            _desactivar_categoria(sel["id"])

                                        btn_icon(Icons.EDIT, on_click=_on_editar_cat_btn, tooltip="Editar seleccionada")
                                        btn_danger("Desactivar", on_click=_on_desactivar_cat_btn, size="sm")

                    # ── Columna derecha: Plantillas (todos los roles AULA) ─────
                    with ui.element("div").classes("page-col-main"):
                        with ui.element("div").classes("panel-card"):
                            with ui.row().classes("panel-toolbar"):
                                ui.label("Plantillas").classes("panel-title")
                                ui.element("div").classes("panel-toolbar-spacer")
                                btn_primary(
                                    "Nueva plantilla",
                                    on_click=_abrir_nueva_plantilla,
                                    icon=Icons.ADD,
                                    size="sm",
                                )

                            if not plantillas:
                                empty_state(
                                    icono="description",
                                    titulo="Sin plantillas",
                                    descripcion="No hay plantillas de observación registradas.",
                                    cta_label="Nueva plantilla",
                                    cta_on_click=_abrir_nueva_plantilla,
                                    cta_icono="add",
                                )
                            else:
                                filas_plt = [
                                    {
                                        "id":       getattr(plt, "id", None),
                                        "texto":    getattr(plt, "texto", ""),
                                        "categoria": nombres_cat.get(getattr(plt, "categoria_id", None), "Sin categoría"),
                                        "usos":     getattr(plt, "uso_count", 0),
                                        "estado":   "Activa" if getattr(plt, "activa", True) else "Inactiva",
                                        "activa":   getattr(plt, "activa", True),
                                    }
                                    for plt in plantillas
                                ]
                                plt_grid = ui.aggrid({
                                    "columnDefs": [
                                        {
                                            "headerName": "Texto",
                                            "field":      "texto",
                                            "flex":       1,
                                            "resizable":  True,
                                            "sortable":   True,
                                            "wrapText":   True,
                                            "autoHeight": True,
                                            "cellClass":  "cell-multiline",
                                        },
                                        {
                                            "headerName": "Categoría",
                                            "field":      "categoria",
                                            "width":      140,
                                            "resizable":  False,
                                            "sortable":   True,
                                        },
                                        {
                                            "headerName": "Usos",
                                            "field":      "usos",
                                            "width":      75,
                                            "resizable":  False,
                                            "sortable":   True,
                                        },
                                        {
                                            "headerName": "Estado",
                                            "field":      "estado",
                                            "width":      100,
                                            "resizable":  False,
                                            "sortable":   True,
                                        },
                                    ],
                                    "rowData":      filas_plt,
                                    "rowSelection": "single",
                                    "domLayout":    "autoHeight",
                                }).classes("w-full")

                                async def _on_plt_sel() -> None:
                                    rows = await plt_grid.get_selected_rows()
                                    _s["sel_plt"] = rows[0] if rows else None

                                plt_grid.on("selectionChanged", _on_plt_sel)

                                with ui.row().classes("gap-sm"):
                                    def _on_editar_plt_btn() -> None:
                                        sel = _s.get("sel_plt")
                                        if not sel:
                                            toast_warning("Selecciona una plantilla de la tabla.")
                                            return
                                        plt_obj = next(
                                            (p for p in _s["plantillas"] if getattr(p, "id", None) == sel.get("id")),
                                            None,
                                        )
                                        if plt_obj:
                                            _abrir_editar_plantilla(plt_obj)

                                    def _on_desactivar_plt_btn() -> None:
                                        sel = _s.get("sel_plt")
                                        if not sel:
                                            toast_warning("Selecciona una plantilla de la tabla.")
                                            return
                                        if not sel.get("activa"):
                                            toast_warning("La plantilla ya está inactiva.")
                                            return
                                        _desactivar_plantilla(sel["id"])

                                    btn_icon(Icons.EDIT, on_click=_on_editar_plt_btn, tooltip="Editar seleccionada")
                                    if es_directivo:
                                        btn_danger("Desactivar", on_click=_on_desactivar_plt_btn, size="sm")

        app_layout(
            ctx_actual,
            contenido_pagina,
            page_titulo="Configuración de convivencia",
            page_icono="settings",
        )

    _contenido()


__all__ = ["configuracion_convivencia_page"]
