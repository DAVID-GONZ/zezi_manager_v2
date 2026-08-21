"""
src/interface/pages/convivencia/alertas.py
==========================================
Página centralizada de alertas — lista filtrable con resolución inline.
Ruta: /convivencia/alertas   Roles: _AULA
"""

from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    counter_card,
    empty_state,
    form_dialog,
    status_badge,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_secondary
from src.interface.design.components.form_fields import filter_select
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.services.alerta_service import FiltroAlertasDTO, NivelAlerta, TipoAlerta

logger = logging.getLogger("CONVIVENCIA.ALERTAS")

_TIPO_DISPLAY: dict[str, str] = {
    "faltas_injustificadas": "Faltas injustificadas",
    "promedio_bajo": "Promedio bajo",
    "materias_en_riesgo": "Materias en riesgo",
    "plan_mejoramiento_vencido": "Plan mejoramiento vencido",
    "habilitacion_pendiente": "Habilitación pendiente",
    "seguimiento_requerido": "Seguimiento requerido",
}

_NIVEL_DISPLAY: dict[str, str] = {
    "info": "Información",
    "advertencia": "Advertencia",
    "critica": "Crítica",
}

_NIVEL_VARIANTE: dict[str, str] = {
    "info": "info",
    "advertencia": "warning",
    "critica": "error",
}

_NIVEL_ICONO: dict[str, str] = {
    "info": "info",
    "advertencia": "warning",
    "critica": "error",
}

_NIVEL_COLOR: dict[str, str] = {
    "info": "var(--color-info)",
    "advertencia": "var(--color-warning)",
    "critica": "var(--color-error)",
}


def _resolver_nombre(est_id: int, nombres: dict[int, str]) -> str:
    if est_id in nombres:
        return nombres[est_id]
    if est_id == 0:
        nombre = "Estudiante eliminado"
    else:
        try:
            est = Container.estudiante_service().get_by_id(est_id)
            nombre = est.nombre_completo
        except Exception:
            nombre = f"Estudiante #{est_id}"
    nombres[est_id] = nombre
    return nombre


