"""
src/interface/pages/evaluacion/configuracion_evaluacion.py
===========================================================
Configuración de categorías de evaluación por asignación y periodo.
Ruta: /evaluacion/configuracion
Acceso: todos los autenticados (filtra por asignación del docente)

Permite:
 - Ver categorías de evaluación por periodo y asignación.
 - Crear, editar y eliminar categorías con validación de pesos.
 - Mostrar suma actual de pesos en tiempo real.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_danger, btn_ghost, btn_icon
from src.services.evaluacion_service import NuevaCategoriaDTO, ActualizarCategoriaDTO
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("EVALUACION.CONFIGURACION")


@ui.page("/evaluacion/configuracion")
def configuracion_evaluacion_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Config evaluación: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "periodos":       [],
        "asignaciones":   [],
        "categorias":     [],
        "periodo_id":     None,
        "asignacion_id":  None,
        # formulario crear categoría
        "form_nombre":    "",
        "form_peso":      0.10,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            anio_id = config.id if config else None
            if anio_id:
                _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id)
            else:
                _s["periodos"] = []
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)
            _s["periodos"] = []

        try:
            filtro = FiltroAsignacionesDTO(
                usuario_id=ctx.usuario_id if ctx.usuario_rol == "profesor" else None,
                solo_activas=True,
            )
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error cargando asignaciones: %s", exc)
            _s["asignaciones"] = []

    def _cargar_categorias() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["categorias"] = []
            return
        try:
            _s["categorias"] = Container.evaluacion_service().listar_categorias(
                asig_id, per_id
            )
        except Exception as exc:
            logger.error("Error cargando categorías: %s", exc)
            _s["categorias"] = []

    _cargar_estado()

    # ── Acciones CRUD ─────────────────────────────────────────────────────────
    def _crear_categoria() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        if not asig_id or not per_id:
            ui.notify("Seleccione periodo y asignación primero", type="warning")
            return
        nombre = str(_s["form_nombre"]).strip()
        if not nombre:
            ui.notify("El nombre no puede estar vacío", type="warning")
            return
        try:
            peso = float(_s["form_peso"])
        except (TypeError, ValueError):
            ui.notify("El peso debe ser un número entre 0 y 1", type="warning")
            return

        try:
            dto = NuevaCategoriaDTO(
                nombre=nombre,
                peso=peso,
                asignacion_id=asig_id,
                periodo_id=per_id,
            )
            Container.evaluacion_service().agregar_categoria(dto, ctx_dto=None)
            ui.notify(f"Categoría '{nombre}' creada", type="positive")
            _s["form_nombre"] = ""
            _s["form_peso"] = 0.10
            _cargar_categorias()
            tabla_categorias.refresh()
            panel_suma.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al crear categoría: %s", exc)
            ui.notify("Error al crear la categoría", type="negative")

    def _editar_categoria(cat) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            ui.label("Editar categoría").classes("text-lg font-bold mb-2")
            nom_inp = ui.input("Nombre", value=cat.nombre).classes("w-full")
            peso_inp = ui.number(
                "Peso (0.01 – 1.0)",
                value=cat.peso,
                min=0.01,
                max=1.0,
                step=0.01,
                format="%.2f",
            ).classes("w-full")
            ui.label(f"Porcentaje actual: {cat.peso_porcentaje:.1f}%").classes(
                "text-sm text-grey-6"
            )

            def _guardar() -> None:
                try:
                    nuevo_nombre = str(nom_inp.value).strip() or None
                    nuevo_peso = float(peso_inp.value) if peso_inp.value else None
                    dto_act = ActualizarCategoriaDTO(nombre=nuevo_nombre, peso=nuevo_peso)
                    Container.evaluacion_service().actualizar_categoria(cat.id, dto_act)
                    ui.notify("Categoría actualizada", type="positive")
                    dlg.close()
                    _cargar_categorias()
                    tabla_categorias.refresh()
                    panel_suma.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al actualizar categoría: %s", exc)
                    ui.notify("Error al actualizar", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_primary("Guardar", on_click=_guardar)
        dlg.open()

    def _eliminar_categoria(cat) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label(
                f"¿Eliminar categoría '{cat.nombre}'? Esta acción es irreversible."
            ).classes("text-base font-medium")
            with ui.row().classes("gap-2 mt-4"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_danger(
                    "Eliminar",
                    on_click=lambda: _confirmar_eliminar(dlg, cat),
                )
        dlg.open()

    def _confirmar_eliminar(dlg, cat) -> None:
        try:
            Container.evaluacion_service().eliminar_categoria(cat.id)
            ui.notify(f"Categoría '{cat.nombre}' eliminada", type="positive")
            dlg.close()
            _cargar_categorias()
            tabla_categorias.refresh()
            panel_suma.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al eliminar categoría: %s", exc)
            ui.notify("Error al eliminar", type="negative")
            dlg.close()

    def _on_selector_cambio() -> None:
        _cargar_categorias()
        tabla_categorias.refresh()
        panel_suma.refresh()

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def panel_suma() -> None:
        cats = _s["categorias"]
        if not cats:
            return
        total = round(sum(c.peso for c in cats), 4)
        pct = round(total * 100, 1)
        with ui.element("div").classes("flex items-center gap-3 p-3 rounded border"):
            ui.label("Suma de pesos:").classes("text-sm font-semibold")
            ui.badge(f"{pct}%").classes(f"badge-{'success' if total <= 1.0 else 'error'}")
            if total > 1.0:
                ui.label("⚠ La suma supera el 100%").classes("text-sm text-red-600")
            else:
                ui.label(f"Disponible: {round((1.0 - total) * 100, 1)}%").classes(
                    "text-sm text-grey-6"
                )

    @ui.refreshable
    def tabla_categorias() -> None:
        cats = _s["categorias"]
        if not cats:
            ui.label("No hay categorías para esta asignación y periodo.").classes(
                "text-empty mt-4"
            )
            return

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-3 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Nombre").classes("flex-1")
                ui.label("Peso").classes("w-20 text-right")
                ui.label("Porcentaje").classes("w-24 text-right")
                ui.label("Acciones").classes("w-20 text-right")

            for cat in cats:
                with ui.element("div").classes("flex items-center gap-3 p-2 border-b"):
                    ui.label(cat.nombre).classes("flex-1 text-sm")
                    ui.label(f"{cat.peso:.4f}").classes("w-20 text-right font-mono text-sm")
                    ui.label(f"{cat.peso_porcentaje:.1f}%").classes(
                        "w-24 text-right text-sm font-medium"
                    )
                    with ui.row().classes("w-20 justify-end gap-1"):
                        btn_icon("edit", on_click=lambda c=cat: _editar_categoria(c), tooltip="Editar")
                        btn_icon("delete", on_click=lambda c=cat: _eliminar_categoria(c), tooltip="Eliminar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Selectores
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Configuración de Evaluación").classes("text-xl font-bold")

                periodos_opts = {p.id: p.nombre for p in _s["periodos"]}
                asigs_opts = {a.asignacion_id: a.display_corto for a in _s["asignaciones"]}

                with ui.row().classes("gap-4 items-center flex-wrap"):
                    ui.select(
                        periodos_opts or {"": "Sin periodos"},
                        value=None,
                        label="Periodo *",
                        on_change=lambda e: (
                            _s.__setitem__("periodo_id", e.value),
                            _on_selector_cambio(),
                        ),
                    ).classes("w-48")
                    ui.select(
                        asigs_opts or {"": "Sin asignaciones"},
                        value=None,
                        label="Asignación *",
                        on_change=lambda e: (
                            _s.__setitem__("asignacion_id", e.value),
                            _on_selector_cambio(),
                        ),
                    ).classes("w-64")

            # Formulario crear categoría
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Nueva categoría").classes("text-base font-semibold mb-3")
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input(
                        "Nombre *",
                        placeholder="Ej: Trabajos escritos",
                    ).classes("w-52").bind_value(_s, "form_nombre")
                    ui.number(
                        "Peso (0.01–1.0)",
                        value=0.10,
                        min=0.01,
                        max=1.0,
                        step=0.01,
                        format="%.2f",
                    ).classes("w-36").bind_value(_s, "form_peso")
                    btn_primary("Agregar categoría", icon="add", on_click=_crear_categoria)

            # Resumen de pesos y tabla
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ui.label("Categorías registradas").classes("text-base font-semibold")
                    ui.badge(str(len(_s["categorias"]))).classes("badge-primary")
                    btn_icon(
                        "refresh",
                        on_click=lambda: (
                            _cargar_categorias(),
                            tabla_categorias.refresh(),
                            panel_suma.refresh(),
                        ),
                        tooltip="Recargar",
                    )

                panel_suma()
                ui.separator().classes("my-3")
                tabla_categorias()

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        titulo_pagina="Evaluación · Configuración",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/evaluacion/configuracion",
        contenido=contenido,
        ctx=ctx,
        on_context_change=on_context_change,
    )


__all__ = ["configuracion_evaluacion_page"]
