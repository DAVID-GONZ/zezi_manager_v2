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
from src.interface.presenters.convivencia.configuracion_convivencia_presenter import (
    ConfiguracionConvivenciaPresenter,
)
from src.services.convivencia_service import (
    NuevaCategoriaDTO,
    NuevaMedidaPedagogicaDTO,
    NuevaPlantillaDTO,
    NuevoTipoSituacionDTO,
)

logger = logging.getLogger("CONFIG_CONVIVENCIA")

_ROLES_DIRECTIVOS = ("director", "coordinador")


# ── Estado ────────────────────────────────────────────────────────────────────


def _estado_inicial() -> dict:
    return {
        "categorias": [],  # list[CategoriaObservacion]
        "plantillas": [],  # list[PlantillaObservacion]
        "tipos_situacion": [],  # list[TipoSituacion]
        "medidas": [],  # list[MedidaPedagogica]
        "editando_cat": None,  # CategoriaObservacion | None
        "editando_plt": None,  # PlantillaObservacion | None
        "editando_tipo": None,  # TipoSituacion | None
        "editando_medida": None,  # MedidaPedagogica | None
        "sel_cat": None,  # dict | None — fila seleccionada en el grid
        "sel_plt": None,  # dict | None — fila seleccionada en el grid de plantillas
        "sel_tipo": None,  # dict | None — fila seleccionada en el grid de tipos
        "sel_medida": None,  # dict | None — fila seleccionada en el grid de medidas
    }


