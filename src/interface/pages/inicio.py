"""
src/interface/pages/inicio.py
==============================
Dashboard principal de ZECI Manager v2.0.
Regla de CSS: ningún style="" con valores estáticos.
Solo inline para valores calculados dinámicamente (marcados # DYNAMIC).
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.tokens import Icons
from src.interface.design.theme import ThemeManager
from src.interface.design.components.status_badge import status_badge
from src.interface.design.components import stat_card, empty_state
from src.interface.design.components.buttons import btn_secondary
from src.interface.design.layout import app_layout
from src.services.auditoria_service import FiltroAuditoriaDTO
from src.services.alerta_service import FiltroAlertasDTO

logger = logging.getLogger("INICIO")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _saludo_temporal() -> str:
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Buenos días"
    elif 12 <= hora < 20:
        return "Buenas tardes"
    return "Buenas noches"


def _tiempo_relativo(ts) -> str:
    try:
        if ts is None:
            return "—"
        fecha = (
            datetime.fromisoformat(ts) if isinstance(ts, str) and "T" in ts
            else datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S") if isinstance(ts, str)
            else ts
        )
        delta = datetime.now() - fecha
        if delta.days > 0:
            return f"Hace {delta.days}d"
        h = delta.seconds // 3600
        if h > 0:
            return f"Hace {h}h"
        m = delta.seconds // 60
        return f"Hace {m}m" if m > 0 else "Ahora"
    except Exception:
        return "—"


def _clase_dias(dias: int) -> str:
    if dias > 14:
        return "hito-dias-ok"
    if dias > 5:
        return "hito-dias-warning"
    return "hito-dias-danger"


def _clase_periodo_bar(progreso: float) -> str:
    if progreso < 60:
        return ""
    if progreso < 85:
        return "warning"
    return "error"


def _clase_period_days(dias_restantes: int) -> str:
    if dias_restantes < 7:
        return "period-days period-days-danger"
    if dias_restantes < 15:
        return "period-days period-days-warn"
    return "period-days period-days-ok"


def _panel_titulo(icono: str, texto: str, color: str = "var(--color-primary)") -> None:
    """Encabezado estándar de panel. Usa .panel-header y .panel-title."""
    with ui.element("div").classes("panel-header"):
        ThemeManager.icono(icono, size=20, color=color)
        ui.label(texto).classes("panel-title")


# ── SECCIÓN 1 — Saludo + Estado del periodo ───────────────────────────────────

def _seccion_saludo(ctx: SessionContext, config) -> None:
    _MENSAJES = {
        "profesor":    "Gestiona notas, asistencia y seguimiento de tus estudiantes",
        "director":    "Monitorea el desempeño académico de tu institución",
        "coordinador": "Supervisa la convivencia y el seguimiento académico",
        "admin":       "Administra la configuración y los usuarios del sistema",
    }
    _LABELS = {
        "profesor":    "Docente",
        "director":    "Director",
        "coordinador": "Coordinador",
        "admin":       "Administrador",
    }

    with ui.row().classes("w-full gap-4 items-stretch"):

        # ── Hero de saludo ────────────────────────────────
        with ui.element("div").classes("greeting-hero flex-1"):
            nombre_corto = ctx.usuario_nombre.split()[0] if ctx.usuario_nombre else ""
            ui.label(f"{_saludo_temporal()}, {nombre_corto}").classes("greeting-name")
            ui.label(_MENSAJES.get(ctx.usuario_rol, "Bienvenido")).classes("greeting-desc")
            with ui.element("div").classes("greeting-meta"):
                ThemeManager.icono(Icons.PROFILE, size=16, color="var(--color-primary)")
                ui.label(ctx.usuario_nombre).classes("greeting-user")
                ui.element("span").classes("greeting-dot")
                ui.label(
                    _LABELS.get(ctx.usuario_rol, ctx.usuario_rol.capitalize())
                ).classes("greeting-role")

        # ── Panel estado del periodo ──────────────────────
        with ui.element("div").classes("panel-card period-status-card"):
            ui.label("Periodo activo").classes("eyebrow-label")

            try:
                if config is None:
                    raise ValueError("sin config")

                periodo = Container.periodo_service().get_activo(config.id)
                ui.label(periodo.nombre).classes("period-name")

                hoy = date.today()
                if periodo.fecha_inicio and periodo.fecha_fin:
                    total_dias   = (periodo.fecha_fin - periodo.fecha_inicio).days
                    dias_pasados = (hoy - periodo.fecha_inicio).days
                    dias_rest    = (periodo.fecha_fin - hoy).days
                    progreso     = min(100, max(0,
                        dias_pasados / total_dias * 100 if total_dias > 0 else 0
                    ))
                    clase_bar = _clase_periodo_bar(progreso)

                    with ui.element("div").classes("period-dates-row"):
                        ui.label(periodo.fecha_inicio.strftime("%d %b")).classes("text-xs-meta")
                        ui.label(periodo.fecha_fin.strftime("%d %b")).classes("text-xs-meta")

                    with ui.element("div").classes("period-bar-track"):
                        ui.element("div").classes(
                            f"period-bar-fill {clase_bar}"
                        ).style(f"width:{progreso:.0f}%")  # DYNAMIC: valor calculado

                    ui.label(
                        f"{max(0, dias_rest)} días restantes · {progreso:.0f}% transcurrido"
                    ).classes(_clase_period_days(dias_rest))

                status_badge("Cerrado", "neutral") if periodo.cerrado else status_badge("Activo", "success")

            except Exception:
                ui.label("Sin periodo activo").classes("text-empty")
                ui.label("Configura un periodo en administración").classes("text-hint")


# ── SECCIÓN 2 — Stat cards ────────────────────────────────────────────────────


_ROLES_DIRECTIVO = ("director", "coordinador")


def _seccion_stats(ctx: SessionContext, config) -> None:
    """Stat-cards del profesor: métricas del grupo del chip (vista personal)."""
    _CONFIG = [
        ("Estudiantes",   Icons.STUDENTS,   "primary"),
        ("% Asistencia",  Icons.ATTENDANCE, "success"),
        ("En riesgo",     Icons.ALERTS,     "error"),
        ("Alertas act.",  Icons.ALERTS,     "warning"),
    ]
    valores    = ["—", "—", "—", "—"]
    subtitulos = [""] * 4

    try:
        if ctx and ctx.grupo_id and ctx.periodo_id:
            anio_id = config.id if config else None
            m = Container.estadisticos_service().metricas_dashboard(
                ctx.grupo_id, ctx.periodo_id, anio_id
            )
            valores    = [str(m.total_estudiantes), f"{m.porcentaje_asistencia:.1f}%",
                          str(m.estudiantes_en_riesgo), str(m.alertas_pendientes)]
            subtitulos = ["en tu grupo", "este periodo", "bajo el mínimo", "pendientes"]
        else:
            subtitulos = ["Selecciona un grupo"] * 4
    except Exception as e:
        logger.warning("Error métricas profesor: %s", e)

    with ui.element("div").classes("stats-grid"):
        for i, (titulo_s, icono_s, variante_s) in enumerate(_CONFIG):
            stat_card(
                titulo=titulo_s, valor=valores[i],
                icono=icono_s, subtitulo=subtitulos[i],
                variante=variante_s,
            )


def _seccion_stats_institucional(ctx: SessionContext, config) -> None:
    """Stat-cards del directivo: agregados INSTITUCIONALES del periodo
    (todos los grupos), no las métricas de un único grupo del chip."""
    _CONFIG = [
        ("Estudiantes",    Icons.STUDENTS,   "primary"),
        ("Promedio gral.", Icons.GRADES,     "info"),
        ("% Asistencia",   Icons.ATTENDANCE, "success"),
        ("En riesgo",      Icons.ALERTS,     "error"),
    ]
    valores    = ["—", "—", "—", "—"]
    subtitulos = ["", "", "", ""]

    try:
        anio_id = config.id if config else None
        if ctx and ctx.periodo_id:
            mi = Container.estadisticos_service().metricas_institucionales(
                ctx.periodo_id, anio_id
            )
            if mi.kpi_grupos:
                total_est = sum(g["total"] for g in mi.grupos)
                valores = [
                    str(total_est),
                    f"{mi.kpi_promedio:.1f}",
                    f"{mi.kpi_asistencia:.1f}%",
                    str(mi.kpi_riesgo),
                ]
                subtitulos = [
                    f"en {mi.kpi_grupos} grupos",
                    "promedio entre grupos",
                    "asistencia media",
                    "bajo el mínimo",
                ]
            else:
                subtitulos = ["Sin datos del periodo"] * 4
        else:
            subtitulos = ["Sin periodo activo"] * 4
    except Exception as e:
        logger.warning("Error métricas institucionales: %s", e)

    with ui.element("div").classes("stats-grid"):
        for i, (titulo_s, icono_s, variante_s) in enumerate(_CONFIG):
            stat_card(
                titulo=titulo_s, valor=valores[i],
                icono=icono_s, subtitulo=subtitulos[i],
                variante=variante_s,
            )


# ── SECCIÓN 3 — Acciones rápidas ──────────────────────────────────────────────

def _seccion_acciones_rapidas(rol: str) -> None:
    # Cada acción: (icono, label, desc, ruta, bg_color, icon_color)
    # bg_color e icon_color son DYNAMIC: cada acción tiene su propio color
    _ACCIONES = {
        "profesor": [
            (Icons.ATTENDANCE, "Registrar Asistencia", "Control diario",
             "/asistencia", "var(--color-success-light)", "var(--color-success)"),
            (Icons.GRADES, "Planilla de Notas", "Calificar actividades",
             "/evaluacion/planilla", "var(--color-primary-lighter)", "var(--color-primary)"),
            (Icons.BEHAVIOR, "Convivencia", "Observaciones y registros",
             "/convivencia", "var(--color-warning-light)", "var(--color-warning)"),
            (Icons.REPORTS, "Mis Informes", "Exportar notas y asistencia",
             "/informes", "var(--color-info-light)", "var(--color-info)"),
        ],
        "director": [
            (Icons.REPORTS, "Informes", "Consolidados por grupo",
             "/informes", "var(--color-primary-lighter)", "var(--color-primary)"),
            (Icons.CLOSE_PERIOD, "Cierre de Periodo", "Gestionar cierres",
             "/evaluacion/cierre", "var(--color-warning-light)", "var(--color-warning)"),
            (Icons.TEACHERS, "Docentes", "Carga académica",
             "/admin/usuarios", "var(--color-success-light)", "var(--color-success)"),
            (Icons.CONFIG, "Configuración", "Niveles y criterios SIE",
             "/admin/configuracion", "var(--color-info-light)", "var(--color-info)"),
        ],
        "coordinador": [
            (Icons.BEHAVIOR, "Convivencia", "Seguimiento disciplinario",
             "/convivencia", "var(--color-warning-light)", "var(--color-warning)"),
            (Icons.ALERTS, "Alertas Activas", "Estudiantes en seguimiento",
             "/alertas", "var(--color-error-light)", "var(--color-error)"),
            (Icons.STUDENTS, "Estudiantes", "Listado y PIAR",
             "/estudiantes", "var(--color-primary-lighter)", "var(--color-primary)"),
            (Icons.REPORTS, "Informes", "Reportes de seguimiento",
             "/informes", "var(--color-info-light)", "var(--color-info)"),
        ],
    }
    acciones = _ACCIONES.get(rol, _ACCIONES["profesor"])

    with ui.element("div").classes("panel-card"):
        _panel_titulo("bolt", "Accesos rápidos")
        with ui.grid(columns=2).classes("w-full gap-3"):
            for icono, label, desc, ruta, bg, icon_color in acciones:
                with ui.element("div").classes("quick-action-card").on(
                    "click", lambda r=ruta: ui.navigate.to(r)
                ):
                    with ui.element("div").classes("quick-action-icon").style(  # DYNAMIC: bg por acción
                        f"background:{bg}"
                    ):
                        ThemeManager.icono(icono, size=22, color=icon_color)
                    with ui.element("div").classes("action-text-col"):
                        ui.label(label).classes("action-label")
                        ui.label(desc).classes("action-desc")


# ── SECCIÓN 4 — Feed de actividad reciente ────────────────────────────────────

def _seccion_actividad_reciente(ctx: SessionContext) -> None:
    with ui.element("div").classes("panel-card"):
        _panel_titulo("history", "Actividad reciente")

        try:
            cambios = Container.auditoria_service().listar_cambios(
                FiltroAuditoriaDTO(
                    usuario_id=ctx.usuario_id if ctx.usuario_rol == "profesor" else None,
                    pagina=1, por_pagina=6,
                )
            )

            if not cambios:
                ui.label("Sin actividad reciente").classes("empty-state-lg")
                return

            _ETIQUETAS = {
                "notas":          "Calificación registrada",
                "control_diario": "Asistencia registrada",
                "convivencia":    "Registro de convivencia",
                "habilitaciones": "Habilitación actualizada",
                "alertas":        "Alerta generada",
            }
            for cambio in cambios:
                tabla    = getattr(cambio, "tabla", "sistema")
                etiqueta = _ETIQUETAS.get(tabla, tabla.replace("_", " ").capitalize())
                tiempo   = _tiempo_relativo(getattr(cambio, "timestamp", None))

                with ui.element("div").classes("activity-feed-item"):
                    ui.element("div").classes("activity-dot")
                    with ui.element("div").classes("feed-text-col"):
                        ui.label(etiqueta).classes("feed-label")
                        ui.label(tabla).classes("feed-meta")
                    ui.label(tiempo).classes("feed-time")

        except Exception as e:
            logger.warning("Error actividad reciente: %s", e)
            ui.label("No disponible").classes("unavailable-text")


# ── SECCIÓN 5 — Alertas pendientes ───────────────────────────────────────────

def _seccion_alertas(ctx: SessionContext) -> None:
    with ui.element("div").classes("panel-card"):
        _panel_titulo(Icons.ALERTS, "Alertas pendientes", "var(--color-error)")

        try:
            alertas = Container.alerta_service().listar_alertas(
                FiltroAlertasDTO(solo_pendientes=True, por_pagina=10)
            )

            if not alertas:
                with ui.element("div").classes("flex-col items-center"):
                    ThemeManager.icono("check_circle", size=36, color="var(--color-success)")
                    ui.label("Sin alertas pendientes").classes("success-empty-text")
                return

            criticas     = [a for a in alertas if str(getattr(a, "nivel", "")).lower() == "critica"]
            advertencias = [a for a in alertas if str(getattr(a, "nivel", "")).lower() == "advertencia"]

            if criticas:
                with ui.element("div").classes("alert-summary alert-summary-error"):
                    ThemeManager.icono("error", size=18, color="var(--color-error)")
                    ui.label(f"{len(criticas)} alerta(s) crítica(s)").classes("alert-count-text")

            if advertencias:
                with ui.element("div").classes("alert-summary alert-summary-warning"):
                    ThemeManager.icono("warning", size=18, color="var(--color-warning)")
                    ui.label(f"{len(advertencias)} advertencia(s)").classes("alert-count-text")

            _clase_map  = {"critica": "alerta-critica", "advertencia": "alerta-advertencia"}
            _icono_map  = {"critica": "error",          "advertencia": "warning"}
            _color_map  = {
                "critica":     "var(--color-error)",
                "advertencia": "var(--color-warning)",
            }

            for alerta in alertas[:5]:
                nivel   = str(getattr(alerta, "nivel", "info")).lower()
                tipo    = str(getattr(alerta, "tipo_alerta", "alerta")).replace("_", " ").capitalize()
                clase   = _clase_map.get(nivel, "alerta-info")
                icono_n = _icono_map.get(nivel, "info")
                color   = _color_map.get(nivel, "var(--color-info)")

                with ui.element("div").classes(f"alerta-item {clase}"):
                    ThemeManager.icono(icono_n, size=16, color=color)
                    ui.label(tipo).classes("alerta-item-text")

            if len(alertas) > 5:
                ui.label(f"+ {len(alertas) - 5} más").classes("more-items-text")

        except Exception as e:
            logger.warning("Error alertas: %s", e)
            ui.label("No disponible").classes("unavailable-text")


# ── SECCIÓN 6 — Hitos próximos ────────────────────────────────────────────────

def _seccion_hitos(config) -> None:
    with ui.element("div").classes("panel-card"):
        _panel_titulo(Icons.PERIODS, "Próximas fechas")

        try:
            if config is None:
                raise ValueError("sin config")

            hitos = Container.periodo_service().listar_hitos_proximos(
                anio_id=config.id, dias=30
            )

            if not hitos:
                ui.label("Sin hitos en los próximos 30 días").classes("empty-state")
                return

            hoy = date.today()
            for hito in hitos[:6]:
                fecha_limite = getattr(hito, "fecha_limite", None)
                descripcion  = getattr(hito, "descripcion", "Hito")
                dias_txt     = "—"
                clase_dias   = "hito-dias-ok"

                if fecha_limite:
                    dias = (fecha_limite - hoy).days
                    clase_dias = _clase_dias(dias)
                    dias_txt   = f"{dias}d" if dias > 0 else "HOY"

                with ui.element("div").classes("hito-item"):
                    with ui.element("div").classes(f"hito-dias-badge {clase_dias}"):
                        ui.label(dias_txt)
                    with ui.element("div").classes("hito-text-col"):
                        ui.label(str(descripcion)[:45]).classes("hito-desc")
                        if fecha_limite:
                            ui.label(fecha_limite.strftime("%d %b %Y")).classes("hito-date")

        except Exception as e:
            logger.warning("Error hitos: %s", e)
            ui.label("No disponible").classes("unavailable-text")


# ── SECCIÓN 7 — DIRECTIVO: grupos que requieren atención ──────────────────────

def _seccion_grupos_atencion(ctx: SessionContext, config) -> None:
    """Ranking de grupos con más estudiantes en riesgo (solo directivo).
    Cada fila navega al tablero estadístico. Solo lectura."""
    with ui.element("div").classes("panel-card"):
        _panel_titulo(Icons.ALERTS, "Grupos que requieren atención", "var(--color-error)")

        try:
            anio_id = config.id if config else None
            if not (ctx and ctx.periodo_id):
                ui.label("Sin periodo activo").classes("empty-state")
                return

            mi = Container.estadisticos_service().metricas_institucionales(
                ctx.periodo_id, anio_id
            )
            en_riesgo = sorted(
                [g for g in mi.grupos if g.get("en_riesgo", 0) > 0],
                key=lambda g: g["en_riesgo"],
                reverse=True,
            )[:5]

            if not en_riesgo:
                with ui.element("div").classes("flex-col items-center"):
                    ThemeManager.icono("check_circle", size=36, color="var(--color-success)")
                    ui.label("Ningún grupo con estudiantes en riesgo").classes("success-empty-text")
                return

            for g in en_riesgo:
                n_riesgo  = g["en_riesgo"]
                clase_badge = _clase_dias_riesgo(n_riesgo)
                with ui.element("div").classes("hito-item quick-action-card").on(
                    "click", lambda gid=g["grupo_id"]: ui.navigate.to("/academico/tablero")
                ):
                    with ui.element("div").classes(f"hito-dias-badge {clase_badge}"):
                        ui.label(str(n_riesgo))
                    with ui.element("div").classes("hito-text-col"):
                        ui.label(f"Grupo {g['codigo']}").classes("hito-desc")
                        ui.label(
                            f"Promedio {g['promedio']:.1f} · {g['total']} estudiantes"
                        ).classes("hito-date")

        except Exception as e:
            logger.warning("Error grupos en atención: %s", e)
            ui.label("No disponible").classes("unavailable-text")


def _clase_dias_riesgo(n: int) -> str:
    """Reusa los colores de badge de hitos según severidad del conteo en riesgo."""
    if n >= 5:
        return "hito-dias-danger"
    if n >= 2:
        return "hito-dias-warning"
    return "hito-dias-ok"


# ── SECCIÓN 8 — DIRECTIVO: pendientes institucionales ─────────────────────────

def _seccion_pendientes_institucionales(ctx: SessionContext, config) -> None:
    """Resumen institucional de pendientes (solo directivo): estado de cierres
    del periodo y habilitaciones pendientes. Cada item enlaza a su módulo.
    Solo lectura."""
    with ui.element("div").classes("panel-card"):
        _panel_titulo(Icons.CLOSE_PERIOD, "Pendientes institucionales")

        try:
            if not (ctx and ctx.periodo_id):
                ui.label("Sin periodo activo").classes("empty-state")
                return

            cierres = Container.cierre_service().resumen_cierres_institucional(
                ctx.periodo_id
            )
            habs_pend = Container.habilitacion_service().contar_habilitaciones_pendientes(
                ctx.periodo_id
            )

            cerradas   = cierres.get("cerradas", 0)
            pendientes = cierres.get("pendientes", 0)
            total      = cierres.get("total", 0)

            if total == 0 and habs_pend == 0:
                with ui.element("div").classes("flex-col items-center"):
                    ThemeManager.icono("check_circle", size=36, color="var(--color-success)")
                    ui.label("Sin pendientes institucionales").classes("success-empty-text")
                return

            # Cierres del periodo
            clase_cierres = "hito-dias-ok" if pendientes == 0 else (
                "hito-dias-danger" if pendientes > cerradas else "hito-dias-warning"
            )
            with ui.element("div").classes("hito-item quick-action-card").on(
                "click", lambda: ui.navigate.to("/evaluacion/cierre-periodo")
            ):
                with ui.element("div").classes(f"hito-dias-badge {clase_cierres}"):
                    ui.label(str(pendientes))
                with ui.element("div").classes("hito-text-col"):
                    ui.label("Cierres de periodo pendientes").classes("hito-desc")
                    ui.label(
                        f"{cerradas} de {total} asignaciones cerradas"
                    ).classes("hito-date")

            # Habilitaciones pendientes
            clase_habs = "hito-dias-ok" if habs_pend == 0 else "hito-dias-warning"
            with ui.element("div").classes("hito-item quick-action-card").on(
                "click", lambda: ui.navigate.to("/evaluacion/habilitaciones")
            ):
                with ui.element("div").classes(f"hito-dias-badge {clase_habs}"):
                    ui.label(str(habs_pend))
                with ui.element("div").classes("hito-text-col"):
                    ui.label("Habilitaciones pendientes").classes("hito-desc")
                    ui.label("Programadas sin nota registrada").classes("hito-date")

        except Exception as e:
            logger.warning("Error pendientes institucionales: %s", e)
            ui.label("No disponible").classes("unavailable-text")


# ── SECCIÓN 9 — PROFESOR: tus pendientes (accionable) ─────────────────────────

def _seccion_pendientes_docente(ctx: SessionContext, config) -> None:
    """Pendientes accionables del profesor (filtrados por usuario_id): actividades
    sin calificar, asistencia de hoy sin registrar y alertas de sus estudiantes.
    Cada item enlaza a la pantalla que lo resuelve. Solo lectura."""
    with ui.element("div").classes("panel-card"):
        _panel_titulo("checklist", "Tus pendientes")

        try:
            anio_id = config.id if config else None
            if not (ctx and ctx.usuario_id and ctx.periodo_id):
                ui.label("Sin periodo activo").classes("empty-state")
                return

            p = Container.estadisticos_service().pendientes_docente(
                ctx.usuario_id, ctx.periodo_id, anio_id
            )

            if p.total_asignaciones == 0:
                ui.label("No tienes asignaciones en este periodo").classes("empty-state")
                return

            if not p.hay_pendientes:
                with ui.element("div").classes("flex-col items-center"):
                    ThemeManager.icono("check_circle", size=36, color="var(--color-success)")
                    ui.label("Estás al día").classes("success-empty-text")
                return

            # (conteo, label, sublabel, ruta, icono, color_icono)
            items = [
                (p.actividades_sin_calificar, "Actividades sin calificar",
                 "Publicadas sin notas", "/evaluacion/planilla",
                 Icons.GRADES, "var(--color-primary)"),
                (p.asignaciones_sin_asistencia, "Asistencia de hoy sin registrar",
                 "En tus asignaciones", "/asistencia",
                 Icons.ATTENDANCE, "var(--color-success)"),
                (p.alertas_estudiantes, "Alertas de tus estudiantes",
                 "Pendientes de revisar", "/alertas",
                 Icons.ALERTS, "var(--color-error)"),
            ]

            for conteo, label, sub, ruta, icono, color_icono in items:
                if conteo <= 0:
                    continue
                with ui.element("div").classes("hito-item quick-action-card").on(
                    "click", lambda r=ruta: ui.navigate.to(r)
                ):
                    with ui.element("div").classes("quick-action-icon").style(  # DYNAMIC: bg por item
                        "background:var(--color-surface-alt)"
                    ):
                        ThemeManager.icono(icono, size=20, color=color_icono)
                    with ui.element("div").classes("hito-text-col"):
                        ui.label(f"{conteo} · {label}").classes("hito-desc")
                        ui.label(sub).classes("hito-date")

        except Exception as e:
            logger.warning("Error pendientes docente: %s", e)
            ui.label("No disponible").classes("unavailable-text")


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD DE PLATAFORMA (ADMIN) — paso_21
# Solo la rama admin. NO toca profesor / director / coordinador.
#
# paso_38: el lanzador "Ver como…" se movió a la página de herramientas de admin
# (/diagnostico). El dashboard ya no expone esa tarjeta de acceso rápido.
# ══════════════════════════════════════════════════════════════════════════════


def _admin_stat_card(titulo: str, valor: str, icono: str, subtitulo: str,
                     variante: str) -> None:
    stat_card(titulo=titulo, valor=valor, icono=icono,
              subtitulo=subtitulo, variante=variante)


def _seccion_admin_saludo(ctx: SessionContext, config) -> None:
    inst = getattr(config, "nombre_institucion", "") if config else ""
    with ui.element("div").classes("greeting-hero w-full"):
        nombre_corto = ctx.usuario_nombre.split()[0] if ctx.usuario_nombre else ""
        ui.label(f"{_saludo_temporal()}, {nombre_corto}").classes("greeting-name")
        ui.label(
            "Panel de plataforma · auditoría, cuentas de usuario y uso del sistema"
        ).classes("greeting-desc")
        with ui.element("div").classes("greeting-meta"):
            ThemeManager.icono("shield_person", size=16, color="var(--color-primary)")
            ui.label(ctx.usuario_nombre).classes("greeting-user")
            ui.element("span").classes("greeting-dot")
            ui.label("Administrador de plataforma").classes("greeting-role")


def _seccion_admin_metricas(config) -> None:
    """Stat cards con datos REALES de uso/usuarios (servicios de solo lectura)."""
    resumen = None
    uso = None
    try:
        resumen = Container.usuario_service().resumen_por_rol()
    except Exception as e:
        logger.warning("Error resumen_por_rol: %s", e)
    try:
        uso = Container.auditoria_service().resumen_uso(7)
    except Exception as e:
        logger.warning("Error resumen_uso: %s", e)

    total_usuarios = str(resumen.total) if resumen else "—"
    sub_usuarios   = f"{resumen.activos} activos" if resumen else "sin datos"
    directores     = str(resumen.directores) if resumen else "—"
    logins_hoy     = str(uso.logins_hoy) if uso else "—"
    activos_7d     = str(uso.usuarios_activos) if uso else "—"
    denegados      = str(uso.accesos_denegados) if uso else "0"

    with ui.element("div").classes("stats-grid"):
        _admin_stat_card("Usuarios", total_usuarios, Icons.TEACHERS, sub_usuarios, "primary")
        _admin_stat_card("Directores", directores, Icons.PROFILE, "cuentas de dirección", "info")
        _admin_stat_card("Logins hoy", logins_hoy, "login", f"{activos_7d} activos (7 días)", "success")
        _admin_stat_card("Accesos denegados", denegados, Icons.ALERTS, "últimos 7 días", "warning")


def _seccion_admin_instituciones(config) -> None:
    """
    Uso por institución. Hoy single-tenant (una fila = config activa), pero la
    presentación es una lista para que añadir tenants sea natural más adelante.
    """
    with ui.element("div").classes("panel-card"):
        _panel_titulo("apartment", "Uso por institución")

        # Multi-tenant ready: lista de instituciones. Hoy: 0 o 1 (config activa).
        instituciones = []
        if config is not None:
            instituciones.append(config)

        if not instituciones:
            ui.label("Sin institución configurada").classes("text-empty")
            ui.label("Configura un año lectivo activo").classes("text-hint")
            return

        try:
            uso = Container.auditoria_service().resumen_uso(7)
        except Exception:
            uso = None

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes("flex gap-4 p-2 font-semibold text-sm border-b"):
                ui.label("Institución").classes("flex-1")
                ui.label("Sesiones (7d)").classes("w-32 text-right")
                ui.label("Activos (7d)").classes("w-32 text-right")
            for inst in instituciones:
                nombre = getattr(inst, "nombre_institucion", None) or "Institución"
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    ui.label(str(nombre)).classes("flex-1")
                    ui.label(str(uso.sesiones_periodo) if uso else "—").classes("w-32 text-right")
                    ui.label(str(uso.usuarios_activos) if uso else "—").classes("w-32 text-right")


def _seccion_admin_accesos() -> None:
    """Accesos rápidos VÁLIDOS para admin (sin enlaces rotos)."""
    with ui.element("div").classes("panel-card"):
        _panel_titulo("bolt", "Accesos rápidos")
        with ui.grid(columns=2).classes("w-full gap-3"):
            # Auditoría
            with ui.element("div").classes("quick-action-card").on(
                "click", lambda: ui.navigate.to("/admin/auditoria")
            ):
                with ui.element("div").classes("quick-action-icon").style(  # DYNAMIC: bg por acción
                    "background:var(--color-primary-lighter)"
                ):
                    ThemeManager.icono("history", size=22, color="var(--color-primary)")
                with ui.element("div").classes("action-text-col"):
                    ui.label("Auditoría").classes("action-label")
                    ui.label("Eventos de sesión y cambios").classes("action-desc")
            # Usuarios
            with ui.element("div").classes("quick-action-card").on(
                "click", lambda: ui.navigate.to("/admin/usuarios")
            ):
                with ui.element("div").classes("quick-action-icon").style(  # DYNAMIC: bg por acción
                    "background:var(--color-success-light)"
                ):
                    ThemeManager.icono(Icons.TEACHERS, size=22, color="var(--color-success)")
                with ui.element("div").classes("action-text-col"):
                    ui.label("Usuarios").classes("action-label")
                    ui.label("Cuentas y roles").classes("action-desc")


def _dashboard_admin(ctx: SessionContext, config) -> None:
    """Cuerpo del dashboard de plataforma (admin)."""
    with ui.element("div").classes("page-stack"):
        _seccion_admin_saludo(ctx, config)
        _seccion_admin_metricas(config)
        with ui.element("div").classes("page-body"):
            with ui.element("div").classes("page-col-main"):
                _seccion_admin_instituciones(config)
                _seccion_actividad_reciente(ctx)
            with ui.element("div").classes("page-col-side"):
                _seccion_admin_accesos()


# ── FUNCIÓN PRINCIPAL ─────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def inicio_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Dashboard: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    config = None
    try:
        config = Container.configuracion_service().get_activa(ctx.institucion_id)
    except Exception as e:
        logger.warning("Sin configuración activa: %s", e)

    # ── Rama admin: dashboard de plataforma (paso_21) ─────────────────────────
    # Solo el admin real (no impersonando). Durante "Ver como", ctx.usuario_rol
    # es el del usuario objetivo, por lo que cae en las ramas de abajo.
    if ctx.usuario_rol == "admin":
        def contenido_admin() -> None:
            _dashboard_admin(ctx, config)

        app_layout(
            ctx, contenido_admin,
            page_titulo="Plataforma",
            page_subtitulo="Auditoría y gestión de cuentas",
            page_icono="shield_person",
        )
        return

    es_directivo = ctx.usuario_rol in _ROLES_DIRECTIVO

    @ui.refreshable
    def stats_refreshable() -> None:
        # desde_storage() crea un snapshot DESPUÉS de que ctx.guardar() ya
        # completó (NiceGUI serializa eventos en un hilo). Siempre lee datos frescos.
        ctx_fresco = SessionContext.desde_storage()
        if es_directivo:
            _seccion_stats_institucional(ctx_fresco, config)
        else:
            _seccion_stats(ctx_fresco, config)

    @ui.refreshable
    def contexto_refreshable() -> None:
        """Secciones sensibles al periodo/grupo: institucionales (directivo)
        o pendientes del docente (profesor)."""
        ctx_fresco = SessionContext.desde_storage()
        if es_directivo:
            _seccion_grupos_atencion(ctx_fresco, config)
            _seccion_pendientes_institucionales(ctx_fresco, config)
        else:
            _seccion_pendientes_docente(ctx_fresco, config)

    def on_context_change() -> None:
        stats_refreshable.refresh()
        contexto_refreshable.refresh()

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            _seccion_saludo(ctx, config)

            stats_refreshable()

            with ui.element("div").classes("page-body"):
                with ui.element("div").classes("page-col-main"):
                    _seccion_acciones_rapidas(ctx.usuario_rol)
                    contexto_refreshable()
                    _seccion_actividad_reciente(ctx)
                with ui.element("div").classes("page-col-side"):
                    _seccion_alertas(ctx)
                    _seccion_hitos(config)

    app_layout(
        ctx, contenido,
        page_titulo="Dashboard",
        on_context_change=on_context_change,
    )


__all__ = ["inicio_page"]
