"""
src/interface/pages/convivencia/plantillas.py
=============================================
Página CRUD de plantillas de observación — ZECI Manager v2.0.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Los DTOs se acceden a través del módulo de servicios.
  Solo usa Container (servicios) e imports de la capa de interfaz.

RBAC:
  Solo Rol.COORDINADOR y Rol.DIRECTOR acceden.

Flujo:
  1. Guard RBAC → redirige a /inicio si el rol no está permitido.
  2. _s carga plantillas del servicio (todas, incluyendo inactivas).
  3. Tabla: Texto, Categoría, Usos, Estado.
  4. Botón "Nueva plantilla" → form_dialog.
  5. Botón editar (lápiz) por fila → form_dialog precargado.
  6. Botón desactivar por fila (solo si activa) → confirm_dialog con variante "danger".
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
    status_badge,
    toast_error,
    toast_success,
)
from src.interface.design.components.buttons import btn_danger, btn_icon, btn_primary
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.services.convivencia_service import NuevaPlantillaDTO

logger = logging.getLogger("PLANTILLAS")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "plantillas": [],   # list[PlantillaObservacion]
        "categorias": [],   # list[CategoriaObservacion] (activas para el selector)
        "editando":   None, # PlantillaObservacion | None
    }


def _cargar_estado(_s: dict) -> None:
    """Carga las plantillas y categorías desde el servicio."""
    try:
        _s["plantillas"] = Container.convivencia_service().listar_todas_plantillas()
    except Exception as exc:
        logger.error("Error cargando plantillas: %s", exc)
        _s["plantillas"] = []
    try:
        _s["categorias"] = Container.convivencia_service().listar_categorias(
            solo_activas=True
        )
    except Exception as exc:
        logger.error("Error cargando categorías: %s", exc)
        _s["categorias"] = []


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (convivencia_17)
def plantillas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    # Guard RBAC
    rol = getattr(ctx, "usuario_rol", None)
    if rol not in ("coordinador", "director"):
        ui.navigate.to("/inicio")
        return

    _s = _estado_inicial()
    _cargar_estado(_s)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _opciones_categorias() -> dict:
        """Construye dict {None: 'Sin categoría', cat_id: nombre} para el select."""
        opts: dict = {None: "Sin categoría"}
        for cat in _s["categorias"]:
            cat_id = getattr(cat, "id", None)
            nombre = getattr(cat, "nombre", "")
            if cat_id is not None:
                opts[cat_id] = nombre
        return opts

    def _cat_nombre_por_id() -> dict:
        """Dict {cat_id: nombre} para resolver IDs en la tabla."""
        return {
            getattr(c, "id", None): getattr(c, "nombre", "")
            for c in _s["categorias"]
        }

    # ── Handlers ───────────────────────────────────────────────────────────

    def _abrir_nueva_plantilla() -> None:
        _s["editando"] = None
        opciones = _opciones_categorias()
        campos = [
            {
                "key":      "texto",
                "label":    "Texto",
                "tipo":     "textarea",
                "requerido": True,
                "placeholder": "Texto de la plantilla (máx. 2000 caracteres)",
            },
            {
                "key":     "categoria_id",
                "label":   "Categoría",
                "tipo":    "select",
                "opciones": opciones,
                "valor":   None,
            },
        ]
        form_dialog(
            titulo="Nueva plantilla",
            campos=campos,
            on_submit=_crear_plantilla,
            texto_submit="Guardar",
        )

    def _abrir_editar_plantilla(plantilla) -> None:
        _s["editando"] = plantilla
        opciones = _opciones_categorias()
        campos = [
            {
                "key":      "texto",
                "label":    "Texto",
                "tipo":     "textarea",
                "valor":    getattr(plantilla, "texto", ""),
                "requerido": True,
                "placeholder": "Texto de la plantilla (máx. 2000 caracteres)",
            },
            {
                "key":     "categoria_id",
                "label":   "Categoría",
                "tipo":    "select",
                "opciones": opciones,
                "valor":   getattr(plantilla, "categoria_id", None),
            },
        ]
        form_dialog(
            titulo="Editar plantilla",
            campos=campos,
            on_submit=_actualizar_plantilla,
            texto_submit="Guardar cambios",
        )

    def _crear_plantilla(datos: dict) -> bool | None:
        texto = str(datos.get("texto", "")).strip()
        categoria_id = datos.get("categoria_id", None)
        if not texto:
            from src.interface.design.components import toast_warning
            toast_warning("El texto de la plantilla es requerido.")
            return False
        try:
            dto = NuevaPlantillaDTO(
                texto=texto,
                categoria_id=categoria_id,
            )
            Container.convivencia_service().crear_plantilla(
                dto,
                usuario_id=getattr(ctx, "usuario_id", None),
                usuario_rol=getattr(ctx, "usuario_rol", None),
            )
            toast_success("Plantilla creada.")
            _cargar_estado(_s)
            _contenido.refresh()
            return None
        except Exception as exc:
            logger.error("Error creando plantilla: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _actualizar_plantilla(datos: dict) -> bool | None:
        plantilla = _s.get("editando")
        if plantilla is None:
            toast_error("No hay plantilla seleccionada para editar.")
            return False
        texto = str(datos.get("texto", "")).strip()
        categoria_id = datos.get("categoria_id", None)
        if not texto:
            from src.interface.design.components import toast_warning
            toast_warning("El texto de la plantilla es requerido.")
            return False
        try:
            dto = NuevaPlantillaDTO(
                texto=texto,
                categoria_id=categoria_id,
            )
            Container.convivencia_service().actualizar_plantilla(
                getattr(plantilla, "id"),
                dto,
                usuario_id=getattr(ctx, "usuario_id", None),
                usuario_rol=getattr(ctx, "usuario_rol", None),
            )
            toast_success("Plantilla actualizada.")
            _cargar_estado(_s)
            _contenido.refresh()
            return None
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
            mensaje=(
                "¿Confirmas la desactivación de esta plantilla? "
                "Los registros históricos no se verán afectados."
            ),
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Refreshable ────────────────────────────────────────────────────────

    @ui.refreshable
    def _contenido() -> None:
        ctx_actual = SessionContext.desde_storage() or ctx
        plantillas = _s["plantillas"]
        nombres_cat = _cat_nombre_por_id()

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes("panel-toolbar"):
                        ui.element("div").classes("panel-toolbar-spacer")
                        btn_primary(
                            "Nueva plantilla",
                            on_click=_abrir_nueva_plantilla,
                            icon=Icons.ADD,
                        )

                with ui.element("div").classes("panel-card"):
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
                        # Cabecera
                        with ui.element("div").classes("config-list-header"):
                            with ui.element("div").classes("config-col-name-hdr"):
                                ui.label("Texto").classes("config-list-header-label")
                            with ui.element("div").classes("config-col-badge"):
                                ui.label("Categoría").classes("config-list-header-label")
                            with ui.element("div").classes("config-col-count-hdr"):
                                ui.label("Usos").classes("config-list-header-label")
                            with ui.element("div").classes("config-col-status"):
                                ui.label("Estado").classes("config-list-header-label")
                            with ui.element("div").classes("config-col-actions-hdr"):
                                ui.label("Acciones").classes("config-list-header-label")

                        # Filas
                        for plantilla in plantillas:
                            plantilla_id = getattr(plantilla, "id", None)
                            texto = getattr(plantilla, "texto", "")
                            categoria_id = getattr(plantilla, "categoria_id", None)
                            activa = getattr(plantilla, "activa", True)
                            nombre_cat = nombres_cat.get(categoria_id, "Sin categoría")
                            texto_corto = texto[:75] + ("…" if len(texto) > 75 else "")
                            with ui.element("div").classes("config-list-row"):
                                ui.label(texto_corto).classes("config-col-name")
                                with ui.element("div").classes("config-col-badge"):
                                    status_badge(nombre_cat, variante="neutral")
                                ui.label(str(getattr(plantilla, "uso_count", 0))).classes("config-col-count")
                                with ui.element("div").classes("config-col-status"):
                                    if activa:
                                        status_badge("Activa", variante="success")
                                    else:
                                        status_badge("Inactiva", variante="neutral")
                                with ui.element("div").classes("config-col-actions"):
                                    btn_icon(
                                        Icons.EDIT,
                                        on_click=lambda p=plantilla: _abrir_editar_plantilla(p),
                                        tooltip="Editar",
                                    )
                                    if activa:
                                        btn_danger(
                                            "Desactivar",
                                            on_click=lambda pid=plantilla_id: _desactivar_plantilla(pid),
                                            size="sm",
                                        )

        app_layout(
            ctx_actual,
            contenido_pagina,
            page_titulo="Plantillas de Observación",
        )

    _contenido()


__all__ = ["plantillas_page"]
