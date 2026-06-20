"""
src/interface/pages/evaluacion/configuracion_evaluacion.py
===========================================================
Categorías de evaluación propias del docente.

Ruta:   /evaluacion/configuracion
Acceso: profesor (exclusivamente)

Roles admin/director/coordinador son redirigidos a /admin/configuracion.

Secciones:
  B — Mis categorías (solo si modo != INSTITUCIONAL_FIJO)
      - Docentes gestionan sus propias categorías dentro del peso disponible.
      - En modo MIXTO_SUBCATEGORIAS pueden anclar una categoría como
        sub-categoría de una institucional que lo permita.
      - En modo MIXTO_AUTONOMIA se muestra la barra de peso autónomo.

  C — Corte plan de mejoramiento.

La configuración institucional del SIEE se gestiona en /admin/configuracion.
La gestión de actividades (crear, publicar, cerrar, eliminar) se delega
completamente a /evaluacion/planilla.
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
    btn_primary, btn_ghost, btn_icon,
)
from src.interface.design.components import confirm_dialog, form_dialog, toast_error, toast_success, toast_warning
from src.services.evaluacion_service import (
    NuevaCategoriaDTO,
    ActualizarCategoriaDTO,
    ContextoAcademicoDTO,
)
from src.services.asignacion_service import FiltroAsignacionesDTO
from src.services.plan_mejoramiento_service import (
    EjecutarCorteDTO,
    EstadoNotaCorte,
)

logger = logging.getLogger("EVALUACION.CONFIGURACION")


@ui.page("/evaluacion/configuracion")
def configuracion_evaluacion_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("profesor",):
        # Roles institucionales: redirigir a su módulo
        ui.navigate.to("/admin/configuracion")
        return

    logger.info("Config evaluación: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "anio_id":            None,
        "periodos":           [],
        "asignaciones":       [],
        "periodo_id":         None,
        "asignacion_id":      None,
        # SIEE
        "siee_cfg":           None,    # ConfiguracionSIEE
        "cats_inst":          [],      # list[Categoria] institucionales
        # Categorías del docente (para la asignacion+periodo activos)
        "cats_docente":       [],      # list[Categoria] es_institucional=False
        # formulario nueva cat docente
        "form_nombre":        "",
        "form_peso":          0.10,
        "form_padre_id":      None,    # solo MIXTO_SUBCATEGORIAS
        # Corte plan de mejoramiento
        "corte":               None,   # CortePlan | None
        "notas_corte":         [],     # list[NotaCortePlan]
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            _s["anio_id"] = config.id if config else None
            _s["periodos"] = (
                Container.periodo_service().listar_por_anio(_s["anio_id"])
                if _s["anio_id"] else []
            )
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

    def _cargar_siee() -> None:
        anio_id = _s["anio_id"]
        if not anio_id:
            return
        try:
            svc = Container.evaluacion_service()
            _s["siee_cfg"]   = svc.get_configuracion_siee(anio_id)
            _s["cats_inst"]  = svc.listar_categorias_institucionales(anio_id)
        except Exception as exc:
            logger.error("Error cargando SIEE: %s", exc)

    def _cargar_cats_docente() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["cats_docente"] = []
            return
        try:
            todas = Container.evaluacion_service().listar_categorias(asig_id, per_id)
            _s["cats_docente"] = [c for c in todas if not c.es_institucional]
        except Exception as exc:
            logger.error("Error cargando categorías docente: %s", exc)
            _s["cats_docente"] = []

    def _cargar_corte() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["corte"] = None
            _s["notas_corte"] = []
            return
        try:
            svc = Container.plan_mejoramiento_service()
            _s["corte"] = svc.get_corte(asig_id, per_id)
            if _s["corte"]:
                _s["notas_corte"] = svc.listar_notas_corte(_s["corte"].id)
            else:
                _s["notas_corte"] = []
        except Exception as exc:
            logger.error("Error cargando corte: %s", exc)
            _s["corte"] = None
            _s["notas_corte"] = []

    _cargar_estado()
    _cargar_siee()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _modo_actual() -> str:
        cfg = _s["siee_cfg"]
        return cfg.modo.value if cfg else "libre"

    def _ctx_dto() -> ContextoAcademicoDTO | None:
        anio_id = _s["anio_id"]
        per_id  = _s["periodo_id"]
        if not anio_id or not per_id:
            return None
        return ContextoAcademicoDTO(
            usuario_id    = ctx.usuario_id,
            anio_id       = anio_id,
            periodo_id    = per_id,
            asignacion_id = _s["asignacion_id"],
        )

    def _peso_disponible_docente() -> float:
        anio_id = _s["anio_id"]
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not anio_id or not asig_id or not per_id:
            return 1.0
        try:
            return Container.evaluacion_service().peso_autonomia_disponible(
                asig_id, per_id, anio_id
            )
        except Exception:
            return 1.0

    # ── Acciones — categorías docente ─────────────────────────────────────────
    def _crear_cat_docente() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        cdt     = _ctx_dto()
        if not asig_id or not per_id or not cdt:
            toast_warning("Seleccione periodo y asignación primero")
            return

        padre_id = _s["form_padre_id"] if _modo_actual() == "mixto_subcategorias" else None

        # NuevaCategoriaDTO valida nombre (no vacío) y peso (0 < x <= 1).
        try:
            dto = NuevaCategoriaDTO(
                nombre             = _s["form_nombre"],
                peso               = _s["form_peso"],
                asignacion_id      = asig_id,
                periodo_id         = per_id,
                categoria_padre_id = padre_id,
            )
            Container.evaluacion_service().agregar_categoria(
                dto, cdt, usuario_id=ctx.usuario_id
            )
            toast_success(f"Categoría '{dto.nombre}' creada")
            _s["form_nombre"]   = ""
            _s["form_peso"]     = 0.10
            _s["form_padre_id"] = None
            _cargar_cats_docente()
            seccion_docente.refresh()
        except PermissionError as exc:
            toast_warning(str(exc))
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al crear categoría: %s", exc)
            toast_error("Error al crear la categoría")

    def _editar_cat_docente(cat) -> None:
        def _guardar(datos: dict) -> "bool | None":
            try:
                nuevo_nombre = str(datos.get("nombre", "")).strip() or None
                if not nuevo_nombre:
                    toast_warning("El nombre es obligatorio")
                    return False
                nuevo_peso = float(datos["peso"]) if datos.get("peso") is not None else None
                dto_act = ActualizarCategoriaDTO(nombre=nuevo_nombre, peso=nuevo_peso)
                Container.evaluacion_service().actualizar_categoria(
                    cat.id, dto_act, usuario_id=ctx.usuario_id
                )
                toast_success("Categoría actualizada")
                _cargar_cats_docente()
                seccion_docente.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al actualizar categoría: %s", exc)
                toast_error("Error al actualizar")
                return False

        form_dialog(
            titulo    = "Editar categoría",
            campos    = [
                {"key": "nombre", "label": "Nombre *", "tipo": "text",
                 "valor": cat.nombre, "requerido": True},
                {"key": "peso",   "label": "Peso (0.01–1.0) *", "tipo": "number",
                 "valor": cat.peso, "min": 0.01, "max": 1.0, "step": 0.01, "format": "%.2f"},
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    def _eliminar_cat_docente(cat) -> None:
        def _ejecutar() -> None:
            try:
                Container.evaluacion_service().eliminar_categoria(
                    cat.id, usuario_id=ctx.usuario_id
                )
                toast_success(f"'{cat.nombre}' eliminada")
                _cargar_cats_docente()
                seccion_docente.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error al eliminar categoría: %s", exc)
                toast_error("Error al eliminar")

        confirm_dialog(
            titulo          = "Eliminar categoría",
            mensaje         = f"¿Eliminar '{cat.nombre}'? Esta acción es irreversible.",
            on_confirm      = _ejecutar,
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    def _on_selector_cambio() -> None:
        _cargar_cats_docente()
        _cargar_corte()
        seccion_docente.refresh()
        seccion_corte.refresh()

    def _ejecutar_corte() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not asig_id or not per_id:
            toast_warning("Selecciona periodo y asignación primero")
            return
        # Obtener grupo_id de la asignacion seleccionada
        asig_info = next(
            (a for a in _s["asignaciones"] if a.asignacion_id == asig_id), None
        )
        if not asig_info:
            toast_warning("Asignación no encontrada")
            return
        grupo_id = asig_info.grupo_id

        def _confirmar() -> None:
            try:
                dto = EjecutarCorteDTO(
                    asignacion_id=asig_id,
                    periodo_id=per_id,
                    nota_minima_aprobacion=60.0,
                    usuario_id=ctx.usuario_id,
                )
                corte, notas = Container.plan_mejoramiento_service().ejecutar_corte(dto, grupo_id)
                en_plan = sum(1 for n in notas if n.estado == EstadoNotaCorte.EN_PLAN)
                toast_success(f"Corte ejecutado: {len(notas)} estudiantes, {en_plan} en plan de mejoramiento.")
                _cargar_corte()
                seccion_corte.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error ejecutando corte: %s", exc)
                toast_error("Error al ejecutar el corte")

        confirm_dialog(
            titulo          = "Ejecutar corte de Plan de Mejoramiento",
            mensaje         = (
                "Se calculará el corte con las notas registradas hasta ahora. "
                "Los estudiantes con promedio ponderado menor al umbral irán a "
                "Plan de Mejoramiento. Esta acción no se puede deshacer."
            ),
            on_confirm      = _confirmar,
            texto_confirmar = "Ejecutar corte",
            texto_cancelar  = "Cancelar",
        )

    # ── Secciones refreshables ────────────────────────────────────────────────

    @ui.refreshable
    def seccion_docente() -> None:
        """Sección B — Categorías propias del docente."""
        modo      = _modo_actual()
        cats_doc  = _s["cats_docente"]
        asig_id   = _s["asignacion_id"]
        per_id    = _s["periodo_id"]

        # En modo INSTITUCIONAL_FIJO: solo mostramos info
        if modo == "institucional_fijo":
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-2 text-warning bg-warning-soft rounded p-3"):
                    ThemeManager.icono("info", size=20)
                    ui.label(
                        "El SIEE está en modo Institucional fijo. "
                        "Las categorías son gestionadas exclusivamente por administración."
                    ).classes("text-sm")
            return

        with ui.element("div").classes("panel-card mt-4"):
            with ui.row().classes("items-center gap-2 mb-4"):
                ThemeManager.icono("edit_note", size=24, color="var(--color-primary)")
                ui.label("Mis categorías").classes("text-lg font-bold flex-1")

            # Selector de contexto
            periodos_opts   = {p.id: p.nombre for p in _s["periodos"]}
            asigs_opts      = {a.asignacion_id: a.display_corto for a in _s["asignaciones"]}

            with ui.row().classes("gap-4 items-center flex-wrap mb-4"):
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
                ).classes("w-64")

            if not asig_id or not per_id:
                ui.label("Selecciona periodo y asignación para gestionar tus categorías.").classes(
                    "text-empty text-sm"
                )
                return

            # Barra de peso disponible
            disponible = _peso_disponible_docente()
            usado      = round((1.0 - disponible) * 100, 1)
            total_pct  = round(disponible * 100, 1)

            with ui.element("div").classes("mb-4"):
                with ui.row().classes("items-center gap-3 mb-1"):
                    ui.label("Peso disponible:").classes("text-sm font-semibold")
                    ui.label(f"{total_pct:.1f}%").classes(
                        f"font-bold {'text-success' if disponible > 0.001 else 'text-faint'}"
                    )
                    ui.label(f"(usado: {usado:.1f}%)").classes("text-sm text-muted")

                # Barra visual
                with ui.element("div").classes("w-full rounded h-2 bg-surface-alt overflow-hidden"):
                    ancho_usado = min(100, round(usado))
                    color_bar   = "fill-success" if usado <= 100 else "fill-error"
                    ui.element("div").classes(f"{color_bar} h-full").style(
                        f"width: {ancho_usado}%"  # DYNAMIC: ancho proporcional al % usado
                    )

            # Formulario nueva categoría docente
            if modo == "mixto_subcategorias":
                cats_inst = _s["cats_inst"]
                padres_permitidos = {c.id: c.nombre for c in cats_inst if c.permite_subcategorias}

            with ui.element("div").classes("bg-subtle rounded p-3 mb-4"):
                ui.label("Nueva categoría").classes("text-sm font-semibold mb-2")
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input(
                        "Nombre *",
                        placeholder="Ej: Quizzes",
                    ).classes("w-44").bind_value(_s, "form_nombre")
                    ui.number(
                        "Peso (0.01–1.0)",
                        value=0.10,
                        min=0.01,
                        max=1.0,
                        step=0.01,
                        format="%.2f",
                    ).classes("w-32").bind_value(_s, "form_peso")

                    # Selector de padre solo en MIXTO_SUBCATEGORIAS
                    if modo == "mixto_subcategorias" and padres_permitidos:
                        ui.select(
                            {None: "— Sin padre —", **padres_permitidos},
                            value=None,
                            label="Sub-categoría de",
                            on_change=lambda e: _s.__setitem__("form_padre_id", e.value),
                        ).classes("w-44")

                    btn_primary("Agregar", icon="add", on_click=_crear_cat_docente)

            # Tabla de categorías docente
            if not cats_doc:
                ui.label("No has creado categorías propias para este periodo y asignación.").classes(
                    "text-empty text-sm"
                )
                return

            with ui.element("div").classes("w-full"):
                with ui.element("div").classes(
                    "flex gap-3 px-2 py-1 font-semibold text-xs text-muted border-b"
                ):
                    ui.label("Nombre").classes("flex-1")
                    ui.label("Padre").classes("w-28")
                    ui.label("Peso").classes("w-20 text-right")
                    ui.label("").classes("w-20 text-right")

                cats_inst_map = {c.id: c.nombre for c in _s["cats_inst"]}
                for cat in cats_doc:
                    padre_nombre = (
                        cats_inst_map.get(cat.categoria_padre_id, "—")
                        if cat.categoria_padre_id else "—"
                    )
                    with ui.element("div").classes("flex items-center gap-3 px-2 py-2 border-b"):
                        ui.label(cat.nombre).classes("flex-1 text-sm")
                        ui.label(padre_nombre).classes("w-28 text-xs text-muted")
                        ui.label(f"{cat.peso_porcentaje:.1f}%").classes(
                            "w-20 text-right font-mono text-sm"
                        )
                        with ui.row().classes("w-20 justify-end gap-1"):
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

    @ui.refreshable
    def seccion_corte() -> None:
        """Sección C — Corte de Plan de Mejoramiento."""
        asig_id    = _s["asignacion_id"]
        per_id     = _s["periodo_id"]
        corte      = _s["corte"]
        notas      = _s["notas_corte"]

        with ui.element("div").classes("panel-card mt-4"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ThemeManager.icono("assignment_late", size=24, color="var(--color-warning)")
                ui.label("Corte — Plan de Mejoramiento").classes("text-lg font-bold flex-1")

            if not asig_id or not per_id:
                ui.label(
                    "Selecciona periodo y asignación para ver el estado del corte."
                ).classes("text-empty text-sm")
                return

            if corte is None:
                # Sin corte: mostrar botón para ejecutar (solo admin/coord/docente)
                with ui.element("div").classes(
                    "flex items-center gap-3 p-3 bg-info-soft rounded border border-info"
                ):
                    ThemeManager.icono("info", size=24, color="var(--color-info)")
                    ui.label(
                        "No se ha ejecutado el corte para este periodo. "
                        "Al ejecutar, se generará una nota de corte para cada estudiante."
                    ).classes("text-sm text-info flex-1")
                    btn_primary(
                        "Ejecutar corte",
                        icon="play_arrow",
                        on_click=_ejecutar_corte,
                    )
                return

            # Con corte: mostrar estadísticas
            en_plan  = sum(1 for n in notas if n.estado == EstadoNotaCorte.EN_PLAN)
            sin_plan = sum(1 for n in notas if n.estado == EstadoNotaCorte.SIN_PLAN)
            aprobado = sum(1 for n in notas if n.estado == EstadoNotaCorte.APROBADO)
            reprobado = sum(1 for n in notas if n.estado == EstadoNotaCorte.REPROBADO)

            with ui.element("div").classes(
                "p-3 bg-success-soft rounded border border-success mb-3"
            ):
                with ui.row().classes("items-center gap-2 mb-2"):
                    ThemeManager.icono("check_circle", size=24, color="var(--color-success)")
                    ui.label(
                        f"Corte ejecutado el {corte.fecha_ejecucion.strftime('%d/%m/%Y')}"
                    ).classes("font-semibold text-sm text-success")
                with ui.row().classes("gap-4 flex-wrap"):
                    ui.label(
                        f"Peso registrado: {corte.peso_registrado * 100:.1f}%"
                    ).classes("text-sm")
                    ui.label(
                        f"Umbral aprobación: {corte.nota_umbral:.1f}"
                    ).classes("text-sm")

            # Conteos por estado
            with ui.row().classes("gap-3 flex-wrap mt-2"):
                with ui.element("div").classes(
                    "flex items-center gap-2 px-3 py-2 rounded bg-subtle"
                ):
                    ui.label(f"Total: {len(notas)}").classes("text-sm font-semibold")
                with ui.element("div").classes(
                    "flex items-center gap-2 px-3 py-2 rounded bg-error-soft"
                ):
                    ui.label(f"En plan: {en_plan}").classes("text-sm font-semibold text-error")
                with ui.element("div").classes(
                    "flex items-center gap-2 px-3 py-2 rounded bg-success-soft"
                ):
                    ui.label(f"Sin plan: {sin_plan}").classes("text-sm font-semibold text-success")
                if aprobado or reprobado:
                    with ui.element("div").classes(
                        "flex items-center gap-2 px-3 py-2 rounded bg-info-soft"
                    ):
                        ui.label(f"Aprobó plan: {aprobado}").classes("text-sm font-semibold text-info")
                    with ui.element("div").classes(
                        "flex items-center gap-2 px-3 py-2 rounded bg-warning-soft"
                    ):
                        ui.label(f"Reprobó plan: {reprobado}").classes("text-sm font-semibold text-warning")

            ui.label(
                "Para gestionar actividades del plan y cerrar por estudiante, "
                "ve a Planes de Mejoramiento."
            ).classes("text-xs text-muted mt-3")
            btn_ghost(
                "Ir a Planes de Mejoramiento",
                icon="open_in_new",
                on_click=lambda: ui.navigate.to("/evaluacion/planes"),
            )

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Header de página
            with ui.element("div").classes("panel-card mb-0"):
                with ui.row().classes("items-center gap-2"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Mis categorías de evaluación").classes("text-xl font-bold flex-1")
                    btn_ghost(
                        "Ir a Planilla de notas",
                        icon="table_chart",
                        on_click=lambda: ui.navigate.to("/evaluacion/planilla"),
                    )

            with ui.element("div").classes("mt-4"):
                ui.label(
                    "Configura tus categorías propias para cada asignación y periodo. "
                    "La configuración institucional del SIEE la gestiona administración."
                ).classes("text-sm text-muted mb-4")

            # Sección B — categorías docente
            seccion_docente()

            # Sección C — Corte plan de mejoramiento
            seccion_corte()

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        ctx, contenido,
        page_titulo       = "Evaluación · Configuración",
        on_context_change = on_context_change,
    )


__all__ = ["configuracion_evaluacion_page"]
