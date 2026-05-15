"""
src/interface/pages/inicio.py
==============================
Dashboard principal de ZECI Manager v2.0.

Diseño: Andes Minimal v2
Servicios: EstadisticosService, AlertaService,
           PeriodoService, ConfiguracionService
Contexto: SessionContext (desde app.storage.user)
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.tokens import Icons
from src.interface.design.theme import ThemeManager
from src.interface.design.components.stat_card import stat_card
from src.interface.design.components.status_badge import status_badge
from src.interface.design.layout import app_layout

logger = logging.getLogger("INICIO")

# ──────────────────────────────────────────────────────────────
# CSS adicional — específico de esta página
# ──────────────────────────────────────────────────────────────

INICIO_CSS = """
.period-bar-track {
  width: 100%;
  height: 8px;
  background: var(--color-divider);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.period-bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg,
    var(--color-primary) 0%,
    var(--color-primary-light) 100%);
  transition: width 0.8s ease;
}
.period-bar-fill.warning { background: var(--color-warning); }
.period-bar-fill.danger  { background: var(--color-error); }

.quick-action-card {
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
  background: var(--color-surface);
  cursor: pointer;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  gap: var(--space-md);
}
.quick-action-card:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-lighter);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.quick-action-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.activity-feed-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--color-divider);
}
.activity-feed-item:last-child { border-bottom: none; }
.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  margin-top: 6px;
  flex-shrink: 0;
}

.hito-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--color-divider);
}
.hito-item:last-child { border-bottom: none; }
.hito-dias-badge {
  min-width: 52px;
  text-align: center;
  padding: 4px 8px;
  border-radius: var(--radius-md);
  font-size: 11px;
  font-weight: 700;
}
.hito-dias-ok      { background: var(--color-success-light); color: var(--color-success); }
.hito-dias-warning { background: var(--color-warning-light); color: var(--color-warning); }
.hito-dias-danger  { background: var(--color-error-light);   color: var(--color-error);   }

.alerta-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-xs);
}
.alerta-critica     { background: var(--color-error-light); }
.alerta-advertencia { background: var(--color-warning-light); }
.alerta-info        { background: var(--color-info-light); }

