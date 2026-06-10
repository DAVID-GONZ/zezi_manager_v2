"""
src/interface/pages/evaluacion/habilitaciones.py
================================================
Gestión de Nivelación.
Ruta: /evaluacion/habilitaciones

Tab 1 — Nivelación: planilla automática para estudiantes con bajo desempeño.
           El profesor selecciona periodo y asignatura (solo sus propias asignaciones).
Tab 2 — Configuración: (implementación futura) publicación de actividades y fechas
           de entrega visibles para los estudiantes.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_ghost, btn_icon, btn_secondary
from src.interface.design.components import confirm_dialog, empty_state, form_dialog, toast_error, toast_success, toast_warning
from src.services.asignacion_service import FiltroAsignacionesDTO
from src.services.nivelacion_service import (
    NuevaActividadNivelacionDTO,
    CalificarNotaNivelacionDTO,
    CalculadorNivelacion,
)

logger = logging.getLogger("EVALUACION.HABILITACIONES")


@ui.page("/evaluacion/habilitaciones")
def habilitaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _ROLES_VALIDOS = {"admin", "director", "coordinador", "profesor"}
    if ctx.usuario_rol not in _ROLES_VALIDOS:
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    logger.info("Habilitaciones: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable global ─────────────────────────────────────────────────
    _s: dict = {
        # datos base
        "periodos":     [],
        "asignaciones": [],   # solo las del profesor (o todas si es directivo/admin)
        # nivelación
        "nivel_periodo_id":  None,
        "nivel_asig_id":     None,   # asignación seleccionada en el desplegable
        "nivel_cierres":     [],     # list[CierrePeriodo] bajo desempeño
        "nivel_actividades": [],     # list[ActividadNivelacion]
        "nivel_notas":       [],     # list[NotaNivelacion]
        "nivel_cierre":      None,   # CierreNivelacion | None (si ya cerrada)
    }

    # ── Carga de datos base ───────────────────────────────────────────────────
    def _cargar_base() -> None:
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
            # Los profesores solo ven sus propias asignaciones.
            # Roles superiores (admin, director, coordinador) ven todas.
            usuario_id_filtro = ctx.usuario_id if ctx.es_docente else None
            filtro = FiltroAsignacionesDTO(
                solo_activas=True,
                usuario_id=usuario_id_filtro,
            )
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error cargando asignaciones: %s", exc)
            _s["asignaciones"] = []

    _cargar_base()

    # ── Helpers nivelación ────────────────────────────────────────────────────

    def _asignaciones_del_profesor() -> list[int]:
        """IDs de asignaciones del usuario actual en el periodo seleccionado."""
        per_id = _s["nivel_periodo_id"]
        if per_id is None:
            return [a.asignacion_id for a in _s["asignaciones"]]
        return [
            a.asignacion_id for a in _s["asignaciones"]
            if a.periodo_id == per_id
        ]

    def _cargar_nivelacion() -> None:
        """Carga bajo-desempeño, actividades y notas para la asignación seleccionada."""
        asig_id  = _s["nivel_asig_id"]
        per_id   = _s["nivel_periodo_id"]
        if asig_id is None or per_id is None:
            _s["nivel_cierres"]     = []
            _s["nivel_actividades"] = []
            _s["nivel_notas"]       = []
            _s["nivel_cierre"]      = None
            return
        try:
            svc = Container.nivelacion_service()
            _s["nivel_cierres"]     = svc.listar_bajo_desempeno([asig_id], per_id)
            _s["nivel_actividades"] = svc.listar_actividades(asig_id, per_id)
            _s["nivel_notas"]       = svc.listar_notas(asig_id, per_id)
            _s["nivel_cierre"]      = svc.get_cierre(asig_id, per_id)
        except Exception as exc:
            logger.error("Error cargando nivelación: %s", exc)
            _s["nivel_cierres"]     = []
            _s["nivel_actividades"] = []
            _s["nivel_notas"]       = []
            _s["nivel_cierre"]      = None

    # ── Acciones nivelación ───────────────────────────────────────────────────

    def _agregar_actividad_dialog() -> None:
        asig_id = _s["nivel_asig_id"]
        per_id  = _s["nivel_periodo_id"]
        if asig_id is None or per_id is None:
            toast_warning("Seleccione asignación y periodo primero.")
            return
        if _s["nivel_cierre"] is not None:
            toast_warning("La nivelación ya está cerrada.")
            return

        def _guardar(datos: dict) -> "bool | None":
            try:
                dto = NuevaActividadNivelacionDTO(
                    asignacion_id=asig_id,
                    periodo_id=per_id,
                    nombre=str(datos.get("nombre", "")).strip(),
                    descripcion=str(datos.get("descripcion", "")).strip() or None,
                    peso=float(datos.get("peso") or 0) / 100,   # UI en % → fracción
                    fecha=None,
                )
                est_ids = [c.estudiante_id for c in _s["nivel_cierres"]]
                Container.nivelacion_service().agregar_actividad(
                    dto, est_ids, usuario_id=ctx.usuario_id
                )
                toast_success("Actividad creada")
                _cargar_nivelacion()
                planilla_nivelacion.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error creando actividad nivelación: %s", exc)
                toast_error("Error al crear actividad")
                return False

        form_dialog(
            titulo="Nueva actividad de nivelación",
            campos=[
                {"key": "nombre",      "label": "Nombre *",           "tipo": "text",
                 "placeholder": "Ej: Taller recuperación 1", "requerido": True},
                {"key": "descripcion", "label": "Descripción",         "tipo": "text",
                 "placeholder": "Opcional"},
                {"key": "peso",        "label": "Peso (%) *",          "tipo": "number",
                 "valor": 30, "min": 1, "max": 100, "step": 1, "requerido": True},
            ],
            on_submit=_guardar,
            texto_submit="Crear actividad",
        )

    def _calificar_nota(actividad_id: int, estudiante_id: int, valor_actual) -> None:
        """Abre dialog para calificar una celda."""
        if _s["nivel_cierre"] is not None:
            toast_warning("La nivelación está cerrada.")
            return

        def _guardar(datos: dict) -> "bool | None":
            try:
                dto = CalificarNotaNivelacionDTO(
                    valor=float(datos.get("nota") or 0),
                    usuario_id=ctx.usuario_id,
                )
                Container.nivelacion_service().calificar_nota(
                    actividad_id, estudiante_id, dto
                )
                toast_success("Nota guardada")
                _cargar_nivelacion()
                planilla_nivelacion.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error calificando nota: %s", exc)
                toast_error("Error al guardar nota")
                return False

        form_dialog(
            titulo=f"Calificar — Estudiante {estudiante_id}",
            campos=[
                {"key": "nota", "label": "Nota (0–100) *", "tipo": "number",
                 "valor": valor_actual if valor_actual is not None else 0.0,
                 "min": 0.0, "max": 100.0, "step": 0.5, "requerido": True},
            ],
            on_submit=_guardar,
            texto_submit="Guardar nota",
            max_width="max-w-xs",
        )

    def _cerrar_nivelacion() -> None:
        asig_id = _s["nivel_asig_id"]
        per_id  = _s["nivel_periodo_id"]
        if asig_id is None or per_id is None:
            return

        def _confirmar():
            try:
                Container.nivelacion_service().cerrar_nivelacion(
                    asig_id, per_id, usuario_id=ctx.usuario_id
                )
                toast_success("Nivelación cerrada correctamente")
                _cargar_nivelacion()
                planilla_nivelacion.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error cerrando nivelación: %s", exc)
                toast_error("Error al cerrar nivelación")

        confirm_dialog(
            titulo="Cerrar nivelación",
            mensaje=(
                "Una vez cerrada no se podrán editar las notas. "
                "El resultado quedará disponible para el boletín siguiente."
            ),
            on_confirm=_confirmar,
            variante="warning",
            texto_confirmar="Cerrar nivelación",
            texto_cancelar="Cancelar",
        )

    # ── Sección refreshable: planilla nivelación ──────────────────────────────

    @ui.refreshable
    def planilla_nivelacion() -> None:
        actividades = _s["nivel_actividades"]
        cierres     = _s["nivel_cierres"]     # list[CierrePeriodo] bajo desempeño
        notas       = _s["nivel_notas"]
        cerrado     = _s["nivel_cierre"] is not None
        asig_id     = _s["nivel_asig_id"]
        per_id      = _s["nivel_periodo_id"]

        if asig_id is None or per_id is None:
            ui.label("Seleccione una asignación y un periodo para ver la planilla.").classes(
                "text-empty mt-4"
            )
            return

        # Construir mapa de notas: (actividad_id, estudiante_id) → NotaNivelacion
        nota_map: dict[tuple[int, int], "NotaNivelacion"] = {
            (n.actividad_nivelacion_id, n.estudiante_id): n
            for n in notas
        }

        # Construir mapa de notas previas: estudiante_id → nota_definitiva del cierre
        cierre_map = {c.estudiante_id: c.nota_definitiva for c in cierres}

        # Calcular suma de pesos actual
        suma_pesos = sum(a.peso for a in actividades)

        # ── Barra de acciones ────────────────────────────────────────────────
        with ui.row().classes("items-center gap-3 mb-3 flex-wrap"):
            if cerrado:
                with ui.row().classes("items-center gap-1"):
                    ThemeManager.icono("lock", size=20, color="var(--color-error)")
                    ui.label("Nivelación cerrada").classes("text-sm text-error font-semibold")
            else:
                btn_ghost(
                    "Añadir actividad",
                    icon="add_circle_outline",
                    on_click=_agregar_actividad_dialog,
                )
                if actividades:
                    ui.label(f"Pesos: {suma_pesos:.0%}").classes(
                        "text-sm " + (
                            "text-success font-semibold" if abs(suma_pesos - 1.0) <= 0.005
                            else "text-warning"
                        )
                    )
                    btn_secondary(
                        "Cerrar nivelación",
                        icon="lock",
                        on_click=_cerrar_nivelacion,
                    )

        if not cierres:
            empty_state(
                icono="school",
                titulo="Sin estudiantes en nivelación",
                descripcion="No hay estudiantes con bajo desempeño en esta asignación y periodo.",
            )
            return

        # ── Tabla/planilla ────────────────────────────────────────────────────
        with ui.element("div").classes("w-full overflow-x-auto"):
            # Cabecera
            with ui.element("div").classes(
                "flex gap-1 p-2 font-semibold text-xs border-b bg-gray-50 rounded-t"
            ):
                ui.label("Estudiante").classes("w-32 no-shrink")
                ui.label("Nota período").classes("w-24 text-right no-shrink")
                for act in actividades:
                    with ui.element("div").classes("w-28 text-center no-shrink"):
                        ui.label(act.nombre).classes("text-truncate max-w-full")
                        ui.label(f"{act.peso:.0%}").classes("text-gray-400 text-xs")
                if actividades:
                    ui.label("Promedio pond.").classes("w-28 text-right no-shrink font-semibold")

            # Filas
            for cierre in cierres:
                est_id     = cierre.estudiante_id
                nota_previa = cierre_map.get(est_id)

                with ui.element("div").classes(
                    "flex gap-1 items-center p-2 border-b hover:bg-gray-50"
                ):
                    # Nombre/ID del estudiante
                    ui.label(str(est_id)).classes("w-32 no-shrink font-mono text-sm")

                    # Nota del período (en rojo, era bajo desempeño)
                    nota_str = f"{nota_previa:.1f}" if nota_previa is not None else "—"
                    ui.label(nota_str).classes("w-24 text-right font-mono text-sm text-error no-shrink")

                    # Celdas por actividad
                    notas_est = []
                    for act in actividades:
                        clave = (act.id, est_id)
                        nota_obj = nota_map.get(clave)
                        valor = nota_obj.valor if nota_obj else None
                        notas_est.append(nota_obj)

                        with ui.element("div").classes("w-28 text-center no-shrink"):
                            valor_str = f"{valor:.1f}" if valor is not None else "—"
                            color_cls = (
                                "text-success" if valor is not None and valor >= 60
                                else "text-error" if valor is not None
                                else "text-gray-400"
                            )
                            if cerrado:
                                ui.label(valor_str).classes(
                                    f"text-sm font-mono {color_cls}"
                                )
                            else:
                                ui.button(
                                    valor_str,
                                    on_click=lambda _act_id=act.id, _est_id=est_id, _v=valor:
                                        _calificar_nota(_act_id, _est_id, _v),
                                ).props("flat dense").classes(
                                    f"text-sm font-mono {color_cls}"
                                )

                    # Promedio ponderado
                    if actividades:
                        prom = CalculadorNivelacion.nota_definitiva(
                            [n for n in notas_est if n is not None],
                            actividades,
                        )
                        prom_str = f"{prom:.1f}" if prom is not None else "…"
                        prom_cls = (
                            "text-success font-semibold" if prom is not None and prom >= 60
                            else "text-error font-semibold" if prom is not None
                            else "text-gray-400"
                        )
                        ui.label(prom_str).classes(f"w-28 text-right font-mono text-sm {prom_cls} no-shrink")

    # ── Contenido principal ───────────────────────────────────────────────────

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.tabs().classes("w-full") as tabs:
                tab_nivel  = ui.tab("nivelacion",     label="Nivelación",             icon="school")
                tab_config = ui.tab("configuracion",  label="Configuración",          icon="settings")

            with ui.tab_panels(tabs, value="nivelacion").classes("w-full mt-0"):


                # ── Tab 1: Nivelación ─────────────────────────────────────────
                with ui.tab_panel("nivelacion"):
                    with ui.element("div").classes("panel-card"):
                        with ui.row().classes("items-center gap-2 mb-4"):
                            ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                            ui.label("Planilla de Nivelación").classes("text-xl font-bold")
                            ui.label(
                                "Estudiantes con bajo desempeño al cierre del período"
                            ).classes("text-sm text-secondary ml-2")

                        periodos_opts  = {None: "— Seleccione periodo —"}
                        periodos_opts.update({p.id: p.nombre for p in _s["periodos"]})
                        asig_opts = {None: "— Seleccione asignación —"}
                        asig_opts.update({
                            a.asignacion_id: a.display_corto
                            for a in _s["asignaciones"]
                        })

                        with ui.row().classes("gap-3 items-end flex-wrap mb-4"):
                            ui.select(
                                periodos_opts,
                                value=None,
                                label="Periodo *",
                                on_change=lambda e: (
                                    _s.__setitem__("nivel_periodo_id", e.value),
                                    _cargar_nivelacion(),
                                    planilla_nivelacion.refresh(),
                                ),
                            ).classes("w-40")
                            ui.select(
                                asig_opts,
                                value=None,
                                label="Asignación *",
                                on_change=lambda e: (
                                    _s.__setitem__("nivel_asig_id", e.value),
                                    _cargar_nivelacion(),
                                    planilla_nivelacion.refresh(),
                                ),
                            ).classes("w-60")
                            btn_icon(
                                "refresh",
                                on_click=lambda: (_cargar_nivelacion(), planilla_nivelacion.refresh()),
                                tooltip="Recargar",
                            )

                        planilla_nivelacion()

                # ── Tab 2: Configuración (implementación futura) ──────────────
                with ui.tab_panel("configuracion"):
                    with ui.element("div").classes("panel-card"):
                        with ui.row().classes("items-center gap-2 mb-2"):
                            ThemeManager.icono("settings", size=22, color="var(--color-secondary)")
                            ui.label("Configuración de nivelación").classes("text-xl font-bold")

                        # Banner de implementación futura
                        with ui.element("div").classes(
                            "flex items-start gap-3 p-4 mt-2 rounded-lg border border-dashed "
                            "border-amber-300 bg-amber-50"
                        ):
                            ThemeManager.icono("construction", size=32, color="var(--color-warning)")
                            with ui.element("div"):
                                ui.label("Funcionalidad en desarrollo").classes(
                                    "text-sm font-semibold text-amber-800"
                                )
                                ui.label(
                                    "Esta sección permitirá publicar las actividades de nivelación "
                                    "con sus fechas de entrega para que los estudiantes puedan "
                                    "consultarlas desde el portal estudiantil."
                                ).classes("text-sm text-amber-700 mt-1")

                    # Vista previa de lo que vendrá
                    with ui.element("div").classes("panel-card mt-4"):
                        ui.label("Próximas funcionalidades").classes(
                            "text-base font-semibold mb-3"
                        )
                        funcionalidades = [
                            (
                                "list_alt",
                                "Listado de nivelaciones configuradas",
                                "Ver todas las actividades de nivelación creadas, por asignatura "
                                "y período, con su estado de cierre.",
                            ),
                            (
                                "event",
                                "Fechas de entrega por actividad",
                                "Asignar una fecha límite a cada actividad de nivelación para "
                                "que los estudiantes conozcan el cronograma.",
                            ),
                            (
                                "visibility",
                                "Publicación hacia estudiantes",
                                "Controlar qué actividades son visibles en el portal estudiantil "
                                "y cuáles permanecen ocultas hasta que el docente las habilite.",
                            ),
                            (
                                "notifications",
                                "Notificaciones automáticas",
                                "Enviar alertas a los estudiantes con bajo desempeño cuando una "
                                "nueva actividad de nivelación esté disponible.",
                            ),
                        ]
                        for icono, titulo, descripcion in funcionalidades:
                            with ui.element("div").classes(
                                "flex items-start gap-3 p-3 mb-2 rounded border border-gray-100 "
                                "hover:bg-gray-50"
                            ):
                                ThemeManager.icono(icono, size=20, color="var(--color-secondary)")
                                with ui.element("div"):
                                    ui.label(titulo).classes("text-sm font-medium")
                                    ui.label(descripcion).classes(
                                        "text-xs text-secondary mt-0.5"
                                    )

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        ctx, contenido,
        page_titulo="Evaluación · Nivelación",
        on_context_change=on_context_change,
    )


__all__ = ["habilitaciones_page"]
