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

import csv
import io
import logging
from datetime import time, date

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger, btn_ghost, btn_icon
from src.interface.design.components import (
    confirm_dialog, empty_state, form_dialog, toast_error, toast_success, toast_warning,
    stat_card,
)
from src.interface.pages.academico.parrilla_widget import render_parrilla, render_tablero_maestro
from src.services.infraestructura_service import NuevoHorarioDTO, DiaSemana
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("HORARIOS")

# Roles con permisos de escritura
_ROLES_ESCRITURA = frozenset({"admin", "director"})
# Roles que pueden cambiar la vista grupo/docente
_ROLES_SELECTOR_VISTA = frozenset({"admin", "director", "coordinador"})

# Días de la semana en orden
_DIAS_BASE = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

# Mapeo inglés→español para date.strftime
_DIA_MAP = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}


# =============================================================================
# Helpers de construcción de grilla
# =============================================================================

def _build_grilla(bloques: list) -> tuple[dict, list]:
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

    if not es_profesor:
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
        if _s["grupos"]:
            _s["grupo_id"] = _s["grupos"][0].id
        elif hasattr(ctx, "grupo_id") and ctx.grupo_id:
            _s["grupo_id"] = ctx.grupo_id

    # ── Ampliar _s con campos de escenarios (rama gestión) ────────────────────
    if not es_profesor:
        _s["escenarios"]    = []
        _s["escenario_sel"] = None
        _s["anio_id"]       = _s["config"].id if _s["config"] else None
        # Estado de la parrilla visual (paso_15e)
        _s["parrilla_perspectiva"] = "Grupo"   # Grupo | Docente | Sala
        _s["parrilla_eje_sel"]     = None        # elemento concreto del eje
        # Filtros de la parrilla (paso_15f); None = "todos" (sin filtrar)
        _s["parrilla_filtro_areas"] = None       # set[int] | None
        _s["parrilla_filtro_dias"]  = None       # set[str] | None
        # Vista unificada de horario (rediseño): modo + día del tablero maestro
        _s["parrilla_modo"]         = "Por entidad"  # "Por entidad" | "Tablero maestro"
        _s["parrilla_dia_maestro"]  = None       # str | None

    # ── Estado docente ────────────────────────────────────────────────────────
    _hoy = date.today()
    _dia_hoy_es = _DIA_MAP.get(_hoy.strftime("%A"), "Lunes")
    if _dia_hoy_es not in _DIAS_BASE:
        _dia_hoy_es = "Lunes"

    _s_doc: dict = {
        "bloques":    [],
        "vista_grid": "semana",
        "dia_sel":    _dia_hoy_es,
        "mes_sel":    _hoy.month,
        "anio_cal":   _hoy.year,
        "clases_mes": 0,
        "periodo_id": _s["periodo_id"],
        "anio_id":    _s["config"].id if _s["config"] else None,
    }

    # ── Función de carga de bloques (rama gestión — legacy, no se usa en escenarios) ─

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

    # ── Función de carga de escenarios ────────────────────────────────────────

    def _cargar_escenarios() -> None:
        anio_id = _s["anio_id"]
        if not anio_id:
            _s["escenarios"] = []
            _s["escenario_sel"] = None
            return
        try:
            svc = Container.infraestructura_service()
            _s["escenarios"] = svc.listar_escenarios(anio_id)
            # Preseleccionar el activo; si no hay activo, el primero
            activo = next((e for e in _s["escenarios"] if e.activo), None)
            _s["escenario_sel"] = activo or (_s["escenarios"][0] if _s["escenarios"] else None)
        except Exception as exc:
            logger.error("Error cargando escenarios: %s", exc)
            _s["escenarios"] = []
            _s["escenario_sel"] = None

    # ── Función de carga de bloques por escenario ─────────────────────────────

    def _cargar_bloques_escenario() -> None:
        esc = _s["escenario_sel"]
        grp = _s["grupo_id"]
        if not esc or not grp:
            _s["bloques"] = []
            return
        try:
            _s["bloques"] = Container.infraestructura_service().listar_horario_grupo_escenario(
                grp, esc.id
            )
        except Exception as exc:
            logger.error("Error cargando bloques escenario: %s", exc)
            _s["bloques"] = []

    # ── Funciones de carga docente ────────────────────────────────────────────

    def _cargar_bloques_docente() -> None:
        if not _s_doc["periodo_id"]:
            _s_doc["bloques"] = []
            return
        try:
            _s_doc["bloques"] = Container.infraestructura_service().listar_horario_docente(
                ctx.usuario_id, _s_doc["periodo_id"]
            )
        except Exception as exc:
            logger.error("Error cargando horario docente: %s", exc)
            _s_doc["bloques"] = []

    def _cargar_clases_mes() -> None:
        try:
            _s_doc["clases_mes"] = Container.asistencia_service().contar_clases_mes(
                ctx.usuario_id, _s_doc["anio_cal"], _s_doc["mes_sel"]
            )
        except Exception as exc:
            logger.error("Error contando clases del mes: %s", exc)
            _s_doc["clases_mes"] = 0

    # Carga inicial
    if es_profesor:
        _cargar_bloques_docente()
        _cargar_clases_mes()
    else:
        _cargar_escenarios()
        _cargar_bloques_escenario()

    # ── Refreshables (rama gestión) ───────────────────────────────────────────

    @ui.refreshable
    def escenarios_refreshable() -> None:
        from src.interface.design.components import status_badge
        escenarios = _s["escenarios"]
        sel = _s["escenario_sel"]

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center justify-between flex-wrap gap-2"):
                ui.label("Escenarios de horario").classes("text-subtitle1 font-semibold")
                if puede_escribir:
                    btn_secondary("Nuevo escenario", icon="add", on_click=_crear_escenario_dialog)

            if not escenarios:
                ui.label("No hay escenarios creados para este año.").classes("text-caption text-grey-6 q-mt-sm")
                return

            with ui.element("div").classes("q-mt-sm flex flex-wrap gap-2"):
                for esc in escenarios:
                    is_sel = sel and sel.id == esc.id
                    chip_classes = "cursor-pointer rounded px-3 py-1 border text-sm " + (
                        "border-primary text-primary font-semibold" if is_sel
                        else "border-grey-3 text-grey-8"
                    )
                    with ui.element("div").classes(chip_classes).on("click", lambda _, e=esc: _seleccionar_escenario(e)):
                        with ui.row().classes("items-center gap-1"):
                            ui.label(esc.nombre)
                            if esc.activo:
                                status_badge("Activo", variante="success")

            # Acciones del escenario seleccionado
            if sel and puede_escribir:
                with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
                    if not sel.activo:
                        btn_primary("Activar", icon="check_circle",
                                    on_click=lambda: _activar_escenario(sel.id))
                    btn_secondary("Renombrar", icon="edit",
                                  on_click=lambda: _renombrar_escenario_dialog(sel))
                    btn_secondary("Duplicar", icon="content_copy",
                                  on_click=lambda: _duplicar_escenario_dialog(sel))
                    btn_danger("Eliminar", icon="delete",
                               on_click=lambda: _eliminar_escenario_confirm(sel))

    # ── Refreshables (rama docente) ───────────────────────────────────────────

    @ui.refreshable
    def grilla_docente_refreshable() -> None:
        bloques = _s_doc["bloques"]
        if not bloques:
            empty_state(
                icono=Icons.SCHEDULE,
                titulo="Sin horario registrado",
                descripcion="No tienes bloques asignados en el horario vigente.",
            )
            return

        if _s_doc["vista_grid"] == "semana":
            grilla, dias = _build_grilla(bloques)
            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("overflow-auto"):
                    with ui.element("table").classes("w-full border-collapse"):
                        with ui.element("thead"):
                            with ui.element("tr"):
                                with ui.element("th").classes(
                                    "border px-3 py-2 text-left text-sm font-semibold bg-grey-2"
                                ):
                                    ui.label("Hora")
                                for dia in dias:
                                    with ui.element("th").classes(
                                        "border px-3 py-2 text-center text-sm font-semibold bg-grey-2"
                                    ):
                                        ui.label(str(dia))
                        with ui.element("tbody"):
                            for hora_key, celdas in grilla.items():
                                with ui.element("tr"):
                                    with ui.element("td").classes(
                                        "border px-3 py-2 text-sm font-medium text-grey-8 whitespace-nowrap"
                                    ):
                                        ui.label(str(hora_key))
                                    for dia in dias:
                                        bloque = celdas.get(dia)
                                        with ui.element("td").classes(
                                            "border px-2 py-2 text-sm align-top min-w-[120px]"
                                        ):
                                            if bloque is None:
                                                ui.label("—").classes("text-grey-4 text-center block")
                                            else:
                                                with ui.element("div").classes("bg-info-soft rounded p-1"):
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
                                                    ui.label(f"hasta {hora_fin}").classes(
                                                        "text-xs text-grey-5 block"
                                                    )
        else:
            # Vista diaria — listar bloques de dia_sel ordenados por hora_inicio
            bloques_dia = sorted(
                [b for b in bloques
                 if (b.dia_semana.value if hasattr(b.dia_semana, "value") else b.dia_semana) == _s_doc["dia_sel"]],
                key=lambda b: b.hora_inicio,
            )
            if not bloques_dia:
                empty_state(
                    icono=Icons.SCHEDULE,
                    titulo=f"Sin clases el {_s_doc['dia_sel']}",
                    descripcion="No tienes bloques asignados para este día.",
                )
            else:
                with ui.element("div").classes("panel-card"):
                    for b in bloques_dia:
                        with ui.element("div").classes("flex items-start gap-3 py-2 border-b"):
                            ui.label(
                                f"{b.hora_inicio.strftime('%H:%M')} – {b.hora_fin.strftime('%H:%M')}"
                            ).classes("text-sm font-semibold text-grey-8 w-32 no-shrink")
                            with ui.element("div"):
                                ui.label(b.asignatura_nombre).classes("text-sm font-semibold text-primary")
                                ui.label(f"Grupo: {getattr(b, 'grupo_nombre', b.grupo_id)}").classes("text-xs text-grey-7")
                                if b.sala and b.sala != "Aula":
                                    ui.label(f"Sala: {b.sala}").classes("text-xs text-grey-5")

    @ui.refreshable
    def metricas_docente_refreshable() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center gap-4 flex-wrap"):
                stat_card(
                    titulo="Clases dictadas",
                    valor=str(_s_doc["clases_mes"]),
                    icono="school",
                    subtitulo=f"mes {_s_doc['mes_sel']}/{_s_doc['anio_cal']}",
                )
                # Selector mes/año
                meses = {i: f"Mes {i}" for i in range(1, 13)}
                anio_actual = date.today().year
                anios = {y: str(y) for y in range(anio_actual - 1, anio_actual + 1)}

                ui.select(
                    label="Mes",
                    options=meses,
                    value=_s_doc["mes_sel"],
                    on_change=lambda e: _on_cambio_mes(e.value, _s_doc["anio_cal"]),
                ).classes("w-28")
                ui.select(
                    label="Año",
                    options=anios,
                    value=_s_doc["anio_cal"],
                    on_change=lambda e: _on_cambio_mes(_s_doc["mes_sel"], e.value),
                ).classes("w-24")

    # ── Handlers docente ──────────────────────────────────────────────────────

    def _on_cambio_mes(mes: int, anio: int) -> None:
        _s_doc["mes_sel"] = mes
        _s_doc["anio_cal"] = anio
        _cargar_clases_mes()
        metricas_docente_refreshable.refresh()

    def _toggle_vista_doc(valor: str) -> None:
        _s_doc["vista_grid"] = valor
        grilla_docente_refreshable.refresh()

    def _cambiar_dia_doc(dia: str) -> None:
        _s_doc["dia_sel"] = dia
        grilla_docente_refreshable.refresh()

    # ── Handlers de escenarios ────────────────────────────────────────────────

    def _seleccionar_escenario(esc) -> None:
        _s["escenario_sel"] = esc
        _cargar_bloques_escenario()
        escenarios_refreshable.refresh()
        parrilla_unificada_refreshable.refresh()

    def _crear_escenario_dialog() -> None:
        def _guardar(datos: dict) -> "bool | None":
            nombre = (datos.get("nombre") or "").strip()
            if not nombre:
                toast_warning("El nombre es obligatorio.")
                return False
            try:
                nuevo = Container.infraestructura_service().crear_escenario_simple(
                    anio_id=_s["anio_id"],
                    nombre=nombre,
                    descripcion=datos.get("descripcion") or None,
                )
                _s["escenarios"].append(nuevo)
                _s["escenario_sel"] = nuevo
                _cargar_bloques_escenario()
                escenarios_refreshable.refresh()
                parrilla_unificada_refreshable.refresh()
                toast_success(f"Escenario '{nuevo.nombre}' creado")
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error creando escenario: %s", exc)
                toast_error("Error al crear el escenario")
                return False

        form_dialog(
            titulo="Nuevo escenario",
            campos=[
                {"key": "nombre", "label": "Nombre *", "tipo": "text", "requerido": True},
                {"key": "descripcion", "label": "Descripción", "tipo": "text"},
            ],
            on_submit=_guardar,
        )

    def _activar_escenario(escenario_id: int) -> None:
        try:
            Container.infraestructura_service().activar_escenario(escenario_id)
            _cargar_escenarios()
            escenarios_refreshable.refresh()
            toast_success("Escenario activado")
        except Exception as exc:
            logger.error("Error activando escenario: %s", exc)
            toast_error(str(exc))

    def _renombrar_escenario_dialog(esc) -> None:
        def _guardar(datos: dict) -> "bool | None":
            nombre = (datos.get("nombre") or "").strip()
            if not nombre:
                toast_warning("El nombre es obligatorio.")
                return False
            try:
                Container.infraestructura_service().renombrar_escenario(
                    esc_existente=esc,
                    nombre=nombre,
                    descripcion=datos.get("descripcion") or None,
                )
                _cargar_escenarios()
                escenarios_refreshable.refresh()
                toast_success("Escenario renombrado")
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error renombrando escenario: %s", exc)
                toast_error("Error al renombrar")
                return False

        form_dialog(
            titulo="Renombrar escenario",
            campos=[
                {"key": "nombre", "label": "Nombre *", "tipo": "text",
                 "valor": esc.nombre, "requerido": True},
                {"key": "descripcion", "label": "Descripción", "tipo": "text",
                 "valor": esc.descripcion or ""},
            ],
            on_submit=_guardar,
        )

    def _duplicar_escenario_dialog(esc) -> None:
        def _guardar(datos: dict) -> "bool | None":
            nombre = (datos.get("nombre") or "").strip()
            if not nombre:
                toast_warning("El nombre es obligatorio.")
                return False
            try:
                nuevo = Container.infraestructura_service().duplicar_escenario(esc.id, nombre)
                _cargar_escenarios()
                _s["escenario_sel"] = nuevo
                _cargar_bloques_escenario()
                escenarios_refreshable.refresh()
                parrilla_unificada_refreshable.refresh()
                toast_success(f"Escenario duplicado como '{nuevo.nombre}'")
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error duplicando escenario: %s", exc)
                toast_error("Error al duplicar")
                return False

        form_dialog(
            titulo="Duplicar escenario",
            campos=[
                {"key": "nombre", "label": "Nombre del nuevo escenario *", "tipo": "text",
                 "valor": f"Copia de {esc.nombre}", "requerido": True},
            ],
            on_submit=_guardar,
        )

    def _eliminar_escenario_confirm(esc) -> None:
        def _ok() -> None:
            try:
                Container.infraestructura_service().eliminar_escenario(esc.id)
                _cargar_escenarios()
                escenarios_refreshable.refresh()
                _s["bloques"] = []
                parrilla_unificada_refreshable.refresh()
                toast_success("Escenario eliminado")
            except Exception as exc:
                logger.error("Error eliminando escenario: %s", exc)
                toast_error(str(exc))

        confirm_dialog(
            titulo="Eliminar escenario",
            mensaje=f"¿Eliminar el escenario '{esc.nombre}'? Se eliminarán todos sus bloques.",
            on_confirm=_ok,
            variante="danger",
            texto_confirmar="Eliminar",
            texto_cancelar="Cancelar",
        )

    # ── Handlers de bloques (rama gestión) ────────────────────────────────────

    def _confirmar_eliminar(horario_id: int) -> None:
        def _ok() -> None:
            try:
                Container.horario_service().eliminar_bloque(horario_id)
                toast_success("Bloque eliminado")
                _cargar_bloques_escenario()
                parrilla_unificada_refreshable.refresh()
            except Exception as exc:
                logger.error("Error eliminando bloque: %s", exc)
                toast_error(str(exc))

        confirm_dialog(
            titulo="Eliminar bloque",
            mensaje="¿Eliminar este bloque del horario?",
            on_confirm=_ok,
            variante="danger",
            texto_confirmar="Eliminar",
            texto_cancelar="Cancelar",
        )

    def _abrir_dialog_crear(dia_prefill: str = "", hora_prefill: str = "") -> None:
        esc = _s["escenario_sel"]
        if not esc:
            toast_warning("Selecciona un escenario primero.")
            return

        # Cargar asignaciones
        _s["asignaciones"] = []
        if _s["periodo_id"]:
            try:
                _s["asignaciones"] = Container.asignacion_service().listar_con_info(
                    FiltroAsignacionesDTO(periodo_id=_s["periodo_id"])
                )
            except Exception as exc:
                logger.error("Error cargando asignaciones: %s", exc)

        if not _s["asignaciones"]:
            toast_warning("No hay asignaciones activas en este periodo.")
            return

        asig_opts = {
            a.asignacion_id: f"{a.grupo_codigo} – {a.asignatura_nombre} ({a.docente_nombre})"
            for a in _s["asignaciones"]
        }

        def _guardar(datos: dict) -> "bool | None":
            asig_id = datos.get("asignacion_id")
            if not asig_id:
                toast_warning("Selecciona una asignación.")
                return False
            try:
                Container.horario_service().crear_bloque(
                    escenario_id=esc.id,
                    asignacion_id=asig_id,
                    dia=datos.get("dia", DiaSemana.LUNES.value),
                    hora_inicio=datos.get("hora_inicio", "07:00"),
                    hora_fin=datos.get("hora_fin", "07:55"),
                    sala=str(datos.get("sala", "") or "Aula"),
                )
                toast_success("Bloque guardado")
                _cargar_bloques_escenario()
                parrilla_unificada_refreshable.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error guardando bloque: %s", exc)
                toast_error("Error al guardar el bloque")
                return False

        form_dialog(
            titulo="Agregar bloque de horario",
            campos=[
                {"key": "asignacion_id", "label": "Asignación *", "tipo": "select",
                 "opciones": asig_opts, "requerido": True},
                {"key": "dia", "label": "Día *", "tipo": "select",
                 "opciones": {d.value: d.value for d in DiaSemana},
                 "valor": dia_prefill or DiaSemana.LUNES.value, "requerido": True},
                {"key": "hora_inicio", "label": "Hora inicio", "tipo": "time",
                 "valor": hora_prefill or "07:00"},
                {"key": "hora_fin", "label": "Hora fin", "tipo": "time", "valor": "07:55"},
                {"key": "sala", "label": "Sala", "tipo": "text",
                 "valor": "Aula", "placeholder": "Aula, Lab. Química..."},
            ],
            on_submit=_guardar,
            max_width="max-w-lg",
            columnas=2,
        )

    def _abrir_dialog_editar(horario_id: int) -> None:
        # Obtener el bloque actual. La parrilla unificada muestra TODOS los
        # grupos, por lo que el bloque a editar puede no estar en _s["bloques"]
        # (cargado por grupo). Lo buscamos en todo el escenario.
        bloque = next((b for b in _s["bloques"] if b.id == horario_id), None)
        if not bloque:
            esc = _s["escenario_sel"]
            if esc:
                try:
                    todos = Container.infraestructura_service().listar_horario_escenario(esc.id)
                    bloque = next((b for b in todos if b.id == horario_id), None)
                except Exception as exc:
                    logger.error("Error obteniendo bloque del escenario: %s", exc)
        if not bloque:
            toast_warning("Bloque no encontrado.")
            return

        def _guardar(datos: dict) -> "bool | None":
            try:
                Container.horario_service().actualizar_bloque(
                    horario_id,
                    dia=datos.get("dia", bloque.dia_semana.value if hasattr(bloque.dia_semana, "value") else bloque.dia_semana),
                    hora_inicio=datos.get("hora_inicio", bloque.hora_inicio.strftime("%H:%M")),
                    hora_fin=datos.get("hora_fin", bloque.hora_fin.strftime("%H:%M")),
                    sala=str(datos.get("sala", "") or "Aula"),
                )
                toast_success("Bloque actualizado")
                _cargar_bloques_escenario()
                parrilla_unificada_refreshable.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error editando bloque: %s", exc)
                toast_error("Error al editar el bloque")
                return False

        hora_inicio_str = bloque.hora_inicio.strftime("%H:%M") if hasattr(bloque.hora_inicio, "strftime") else str(bloque.hora_inicio)
        hora_fin_str = bloque.hora_fin.strftime("%H:%M") if hasattr(bloque.hora_fin, "strftime") else str(bloque.hora_fin)
        dia_val = bloque.dia_semana.value if hasattr(bloque.dia_semana, "value") else str(bloque.dia_semana)

        form_dialog(
            titulo="Editar bloque",
            campos=[
                {"key": "dia", "label": "Día *", "tipo": "select",
                 "opciones": {d.value: d.value for d in DiaSemana},
                 "valor": dia_val, "requerido": True},
                {"key": "hora_inicio", "label": "Hora inicio", "tipo": "time",
                 "valor": hora_inicio_str},
                {"key": "hora_fin", "label": "Hora fin", "tipo": "time",
                 "valor": hora_fin_str},
                {"key": "sala", "label": "Sala", "tipo": "text",
                 "valor": bloque.sala or "Aula"},
            ],
            on_submit=_guardar,
            max_width="max-w-md",
            columnas=2,
        )

    # ── Sección horario unificada (rediseño): Por entidad / Tablero maestro ───

    def _parrilla_cargar_datos() -> dict:
        esc = _s["escenario_sel"]
        if not esc:
            return {"dias": [], "franjas": [], "celdas": []}
        try:
            return Container.horario_service().datos_parrilla(esc.id)
        except Exception as exc:
            logger.error("Error cargando datos de parrilla: %s", exc)
            return {"dias": [], "franjas": [], "celdas": []}

    def _parrilla_opciones_eje(datos: dict, perspectiva: str) -> dict:
        """Mapa {clave_eje: etiqueta} según la perspectiva activa."""
        opts: dict = {}
        for c in datos["celdas"]:
            if perspectiva == "Grupo":
                opts.setdefault(c["grupo_id"], c["grupo_codigo"])
            elif perspectiva == "Docente":
                opts.setdefault(c["usuario_id"], c["docente_nombre"])
            else:  # Sala
                opts.setdefault(c["sala"], c["sala"])
        return dict(sorted(opts.items(), key=lambda kv: str(kv[1])))

    def _parrilla_cargar_metricas() -> dict:
        esc = _s["escenario_sel"]
        vacio = {
            "total_bloques": 0, "n_grupos": 0, "n_docentes": 0,
            "n_salas": 0, "huecos_grupo": 0, "ocupacion_pct": 0,
        }
        if not esc:
            return vacio
        try:
            return Container.horario_service().metricas_parrilla(esc.id)
        except Exception as exc:
            logger.error("Error cargando métricas de parrilla: %s", exc)
            return vacio

    def _parrilla_cargar_areas() -> list[dict]:
        esc = _s["escenario_sel"]
        if not esc:
            return []
        try:
            return Container.horario_service().areas_parrilla(esc.id)
        except Exception as exc:
            logger.error("Error cargando áreas de parrilla: %s", exc)
            return []

    # ── Handlers de estado de la parrilla ─────────────────────────────────────

    def _cambiar_modo(valor: str) -> None:
        _s["parrilla_modo"] = valor
        parrilla_unificada_refreshable.refresh()

    def _cambiar_perspectiva(valor: str) -> None:
        _s["parrilla_perspectiva"] = valor
        _s["parrilla_eje_sel"] = None
        parrilla_unificada_refreshable.refresh()

    def _cambiar_eje(valor) -> None:
        _s["parrilla_eje_sel"] = valor
        parrilla_unificada_refreshable.refresh()

    def _cambiar_dia_maestro(valor: str) -> None:
        _s["parrilla_dia_maestro"] = valor
        parrilla_unificada_refreshable.refresh()

    def _segmento(opciones: list[str], valor_actual: str, on_change) -> None:
        with ui.element("div").classes("parrilla-segmento"):
            for _op in opciones:
                _cls = "parrilla-seg-btn" + (" parrilla-seg-btn-activo" if _op == valor_actual else "")
                _btn = ui.element("div").classes(_cls)
                _btn.on("click", lambda _, o=_op: on_change(o))
                with _btn:
                    ui.label(str(_op))

    def _cambiar_filtro_areas(valores) -> None:
        # ui.select multiple devuelve list; None/[] => sin filtro (todas)
        _s["parrilla_filtro_areas"] = set(valores) if valores else None
        parrilla_unificada_refreshable.refresh()

    def _cambiar_filtro_dias(valores) -> None:
        _s["parrilla_filtro_dias"] = set(valores) if valores else None
        parrilla_unificada_refreshable.refresh()

    def _editar_color_area(area: dict) -> None:
        def _guardar(datos: dict) -> "bool | None":
            color = (datos.get("color") or "").strip() or None
            try:
                Container.infraestructura_service().set_color_area(
                    area["area_id"], color
                )
                toast_success(f"Color de '{area['area_nombre']}' actualizado")
                parrilla_unificada_refreshable.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error actualizando color de área: %s", exc)
                toast_error("No se pudo actualizar el color")
                return False

        form_dialog(
            titulo=f"Color de «{area['area_nombre']}»",
            campos=[
                {"key": "color", "label": "Color", "tipo": "color",
                 "valor": area.get("color") or ""},
            ],
            on_submit=_guardar,
            max_width="max-w-xs",
        )

    # ── Clic en celda → menú editar/eliminar (ocupada) o alta (vacía) ─────────

    def _on_celda_click(ctx_celda: dict) -> None:
        if not puede_escribir:
            return
        if ctx_celda.get("tipo") == "ocupada":
            celda = ctx_celda.get("celda") or {}
            bid = celda.get("id")
            if bid is None:
                return
            with ui.menu() as menu:
                with ui.menu_item(on_click=lambda: (menu.close(), _abrir_dialog_editar(bid))):
                    with ui.row().classes("items-center gap-2"):
                        ThemeManager.icono(Icons.EDIT)
                        ui.label("Editar")
                with ui.menu_item(on_click=lambda: (menu.close(), _confirmar_eliminar(bid))):
                    with ui.row().classes("items-center gap-2"):
                        ThemeManager.icono(Icons.DELETE)
                        ui.label("Eliminar")
            menu.open()
        else:  # vacía
            grupo_id = ctx_celda.get("grupo_id")
            if grupo_id is not None:
                _s["grupo_id"] = grupo_id
            _abrir_dialog_crear(
                dia_prefill=ctx_celda.get("dia", ""),
                hora_prefill=ctx_celda.get("hora_inicio", ""),
            )

    @ui.refreshable
    def parrilla_unificada_refreshable() -> None:
        esc = _s["escenario_sel"]
        with ui.element("div").classes("panel-card q-mt-sm"):
            # Toolbar superior: modo + acción de alta
            with ui.row().classes("items-center justify-between flex-wrap gap-2"):
                ui.label("Parrilla").classes("text-subtitle1 font-semibold")
                with ui.row().classes("items-center gap-2"):
                    _segmento(
                        ["Por entidad", "Tablero maestro"],
                        _s["parrilla_modo"],
                        _cambiar_modo,
                    )
                    if puede_escribir:
                        btn_secondary("Agregar bloque", icon="add",
                                      on_click=lambda: _abrir_dialog_crear())

            if not esc:
                empty_state(
                    icono=Icons.SCHEDULE,
                    titulo="Sin escenario seleccionado",
                    descripcion="Selecciona un escenario para ver la parrilla.",
                )
                return

            datos = _parrilla_cargar_datos()

            # ── Métricas (tira compacta) ───────────────────────────────────
            m = _parrilla_cargar_metricas()
            with ui.element("div").classes("parrilla-metricas"):
                for _val, _lbl in [
                    (str(m["total_bloques"]), "Bloques"),
                    (str(m["n_grupos"]), "Grupos"),
                    (str(m["n_docentes"]), "Docentes"),
                    (str(m["huecos_grupo"]), "Huecos"),
                    (f"{m['ocupacion_pct']}%", "Ocupación"),
                ]:
                    with ui.element("div").classes("parrilla-metrica"):
                        ui.label(_val).classes("parrilla-metrica-valor")
                        ui.label(_lbl).classes("parrilla-metrica-label")

            if not datos["celdas"] or not datos["franjas"]:
                empty_state(
                    icono=Icons.SCHEDULE,
                    titulo="Escenario sin bloques",
                    descripcion="No hay bloques para visualizar en la parrilla.",
                    cta_label="Agregar bloque" if puede_escribir else None,
                    cta_on_click=(lambda: _abrir_dialog_crear()) if puede_escribir else None,
                    cta_icono="add",
                )
                return

            areas = _parrilla_cargar_areas()
            dias_activos = datos["dias"] or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
            f_areas = _s["parrilla_filtro_areas"]

            if _s["parrilla_modo"] == "Tablero maestro":
                # ── Selector de día (chips) ────────────────────────────────
                dia_maestro = _s["parrilla_dia_maestro"]
                if dia_maestro not in dias_activos:
                    dia_maestro = dias_activos[0]
                    _s["parrilla_dia_maestro"] = dia_maestro

                ui.label("Selecciona el día").classes("parrilla-chips-label")
                with ui.element("div").classes("parrilla-chips"):
                    for d in dias_activos:
                        activo = (d == dia_maestro)
                        chip_cls = "parrilla-chip" + (" parrilla-chip-activo" if activo else "")
                        _chip = ui.element("div").classes(chip_cls)
                        _chip.on("click", lambda _, dd=d: _cambiar_dia_maestro(dd))
                        with _chip:
                            ui.label(str(d))

                # ── Filtro de área ─────────────────────────────────────────
                with ui.element("div").classes("parrilla-toolbar"):
                    ui.label("Filtrar:").classes("parrilla-filtro-label")
                    if areas:
                        area_opts = {a["area_id"]: a["area_nombre"] for a in areas}
                        area_val = (
                            [aid for aid in f_areas if aid in area_opts]
                            if f_areas is not None else list(area_opts)
                        )
                        ui.select(
                            label="Áreas",
                            options=area_opts,
                            value=area_val,
                            multiple=True,
                            on_change=lambda e: _cambiar_filtro_areas(e.value),
                        ).classes("w-64")

                render_tablero_maestro(
                    datos=datos,
                    dia=dia_maestro,
                    areas_filtro=f_areas,
                    on_celda_click=_on_celda_click,
                    puede_editar=puede_escribir,
                )

            else:
                # ── Modo "Por entidad" ─────────────────────────────────────
                perspectiva = _s["parrilla_perspectiva"]
                f_dias = _s["parrilla_filtro_dias"]

                # Segmentado de perspectiva
                with ui.element("div").classes("parrilla-toolbar"):
                    _segmento(
                        ["Grupo", "Docente", "Sala"],
                        perspectiva,
                        _cambiar_perspectiva,
                    )

                # Selector de entidad como CHIPS
                eje_opts = _parrilla_opciones_eje(datos, perspectiva)
                if eje_opts:
                    eje_sel = _s["parrilla_eje_sel"]
                    if eje_sel not in eje_opts:
                        eje_sel = next(iter(eje_opts))
                        _s["parrilla_eje_sel"] = eje_sel
                    _nombre_eje = {"Grupo": "grupo", "Docente": "docente", "Sala": "sala"}[perspectiva]
                    ui.label(f"Selecciona un {_nombre_eje} para ver su horario").classes("parrilla-chips-label")
                    with ui.element("div").classes("parrilla-chips"):
                        for clave, etiqueta in eje_opts.items():
                            activo = (clave == eje_sel)
                            chip_cls = "parrilla-chip" + (" parrilla-chip-activo" if activo else "")
                            _chip = ui.element("div").classes(chip_cls)
                            _chip.on("click", lambda _, c=clave: _cambiar_eje(c))
                            with _chip:
                                ui.label(str(etiqueta))

                # Filtros Área y Día
                with ui.element("div").classes("parrilla-toolbar"):
                    ui.label("Filtrar:").classes("parrilla-filtro-label")
                    if areas:
                        area_opts = {a["area_id"]: a["area_nombre"] for a in areas}
                        area_val = (
                            [aid for aid in f_areas if aid in area_opts]
                            if f_areas is not None else list(area_opts)
                        )
                        ui.select(
                            label="Áreas",
                            options=area_opts,
                            value=area_val,
                            multiple=True,
                            on_change=lambda e: _cambiar_filtro_areas(e.value),
                        ).classes("w-64")
                    dia_opts = {d: d for d in dias_activos}
                    dia_val = (
                        [d for d in f_dias if d in dia_opts]
                        if f_dias is not None else list(dia_opts)
                    )
                    ui.select(
                        label="Días",
                        options=dia_opts,
                        value=dia_val,
                        multiple=True,
                        on_change=lambda e: _cambiar_filtro_dias(e.value),
                    ).classes("w-64")

                render_parrilla(
                    datos=datos,
                    perspectiva=perspectiva,
                    eje_sel=_s["parrilla_eje_sel"],
                    dias_filtro=f_dias,
                    areas_filtro=f_areas,
                    on_celda_click=_on_celda_click,
                    puede_editar=puede_escribir,
                )

            # ── Leyenda de colores editable ────────────────────────────────
            if areas:
                ui.label("Áreas (clic para cambiar color)").classes(
                    "text-xs text-grey-6 q-mt-sm"
                )
                with ui.element("div").classes("parrilla-leyenda"):
                    for a in areas:
                        item = ui.element("div").classes("parrilla-leyenda-item")
                        with item:
                            color = a.get("color")
                            if color:
                                sw = ui.element("span").classes("parrilla-swatch")
                                sw.style(f"background-color:{color}")  # DYNAMIC
                            else:
                                aid = a["area_id"] or 0
                                ui.element("span").classes(
                                    f"parrilla-swatch parrilla-area-{aid % 10}"
                                )
                            ui.label(a["area_nombre"]).classes(
                                "parrilla-leyenda-label"
                            )
                        item.on("click", lambda _, ar=a: _editar_color_area(ar))

    def _seccion_horario_unificada() -> None:
        parrilla_unificada_refreshable()

    # ── Sección carga masiva ──────────────────────────────────────────────────

    def _seccion_carga_masiva() -> None:
        from src.interface.design.components import status_badge

        _s_lote: dict = {"reporte": None, "filas_raw": []}

        @ui.refreshable
        def reporte_lote_refreshable() -> None:
            reporte = _s_lote["reporte"]
            if reporte is None:
                return
            with ui.element("div").classes("q-mt-sm"):
                ui.label(
                    f"Análisis: {reporte.validas} válidas, {reporte.invalidas} con error"
                ).classes("text-sm text-grey-7 q-mb-xs")
                with ui.element("div").classes("overflow-auto"):
                    with ui.element("table").classes("w-full border-collapse text-xs"):
                        with ui.element("thead"):
                            with ui.element("tr"):
                                for col in ("#", "Estado", "Resumen", "Motivo"):
                                    with ui.element("th").classes(
                                        "border px-2 py-1 text-left bg-grey-2"
                                    ):
                                        ui.label(str(col))
                        with ui.element("tbody"):
                            for f in reporte.filas:
                                with ui.element("tr"):
                                    with ui.element("td").classes("border px-2 py-1"):
                                        ui.label(str(f.indice + 1))
                                    with ui.element("td").classes("border px-2 py-1"):
                                        status_badge(
                                            "OK" if f.ok else "Error",
                                            variante="success" if f.ok else "danger",
                                        )
                                    with ui.element("td").classes("border px-2 py-1"):
                                        ui.label(str(f.resumen))
                                    with ui.element("td").classes("border px-2 py-1"):
                                        ui.label(str(f.motivo or ""))
                with ui.row().classes("gap-2 q-mt-sm"):
                    if reporte.todo_ok:
                        btn_primary("Aplicar todo", icon="upload",
                                    on_click=lambda: _aplicar(False))
                    if reporte.validas > 0:
                        btn_secondary(f"Aplicar solo válidas ({reporte.validas})",
                                      icon="check", on_click=lambda: _aplicar(True))

        def _descargar_plantilla() -> None:
            periodo_id = _s.get("periodo_id")
            if not periodo_id:
                toast_warning("No hay periodo activo seleccionado.")
                return
            filas = Container.horario_service().plantilla_filas(periodo_id)
            if not filas:
                toast_warning("No hay asignaciones activas en el periodo.")
                return
            data = Container.exporter_service().exportar_csv(filas)
            ui.download(data, filename="plantilla_horario.csv")

        def _descargar_horario() -> None:
            esc = _s.get("escenario_sel")
            if esc is None:
                toast_warning("No hay escenario seleccionado.")
                return
            filas = Container.horario_service().filas_exportables(esc.id)
            if not filas:
                toast_warning("El escenario no tiene bloques para exportar.")
                return
            data = Container.exporter_service().exportar_csv(filas)
            ui.download(data, filename=f"horario_{esc.nombre}.csv")

        def _on_upload(e) -> None:
            try:
                raw = e.content.read()
                text = raw.decode("utf-8-sig")
                filas = list(csv.DictReader(io.StringIO(text)))
                if not filas:
                    toast_warning("El archivo no tiene filas de datos.")
                    return
                esc = _s.get("escenario_sel")
                if not esc:
                    toast_warning("Selecciona un escenario primero.")
                    return
                _s_lote["filas_raw"] = filas
                reporte = Container.horario_service().analizar_lote(
                    esc.id, _s.get("periodo_id") or 0, filas
                )
                _s_lote["reporte"] = reporte
                reporte_lote_refreshable.refresh()
            except Exception as exc:
                logger.error("Error procesando archivo: %s", exc)
                toast_error(f"Error al procesar el archivo: {exc}")

        def _aplicar(solo_validas: bool) -> None:
            esc = _s.get("escenario_sel")
            if not esc or not _s_lote["filas_raw"]:
                toast_warning("Sin datos para aplicar.")
                return
            try:
                resultado = Container.horario_service().aplicar_lote(
                    esc.id, _s.get("periodo_id") or 0,
                    _s_lote["filas_raw"], solo_validas=solo_validas,
                )
                if resultado.creados == 0 and not solo_validas:
                    toast_warning("No se creó ningún bloque. Revisa los errores del reporte.")
                else:
                    toast_success(f"{resultado.creados} bloques creados, {resultado.omitidos} omitidos.")
                    _s_lote["reporte"] = None
                    _s_lote["filas_raw"] = []
                    _cargar_bloques_escenario()
                    parrilla_unificada_refreshable.refresh()
                    reporte_lote_refreshable.refresh()
            except Exception as exc:
                logger.error("Error aplicando lote: %s", exc)
                toast_error(str(exc))

        with ui.element("div").classes("panel-card q-mt-sm"):
            with ui.row().classes("items-center justify-between q-mb-sm"):
                ui.label("Carga masiva de bloques").classes("text-subtitle1 font-semibold")
                with ui.row().classes("gap-2"):
                    btn_secondary("Descargar plantilla", icon="download",
                                  on_click=_descargar_plantilla)
                    if puede_escribir:
                        btn_secondary("Descargar horario", icon="table_view",
                                      on_click=_descargar_horario)
            ui.label(
                "Columnas requeridas: asignacion_id, dia_semana, hora_inicio, hora_fin, sala"
            ).classes("text-caption text-grey-6 q-mb-xs")
            ui.upload(label="Subir CSV", on_upload=_on_upload, auto_upload=True).classes("w-full")
            reporte_lote_refreshable()

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def contenido() -> None:

        with ui.element("div").classes("page-stack"):

            if es_profesor:
                # ── Rama docente ──────────────────────────────────────────────

                # Panel de controles docente
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes("items-center gap-3 flex-wrap"):
                        ui.label("Vista:").classes("text-sm text-grey-7")
                        btn_secondary(
                            "Semana",
                            on_click=lambda: _toggle_vista_doc("semana"),
                        )
                        btn_secondary(
                            "Día",
                            on_click=lambda: _toggle_vista_doc("dia"),
                        )
                        # Selector de día (solo en vista diaria)
                        if _s_doc["vista_grid"] == "dia":
                            dia_opts = {d: d for d in _DIAS_BASE}
                            ui.select(
                                label="Día",
                                options=dia_opts,
                                value=_s_doc["dia_sel"],
                                on_change=lambda e: _cambiar_dia_doc(e.value),
                            ).classes("w-32")

                # Métricas (tarjeta de clases)
                metricas_docente_refreshable()

                # Grilla docente
                grilla_docente_refreshable()

            else:
                # ── Rama gestión (admin/director/coordinador) ─────────────────────
                # Panel de escenarios
                escenarios_refreshable()

                # Sección unificada: Por entidad / Tablero maestro con edición
                # integrada en la celda (clic). El grupo se elige con chips o
                # columnas, no con un selector aparte.
                _seccion_horario_unificada()

                if puede_escribir:
                    _seccion_carga_masiva()

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
