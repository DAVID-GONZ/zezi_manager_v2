"""
src/interface/pages/evaluacion/planes_mejoramiento.py
======================================================
Gestión de Planes de Mejoramiento con corte mid-periodo.
Ruta: /evaluacion/planes
Acceso: todos los autenticados

Flujo:
  1. Seleccionar asignación y periodo.
  2. Ver estado del corte (nota_al_corte y estado para todos los estudiantes).
  3. Gestionar actividades del plan para los estudiantes EN_PLAN.
  4. Cerrar el plan por estudiante (Aprobar / Reprobar).
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_ghost, btn_icon, btn_danger
from src.interface.design.components import confirm_dialog, empty_state, form_dialog, status_badge, toast_error, toast_success, toast_warning
from src.services.plan_mejoramiento_service import (
    EstadoNotaCorte,
    NuevaActividadPlanDTO,
    CalificarNotaPlanDTO,
    CerrarPlanEstudianteDTO,
)
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("EVALUACION.PLANES")

_ROL_ADMIN = {"admin", "director", "coordinador"}

_ESTADO_LABELS = {
    EstadoNotaCorte.SIN_PLAN.value:  ("Sin plan",  "grey"),
    EstadoNotaCorte.EN_PLAN.value:   ("En plan",   "warning"),
    EstadoNotaCorte.APROBADO.value:  ("Aprobó",    "positive"),
    EstadoNotaCorte.REPROBADO.value: ("Reprobó",   "negative"),
}


@ui.page("/evaluacion/planes")
def planes_mejoramiento_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _ROLES_VALIDOS = {"admin", "director", "coordinador", "profesor"}
    if ctx.usuario_rol not in _ROLES_VALIDOS:
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    logger.info("Planes mejoramiento: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    es_admin = ctx.usuario_rol in _ROL_ADMIN

    # ── Estado mutable ─────────────────────────────────────────────────────────
    _s: dict = {
        "periodos":         [],
        "asignaciones":     [],
        "periodo_id":       None,
        "asignacion_id":    None,
        "grupo_id":         None,
        "corte":            None,    # CortePlan | None
        "notas_corte":      [],      # list[NotaCortePlan] — todos los estudiantes
        "actividades_plan": [],      # list[ActividadPlan]
        # formulario nueva actividad
        "form_act_nombre":  "",
        "form_act_peso":    0.20,
        "form_act_desc":    "",
        # Mapa estudiante_id → nombre (cargado junto con notas_corte)
        "nombres_est":      {},
        # Notas por actividad plan: {actividad_plan_id: {estudiante_id: NotaActividadPlan}}
        "notas_act":        {},
    }

    # ── Carga de datos ─────────────────────────────────────────────────────────
    def _cargar_estado_inicial() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            anio_id = config.id if config else None
            _s["periodos"] = (
                Container.periodo_service().listar_por_anio(anio_id) if anio_id else []
            )
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)
            _s["periodos"] = []

        try:
            usuario_id_filtro = ctx.usuario_id if not es_admin else None
            filtro = FiltroAsignacionesDTO(solo_activas=True, usuario_id=usuario_id_filtro)
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error cargando asignaciones: %s", exc)
            _s["asignaciones"] = []

    def _cargar_corte() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["corte"] = None
            _s["notas_corte"] = []
            _s["actividades_plan"] = []
            _s["notas_act"] = {}
            return

        svc = Container.plan_mejoramiento_service()
        try:
            corte = svc.get_corte(asig_id, per_id)
            _s["corte"] = corte
        except Exception as exc:
            logger.error("Error cargando corte: %s", exc)
            _s["corte"] = None
            _s["notas_corte"] = []
            _s["actividades_plan"] = []
            return

        if not corte:
            _s["notas_corte"] = []
            _s["actividades_plan"] = []
            _s["notas_act"] = {}
            return

        try:
            _s["notas_corte"] = svc.listar_notas_corte(corte.id)
        except Exception as exc:
            logger.error("Error cargando notas_corte: %s", exc)
            _s["notas_corte"] = []

        try:
            _s["actividades_plan"] = svc.listar_actividades(corte.id)
        except Exception as exc:
            logger.error("Error cargando actividades_plan: %s", exc)
            _s["actividades_plan"] = []

        # Cargar notas por actividad
        notas_act: dict = {}
        for act in _s["actividades_plan"]:
            try:
                notas = svc.listar_notas_actividad(act.id)
                notas_act[act.id] = {n.estudiante_id: n for n in notas}
            except Exception as exc:
                logger.error("Error cargando notas actividad %s: %s", act.id, exc)
                notas_act[act.id] = {}
        _s["notas_act"] = notas_act

        # Obtener nombres de estudiantes (desde el grupo)
        try:
            grupo_id = _s["grupo_id"]
            if grupo_id:
                ests = Container.estudiante_service().listar_por_grupo(grupo_id)
                _s["nombres_est"] = {
                    e.id: f"{e.apellido}, {e.nombre}" for e in ests
                }
        except Exception as exc:
            logger.error("Error cargando nombres: %s", exc)
            _s["nombres_est"] = {}

    def _on_selector_cambio() -> None:
        # Determinar grupo_id a partir de la asignación seleccionada
        asig_id = _s["asignacion_id"]
        asig_info = next((a for a in _s["asignaciones"] if a.asignacion_id == asig_id), None)
        _s["grupo_id"] = asig_info.grupo_id if asig_info else None
        _cargar_corte()
        panel_corte.refresh()
        panel_estudiantes.refresh()
        panel_actividades.refresh()

    _cargar_estado_inicial()

    # ── Acciones ───────────────────────────────────────────────────────────────
    def _agregar_actividad() -> None:
        corte = _s["corte"]
        if not corte:
            toast_warning("No hay corte activo")
            return
        nombre = _s["form_act_nombre"].strip()
        if not nombre:
            toast_warning("El nombre es requerido")
            return
        try:
            peso = float(_s["form_act_peso"])
        except (ValueError, TypeError):
            toast_warning("Peso inválido")
            return
        try:
            dto = NuevaActividadPlanDTO(
                corte_id=corte.id,
                asignacion_id=corte.asignacion_id,
                periodo_id=corte.periodo_id,
                nombre=nombre,
                descripcion=_s["form_act_desc"].strip() or None,
                peso=peso,
            )
            Container.plan_mejoramiento_service().agregar_actividad(dto, ctx.usuario_id)
            toast_success("Actividad añadida")
            _s["form_act_nombre"] = ""
            _s["form_act_peso"] = 0.20
            _s["form_act_desc"] = ""
            _cargar_corte()
            panel_actividades.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error añadiendo actividad: %s", exc)
            toast_error("Error al añadir actividad")

    def _calificar_nota(actividad_plan_id: int, estudiante_id: int, valor_raw: str) -> None:
        try:
            valor = float(valor_raw)
        except (ValueError, TypeError):
            toast_warning("Valor inválido")
            return
        try:
            dto = CalificarNotaPlanDTO(valor=valor, usuario_id=ctx.usuario_id)
            Container.plan_mejoramiento_service().calificar_nota(
                actividad_plan_id, estudiante_id, dto
            )
            # Actualizar cache local
            mapa = _s["notas_act"].setdefault(actividad_plan_id, {})
            nota = mapa.get(estudiante_id)
            if nota:
                mapa[estudiante_id] = nota.model_copy(update={"valor": valor})
            toast_success("Nota guardada")
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error calificando nota: %s", exc)
            toast_error("Error al guardar nota")

    def _cerrar_plan(nc, aprobado: bool) -> None:
        nombre = _s["nombres_est"].get(nc.estudiante_id, f"Est. {nc.estudiante_id}")
        accion = "Aprobar" if aprobado else "Reprobar"
        corte  = _s["corte"]

        def _ejecutar() -> None:
            try:
                dto = CerrarPlanEstudianteDTO(
                    estudiante_id=nc.estudiante_id,
                    corte_id=corte.id,
                    aprobado=aprobado,
                    usuario_cierre_id=ctx.usuario_id,
                )
                Container.plan_mejoramiento_service().cerrar_plan_estudiante(dto)
                estado_txt = "aprobado" if aprobado else "reprobado"
                toast_success(f"{nombre} — plan {estado_txt}")
                _cargar_corte()
                panel_estudiantes.refresh()
                panel_actividades.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error cerrando plan: %s", exc)
                toast_error("Error al cerrar el plan")

        confirm_dialog(
            titulo          = f"{accion} plan de {nombre}",
            mensaje         = (
                f"¿Confirmas {'aprobar' if aprobado else 'reprobar'} el plan de {nombre}? "
                "Esta acción congela la nota definitiva del plan y no se puede revertir."
            ),
            on_confirm      = _ejecutar,
            texto_confirmar = accion,
            texto_cancelar  = "Cancelar",
            variante        = "default" if aprobado else "danger",
        )

    # ── Secciones refreshables ─────────────────────────────────────────────────
    @ui.refreshable
    def panel_corte() -> None:
        corte = _s["corte"]
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]

        if not asig_id or not per_id:
            return

        with ui.element("div").classes("panel-card mt-4"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ThemeManager.icono("assignment_late", size=24)
                ui.label("Estado del Corte").classes("text-lg font-bold flex-1")
                if corte is None:
                    ui.html('<span class="badge badge-neutral text-xs">Sin corte</span>')
                else:
                    ui.badge(
                        f"Corte: {corte.fecha_ejecucion.strftime('%d/%m/%Y')}",
                        color="positive",
                    ).classes("text-xs")

            if corte is None:
                ui.label(
                    "No se ha ejecutado el corte para este periodo. "
                    "Ejecuta el corte desde Configuración de Evaluación."
                ).classes("text-sm text-grey-7")
                btn_ghost(
                    "Ir a Configuración",
                    icon="settings",
                    on_click=lambda: ui.navigate.to("/evaluacion/configuracion"),
                )
            else:
                notas = _s["notas_corte"]
                en_plan  = sum(1 for n in notas if n.estado == EstadoNotaCorte.EN_PLAN)
                sin_plan = sum(1 for n in notas if n.estado == EstadoNotaCorte.SIN_PLAN)
                cerrados = sum(
                    1 for n in notas
                    if n.estado in (EstadoNotaCorte.APROBADO, EstadoNotaCorte.REPROBADO)
                )
                with ui.row().classes("gap-4 flex-wrap text-sm"):
                    ui.label(
                        f"Peso registrado: {corte.peso_registrado * 100:.1f}%"
                    ).classes("text-grey-7")
                    ui.label(
                        f"Umbral: {corte.nota_umbral:.1f}"
                    ).classes("text-grey-7")
                    ui.label(f"Total: {len(notas)}").classes("font-semibold")
                    ui.label(f"En plan: {en_plan}").classes("font-semibold text-orange-600")
                    ui.label(f"Sin plan: {sin_plan}").classes("font-semibold text-green-600")
                    if cerrados:
                        ui.label(f"Cerrados: {cerrados}").classes("font-semibold text-blue-600")

    @ui.refreshable
    def panel_estudiantes() -> None:
        corte  = _s["corte"]
        notas  = _s["notas_corte"]
        if not corte or not notas:
            empty_state(
                icono="assignment",
                titulo="Sin planes activos",
                descripcion="No hay estudiantes con plan de mejoramiento en esta asignación y periodo.",
            )
            return

        with ui.element("div").classes("panel-card mt-4"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ThemeManager.icono("people", size=24)
                ui.label("Estudiantes — Resultado del Corte").classes("text-lg font-bold")

            # Encabezado
            with ui.element("div").classes(
                "grid gap-2 p-2 font-semibold text-sm border-b bg-grey-1"
            ).style("grid-template-columns: 1fr 80px 100px 120px"):
                ui.label("Estudiante")
                ui.label("Nota corte").classes("text-center")
                ui.label("Estado").classes("text-center")
                ui.label("Acciones").classes("text-center")

            nombres = _s["nombres_est"]
            for nc in sorted(notas, key=lambda n: nombres.get(n.estudiante_id, "")):
                nombre    = nombres.get(nc.estudiante_id, f"Est. {nc.estudiante_id}")
                lbl, color = _ESTADO_LABELS.get(nc.estado.value, (nc.estado.value, "grey"))
                ya_cerrado = nc.estado in (EstadoNotaCorte.APROBADO, EstadoNotaCorte.REPROBADO)

                with ui.element("div").classes(
                    "grid gap-2 p-2 border-b items-center"
                ).style("grid-template-columns: 1fr 80px 100px 120px"):
                    ui.label(nombre).classes("text-sm")
                    ui.label(f"{nc.nota_al_corte:.1f}").classes("text-center text-sm font-mono")
                    status_badge(lbl, color)
                    # Acciones
                    with ui.row().classes("gap-1 justify-center"):
                        if nc.estado == EstadoNotaCorte.EN_PLAN:
                            btn_primary(
                                "Aprobar",
                                icon="check",
                                on_click=lambda n=nc: _cerrar_plan(n, True),
                            ).props("size=xs dense")
                            btn_danger(
                                "Reprobar",
                                icon="close",
                                on_click=lambda n=nc: _cerrar_plan(n, False),
                            ).props("size=xs dense")
                        elif ya_cerrado:
                            nota_def = nc.nota_definitiva_plan
                            if nota_def is not None:
                                ui.label(
                                    f"Def: {nota_def:.1f}"
                                ).classes("text-xs text-grey-7")

    @ui.refreshable
    def panel_actividades() -> None:
        corte    = _s["corte"]
        acts     = _s["actividades_plan"]
        notas    = _s["notas_corte"]
        notas_act = _s["notas_act"]
        nombres  = _s["nombres_est"]

        if not corte:
            return

        en_plan = [n for n in notas if n.estado == EstadoNotaCorte.EN_PLAN]
        if not en_plan:
            return

        with ui.element("div").classes("panel-card mt-4"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ThemeManager.icono("assignment", size=24)
                ui.label("Actividades del Plan").classes("text-lg font-bold flex-1")
                # Suma de pesos
                suma = round(sum(a.peso for a in acts) * 100, 1)
                ui.badge(f"Peso total: {suma:.0f}%", color="primary" if suma <= 100 else "negative")

            # ── Planilla de actividades ────────────────────────────────────────
            if not acts:
                ui.label("No hay actividades del plan aún.").classes("text-empty text-sm mb-4")
            else:
                # Encabezado de la planilla
                n_cols = 1 + len(acts)
                header_cols = "180px " + " ".join(["80px"] * len(acts))
                with ui.element("div").classes(
                    "grid gap-1 p-2 font-semibold text-sm border-b bg-grey-1"
                ).style(f"grid-template-columns: {header_cols}"):
                    ui.label("Estudiante")
                    for act in acts:
                        ui.label(f"{act.nombre[:18]} ({act.peso*100:.0f}%)").classes(
                            "text-center text-xs"
                        )

                # Filas de estudiantes EN_PLAN
                for nc in sorted(en_plan, key=lambda n: nombres.get(n.estudiante_id, "")):
                    nombre = nombres.get(nc.estudiante_id, f"Est. {nc.estudiante_id}")
                    ya_cerrado = nc.estado in (
                        EstadoNotaCorte.APROBADO, EstadoNotaCorte.REPROBADO
                    )
                    with ui.element("div").classes(
                        "grid gap-1 p-2 border-b items-center"
                    ).style(f"grid-template-columns: {header_cols}"):
                        ui.label(nombre).classes("text-sm")
                        for act in acts:
                            nota = notas_act.get(act.id, {}).get(nc.estudiante_id)
                            valor_actual = nota.valor if nota else None
                            if ya_cerrado or not act:
                                ui.label(
                                    f"{valor_actual:.1f}" if valor_actual is not None else "—"
                                ).classes("text-center text-sm font-mono")
                            else:
                                inp = ui.input(
                                    value=str(round(valor_actual, 1)) if valor_actual is not None else "",
                                    placeholder="0-100",
                                ).classes("w-16 text-center").props("dense")
                                # Guardar al perder foco
                                inp.on("blur", lambda e, aid=act.id, eid=nc.estudiante_id: (
                                    _calificar_nota(aid, eid, e.sender.value)
                                    if e.sender.value.strip()
                                    else None
                                ))

            # ── Añadir actividad ───────────────────────────────────────────────
            with ui.element("div").classes("mt-4 pt-4 border-top-soft"):
                ui.label("Añadir actividad al plan").classes("text-sm font-semibold mb-3")
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input(
                        "Nombre *",
                        placeholder="Ej: Taller de refuerzo",
                    ).classes("w-48").bind_value(_s, "form_act_nombre")
                    ui.number(
                        "Peso (0-1) *",
                        value=_s["form_act_peso"],
                        min=0.01, max=1.0, step=0.05, precision=2,
                        on_change=lambda e: _s.__setitem__("form_act_peso", e.value),
                    ).classes("w-32")
                    ui.input(
                        "Descripción",
                        placeholder="Opcional",
                    ).classes("w-48").bind_value(_s, "form_act_desc")
                    btn_primary(
                        "Añadir",
                        icon="add",
                        on_click=_agregar_actividad,
                    )
                # Info de peso disponible
                suma_pesos = sum(a.peso for a in acts)
                disp = round((1.0 - suma_pesos) * 100, 1)
                ui.label(
                    f"Peso disponible para actividades: {disp:.1f}%"
                ).classes("text-xs text-grey-6 mt-1")

    # ── Contenido principal ────────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Header
            with ui.element("div").classes("panel-card mb-0"):
                with ui.row().classes("items-center gap-2"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Planes de Mejoramiento").classes("text-xl font-bold flex-1")
                    btn_ghost(
                        "Configuración",
                        icon="settings",
                        on_click=lambda: ui.navigate.to("/evaluacion/configuracion"),
                    )

            # Selectores de contexto
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Contexto").classes("text-base font-semibold mb-3")
                periodos_opts = {p.id: p.nombre for p in _s["periodos"]}
                asigs_opts    = {
                    a.asignacion_id: a.display_corto for a in _s["asignaciones"]
                }
                with ui.row().classes("gap-4 items-center flex-wrap"):
                    ui.select(
                        periodos_opts or {"": "Sin periodos"},
                        value=_s["periodo_id"],
                        label="Periodo *",
                        on_change=lambda e: (
                            _s.__setitem__("periodo_id", e.value),
                            _on_selector_cambio(),
                        ),
                    ).classes("w-48")
                    ui.select(
                        asigs_opts or {"": "Sin asignaciones"},
                        value=_s["asignacion_id"],
                        label="Asignación *",
                        on_change=lambda e: (
                            _s.__setitem__("asignacion_id", e.value),
                            _on_selector_cambio(),
                        ),
                    ).classes("w-72")

                if not _s["asignacion_id"] or not _s["periodo_id"]:
                    ui.label(
                        "Selecciona periodo y asignación para ver los planes."
                    ).classes("text-empty text-sm mt-2")

            # Panel corte (estado)
            panel_corte()

            # Panel estudiantes
            panel_estudiantes()

            # Panel actividades
            panel_actividades()

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        ctx, contenido,
        page_titulo       = "Evaluación · Planes de Mejoramiento",
        on_context_change = on_context_change,
    )


__all__ = ["planes_mejoramiento_page"]
