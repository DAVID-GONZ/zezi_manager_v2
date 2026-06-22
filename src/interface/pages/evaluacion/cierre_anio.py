"""
src/interface/pages/evaluacion/cierre_anio.py
=============================================
Cierre anual por grupo.
Ruta: /evaluacion/cierre-anio
Acceso: admin, director (solo ellos)

Genera las notas definitivas anuales para todos los estudiantes
de un grupo. Requiere que todos los periodos estén cerrados.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_danger, btn_icon
from src.services.cierre_service import ContextoAcademicoDTO
from src.interface.design.components import confirm_dialog, toast_error, toast_success, toast_warning

logger = logging.getLogger("EVALUACION.CIERRE_ANIO")


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def cierre_anio_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Cierre año: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "grupos":      [],
        "anio":        None,
        "grupo_id":    None,
        "resultado":   [],
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error cargando grupos: %s", exc)
            _s["grupos"] = []

        try:
            _s["anio"] = Container.configuracion_service().get_activa()
        except Exception as exc:
            logger.error("Error cargando año activo: %s", exc)
            _s["anio"] = None

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _abrir_confirmar_cierre() -> None:
        grupo_id = _s["grupo_id"]
        anio = _s["anio"]
        if not grupo_id:
            toast_warning("Seleccione un grupo")
            return
        if not anio:
            toast_warning("No hay año lectivo activo")
            return

        grupo_nombre = next(
            (g.codigo for g in _s["grupos"] if g.id == grupo_id), str(grupo_id)
        )

        def _ejecutar_cierre() -> None:
            try:
                ctx_dto = ContextoAcademicoDTO(
                    usuario_id=ctx.usuario_id,
                    anio_id=anio.id,
                    periodo_id=1,   # requerido por DTO pero no relevante en cierre año
                    grupo_id=grupo_id,
                )
                resultado = Container.cierre_service().cerrar_anio(
                    grupo_id, anio.id, ctx_dto, usuario_id=ctx.usuario_id
                )
                _s["resultado"] = resultado
                toast_success(f"Año cerrado. {len(resultado)} cierres generados.")
                tabla_resultado.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error al cerrar año: %s", exc)
                toast_error("Error al cerrar el año")

        confirm_dialog(
            titulo="Confirmar cierre de año",
            mensaje=(
                f"Se generarán notas definitivas anuales para todos los estudiantes del grupo. "
                f"Grupo: {grupo_nombre} — Año: {anio.anio}. "
                "Requiere todos los periodos cerrados. Esta acción no se puede deshacer."
            ),
            on_confirm=_ejecutar_cierre,
            variante="danger",
            texto_confirmar="Cerrar año",
            texto_cancelar="Cancelar",
        )

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def tabla_resultado() -> None:
        resultado = _s["resultado"]
        if not resultado:
            return

        ui.label(f"Cierres generados — {len(resultado)} registros").classes(
            "text-base font-semibold mb-2"
        )
        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-3 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Estudiante ID").classes("w-32")
                ui.label("Asignación ID").classes("w-32")
                ui.label("Nota anual").classes("w-28 text-right")
                ui.label("Perdió").classes("w-20 text-center")
                ui.label("Fecha").classes("w-36")

            for c in resultado:
                with ui.element("div").classes("flex items-center gap-3 p-2 border-b"):
                    ui.label(str(c.estudiante_id)).classes("w-32 font-mono text-sm")
                    ui.label(str(c.asignacion_id)).classes("w-32 font-mono text-sm")
                    ui.label(f"{c.nota_definitiva_anual:.1f}").classes(
                        "w-28 text-right font-mono font-semibold text-sm"
                    )
                    perdio_clase = "badge-error" if c.perdio else "badge-success"
                    ui.badge("Sí" if c.perdio else "No").classes(
                        f"w-20 text-center {perdio_clase}"
                    )
                    fecha_str = (
                        c.fecha_cierre.strftime("%d/%m/%Y") if c.fecha_cierre else "—"
                    )
                    ui.label(fecha_str).classes("w-36 text-sm text-muted")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ThemeManager.icono(Icons.CLOSE_PERIOD, size=22, color="var(--color-negative)")
                    ui.label("Cierre de Año").classes("text-xl font-bold")

                # Info año activo
                anio = _s["anio"]
                if anio:
                    with ui.row().classes("items-center gap-3 mb-4"):
                        ui.label("Año lectivo activo:").classes("text-sm font-semibold")
                        ui.badge(str(anio.anio)).classes("badge-primary")
                else:
                    with ui.element("div").classes("p-3 rounded border border-error bg-error-soft mb-4"):
                        ui.label("No hay año lectivo activo. Configure uno antes de continuar.").classes(
                            "text-sm text-error"
                        )

                grupos_opts = {g.id: g.codigo for g in _s["grupos"]}
                with ui.row().classes("gap-4 items-center flex-wrap"):
                    ui.select(
                        grupos_opts or {"": "Sin grupos"},
                        value=None,
                        label="Grupo *",
                        on_change=lambda e: _s.__setitem__("grupo_id", e.value),
                    ).classes("w-48")
                    btn_icon("refresh", on_click=lambda: (_cargar_estado()), tooltip="Recargar")

            # Advertencia prominente
            with ui.element("div").classes("panel-card mt-4"):
                with ui.element("div").classes(
                    "p-4 rounded border border-error bg-error-soft"
                ):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ThemeManager.icono(Icons.WARNING, size=20, color="var(--color-error)")
                        ui.label("Precauciones importantes").classes(
                            "font-bold text-error"
                        )
                    ui.label(
                        "1. Todos los periodos del grupo deben estar cerrados antes de ejecutar el cierre anual."
                    ).classes("text-sm text-error mb-1")
                    ui.label(
                        "2. El sistema generará notas definitivas anuales calculando el promedio ponderado de todos los periodos."
                    ).classes("text-sm text-error mb-1")
                    ui.label(
                        "3. Esta operación no se puede deshacer. Verifique que los datos del periodo están correctos."
                    ).classes("text-sm text-error")

            # Botón de cierre
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Ejecutar cierre de año").classes("text-base font-semibold mb-2")
                btn_danger("Cerrar año lectivo", icon="lock", on_click=_abrir_confirmar_cierre)

            # Tabla resultado
            with ui.element("div").classes("panel-card mt-4"):
                tabla_resultado()

    app_layout(
        ctx, contenido,
        page_titulo="Evaluación · Cierre de Año",
        mostrar_contexto=False,  # selector de grupo interno; no depende del chip (paso_41)
    )


__all__ = ["cierre_anio_page"]
