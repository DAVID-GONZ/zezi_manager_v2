"""
src/interface/pages/admin/plan_estudios.py
===========================================
Editor del plan de estudios por grado.
Ruta: /admin/plan-estudios
Acceso: admin, director, coordinador

Tres bloques:
  1. Grados ofrecidos por la institución, con mín/máx de estudiantes (norma) y
     el total de horas semanales objetivo del grado.
  2. (incluido en 1) horas semanales objetivo por grado.
  3. Vinculación de asignaturas a cada grado y asignación de horas hasta
     completar el objetivo, con filtro por área y barra de progreso.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_icon
from src.interface.design.components import (
    confirm_dialog, empty_state, form_dialog, pipeline_nav, status_badge,
    toast_error, toast_success, toast_warning,
)

logger = logging.getLogger("ADMIN.PLAN_ESTUDIOS")

# Flujo de configuración del generador de horarios.
_PASOS_HORARIO = [
    ("asignaturas",  "Asignaturas",      "/admin/asignaturas"),
    ("plan",         "Plan de estudios", "/admin/plan-estudios"),
    ("asignaciones", "Asignaciones",     "/admin/asignaciones"),
    ("horarios",     "Horarios",         "/horarios"),
]

_NOMBRES_GRADO = {
    1: "Primero", 2: "Segundo", 3: "Tercero", 4: "Cuarto", 5: "Quinto",
    6: "Sexto", 7: "Séptimo", 8: "Octavo", 9: "Noveno",
    10: "Décimo", 11: "Once", 12: "Doce", 13: "Trece",
}


def _barra(actual: int, objetivo: int) -> None:
    """Barra de progreso 'asignadas / objetivo' (verde al completar, roja si excede)."""
    if not objetivo or objetivo <= 0:
        return
    pct = min(100, round(actual / objetivo * 100))
    cls = "cs-period-bar-fill"
    if actual > objetivo:
        cls += " cs-bar-danger"
    elif actual == objetivo:
        pass  # primario = completo
    with ui.element("div").classes("cs-period-bar-track"):
        ui.element("div").classes(cls).style(f"width:{pct}%")  # DYNAMIC: progreso del plan


@ui.page("/admin/plan-estudios")
def plan_estudios_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return
    if ctx.usuario_rol not in ("director", "coordinador"):
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    logger.info("Plan de estudios admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    _s: dict = {
        "grados":      [],     # list[Grado]
        "asignaturas": [],
        "areas":       [],
        "grado_sel":   None,   # numero
        "plan_map":    {},     # {asignatura_id: horas} del grado seleccionado
        # form nuevo grado
        "g_numero": None, "g_nombre": "", "g_min": 20, "g_max": 40, "g_horas": 30,
        # vincular asignatura
        "vinc_area_id": None, "vinc_asig_id": None,
    }

    # ── Carga ─────────────────────────────────────────────────────────────────
    def _cargar_catalogo() -> None:
        svc = Container.plan_estudios_service()
        infra = Container.infraestructura_service()
        try:
            _s["grados"] = svc.listar_grados()
        except Exception as exc:
            logger.error("Error cargando grados: %s", exc)
            _s["grados"] = []
        try:
            _s["asignaturas"] = sorted(infra.listar_asignaturas(), key=lambda a: a.nombre)
        except Exception as exc:
            logger.error("Error cargando asignaturas: %s", exc)
            _s["asignaturas"] = []
        try:
            _s["areas"] = infra.listar_areas()
        except Exception as exc:
            logger.error("Error cargando áreas: %s", exc)
            _s["areas"] = []
        if _s["grados"] and _s["grado_sel"] is None:
            _s["grado_sel"] = _s["grados"][0].numero

    def _cargar_plan() -> None:
        g = _s["grado_sel"]
        if g is None:
            _s["plan_map"] = {}
            return
        try:
            _s["plan_map"] = {
                p.asignatura_id: p.horas_semanales
                for p in Container.plan_estudios_service().por_grado(g)
            }
        except Exception as exc:
            logger.error("Error cargando plan del grado %s: %s", g, exc)
            _s["plan_map"] = {}

    _cargar_catalogo()
    _cargar_plan()

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _grado_obj(numero):
        return next((g for g in _s["grados"] if g.numero == numero), None)

    def _asig_nombre(aid) -> str:
        return next((a.nombre for a in _s["asignaturas"] if a.id == aid), f"#{aid}")

    def _area_de(aid):
        return next((a.area_id for a in _s["asignaturas"] if a.id == aid), None)

    # ── Acciones: grados ────────────────────────────────────────────────────────
    def _guardar_grado() -> None:
        numero = _s["g_numero"]
        if not numero:
            toast_warning("Selecciona el número de grado.")
            return
        try:
            Container.plan_estudios_service().guardar_grado(
                int(numero), str(_s["g_nombre"] or "").strip() or _NOMBRES_GRADO.get(int(numero)),
                int(_s["g_min"] or 0), int(_s["g_max"] or 1), int(_s["g_horas"] or 0),
            )
            toast_success(f"Grado {numero} guardado")
            _s["g_numero"] = None
            _s["g_nombre"] = ""
            _cargar_catalogo()
            vista.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error guardando grado: %s", exc)
            toast_error("No se pudo guardar el grado")

    def _editar_grado(g) -> None:
        def _ok(datos: dict) -> "bool | None":
            try:
                Container.plan_estudios_service().guardar_grado(
                    g.numero, str(datos.get("nombre") or "").strip() or None,
                    int(datos.get("min_estudiantes") or 0),
                    int(datos.get("max_estudiantes") or 1),
                    int(datos.get("horas_semanales") or 0),
                )
                toast_success(f"Grado {g.numero} actualizado")
                _cargar_catalogo()
                vista.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error actualizando grado: %s", exc)
                toast_error("No se pudo actualizar el grado")
                return False

        form_dialog(
            titulo=f"Editar grado {g.numero}",
            campos=[
                {"key": "nombre", "label": "Nombre", "tipo": "text", "valor": g.nombre or ""},
                {"key": "min_estudiantes", "label": "Mín. estudiantes", "tipo": "number",
                 "valor": g.min_estudiantes, "min": 0},
                {"key": "max_estudiantes", "label": "Máx. estudiantes", "tipo": "number",
                 "valor": g.max_estudiantes, "min": 1},
                {"key": "horas_semanales", "label": "Horas/semana objetivo", "tipo": "number",
                 "valor": g.horas_semanales, "min": 0},
            ],
            on_submit=_ok,
            max_width="max-w-md",
        )

    def _eliminar_grado(g) -> None:
        def _ok() -> None:
            try:
                Container.plan_estudios_service().eliminar_grado(g.numero)
                toast_success(f"Grado {g.numero} eliminado")
                if _s["grado_sel"] == g.numero:
                    _s["grado_sel"] = None
                _cargar_catalogo()
                _cargar_plan()
                vista.refresh()
            except Exception as exc:
                logger.error("Error eliminando grado: %s", exc)
                toast_error("No se pudo eliminar el grado")

        confirm_dialog(
            titulo="Eliminar grado",
            mensaje=f"¿Eliminar el grado {g.numero}? No borra el plan ya asignado.",
            on_confirm=_ok, variante="danger", texto_confirmar="Eliminar",
        )

    # ── Acciones: plan (vincular / horas) ───────────────────────────────────────
    def _seleccionar_grado(numero: int) -> None:
        _s["grado_sel"] = numero
        _s["vinc_asig_id"] = None
        _cargar_plan()
        vista.refresh()

    def _vincular() -> None:
        g, aid = _s["grado_sel"], _s["vinc_asig_id"]
        if not g or not aid:
            toast_warning("Selecciona una asignatura para vincular.")
            return
        try:
            Container.plan_estudios_service().set_horas(g, aid, 1)
            _s["vinc_asig_id"] = None
            _cargar_plan()
            vista.refresh()
        except Exception as exc:
            logger.error("Error vinculando asignatura: %s", exc)
            toast_error("No se pudo vincular la asignatura")

    def _set_horas(aid: int, valor) -> None:
        # Valores vacíos/0 se ignoran (quitar una materia es vía la ✕), para no
        # borrar la fila mientras se está escribiendo. Guarda de UX del debounce,
        # no validación de dominio: el tope 1–40 lo impone NuevoPlanEstudiosDTO.
        g = _s["grado_sel"]
        try:
            horas = int(valor or 0)
        except (TypeError, ValueError):
            return
        if horas < 1:
            return
        try:
            Container.plan_estudios_service().set_horas(g, aid, horas)
            _s["plan_map"][aid] = horas
            barra_plan.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error fijando horas: %s", exc)
            toast_error("No se pudieron guardar las horas")

    def _quitar(aid: int) -> None:
        g = _s["grado_sel"]
        try:
            # El servicio propaga la cascada (desactiva asignaciones del grado).
            _, n = Container.plan_estudios_service().eliminar(
                g, aid, cascade=True, usuario_id=ctx.usuario_id
            )
            if n:
                toast_warning(
                    f"Se quitaron {n} asignación(es) de docentes para esta materia."
                )
            else:
                toast_success("Materia quitada del plan.")
            _cargar_plan()
            vista.refresh()
        except Exception as exc:
            logger.error("Error quitando asignatura del plan: %s", exc)
            toast_error("No se pudo quitar la asignatura")

    # ── Barra de progreso del plan ──────────────────────────────────────────────
    @ui.refreshable
    def barra_plan() -> None:
        g = _grado_obj(_s["grado_sel"])
        objetivo = g.horas_semanales if g else 0
        asignadas = sum(_s["plan_map"].values())
        restantes = objetivo - asignadas
        with ui.row().classes("items-center gap-2 flex-wrap"):
            var = ("success" if objetivo and asignadas == objetivo
                   else ("error" if objetivo and asignadas > objetivo else "info"))
            status_badge(f"{asignadas} / {objetivo or '—'} h", variante=var)
            if objetivo:
                if restantes > 0:
                    ui.label(f"Faltan {restantes} h").classes("text-xs text-warning")
                elif restantes < 0:
                    ui.label(f"Excede por {-restantes} h").classes("text-xs text-error")
                else:
                    ui.label("Completo ✓").classes("text-xs text-success")
        _barra(asignadas, objetivo)

    # ── Vista completa ──────────────────────────────────────────────────────────
    @ui.refreshable
    def vista() -> None:
        # ── Sección 1: Grados ofrecidos ──────────────────────────────────
        with ui.element("div").classes("panel-card"):
            ui.label("Grados ofrecidos").classes("text-subtitle1 font-semibold")
            ui.label(
                "Define los grados de la institución, su rango de estudiantes "
                "(norma) y las horas semanales objetivo del plan."
            ).classes("text-caption text-secondary u-mb-sm")

            usados = {g.numero for g in _s["grados"]}
            num_opts = {n: f"{n} — {_NOMBRES_GRADO.get(n, n)}"
                        for n in range(1, 14) if n not in usados}
            with ui.row().classes("items-end gap-3 flex-wrap"):
                ui.select(num_opts or {None: "Todos creados"}, label="Grado *") \
                    .classes("w-44").props("dense outlined").bind_value(_s, "g_numero")
                ui.input("Nombre (opcional)").classes("w-40").props("dense outlined") \
                    .bind_value(_s, "g_nombre")
                ui.number("Mín. estud.", min=0).classes("w-28").props("dense outlined") \
                    .bind_value(_s, "g_min")
                ui.number("Máx. estud.", min=1).classes("w-28").props("dense outlined") \
                    .bind_value(_s, "g_max")
                ui.number("Horas/sem", min=0).classes("w-28").props("dense outlined") \
                    .bind_value(_s, "g_horas")
                btn_primary("Guardar grado", icon="add", on_click=_guardar_grado)

            if _s["grados"]:
                with ui.element("div").classes("u-mt-sm"):
                    with ui.element("div").classes("lista-head"):
                        ui.label("Grado").classes("w-40")
                        ui.label("Estudiantes (mín–máx)").classes("w-40")
                        ui.label("Horas objetivo").classes("w-28")
                        ui.label("").classes("flex-1")
                    for g in _s["grados"]:
                        with ui.element("div").classes("lista-fila"):
                            ui.label(f"{g.numero} · {g.nombre or _NOMBRES_GRADO.get(g.numero, '')}").classes("w-40 font-medium")
                            ui.label(f"{g.min_estudiantes} – {g.max_estudiantes}").classes("w-40 text-sm")
                            ui.label(f"{g.horas_semanales} h").classes("w-28 text-sm")
                            with ui.row().classes("flex-1 justify-end gap-1"):
                                btn_icon("edit", tooltip="Editar", on_click=lambda gg=g: _editar_grado(gg))
                                btn_icon("delete", variante="danger", tooltip="Eliminar",
                                         on_click=lambda gg=g: _eliminar_grado(gg))

        # ── Sección 3: Plan de estudios del grado ────────────────────────
        with ui.element("div").classes("panel-card u-mt-sm"):
            ui.label("Plan de estudios por grado").classes("text-subtitle1 font-semibold u-mb-xs")
            if not _s["grados"]:
                empty_state(icono=Icons.SUBJECTS, titulo="Crea primero un grado",
                            descripcion="Agrega grados arriba para definir su plan.")
                return

            ui.label("Grado").classes("parrilla-chips-label")
            with ui.element("div").classes("parrilla-chips"):
                for g in _s["grados"]:
                    cls = "parrilla-chip" + (" parrilla-chip-activo" if g.numero == _s["grado_sel"] else "")
                    chip = ui.element("div").classes(cls)
                    chip.on("click", lambda _, n=g.numero: _seleccionar_grado(n))
                    with chip:
                        ui.label(f"Grado {g.numero}")

            with ui.element("div").classes("u-mt-sm"):
                barra_plan()

            # Vincular asignatura (filtro por área)
            area_opts = {None: "Todas las áreas"}
            area_opts.update({a.id: a.nombre for a in _s["areas"]})
            f_area = _s["vinc_area_id"]
            disponibles = {
                a.id: a.nombre for a in _s["asignaturas"]
                if a.id not in _s["plan_map"] and (f_area is None or a.area_id == f_area)
            }
            with ui.row().classes("items-end gap-3 flex-wrap u-mt-sm"):
                ui.select(
                    area_opts, value=_s["vinc_area_id"], label="Filtrar por área",
                    on_change=lambda e: (_s.__setitem__("vinc_area_id", e.value), vista.refresh()),
                ).classes("w-44").props("dense outlined")
                ui.select(disponibles or {None: "Sin asignaturas"}, label="Asignatura a vincular") \
                    .classes("w-56").props("dense outlined") \
                    .bind_value(_s, "vinc_asig_id")
                btn_secondary("Vincular", icon="add_link", on_click=_vincular)

            # Tabla de asignaturas vinculadas con horas
            if not _s["plan_map"]:
                ui.label("Aún no hay asignaturas vinculadas a este grado.").classes(
                    "text-caption text-secondary u-mt-sm"
                )
            else:
                with ui.element("div").classes("u-mt-sm"):
                    with ui.element("div").classes("lista-head"):
                        ui.label("Asignatura").classes("flex-1")
                        ui.label("Horas/sem").classes("w-28")
                        ui.label("").classes("w-10")
                    for aid in sorted(_s["plan_map"], key=_asig_nombre):
                        with ui.element("div").classes("lista-fila"):
                            ui.label(_asig_nombre(aid)).classes("flex-1 text-sm")
                            ui.number(value=_s["plan_map"][aid], min=1, max=40, step=1) \
                                .classes("w-28").props("dense outlined debounce=400") \
                                .on("update:model-value",
                                    lambda e, a=aid: _set_horas(a, e.args))
                            with ui.element("div").classes("w-10 text-right"):
                                btn_icon("close", variante="danger", tooltip="Quitar",
                                         on_click=lambda a=aid: _quitar(a))

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            pipeline_nav(
                _PASOS_HORARIO, activo="plan",
                hint="Paso 2 · Por cada grado define las horas semanales de cada "
                     "asignatura hasta completar el total. Esto alimenta las asignaciones y el horario.",
            )
            vista()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Plan de estudios",
        page_subtitulo = "Grados, horas objetivo y asignaturas por grado",
        page_icono     = Icons.SUBJECTS,
    )


__all__ = ["plan_estudios_page"]
