"""
src/interface/pages/evaluacion/planilla_notas.py
=================================================
Planilla de notas y gestión de actividades.
Ruta: /evaluacion/planilla
Acceso: todos los autenticados

Modos de vista:
  - PLANILLA: tabla de estudiantes x actividades con edición inline de notas.
  - ACTIVIDADES: lista de actividades con CRUD y gestión de estado.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.services.evaluacion_service import NuevaActividadDTO, RegistrarNotaDTO, EstadoActividad
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("EVALUACION.PLANILLA")

_MODOS = {"planilla": "Planilla de notas", "actividades": "Actividades"}


@ui.page("/evaluacion/planilla")
def planilla_notas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Planilla notas: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "periodos":        [],
        "asignaciones":    [],
        "categorias":      [],
        "actividades":     [],
        "planilla":        [],          # list[ResultadoEstudianteDTO]
        "periodo_id":      None,
        "asignacion_id":   None,
        "modo":            "planilla",
        # formulario nueva actividad
        "form_nombre":     "",
        "form_categoria_id": None,
        "form_valor_maximo": 100.0,
        "form_descripcion":  "",
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

    def _cargar_datos_asignacion() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["actividades"] = []
            _s["categorias"] = []
            _s["planilla"] = []
            return

        try:
            _s["actividades"] = Container.evaluacion_service().listar_actividades(
                asig_id, per_id
            )
        except Exception as exc:
            logger.error("Error cargando actividades: %s", exc)
            _s["actividades"] = []

        try:
            _s["categorias"] = Container.evaluacion_service().listar_categorias(
                asig_id, per_id
            )
        except Exception as exc:
            logger.error("Error cargando categorías: %s", exc)
            _s["categorias"] = []

        try:
            _s["planilla"] = Container.evaluacion_service().obtener_planilla(
                asig_id, per_id, ctx=None
            )
        except Exception as exc:
            logger.error("Error cargando planilla: %s", exc)
            _s["planilla"] = []

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _crear_actividad() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        if not asig_id or not per_id:
            ui.notify("Seleccione periodo y asignación", type="warning")
            return
        nombre = str(_s["form_nombre"]).strip()
        if not nombre:
            ui.notify("El nombre no puede estar vacío", type="warning")
            return
        cat_id = _s["form_categoria_id"]
        if not cat_id:
            ui.notify("Seleccione una categoría", type="warning")
            return
        try:
            dto = NuevaActividadDTO(
                nombre=nombre,
                categoria_id=int(cat_id),
                descripcion=str(_s["form_descripcion"]).strip() or None,
                valor_maximo=float(_s["form_valor_maximo"] or 100.0),
            )
            Container.evaluacion_service().agregar_actividad(dto)
            ui.notify(f"Actividad '{nombre}' creada", type="positive")
            _s["form_nombre"] = ""
            _s["form_descripcion"] = ""
            _s["form_valor_maximo"] = 100.0
            _cargar_datos_asignacion()
            contenido_actividades.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al crear actividad: %s", exc)
            ui.notify("Error al crear la actividad", type="negative")

    def _publicar_actividad(act_id: int, nombre: str) -> None:
        try:
            Container.evaluacion_service().publicar_actividad(act_id)
            ui.notify(f"'{nombre}' publicada", type="positive")
            _cargar_datos_asignacion()
            contenido_actividades.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al publicar actividad %s: %s", act_id, exc)
            ui.notify("Error al publicar", type="negative")

    def _cerrar_actividad(act_id: int, nombre: str) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label(
                f"¿Cerrar actividad '{nombre}'? Ya no aceptará más notas."
            ).classes("text-base font-medium")
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button(
                    "Cerrar actividad",
                    color="warning",
                    on_click=lambda: _confirmar_cerrar(dlg, act_id, nombre),
                )
        dlg.open()

    def _confirmar_cerrar(dlg, act_id: int, nombre: str) -> None:
        try:
            Container.evaluacion_service().cerrar_actividad(act_id)
            ui.notify(f"'{nombre}' cerrada", type="positive")
            dlg.close()
            _cargar_datos_asignacion()
            contenido_actividades.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al cerrar actividad %s: %s", act_id, exc)
            ui.notify("Error al cerrar", type="negative")
            dlg.close()

    def _eliminar_actividad(act_id: int, nombre: str) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label(
                f"¿Eliminar actividad '{nombre}'? Esta acción es irreversible."
            ).classes("text-base font-medium")
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button(
                    "Eliminar",
                    color="negative",
                    on_click=lambda: _confirmar_eliminar_act(dlg, act_id, nombre),
                )
        dlg.open()

    def _confirmar_eliminar_act(dlg, act_id: int, nombre: str) -> None:
        try:
            Container.evaluacion_service().eliminar_actividad(act_id)
            ui.notify(f"'{nombre}' eliminada", type="positive")
            dlg.close()
            _cargar_datos_asignacion()
            contenido_actividades.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al eliminar actividad %s: %s", act_id, exc)
            ui.notify("Error al eliminar", type="negative")
            dlg.close()

    def _registrar_nota_dialog(est_id: int, act_id: int, nombre_est: str, nom_act: str) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-sm"):
            ui.label(f"Registrar nota — {nombre_est}").classes("text-base font-bold mb-2")
            ui.label(f"Actividad: {nom_act}").classes("text-sm text-grey-6 mb-2")
            nota_inp = ui.number("Nota (0–100)", value=0.0, min=0.0, max=100.0, step=0.5).classes(
                "w-full"
            )

            def _guardar_nota() -> None:
                try:
                    dto = RegistrarNotaDTO(
                        estudiante_id=est_id,
                        actividad_id=act_id,
                        valor=float(nota_inp.value or 0.0),
                        usuario_registro_id=ctx.usuario_id,
                    )
                    Container.evaluacion_service().registrar_nota(dto, ctx=None)
                    ui.notify("Nota registrada", type="positive")
                    dlg.close()
                    _cargar_datos_asignacion()
                    vista_planilla.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al registrar nota: %s", exc)
                    ui.notify("Error al registrar la nota", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button("Guardar", on_click=_guardar_nota, color="primary")
        dlg.open()

    def _on_selector_cambio() -> None:
        _cargar_datos_asignacion()
        vista_planilla.refresh()
        contenido_actividades.refresh()

    # ── Determinar si periodo está abierto ────────────────────────────────────
    def _periodo_abierto() -> bool:
        per_id = _s["periodo_id"]
        if not per_id:
            return False
        for p in _s["periodos"]:
            if p.id == per_id:
                estado = getattr(p, "estado", None)
                if estado is None:
                    return True
                estado_val = estado.value if hasattr(estado, "value") else str(estado)
                return estado_val not in ("cerrado", "closed")
        return False

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def vista_planilla() -> None:
        planilla = _s["planilla"]
        actividades = _s["actividades"]
        abierto = _periodo_abierto()

        if not planilla:
            ui.label("Sin datos de planilla para los selectores actuales.").classes(
                "text-empty mt-4"
            )
            return

        # Actividades publicadas o cerradas para columnas
        acts_visibles = [
            a for a in actividades
            if a.estado in (EstadoActividad.PUBLICADA, EstadoActividad.CERRADA)
        ]

        with ui.element("div").classes("w-full overflow-x-auto"):
            with ui.element("table").classes("min-w-full border-collapse text-sm"):
                with ui.element("thead"):
                    with ui.element("tr").classes("border-b bg-grey-2"):
                        ui.element("th").classes("p-2 text-left font-semibold").text = (
                            "Estudiante"
                        )
                        for act in acts_visibles:
                            th = ui.element("th").classes("p-2 text-center font-semibold")
                            with th:
                                ui.label(act.nombre).classes("block text-xs")
                                ui.label(f"/{act.valor_maximo:.0f}").classes(
                                    "block text-xs text-grey-6"
                                )
                        ui.element("th").classes("p-2 text-right font-semibold").text = (
                            "Definitiva"
                        )

                with ui.element("tbody"):
                    for resultado in planilla:
                        with ui.element("tr").classes("border-b hover:bg-grey-1"):
                            td = ui.element("td").classes("p-2")
                            with td:
                                ui.label(resultado.nombre_completo).classes("text-sm")

                            for act in acts_visibles:
                                nota_val = resultado.notas.get(act.id)
                                td2 = ui.element("td").classes("p-2 text-center")
                                with td2:
                                    if nota_val is not None:
                                        ui.label(f"{nota_val:.1f}").classes("text-sm font-mono")
                                        if (
                                            abierto
                                            and act.estado == EstadoActividad.PUBLICADA
                                        ):
                                            ui.button(
                                                icon="edit",
                                                on_click=lambda eid=resultado.estudiante_id, aid=act.id, en=resultado.nombre_completo, an=act.nombre: _registrar_nota_dialog(eid, aid, en, an),
                                            ).props("flat round dense size=xs").tooltip(
                                                "Editar nota"
                                            )
                                    else:
                                        if (
                                            abierto
                                            and act.estado == EstadoActividad.PUBLICADA
                                        ):
                                            ui.button(
                                                icon="add",
                                                on_click=lambda eid=resultado.estudiante_id, aid=act.id, en=resultado.nombre_completo, an=act.nombre: _registrar_nota_dialog(eid, aid, en, an),
                                            ).props("flat round dense size=xs").tooltip(
                                                "Ingresar nota"
                                            )
                                        else:
                                            ui.label("—").classes("text-grey-5")

                            td_def = ui.element("td").classes("p-2 text-right")
                            with td_def:
                                ui.label(f"{resultado.definitiva:.1f}").classes(
                                    "font-mono font-semibold"
                                )

    @ui.refreshable
    def contenido_actividades() -> None:
        actividades = _s["actividades"]
        categorias = _s["categorias"]
        cat_opts = {c.id: c.nombre for c in categorias}

        # Formulario nueva actividad
        with ui.element("div").classes("panel-card mb-4"):
            ui.label("Nueva actividad").classes("text-base font-semibold mb-3")
            with ui.row().classes("gap-3 items-end flex-wrap"):
                ui.input(
                    "Nombre *",
                    placeholder="Ej: Taller 1",
                ).classes("w-44").bind_value(_s, "form_nombre")
                ui.select(
                    cat_opts or {"": "Sin categorías"},
                    value=None,
                    label="Categoría *",
                    on_change=lambda e: _s.__setitem__("form_categoria_id", e.value),
                ).classes("w-48")
                ui.number(
                    "Valor máximo",
                    value=100.0,
                    min=0.1,
                    step=0.5,
                ).classes("w-32").bind_value(_s, "form_valor_maximo")
                ui.input("Descripción").classes("w-52").bind_value(_s, "form_descripcion")
                ui.button(
                    "Agregar",
                    icon="add",
                    on_click=_crear_actividad,
                    color="primary",
                )

        # Lista de actividades
        if not actividades:
            ui.label("No hay actividades para esta asignación y periodo.").classes(
                "text-empty mt-4"
            )
            return

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-3 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Nombre").classes("flex-1")
                ui.label("Categoría").classes("w-36")
                ui.label("Valor máx.").classes("w-24 text-right")
                ui.label("Estado").classes("w-24 text-center")
                ui.label("Acciones").classes("w-32 text-right")

            for act in actividades:
                cat_nombre = cat_opts.get(act.categoria_id, "—")
                estado_val = act.estado.value if hasattr(act.estado, "value") else str(act.estado)

                with ui.element("div").classes("flex items-center gap-3 p-2 border-b"):
                    ui.label(act.nombre).classes("flex-1 text-sm")
                    ui.label(cat_nombre).classes("w-36 text-sm text-grey-7")
                    ui.label(f"{act.valor_maximo:.1f}").classes(
                        "w-24 text-right font-mono text-sm"
                    )

                    badge_clase = {
                        "borrador":  "badge-neutral",
                        "publicada": "badge-success",
                        "cerrada":   "badge-warning",
                    }.get(estado_val, "badge-neutral")
                    ui.badge(estado_val.capitalize()).classes(f"w-24 text-center {badge_clase}")

                    with ui.row().classes("w-32 justify-end gap-1"):
                        if act.estado == EstadoActividad.BORRADOR:
                            ui.button(
                                icon="publish",
                                on_click=lambda aid=act.id, an=act.nombre: _publicar_actividad(aid, an),
                            ).props("flat round dense").tooltip("Publicar")
                        elif act.estado == EstadoActividad.PUBLICADA:
                            ui.button(
                                icon="lock",
                                color="warning",
                                on_click=lambda aid=act.id, an=act.nombre: _cerrar_actividad(aid, an),
                            ).props("flat round dense").tooltip("Cerrar")

                        if act.estado != EstadoActividad.CERRADA:
                            ui.button(
                                icon="delete",
                                color="negative",
                                on_click=lambda aid=act.id, an=act.nombre: _eliminar_actividad(aid, an),
                            ).props("flat round dense").tooltip("Eliminar")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4 flex-wrap"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Planilla de Notas").classes("text-xl font-bold")

                periodos_opts = {p.id: p.nombre for p in _s["periodos"]}
                asigs_opts = {
                    a.asignacion_id: a.display_corto for a in _s["asignaciones"]
                }

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
                    ui.select(
                        _MODOS,
                        value="planilla",
                        label="Vista",
                        on_change=lambda e: (
                            _s.__setitem__("modo", e.value),
                            (vista_planilla.refresh() if e.value == "planilla" else contenido_actividades.refresh()),
                        ),
                    ).classes("w-44")
                    ui.button(
                        icon="refresh",
                        on_click=lambda: (
                            _cargar_datos_asignacion(),
                            vista_planilla.refresh(),
                            contenido_actividades.refresh(),
                        ),
                    ).props("flat round dense").tooltip("Recargar")

            with ui.element("div").classes("panel-card mt-4"):
                if _s["modo"] == "planilla":
                    ui.label("Notas por estudiante y actividad").classes(
                        "text-base font-semibold mb-3"
                    )
                    vista_planilla()
                else:
                    ui.label("Gestión de actividades").classes(
                        "text-base font-semibold mb-3"
                    )
                    contenido_actividades()

    app_layout(
        titulo_pagina="Evaluación · Planilla de Notas",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/evaluacion/planilla",
        contenido=contenido,
    )


__all__ = ["planilla_notas_page"]