def alertas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Alertas: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)
    es_directivo = ctx.usuario_rol in ("director", "coordinador", "admin")

    _s: dict = {
        "alertas": [],
        "filtro_tipo": None,
        "filtro_nivel": None,
        "solo_pendientes": True,
        "nombres": {},
    }

    def _cargar() -> None:
        try:
            filtro = FiltroAlertasDTO(
                tipo_alerta=TipoAlerta(_s["filtro_tipo"]) if _s["filtro_tipo"] else None,
                nivel=NivelAlerta(_s["filtro_nivel"]) if _s["filtro_nivel"] else None,
                solo_pendientes=_s["solo_pendientes"],
                usuario_destino_id=None if es_directivo else ctx.usuario_id,
            )
            _s["alertas"] = Container.alerta_service().listar_alertas(filtro)
            for a in _s["alertas"]:
                _resolver_nombre(a.estudiante_id, _s["nombres"])
        except Exception as exc:
            logger.error("Error cargando alertas: %s", exc)
            _s["alertas"] = []

    _cargar()

    def _on_filtro_change() -> None:
        _cargar()
        panel_alertas.refresh()

    def _on_tipo_change(e) -> None:
        _s["filtro_tipo"] = e.value if e.value else None
        _on_filtro_change()

    def _on_nivel_change(e) -> None:
        _s["filtro_nivel"] = e.value if e.value else None
        _on_filtro_change()

    def _on_pendientes_change(e) -> None:
        _s["solo_pendientes"] = e.value
        _on_filtro_change()

    def _resolver(alerta_id: int, datos: dict) -> bool | None:
        obs = (datos.get("observacion") or "").strip() or None
        try:
            Container.alerta_service().resolver_alerta(alerta_id, ctx.usuario_id, obs)
            toast_success("Alerta resuelta correctamente.")
            _cargar()
            panel_alertas.refresh()
            return True
        except ValueError as exc:
            toast_warning(str(exc))
            return False
        except Exception as exc:
            logger.error("Error resolviendo alerta %s: %s", alerta_id, exc)
            toast_error("Error al resolver la alerta.")
            return False

    def _abrir_resolver(alerta_id: int) -> None:
        form_dialog(
            titulo="Resolver alerta",
            campos=[
                {
                    "key": "observacion",
                    "label": "Observación (opcional)",
                    "tipo": "textarea",
                    "placeholder": "¿Cómo se resolvió esta alerta?",
                },
            ],
            on_submit=lambda datos: _resolver(alerta_id, datos),
            texto_submit="Resolver",
        )

    def contenido() -> None:
        # Filtros
        with ui.element("div").classes("filter-bar"):
            opciones_tipo = {t.value: _TIPO_DISPLAY.get(t.value, t.value) for t in TipoAlerta}
            filter_select(
                label="Tipo",
                options=opciones_tipo,
                value=_s["filtro_tipo"],
                placeholder="Todos los tipos",
                on_change=_on_tipo_change,
            )
            opciones_nivel = {n.value: _NIVEL_DISPLAY.get(n.value, n.value) for n in NivelAlerta}
            filter_select(
                label="Nivel",
                options=opciones_nivel,
                value=_s["filtro_nivel"],
                placeholder="Todos los niveles",
                on_change=_on_nivel_change,
            )
            ui.switch("Solo pendientes", value=_s["solo_pendientes"], on_change=_on_pendientes_change).classes("andes-switch")

        panel_alertas()

    @ui.refreshable
    def panel_alertas() -> None:
        alertas = _s["alertas"]

        # KPIs
        total = len(alertas)
        criticas = sum(1 for a in alertas if str(a.nivel).lower() in ("critica", "nivelalerta.critica"))
        pendientes = sum(1 for a in alertas if not a.resuelta)

        with ui.element("div").classes("stats-row"):
            counter_card("Total", total, icono="notifications")
            counter_card("Críticas", criticas, icono="error", variante="danger" if criticas else "default")
            counter_card("Pendientes", pendientes, icono="pending_actions", variante="warning" if pendientes else "success")

        if not alertas:
            empty_state(
                titulo="Sin alertas",
                descripcion="No se encontraron alertas con los filtros seleccionados.",
                icono="notifications_off",
            )
            return

        # Lista de alertas
        for alerta in alertas:
            nivel_raw = str(alerta.nivel).split(".")[-1] if "." in str(alerta.nivel) else str(alerta.nivel)
            nivel = nivel_raw.lower()
            color = _NIVEL_COLOR.get(nivel, "var(--color-info)")
            icono = _NIVEL_ICONO.get(nivel, "info")
            tipo_label = _TIPO_DISPLAY.get(str(alerta.tipo_alerta).split(".")[-1] if "." in str(alerta.tipo_alerta) else str(alerta.tipo_alerta), str(alerta.tipo_alerta))
            nombre = _s["nombres"].get(alerta.estudiante_id, f"#{alerta.estudiante_id}")
            fecha = str(alerta.fecha_generacion)[:10]

            with ui.element("div").classes(f"alerta-card alerta-card--{nivel}"):
                with ui.element("div").classes("alerta-card-header"):
                    ThemeManager.icono(icono, size=20, color=color)
                    with ui.element("div").classes("alerta-card-info"):
                        with ui.element("div").classes("alerta-card-title-row"):
                            ui.label(nombre).classes("alerta-card-nombre")
                            status_badge(
                                "Pendiente" if alerta.esta_pendiente else "Resuelta",
                                variante="warning" if alerta.esta_pendiente else "success",
                            )
                        ui.label(f"{tipo_label} · {fecha}").classes("alerta-card-meta")
                    if alerta.esta_pendiente:
                        btn_secondary(
                            "Resolver",
                            on_click=lambda aid=alerta.id: _abrir_resolver(aid),
                            icon="check_circle",
                            size="sm",
                        )

                desc = str(alerta.descripcion)[:200]
                ui.label(desc).classes("alerta-card-desc")

                if alerta.resuelta and alerta.observacion_resolucion:
                    with ui.element("div").classes("alerta-card-resolucion"):
                        ThemeManager.icono("check_circle", size=14, color="var(--color-success)")
                        ui.label(alerta.observacion_resolucion[:150]).classes("alerta-card-obs")

    app_layout(
        ctx,
        contenido,
        page_titulo="Alertas",
        page_subtitulo="Alertas pendientes y resueltas del sistema",
        page_icono="notifications",
    )


__all__ = ["alertas_page"]
