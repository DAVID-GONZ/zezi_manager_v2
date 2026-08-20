"""
src/interface/pages/evaluacion/planilla_notas.py
=================================================
Planilla de notas, actividades y categorías docentes.
Ruta:   /evaluacion/planilla
Acceso: todos los autenticados

El periodo, grupo y asignación se seleccionan mediante pills inline al
inicio del contenido. La selección es independiente del topbar.

Vistas:
  PLANILLA           — ag-Grid de estudiantes × actividades con edición inline.
  ACTIVIDADES/CATS   — layout dos columnas: actividades (izq.) y categorías (der.).

La vista activa se controla con dos botones explícitos (no un select).
El corte de Plan de Mejoramiento se gestiona en /evaluacion/configuracion.
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
    skeleton_table,
    status_badge,
    toast_error,
    toast_info,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import (
    btn_ghost,
    btn_icon,
    btn_primary,
    btn_secondary,
)
from src.interface.design.components.form_fields import (
    field_input,
    field_number,
    field_select,
)
from src.interface.design.components.inline_selectors import (
    inline_periodo_grupo_asignatura,
)
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.interface.design.theme import ThemeManager
from src.services.evaluacion_service import (
    ActualizarCategoriaDTO,
    ContextoAcademicoDTO,
    EstadoActividad,
    NuevaActividadDTO,
    NuevaCategoriaDTO,
    PuntosExtra,
    RegistrarNotaDTO,
    TipoPuntosExtra,
)
from src.services.plan_mejoramiento_service import (
    EjecutarCorteDTO,
    EstadoNotaCorte,
)

logger = logging.getLogger("EVALUACION.PLANILLA")

_ROLES_DIRECTIVOS = ("director", "coordinador")


def _build_grid_options() -> dict:
    """Configura el ag-grid para edición por teclado con movimiento de celda."""
    return {
        "defaultColDef": {
            "sortable": True,
            "resizable": True,
        },
        "singleClickEdit": True,
        "stopEditingWhenCellsLoseFocus": True,
        "suppressCellFocus": False,
        "enableCellTextSelection": True,
        "navigateToNextCell": True,
    }


def _promedio_cat(notas_dict: dict, acts_de_cat: list) -> float | None:
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

    _s: dict = {
        # Alias — actualizados por on_sel_change desde los pills inline
        "asignacion_id": None,
        "periodo_id": None,
        "grupo_id": None,
        # Claves del inline selector (escritas por inline_periodo_grupo_asignatura)
        "sel_periodo_id": None,
        "sel_periodo_nombre": "",
        "sel_grupo_id": None,
        "sel_grupo_nombre": "",
        "sel_asignacion_id": None,
        "sel_asignacion_nombre": "",
        "categorias": [],
        "actividades": [],
        "planilla": [],
        "puntos_extra": {},  # {estudiante_id: PuntosExtra}
        "mostrar_puntos": False,
        "modo": "planilla",  # "planilla" | "actividades" | "corte"
        "corte": None,  # CortePlan | None
        "notas_corte": {},  # {estudiante_id: NotaCortePlan}
        # formulario nueva actividad
        "act_nombre": "",
        "act_categoria_id": None,
        "act_valor_max": 100.0,
        "act_descripcion": "",
        # formulario nueva categoría docente
        "form_cat_nombre": "",
        "form_cat_peso": 10,   # porcentaje 1–100; se divide al guardar
        # SIEE / categorías institucionales (cargado una vez en inicio)
        "anio_id": None,
        "siee_cfg": None,
        "cats_inst": [],
        "peso_disponible": 1.0,  # cacheado; actualizado en _cargar_datos
        "cargando": True,  # skeleton mientras carga la planilla inicial
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_datos() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["actividades"] = []
            _s["categorias"] = []
            _s["planilla"] = []
            return

        try:
            datos = Container.evaluacion_service().planilla_completa(
                _s["grupo_id"], asig_id, per_id
            )
            _s["actividades"] = datos.actividades
            _s["categorias"] = datos.categorias
            _s["planilla"] = datos.planilla
            _s["puntos_extra"] = datos.puntos_extra
        except Exception as exc:
            logger.error("Error cargando planilla completa: %s", exc)
            _s["actividades"] = []
            _s["categorias"] = []
            _s["planilla"] = []
            _s["puntos_extra"] = {}

        try:
            asig_id = _s["asignacion_id"]
            per_id = _s["periodo_id"]
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

        # Cachear peso disponible — evita DB-call en el render path
        try:
            anio_id = _s.get("anio_id")
            asig_id = _s["asignacion_id"]
            per_id = _s["periodo_id"]
            if anio_id and asig_id and per_id:
                _s["peso_disponible"] = Container.evaluacion_service().peso_autonomia_disponible(
                    asig_id, per_id, anio_id
                )
            else:
                _s["peso_disponible"] = 1.0
        except Exception:
            _s["peso_disponible"] = 1.0

    async def _carga_inicial():
        _cargar_siee_cats()   # primero: establece anio_id
        _cargar_datos()        # segundo: usa anio_id para cachear peso
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
        per_id = _s["periodo_id"]
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
                    asignacion_id=asig_id,
                    periodo_id=per_id,
                    ctx=ctx_academico,
                    usuario_id=ctx.usuario_id,
                )
                toast_success(
                    f"Definitivas guardadas para {len(cierres)} estudiante(s). "
                    "El cierre quedó registrado para auditoría."
                )
                _cargar_datos()
                panel_vista.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error guardando definitivas: %s", exc)
                toast_error("Error al guardar definitivas.")

        confirm_dialog(
            titulo="Guardar definitivas del periodo",
            mensaje=(
                "Se calculará y registrará la nota definitiva de todos los estudiantes "
                "del grupo para esta asignación y periodo. "
                "Las actividades sin nota cuentan como 0. "
                "El cierre quedará disponible para revisión de administración. "
                "Solo un rol superior puede reabrir este cierre."
            ),
            on_confirm=_ejecutar,
            texto_confirmar="Guardar definitivas",
            texto_cancelar="Cancelar",
        )

    def _guardar_puntos_extra(est_id: int, positivos: int, negativos: int) -> None:
        if not _periodo_abierto():
            raise ValueError("El periodo está cerrado — no se pueden modificar puntos extra.")
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        pe_actual = _s["puntos_extra"].get(est_id)
        pe = PuntosExtra(
            id=pe_actual.id if pe_actual else None,
            estudiante_id=est_id,
            asignacion_id=asig_id,
            periodo_id=per_id,
            tipo=TipoPuntosExtra.PARTICIPACION,
            positivos=max(0, positivos),
            negativos=max(0, negativos),
            observacion=pe_actual.observacion if pe_actual else None,
        )
        saved = Container.evaluacion_service().guardar_puntos_extra(pe, ctx.usuario_id)
        _s["puntos_extra"][est_id] = saved

    # ── Helpers — SIEE y categorías ──────────────────────────────────────────
    def _cargar_siee_cats() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            _s["anio_id"] = config.id if config else None
            if _s["anio_id"]:
                svc = Container.evaluacion_service()
                _s["siee_cfg"] = svc.get_configuracion_siee(_s["anio_id"])
                _s["cats_inst"] = svc.listar_categorias_institucionales(_s["anio_id"])
        except Exception as exc:
            logger.error("Error cargando SIEE/cats inst: %s", exc)

    def _ctx_dto() -> ContextoAcademicoDTO | None:
        anio_id = _s.get("anio_id")
        per_id = _s["periodo_id"]
        asig_id = _s["asignacion_id"]
        if not anio_id or not per_id or not asig_id:
            return None
        return ContextoAcademicoDTO(
            usuario_id=ctx.usuario_id,
            anio_id=anio_id,
            periodo_id=per_id,
            asignacion_id=asig_id,
        )

    def _peso_disponible_docente() -> float:
        return _s.get("peso_disponible", 1.0)

    # ── Acciones — categorías docente ─────────────────────────────────────────
    def _crear_cat_docente() -> None:
        cdt = _ctx_dto()
        if not cdt:
            toast_warning("Selecciona periodo y asignación primero")
            return
        try:
            dto = NuevaCategoriaDTO(
                nombre=_s["form_cat_nombre"],
                peso=_s["form_cat_peso"] / 100.0,
                asignacion_id=_s["asignacion_id"],
                periodo_id=_s["periodo_id"],
                categoria_padre_id=None,
            )
            Container.evaluacion_service().agregar_categoria(dto, cdt, usuario_id=ctx.usuario_id)
            toast_success(f"Categoría '{dto.nombre}' creada")
            _s["form_cat_nombre"] = ""
            _s["form_cat_peso"] = 10
            _cargar_datos()
            panel_vista.refresh()
        except (PermissionError, ValueError) as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al crear categoría: %s", exc)
            toast_error("Error al crear la categoría")

    def _editar_cat_docente(cat) -> None:
        def _guardar(datos: dict) -> bool | None:
            try:
                nuevo_nombre = str(datos.get("nombre", "")).strip() or None
                if not nuevo_nombre:
                    toast_warning("El nombre es obligatorio")
                    return False
                nuevo_peso = (
                    float(datos["peso"]) / 100.0 if datos.get("peso") is not None else None
                )
                dto_act = ActualizarCategoriaDTO(nombre=nuevo_nombre, peso=nuevo_peso)
                Container.evaluacion_service().actualizar_categoria(
                    cat.id, dto_act, usuario_id=ctx.usuario_id
                )
                toast_success("Categoría actualizada")
                _cargar_datos()
                panel_vista.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al actualizar categoría: %s", exc)
                toast_error("Error al actualizar")
                return False

        form_dialog(
            titulo="Editar categoría",
            campos=[
                {
                    "key": "nombre",
                    "label": "Nombre *",
                    "tipo": "text",
                    "valor": cat.nombre,
                    "requerido": True,
                },
                {
                    "key": "peso",
                    "label": "Peso % *",
                    "tipo": "number",
                    "valor": round(cat.peso * 100, 1),
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "format": "%.0f",
                },
            ],
            on_submit=_guardar,
            max_width="max-w-md",
        )

    def _eliminar_cat_docente(cat) -> None:
        def _ejecutar() -> None:
            try:
                Container.evaluacion_service().eliminar_categoria(
                    cat.id, usuario_id=ctx.usuario_id
                )
                toast_success(f"'{cat.nombre}' eliminada")
                _cargar_datos()
                panel_vista.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error al eliminar categoría: %s", exc)
                toast_error("Error al eliminar")

        confirm_dialog(
            titulo="Eliminar categoría",
            mensaje=f"¿Eliminar '{cat.nombre}'? Esta acción es irreversible.",
            on_confirm=_ejecutar,
            variante="danger",
            texto_confirmar="Eliminar",
        )

    # ── Acciones — actividades ────────────────────────────────────────────────
    def _crear_actividad() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
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
                nombre=_s["act_nombre"],
                categoria_id=cat_id,
                descripcion=_s["act_descripcion"] or None,
                valor_maximo=_s["act_valor_max"] or 100.0,
            )
            Container.evaluacion_service().agregar_actividad(dto)
            toast_success(f"Actividad '{dto.nombre}' creada")
            _s["act_nombre"] = ""
            _s["act_descripcion"] = ""
            _s["act_valor_max"] = 100.0
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
            titulo="Cerrar actividad",
            mensaje=(f"¿Cerrar '{nombre}'? Podrás reabrirla después si es necesario."),
            on_confirm=lambda: _ejecutar_cerrar(act_id, nombre),
            texto_confirmar="Cerrar actividad",
            texto_cancelar="Cancelar",
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
            titulo="Reabrir actividad",
            mensaje=(f"¿Reabrir '{nombre}'? Volverá a aceptar registro de notas."),
            on_confirm=lambda: _ejecutar_reabrir(act_id, nombre),
            texto_confirmar="Reabrir",
            texto_cancelar="Cancelar",
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
            titulo="Eliminar actividad",
            mensaje=(
                f"¿Eliminar '{nombre}'? Se borrarán también todas las notas asociadas. "
                "Esta acción es irreversible."
            ),
            on_confirm=lambda: _ejecutar_eliminar(act_id, nombre),
            variante="danger",
            texto_confirmar="Eliminar",
            texto_cancelar="Cancelar",
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
        planilla = _s["planilla"]
        actividades = _s["actividades"]
        categorias = _s["categorias"]
        puntos_map = _s["puntos_extra"]  # {est_id: PuntosExtra}
        mostrar_puntos = _s["mostrar_puntos"]
        periodo_abierto = _periodo_abierto()

        _ESTADO_CORTE_LABELS = {
            EstadoNotaCorte.SIN_PLAN.value: "Sin plan",
            EstadoNotaCorte.EN_PLAN.value: "En plan",
            EstadoNotaCorte.APROBADO.value: "Aprobó",
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
            a
            for a in actividades
            if a.estado in (EstadoActividad.PUBLICADA, EstadoActividad.CERRADA)
        ]

        if not periodo_abierto:
            with ui.element("div").classes(
                "alert-panel-row bg-warning-soft border border-warning-soft mb-3 text-warning"
            ):
                ThemeManager.icono("lock", size=20)
                ui.label("Período CERRADO — Modo solo lectura").classes("font-semibold text-sm")

        color_rules = {
            "grade-bajo": "x != null && x < 60",
            "grade-basico": "x != null && x >= 60 && x < 80",
            "grade-alto": "x != null && x >= 80 && x < 90",
            "grade-superior": "x != null && x >= 90",
        }

        col_defs = [
            {
                "headerName": "Estudiante",
                "field": "nombre_completo",
                "pinned": "left",
                "width": 220,
                "filter": True,
                "sortable": True,
            }
        ]

        for cat in categorias:
            acts_de_cat = [a for a in acts_visibles if a.categoria_id == cat.id]
            children = []
            for act in acts_de_cat:
                children.append(
                    {
                        "headerName": act.nombre[:20],
                        "field": f"act_{act.id}",
                        "editable": periodo_abierto and act.estado == EstadoActividad.PUBLICADA,
                        "width": 80,
                        "type": "numericColumn",
                        "valueFormatter": "value != null ? Number(value).toFixed(1) : ''",
                        "cellClassRules": color_rules,
                    }
                )
            children.append(
                {
                    "headerName": "PROM",
                    "field": f"cat_avg_{cat.id}",
                    "editable": False,
                    "width": 70,
                    "valueFormatter": "value != null ? Number(value).toFixed(1) : ''",
                    "cellClassRules": color_rules,
                }
            )
            col_defs.append(
                {
                    "headerName": f"{cat.nombre} ({cat.peso_porcentaje:.0f}%)",
                    "children": children,
                }
            )

        # Columna de corte plan de mejoramiento (solo si hay corte activo)
        corte = _s["corte"]
        if corte:
            col_defs.append(
                {
                    "headerName": "Plan Mejoramiento",
                    "children": [
                        {
                            "headerName": "Corte",
                            "field": "corte_nota",
                            "editable": False,
                            "width": 70,
                            "type": "numericColumn",
                            "valueFormatter": "value != null ? Number(value).toFixed(1) : '—'",
                            "cellClassRules": color_rules,
                        },
                        {
                            "headerName": "Estado",
                            "field": "corte_estado",
                            "editable": False,
                            "width": 85,
                            "cellClass": "ag-cell-xs",
                        },
                    ],
                }
            )

        col_defs.append(
            {
                "headerName": "Definitiva",
                "field": "definitiva",
                "pinned": "right",
                "width": 85,
                "editable": False,
                "valueFormatter": "value != null ? Number(value).toFixed(1) : ''",
                "cellClassRules": color_rules,
            }
        )

        if mostrar_puntos:
            col_defs.append(
                {
                    "headerName": "Puntos extra",
                    "children": [
                        {
                            "headerName": "+",
                            "field": "pts_pos",
                            "editable": periodo_abierto,
                            "width": 60,
                            "type": "numericColumn",
                            "valueFormatter": "value != null ? value : 0",
                            "cellClass": "ag-cell-info",
                        },
                        {
                            "headerName": "−",
                            "field": "pts_neg",
                            "editable": periodo_abierto,
                            "width": 60,
                            "type": "numericColumn",
                            "valueFormatter": "value != null ? value : 0",
                            "cellClass": "ag-cell-error",
                        },
                        {
                            "headerName": "Bal.",
                            "field": "pts_bal",
                            "editable": False,
                            "width": 65,
                            "type": "numericColumn",
                            "cellClassRules": {
                                "pts-positivo": "x != null && x > 0",
                                "pts-negativo": "x != null && x < 0",
                            },
                        },
                    ],
                }
            )

        row_data = []
        for resultado in planilla:
            row: dict = {
                "estudiante_id": resultado.estudiante_id,
                "nombre_completo": resultado.nombre_completo,
                "definitiva": resultado.definitiva,
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
                row["pts_bal"] = pe.balance if pe else 0
            # Datos de corte plan
            nc = _s["notas_corte"].get(resultado.estudiante_id)
            row["corte_nota"] = nc.nota_al_corte if nc else None
            row["corte_estado"] = (
                _ESTADO_CORTE_LABELS.get(nc.estado.value, nc.estado.value) if nc else None
            )
            row_data.append(row)

        grid = ui.aggrid(
            {
                **_build_grid_options(),
                "columnDefs": col_defs,
                "rowData": row_data,
            }
        ).classes("w-full h-grid-default")

        async def on_cell_edit(e) -> None:
            # Guard: re-verificar periodo en runtime (puede haberse cerrado
            # mientras la página estaba abierta)
            if not _periodo_abierto():
                toast_warning("El periodo está cerrado — no se pueden registrar cambios.")
                panel_vista.refresh()
                return

            col_id = e.args.get("colId", "")
            val_raw = e.args.get("newValue")
            data = e.args.get("data", {})
            est_id = data.get("estudiante_id")

            # ── Puntos extra ──────────────────────────────────────────────────
            if col_id in ("pts_pos", "pts_neg"):
                try:
                    new_val = max(0, int(float(val_raw or 0)))
                except (ValueError, TypeError):
                    toast_warning("Valor inválido — debe ser un número entero")
                    panel_vista.refresh()
                    return
                pe_actual = _s["puntos_extra"].get(est_id)
                positivos = (
                    new_val if col_id == "pts_pos" else (pe_actual.positivos if pe_actual else 0)
                )
                negativos = (
                    new_val if col_id == "pts_neg" else (pe_actual.negativos if pe_actual else 0)
                )
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

    # ── Vista: actividades + categorías (layout 2 columnas) ──────────────────
    def _render_actividades() -> None:
        actividades = _s["actividades"]
        categorias = _s["categorias"]
        cat_opts = {c.id: c.nombre for c in categorias}

        if not _s["asignacion_id"] or not _s["periodo_id"]:
            with ui.element("div").classes("tablero-empty"):
                ThemeManager.icono("tune", size=32).classes("mb-2")
                ui.label(
                    "Configura el periodo y la asignación desde la barra de contexto superior."
                ).classes("tablero-empty-hint")
            return

        with ui.element("div").classes("flex gap-6 flex-wrap items-start"):

            # ── Columna izquierda: Actividades ────────────────────────────────
            with ui.element("div").classes("flex-1").style("min-width:360px"):

                # Formulario nueva actividad — etiquetas estáticas sobre cada campo
                with ui.element("div").classes("bg-subtle form-box u-mb-lg"):
                    with ui.row().classes("items-end gap-3 flex-wrap"):

                        with ui.element("div").classes("flex-1").style("min-width:130px"):
                            field_input(
                                "Nombre",
                                requerido=True,
                                placeholder="Ej: Taller 1",
                            ).bind_value(_s, "act_nombre")

                        with ui.element("div").classes("flex-1").style("min-width:150px"):
                            field_select(
                                "Categoría",
                                cat_opts or {"": "Sin categorías — créalas primero →"},
                                value=None,
                                requerido=True,
                                on_change=lambda e: _s.__setitem__("act_categoria_id", e.value),
                            )

                        with ui.element("div").style("width:96px"):
                            field_number(
                                "Val. máx",
                                value=100.0,
                                min=0.1,
                                step=0.5,
                            ).bind_value(_s, "act_valor_max")

                        with ui.element("div").classes("flex-1").style("min-width:120px"):
                            field_input(
                                "Descripción",
                                placeholder="Opcional",
                            ).bind_value(_s, "act_descripcion")

                        with ui.element("div").classes("flex-shrink-0").style("padding-bottom:2px"):
                            btn_primary("Agregar", icon="add", size="sm", on_click=_crear_actividad)

                # Lista de actividades agrupada por categoría
                if not actividades:
                    empty_state(
                        icono="assignment",
                        titulo="Sin actividades",
                        descripcion="Crea tus categorías a la derecha y luego agrega actividades con el formulario.",
                    )
                else:
                    acts_por_cat: dict[int, list] = {}
                    for act in actividades:
                        acts_por_cat.setdefault(act.categoria_id, []).append(act)

                    for cat in categorias:
                        acts_cat = acts_por_cat.get(cat.id, [])
                        if not acts_cat:
                            continue

                        with ui.element("div").classes("u-mb-lg"):
                            with ui.row().classes("form-row-center gap-sm u-mb-sm"):
                                ThemeManager.icono(
                                    "folder_open", size=16, color="var(--color-primary)"
                                )
                                ui.label(cat.nombre).classes("section-subtitle-sm")
                                ui.label(f"{cat.peso_porcentaje:.0f}%").classes(
                                    "text-xs text-muted font-mono"
                                )
                                ui.element("div").classes("flex-1")
                                ui.label(
                                    f"{len(acts_cat)} actividad{'es' if len(acts_cat) != 1 else ''}"
                                ).classes("text-xs text-muted")

                            with ui.element("div").classes("border-default").style(
                                "border-radius:var(--radius-lg);overflow:hidden"
                            ):
                                for act in acts_cat:
                                    estado_val = (
                                        act.estado.value
                                        if hasattr(act.estado, "value")
                                        else str(act.estado)
                                    )
                                    badge_tipo = {
                                        "borrador": "neutral",
                                        "publicada": "success",
                                        "cerrada": "warning",
                                    }.get(estado_val, "neutral")

                                    with ui.element("div").classes(
                                        "flex items-center gap-3 px-3 py-2 border-top-soft row-hover"
                                    ).style("min-height:44px"):
                                        ui.label(act.nombre).classes(
                                            "flex-1 text-sm font-medium"
                                        )
                                        if act.descripcion:
                                            ui.label(act.descripcion).classes(
                                                "text-xs text-muted text-truncate"
                                            ).style("max-width:200px")
                                        ui.label(f"{act.valor_maximo:.0f}").classes(
                                            "text-xs font-mono text-muted"
                                        ).tooltip("Valor máximo")
                                        status_badge(estado_val.capitalize(), badge_tipo)
                                        with ui.row().classes(
                                            "form-row-actions no-shrink"
                                        ).style("width:auto"):
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

            # ── Columna derecha: Categorías propias ───────────────────────────
            with ui.element("div").classes("panel-card").style(
                "width:300px;flex-shrink:0"
            ):
                siee_cfg = _s.get("siee_cfg")
                modo_siee = siee_cfg.modo.value if siee_cfg else "libre"

                with ui.row().classes("form-row-center-md u-mb-md"):
                    ThemeManager.icono("folder", size=18, color="var(--color-primary)")
                    ui.label("Mis categorías").classes("section-subtitle-sm flex-1")

                # Fallo de carga de configuración SIEE
                if not _s.get("anio_id"):
                    with ui.element("div").classes("alert-panel-row text-warning bg-warning-soft"):
                        ThemeManager.icono("warning", size=16)
                        ui.label(
                            "No se pudo cargar la configuración. "
                            "Recarga la página para intentarlo de nuevo."
                        ).classes("text-xs")
                elif modo_siee == "institucional_fijo":
                    with ui.element("div").classes(
                        "alert-panel-row text-warning bg-warning-soft"
                    ):
                        ThemeManager.icono("info", size=16)
                        ui.label(
                            "Categorías gestionadas por administración."
                        ).classes("text-xs")
                else:
                    # Barra de peso disponible
                    disponible = _peso_disponible_docente()
                    usado = round((1.0 - disponible) * 100, 1)
                    total_pct = round(disponible * 100, 1)

                    with ui.element("div").classes("u-mb-md"):
                        with ui.row().classes("items-center gap-2 u-mb-xs"):
                            ui.label("Peso disponible:").classes(
                                "text-xs font-semibold flex-1"
                            )
                            ui.label(f"{total_pct:.1f}%").classes(
                                f"text-xs font-bold {'text-success' if disponible > 0.001 else 'text-faint'}"
                            )
                            ui.label(f"(usado: {usado:.1f}%)").classes("text-xs text-muted")
                        with ui.element("div").classes("progress-bar-track bg-surface-alt"):
                            ancho_usado = min(100, round(usado))
                            color_bar = "fill-success" if usado <= 100 else "fill-error"
                            ui.element("div").classes(f"{color_bar} h-full").style(
                                f"width:{ancho_usado}%"
                            )

                    # Formulario nueva categoría — etiquetas estáticas
                    with ui.element("div").classes("bg-subtle form-box u-mb-md"):
                        ui.label("Nueva categoría").classes("text-xs font-semibold u-mb-sm")
                        with ui.row().classes("items-end gap-2"):

                            with ui.element("div").classes("flex-1"):
                                field_input(
                                    "Nombre",
                                    requerido=True,
                                    placeholder="Ej: Quizzes",
                                ).bind_value(_s, "form_cat_nombre")

                            with ui.element("div").style("width:72px"):
                                field_number(
                                    "Peso %",
                                    value=10,
                                    min=1,
                                    max=100,
                                    step=1,
                                    format="%.0f",
                                ).bind_value(_s, "form_cat_peso")

                            with ui.element("div").classes("flex-shrink-0").style("padding-bottom:2px"):
                                btn_primary("Agregar", icon="add", size="sm", on_click=_crear_cat_docente)

                    # Lista categorías docente
                    cats_doc = [c for c in categorias if not c.es_institucional]
                    if not cats_doc:
                        ui.label("Sin categorías propias aún.").classes(
                            "text-empty text-xs"
                        )
                    else:
                        with ui.element("div").classes("w-full"):
                            for cat in cats_doc:
                                with ui.element("div").classes("divider-row"):
                                    with ui.element("div").classes("flex-1 min-w-0"):
                                        ui.label(cat.nombre).classes(
                                            "text-sm font-medium text-truncate"
                                        )
                                        ui.label(f"{cat.peso_porcentaje:.1f}%").classes(
                                            "text-xs text-muted font-mono"
                                        )
                                    with ui.row().classes("form-row-actions no-shrink"):
                                        btn_icon(
                                            "edit",
                                            on_click=lambda c=cat: _editar_cat_docente(c),
                                            tooltip="Editar",
                                        )
                                        btn_icon(
                                            "delete",
                                            on_click=lambda c=cat: _eliminar_cat_docente(c),
                                            tooltip="Eliminar",
                                            variante="danger",
                                        )

    # ── Acción: ejecutar corte ────────────────────────────────────────────────
    def _ejecutar_corte() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        grupo_id = _s["grupo_id"]
        if not asig_id or not per_id or not grupo_id:
            toast_warning("Define el contexto desde la barra superior")
            return

        def _confirmar() -> None:
            try:
                dto = EjecutarCorteDTO(
                    asignacion_id=asig_id,
                    periodo_id=per_id,
                    nota_minima_aprobacion=60.0,
                    usuario_id=ctx.usuario_id,
                )
                _corte, notas = Container.plan_mejoramiento_service().ejecutar_corte(
                    dto, grupo_id
                )
                en_plan = sum(1 for n in notas if n.estado == EstadoNotaCorte.EN_PLAN)
                toast_success(
                    f"Corte ejecutado: {len(notas)} estudiantes, {en_plan} en plan de mejoramiento."
                )
                _cargar_datos()
                panel_vista.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error ejecutando corte: %s", exc)
                toast_error("Error al ejecutar el corte")

        confirm_dialog(
            titulo="Ejecutar corte de Plan de Mejoramiento",
            mensaje=(
                "Se calculará el corte con las notas registradas hasta ahora. "
                "Los estudiantes con promedio ponderado menor al umbral irán a "
                "Plan de Mejoramiento. Esta acción no se puede deshacer."
            ),
            on_confirm=_confirmar,
            texto_confirmar="Ejecutar corte",
            texto_cancelar="Cancelar",
        )

    # ── Vista: corte de plan de mejoramiento ──────────────────────────────────
    def _render_corte() -> None:
        corte = _s["corte"]
        notas = list(_s["notas_corte"].values())

        if not _s["asignacion_id"] or not _s["periodo_id"]:
            with ui.element("div").classes("tablero-empty"):
                ThemeManager.icono("tune", size=32).classes("mb-2")
                ui.label(
                    "Configura el periodo y la asignación desde la barra de contexto superior."
                ).classes("tablero-empty-hint")
            return

        if corte is None:
            with ui.element("div").classes("alert-panel-row bg-info-soft border border-info"):
                ThemeManager.icono("info", size=24, color="var(--color-info)")
                ui.label(
                    "No se ha ejecutado el corte para este periodo. "
                    "Al ejecutar, se generará una nota de corte para cada estudiante "
                    "con su promedio ponderado actual."
                ).classes("text-sm text-info flex-1")
                btn_primary(
                    "Ejecutar corte",
                    icon="play_arrow",
                    on_click=_ejecutar_corte,
                )
            return

        # Corte ejecutado — resumen
        en_plan = sum(1 for n in notas if n.estado == EstadoNotaCorte.EN_PLAN)
        sin_plan = sum(1 for n in notas if n.estado == EstadoNotaCorte.SIN_PLAN)
        aprobado = sum(1 for n in notas if n.estado == EstadoNotaCorte.APROBADO)
        reprobado = sum(1 for n in notas if n.estado == EstadoNotaCorte.REPROBADO)

        with ui.element("div").classes("form-box bg-success-soft border border-success mb-3"):
            with ui.row().classes("form-row-center u-mb-sm"):
                ThemeManager.icono("check_circle", size=24, color="var(--color-success)")
                ui.label(
                    f"Corte ejecutado el {corte.fecha_ejecucion.strftime('%d/%m/%Y')}"
                ).classes("font-semibold text-sm text-success")
            with ui.row().classes("gap-4 flex-wrap"):
                ui.label(f"Peso registrado: {corte.peso_registrado * 100:.1f}%").classes("text-sm")
                ui.label(f"Umbral aprobación: {corte.nota_umbral:.1f}").classes("text-sm")

        with ui.row().classes("form-row-center u-mt-sm flex-wrap gap-2"):
            with ui.element("div").classes("form-box-sm flex items-center gap-2 bg-subtle"):
                ui.label(f"Total: {len(notas)}").classes("text-sm font-semibold")
            with ui.element("div").classes("form-box-sm flex items-center gap-2 bg-error-soft"):
                ui.label(f"En plan: {en_plan}").classes("text-sm font-semibold text-error")
            with ui.element("div").classes(
                "form-box-sm flex items-center gap-2 bg-success-soft"
            ):
                ui.label(f"Sin plan: {sin_plan}").classes("text-sm font-semibold text-success")
            if aprobado or reprobado:
                with ui.element("div").classes(
                    "form-box-sm flex items-center gap-2 bg-info-soft"
                ):
                    ui.label(f"Aprobó plan: {aprobado}").classes(
                        "text-sm font-semibold text-info"
                    )
                with ui.element("div").classes(
                    "form-box-sm flex items-center gap-2 bg-warning-soft"
                ):
                    ui.label(f"Reprobó plan: {reprobado}").classes(
                        "text-sm font-semibold text-warning"
                    )

        with ui.row().classes("items-center gap-2 mt-4"):
            ui.label(
                "Para gestionar actividades del plan y hacer seguimiento por estudiante,"
                " ve a Planes de Mejoramiento."
            ).classes("text-xs text-muted flex-1")
            btn_ghost(
                "Ir a Planes de Mejoramiento",
                icon="open_in_new",
                on_click=lambda: ui.navigate.to("/evaluacion/planes"),
            )

    # ── Refreshables ──────────────────────────────────────────────────────────
    @ui.refreshable
    def barra_vista() -> None:
        """Toolbar: selector de vista (izq.) + acciones contextuales (der.)."""
        modo = _s["modo"]
        mostrar_puntos = _s["mostrar_puntos"]

        with ui.row().classes("items-center justify-between gap-2 flex-wrap w-full"):

            # ── Grupo izquierdo: selector de modo (segmented tabs) ────────────
            with ui.element("div").classes(
                "flex items-center gap-1 bg-subtle rounded-lg"
            ).style("padding:3px"):
                (btn_primary if modo == "planilla" else btn_ghost)(
                    "Planilla",
                    icon="table_chart",
                    size="sm",
                    on_click=lambda: _cambiar_vista("planilla"),
                )
                (btn_primary if modo == "actividades" else btn_ghost)(
                    "Actividades",
                    icon="assignment",
                    size="sm",
                    on_click=lambda: _cambiar_vista("actividades"),
                )
                (btn_primary if modo == "corte" else btn_ghost)(
                    "Corte",
                    icon="assignment_late",
                    size="sm",
                    on_click=lambda: _cambiar_vista("corte"),
                )

            # ── Grupo derecho: acciones contextuales ──────────────────────────
            with ui.row().classes("items-center gap-1"):
                if modo == "planilla":
                    (btn_primary if mostrar_puntos else btn_ghost)(
                        "Pts. extra",
                        icon="stars",
                        size="sm",
                        on_click=_toggle_puntos,
                    )
                    ui.element("div").classes("w-px h-5 bg-muted mx-1")
                    periodo_ok = _periodo_abierto()
                    btn = btn_secondary(
                        "Guardar definitivas",
                        icon="save",
                        size="sm",
                        on_click=_guardar_definitivas,
                    )
                    if not periodo_ok:
                        btn.props("disabled")
                    ui.element("div").classes("w-px h-5 bg-muted mx-1")
                btn_icon("refresh", on_click=_recargar, tooltip="Recargar datos", size="sm")

    @ui.refreshable
    def panel_vista() -> None:
        """Panel principal — renderiza la vista activa."""
        if _s.get("cargando"):
            skeleton_table(rows=15, cols=8)
            return
        modo = _s["modo"]
        if modo == "planilla":
            _render_planilla()
        elif modo == "actividades":
            _render_actividades()
        else:
            _render_corte()

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        def on_sel_change(s: dict) -> None:
            _s["asignacion_id"] = s["sel_asignacion_id"]
            _s["periodo_id"] = s["sel_periodo_id"]
            _s["grupo_id"] = s["sel_grupo_id"]
            _cargar_datos()
            panel_vista.refresh()

        inline_periodo_grupo_asignatura(
            _s,
            on_sel_change,
            usuario_id=ctx.usuario_id,
            institucion_id=ctx.institucion_id,
            usuario_rol=ctx.usuario_rol,
            preselect_periodo=True,
        )

        with ui.element("div").classes("page-stack"):
            # Cabecera: título en fila propia, toolbar en fila separada
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 u-mb-sm"):
                    ThemeManager.icono(Icons.GRADES, size=20, color="var(--color-primary)")
                    ui.label("Planilla de Notas").classes("section-title-xl")
                barra_vista()

            # Contenido de la vista activa
            with ui.element("div").classes("panel-card mt-4"):
                panel_vista()

    app_layout(
        ctx,
        contenido,
        page_titulo="Evaluación · Planilla de Notas",
    )


__all__ = ["planilla_notas_page"]
