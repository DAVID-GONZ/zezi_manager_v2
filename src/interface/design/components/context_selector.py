"""
context_selector.py — Selector de contexto académico.

Reemplaza context_bar.py con una arquitectura correcta:
  - Sin CSS inline (todo en styles.css)
  - Sin SQL directo (usa Container)
  - Sin AppState (usa SessionContext)

Dos componentes públicos:
  context_chip(ctx, on_change, mostrar_asignatura) → chip para la topbar
  abrir_selector(ctx, on_change, mostrar_asignatura) → dialog de selección visual

El chip siempre visible en la topbar muestra el contexto activo.
Hacer clic abre el dialog de selección por tarjetas.

Lógica clave preservada del legacy:
  Al cambiar periodo, el asignatura_id (entidad estable) se usa
  como hint para encontrar la asignacion equivalente en el nuevo
  periodo. Evita que el docente re-seleccione manualmente.
"""
from __future__ import annotations

import logging
from datetime import date

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.tokens import Icons
from src.interface.design.theme import ThemeManager

logger = logging.getLogger("CONTEXT_SELECTOR")


# ── Helpers internos ──────────────────────────────────────────────────────────

def _progreso_periodo(fecha_inicio, fecha_fin) -> tuple[float, str]:
    """Retorna (porcentaje 0-100, clase CSS para el color de la barra)."""
    if not fecha_inicio or not fecha_fin:
        return 0.0, ""
    hoy = date.today()
    total = (fecha_fin - fecha_inicio).days
    if total <= 0:
        return 100.0, "cs-bar-done"
    pasados = (hoy - fecha_inicio).days
    pct = min(100.0, max(0.0, pasados / total * 100))
    if hoy > fecha_fin:
        return 100.0, "cs-bar-done"
    if pct >= 85:
        return pct, "cs-bar-danger"
    if pct >= 60:
        return pct, "cs-bar-warn"
    return pct, ""


def _texto_chip(ctx: SessionContext) -> tuple[str, bool]:
    """
    Retorna (texto para mostrar en el chip, tiene_contexto).
    Usa los nombres guardados en SessionContext para evitar queries.
    """
    partes = []
    if ctx.periodo_nombre:
        partes.append(ctx.periodo_nombre)
    if ctx.grupo_nombre:
        partes.append(ctx.grupo_nombre)
    if ctx.asignacion_nombre:
        partes.append(ctx.asignacion_nombre)

    if not partes:
        return "Seleccionar contexto", False
    return "  ·  ".join(partes), True


# ── Chip del topbar ───────────────────────────────────────────────────────────

def context_chip(
    ctx: SessionContext,
    on_change=None,
    mostrar_asignatura: bool = True,
) -> None:
    """
    Chip compacto para la topbar. Muestra el contexto activo.
    Hacer clic abre el dialog de selección visual.

    Args:
        ctx: Contexto de sesión activo.
        on_change: Callback llamado al confirmar un nuevo contexto.
        mostrar_asignatura: False para páginas que solo necesitan P+G.
    """
    texto, tiene_contexto = _texto_chip(ctx)
    clase_chip = "cs-chip" + ("" if tiene_contexto else " cs-chip-empty")

    def abrir():
        abrir_selector(ctx=ctx, on_change=on_change, mostrar_asignatura=mostrar_asignatura)

    with ui.element("div").classes(clase_chip).on("click", abrir):
        ThemeManager.icono("swap_horiz", size=16, clases="cs-chip-icon")
        ui.label(texto)
        ThemeManager.icono("expand_more", size=16, clases="cs-chip-icon")


# ── Dialog de selección visual ────────────────────────────────────────────────

