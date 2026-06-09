"""
src/interface/pages/academico/horarios.py
==========================================
Página de gestión de horarios — ZECI Manager v2.0
Ruta: /horarios

Secciones:
  1. Panel de control (selector de vista, grupo/docente, periodo)
  2. Grilla semanal (@ui.refreshable) — filas por hora_inicio, columnas por día
  3. Dialog de creación de bloque (admin/director)
  4. Dialog de confirmación de eliminación (admin/director)

Reglas de capas:
  - Solo Container.*  (no repositorios directos).
  - No importa src.db.
  - No usa model_dump() en strings — solo .model_dump().
  - Estado mutable en _s dict (aislamiento por petición HTTP).

Roles:
  - admin, director:    lectura + escritura (crear y eliminar bloques).
  - coordinador:        solo lectura, puede cambiar vista grupo/docente.
  - profesor:           solo lectura, vista docente fija a su usuario_id.
"""
from __future__ import annotations

import logging
from datetime import time

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger, btn_ghost, btn_icon
from src.interface.design.components import form_dialog
from src.services.infraestructura_service import NuevoHorarioDTO, DiaSemana
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("HORARIOS")

# Roles con permisos de escritura
_ROLES_ESCRITURA = frozenset({"admin", "director"})
# Roles que pueden cambiar la vista grupo/docente
_ROLES_SELECTOR_VISTA = frozenset({"admin", "director", "coordinador"})

# Días de la semana en orden
_DIAS_BASE = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]


# =============================================================================
# Helpers de construcción de grilla
# =============================================================================

def _build_grilla(bloques: list) -> dict:
    """
    Agrupa los bloques horarios por hora_inicio.

    Retorna:
        dict ordenado { "HH:MM": { dia_str: HorarioInfo | None } }
    """
    dias = _DIAS_BASE[:]
    # Verificar si hay bloques de Sábado
    tiene_sabado = any(
        (b.dia_semana.value if hasattr(b.dia_semana, "value") else b.dia_semana) == "Sábado"
        for b in bloques
    )
    if tiene_sabado:
        dias.append("Sábado")

    franjas: dict[str, dict[str, object]] = {}
    for b in bloques:
        hk = b.hora_inicio.strftime("%H:%M")
        if hk not in franjas:
            franjas[hk] = {d: None for d in dias}
        dia_val = b.dia_semana.value if hasattr(b.dia_semana, "value") else str(b.dia_semana)
        if dia_val in franjas[hk]:
            franjas[hk][dia_val] = b

    return dict(sorted(franjas.items())), dias


# =============================================================================
# Página principal
# =============================================================================

