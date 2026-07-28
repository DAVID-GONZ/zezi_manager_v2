"""
src/interface/pages/convivencia/categorias.py
=============================================
Página CRUD de categorías de observación — ZECI Manager v2.0.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Los DTOs se acceden a través del módulo de servicios.
  Solo usa Container (servicios) e imports de la capa de interfaz.

RBAC:
  Solo Rol.COORDINADOR y Rol.DIRECTOR acceden.

Flujo:
  1. Guard RBAC → redirige a /inicio si el rol no está permitido.
  2. _s carga categorías del servicio.
  3. Tabla: Nombre, Tipo (General / Comportamental), Estado (Activa / Inactiva).
  4. Botón "Nueva categoría" → form_dialog.
  5. Botón editar (lápiz) por fila → form_dialog precargado.
  6. Botón desactivar por fila (solo si activa) → confirm_dialog.
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
from src.interface.design.tokens import Icons
from src.services.convivencia_service import NuevaCategoriaDTO

logger = logging.getLogger("CATEGORIAS")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "categorias": [],  # list[CategoriaObservacion]
        "editando":   None,  # CategoriaObservacion | None
    }


def _cargar_estado(_s: dict) -> None:
    """Carga las categorías desde el servicio."""
    try:
        _s["categorias"] = Container.convivencia_service().listar_categorias(
            solo_activas=False
        )
    except Exception as exc:
        logger.error("Error cargando categorías: %s", exc)
        _s["categorias"] = []


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (convivencia_10)
def categorias_page() -> None:
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

    # ── Handlers ───────────────────────────────────────────────────────────

    def _abrir_nueva_categoria() -> None:
        _s["editando"] = None
        campos = [
            {
                "key":      "nombre",
                "label":    "Nombre",
                "tipo":     "text",
                "requerido": True,
            },
            {
                "key":   "es_comportamental",
                "label": "¿Es comportamental?",
                "tipo":  "checkbox",
                "valor": False,
            },
        ]
        form_dialog(
            titulo="Nueva categoría",
            campos=campos,
            on_submit=_crear_categoria,
            texto_submit="Guardar",
        )

    def _abrir_editar_categoria(cat) -> None:
        _s["editando"] = cat
        campos = [
            {
                "key":      "nombre",
                "label":    "Nombre",
                "tipo":     "text",
                "valor":    getattr(cat, "nombre", ""),
                "requerido": True,
            },
            {
                "key":   "es_comportamental",
                "label": "¿Es comportamental?",
                "tipo":  "checkbox",
                "valor": getattr(cat, "es_comportamental", False),
            },
        ]
        form_dialog(
            titulo="Editar categoría",
            campos=campos,
            on_submit=_actualizar_categoria,
            texto_submit="Guardar cambios",
        )

    def _crear_categoria(datos: dict) -> bool | None:
        nombre = str(datos.get("nombre", "")).strip()
        es_comportamental = bool(datos.get("es_comportamental", False))
        if not nombre:
            from src.interface.design.components import toast_warning
            toast_warning("El nombre de la categoría es requerido.")
            return False
        try:
            dto = NuevaCategoriaDTO(
                nombre=nombre,
                es_comportamental=es_comportamental,
            )
            Container.convivencia_service().crear_categoria(dto)
            toast_success("Categoría creada.")
            _cargar_estado(_s)
            _contenido.refresh()
            return None
        except Exception as exc:
            logger.error("Error creando categoría: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _actualizar_categoria(datos: dict) -> bool | None:
        cat = _s.get("editando")
        if cat is None:
            toast_error("No hay categoría seleccionada para editar.")
            return False
        nombre = str(datos.get("nombre", "")).strip()
        es_comportamental = bool(datos.get("es_comportamental", False))
        if not nombre:
            from src.interface.design.components import toast_warning
            toast_warning("El nombre de la categoría es requerido.")
            return False
        try:
            dto = NuevaCategoriaDTO(
                nombre=nombre,
                es_comportamental=es_comportamental,
            )
            Container.convivencia_service().actualizar_categoria(
                getattr(cat, "id"), dto
            )
            toast_success("Categoría actualizada.")
            _cargar_estado(_s)
            _contenido.refresh()
            return None
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
                logger.error(
                    "Error desactivando categoría %s: %s", cat_id, exc, exc_info=True
                )
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Desactivar categoría",
            mensaje=(
                "¿Confirmas la desactivación de esta categoría? "
                "Los registros históricos no se verán afectados."
            ),
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Refreshable ────────────────────────────────────────────────────────

    @ui.refreshable
    def _contenido() -> None:
        ctx_actual = SessionContext.desde_storage() or ctx
        categorias = _s["categorias"]

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes("panel-toolbar"):
                        ui.element("div").classes("panel-toolbar-spacer")
                        btn_primary(
                            "Nueva categoría",
                            on_click=_abrir_nueva_categoria,
                            icon=Icons.ADD,
                        )

                with ui.element("div").classes("panel-card"):
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
                        col_defs = [
                            {"headerName": "Nombre", "field": "nombre", "flex": 2, "sortable": True},
                            {"headerName": "Tipo",   "field": "tipo",   "width": 160},
                            {"headerName": "Estado", "field": "estado", "width": 130},
                        ]
                        filas_ag = [
                            {
                                "id":     getattr(c, "id", None),
                                "nombre": getattr(c, "nombre", ""),
                                "tipo":   "Comportamental" if getattr(c, "es_comportamental", False) else "General",
                                "estado": "Activa" if getattr(c, "activa", True) else "Inactiva",
                                "activa": getattr(c, "activa", True),
                            }
                            for c in categorias
                        ]
                        ui.aggrid({
                            "columnDefs":        col_defs,
                            "rowData":           filas_ag,
                            "defaultColDef":     {"resizable": True},
                            "suppressCellFocus": True,
                            "rowSelection":      "single",
                        }).classes("w-full")

                        with ui.element("div").classes("row-actions"):
                            for cat in categorias:
                                cat_id = getattr(cat, "id", None)
                                nombre = getattr(cat, "nombre", "")
                                es_comportamental = getattr(cat, "es_comportamental", False)
                                activa = getattr(cat, "activa", True)
                                with ui.row().classes("row-actions-item"):
                                    ui.label(nombre).classes("row-actions-name")
                                    if es_comportamental:
                                        status_badge("Comportamental", variante="info")
                                    else:
                                        status_badge("General", variante="neutral")
                                    if activa:
                                        status_badge("Activa", variante="success")
                                    else:
                                        status_badge("Inactiva", variante="neutral")
                                    btn_icon(
                                        Icons.EDIT,
                                        on_click=lambda c=cat: _abrir_editar_categoria(c),
                                        tooltip="Editar",
                                    )
                                    if activa:
                                        btn_danger(
                                            "Desactivar",
                                            on_click=lambda cid=cat_id: _desactivar_categoria(cid),
                                            size="sm",
                                        )

        app_layout(
            ctx_actual,
            contenido_pagina,
            page_titulo="Categorías de Observación",
            mostrar_contexto=False,
        )

    _contenido()


__all__ = ["categorias_page"]