def _cargar_estado(_s: dict) -> None:
    _s["sel_cat"] = None  # resetear selecciones al recargar datos
    _s["sel_plt"] = None
    _s["sel_tipo"] = None
    _s["sel_medida"] = None
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
    try:
        _s["tipos_situacion"] = svc.listar_tipos_situacion(solo_activas=False)
    except Exception as exc:
        logger.error("Error cargando tipos de situación: %s", exc)
        _s["tipos_situacion"] = []
    try:
        _s["medidas"] = svc.listar_medidas_pedagogicas(solo_activas=False)
    except Exception as exc:
        logger.error("Error cargando medidas pedagógicas: %s", exc)
        _s["medidas"] = []


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

    presenter = ConfiguracionConvivenciaPresenter()
    _s = presenter.estado  # misma referencia: los refreshables leen el estado del presenter
    _cargar_estado(_s)

    # ── Handlers: categorías (solo dir/coord) ─────────────────────────────────

    def _abrir_nueva_categoria() -> None:
        _s["editando_cat"] = None
        form_dialog(
            titulo="Nueva categoría",
            campos=[
                {"key": "nombre", "label": "Nombre", "tipo": "text", "requerido": True},
                {
                    "key": "es_comportamental",
                    "label": "¿Es comportamental?",
                    "tipo": "checkbox",
                    "valor": False,
                },
            ],
            on_submit=_crear_categoria,
            texto_submit="Guardar",
        )

    def _abrir_editar_categoria(cat) -> None:
        _s["editando_cat"] = cat
        form_dialog(
            titulo="Editar categoría",
            campos=[
                {
                    "key": "nombre",
                    "label": "Nombre",
                    "tipo": "text",
                    "valor": getattr(cat, "nombre", ""),
                    "requerido": True,
                },
                {
                    "key": "es_comportamental",
                    "label": "¿Es comportamental?",
                    "tipo": "checkbox",
                    "valor": getattr(cat, "es_comportamental", False),
                },
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
            dto = NuevaCategoriaDTO(
                nombre=nombre, es_comportamental=bool(datos.get("es_comportamental", False))
            )
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
            dto = NuevaCategoriaDTO(
                nombre=nombre, es_comportamental=bool(datos.get("es_comportamental", False))
            )
            Container.convivencia_service().actualizar_categoria(cat.id, dto)
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

    # ── Handlers: tipos de situación (solo dir/coord) ────────────────────────

    _OPCIONES_NIVEL = {1: "Tipo I - Conflictos", 2: "Tipo II - Agresión/Acoso", 3: "Tipo III - Presuntos delitos"}

    def _abrir_nuevo_tipo() -> None:
        _s["editando_tipo"] = None
        form_dialog(
            titulo="Nuevo tipo de situación",
            campos=[
                {"key": "nombre", "label": "Nombre", "tipo": "text", "requerido": True},
                {
                    "key": "nivel",
                    "label": "Nivel",
                    "tipo": "select",
                    "opciones": _OPCIONES_NIVEL,
                    "valor": 1,
                },
                {"key": "descripcion", "label": "Descripción", "tipo": "textarea"},
                {"key": "protocolo", "label": "Protocolo de atención", "tipo": "textarea"},
            ],
            on_submit=_crear_tipo,
            texto_submit="Guardar",
        )

    def _abrir_editar_tipo(tipo) -> None:
        _s["editando_tipo"] = tipo
        form_dialog(
            titulo="Editar tipo de situación",
            campos=[
                {
                    "key": "nombre",
                    "label": "Nombre",
                    "tipo": "text",
                    "valor": getattr(tipo, "nombre", ""),
                    "requerido": True,
                },
                {
                    "key": "nivel",
                    "label": "Nivel",
                    "tipo": "select",
                    "opciones": _OPCIONES_NIVEL,
                    "valor": getattr(tipo, "nivel", 1),
                },
                {
                    "key": "descripcion",
                    "label": "Descripción",
                    "tipo": "textarea",
                    "valor": getattr(tipo, "descripcion", "") or "",
                },
                {
                    "key": "protocolo",
                    "label": "Protocolo de atención",
                    "tipo": "textarea",
                    "valor": getattr(tipo, "protocolo", "") or "",
                },
            ],
            on_submit=_actualizar_tipo,
            texto_submit="Guardar cambios",
        )

    def _crear_tipo(datos: dict) -> bool | None:
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            toast_warning("El nombre es requerido.")
            return False
        try:
            dto = NuevoTipoSituacionDTO(
                nombre=nombre,
                nivel=int(datos.get("nivel", 1)),
                descripcion=str(datos.get("descripcion", "")).strip() or None,
                protocolo=str(datos.get("protocolo", "")).strip() or None,
            )
            Container.convivencia_service().crear_tipo_situacion(
                dto, usuario_rol=getattr(ctx, "usuario_rol", None)
            )
            toast_success("Tipo de situación creado.")
            _cargar_estado(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error creando tipo situación: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _actualizar_tipo(datos: dict) -> bool | None:
        tipo = _s.get("editando_tipo")
        if tipo is None:
            toast_error("No hay tipo seleccionado.")
            return False
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            toast_warning("El nombre es requerido.")
            return False
        try:
            dto = NuevoTipoSituacionDTO(
                nombre=nombre,
                nivel=int(datos.get("nivel", 1)),
                descripcion=str(datos.get("descripcion", "")).strip() or None,
                protocolo=str(datos.get("protocolo", "")).strip() or None,
            )
            Container.convivencia_service().actualizar_tipo_situacion(
                tipo.id, dto, usuario_rol=getattr(ctx, "usuario_rol", None)
            )
            toast_success("Tipo de situación actualizado.")
            _cargar_estado(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error actualizando tipo situación: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _desactivar_tipo(tipo_id: int) -> None:
        def _ejecutar() -> None:
            try:
                Container.convivencia_service().desactivar_tipo_situacion(
                    tipo_id, usuario_rol=getattr(ctx, "usuario_rol", None)
                )
                toast_success("Tipo de situación desactivado.")
                _cargar_estado(_s)
                _contenido.refresh()
            except Exception as exc:
                logger.error("Error desactivando tipo %s: %s", tipo_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Desactivar tipo de situación",
            mensaje="¿Confirmas? Los registros históricos no se verán afectados.",
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Handlers: medidas pedagógicas (solo dir/coord) ───────────────────────

    _OPCIONES_NIVEL_MEDIDA = {1: "Nivel I - Tipo I", 2: "Nivel II - Tipo II+", 3: "Nivel III - Tipo III"}

    def _abrir_nueva_medida() -> None:
        _s["editando_medida"] = None
        form_dialog(
            titulo="Nueva medida pedagógica",
            campos=[
                {"key": "nombre", "label": "Nombre", "tipo": "text", "requerido": True},
                {
                    "key": "nivel_minimo",
                    "label": "Nivel mínimo aplicable",
                    "tipo": "select",
                    "opciones": _OPCIONES_NIVEL_MEDIDA,
                    "valor": 1,
                },
                {"key": "descripcion", "label": "Descripción", "tipo": "textarea"},
            ],
            on_submit=_crear_medida,
            texto_submit="Guardar",
        )

    def _abrir_editar_medida(medida) -> None:
        _s["editando_medida"] = medida
        form_dialog(
            titulo="Editar medida pedagógica",
            campos=[
                {
                    "key": "nombre",
                    "label": "Nombre",
                    "tipo": "text",
                    "valor": getattr(medida, "nombre", ""),
                    "requerido": True,
                },
                {
                    "key": "nivel_minimo",
                    "label": "Nivel mínimo aplicable",
                    "tipo": "select",
                    "opciones": _OPCIONES_NIVEL_MEDIDA,
                    "valor": getattr(medida, "nivel_minimo", 1),
                },
                {
                    "key": "descripcion",
                    "label": "Descripción",
                    "tipo": "textarea",
                    "valor": getattr(medida, "descripcion", "") or "",
                },
            ],
            on_submit=_actualizar_medida,
            texto_submit="Guardar cambios",
        )

    def _crear_medida(datos: dict) -> bool | None:
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            toast_warning("El nombre es requerido.")
            return False
        try:
            dto = NuevaMedidaPedagogicaDTO(
                nombre=nombre,
                nivel_minimo=int(datos.get("nivel_minimo", 1)),
                descripcion=str(datos.get("descripcion", "")).strip() or None,
            )
            Container.convivencia_service().crear_medida_pedagogica(
                dto, usuario_rol=getattr(ctx, "usuario_rol", None)
            )
            toast_success("Medida pedagógica creada.")
            _cargar_estado(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error creando medida: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _actualizar_medida(datos: dict) -> bool | None:
        medida = _s.get("editando_medida")
        if medida is None:
            toast_error("No hay medida seleccionada.")
            return False
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            toast_warning("El nombre es requerido.")
            return False
        try:
            dto = NuevaMedidaPedagogicaDTO(
                nombre=nombre,
                nivel_minimo=int(datos.get("nivel_minimo", 1)),
                descripcion=str(datos.get("descripcion", "")).strip() or None,
            )
            Container.convivencia_service().actualizar_medida_pedagogica(
                medida.id, dto, usuario_rol=getattr(ctx, "usuario_rol", None)
            )
            toast_success("Medida pedagógica actualizada.")
            _cargar_estado(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error actualizando medida: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _desactivar_medida(medida_id: int) -> None:
        def _ejecutar() -> None:
            try:
                Container.convivencia_service().desactivar_medida_pedagogica(
                    medida_id, usuario_rol=getattr(ctx, "usuario_rol", None)
                )
                toast_success("Medida pedagógica desactivada.")
                _cargar_estado(_s)
                _contenido.refresh()
            except Exception as exc:
                logger.error("Error desactivando medida %s: %s", medida_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Desactivar medida pedagógica",
            mensaje="¿Confirmas? Los registros históricos no se verán afectados.",
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Handlers: plantillas (todos los roles AULA) ───────────────────────────

    def _abrir_nueva_plantilla() -> None:
        _s["editando_plt"] = None
        form_dialog(
            titulo="Nueva plantilla",
            campos=[
                {
                    "key": "texto",
                    "label": "Texto",
                    "tipo": "textarea",
                    "requerido": True,
                    "placeholder": "Texto de la plantilla (máx. 2000 caracteres)",
                },
                {
                    "key": "categoria_id",
                    "label": "Categoría",
                    "tipo": "select",
                    "opciones": presenter.opciones_categorias(),
                    "valor": None,
                },
            ],
            on_submit=_crear_plantilla,
            texto_submit="Guardar",
        )

    def _abrir_editar_plantilla(plantilla) -> None:
        _s["editando_plt"] = plantilla
        form_dialog(
            titulo="Editar plantilla",
            campos=[
                {
                    "key": "texto",
                    "label": "Texto",
                    "tipo": "textarea",
                    "valor": getattr(plantilla, "texto", ""),
                    "requerido": True,
                    "placeholder": "Texto de la plantilla (máx. 2000 caracteres)",
                },
                {
                    "key": "categoria_id",
                    "label": "Categoría",
                    "tipo": "select",
                    "opciones": presenter.opciones_categorias(),
                    "valor": getattr(plantilla, "categoria_id", None),
                },
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
                plt.id,
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
                logger.error(
                    "Error desactivando plantilla %s: %s", plantilla_id, exc, exc_info=True
                )
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
        nombres_cat = presenter.cat_nombre_por_id()

        def contenido_pagina() -> None:
            tipos_situacion = _s["tipos_situacion"]
            with ui.element("div").classes("page-stack"):
                layout_cls = "config-grid" if es_directivo else "page-body"
                with ui.element("div").classes(layout_cls):
                    # ── Columna izquierda: Categorías (solo dir/coord) ─────────
                    if es_directivo:
                        with ui.element("div").classes("page-col-side").style("order: 1"):
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
                                            "id": getattr(cat, "id", None),
                                            "nombre": getattr(cat, "nombre", ""),
                                            "tipo": "Comportamental"
                                            if getattr(cat, "es_comportamental", False)
                                            else "General",
                                            "estado": "Activa"
                                            if getattr(cat, "activa", True)
                                            else "Inactiva",
                                            "activa": getattr(cat, "activa", True),
                                        }
                                        for cat in categorias
                                    ]
                                    with ui.element("div").classes("config-scroll"):
                                        cat_grid = ui.aggrid(
                                            {
                                                "columnDefs": [
                                                    {
                                                        "headerName": "Nombre",
                                                        "field": "nombre",
                                                        "flex": 1,
                                                        "resizable": True,
                                                        "sortable": True,
                                                    },
                                                    {
                                                        "headerName": "Tipo",
                                                        "field": "tipo",
                                                        "width": 110,
                                                        "resizable": False,
                                                        "sortable": True,
                                                    },
                                                    {
                                                        "headerName": "Estado",
                                                        "field": "estado",
                                                        "width": 100,
                                                        "resizable": False,
                                                        "sortable": True,
                                                    },
                                                ],
                                                "rowData": filas_cat,
                                                "rowSelection": "single",
                                                "domLayout": "autoHeight",
                                            }
                                        ).classes("w-full")

                                    async def _on_cat_sel() -> None:
                                        rows = await cat_grid.get_selected_rows()
                                        _s["sel_cat"] = rows[0] if rows else None

                                    cat_grid.on("selectionChanged", _on_cat_sel)

                                    with ui.row().classes("gap-sm").style("flex-wrap: wrap; align-items: center"):

                                        def _on_editar_cat_btn() -> None:
                                            sel = _s.get("sel_cat")
                                            if not sel:
                                                toast_warning(
                                                    "Selecciona una categoría de la tabla."
                                                )
                                                return
                                            cat_obj = next(
                                                (
                                                    c
                                                    for c in _s["categorias"]
                                                    if getattr(c, "id", None) == sel.get("id")
                                                ),
                                                None,
                                            )
                                            if cat_obj:
                                                _abrir_editar_categoria(cat_obj)

                                        def _on_desactivar_cat_btn() -> None:
                                            sel = _s.get("sel_cat")
                                            if not sel:
                                                toast_warning(
                                                    "Selecciona una categoría de la tabla."
                                                )
                                                return
                                            if not sel.get("activa"):
                                                toast_warning("La categoría ya está inactiva.")
                                                return
                                            _desactivar_categoria(sel["id"])

                                        btn_icon(
                                            Icons.EDIT,
                                            on_click=_on_editar_cat_btn,
                                            tooltip="Editar seleccionada",
                                        )
                                        btn_danger(
                                            "Desactivar", on_click=_on_desactivar_cat_btn, size="sm"
                                        )

                    # ── Tipos de situación (solo dir/coord) ───────────────────
                    if es_directivo:
                        with ui.element("div").classes("page-col-main").style("order: 3"):
                            with ui.element("div").classes("panel-card"):
                                with ui.row().classes("panel-toolbar"):
                                    ui.label("Tipos de situación (Ley 1620)").classes("panel-title")
                                    ui.element("div").classes("panel-toolbar-spacer")
                                    btn_primary(
                                        "Nuevo tipo",
                                        on_click=_abrir_nuevo_tipo,
                                        icon=Icons.ADD,
                                        size="sm",
                                    )

                                if not tipos_situacion:
                                    empty_state(
                                        icono="gavel",
                                        titulo="Sin tipos de situación",
                                        descripcion="No hay tipos de situación registrados.",
                                        cta_label="Nuevo tipo",
                                        cta_on_click=_abrir_nuevo_tipo,
                                        cta_icono="add",
                                    )
                                else:
                                    filas_tipo = [
                                        {
                                            "id": getattr(t, "id", None),
                                            "nombre": getattr(t, "nombre", ""),
                                            "nivel": getattr(t, "nivel", 1),
                                            "estado": "Activo"
                                            if getattr(t, "activa", True)
                                            else "Inactivo",
                                            "activa": getattr(t, "activa", True),
                                        }
                                        for t in tipos_situacion
                                    ]
                                    with ui.element("div").classes("config-scroll"):
                                        tipo_grid = ui.aggrid(
                                            {
                                                "columnDefs": [
                                                    {
                                                        "headerName": "Nombre",
                                                        "field": "nombre",
                                                        "flex": 1,
                                                        "resizable": True,
                                                        "sortable": True,
                                                    },
                                                    {
                                                        "headerName": "Nivel",
                                                        "field": "nivel",
                                                        "width": 80,
                                                        "resizable": False,
                                                        "sortable": True,
                                                    },
                                                    {
                                                        "headerName": "Estado",
                                                        "field": "estado",
                                                        "width": 100,
                                                        "resizable": False,
                                                        "sortable": True,
                                                    },
                                                ],
                                                "rowData": filas_tipo,
                                                "rowSelection": "single",
                                                "domLayout": "autoHeight",
                                            }
                                        ).classes("w-full")

                                    async def _on_tipo_sel() -> None:
                                        rows = await tipo_grid.get_selected_rows()
                                        _s["sel_tipo"] = rows[0] if rows else None

                                    tipo_grid.on("selectionChanged", _on_tipo_sel)

                                    with ui.row().classes("gap-sm").style("flex-wrap: wrap; align-items: center"):

                                        def _on_editar_tipo_btn() -> None:
                                            sel = _s.get("sel_tipo")
                                            if not sel:
                                                toast_warning("Selecciona un tipo de la tabla.")
                                                return
                                            tipo_obj = next(
                                                (
                                                    t
                                                    for t in _s["tipos_situacion"]
                                                    if getattr(t, "id", None) == sel.get("id")
                                                ),
                                                None,
                                            )
                                            if tipo_obj:
                                                _abrir_editar_tipo(tipo_obj)

                                        def _on_desactivar_tipo_btn() -> None:
                                            sel = _s.get("sel_tipo")
                                            if not sel:
                                                toast_warning("Selecciona un tipo de la tabla.")
                                                return
                                            if not sel.get("activa"):
                                                toast_warning("El tipo ya está inactivo.")
                                                return
                                            _desactivar_tipo(sel["id"])

                                        btn_icon(
                                            Icons.EDIT,
                                            on_click=_on_editar_tipo_btn,
                                            tooltip="Editar seleccionado",
                                        )
                                        btn_danger(
                                            "Desactivar",
                                            on_click=_on_desactivar_tipo_btn,
                                            size="sm",
                                        )

                    # ── Medidas pedagógicas (solo dir/coord) ──────────────────
                    if es_directivo:
                        medidas = _s["medidas"]
                        with ui.element("div").classes("page-col-main").style("order: 4"):
                            with ui.element("div").classes("panel-card"):
                                with ui.row().classes("panel-toolbar"):
                                    ui.label("Medidas pedagógicas (Decreto 1965)").classes("panel-title")
                                    ui.element("div").classes("panel-toolbar-spacer")
                                    btn_primary(
                                        "Nueva medida",
                                        on_click=_abrir_nueva_medida,
                                        icon=Icons.ADD,
                                        size="sm",
                                    )

                                if not medidas:
                                    empty_state(
                                        icono="gavel",
                                        titulo="Sin medidas pedagógicas",
                                        descripcion="No hay medidas pedagógicas registradas.",
                                        cta_label="Nueva medida",
                                        cta_on_click=_abrir_nueva_medida,
                                        cta_icono="add",
                                    )
                                else:
                                    filas_medida = [
                                        {
                                            "id": getattr(m, "id", None),
                                            "nombre": getattr(m, "nombre", ""),
                                            "nivel_minimo": getattr(m, "nivel_minimo", 1),
                                            "estado": "Activa"
                                            if getattr(m, "activa", True)
                                            else "Inactiva",
                                            "activa": getattr(m, "activa", True),
                                        }
                                        for m in medidas
                                    ]
                                    with ui.element("div").classes("config-scroll"):
                                        medida_grid = ui.aggrid(
                                            {
                                                "columnDefs": [
                                                    {
                                                        "headerName": "Nombre",
                                                        "field": "nombre",
                                                        "flex": 1,
                                                        "resizable": True,
                                                        "sortable": True,
                                                    },
                                                    {
                                                        "headerName": "Nivel mín.",
                                                        "field": "nivel_minimo",
                                                        "width": 100,
                                                        "resizable": False,
                                                        "sortable": True,
                                                    },
                                                    {
                                                        "headerName": "Estado",
                                                        "field": "estado",
                                                        "width": 100,
                                                        "resizable": False,
                                                        "sortable": True,
                                                    },
                                                ],
                                                "rowData": filas_medida,
                                                "rowSelection": "single",
                                                "domLayout": "autoHeight",
                                            }
                                        ).classes("w-full")

                                    async def _on_medida_sel() -> None:
                                        rows = await medida_grid.get_selected_rows()
                                        _s["sel_medida"] = rows[0] if rows else None

                                    medida_grid.on("selectionChanged", _on_medida_sel)

                                    with ui.row().classes("gap-sm").style("flex-wrap: wrap; align-items: center"):

                                        def _on_editar_medida_btn() -> None:
                                            sel = _s.get("sel_medida")
                                            if not sel:
                                                toast_warning("Selecciona una medida de la tabla.")
                                                return
                                            medida_obj = next(
                                                (
                                                    m
                                                    for m in _s["medidas"]
                                                    if getattr(m, "id", None) == sel.get("id")
                                                ),
                                                None,
                                            )
                                            if medida_obj:
                                                _abrir_editar_medida(medida_obj)

                                        def _on_desactivar_medida_btn() -> None:
                                            sel = _s.get("sel_medida")
                                            if not sel:
                                                toast_warning("Selecciona una medida de la tabla.")
                                                return
                                            if not sel.get("activa"):
                                                toast_warning("La medida ya está inactiva.")
                                                return
                                            _desactivar_medida(sel["id"])

                                        btn_icon(
                                            Icons.EDIT,
                                            on_click=_on_editar_medida_btn,
                                            tooltip="Editar seleccionada",
                                        )
                                        btn_danger(
                                            "Desactivar",
                                            on_click=_on_desactivar_medida_btn,
                                            size="sm",
                                        )

                    # ── Plantillas (todos los roles AULA) ─────
                    with ui.element("div").classes("page-col-main").style("order: 2"):
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
                                        "id": getattr(plt, "id", None),
                                        "texto": getattr(plt, "texto", ""),
                                        "categoria": nombres_cat.get(
                                            getattr(plt, "categoria_id", None), "Sin categoría"
                                        ),
                                        "usos": getattr(plt, "uso_count", 0),
                                        "estado": "Activa"
                                        if getattr(plt, "activa", True)
                                        else "Inactiva",
                                        "activa": getattr(plt, "activa", True),
                                    }
                                    for plt in plantillas
                                ]
                                with ui.element("div").classes("config-scroll"):
                                    plt_grid = ui.aggrid(
                                        {
                                            "columnDefs": [
                                                {
                                                    "headerName": "Texto",
                                                    "field": "texto",
                                                    "flex": 1,
                                                    "resizable": True,
                                                    "sortable": True,
                                                    "wrapText": True,
                                                    "autoHeight": True,
                                                    "cellClass": "cell-multiline",
                                                },
                                                {
                                                    "headerName": "Categoría",
                                                    "field": "categoria",
                                                    "width": 120,
                                                    "resizable": False,
                                                    "sortable": True,
                                                },
                                                {
                                                    "headerName": "Usos",
                                                    "field": "usos",
                                                    "width": 65,
                                                    "resizable": False,
                                                    "sortable": True,
                                                },
                                                {
                                                    "headerName": "Estado",
                                                    "field": "estado",
                                                    "width": 90,
                                                    "resizable": False,
                                                    "sortable": True,
                                                },
                                            ],
                                            "rowData": filas_plt,
                                            "rowSelection": "single",
                                            "domLayout": "autoHeight",
                                        }
                                    ).classes("w-full")

                                async def _on_plt_sel() -> None:
                                    rows = await plt_grid.get_selected_rows()
                                    _s["sel_plt"] = rows[0] if rows else None

                                plt_grid.on("selectionChanged", _on_plt_sel)

                                with ui.row().classes("gap-sm").style("flex-wrap: wrap; align-items: center"):

                                    def _on_editar_plt_btn() -> None:
                                        sel = _s.get("sel_plt")
                                        if not sel:
                                            toast_warning("Selecciona una plantilla de la tabla.")
                                            return
                                        plt_obj = next(
                                            (
                                                p
                                                for p in _s["plantillas"]
                                                if getattr(p, "id", None) == sel.get("id")
                                            ),
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

                                    btn_icon(
                                        Icons.EDIT,
                                        on_click=_on_editar_plt_btn,
                                        tooltip="Editar seleccionada",
                                    )
                                    if es_directivo:
                                        btn_danger(
                                            "Desactivar", on_click=_on_desactivar_plt_btn, size="sm"
                                        )

        app_layout(
            ctx_actual,
            contenido_pagina,
            page_titulo="Configuración de convivencia",
            page_icono="settings",
        )

    _contenido()


__all__ = ["configuracion_convivencia_page"]