.greeting-hero {
  background: linear-gradient(135deg,
    var(--color-primary) 0%,
    var(--color-primary-dark) 100%);
  border-radius: var(--radius-xl);
  padding: var(--space-xl);
  color: white;
  position: relative;
  overflow: hidden;
}
.greeting-hero::after {
  content: '';
  position: absolute;
  right: -40px;
  top: -40px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
}
"""

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _saludo_temporal() -> str:
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Buenos días"
    elif 12 <= hora < 14:
        return "Buen mediodía"
    elif 14 <= hora < 20:
        return "Buenas tardes"
    else:
        return "Buenas noches"


def _tiempo_relativo(ts) -> str:
    try:
        if ts is None:
            return "—"
        if isinstance(ts, str):
            if "T" in ts:
                fecha = datetime.fromisoformat(ts)
            else:
                fecha = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
        else:
            fecha = ts
        delta = datetime.now() - fecha
        if delta.days > 0:
            return f"Hace {delta.days}d"
        horas = delta.seconds // 3600
        if horas > 0:
            return f"Hace {horas}h"
        minutos = delta.seconds // 60
        return f"Hace {minutos}m" if minutos > 0 else "Ahora"
    except Exception:
        return "—"


def _clase_dias(dias: int) -> str:
    if dias > 14:
        return "hito-dias-ok"
    elif dias > 5:
        return "hito-dias-warning"
    else:
        return "hito-dias-danger"


def _clase_periodo_bar(progreso: float) -> str:
    if progreso < 60:
        return ""
    elif progreso < 85:
        return "warning"
    else:
        return "danger"


def _panel_card_style() -> str:
    return (
        "background:var(--color-surface);"
        "border:1px solid var(--color-divider);"
        "border-radius:var(--radius-xl);"
        "padding:var(--space-lg);"
    )


def _panel_titulo(icono: str, texto: str, color: str = "var(--color-primary)") -> None:
    with ui.row().classes("items-center gap-2").style("margin-bottom:var(--space-md)"):
        ThemeManager.icono(icono, size=20, color=color)
        ui.label(texto).style(
            "font-size:15px;font-weight:600;color:var(--color-text-primary)"
        )


# ──────────────────────────────────────────────────────────────
# SECCIÓN 1 — Saludo + Estado del periodo
# ──────────────────────────────────────────────────────────────

def _seccion_saludo(ctx: SessionContext, config) -> None:
    with ui.row().classes("w-full gap-4 items-stretch"):

        # Hero de saludo
        with ui.element("div").classes("greeting-hero flex-1"):
            _MENSAJES_ROL = {
                "profesor":    "Gestiona notas, asistencia y seguimiento de tus estudiantes",
                "director":    "Monitorea el desempeño académico de tu institución",
                "coordinador": "Supervisa la convivencia y el seguimiento académico",
                "admin":       "Administra la configuración y los usuarios del sistema",
            }
            _LABELS_ROL = {
                "profesor":    "Docente",
                "director":    "Director",
                "coordinador": "Coordinador",
                "admin":       "Administrador",
            }
            nombre_corto = ctx.usuario_nombre.split()[0] if ctx.usuario_nombre else ""

            ui.label(f"{_saludo_temporal()}, {nombre_corto}").style(
                "font-size:26px;font-weight:700;color:white;margin-bottom:8px;"
                "position:relative;z-index:1"
            )
            ui.label(_MENSAJES_ROL.get(ctx.usuario_rol, "Bienvenido al sistema")).style(
                "color:rgba(255,255,255,0.80);font-size:14px;position:relative;z-index:1"
            )
            with ui.row().classes("items-center gap-2").style(
                "margin-top:var(--space-md);position:relative;z-index:1"
            ):
                ThemeManager.icono(Icons.PROFILE, size=16, color="rgba(255,255,255,0.70)")
                ui.label(ctx.usuario_nombre).style(
                    "color:rgba(255,255,255,0.90);font-size:13px;font-weight:500"
                )
                ui.element("span").style(
                    "width:4px;height:4px;border-radius:50%;"
                    "background:rgba(255,255,255,0.4);display:inline-block"
                )
                ui.label(_LABELS_ROL.get(ctx.usuario_rol, ctx.usuario_rol.capitalize())).style(
                    "color:rgba(255,255,255,0.70);font-size:12px"
                )

        # Panel de estado del periodo
        with ui.element("div").style(
            _panel_card_style()
            + "min-width:280px;max-width:340px;"
            "display:flex;flex-direction:column;gap:var(--space-sm);"
        ):
            ui.label("Periodo activo").style(
                "font-size:11px;font-weight:600;text-transform:uppercase;"
                "letter-spacing:0.5px;color:var(--color-text-secondary)"
            )

            try:
                if config is None:
                    raise ValueError("sin config")

                svc_periodo = Container.periodo_service()
                periodo = svc_periodo.get_activo(config.id)

                ui.label(periodo.nombre).style(
                    "font-size:18px;font-weight:700;color:var(--color-text-primary)"
                )

                hoy = date.today()
                if periodo.fecha_inicio and periodo.fecha_fin:
                    total_dias = (periodo.fecha_fin - periodo.fecha_inicio).days
                    dias_pasados = (hoy - periodo.fecha_inicio).days
                    dias_restantes = (periodo.fecha_fin - hoy).days
                    progreso = min(100, max(0, (
                        dias_pasados / total_dias * 100
                    ) if total_dias > 0 else 0))
                    clase_bar = _clase_periodo_bar(progreso)

                    with ui.column().classes("gap-1 w-full"):
                        with ui.row().classes("justify-between"):
                            ui.label(periodo.fecha_inicio.strftime("%d %b")).style(
                                "font-size:11px;color:var(--color-text-secondary)"
                            )
                            ui.label(periodo.fecha_fin.strftime("%d %b")).style(
                                "font-size:11px;color:var(--color-text-secondary)"
                            )
                        with ui.element("div").classes("period-bar-track"):
                            ui.element("div").classes(
                                f"period-bar-fill {clase_bar}"
                            ).style(f"width:{progreso:.0f}%")

                        color_dias = (
                            "color:var(--color-error)" if dias_restantes < 7
                            else "color:var(--color-warning)" if dias_restantes < 15
                            else "color:var(--color-text-secondary)"
                        )
                        ui.label(
                            f"{max(0, dias_restantes)} días restantes · {progreso:.0f}% transcurrido"
                        ).style(f"font-size:12px;{color_dias}")

                status_badge("Cerrado", "neutral") if periodo.cerrado else status_badge("Activo", "success")

            except Exception:
                ui.label("Sin periodo activo").style(
                    "color:var(--color-text-secondary);font-size:14px"
                )
                ui.label("Configura un periodo en el módulo de administración").style(
                    "font-size:12px;color:var(--color-text-disabled)"
                )


# ──────────────────────────────────────────────────────────────
# SECCIÓN 2 — Stat cards con métricas reales
# ──────────────────────────────────────────────────────────────

def _seccion_stats(ctx: SessionContext, config) -> None:
    _STAT_CONFIGS = {
        "profesor": [
            ("Estudiantes",   Icons.STUDENTS,    "primary"),
            ("% Asistencia",  Icons.ATTENDANCE,  "success"),
            ("En riesgo",     Icons.ALERTS,      "danger"),
            ("Alertas act.",  Icons.ALERTS,      "warning"),
        ],
        "director": [
            ("Estudiantes",   Icons.STUDENTS,    "primary"),
            ("Promedio gral.",Icons.GRADES,      "info"),
            ("% Asistencia",  Icons.ATTENDANCE,  "success"),
            ("Alertas act.",  Icons.ALERTS,      "danger"),
        ],
        "coordinador": [
            ("Estudiantes",   Icons.STUDENTS,    "primary"),
            ("% Asistencia",  Icons.ATTENDANCE,  "success"),
            ("En riesgo",     Icons.ALERTS,      "danger"),
            ("Alertas act.",  Icons.ALERTS,      "warning"),
        ],
        "admin": [
            ("Usuarios",  Icons.TEACHERS,  "primary"),
            ("Grupos",    Icons.GROUPS,    "info"),
            ("Periodos",  Icons.PERIODS,   "success"),
            ("Alertas",   Icons.ALERTS,   "warning"),
        ],
    }
    rol = ctx.usuario_rol
    configs_stat = _STAT_CONFIGS.get(rol, _STAT_CONFIGS["admin"])
    valores    = ["—", "—", "—", "—"]
    subtitulos = ["", "", "", ""]

    try:
        if rol in ("profesor", "director", "coordinador"):
            if ctx.grupo_id and ctx.periodo_id:
                svc_est = Container.estadisticos_service()
                anio_id = config.id if config else None
                m = svc_est.metricas_dashboard(ctx.grupo_id, ctx.periodo_id, anio_id)
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
        logger.warning("Error cargando métricas: %s", e)

    with ui.grid(columns=4).classes("w-full gap-4"):
        for i, (titulo_stat, icono_stat, variante_stat) in enumerate(configs_stat):
            stat_card(
                titulo=titulo_stat,
                valor=valores[i],
                icono=icono_stat,
                subtitulo=subtitulos[i],
                variante=variante_stat,
            )


# ──────────────────────────────────────────────────────────────
# SECCIÓN 3 — Acciones rápidas por rol
# ──────────────────────────────────────────────────────────────

def _seccion_acciones_rapidas(rol: str) -> None:
    _ACCIONES = {
        "profesor": [
            (Icons.ATTENDANCE, "Registrar Asistencia", "Control diario del grupo",
             "/asistencia", "var(--color-success-light)", "var(--color-success)"),
            (Icons.GRADES, "Planilla de Notas", "Calificar actividades",
             "/evaluacion/planilla", "var(--color-primary-lighter)", "var(--color-primary)"),
            (Icons.BEHAVIOR, "Convivencia", "Observaciones y registros",
             "/convivencia", "var(--color-warning-light)", "var(--color-warning)"),
            (Icons.REPORTS, "Mis Informes", "Exportar notas y asistencia",
             "/informes", "var(--color-info-light)", "var(--color-info)"),
        ],
        "director": [
            (Icons.REPORTS, "Informes Institucionales", "Consolidados por grupo",
             "/informes", "var(--color-primary-lighter)", "var(--color-primary)"),
            (Icons.CLOSE_PERIOD, "Cierre de Periodo", "Gestionar cierres académicos",
             "/evaluacion/cierre", "var(--color-warning-light)", "var(--color-warning)"),
            (Icons.TEACHERS, "Docentes", "Carga académica y horarios",
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
            (Icons.TEACHERS, "Usuarios y Roles", "Docentes y administradores",
             "/admin/usuarios", "var(--color-success-light)", "var(--color-success)"),
            (Icons.GROUPS, "Grupos y Asignaturas", "Estructura académica",
             "/admin/grupos", "var(--color-info-light)", "var(--color-info)"),
            (Icons.SCHEDULE, "Asignaciones", "Docente · Grupo · Materia",
             "/admin/asignaciones", "var(--color-warning-light)", "var(--color-warning)"),
        ],
    }
    acciones = _ACCIONES.get(rol, _ACCIONES["admin"])

    with ui.element("div").style(_panel_card_style()):
        _panel_titulo("bolt", "Accesos rápidos")
        with ui.grid(columns=2).classes("w-full gap-3"):
            for icono, label, desc, ruta, bg, color in acciones:
                with ui.element("div").classes("quick-action-card").on(
                    "click", lambda r=ruta: ui.navigate.to(r)
                ):
                    with ui.element("div").classes("quick-action-icon").style(
                        f"background:{bg}"
                    ):
                        ThemeManager.icono(icono, size=22, color=color)
                    with ui.column().style("gap:2px;min-width:0"):
                        ui.label(label).style(
                            "font-size:13px;font-weight:600;"
                            "color:var(--color-text-primary)"
                        )
                        ui.label(desc).style(
                            "font-size:12px;color:var(--color-text-secondary);"
                            "white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
                        )


# ──────────────────────────────────────────────────────────────
# SECCIÓN 4 — Feed de actividad reciente
# ──────────────────────────────────────────────────────────────

def _seccion_actividad_reciente(ctx: SessionContext) -> None:
    with ui.element("div").style(_panel_card_style()):
        _panel_titulo("history", "Actividad reciente")

        try:
            from src.domain.models.auditoria import FiltroAuditoriaDTO
            filtro = FiltroAuditoriaDTO(
                usuario_id=ctx.usuario_id if ctx.usuario_rol == "profesor" else None,
                pagina=1,
                por_pagina=6,
            )
            cambios = Container.auditoria_service().listar_cambios(filtro)

            if not cambios:
                ui.label("Sin actividad reciente").style(
                    "color:var(--color-text-disabled);font-size:13px;"
                    "text-align:center;padding:24px 0"
                )
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
                    with ui.column().style("gap:2px;flex:1;min-width:0"):
                        ui.label(etiqueta).style(
                            "font-size:13px;font-weight:500;"
                            "color:var(--color-text-primary)"
                        )
                        ui.label(tabla).style(
                            "font-size:12px;color:var(--color-text-secondary)"
                        )
                    ui.label(tiempo).style(
                        "font-size:11px;color:var(--color-text-disabled);flex-shrink:0"
                    )

        except Exception as e:
            logger.warning("Error actividad reciente: %s", e)
            ui.label("No disponible").style(
                "color:var(--color-text-disabled);font-size:13px"
            )


# ──────────────────────────────────────────────────────────────
# SECCIÓN 5 — Alertas pendientes
# ──────────────────────────────────────────────────────────────

def _seccion_alertas(ctx: SessionContext) -> None:
    with ui.element("div").style(_panel_card_style()):
        _panel_titulo(Icons.ALERTS, "Alertas pendientes", "var(--color-error)")

        try:
            from src.domain.models.alerta import FiltroAlertasDTO
            svc_alerta = Container.alerta_service()
            alertas = svc_alerta.listar_alertas(
                FiltroAlertasDTO(solo_pendientes=True, por_pagina=10)
            )

            if not alertas:
                with ui.column().classes("items-center").style("padding:16px 0"):
                    ThemeManager.icono("check_circle", size=36, color="var(--color-success)")
                    ui.label("Sin alertas pendientes").style(
                        "font-size:13px;color:var(--color-success);"
                        "font-weight:500;margin-top:8px"
                    )
                return

            criticas     = [a for a in alertas if str(getattr(a, "nivel", "")).lower() == "critica"]
            advertencias = [a for a in alertas if str(getattr(a, "nivel", "")).lower() == "advertencia"]

            if criticas:
                with ui.element("div").style(
                    "background:var(--color-error-light);border-radius:var(--radius-md);"
                    "padding:10px 12px;margin-bottom:8px"
                ):
                    with ui.row().classes("items-center gap-2"):
                        ThemeManager.icono("error", size=18, color="var(--color-error)")
                        ui.label(f"{len(criticas)} alerta(s) crítica(s)").style(
                            "font-size:13px;font-weight:600;color:var(--color-error)"
                        )

            if advertencias:
                with ui.element("div").style(
                    "background:var(--color-warning-light);border-radius:var(--radius-md);"
                    "padding:10px 12px;margin-bottom:8px"
                ):
                    with ui.row().classes("items-center gap-2"):
                        ThemeManager.icono("warning", size=18, color="var(--color-warning)")
                        ui.label(f"{len(advertencias)} advertencia(s)").style(
                            "font-size:13px;font-weight:600;color:var(--color-warning)"
                        )

            for alerta in alertas[:5]:
                nivel = str(getattr(alerta, "nivel", "info")).lower()
                tipo  = str(getattr(alerta, "tipo_alerta", "alerta")).replace("_", " ").capitalize()

                if nivel == "critica":
                    clase, color, icono_n = "alerta-critica",     "var(--color-error)",   "error"
                elif nivel == "advertencia":
                    clase, color, icono_n = "alerta-advertencia", "var(--color-warning)", "warning"
                else:
                    clase, color, icono_n = "alerta-info",        "var(--color-info)",    "info"

                with ui.element("div").classes(f"alerta-item {clase}"):
                    ThemeManager.icono(icono_n, size=16, color=color)
                    ui.label(tipo).style(
                        f"font-size:12px;font-weight:500;color:{color}"
                    )

            if len(alertas) > 5:
                ui.label(f"+ {len(alertas) - 5} más").style(
                    "font-size:12px;color:var(--color-text-secondary);"
                    "text-align:right;margin-top:8px"
                )

        except Exception as e:
            logger.warning("Error cargando alertas: %s", e)
            ui.label("No disponible").style(
                "font-size:12px;color:var(--color-text-disabled)"
            )


# ──────────────────────────────────────────────────────────────
# SECCIÓN 6 — Hitos próximos del periodo
# ──────────────────────────────────────────────────────────────

def _seccion_hitos(config) -> None:
    with ui.element("div").style(_panel_card_style()):
        _panel_titulo(Icons.PERIODS, "Próximas fechas")

        try:
            if config is None:
                raise ValueError("sin config")

            hitos = Container.periodo_service().listar_hitos_proximos(
                anio_id=config.id, dias=30
            )

            if not hitos:
                ui.label("Sin hitos en los próximos 30 días").style(
                    "font-size:12px;color:var(--color-text-disabled);"
                    "text-align:center;padding:16px 0"
                )
                return

            hoy = date.today()
            for hito in hitos[:6]:
                fecha_limite = getattr(hito, "fecha_limite", None)
                descripcion  = getattr(hito, "descripcion", "Hito")

                if fecha_limite:
                    dias = (fecha_limite - hoy).days
                    clase_dias = _clase_dias(dias)
                    dias_txt   = f"{dias}d" if dias > 0 else "HOY"
                else:
                    dias_txt   = "—"
                    clase_dias = "hito-dias-ok"

                with ui.element("div").classes("hito-item"):
                    with ui.element("div").classes(f"hito-dias-badge {clase_dias}"):
                        ui.label(dias_txt).style("font-size:11px;font-weight:700")
                    with ui.column().style("gap:0;flex:1;min-width:0"):
                        ui.label(str(descripcion)[:45]).style(
                            "font-size:13px;font-weight:500;"
                            "color:var(--color-text-primary)"
                        )
                        if fecha_limite:
                            ui.label(fecha_limite.strftime("%d %b %Y")).style(
                                "font-size:11px;color:var(--color-text-secondary)"
                            )

        except Exception as e:
            logger.warning("Error cargando hitos: %s", e)
            ui.label("No disponible").style(
                "font-size:12px;color:var(--color-text-disabled)"
            )


# ──────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────────────────────

def inicio_page() -> None:
    """
    Dashboard principal. Registrada en main.py como @ui.page("/inicio").
    Usa app_layout() para sidebar + topbar.
    """
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Dashboard cargado para %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    ui.add_head_html(f"<style>{INICIO_CSS}</style>")

    config = None
    try:
        config = Container.configuracion_service().get_activa()
    except Exception as e:
        logger.warning("Sin configuración activa: %s", e)

    @ui.refreshable
    def stats_refreshable() -> None:
        # desde_storage() crea un snapshot del storage en este instante.
        # Se llama DESPUÉS de ctx.guardar() (en el callback on_context_change),
        # lo que es seguro porque NiceGUI serializa los eventos en un solo hilo.
        ctx_actual = SessionContext.desde_storage()
        _seccion_stats(ctx_actual, config)

    def on_context_change() -> None:
        # guardar() ya completó antes de que este callback se ejecute,
        # por lo que desde_storage() dentro de stats_refreshable leerá
        # los valores actualizados.
        stats_refreshable.refresh()

    def contenido() -> None:
        with ui.column().classes("w-full gap-6"):
            _seccion_saludo(ctx, config)
            stats_refreshable()

            with ui.row().classes("w-full gap-4 items-start"):
                with ui.column().style("flex:3;gap:var(--space-md);min-width:0"):
                    _seccion_acciones_rapidas(ctx.usuario_rol)
                    _seccion_actividad_reciente(ctx)

                with ui.column().style("flex:2;gap:var(--space-md);min-width:0"):
                    _seccion_alertas(ctx)
                    _seccion_hitos(config)

    app_layout(
        titulo_pagina="Dashboard",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/inicio",
        contenido=contenido,
        ctx=ctx,
        on_context_change=on_context_change,
    )


__all__ = ["inicio_page"]