@ui.page("/horarios")
def horarios_page() -> None:
    """Punto de entrada de /horarios."""

    # ── Guard de autenticación ────────────────────────────────────────────────
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    rol = ctx.usuario_rol or ""
    puede_escribir = rol in _ROLES_ESCRITURA
    puede_cambiar_vista = rol in _ROLES_SELECTOR_VISTA
    es_profesor = (rol == "profesor")

    # ── Estado mutable de la página ───────────────────────────────────────────
    _s: dict = {
        "bloques":      [],
        "vista":        "grupo" if not es_profesor else "docente",
        "grupos":       [],
        "docentes":     [],
        "periodo_id":   None,
        "grupo_id":     None,
        "usuario_id":   ctx.usuario_id,
        "config":       None,
        "asignaciones": [],
    }

    # ── Carga inicial de datos de soporte ─────────────────────────────────────
    try:
        _s["config"] = Container.configuracion_service().get_activa()
    except Exception as exc:
        logger.error("Error cargando configuración activa: %s", exc)

    if _s["config"]:
        try:
            periodos = Container.periodo_service().listar_por_anio(_s["config"].id)
            # Usar el primer periodo no cerrado; si todos están cerrados, usar el primero
            activos = [p for p in periodos if not getattr(p, "cerrado", False)]
            periodo_sel = activos[0] if activos else (periodos[0] if periodos else None)
            if periodo_sel:
                _s["periodo_id"] = periodo_sel.id
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)

    try:
        _s["grupos"] = Container.infraestructura_service().listar_grupos()
    except Exception as exc:
        logger.error("Error cargando grupos: %s", exc)

    try:
        docentes = Container.usuario_service().listar_docentes()
        _s["docentes"] = docentes
    except Exception as exc:
        logger.error("Error cargando docentes: %s", exc)

    # Grupo por defecto según rol
    if not es_profesor and _s["grupos"]:
        _s["grupo_id"] = _s["grupos"][0].id
    elif es_profesor and hasattr(ctx, "grupo_id") and ctx.grupo_id:
        _s["grupo_id"] = ctx.grupo_id

    # ── Función de carga de bloques ───────────────────────────────────────────

    def _cargar_bloques() -> None:
        """Recarga _s['bloques'] según la vista y selector activos."""
        if not _s["periodo_id"]:
            _s["bloques"] = []
            return
        try:
            svc = Container.infraestructura_service()
            if _s["vista"] == "grupo" and _s["grupo_id"]:
                _s["bloques"] = svc.listar_horario_grupo(
                    _s["grupo_id"], _s["periodo_id"]
                )
            elif _s["vista"] == "docente" and _s["usuario_id"]:
                _s["bloques"] = svc.listar_horario_docente(
                    _s["usuario_id"], _s["periodo_id"]
                )
            else:
                _s["bloques"] = []
        except Exception as exc:
            logger.error("Error cargando bloques horarios: %s", exc)
            _s["bloques"] = []

    # Carga inicial de bloques
    _cargar_bloques()

    # ── Refreshables ──────────────────────────────────────────────────────────

    @ui.refreshable
    def grilla_refreshable() -> None:
        """Renderiza la grilla semanal de horarios."""
        bloques = _s["bloques"]

        if not bloques:
            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("tablero-empty"):
                    ThemeManager.icono(Icons.SCHEDULE, size=40)
                    ui.label("No hay bloques registrados para este periodo.").classes(
                        "tablero-panel-subtitle"
                    )
            return

        grilla, dias = _build_grilla(bloques)

        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("overflow-auto"):
                with ui.element("table").classes("w-full border-collapse"):

                    # Cabecera
                    with ui.element("thead"):
                        with ui.element("tr"):
                            ui.element("th").classes(
                                "border px-3 py-2 text-left text-sm font-semibold bg-grey-2"
                            ).text = "Hora"
                            for dia in dias:
                                ui.element("th").classes(
                                    "border px-3 py-2 text-center text-sm font-semibold bg-grey-2"
                                ).text = dia

                    # Cuerpo
                    with ui.element("tbody"):
                        for hora_key, celdas in grilla.items():
                            with ui.element("tr"):
                                # Celda de hora
                                hora_td = ui.element("td").classes(
                                    "border px-3 py-2 text-sm font-medium text-grey-8 whitespace-nowrap"
                                )
                                hora_td.text = hora_key

                                # Celdas por día
                                for dia in dias:
                                    bloque = celdas.get(dia)
                                    with ui.element("td").classes(
                                        "border px-2 py-2 text-sm align-top min-w-[120px]"
                                    ):
                                        if bloque is None:
                                            ui.label("—").classes("text-grey-4 text-center block")
                                        else:
                                            with ui.element("div").classes(
                                                "relative bg-blue-1 rounded p-1"
                                            ):
                                                ui.label(bloque.asignatura_nombre).classes(
                                                    "text-xs font-semibold text-primary block"
                                                )
                                                ui.label(bloque.docente_nombre).classes(
                                                    "text-xs text-grey-7 block"
                                                )
                                                if bloque.sala and bloque.sala != "Aula":
                                                    ui.label(bloque.sala).classes(
                                                        "text-xs text-grey-5 block"
                                                    )
                                                hora_fin = bloque.hora_fin.strftime("%H:%M")
                                                ui.label(
                                                    f"hasta {hora_fin}"
                                                ).classes("text-xs text-grey-5 block")

                                                # Botón eliminar (solo admin/director)
                                                if puede_escribir:
                                                    btn_icon(
                                                        "close",
                                                        on_click=lambda _, bid=bloque.id: _confirmar_eliminar(bid),
                                                        tooltip="Eliminar bloque",
                                                        variante="danger",
                                                        size="sm",
                                                    ).classes("btn-cell-overlay")

    # ── Helpers de diálogos ───────────────────────────────────────────────────

    def _confirmar_eliminar(horario_id: int) -> None:
        """Dialog de confirmación antes de eliminar un bloque."""
        with ui.dialog() as dlg, ui.card():
            ui.label("¿Eliminar este bloque del horario?").classes("text-subtitle1 q-mb-md")
            with ui.row().classes("justify-end gap-sm"):
                btn_ghost("Cancelar", on_click=dlg.close)

                def _ok() -> None:
                    try:
                        Container.infraestructura_service().eliminar_horario(horario_id)
                        ui.notify("Bloque eliminado", type="positive")
                        dlg.close()
                        _cargar_bloques()
                        grilla_refreshable.refresh()
                    except Exception as exc:
                        logger.error("Error eliminando bloque %s: %s", horario_id, exc)
                        ui.notify(str(exc), type="negative")

                btn_danger("Eliminar", on_click=_ok)
        dlg.open()

    def _abrir_dialog_crear() -> None:
        """Dialog para crear un nuevo bloque horario."""
        # Cargar asignaciones del periodo
        _s["asignaciones"] = []
        if _s["periodo_id"]:
            try:
                _s["asignaciones"] = Container.asignacion_service().listar_con_info(
                    FiltroAsignacionesDTO(periodo_id=_s["periodo_id"])
                )
            except Exception as exc:
                logger.error("Error cargando asignaciones: %s", exc)

        if not _s["asignaciones"]:
            ui.notify(
                "No hay asignaciones activas en este periodo.", type="warning"
            )
            return

        # Opciones de asignación para el selector
        asig_opts: dict[int, str] = {
            a.asignacion_id: f"{a.grupo_codigo} – {a.asignatura_nombre} ({a.docente_nombre})"
            for a in _s["asignaciones"]
        }

        def _guardar(datos: dict) -> "bool | None":
            asig_id = datos.get("asignacion_id")
            if not asig_id:
                ui.notify("Selecciona una asignación.", type="warning")
                return False
            try:
                asig = next(
                    a for a in _s["asignaciones"]
                    if a.asignacion_id == asig_id
                )
                dto = NuevoHorarioDTO(
                    grupo_id=asig.grupo_id,
                    asignatura_id=asig.asignatura_id,
                    usuario_id=asig.usuario_id,
                    periodo_id=_s["periodo_id"],
                    dia_semana=datos.get("dia", DiaSemana.LUNES.value),
                    hora_inicio=datos.get("hora_inicio", "07:00"),
                    hora_fin=datos.get("hora_fin", "07:55"),
                    asignacion_id=asig.asignacion_id,
                    sala=str(datos.get("sala", "") or "Aula"),
                )
                Container.infraestructura_service().guardar_horario(dto.to_horario())
                ui.notify("Bloque guardado", type="positive")
                _cargar_bloques()
                grilla_refreshable.refresh()
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
                return False
            except StopIteration:
                ui.notify("Asignación no encontrada.", type="warning")
                return False
            except Exception as exc:
                logger.error("Error guardando bloque: %s", exc)
                ui.notify("Error al guardar el bloque", type="negative")
                return False

        form_dialog(
            titulo    = "Agregar bloque de horario",
            campos    = [
                {"key": "asignacion_id", "label": "Asignación *",  "tipo": "select",
                 "opciones": asig_opts, "requerido": True},
                {"key": "dia",           "label": "Día *",          "tipo": "select",
                 "opciones": {d.value: d.value for d in DiaSemana},
                 "valor": DiaSemana.LUNES.value, "requerido": True},
                {"key": "hora_inicio",   "label": "Hora inicio",    "tipo": "time",
                 "valor": "07:00"},
                {"key": "hora_fin",      "label": "Hora fin",       "tipo": "time",
                 "valor": "07:55"},
                {"key": "sala",          "label": "Sala",           "tipo": "text",
                 "valor": "Aula", "placeholder": "Aula, Lab. Química..."},
            ],
            on_submit    = _guardar,
            max_width    = "max-w-lg",
            columnas     = 2,
        )

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def contenido() -> None:

        with ui.element("div").classes("page-stack"):

            # ── Panel de control ──────────────────────────────────────────────
            with ui.element("div").classes("panel-card"):

                with ui.row().classes("w-full q-col-gutter-md items-end q-mb-sm"):

                    # Selector de vista (solo para roles con permiso)
                    if puede_cambiar_vista and not es_profesor:
                        vista_opts = {"grupo": "Por grupo", "docente": "Por docente"}
                        ui.select(
                            label="Vista",
                            options=vista_opts,
                            value=_s["vista"],
                            on_change=lambda e: _s.update({"vista": e.value}),
                        ).classes("flex-2")

                    # Selector de grupo o docente según vista
                    @ui.refreshable
                    def selector_entidad() -> None:
                        if _s["vista"] == "grupo":
                            if _s["grupos"]:
                                grupos_opts = {g.id: g.codigo for g in _s["grupos"]}
                                ui.select(
                                    label="Grupo",
                                    options=grupos_opts,
                                    value=_s["grupo_id"],
                                    on_change=lambda e: _s.update({"grupo_id": e.value}),
                                ).classes("flex-3")
                            else:
                                ui.label("Sin grupos").classes("text-caption text-grey")
                        else:
                            # Vista docente
                            if es_profesor:
                                # Profesor: fijo a su usuario_id, sin selector
                                nombre_docente = ctx.usuario_nombre or f"Docente #{ctx.usuario_id}"
                                ui.label(f"Docente: {nombre_docente}").classes(
                                    "text-body2 flex-3"
                                )
                            else:
                                if _s["docentes"]:
                                    docentes_opts = {
                                        d.id: getattr(d, "nombre_completo", None)
                                        or f"{getattr(d, 'nombre', '')} {getattr(d, 'apellido', '')}".strip()
                                        for d in _s["docentes"]
                                    }
                                    ui.select(
                                        label="Docente",
                                        options=docentes_opts,
                                        value=_s["usuario_id"],
                                        on_change=lambda e: _s.update(
                                            {"usuario_id": e.value}
                                        ),
                                    ).classes("flex-3")
                                else:
                                    ui.label("Sin docentes").classes("text-caption text-grey")

                    selector_entidad()

                    # Botón Ver horario
                    def _ver_horario() -> None:
                        _cargar_bloques()
                        grilla_refreshable.refresh()

                    btn_primary(
                        "Ver horario",
                        icon=Icons.SEARCH,
                        on_click=_ver_horario,
                    )

                    # Botón Agregar bloque (solo admin/director)
                    if puede_escribir:
                        btn_secondary(
                            "Agregar bloque",
                            icon="add",
                            on_click=_abrir_dialog_crear,
                        )

            # ── Grilla semanal ────────────────────────────────────────────────
            grilla_refreshable()

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        ctx,
        contenido,
        page_titulo       = "Horarios",
        page_subtitulo    = "Grilla semanal de bloques de clase por grupo",
        page_icono        = Icons.SCHEDULE,
        on_context_change = on_context_change,
    )


__all__ = ["horarios_page"]
