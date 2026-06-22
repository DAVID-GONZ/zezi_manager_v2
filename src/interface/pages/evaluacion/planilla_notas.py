"""
src/interface/pages/evaluacion/planilla_notas.py
=================================================
Planilla de notas y gestión de actividades.
Ruta:   /evaluacion/planilla
Acceso: todos los autenticados

El periodo y la asignación activos se leen exclusivamente del context_bar
(barra de contexto del topbar). Esta página no expone selectores propios
para esos campos; cualquier cambio de contexto recarga la página.

Vistas:
  PLANILLA    — ag-Grid de estudiantes × actividades con edición inline de notas.
  ACTIVIDADES — lista de actividades con CRUD completo y gestión de estado.

La vista activa se controla con dos botones explícitos (no un select).
La configuración de categorías se delega a /evaluacion/configuracion.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary, btn_secondary, btn_ghost, btn_icon,
)
from src.interface.design.components import (
    confirm_dialog, empty_state, skeleton_table, status_badge,
    toast_error, toast_info, toast_success, toast_warning,
)
from src.services.evaluacion_service import (
    NuevaActividadDTO, RegistrarNotaDTO, EstadoActividad,
    PuntosExtra, TipoPuntosExtra,
)
from src.services.plan_mejoramiento_service import EstadoNotaCorte

logger = logging.getLogger("EVALUACION.PLANILLA")

_ROLES_DIRECTIVOS = ("director", "coordinador")


def _promedio_cat(notas_dict: dict, acts_de_cat: list) -> "float | None":
    vals = [notas_dict.get(a.id) for a in acts_de_cat if notas_dict.get(a.id) is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def planilla_notas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Planilla notas: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    es_directivo = ctx.usuario_rol in _ROLES_DIRECTIVOS

    # ── Estado — solo lo que no viene del context_bar ─────────────────────────
    _s: dict = {
        "asignacion_id":    ctx.asignacion_id,
        "periodo_id":       ctx.periodo_id,
        "grupo_id":         ctx.grupo_id,
        "categorias":       [],
        "actividades":      [],
        "planilla":         [],
        "puntos_extra":     {},   # {estudiante_id: PuntosExtra}
        "mostrar_puntos":   False,
        "modo":             "planilla",   # "planilla" | "actividades"
        "corte":            None,   # CortePlan | None
        "notas_corte":      {},     # {estudiante_id: NotaCortePlan}
        # formulario nueva actividad
        "act_nombre":       "",
        "act_categoria_id": None,
        "act_valor_max":    100.0,
        "act_descripcion":  "",
        "cargando":         True,   # skeleton mientras carga la planilla inicial
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_datos() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["actividades"] = []
            _s["categorias"]  = []
            _s["planilla"]    = []
            return

        try:
            datos = Container.evaluacion_service().planilla_completa(
                _s["grupo_id"], asig_id, per_id
            )
            _s["actividades"]  = datos.actividades
            _s["categorias"]   = datos.categorias
            _s["planilla"]     = datos.planilla
            _s["puntos_extra"] = datos.puntos_extra
        except Exception as exc:
            logger.error("Error cargando planilla completa: %s", exc)
            _s["actividades"]  = []
            _s["categorias"]   = []
            _s["planilla"]     = []
            _s["puntos_extra"] = {}

        try:
            asig_id = _s["asignacion_id"]
            per_id  = _s["periodo_id"]
            if asig_id and per_id:
                corte = Container.plan_mejoramiento_service().get_corte(asig_id, per_id)
                _s["corte"] = corte
                if corte:
                    notas = Container.plan_mejoramiento_service().listar_notas_corte(corte.id)
                    _s["notas_corte"] = {n.estudiante_id: n for n in notas}
                else:
                    _s["notas_corte"] = {}
            else:
                _s["corte"] = None
                _s["notas_corte"] = {}
        except Exception as exc:
            logger.error("Error cargando corte plan: %s", exc)
            _s["corte"] = None
            _s["notas_corte"] = {}

    async def _carga_inicial():
        _cargar_datos()
        _s["cargando"] = False
        barra_vista.refresh()
        panel_vista.refresh()

    ui.timer(0.05, _carga_inicial, once=True)

    # ── Helper de periodo ─────────────────────────────────────────────────────
    def _periodo_abierto() -> bool:
        per_id = _s["periodo_id"]
        if not per_id:
            return False
        try:
            p = Container.periodo_service().get_by_id(per_id)
            if p is None:
                return True
            return bool(p.esta_abierto)
        except Exception:
            return True

    # ── Cambio de vista ───────────────────────────────────────────────────────
    def _cambiar_vista(modo: str) -> None:
        _s["modo"] = modo
        barra_vista.refresh()
        panel_vista.refresh()

    def _recargar() -> None:
        _cargar_datos()
        barra_vista.refresh()
        panel_vista.refresh()

    def _toggle_puntos() -> None:
        _s["mostrar_puntos"] = not _s["mostrar_puntos"]
        barra_vista.refresh()
        panel_vista.refresh()

    def _guardar_definitivas() -> None:
        """
        El docente cierra sus notas del periodo: calcula y persiste la nota
        definitiva de cada estudiante del grupo. Esta acción queda registrada
        para auditoría e informe a roles superiores.

        Solo puede ejecutarse mientras el periodo esté abierto.
        La reapertura de un cierre ya guardado es exclusiva de admin/director/coordinador.
        """
        if not _periodo_abierto():
            toast_warning("El periodo está cerrado — no se pueden guardar definitivas.")
            return

        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not asig_id or not per_id:
            toast_warning("Contexto incompleto (periodo o asignación no definidos).")
            return

        def _ejecutar() -> None:
            try:
                ctx_academico = ctx.to_contexto_academico()
            except ValueError as exc:
                toast_warning(str(exc))
                return
            try:
                cierres = Container.cierre_service().cerrar_periodo(
                    asignacion_id = asig_id,
                    periodo_id    = per_id,
                    ctx           = ctx_academico,
                    usuario_id    = ctx.usuario_id,
                )
                toast_success(f"Definitivas guardadas para {len(cierres)} estudiante(s). " "El cierre quedó registrado para auditoría.")
                _cargar_datos()
                panel_vista.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error guardando definitivas: %s", exc)
                toast_error("Error al guardar definitivas.")

        confirm_dialog(
            titulo          = "Guardar definitivas del periodo",
            mensaje         = (
                "Se calculará y registrará la nota definitiva de todos los estudiantes "
                "del grupo para esta asignación y periodo. "
                "Las actividades sin nota cuentan como 0. "
                "El cierre quedará disponible para revisión de administración. "
                "Solo un rol superior puede reabrir este cierre."
            ),
            on_confirm      = _ejecutar,
            texto_confirmar = "Guardar definitivas",
            texto_cancelar  = "Cancelar",
        )

    def _guardar_puntos_extra(est_id: int, positivos: int, negativos: int) -> None:
        if not _periodo_abierto():
            raise ValueError("El periodo está cerrado — no se pueden modificar puntos extra.")
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        pe_actual = _s["puntos_extra"].get(est_id)
        pe = PuntosExtra(
            id            = pe_actual.id if pe_actual else None,
            estudiante_id = est_id,
            asignacion_id = asig_id,
            periodo_id    = per_id,
            tipo          = TipoPuntosExtra.PARTICIPACION,
            positivos     = max(0, positivos),
            negativos     = max(0, negativos),
            observacion   = pe_actual.observacion if pe_actual else None,
        )
        saved = Container.evaluacion_service().guardar_puntos_extra(pe, ctx.usuario_id)
        _s["puntos_extra"][est_id] = saved

    # ── Acciones — actividades ────────────────────────────────────────────────
    def _crear_actividad() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not asig_id or not per_id:
            toast_warning("Define el contexto desde la barra superior")
            return
        cat_id = _s["act_categoria_id"]
        if not cat_id:
            toast_warning("Selecciona una categoría")
            return
        # NuevaActividadDTO valida nombre (no vacío) y coacciona los numéricos.
        try:
            dto = NuevaActividadDTO(
                nombre       = _s["act_nombre"],
                categoria_id = cat_id,
                descripcion  = _s["act_descripcion"] or None,
                valor_maximo = _s["act_valor_max"] or 100.0,
            )
            Container.evaluacion_service().agregar_actividad(dto)
            toast_success(f"Actividad '{dto.nombre}' creada")
            _s["act_nombre"]       = ""
            _s["act_descripcion"]  = ""
            _s["act_valor_max"]    = 100.0
            _s["act_categoria_id"] = None
            _cargar_datos()
            panel_vista.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al crear actividad: %s", exc)
            toast_error("Error al crear la actividad")

    def _publicar_actividad(act_id: int, nombre: str) -> None:
        try:
            Container.evaluacion_service().publicar_actividad(act_id)
            toast_success(f"'{nombre}' publicada")
            _cargar_datos()
            panel_vista.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al publicar %s: %s", act_id, exc)
            toast_error("Error al publicar")

    def _cerrar_actividad(act_id: int, nombre: str) -> None:
        confirm_dialog(
            titulo          = "Cerrar actividad",
            mensaje         = (
                f"¿Cerrar '{nombre}'? Podrás reabrirla después si es necesario."
            ),
            on_confirm      = lambda: _ejecutar_cerrar(act_id, nombre),
            texto_confirmar = "Cerrar actividad",
            texto_cancelar  = "Cancelar",
        )

    def _ejecutar_cerrar(act_id: int, nombre: str) -> None:
        try:
            Container.evaluacion_service().cerrar_actividad(act_id)
            toast_success(f"'{nombre}' cerrada")
            _cargar_datos()
            panel_vista.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al cerrar %s: %s", act_id, exc)
            toast_error("Error al cerrar")

    def _reabrir_actividad(act_id: int, nombre: str) -> None:
        confirm_dialog(
            titulo          = "Reabrir actividad",
            mensaje         = (
                f"¿Reabrir '{nombre}'? Volverá a aceptar registro de notas."
            ),
            on_confirm      = lambda: _ejecutar_reabrir(act_id, nombre),
            texto_confirmar = "Reabrir",
            texto_cancelar  = "Cancelar",
        )

    def _ejecutar_reabrir(act_id: int, nombre: str) -> None:
        try:
            Container.evaluacion_service().reabrir_actividad(act_id)
            toast_success(f"'{nombre}' reabierta")
            _cargar_datos()
            panel_vista.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al reabrir %s: %s", act_id, exc)
            toast_error("Error al reabrir")

    def _eliminar_actividad(act_id: int, nombre: str) -> None:
        confirm_dialog(
            titulo          = "Eliminar actividad",
            mensaje         = (
                f"¿Eliminar '{nombre}'? Se borrarán también todas las notas asociadas. "
                "Esta acción es irreversible."
            ),
            on_confirm      = lambda: _ejecutar_eliminar(act_id, nombre),
            variante        = "danger",
            texto_confirmar = "Eliminar",
            texto_cancelar  = "Cancelar",
        )

    def _ejecutar_eliminar(act_id: int, nombre: str) -> None:
        try:
            Container.evaluacion_service().eliminar_actividad(act_id)
            toast_success(f"'{nombre}' eliminada")
            _cargar_datos()
            panel_vista.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al eliminar %s: %s", act_id, exc)
            toast_error("Error al eliminar")

    # ── Vista: planilla de notas (ag-Grid) ────────────────────────────────────
    def _render_planilla() -> None:
        planilla        = _s["planilla"]
        actividades     = _s["actividades"]
        categorias      = _s["categorias"]
        puntos_map      = _s["puntos_extra"]   # {est_id: PuntosExtra}
        mostrar_puntos  = _s["mostrar_puntos"]
        periodo_abierto = _periodo_abierto()

        _ESTADO_CORTE_LABELS = {
            EstadoNotaCorte.SIN_PLAN.value:  "Sin plan",
            EstadoNotaCorte.EN_PLAN.value:   "En plan",
            EstadoNotaCorte.APROBADO.value:  "Aprobó",
            EstadoNotaCorte.REPROBADO.value: "Reprobó",
        }

        if not _s["asignacion_id"] or not _s["periodo_id"]:
            with ui.element("div").classes("tablero-empty"):
                ThemeManager.icono("tune", size=32).classes("mb-2")
                ui.label(
                    "Configura el periodo y la asignación desde la barra de contexto superior."
                ).classes("tablero-empty-hint")
            return

        if not planilla:
            empty_state(
                icono=Icons.GRADES,
                titulo="Sin datos de planilla",
                descripcion="No hay estudiantes registrados para el contexto activo. Verifica el grupo y la asignación.",
            )
            return

        acts_visibles = [
            a for a in actividades
            if a.estado in (EstadoActividad.PUBLICADA, EstadoActividad.CERRADA)
        ]

        if not periodo_abierto:
            with ui.element("div").classes(
                "flex items-center gap-2 bg-warning-soft border border-warning-soft "
                "rounded p-3 mb-3 text-warning"
            ):
                ThemeManager.icono("lock", size=20)
                ui.label("Período CERRADO — Modo solo lectura").classes("font-semibold text-sm")

        color_rules = {
            "grade-bajo":     "x != null && x < 60",
            "grade-basico":   "x != null && x >= 60 && x < 80",
            "grade-alto":     "x != null && x >= 80 && x < 90",
            "grade-superior": "x != null && x >= 90",
        }

        col_defs = [{
            "headerName": "Estudiante",
            "field":      "nombre_completo",
            "pinned":     "left",
            "width":      220,
            "filter":     True,
            "sortable":   True,
        }]

        for cat in categorias:
            acts_de_cat = [a for a in acts_visibles if a.categoria_id == cat.id]
            children = []
            for act in acts_de_cat:
                children.append({
                    "headerName":    act.nombre[:20],
                    "field":         f"act_{act.id}",
                    "editable":      periodo_abierto and act.estado == EstadoActividad.PUBLICADA,
                    "width":         80,
                    "type":          "numericColumn",
                    "valueFormatter":"value != null ? Number(value).toFixed(1) : ''",
                    "cellClassRules": color_rules,
                })
            children.append({
                "headerName":    "PROM",
                "field":         f"cat_avg_{cat.id}",
                "editable":      False,
                "width":         70,
                "valueFormatter":"value != null ? Number(value).toFixed(1) : ''",
                "cellClassRules": color_rules,
            })
            col_defs.append({
                "headerName": f"{cat.nombre} ({cat.peso_porcentaje:.0f}%)",
                "children":   children,
            })

        # Columna de corte plan de mejoramiento (solo si hay corte activo)
        corte = _s["corte"]
        if corte:
            col_defs.append({
                "headerName": "Plan Mejoramiento",
                "children": [
                    {
                        "headerName":    "Corte",
                        "field":         "corte_nota",
                        "editable":      False,
                        "width":         70,
                        "type":          "numericColumn",
                        "valueFormatter":"value != null ? Number(value).toFixed(1) : '—'",
                        "cellClassRules": color_rules,
                    },
                    {
                        "headerName": "Estado",
                        "field":      "corte_estado",
                        "editable":   False,
                        "width":      85,
                        "cellClass":  "ag-cell-xs",
                    },
                ],
            })

        col_defs.append({
            "headerName":    "Definitiva",
            "field":         "definitiva",
            "pinned":        "right",
            "width":         85,
            "editable":      False,
            "valueFormatter":"value != null ? Number(value).toFixed(1) : ''",
            "cellClassRules": color_rules,
        })

        if mostrar_puntos:
            col_defs.append({
                "headerName": "Puntos extra",
                "children": [
                    {
                        "headerName":    "+",
                        "field":         "pts_pos",
                        "editable":      periodo_abierto,
                        "width":         60,
                        "type":          "numericColumn",
                        "valueFormatter":"value != null ? value : 0",
                        "cellClass":     "ag-cell-info",
                    },
                    {
                        "headerName":    "−",
                        "field":         "pts_neg",
                        "editable":      periodo_abierto,
                        "width":         60,
                        "type":          "numericColumn",
                        "valueFormatter":"value != null ? value : 0",
                        "cellClass":     "ag-cell-error",
                    },
                    {
                        "headerName":    "Bal.",
                        "field":         "pts_bal",
                        "editable":      False,
                        "width":         65,
                        "type":          "numericColumn",
                        "cellClassRules": {
                            "pts-positivo": "x != null && x > 0",
                            "pts-negativo": "x != null && x < 0",
                        },
                    },
                ],
            })

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
            if mostrar_puntos:
                pe = puntos_map.get(resultado.estudiante_id)
                row["pts_pos"] = pe.positivos if pe else 0
                row["pts_neg"] = pe.negativos if pe else 0
                row["pts_bal"] = pe.balance   if pe else 0
            # Datos de corte plan
            nc = _s["notas_corte"].get(resultado.estudiante_id)
            row["corte_nota"]   = nc.nota_al_corte if nc else None
            row["corte_estado"] = _ESTADO_CORTE_LABELS.get(nc.estado.value, nc.estado.value) if nc else None
            row_data.append(row)

        grid = ui.aggrid({
            "columnDefs":                col_defs,
            "rowData":                   row_data,
            "defaultColDef":             {"sortable": True, "resizable": True},
            "singleClickEdit":           True,
            "stopEditingWhenCellsLoseFocus": True,
        }).classes("w-full h-grid-default")

        async def on_cell_edit(e) -> None:
            # Guard: re-verificar periodo en runtime (puede haberse cerrado
            # mientras la página estaba abierta)
            if not _periodo_abierto():
                toast_warning("El periodo está cerrado — no se pueden registrar cambios.")
                panel_vista.refresh()
                return

            col_id  = e.args.get("colId", "")
            val_raw = e.args.get("newValue")
            data    = e.args.get("data", {})
            est_id  = data.get("estudiante_id")

            # ── Puntos extra ──────────────────────────────────────────────────
            if col_id in ("pts_pos", "pts_neg"):
                try:
                    new_val = max(0, int(float(val_raw or 0)))
                except (ValueError, TypeError):
                    toast_warning("Valor inválido — debe ser un número entero")
                    panel_vista.refresh()
                    return
                pe_actual = _s["puntos_extra"].get(est_id)
                positivos = new_val if col_id == "pts_pos" else (pe_actual.positivos if pe_actual else 0)
                negativos = new_val if col_id == "pts_neg" else (pe_actual.negativos if pe_actual else 0)
                try:
                    _guardar_puntos_extra(est_id, positivos, negativos)
                    toast_success(f"Pts. extra guardados (+{positivos} / −{negativos})")
                except Exception as exc:
                    logger.error("Error guardando puntos extra est=%s: %s", est_id, exc)
                    toast_error("Error al guardar puntos extra")
                    panel_vista.refresh()
                return

            # ── Notas de actividades ──────────────────────────────────────────
            if not col_id.startswith("act_"):
                return

            act_id = int(col_id.replace("act_", ""))

            if val_raw is None or str(val_raw).strip() == "":
                toast_info("Para eliminar una nota usa edición individual.")
                panel_vista.refresh()
                return

            try:
                new_val = float(val_raw)
            except (ValueError, TypeError):
                toast_warning("Valor inválido — debe ser un número")
                panel_vista.refresh()
                return

            if not (0 <= new_val <= 100):
                toast_warning("La nota debe estar entre 0 y 100")
                panel_vista.refresh()
                return

            try:
                dto = RegistrarNotaDTO(
                    estudiante_id       = est_id,
                    actividad_id        = act_id,
                    valor               = new_val,
                    usuario_registro_id = ctx.usuario_id,
                )
                Container.evaluacion_service().registrar_nota(
                    dto,
                    ctx        = ctx.to_contexto_academico(),
                    usuario_id = ctx.usuario_id,
                )
                toast_success(f"Nota {new_val:.1f} guardada")
            except ValueError as exc:
                toast_warning(str(exc))
                panel_vista.refresh()
            except Exception as exc:
                logger.error("Error guardando nota: %s", exc)
                toast_error("Error al guardar la nota")
                panel_vista.refresh()

        if periodo_abierto:
            grid.on("cellValueChanged", on_cell_edit)

    # ── Vista: gestión de actividades ─────────────────────────────────────────
    def _render_actividades() -> None:
        actividades = _s["actividades"]
        categorias  = _s["categorias"]
        cat_opts    = {c.id: c.nombre for c in categorias}

        if not _s["asignacion_id"] or not _s["periodo_id"]:
            with ui.element("div").classes("tablero-empty"):
                ThemeManager.icono("tune", size=32).classes("mb-2")
                ui.label(
                    "Configura el periodo y la asignación desde la barra de contexto superior."
                ).classes("tablero-empty-hint")
            return

        # Enlace a configuración de categorías
        with ui.row().classes("items-center gap-1 mb-4 text-sm text-muted"):
            ThemeManager.icono("info_outline", size=16)
            ui.label("Las categorías se configuran en")
            ui.link(
                "Configuración de evaluación",
                target="/evaluacion/configuracion",
            ).classes("text-primary font-medium")

        # Formulario nueva actividad
        with ui.element("div").classes("bg-subtle rounded p-4 mb-4"):
            ui.label("Nueva actividad").classes("text-sm font-semibold mb-3")
            with ui.row().classes("gap-3 items-end flex-wrap"):
                ui.input(
                    "Nombre *",
                    placeholder="Ej: Taller 1",
                ).classes("w-44").bind_value(_s, "act_nombre")
                ui.select(
                    cat_opts or {"": "Sin categorías — configúralas primero"},
                    value=None,
                    label="Categoría *",
                    on_change=lambda e: _s.__setitem__("act_categoria_id", e.value),
                ).classes("w-52")
                ui.number(
                    "Valor máximo",
                    value=100.0,
                    min=0.1,
                    step=0.5,
                ).classes("w-28").bind_value(_s, "act_valor_max")
                ui.input(
                    "Descripción",
                    placeholder="Opcional",
                ).classes("w-48").bind_value(_s, "act_descripcion")
                btn_primary("Agregar", icon="add", on_click=_crear_actividad)

        # Lista de actividades
        if not actividades:
            with ui.element("div").classes("tablero-empty mt-2"):
                ui.label("Sin actividades para este periodo y asignación.").classes(
                    "tablero-empty-hint"
                )
            return

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-3 px-3 py-2 font-semibold text-xs text-muted border-b"
            ):
                ui.label("Nombre").classes("flex-1")
                ui.label("Categoría").classes("w-36")
                ui.label("Val. máx.").classes("w-20 text-right")
                ui.label("Estado").classes("w-24 text-center")
                ui.label("").classes("w-28")

            for act in actividades:
                cat_nombre = cat_opts.get(act.categoria_id, "—")
                estado_val = act.estado.value if hasattr(act.estado, "value") else str(act.estado)
                badge_tipo = {
                    "borrador":  "neutral",
                    "publicada": "success",
                    "cerrada":   "warning",
                }.get(estado_val, "neutral")

                with ui.element("div").classes(
                    "flex items-center gap-3 px-3 py-2 border-b row-hover"
                ):
                    ui.label(act.nombre).classes("flex-1 text-sm")
                    ui.label(cat_nombre).classes("w-36 text-sm text-muted")
                    ui.label(f"{act.valor_maximo:.1f}").classes(
                        "w-20 text-right font-mono text-sm"
                    )
                    with ui.element("div").classes("w-24 flex justify-center"):
                        status_badge(estado_val.capitalize(), badge_tipo)

                    with ui.row().classes("w-28 justify-end gap-1"):
                        if act.estado == EstadoActividad.BORRADOR:
                            btn_icon(
                                "publish",
                                on_click=lambda aid=act.id, an=act.nombre: _publicar_actividad(aid, an),
                                tooltip="Publicar",
                            )
                            btn_icon(
                                "delete",
                                on_click=lambda aid=act.id, an=act.nombre: _eliminar_actividad(aid, an),
                                tooltip="Eliminar",
                                variante="danger",
                            )
                        elif act.estado == EstadoActividad.PUBLICADA:
                            btn_icon(
                                "lock",
                                on_click=lambda aid=act.id, an=act.nombre: _cerrar_actividad(aid, an),
                                tooltip="Cerrar actividad",
                            )
                            btn_icon(
                                "delete",
                                on_click=lambda aid=act.id, an=act.nombre: _eliminar_actividad(aid, an),
                                tooltip="Eliminar",
                                variante="danger",
                            )
                        elif act.estado == EstadoActividad.CERRADA:
                            btn_icon(
                                "lock_open",
                                on_click=lambda aid=act.id, an=act.nombre: _reabrir_actividad(aid, an),
                                tooltip="Reabrir actividad",
                            )

    # ── Refreshables ──────────────────────────────────────────────────────────
    @ui.refreshable
    def barra_vista() -> None:
        """Botones de vista y toggle de puntos extra."""
        modo           = _s["modo"]
        mostrar_puntos = _s["mostrar_puntos"]
        with ui.row().classes("gap-2 items-center"):
            # Vista
            if modo == "planilla":
                btn_primary(
                    "Planilla de notas",
                    icon="table_chart",
                    on_click=lambda: _cambiar_vista("planilla"),
                )
                btn_secondary(
                    "Actividades",
                    icon="assignment",
                    on_click=lambda: _cambiar_vista("actividades"),
                )
            else:
                btn_secondary(
                    "Planilla de notas",
                    icon="table_chart",
                    on_click=lambda: _cambiar_vista("planilla"),
                )
                btn_primary(
                    "Actividades",
                    icon="assignment",
                    on_click=lambda: _cambiar_vista("actividades"),
                )

            # Separador visual
            ui.element("div").classes("w-px h-6 bg-muted mx-1")

            # Toggle puntos extra (solo visible en vista planilla)
            if modo == "planilla":
                if mostrar_puntos:
                    btn_primary(
                        "Pts. extra",
                        icon="stars",
                        on_click=_toggle_puntos,
                    )
                else:
                    btn_ghost(
                        "Pts. extra",
                        icon="stars",
                        on_click=_toggle_puntos,
                    )

            # Guardar definitivas — disponible para todos los roles, solo en planilla
            if modo == "planilla":
                ui.element("div").classes("w-px h-6 bg-muted mx-1")
                periodo_ok = _periodo_abierto()
                btn = btn_secondary(
                    "Guardar definitivas",
                    icon="save",
                    on_click=_guardar_definitivas,
                )
                if not periodo_ok:
                    btn.props("disabled")

    @ui.refreshable
    def panel_vista() -> None:
        """Panel principal — renderiza la vista activa."""
        if _s.get("cargando"):
            skeleton_table(rows=15, cols=8)
            return
        if _s["modo"] == "planilla":
            _render_planilla()
        else:
            _render_actividades()

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Cabecera: título + barra de vista + recarga
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Planilla de Notas").classes("text-xl font-bold flex-1")
                    barra_vista()
                    btn_icon(
                        "refresh",
                        on_click=_recargar,
                        tooltip="Recargar datos",
                    )

            # Contenido de la vista activa
            with ui.element("div").classes("panel-card mt-4"):
                panel_vista()

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        ctx, contenido,
        page_titulo       = "Evaluación · Planilla de Notas",
        on_context_change = on_context_change,
    )


__all__ = ["planilla_notas_page"]