def abrir_selector(
    ctx: SessionContext,
    on_change=None,
    mostrar_asignatura: bool = True,
) -> None:
    """
    Abre el diálogo de selección visual de contexto académico.

    Flujo guiado en tres pasos:
      1. Periodo   — tarjetas con progress bar y estado
      2. Grupo     — tarjetas con código y número de estudiantes
      3. Asignatura — lista con nombre y horario (si mostrar_asignatura=True)

    Preserva la lógica de asignatura_hint del legacy:
    Al cambiar de periodo, guarda el asignatura_id (entidad estable)
    y lo usa para encontrar la asignacion equivalente en el nuevo periodo.
    """
    rol = ctx.usuario_rol

    # Estado interno del dialog (selecciones en progreso, no confirmadas)
    seleccion = {
        "periodo_id":        ctx.periodo_id,
        "periodo_nombre":    ctx.periodo_nombre,
        "grupo_id":          ctx.grupo_id,
        "grupo_nombre":      ctx.grupo_nombre,
        "asignacion_id":     ctx.asignacion_id,
        "asignacion_nombre": ctx.asignacion_nombre,
        "asignatura_id":     None,  # hint para restaurar asignatura al cambiar periodo
    }

    btn_aplicar = None

    def _actualizar_btn_aplicar():
        if not btn_aplicar:
            return
        completo = bool(seleccion["periodo_id"] and seleccion["grupo_id"])
        if mostrar_asignatura:
            completo = completo and bool(seleccion["asignacion_id"])
        if completo:
            btn_aplicar.enable()
        else:
            btn_aplicar.disable()

    # ── Render de cada paso ───────────────────────────────────────────────────

    def _render_periodos(contenedor) -> None:
        contenedor.clear()
        with contenedor:
            try:
                anio_id = ctx.anio_id
                if not anio_id:
                    cfg = Container.configuracion_service().get_activa()
                    anio_id = cfg.id if cfg and cfg.id else None

                if not anio_id:
                    ui.label("Sin año académico activo").style(
                        "color:var(--color-text-secondary);font-size:13px"
                    )
                    return

                periodos = Container.periodo_service().listar_por_anio(anio_id)
                if not periodos:
                    ui.label("Sin periodos configurados").style(
                        "color:var(--color-text-secondary);font-size:13px"
                    )
                    return

                with ui.row().classes("gap-2 flex-wrap"):
                    for p in periodos:
                        if not p.id:
                            continue
                        pct, clase_bar = _progreso_periodo(p.fecha_inicio, p.fecha_fin)
                        es_sel = seleccion["periodo_id"] == p.id
                        clase = "cs-period-card" + (" selected" if es_sel else "") + (
                            " closed" if getattr(p, "cerrado", False) else ""
                        )
                        estado_txt = (
                            "Cerrado" if getattr(p, "cerrado", False) else
                            "Activo"  if getattr(p, "activo",  False) else
                            "Pendiente"
                        )

                        def seleccionar_periodo(pid=p.id, pnom=p.nombre):
                            seleccion["periodo_id"]      = pid
                            seleccion["periodo_nombre"]  = pnom
                            seleccion["grupo_id"]        = None
                            seleccion["grupo_nombre"]    = ""
                            seleccion["asignacion_id"]   = None
                            seleccion["asignacion_nombre"] = ""
                            # Resolver asignatura_hint desde el contexto actual
                            if ctx.asignacion_id:
                                try:
                                    asig = Container.asignacion_repo().get_by_id(
                                        ctx.asignacion_id
                                    )
                                    if asig:
                                        seleccion["asignatura_id"] = asig.asignatura_id
                                except Exception:
                                    pass
                            _render_periodos(cont_periodos)
                            _render_grupos(cont_grupos)
                            if mostrar_asignatura:
                                _render_asignaturas(cont_asignaturas)
                            _actualizar_btn_aplicar()

                        with ui.element("div").classes(clase).on("click", seleccionar_periodo):
                            ui.label(p.nombre).classes("cs-period-name")
                            with ui.element("div").classes("cs-period-bar-track"):
                                ui.element("div").classes(
                                    f"cs-period-bar-fill {clase_bar}"
                                ).style(f"width:{pct:.0f}%")
                            ui.label(f"{pct:.0f}% · {estado_txt}").classes("cs-period-meta")

            except Exception as e:
                logger.error("Error cargando periodos: %s", e)
                ui.label("Error al cargar periodos").style(
                    "color:var(--color-error);font-size:13px"
                )

    def _render_grupos(contenedor) -> None:
        contenedor.clear()
        with contenedor:
            try:
                periodo_id = seleccion["periodo_id"]
                if not periodo_id:
                    ui.label("Selecciona un periodo primero").style(
                        "color:var(--color-text-disabled);font-size:13px"
                    )
                    return

                if rol == "profesor":
                    asignaciones = Container.asignacion_repo().listar_por_docente(
                        ctx.usuario_id, periodo_id
                    )
                    grupos_vistos: dict[int, str] = {}
                    for a in asignaciones:
                        if a.grupo_id not in grupos_vistos:
                            grupos_vistos[a.grupo_id] = a.grupo_codigo
                    grupos_data = [(gid, cod, None) for gid, cod in grupos_vistos.items()]
                else:
                    grupos = Container.infraestructura_repo().listar_grupos()
                    grupos_data = [
                        (g.id, g.codigo, g.capacidad_maxima) for g in grupos if g.id
                    ]

                if not grupos_data:
                    ui.label("Sin grupos disponibles").style(
                        "color:var(--color-text-secondary);font-size:13px"
                    )
                    return

                with ui.row().classes("gap-2 flex-wrap"):
                    for gid, gcod, gcap in grupos_data:
                        es_sel = seleccion["grupo_id"] == gid
                        clase = "cs-group-card" + (" selected" if es_sel else "")

                        try:
                            n_est = Container.estudiante_repo().contar_por_grupo(gid)
                        except Exception:
                            n_est = gcap or 0

                        def seleccionar_grupo(gid_=gid, gcod_=gcod):
                            seleccion["grupo_id"]          = gid_
                            seleccion["grupo_nombre"]      = gcod_
                            seleccion["asignacion_id"]     = None
                            seleccion["asignacion_nombre"] = ""
                            _render_grupos(cont_grupos)
                            if mostrar_asignatura:
                                _render_asignaturas(cont_asignaturas)
                            _actualizar_btn_aplicar()

                        with ui.element("div").classes(clase).on("click", seleccionar_grupo):
                            ui.label(gcod).classes("cs-group-code")
                            ui.label(
                                f"{n_est} estudiantes" if n_est else "—"
                            ).classes("cs-group-meta")

            except Exception as e:
                logger.error("Error cargando grupos: %s", e)
                ui.label("Error al cargar grupos").style(
                    "color:var(--color-error);font-size:13px"
                )

    def _render_asignaturas(contenedor) -> None:
        contenedor.clear()
        with contenedor:
            try:
                periodo_id = seleccion["periodo_id"]
                grupo_id   = seleccion["grupo_id"]
                if not periodo_id or not grupo_id:
                    ui.label("Selecciona periodo y grupo primero").style(
                        "color:var(--color-text-disabled);font-size:13px"
                    )
                    return

                asignaciones = Container.asignacion_repo().listar_por_grupo(
                    grupo_id, periodo_id
                )
                if rol == "profesor":
                    asignaciones = [
                        a for a in asignaciones if a.usuario_id == ctx.usuario_id
                    ]

                if not asignaciones:
                    ui.label("Sin asignaturas asignadas").style(
                        "color:var(--color-text-secondary);font-size:13px"
                    )
                    return

                # Restaurar selección por asignatura_hint (legacy logic)
                hint_asig_id = seleccion.get("asignatura_id")
                if hint_asig_id and not seleccion["asignacion_id"]:
                    match = next(
                        (a for a in asignaciones if a.asignatura_id == hint_asig_id),
                        None,
                    )
                    if match:
                        seleccion["asignacion_id"]     = match.asignacion_id
                        seleccion["asignacion_nombre"] = match.asignatura_nombre

                for asig in asignaciones:
                    if not asig.asignacion_id:
                        continue
                    es_sel = seleccion["asignacion_id"] == asig.asignacion_id
                    clase = "cs-subject-item" + (" selected" if es_sel else "")

                    horario_txt = ""
                    try:
                        horarios = Container.infraestructura_repo().listar_horario_grupo(
                            grupo_id, periodo_id
                        )
                        h_asig = [h for h in horarios if h.asignacion_id == asig.asignacion_id]
                        if h_asig:
                            dias = list({h.dia_semana.value for h in h_asig})
                            horario_txt = " · ".join(sorted(dias)[:3])
                    except Exception:
                        pass

                    def seleccionar_asignatura(
                        aid=asig.asignacion_id,
                        anom=asig.asignatura_nombre,
                        asig_id=asig.asignatura_id,
                    ):
                        seleccion["asignacion_id"]     = aid
                        seleccion["asignacion_nombre"] = anom
                        seleccion["asignatura_id"]     = asig_id
                        _render_asignaturas(cont_asignaturas)
                        _actualizar_btn_aplicar()

                    with ui.element("div").classes(clase).on("click", seleccionar_asignatura):
                        radio_clase = "cs-subject-radio" + (" checked" if es_sel else "")
                        ui.element("div").classes(radio_clase)
                        ui.label(asig.asignatura_nombre).classes("cs-subject-name")
                        if horario_txt:
                            ui.label(horario_txt).classes("cs-subject-schedule")

            except Exception as e:
                logger.error("Error cargando asignaturas: %s", e)
                ui.label("Error al cargar asignaturas").style(
                    "color:var(--color-error);font-size:13px"
                )

    # ── Construcción del dialog ───────────────────────────────────────────────

    with ui.dialog() as dialog:
        dialog.props("persistent")

        with ui.card().style(
            "width:580px;max-width:95vw;max-height:85vh;"
            "overflow-y:auto;padding:24px;border-radius:12px"
        ):
            # Encabezado
            with ui.row().classes("items-center justify-between mb-5"):
                with ui.row().classes("items-center gap-2"):
                    ThemeManager.icono("swap_horiz", size=22, color="var(--color-primary)")
                    ui.label("Contexto de trabajo").classes("cs-dialog-header")
                ui.button(icon="close", on_click=dialog.close).props(
                    "flat round dense"
                ).style("color:var(--color-text-secondary)")

            # PASO 1: Periodo
            with ui.column().classes("gap-2 mb-5"):
                with ui.element("div").classes("cs-step-label"):
                    ui.label("1").classes("cs-step-number")
                    ui.label("Periodo académico")
                cont_periodos = ui.element("div")
                _render_periodos(cont_periodos)

            # PASO 2: Grupo
            with ui.column().classes("gap-2 mb-5"):
                with ui.element("div").classes("cs-step-label"):
                    num_clase = "cs-step-number" + (
                        "" if seleccion["periodo_id"] else " cs-step-number-pending"
                    )
                    ui.label("2").classes(num_clase)
                    ui.label("Grupo")
                cont_grupos = ui.element("div")
                _render_grupos(cont_grupos)

            # PASO 3: Asignatura (condicional)
            # cont_asignaturas siempre definido para que los callbacks de los pasos
            # anteriores puedan referenciarlo sin importar mostrar_asignatura
            cont_asignaturas = ui.element("div")  # placeholder (vacío si no aplica)
            if mostrar_asignatura:
                with ui.column().classes("gap-2 mb-5"):
                    with ui.element("div").classes("cs-step-label"):
                        num_clase3 = "cs-step-number" + (
                            "" if seleccion["grupo_id"] else " cs-step-number-pending"
                        )
                        ui.label("3").classes(num_clase3)
                        ui.label("Asignatura")
                    cont_asignaturas = ui.element("div")
                    _render_asignaturas(cont_asignaturas)

            # Botones de acción
            ui.separator().classes("my-2")

            def aplicar():
                ctx.periodo_id        = seleccion["periodo_id"]
                ctx.periodo_nombre    = seleccion["periodo_nombre"]
                ctx.grupo_id          = seleccion["grupo_id"]
                ctx.grupo_nombre      = seleccion["grupo_nombre"]
                ctx.asignacion_id     = seleccion["asignacion_id"]
                ctx.asignacion_nombre = seleccion["asignacion_nombre"]
                ctx.guardar()
                logger.info(
                    "Contexto aplicado: %s · %s · %s",
                    ctx.periodo_nombre, ctx.grupo_nombre, ctx.asignacion_nombre,
                )
                dialog.close()
                if on_change:
                    on_change()

            with ui.row().classes("gap-2 justify-end"):
                ui.button("Cancelar", on_click=dialog.close).props("flat").style(
                    "color:var(--color-text-secondary)"
                )
                btn_aplicar = ui.button("Aplicar contexto", on_click=aplicar).classes(
                    "btn-primary"
                )
                _actualizar_btn_aplicar()

    dialog.open()


__all__ = ["context_chip", "abrir_selector"]
