"""
src/interface/pages/admin/asignaciones.py
==========================================
Página de administración de asignaciones docente-grupo-asignatura.
Ruta: /admin/asignaciones
Acceso: admin, director

Dos perspectivas complementarias sobre la misma relación docente×grupo×materia:

  • Por grupo   — para cada grupo, las materias del plan de estudios (con sus
                  horas) y el docente asignado a cada una. Mide cobertura del plan.
  • Por docente — para cada docente, las materias/grupos que dicta y su carga
                  acumulada frente al máximo (carga_horaria_max).

Las horas provienen del plan de estudios del grado (fallback al horas global de
la asignatura), de modo que carga y cobertura son coherentes con el generador.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary, btn_secondary, btn_icon,
)
from src.interface.design.components import (
    confirm_dialog, empty_state, form_dialog, pipeline_nav, stat_card, status_badge,
    toast_error, toast_success, toast_warning,
)
from src.services.asignacion_service import NuevaAsignacionDTO, FiltroAsignacionesDTO

# Flujo de configuración del generador de horarios.
_PASOS_HORARIO = [
    ("asignaturas",  "Asignaturas",      "/admin/asignaturas"),
    ("plan",         "Plan de estudios", "/admin/plan-estudios"),
    ("asignaciones", "Asignaciones",     "/admin/asignaciones"),
    ("horarios",     "Horarios",         "/horarios"),
]

logger = logging.getLogger("ADMIN.ASIGNACIONES")


def _texto_error(exc: Exception) -> str:
    """Mensaje legible a partir de una excepción (limpia el ruido de Pydantic)."""
    errores = getattr(exc, "errors", None)
    if callable(errores):
        try:
            msgs = [
                str(e.get("msg", "")).split("Value error, ", 1)[-1].strip()
                for e in exc.errors()
            ]
            msgs = [m for m in msgs if m]
            if msgs:
                return " · ".join(msgs)
        except Exception:
            pass
    return str(exc)


def _barra_progreso(actual: int, tope: int | None, *, alerta_sobre: bool = True) -> None:
    """Barra de progreso (reusa los estilos cs-period-bar).

    alerta_sobre=True  → semáforo de carga: ámbar al acercarse, rojo al superar.
    alerta_sobre=False → barra de avance neutra (p. ej. cobertura del plan).
    """
    if not tope or tope <= 0:
        return
    pct = min(100, round(actual / tope * 100))
    cls = "cs-period-bar-fill"
    if alerta_sobre:
        if actual > tope:
            cls += " cs-bar-danger"
        elif actual >= tope * 0.85:
            cls += " cs-bar-warn"
    with ui.element("div").classes("cs-period-bar-track"):
        ui.element("div").classes(cls).style(f"width:{pct}%")  # DYNAMIC: progreso


@ui.page("/admin/asignaciones")
def asignaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("director", "coordinador", "profesor"):
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    # Directivos (director/coordinador): gestión completa.
    # Docentes: solo un tablero de lectura de sus grupos y horas.
    es_directivo = ctx.usuario_rol in ("director", "coordinador")
    es_profesor = (ctx.usuario_rol == "profesor")

    logger.info("Asignaciones: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    _s: dict = {
        "anio_id":      None,
        "periodos":     [],
        "periodo_id":   None,
        "grupos":       [],
        "docentes":     [],
        "asignaturas":  [],
        "perspectiva":  "grupo",   # "grupo" | "docente"
        "solo_con_cupo": True,     # filtrar docentes sin cupo en los selectores
        "grupo_sel_id": None,
        "docente_sel_id": None,
        "plan":         [],   # list[PlanEstudios] del grado del grupo seleccionado
        "asigns":       [],   # AsignacionInfo del grupo+periodo (activas + inactivas)
        "doc_asigns":   [],   # AsignacionInfo activas del docente+periodo
        "mis_asigns":   [],   # AsignacionInfo activas del profesor en sesión
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_catalogo() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            _s["anio_id"] = config.id if config else None
        except Exception as exc:
            logger.error("Error cargando configuración: %s", exc)
            _s["anio_id"] = None
        try:
            _s["docentes"] = Container.usuario_service().listar_docentes()
        except Exception as exc:
            logger.error("Error cargando docentes: %s", exc)
            _s["docentes"] = []
        try:
            _s["grupos"] = sorted(
                Container.infraestructura_service().listar_grupos(),
                key=lambda g: g.codigo,
            )
        except Exception as exc:
            logger.error("Error cargando grupos: %s", exc)
            _s["grupos"] = []
        try:
            _s["asignaturas"] = Container.infraestructura_service().listar_asignaturas()
        except Exception as exc:
            logger.error("Error cargando asignaturas: %s", exc)
            _s["asignaturas"] = []
        try:
            periodos = (
                Container.periodo_service().listar_por_anio(_s["anio_id"])
                if _s["anio_id"] else []
            )
            _s["periodos"] = periodos
            activo = next((p for p in periodos if not getattr(p, "cerrado", False)), None)
            sel = activo or (periodos[0] if periodos else None)
            _s["periodo_id"] = sel.id if sel else None
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)
            _s["periodos"] = []
        if _s["grupos"]:
            _s["grupo_sel_id"] = _s["grupos"][0].id
        if _s["docentes"]:
            _s["docente_sel_id"] = _s["docentes"][0].id

    def _cargar_grupo() -> None:
        gid, pid = _s["grupo_sel_id"], _s["periodo_id"]
        grupo = next((g for g in _s["grupos"] if g.id == gid), None)
        if not grupo or not pid:
            _s["plan"], _s["asigns"] = [], []
            return
        try:
            _s["plan"] = (
                Container.plan_estudios_service().por_grado(grupo.grado)
                if grupo.grado is not None else []
            )
        except Exception as exc:
            logger.error("Error cargando plan: %s", exc)
            _s["plan"] = []
        try:
            _s["asigns"] = Container.asignacion_service().listar_con_info(
                FiltroAsignacionesDTO(grupo_id=gid, periodo_id=pid, solo_activas=False)
            )
        except Exception as exc:
            logger.error("Error cargando asignaciones del grupo: %s", exc)
            _s["asigns"] = []

    def _cargar_docente() -> None:
        did, pid = _s["docente_sel_id"], _s["periodo_id"]
        if not did or not pid:
            _s["doc_asigns"] = []
            return
        try:
            _s["doc_asigns"] = Container.asignacion_service().listar_con_info(
                FiltroAsignacionesDTO(usuario_id=did, periodo_id=pid, solo_activas=True)
            )
        except Exception as exc:
            logger.error("Error cargando asignaciones del docente: %s", exc)
            _s["doc_asigns"] = []

    def _cargar_profesor() -> None:
        pid = _s["periodo_id"]
        if not pid:
            _s["mis_asigns"] = []
            return
        try:
            _s["mis_asigns"] = Container.asignacion_service().listar_con_info(
                FiltroAsignacionesDTO(usuario_id=ctx.usuario_id, periodo_id=pid, solo_activas=True)
            )
        except Exception as exc:
            logger.error("Error cargando asignaciones del profesor: %s", exc)
            _s["mis_asigns"] = []

    def _recargar() -> None:
        if es_profesor:
            _cargar_profesor()
        elif _s["perspectiva"] == "grupo":
            _cargar_grupo()
        else:
            _cargar_docente()

    _cargar_catalogo()
    if es_profesor:
        _cargar_profesor()
    else:
        _cargar_grupo()
        _cargar_docente()

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _grupo_sel():
        return next((g for g in _s["grupos"] if g.id == _s["grupo_sel_id"]), None)

    def _docente_sel():
        return next((d for d in _s["docentes"] if d.id == _s["docente_sel_id"]), None)

    def _activo_por_materia() -> dict:
        return {a.asignatura_id: a for a in _s["asigns"] if a.activo}

    def _horas(grupo_id: int, asignatura_id: int) -> int:
        return Container.asignacion_service().horas_de_asignacion(grupo_id, asignatura_id)

    def _completitud_grupo(g) -> tuple[int, int]:
        """(horas del plan ya asignadas, total del plan) para un grupo+periodo."""
        try:
            c = Container.asignacion_service().completitud_grupo(
                g.id, g.grado, _s["periodo_id"]
            )
        except Exception:
            return (0, 0)
        return (c.horas_asignadas, c.horas_totales)

    def _materias_sin_docente(grupo_id: int) -> dict:
        """{asignatura_id: 'Nombre (Nh)'} del plan del grupo sin docente asignado."""
        g = next((x for x in _s["grupos"] if x.id == grupo_id), None)
        if not g or g.grado is None:
            return {}
        asig_nombre = {a.id: a.nombre for a in _s["asignaturas"]}
        plan_horas = {p.asignatura_id: p.horas_semanales
                      for p in Container.plan_estudios_service().por_grado(g.grado)}
        try:
            pendientes = Container.asignacion_service().materias_sin_docente(
                grupo_id, g.grado, _s["periodo_id"]
            )
        except Exception:
            pendientes = []
        return {
            aid: f"{asig_nombre.get(aid, '?')} ({plan_horas.get(aid, 0)}h)"
            for aid in pendientes
        }

    # ── Acciones (Por grupo) ────────────────────────────────────────────────────
    def _set_docente(asignatura_id: int, nuevo_uid: int | None) -> None:
        gid, pid = _s["grupo_sel_id"], _s["periodo_id"]
        activo = _activo_por_materia().get(asignatura_id)
        if activo and activo.usuario_id == nuevo_uid:
            return
        svc = Container.asignacion_service()
        try:
            svc.asignar_docente_a_materia(
                grupo_id=gid, asignatura_id=asignatura_id, periodo_id=pid,
                nuevo_usuario_id=nuevo_uid, usuario_id=ctx.usuario_id,
            )
            toast_success("Asignación quitada" if nuevo_uid is None else "Docente asignado")
        except ValueError as exc:
            toast_warning(_texto_error(exc))
        except Exception as exc:
            logger.error("Error asignando docente: %s", exc)
            toast_error("No se pudo guardar la asignación")
        finally:
            _cargar_grupo()
            matriz.refresh()

    def _agregar_fuera_plan() -> None:
        grupo = _grupo_sel()
        if not grupo:
            return
        plan_ids = {p.asignatura_id for p in _s["plan"]}
        asignadas = {a.asignatura_id for a in _s["asigns"] if a.activo}
        disponibles = {
            a.id: a.nombre for a in _s["asignaturas"]
            if a.id not in plan_ids and a.id not in asignadas
        }
        if not disponibles:
            toast_warning("No hay materias adicionales para agregar.")
            return
        docentes_opts = {d.id: d.nombre_completo for d in _s["docentes"]}

        def _crear(datos: dict) -> "bool | None":
            if not datos.get("asignatura_id") or not datos.get("usuario_id"):
                toast_warning("Selecciona materia y docente.")
                return False
            try:
                Container.asignacion_service().crear_asignacion(NuevaAsignacionDTO(
                    usuario_id=datos["usuario_id"], grupo_id=_s["grupo_sel_id"],
                    asignatura_id=datos["asignatura_id"], periodo_id=_s["periodo_id"],
                ))
                toast_success("Materia agregada")
                _cargar_grupo()
                matriz.refresh()
            except ValueError as exc:
                toast_warning(_texto_error(exc))
                return False
            except Exception as exc:
                logger.error("Error agregando materia: %s", exc)
                toast_error("No se pudo agregar la materia")
                return False

        form_dialog(
            titulo="Agregar materia fuera del plan",
            campos=[
                {"key": "asignatura_id", "label": "Asignatura *", "tipo": "select",
                 "opciones": disponibles, "requerido": True},
                {"key": "usuario_id", "label": "Docente *", "tipo": "select",
                 "opciones": docentes_opts, "requerido": True},
            ],
            on_submit=_crear,
            texto_submit="Agregar",
            max_width="max-w-md",
        )

    # ── Acciones (Por docente) ──────────────────────────────────────────────────
    def _agregar_a_docente() -> None:
        did = _s["docente_sel_id"]
        if not did:
            return
        # Grupos anotados con su completitud del plan (incompletos primero).
        compl = {g.id: _completitud_grupo(g) for g in _s["grupos"]}

        def _orden(g):
            a, t = compl[g.id]
            return (bool(t) and a >= t, g.codigo)  # incompletos primero

        grupos_opts: dict = {}
        for g in sorted(_s["grupos"], key=_orden):
            asig_h, total_h = compl[g.id]
            if total_h and asig_h >= total_h:
                etiqueta = f"{g.codigo} · completo"
            elif total_h:
                etiqueta = f"{g.codigo} · faltan {total_h - asig_h}h"
            else:
                etiqueta = f"{g.codigo}"
            grupos_opts[g.id] = etiqueta

        # Cupo del docente
        try:
            carga = Container.asignacion_service().carga_docente(did, _s["periodo_id"])
            u = Container.usuario_service().get_by_id(did)
            cap = u.carga_maxima_efectiva if u else None
        except Exception:
            carga, cap = 0, None

        with ui.dialog() as dlg, ui.card().classes("andes-card form-dialog-card max-w-md"):
            ui.label("Asignar materia al docente").classes("font-h3 form-dialog-title")
            cap_txt = f"{carga}/{cap} h" if cap is not None else f"{carga} h · sin tope"
            ui.label(f"Carga actual del docente: {cap_txt}").classes("text-caption text-secondary")

            sel_grupo = ui.select(grupos_opts, label="Grupo *") \
                .classes("w-full").props("outlined")
            sel_asig = ui.select({}, label="Asignatura del plan (sin docente) *") \
                .classes("w-full").props("outlined")

            def _on_grupo(e) -> None:
                opts = _materias_sin_docente(e.value) if e.value else {}
                sel_asig.set_options(opts or {0: "Plan completo o sin plan"}, value=None)

            sel_grupo.on_value_change(_on_grupo)

            def _crear() -> None:
                gid, aid = sel_grupo.value, sel_asig.value
                if not gid or not aid:
                    toast_warning("Selecciona grupo y una asignatura pendiente.")
                    return
                try:
                    Container.asignacion_service().crear_asignacion(NuevaAsignacionDTO(
                        usuario_id=did, grupo_id=gid,
                        asignatura_id=aid, periodo_id=_s["periodo_id"],
                    ))
                    toast_success("Asignación creada")
                    dlg.close()
                    _cargar_docente()
                    matriz.refresh()
                except ValueError as exc:
                    toast_warning(_texto_error(exc))
                except Exception as exc:
                    logger.error("Error creando asignación docente: %s", exc)
                    toast_error("No se pudo crear la asignación")

            with ui.row().classes("base-form-footer w-full gap-2 justify-end u-mt-md"):
                btn_secondary("Cancelar", on_click=dlg.close)
                btn_primary("Asignar", on_click=_crear)

        dlg.open()

    # ── Acción compartida ───────────────────────────────────────────────────────
    def _quitar(asignacion_id: int, label: str) -> None:
        def _ok() -> None:
            try:
                Container.asignacion_service().desactivar(asignacion_id)
                toast_success("Asignación quitada")
            except Exception as exc:
                logger.error("Error desactivando %s: %s", asignacion_id, exc)
                toast_error("No se pudo quitar la asignación")
            finally:
                _recargar()
                matriz.refresh()

        confirm_dialog(
            titulo="Quitar asignación",
            mensaje=f"¿Quitar la asignación de {label}? El histórico de notas y asistencia se conserva.",
            on_confirm=_ok,
            variante="warning",
            texto_confirmar="Quitar",
        )

    def _guardar_carga_docente(did: int, maxv, extrav) -> None:
        try:
            maxh = int(maxv) if maxv not in (None, "") else None
            extra = int(extrav or 0)
            Container.usuario_service().configurar_carga(
                did, maxh, extra, actualizado_por_id=ctx.usuario_id,
            )
            toast_success("Tope de carga actualizado")
        except ValueError as exc:
            toast_warning(_texto_error(exc))
        except Exception as exc:
            logger.error("Error configurando carga: %s", exc)
            toast_error("No se pudo actualizar el tope")
        finally:
            matriz.refresh()

    # ── Selectores ───────────────────────────────────────────────────────────────
    def _cambiar_periodo(pid: int) -> None:
        _s["periodo_id"] = pid
        _recargar()
        matriz.refresh()

    def _cambiar_perspectiva(p: str) -> None:
        _s["perspectiva"] = p
        _recargar()
        matriz.refresh()

    def _seleccionar_grupo(gid: int) -> None:
        _s["grupo_sel_id"] = gid
        _cargar_grupo()
        matriz.refresh()

    def _seleccionar_docente(did: int) -> None:
        _s["docente_sel_id"] = did
        _cargar_docente()
        matriz.refresh()

    # ── Fila de materia (Por grupo, con selector inline) ──────────────────────────
    def _fila_materia(nombre: str, horas, asignatura_id: int, activo,
                      fuera_plan: bool = False) -> None:
        # Construir opciones de docente con su cupo (carga/cap) y filtrar los que
        # no tienen cupo para estas horas (salvo el actualmente asignado).
        h = horas or 0
        cur_uid = activo.usuario_id if activo else None
        cupos = Container.asignacion_service().docentes_con_cupo(
            asignatura_id=asignatura_id, grupo_id=_s["grupo_sel_id"], horas=h,
            periodo_id=_s["periodo_id"],
            docente_ids=[d.id for d in _s["docentes"]],
            usuario_actual_id=cur_uid,
        )
        opts: dict = {0: "— Sin asignar —"}
        for d in _s["docentes"]:
            c = cupos[d.id]
            if c.cap_efectivo is None:
                etiqueta = f"{d.nombre_completo} · {c.carga_actual}h"
            else:
                etiqueta = f"{d.nombre_completo} · {c.carga_actual}/{c.cap_efectivo}h"
                if not c.tiene_cupo:
                    etiqueta += " · sin cupo"
            if _s["solo_con_cupo"] and not c.tiene_cupo and not c.es_actual:
                continue
            opts[d.id] = etiqueta
        if cur_uid and cur_uid not in opts:
            d = next((x for x in _s["docentes"] if x.id == cur_uid), None)
            if d:
                opts[cur_uid] = d.nombre_completo
        with ui.element("div").classes("lista-fila"):
            with ui.element("div").classes("flex-1"):
                ui.label(nombre).classes("text-sm font-medium")
                if fuera_plan:
                    ui.label("Fuera del plan").classes("text-xs text-warning")
            ui.label(f"{horas} h" if horas is not None else "—").classes("w-16 text-sm text-secondary")
            ui.select(
                opts,
                value=cur_uid if cur_uid else 0,
                on_change=lambda e, aid=asignatura_id: _set_docente(aid, e.value or None),
            ).classes("w-72").props("dense outlined")
            with ui.element("div").classes("w-28"):
                status_badge("Asignada", variante="success") if activo \
                    else status_badge("Pendiente", variante="warning")
            with ui.element("div").classes("w-10 text-right"):
                if activo:
                    btn_icon("link_off", variante="danger", tooltip="Quitar",
                             on_click=lambda aid=activo.asignacion_id, lbl=nombre: _quitar(aid, lbl))

    # ── Render: Por grupo ─────────────────────────────────────────────────────────
    def _render_por_grupo() -> None:
        grupo = _grupo_sel()
        if not grupo:
            empty_state(icono="groups", titulo="Selecciona un grupo",
                        descripcion="Elige un grupo para configurar sus asignaciones.")
            return

        activo_map = _activo_por_materia()
        asig_nombre = {a.id: a.nombre for a in _s["asignaturas"]}
        plan = sorted(_s["plan"], key=lambda p: asig_nombre.get(p.asignatura_id, ""))
        plan_ids = {p.asignatura_id for p in plan}
        cubiertas = sum(1 for p in plan if p.asignatura_id in activo_map)
        total_horas = sum(p.horas_semanales for p in plan)
        horas_asignadas = sum(
            p.horas_semanales for p in plan if p.asignatura_id in activo_map
        )
        restantes = total_horas - horas_asignadas

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center justify-between flex-wrap gap-2"):
                with ui.element("div"):
                    ui.label(f"{grupo.codigo} · {grupo.nombre}").classes("text-subtitle1 font-semibold")
                    grado_txt = f"Grado {grupo.grado}" if grupo.grado is not None else "Sin grado"
                    ui.label(grado_txt).classes("text-xs text-secondary")
                with ui.row().classes("items-center gap-2"):
                    if plan:
                        var = "success" if cubiertas == len(plan) else "warning"
                        status_badge(f"{cubiertas}/{len(plan)} materias asignadas", variante=var)
                        status_badge(f"{horas_asignadas}/{total_horas} h del plan", variante="info")
                    btn_secondary("Agregar materia", icon="add", on_click=_agregar_fuera_plan)
            with ui.row().classes("items-center gap-2 u-mt-xs"):
                ui.switch(
                    "Solo docentes con cupo", value=_s["solo_con_cupo"],
                    on_change=lambda e: (_s.__setitem__("solo_con_cupo", e.value), matriz.refresh()),
                ).props("dense")
                ui.label("Los selectores muestran carga/cupo de cada docente.").classes(
                    "text-xs text-secondary"
                )
            if plan:
                # Barra de cobertura (avance del plan) + horas restantes
                _barra_progreso(horas_asignadas, total_horas, alerta_sobre=False)
                if restantes > 0:
                    ui.label(
                        f"Faltan {restantes} h por asignar para completar el plan del grado."
                    ).classes("text-xs text-warning u-mt-xs")
                else:
                    ui.label("Plan del grado completo ✓").classes("text-xs text-success u-mt-xs")
            else:
                ui.label(
                    "Este grado no tiene plan de estudios. Defínelo en «Plan de estudios» "
                    "o usa «Agregar materia»."
                ).classes("text-xs text-secondary u-mt-sm")

        if plan:
            with ui.element("div").classes("panel-card u-mt-sm"):
                ui.label("Plan de estudios del grado").classes("text-subtitle2 font-semibold u-mb-sm")
                with ui.element("div").classes("lista-head"):
                    ui.label("Asignatura").classes("flex-1")
                    ui.label("Horas").classes("w-16")
                    ui.label("Docente").classes("w-60")
                    ui.label("Estado").classes("w-28")
                    ui.label("").classes("w-10")
                for p in plan:
                    _fila_materia(
                        asig_nombre.get(p.asignatura_id, f"#{p.asignatura_id}"),
                        p.horas_semanales, p.asignatura_id,
                        activo_map.get(p.asignatura_id),
                    )

        extras = [a for a in _s["asigns"] if a.activo and a.asignatura_id not in plan_ids]
        if extras:
            with ui.element("div").classes("panel-card u-mt-sm"):
                ui.label("Materias fuera del plan").classes("text-subtitle2 font-semibold u-mb-sm")
                for a in extras:
                    _fila_materia(a.asignatura_nombre, None, a.asignatura_id,
                                  a, fuera_plan=True)

    # ── Render: Por docente ───────────────────────────────────────────────────────
    def _render_por_docente() -> None:
        docente = _docente_sel()
        if not docente:
            empty_state(icono=Icons.TEACHERS, titulo="Selecciona un docente",
                        descripcion="Elige un docente para ver y gestionar su carga.")
            return

        asigns = _s["doc_asigns"]
        grupo_nombre = {g.id: g.codigo for g in _s["grupos"]}
        carga = Container.asignacion_service().carga_docente(docente.id, _s["periodo_id"])
        try:
            usuario = Container.usuario_service().get_by_id(docente.id)
        except Exception:
            usuario = None
        maxh = usuario.carga_horaria_max if usuario else None
        extra = usuario.horas_extra if usuario else 0
        cap = usuario.carga_maxima_efectiva if usuario else None

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center justify-between flex-wrap gap-2"):
                with ui.element("div"):
                    ui.label(docente.nombre_completo).classes("text-subtitle1 font-semibold")
                    ui.label(f"{len(asigns)} asignación(es) en el periodo").classes("text-xs text-secondary")
                with ui.row().classes("items-center gap-2"):
                    if cap is not None:
                        var = "success" if carga <= maxh else ("warning" if carga <= cap else "error")
                        status_badge(f"{carga} / {cap} h", variante=var)
                    else:
                        status_badge(f"{carga} h · sin tope", variante="neutral")
                    btn_secondary("Asignar materia", icon="add", on_click=_agregar_a_docente)

            # Barra de carga (vs tope efectivo = máximo + extra)
            _barra_progreso(carga, cap, alerta_sobre=True)

            # Configuración del tope: máximo base + horas extra
            with ui.row().classes("items-center gap-3 u-mt-sm flex-wrap"):
                inp_max = ui.number(
                    label="Máx. base (h)", value=maxh, min=0, max=60, step=1,
                ).classes("w-32").props("dense outlined")
                inp_extra = ui.number(
                    label="Horas extra", value=extra, min=0, max=30, step=1,
                ).classes("w-32").props("dense outlined")
                btn_secondary(
                    "Guardar tope", icon="save",
                    on_click=lambda: _guardar_carga_docente(
                        docente.id, inp_max.value, inp_extra.value),
                )
                if cap is not None:
                    ui.label(
                        f"Tope efectivo: {cap} h ({maxh or 0} base + {extra or 0} extra)"
                    ).classes("text-xs text-secondary")

            # Mensajes semánticos de sobrecarga
            if cap is not None and carga > cap:
                ui.label(
                    f"⚠ Sobrecarga: {carga - cap} h por encima del tope efectivo. "
                    "Sube las horas extra o reasigna materias."
                ).classes("text-xs text-error u-mt-xs")
            elif maxh is not None and carga > maxh:
                ui.label(
                    f"Usando {carga - maxh} h de las {extra} h extra disponibles."
                ).classes("text-xs text-warning u-mt-xs")

        with ui.element("div").classes("panel-card u-mt-sm"):
            if not asigns:
                empty_state(icono="assignment_ind", titulo="Sin asignaciones",
                            descripcion="Este docente no tiene materias asignadas en el periodo.")
                return
            with ui.element("div").classes("lista-head"):
                ui.label("Grupo").classes("w-24")
                ui.label("Asignatura").classes("flex-1")
                ui.label("Horas").classes("w-16")
                ui.label("").classes("w-10")
            for a in sorted(asigns, key=lambda x: (grupo_nombre.get(x.grupo_id, ""), x.asignatura_nombre)):
                with ui.element("div").classes("lista-fila"):
                    ui.label(grupo_nombre.get(a.grupo_id, str(a.grupo_id))).classes("w-24 font-mono text-sm")
                    ui.label(a.asignatura_nombre).classes("flex-1 text-sm")
                    ui.label(f"{_horas(a.grupo_id, a.asignatura_id)} h").classes("w-16 text-sm text-secondary")
                    with ui.element("div").classes("w-10 text-right"):
                        btn_icon("link_off", variante="danger", tooltip="Quitar",
                                 on_click=lambda aid=a.asignacion_id,
                                 lbl=f"{a.asignatura_nombre} ({grupo_nombre.get(a.grupo_id, '')})": _quitar(aid, lbl))

    # ── Render: tablero del profesor (solo lectura) ────────────────────────────────
    def _render_profesor_board() -> None:
        asigns = _s["mis_asigns"]
        asvc = Container.asignacion_service()
        grupo_nombre = {g.id: g.codigo for g in _s["grupos"]}
        grupo_full = {g.id: g for g in _s["grupos"]}
        total_horas = sum(asvc.horas_de_asignacion(a.grupo_id, a.asignatura_id) for a in asigns)
        n_grupos = len({a.grupo_id for a in asigns})
        n_materias = len({a.asignatura_id for a in asigns})

        with ui.element("div").classes("panel-card"):
            ui.label("Mi carga académica").classes("text-subtitle1 font-semibold u-mb-sm")
            with ui.row().classes("items-center gap-4 flex-wrap"):
                stat_card(titulo="Horas/semana", valor=str(total_horas), icono="schedule")
                stat_card(titulo="Grupos", valor=str(n_grupos), icono="groups")
                stat_card(titulo="Materias", valor=str(n_materias), icono=Icons.SUBJECTS)

        if not asigns:
            with ui.element("div").classes("panel-card u-mt-sm"):
                empty_state(icono="assignment_ind", titulo="Sin asignaciones",
                            descripcion="No tienes materias asignadas en el periodo activo.")
            return

        por_grupo: dict = {}
        for a in asigns:
            por_grupo.setdefault(a.grupo_id, []).append(a)

        with ui.element("div").classes("flex flex-wrap gap-3 u-mt-sm"):
            for gid in sorted(por_grupo, key=lambda g: grupo_nombre.get(g, "")):
                items = sorted(por_grupo[gid], key=lambda x: x.asignatura_nombre)
                sub = sum(asvc.horas_de_asignacion(gid, a.asignatura_id) for a in items)
                g = grupo_full.get(gid)
                with ui.element("div").classes("panel-card w-64"):
                    with ui.row().classes("items-center justify-between"):
                        with ui.element("div"):
                            ui.label(grupo_nombre.get(gid, str(gid))).classes("text-subtitle2 font-semibold")
                            if g is not None:
                                ui.label(g.nombre).classes("text-xs text-secondary")
                        status_badge(f"{sub} h", variante="info")
                    for a in items:
                        with ui.row().classes("items-center justify-between py-1 border-b"):
                            ui.label(a.asignatura_nombre).classes("text-sm")
                            ui.label(
                                f"{asvc.horas_de_asignacion(gid, a.asignatura_id)} h"
                            ).classes("text-xs text-secondary")

    # ── Matriz (controles + dispatch) ───────────────────────────────────────────────
    # Los controles viven DENTRO del refreshable para que su estado activo
    # (toggle de perspectiva, chip seleccionado) se actualice al interactuar.
    @ui.refreshable
    def matriz() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center gap-4 flex-wrap"):
                periodo_opts = {p.id: p.nombre for p in _s["periodos"]}
                if periodo_opts:
                    ui.select(
                        periodo_opts, value=_s["periodo_id"], label="Periodo",
                        on_change=lambda e: _cambiar_periodo(e.value),
                    ).classes("w-48").props("dense outlined")
                if es_directivo:
                    with ui.element("div").classes("parrilla-segmento"):
                        for clave, lbl in [("grupo", "Por grupo"), ("docente", "Por docente")]:
                            cls = "parrilla-seg-btn" + (
                                " parrilla-seg-btn-activo" if _s["perspectiva"] == clave else ""
                            )
                            b = ui.element("div").classes(cls)
                            b.on("click", lambda _, c=clave: _cambiar_perspectiva(c))
                            with b:
                                ui.label(lbl)
                btn_icon("refresh", tooltip="Recargar",
                         on_click=lambda: (_recargar(), matriz.refresh()))

            if es_directivo and _s["perspectiva"] == "grupo":
                ui.label("Grupo").classes("parrilla-chips-label u-mt-sm")
                with ui.element("div").classes("parrilla-chips"):
                    for g in _s["grupos"]:
                        cls = "parrilla-chip" + (
                            " parrilla-chip-activo" if g.id == _s["grupo_sel_id"] else ""
                        )
                        chip = ui.element("div").classes(cls)
                        chip.on("click", lambda _, gid=g.id: _seleccionar_grupo(gid))
                        with chip:
                            ui.label(g.codigo)
            elif es_directivo:
                ui.label("Docente").classes("parrilla-chips-label u-mt-sm")
                with ui.element("div").classes("parrilla-chips"):
                    for d in _s["docentes"]:
                        cls = "parrilla-chip" + (
                            " parrilla-chip-activo" if d.id == _s["docente_sel_id"] else ""
                        )
                        chip = ui.element("div").classes(cls)
                        chip.on("click", lambda _, did=d.id: _seleccionar_docente(did))
                        with chip:
                            ui.label(d.nombre_completo)

        if not _s["periodo_id"]:
            empty_state(icono=Icons.PERIODS, titulo="Sin periodo activo",
                        descripcion="No hay periodos en el año activo. Configúralos primero.")
            return
        if es_profesor:
            _render_profesor_board()
        elif _s["perspectiva"] == "grupo":
            _render_por_grupo()
        else:
            _render_por_docente()

    # ── Contenido ─────────────────────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            if not es_profesor:
                pipeline_nav(
                    _PASOS_HORARIO, activo="asignaciones",
                    hint="Paso 3 · Asigna un docente a cada materia del plan (por grupo) "
                         "o reparte materias a cada docente según su carga. Luego genera el horario.",
                )
            matriz()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Asignaciones",
        page_subtitulo = (
            "Tu carga académica del periodo" if es_profesor
            else "Asigna docentes a materias por grupo, o materias a cada docente según su carga"
        ),
        page_icono     = "assignment_ind",
    )


__all__ = ["asignaciones_page"]
