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
from src.interface.design.components.context_selector import context_chip
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
                ThemeManager.icono(Icons.PROFILE, size=16, color="rgba(255,255,255,0.70)")
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

def _stat_card(
    titulo: str,
    valor: str,
    icono: str,
    subtitulo: str = "",
    variante: str = "primary",
) -> None:
    _icon_colors = {
        "primary": "var(--color-primary)",
        "success": "var(--color-success)",
        "warning": "var(--color-warning)",
        "error":   "var(--color-error)",
        "info":    "var(--color-info)",
    }
    with ui.element("div").classes(f"stat-card-wrapper {variante}"):
        with ui.element("div").classes("stat-card-icon-wrap"):
            ThemeManager.icono(
                icono, size=22,
                color=_icon_colors.get(variante, "var(--color-primary)"),
            )
        ui.label(titulo).classes("stat-card-label")
        ui.label(str(valor)).classes("stat-card-value")
        if subtitulo:
            ui.label(subtitulo).classes("stat-card-subtitle")


def _seccion_stats(ctx: SessionContext, config) -> None:
    _CONFIGS = {
        "profesor":    [
            ("Estudiantes",   Icons.STUDENTS,   "primary"),
            ("% Asistencia",  Icons.ATTENDANCE, "success"),
            ("En riesgo",     Icons.ALERTS,     "error"),
            ("Alertas act.",  Icons.ALERTS,     "warning"),
        ],
        "director":    [
            ("Estudiantes",    Icons.STUDENTS,   "primary"),
            ("Promedio gral.", Icons.GRADES,     "info"),
            ("% Asistencia",  Icons.ATTENDANCE, "success"),
            ("Alertas act.",  Icons.ALERTS,     "error"),
        ],
        "coordinador": [
            ("Estudiantes",   Icons.STUDENTS,   "primary"),
            ("% Asistencia",  Icons.ATTENDANCE, "success"),
            ("En riesgo",     Icons.ALERTS,     "error"),
            ("Alertas act.",  Icons.ALERTS,     "warning"),
        ],
        "admin":       [
            ("Usuarios",  Icons.TEACHERS, "primary"),
            ("Grupos",    Icons.GROUPS,   "info"),
            ("Periodos",  Icons.PERIODS,  "success"),
            ("Alertas",   Icons.ALERTS,  "warning"),
        ],
    }
    rol     = ctx.usuario_rol if ctx else "admin"
    configs = _CONFIGS.get(rol, _CONFIGS["admin"])
    valores    = ["—", "—", "—", "—"]
    subtitulos = [""] * 4

    try:
        if ctx and rol in ("profesor", "director", "coordinador"):
            if ctx.grupo_id and ctx.periodo_id:
                anio_id = config.id if config else None
                m = Container.estadisticos_service().metricas_dashboard(
                    ctx.grupo_id, ctx.periodo_id, anio_id
                )
                if rol == "profesor":
                    valores    = [str(m.total_estudiantes), f"{m.porcentaje_asistencia:.1f}%",
                                  str(m.estudiantes_en_riesgo), str(m.alertas_pendientes)]
                    subtitulos = ["en tu grupo", "este periodo", "bajo el mínimo", "pendientes"]
                else:
                    valores    = [str(m.total_estudiantes), f"{m.promedio_general:.1f}",
                                  f"{m.porcentaje_asistencia:.1f}%", str(m.alertas_pendientes)]
                    subtitulos = ["matriculados", "promedio general", "asistencia", "sin resolver"]
            else:
                subtitulos = ["Selecciona un grupo"] * 4
    except Exception as e:
        logger.warning("Error métricas: %s", e)

    with ui.element("div").classes("stats-grid"):
        for i, (titulo_s, icono_s, variante_s) in enumerate(configs):
            _stat_card(
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
        "admin": [
            (Icons.CONFIG, "Configuración SIE", "Año, niveles, criterios",
             "/admin/configuracion", "var(--color-primary-lighter)", "var(--color-primary)"),
            (Icons.TEACHERS, "Usuarios y Roles", "Docentes y admins",
             "/admin/usuarios", "var(--color-success-light)", "var(--color-success)"),
            (Icons.GROUPS, "Grupos y Asignaturas", "Estructura académica",
             "/admin/grupos", "var(--color-info-light)", "var(--color-info)"),
            (Icons.SCHEDULE, "Asignaciones", "Docente · Grupo · Materia",
             "/admin/asignaciones", "var(--color-warning-light)", "var(--color-warning)"),
        ],
    }
    acciones = _ACCIONES.get(rol, _ACCIONES["admin"])

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


# ── FUNCIÓN PRINCIPAL ─────────────────────────────────────────────────────────

@ui.page("/inicio")
def inicio_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Dashboard: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    config = None
    try:
        config = Container.configuracion_service().get_activa()
    except Exception as e:
        logger.warning("Sin configuración activa: %s", e)

    @ui.refreshable
    def stats_refreshable() -> None:
        # desde_storage() crea un snapshot DESPUÉS de que ctx.guardar() ya
        # completó (NiceGUI serializa eventos en un hilo). Siempre lee datos frescos.
        _seccion_stats(SessionContext.desde_storage(), config)

    def on_context_change() -> None:
        stats_refreshable.refresh()

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            _seccion_saludo(ctx, config)

            # El chip de contexto se muestra en el topbar (layout.py).
            # Se renderiza aquí también como fallback inline si el rol
            # requiere contexto académico y layout.py no lo inyecta aún.
            if ctx.usuario_rol in ("profesor", "director", "coordinador"):
                context_chip(
                    ctx=ctx,
                    on_change=on_context_change,
                    mostrar_asignatura=(ctx.usuario_rol == "profesor"),
                )

            stats_refreshable()

            with ui.element("div").classes("page-body"):
                with ui.element("div").classes("page-col-main"):
                    _seccion_acciones_rapidas(ctx.usuario_rol)
                    _seccion_actividad_reciente(ctx)
                with ui.element("div").classes("page-col-side"):
                    _seccion_alertas(ctx)
                    _seccion_hitos(config)

    app_layout(
        titulo_pagina="Dashboard",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/inicio",
        contenido=contenido,
    )


__all__ = ["inicio_page"]
