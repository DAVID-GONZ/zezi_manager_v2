"""
src/interface/pages/evaluacion/planilla_notas.py
=================================================
Planilla de notas y gestión de actividades.
Ruta: /evaluacion/planilla
Acceso: todos los autenticados

Modos de vista:
  - PLANILLA: tabla ag-Grid de estudiantes x actividades con edición inline de notas.
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
from src.interface.design.components.buttons import btn_primary, btn_danger, btn_ghost, btn_icon
from src.interface.design.components import status_badge, form_dialog
from src.services.evaluacion_service import NuevaActividadDTO, RegistrarNotaDTO, EstadoActividad

logger = logging.getLogger("EVALUACION.PLANILLA")

_MODOS = {"planilla": "Planilla de notas", "actividades": "Actividades"}


def _promedio_cat(notas_dict: dict, acts_de_cat: list) -> "float | None":
    """Calcula el promedio de las notas de las actividades de una categoría."""
    vals = [notas_dict.get(a.id) for a in acts_de_cat if notas_dict.get(a.id) is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


@ui.page("/evaluacion/planilla")
def planilla_notas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Planilla notas: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "asignacion_id":    ctx.asignacion_id,   # leer del context
        "periodo_id":       ctx.periodo_id,       # leer del context
        "grupo_id":         ctx.grupo_id,
        "asignaciones":     [],                   # list[AsignacionInfo] para el selector
        "periodos":         [],
        "categorias":       [],
        "actividades":      [],
        "planilla":         [],                   # list[ResultadoEstudianteDTO]
        "modo":             "planilla",
        # formulario nueva actividad
        "act_nombre":       "",
        "act_categoria_id": None,
        "act_valor_max":    100.0,
        "act_descripcion":  "",
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

    def _cargar_asignaciones() -> None:
        grupo_id = _s["grupo_id"]
        if not grupo_id:
            _s["asignaciones"] = []
            return
        try:
            _s["asignaciones"] = Container.asignacion_service().listar_por_grupo(grupo_id)
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
                _s["grupo_id"], asig_id, per_id
            )
        except Exception as exc:
            logger.error("Error cargando planilla: %s", exc)
            _s["planilla"] = []

    # Cargar datos iniciales desde el contexto del topbar
    _cargar_estado()
    _cargar_asignaciones()
    _cargar_datos_asignacion()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _crear_actividad() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        if not asig_id or not per_id:
            ui.notify("Seleccione periodo y asignación en el contexto", type="warning")
            return
        nombre = str(_s["act_nombre"]).strip()
        if not nombre:
            ui.notify("El nombre no puede estar vacío", type="warning")
            return
        cat_id = _s["act_categoria_id"]
        if not cat_id:
            ui.notify("Seleccione una categoría", type="warning")
            return
        try:
            dto = NuevaActividadDTO(
                nombre=nombre,
                categoria_id=int(cat_id),
                descripcion=str(_s["act_descripcion"]).strip() or None,
                valor_maximo=float(_s["act_valor_max"] or 100.0),
            )
            Container.evaluacion_service().agregar_actividad(dto)
            ui.notify(f"Actividad '{nombre}' creada", type="positive")
            _s["act_nombre"] = ""
            _s["act_descripcion"] = ""
            _s["act_valor_max"] = 100.0
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
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_ghost(
                    "Cerrar actividad",
                    on_click=lambda: _confirmar_cerrar(dlg, act_id, nombre),
                    icon="lock",
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
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_danger(
                    "Eliminar",
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
        return True  # si el periodo no está en la lista, asumir abierto

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def vista_planilla() -> None:
        planilla = _s["planilla"]
        actividades = _s["actividades"]
        categorias = _s["categorias"]
        periodo_abierto = _periodo_abierto()

        if not _s["asignacion_id"] or not _s["periodo_id"]:
            with ui.element("div").classes("tablero-empty"):
                ui.icon("tune").classes("text-grey-5 text-3xl mb-2")
                ui.label("Selecciona un periodo y asignación arriba para ver la planilla.").classes(
                    "tablero-empty-hint"
                )
            return

        if not planilla:
            with ui.element("div").classes("tablero-empty"):
                ui.label("Sin datos de planilla para el contexto activo.").classes(
                    "tablero-empty-hint"
                )
            return

        # Actividades publicadas o cerradas para columnas
        acts_visibles = [
            a for a in actividades
            if a.estado in (EstadoActividad.PUBLICADA, EstadoActividad.CERRADA)
        ]

        # Banner periodo cerrado
        if not periodo_abierto:
            with ui.element("div").classes("panel-card bg-amber-50 border-amber-400 mb-3"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("lock").classes("text-amber-600")
                    ui.label("Período CERRADO — Modo solo lectura").classes("font-bold text-amber-700")

        # Color rules para ag-Grid
        color_rules = {
            "grade-bajo":     "x != null && x < 60",
            "grade-basico":   "x != null && x >= 60 && x < 80",
            "grade-alto":     "x != null && x >= 80 && x < 90",
            "grade-superior": "x != null && x >= 90",
        }

        # Construir columnDefs
        col_defs = [
            {
                "headerName": "Estudiante",
                "field": "nombre_completo",
                "pinned": "left",
                "width": 220,
                "filter": True,
                "sortable": True,
            },
        ]

        for cat in categorias:
            acts_de_cat = [a for a in acts_visibles if a.categoria_id == cat.id]
            children = []
            for act in acts_de_cat:
                es_publicada = act.estado == EstadoActividad.PUBLICADA
                children.append({
                    "headerName": act.nombre[:20],
                    "field": f"act_{act.id}",
                    "editable": periodo_abierto and es_publicada,
                    "width": 80,
                    "type": "numericColumn",
                    "valueFormatter": "value != null ? Number(value).toFixed(1) : ''",
                    "cellClassRules": color_rules,
                })
            # Promedio de categoría
            children.append({
                "headerName": "PROM",
                "field": f"cat_avg_{cat.id}",
                "editable": False,
                "width": 70,
                "valueFormatter": "value != null ? Number(value).toFixed(1) : ''",
                "cellClassRules": color_rules,
            })
            col_defs.append({
                "headerName": f"{cat.nombre} ({cat.peso_porcentaje:.0f}%)",
                "children": children,
            })

        col_defs.append({
            "headerName": "Definitiva",
            "field": "definitiva",
            "pinned": "right",
            "width": 80,
            "editable": False,
            "valueFormatter": "value != null ? Number(value).toFixed(1) : ''",
            "cellClassRules": color_rules,
        })

        # Construir rowData
        row_data = []
        for resultado in planilla:
            row: dict = {
                "estudiante_id":   resultado.estudiante_id,
                "nombre_completo": resultado.nombre_completo,
                "definitiva":      resultado.definitiva,
            }
            for cat in categorias:
                acts_de_cat = [a for a in acts_visibles if a.categoria_id == cat.id]
                for act in acts_de_cat:
                    row[f"act_{act.id}"] = resultado.notas.get(act.id)
                row[f"cat_avg_{cat.id}"] = _promedio_cat(resultado.notas, acts_de_cat)
            row_data.append(row)

        grid = ui.aggrid({
            "columnDefs": col_defs,
            "rowData": row_data,
            "defaultColDef": {"sortable": True, "resizable": True},
            "singleClickEdit": True,
            "stopEditingWhenCellsLoseFocus": True,
        }).classes("w-full h-[600px]")

        async def on_cell_edit(e) -> None:
            col_id = e.args.get("colId", "")
            val_raw = e.args.get("newValue")
            data = e.args.get("data", {})
            est_id = data.get("estudiante_id")

            if not col_id.startswith("act_"):
                return

            act_id = int(col_id.replace("act_", ""))

            # Celda vaciada
            if val_raw is None or str(val_raw).strip() == "":
                ui.notify("Para eliminar una nota usa el botón de edición individual.", type="info")
                vista_planilla.refresh()
                return

            try:
                new_val = float(val_raw)
            except (ValueError, TypeError):
                ui.notify("Valor inválido — debe ser un número", type="warning")
                vista_planilla.refresh()
                return

            if new_val < 0 or new_val > 100:
                ui.notify("La nota debe estar entre 0 y 100", type="warning")
                vista_planilla.refresh()
                return

            try:
                dto = RegistrarNotaDTO(
                    estudiante_id=est_id,
                    actividad_id=act_id,
                    valor=new_val,
                    usuario_registro_id=ctx.usuario_id,
                )
                Container.evaluacion_service().registrar_nota(
                    dto,
                    ctx=ctx.to_contexto_academico(),
                    usuario_id=ctx.usuario_id,
                )
                ui.notify(f"Nota {new_val:.1f} guardada", type="positive", position="bottom-right", timeout=1000)
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
                vista_planilla.refresh()
            except Exception as exc:
                logger.error("Error guardando nota: %s", exc)
                ui.notify("Error al guardar la nota", type="negative")
                vista_planilla.refresh()

        if periodo_abierto:
            grid.on("cellValueChanged", on_cell_edit)

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
                ).classes("w-44").bind_value(_s, "act_nombre")
                ui.select(
                    cat_opts or {"": "Sin categorías"},
                    value=None,
                    label="Categoría *",
                    on_change=lambda e: _s.__setitem__("act_categoria_id", e.value),
                ).classes("w-48")
                ui.number(
                    "Valor máximo",
                    value=100.0,
                    min=0.1,
                    step=0.5,
                ).classes("w-32").bind_value(_s, "act_valor_max")
                ui.input("Descripción").classes("w-52").bind_value(_s, "act_descripcion")
                btn_primary("Agregar", icon="add", on_click=_crear_actividad)

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
                    status_badge(estado_val.capitalize(), badge_clase.replace("badge-", ""))

                    with ui.row().classes("w-32 justify-end gap-1"):
                        if act.estado == EstadoActividad.BORRADOR:
                            btn_icon(
                                "publish",
                                on_click=lambda aid=act.id, an=act.nombre: _publicar_actividad(aid, an),
                                tooltip="Publicar",
                            )
                        elif act.estado == EstadoActividad.PUBLICADA:
                            btn_icon(
                                "lock",
                                on_click=lambda aid=act.id, an=act.nombre: _cerrar_actividad(aid, an),
                                tooltip="Cerrar",
                            )

                        if act.estado != EstadoActividad.CERRADA:
                            btn_icon(
                                "delete",
                                on_click=lambda aid=act.id, an=act.nombre: _eliminar_actividad(aid, an),
                                tooltip="Eliminar",
                                variante="danger",
                            )

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.row().classes("gap-3 items-end flex-wrap mb-4"):
            # Selector de periodo
            per_opts = {p.id: getattr(p, "nombre", str(p.id)) for p in _s["periodos"]}
            ui.select(
                label="Periodo",
                options=per_opts or {None: "Sin periodos"},
                value=_s["periodo_id"],
                on_change=lambda e: on_periodo_change(e.value),
            ).classes("w-44")

            # Selector de asignación
            asig_opts = {
                a.asignacion_id: a.asignatura_nombre
                for a in _s["asignaciones"]
            }
            ui.select(
                label="Asignación",
                options=asig_opts or {None: "Sin asignaciones"},
                value=_s["asignacion_id"],
                on_change=lambda e: on_asignacion_change(e.value),
            ).classes("w-56")

    def on_periodo_change(per_id) -> None:
        _s["periodo_id"] = per_id
        _cargar_datos_asignacion()
        filtros_refreshable.refresh()
        vista_planilla.refresh()
        contenido_actividades.refresh()

    def on_asignacion_change(asig_id) -> None:
        _s["asignacion_id"] = asig_id
        _cargar_datos_asignacion()
        filtros_refreshable.refresh()
        vista_planilla.refresh()
        contenido_actividades.refresh()

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4 flex-wrap"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Planilla de Notas").classes("text-xl font-bold")

                # Selectores de periodo y asignación (pre-poblados desde ctx)
                filtros_refreshable()

                # Selector de Vista + botón recargar
                with ui.row().classes("gap-4 items-center flex-wrap"):
                    ui.select(
                        _MODOS,
                        value="planilla",
                        label="Vista",
                        on_change=lambda e: (
                            _s.__setitem__("modo", e.value),
                            (vista_planilla.refresh() if e.value == "planilla" else contenido_actividades.refresh()),
                        ),
                    ).classes("w-44")
                    btn_icon(
                        "refresh",
                        on_click=lambda: (
                            _cargar_datos_asignacion(),
                            vista_planilla.refresh(),
                            contenido_actividades.refresh(),
                        ),
                        tooltip="Recargar",
                    )

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

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        titulo_pagina="Evaluación · Planilla de Notas",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/evaluacion/planilla",
        contenido=contenido,
        ctx=ctx,
        on_context_change=on_context_change,
    )


__all__ = ["planilla_notas_page"]
