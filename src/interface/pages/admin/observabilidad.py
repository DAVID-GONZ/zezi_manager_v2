"""
src/interface/pages/admin/observabilidad.py
============================================
Panel de observabilidad de plataforma (obs_13).

Ruta: /admin/observabilidad
Acceso: admin (Rol.ADMIN).

Cuatro secciones fail-open (R13):
  1. Salud del sistema — integridad, versión, uptime, tamaño de BD, último backup.
  2. Log de seguridad — últimas N entradas con filtros por tipo de evento.
  3. Alertas de IP — IPs con fallos activos y opción de limpiar (R10, R11).
  4. Uso diario — serie de logins y denegados por día (R12).

Regla de capas:
  - Solo usa Container y la capa de interfaz.
  - No importa src.infrastructure ni fetch_df/execute directamente.
  - Los cálculos viven en ObservabilidadService / dominio.

Limitación declarada (§6 del diseño):
  Las alertas de IP son del proceso actual. En despliegues multi-worker cada
  proceso tiene su propio dict _estados. La solución real es estado compartido
  (seguridad_web_05).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    data_table,
    empty_state,
    stats_grid,
    toast_error,
    toast_success,
)
from src.interface.design.components.mini_chart import mini_chart
from src.interface.design.components.stats_grid import StatItem
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.presenters.admin.observabilidad_presenter import ObservabilidadPresenter

logger = logging.getLogger("ADMIN.OBSERVABILIDAD")

_TIPOS_EVENTO_OPCIONES: dict[str | None, str] = {
    None: "Todos los eventos",
    "LOGIN_EXITOSO": "Login exitoso",
    "LOGIN_FALLIDO": "Login fallido",
    "LOGOUT": "Logout",
    "ACCESO_DENEGADO": "Acceso denegado",
    "VER_COMO_INICIO": "Ver como (inicio)",
    "VER_COMO_FIN": "Ver como (fin)",
    "ALERTA_IP": "Alerta IP",
}


# ── Helpers de formateo ────────────────────────────────────────────────────────

def _fmt_bytes(n: int) -> str:
    """Formatea bytes a unidad legible (KB, MB, GB)."""
    if n < 1024:
        return f"{n} B"
    elif n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    elif n < 1024 ** 3:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024 ** 3:.1f} GB"


def _fmt_uptime(segundos: float) -> str:
    """Formatea segundos a string legible (d h m s)."""
    td = timedelta(seconds=int(segundos))
    dias = td.days
    horas, resto = divmod(td.seconds, 3600)
    minutos, secs = divmod(resto, 60)
    partes = []
    if dias:
        partes.append(f"{dias}d")
    if horas:
        partes.append(f"{horas}h")
    if minutos:
        partes.append(f"{minutos}m")
    partes.append(f"{secs}s")
    return " ".join(partes)


def _fmt_restante(segundos: float) -> str:
    """Formatea segundos restantes a 'Nm Ns'."""
    minutos = int(segundos) // 60
    secs = int(segundos) % 60
    if minutos:
        return f"{minutos}m {secs}s"
    return f"{secs}s"


# ── Carga de datos (fail-open por bloque — R13) ────────────────────────────────

def _cargar_todo(presenter: ObservabilidadPresenter) -> None:
    """Carga los cuatro bloques de forma independiente (R13)."""
    svc = Container.observabilidad_service()

    # Bloque 1: Salud
    try:
        presenter.cargar_salud(svc.salud())
    except Exception as exc:
        logger.error("Error cargando salud: %s", exc)
        presenter.error_salud(str(exc))

    # Bloque 2: Eventos
    try:
        tipo = presenter.estado["filtro_tipo"]
        entradas = svc.eventos_seguridad(tipo_evento=tipo)
        disponible = svc.log_disponible()
        presenter.cargar_eventos(entradas, disponible)
    except Exception as exc:
        logger.error("Error cargando log de seguridad: %s", exc)
        presenter.error_eventos(str(exc))

    # Bloque 3: Alertas de IP
    try:
        presenter.cargar_alertas(svc.alertas_ip())
    except Exception as exc:
        logger.error("Error cargando alertas IP: %s", exc)
        presenter.error_alertas(str(exc))

    # Bloque 4: Uso diario
    try:
        presenter.cargar_uso(svc.uso_diario(dias=14))
    except Exception as exc:
        logger.error("Error cargando uso diario: %s", exc)
        presenter.error_uso(str(exc))


# ── Secciones de UI ────────────────────────────────────────────────────────────

def _seccion_salud(presenter: ObservabilidadPresenter) -> None:
    """Sección 1: estado de salud del sistema."""
    with ui.element("div").classes("page-section"):
        ui.label("Estado del sistema").classes("section-title")

        if presenter.estado["error_salud"]:
            empty_state(
                mensaje=f"Error al obtener el estado de salud: {presenter.estado['error_salud']}",
                icono="error",
            )
            return

        salud = presenter.estado["salud"]
        if salud is None:
            empty_state(mensaje="Cargando...", icono="hourglass_empty")
            return

        # Badge de integridad
        if salud.integra:
            with ui.element("div").classes("status-ok-banner"):
                ThemeManager.icono("check_circle", size=18, color="var(--color-success)")
                ui.label("Base de datos íntegra").classes("status-ok-text")
        else:
            with ui.element("div").classes("status-error-banner"):
                ThemeManager.icono("error", size=18, color="var(--color-error)")
                ui.label("ALERTA: Base de datos corrupta (503)").classes("status-error-text")

        stats_grid([
            StatItem(
                titulo="Versión",
                valor=salud.version,
                icono="tag",
                variante="neutral",
            ),
            StatItem(
                titulo="Tiempo en marcha",
                valor=_fmt_uptime(salud.uptime_segundos),
                icono="timer",
                variante="primary",
            ),
            StatItem(
                titulo="Tamaño de base de datos",
                valor=_fmt_bytes(salud.tamanio_db_bytes),
                icono="storage",
                variante="info",
            ),
            StatItem(
                titulo="Último backup",
                valor=(
                    salud.ultimo_backup.strftime("%Y-%m-%d %H:%M")
                    if salud.ultimo_backup
                    else "Sin backup registrado"
                ),
                icono="backup",
                variante="warning" if salud.ultimo_backup is None else "success",
            ),
        ])


def _seccion_log(presenter: ObservabilidadPresenter, on_filtro_change) -> None:
    """Sección 2: log de seguridad con filtro por tipo de evento."""
    with ui.element("div").classes("page-section"):
        with ui.row().classes("items-center gap-4 section-header"):
            ui.label("Log de seguridad").classes("section-title")
            ui.select(
                options=_TIPOS_EVENTO_OPCIONES,
                value=presenter.estado["filtro_tipo"],
                on_change=lambda e: on_filtro_change(e.value),
            ).classes("select-sm").props("dense outlined")

        if presenter.estado["error_eventos"]:
            empty_state(
                mensaje=f"Error al leer el log: {presenter.estado['error_eventos']}",
                icono="error",
            )
            return

        if not presenter.estado["log_disponible"]:
            from config import settings
            ruta = str(settings.SECURITY_LOG_FILE or "(no configurada)")
            empty_state(
                mensaje=f"Archivo de log no disponible. Ruta configurada: {ruta}",
                icono="folder_off",
            )
            return

        eventos = presenter.estado["eventos"]
        if not eventos:
            empty_state(mensaje="No hay eventos de seguridad registrados.", icono="history")
            return

        filas = []
        for e in eventos:
            filas.append({
                "timestamp": e.timestamp or "",
                "tipo_evento": e.tipo_evento or "",
                "usuario": e.usuario or "",
                "ip": e.ip or "",
                "motivo": e.motivo or e.recurso or e.objetivo or "",
            })

        data_table(
            columns=[
                {"name": "timestamp", "label": "Fecha/hora", "field": "timestamp"},
                {"name": "tipo_evento", "label": "Evento", "field": "tipo_evento"},
                {"name": "usuario", "label": "Usuario", "field": "usuario"},
                {"name": "ip", "label": "IP", "field": "ip"},
                {"name": "motivo", "label": "Detalle", "field": "motivo"},
            ],
            rows=filas,
        )


def _seccion_alertas(
    presenter: ObservabilidadPresenter,
    ctx: SessionContext,
    on_limpiar,
) -> None:
    """Sección 3: alertas de IP activas con opción de limpiar (R10)."""
    with ui.element("div").classes("page-section"):
        ui.label("Alertas de IP activas").classes("section-title")
        ui.label(
            "Nota: muestra las alertas del proceso actual. "
            "En despliegues multi-worker cada proceso lleva su propio estado."
        ).classes("section-note text-caption")

        if presenter.estado["error_alertas"]:
            empty_state(
                mensaje=f"Error al obtener alertas: {presenter.estado['error_alertas']}",
                icono="error",
            )
            return

        alertas = presenter.estado["alertas"]
        if not alertas:
            with ui.element("div").classes("empty-state"):
                ThemeManager.icono("check_circle", size=32, color="var(--color-success)")
                ui.label("Sin alertas de IP activas").classes("empty-state-text")
            return

        with ui.element("div").classes("alerts-panel"):
            for alerta in alertas:
                with ui.row().classes("alert-ip-row items-center gap-4"):
                    ThemeManager.icono("warning", size=16, color="var(--color-warning)")
                    ui.label(alerta.ip).classes("alert-ip-addr")
                    ui.label(f"{alerta.fallos} fallos").classes("alert-ip-count")
                    ui.label(f"Expira en {_fmt_restante(alerta.segundos_restantes)}").classes(
                        "alert-ip-restante"
                    )
                    ui.button(
                        "Limpiar",
                        on_click=lambda ip=alerta.ip: on_limpiar(ip),
                    ).classes("btn-danger-sm").props("dense flat")


def _seccion_uso(presenter: ObservabilidadPresenter) -> None:
    """Sección 4: serie diaria de uso (R12)."""
    with ui.element("div").classes("page-section"):
        ui.label("Uso diario (últimos 14 días)").classes("section-title")

        if presenter.estado["error_uso"]:
            empty_state(
                mensaje=f"Error al cargar el uso: {presenter.estado['error_uso']}",
                icono="error",
            )
            return

        uso = presenter.estado["uso"]
        if not uso:
            empty_state(mensaje="Sin datos de uso en la ventana.", icono="bar_chart")
            return

        # Serie de logins y denegados
        labels = [p.fecha[-5:] for p in uso]  # MM-DD para legibilidad
        logins = [float(p.logins) for p in uso]
        denegados = [float(p.denegados) for p in uso]

        with ui.element("div").classes("mini-charts-row"):
            mini_chart(labels, logins, titulo="Logins por día", clase="echart-sm")
            mini_chart(labels, denegados, titulo="Accesos denegados por día", clase="echart-sm")


# ── Página principal ───────────────────────────────────────────────────────────

def observabilidad_page() -> None:
    """
    Página de observabilidad de plataforma.

    Ruta: /admin/observabilidad — registrada en main.py con roles={Rol.ADMIN}.
    """
    ctx = SessionContext.desde_storage()

    presenter = ObservabilidadPresenter()

    # Carga inicial (fail-open por bloque)
    _cargar_todo(presenter)

    # ── Refreshables ──────────────────────────────────────────────────────────

    @ui.refreshable
    def salud_refreshable() -> None:
        _seccion_salud(presenter)

    @ui.refreshable
    def log_refreshable() -> None:
        def on_filtro_change(valor) -> None:
            presenter.set_filtro_tipo(valor)
            # Recargar solo el bloque de eventos
            try:
                svc = Container.observabilidad_service()
                tipo = presenter.estado["filtro_tipo"]
                entradas = svc.eventos_seguridad(tipo_evento=tipo)
                disponible = svc.log_disponible()
                presenter.cargar_eventos(entradas, disponible)
            except Exception as exc:
                logger.error("Error recargando log: %s", exc)
                presenter.error_eventos(str(exc))
            log_refreshable.refresh()

        _seccion_log(presenter, on_filtro_change)

    @ui.refreshable
    def alertas_refreshable() -> None:
        def on_limpiar(ip: str) -> None:
            """Limpia el estado de una IP y audita la acción (R11)."""
            try:
                from src.domain.policies.alerta_ip import reset_ip
                from src.domain.models.auditoria import TipoEventoSesion
                from src.interface.context.eventos_sesion import construir_evento

                reset_ip(ip)

                # Auditar la limpieza (R11):
                # - tipo_evento=EDITAR_USUARIO → _emit_security_log lo despacha a
                #   sl.gestion_usuario(actor, objetivo=detalles, operacion)
                # - detalles=ip → aparece como `objetivo` en el JSONL del security log
                # - objetivo=ip → se almacena en la columna `objetivo` de la BD
                if ctx:
                    usuario_log = ctx.usuario or ctx.usuario_nombre or "admin"
                    evento = construir_evento(
                        usuario=usuario_log,
                        usuario_id=ctx.usuario_id,
                        tipo_evento=TipoEventoSesion.EDITAR_USUARIO,
                        detalles=ip,        # → objetivo en security log (R11)
                        objetivo=ip,        # → objetivo en BD auditoria (R11)
                    )
                    try:
                        Container.auditoria_service().registrar_evento(evento)
                    except Exception as exc_audit:
                        logger.warning("No se pudo auditar la limpieza de %s: %s", ip, exc_audit)

                toast_success(f"Alerta de {ip} eliminada.")
            except Exception as exc:
                logger.error("Error limpiando alerta de %s: %s", ip, exc)
                toast_error(f"No se pudo limpiar la alerta de {ip}.")
            finally:
                # Recargar el bloque de alertas
                try:
                    svc = Container.observabilidad_service()
                    presenter.cargar_alertas(svc.alertas_ip())
                except Exception as exc:
                    presenter.error_alertas(str(exc))
                alertas_refreshable.refresh()

        _seccion_alertas(presenter, ctx, on_limpiar)

    @ui.refreshable
    def uso_refreshable() -> None:
        _seccion_uso(presenter)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def on_recargar() -> None:
        """Recarga todos los bloques."""
        _cargar_todo(presenter)
        salud_refreshable.refresh()
        log_refreshable.refresh()
        alertas_refreshable.refresh()
        uso_refreshable.refresh()

    # ── Contenido ────────────────────────────────────────────────────────────

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.row().classes("page-header-row items-center gap-4"):
                ui.label("Observabilidad").classes("page-title")
                ui.button(
                    "Recargar",
                    on_click=on_recargar,
                ).classes("btn-secondary").props("dense flat icon=refresh")

            salud_refreshable()
            log_refreshable()
            alertas_refreshable()
            uso_refreshable()

    app_layout(
        ctx,
        contenido,
        page_titulo="Observabilidad",
        page_subtitulo="Estado operativo de la plataforma",
        page_icono="monitor_heart",
    )


__all__ = ["observabilidad_page"]
