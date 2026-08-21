"""
src/interface/pages/convivencia/configuracion_alertas.py
=======================================================
Configuración de umbrales de alertas por año lectivo.
Ruta: /convivencia/configuracion-alertas   Roles: _DIR_COORD
"""

from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    empty_state,
    form_dialog,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_primary, btn_secondary
from src.interface.design.layout import app_layout
from src.services.alerta_service import ConfiguracionAlerta, TipoAlerta

logger = logging.getLogger("CONVIVENCIA.CONFIG_ALERTAS")

_TIPO_DISPLAY: dict[str, str] = {
    "faltas_injustificadas": "Faltas injustificadas",
    "promedio_bajo": "Promedio bajo",
    "materias_en_riesgo": "Materias en riesgo",
    "plan_mejoramiento_vencido": "Plan mejoramiento vencido",
    "habilitacion_pendiente": "Habilitación pendiente",
    "seguimiento_requerido": "Seguimiento requerido",
}

_TIPO_HINT: dict[str, str] = {
    "faltas_injustificadas": "Número de faltas injustificadas antes de generar alerta",
    "promedio_bajo": "Nota por debajo de la cual se genera alerta (0–100)",
    "materias_en_riesgo": "Cantidad de materias perdidas para generar alerta",
    "plan_mejoramiento_vencido": "Días de vencimiento antes de alertar",
    "habilitacion_pendiente": "Días antes de la fecha límite para alertar",
    "seguimiento_requerido": "Cantidad de registros negativos para generar alerta",
}

_TIPO_DEFAULTS: dict[str, float] = {
    "faltas_injustificadas": 3,
    "promedio_bajo": 60.0,
    "materias_en_riesgo": 2,
    "plan_mejoramiento_vencido": 1,
    "habilitacion_pendiente": 1,
    "seguimiento_requerido": 3,
}


def configuracion_alertas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Config alertas: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    _s: dict = {
        "anio_id": None,
        "anio_nombre": "",
        "configs": {},
    }

    def _cargar() -> None:
        try:
            config_anio = Container.configuracion_service().get_activa(ctx.institucion_id)
            if config_anio:
                _s["anio_id"] = config_anio.id
                _s["anio_nombre"] = str(config_anio.anio)
                configs_list = Container.alerta_service().listar_configuraciones(
                    config_anio.id, solo_activas=False
                )
                _s["configs"] = {str(c.tipo_alerta): c for c in configs_list}
            else:
                _s["anio_id"] = None
                _s["configs"] = {}
        except Exception as exc:
            logger.error("Error cargando config alertas: %s", exc)
            _s["anio_id"] = None
            _s["configs"] = {}

    _cargar()

    def _guardar(tipo_str: str, datos: dict) -> bool | None:
        try:
            tipo = TipoAlerta(tipo_str)
            umbral = float(datos["umbral"])
            config = ConfiguracionAlerta(
                anio_id=_s["anio_id"],
                tipo_alerta=tipo,
                umbral=umbral,
                activa=bool(datos.get("activa", True)),
                notificar_docente=bool(datos.get("notificar_docente", True)),
                notificar_director=bool(datos.get("notificar_director", False)),
                notificar_acudiente=bool(datos.get("notificar_acudiente", False)),
            )
            Container.alerta_service().configurar_alerta(config)
            toast_success(f"Configuración de «{_TIPO_DISPLAY.get(tipo_str, tipo_str)}» guardada.")
            _cargar()
            panel_config.refresh()
            return True
        except ValueError as exc:
            toast_warning(str(exc))
            return False
        except Exception as exc:
            logger.error("Error guardando config: %s", exc)
            toast_error("Error al guardar la configuración.")
            return False

    def _abrir_editar(tipo_str: str) -> None:
        config_existente = _s["configs"].get(tipo_str)
        hint = _TIPO_HINT.get(tipo_str, "")
        es_promedio = tipo_str == "promedio_bajo"

        umbral_val = config_existente.umbral if config_existente else _TIPO_DEFAULTS.get(tipo_str, 1)
        activa_val = config_existente.activa if config_existente else True
        notif_doc = config_existente.notificar_docente if config_existente else True
        notif_dir = config_existente.notificar_director if config_existente else False
        notif_acu = config_existente.notificar_acudiente if config_existente else False

        campos = [
            {
                "key": "umbral",
                "label": "Umbral",
                "tipo": "number",
                "valor": umbral_val,
                "hint": hint,
                "requerido": True,
                "min": 0.1 if es_promedio else 1,
                "max": 100 if es_promedio else 999,
                "step": 0.1 if es_promedio else 1,
            },
            {
                "key": "activa",
                "label": "Activar esta alerta",
                "tipo": "checkbox",
                "valor": activa_val,
            },
            {
                "key": "notificar_docente",
                "label": "Notificar al docente",
                "tipo": "checkbox",
                "valor": notif_doc,
            },
            {
                "key": "notificar_director",
                "label": "Notificar al director",
                "tipo": "checkbox",
                "valor": notif_dir,
            },
            {
                "key": "notificar_acudiente",
                "label": "Notificar al acudiente",
                "tipo": "checkbox",
                "valor": notif_acu,
            },
        ]

        titulo = f"Configurar «{_TIPO_DISPLAY.get(tipo_str, tipo_str)}»"
        form_dialog(
            titulo=titulo,
            campos=campos,
            on_submit=lambda datos: _guardar(tipo_str, datos),
            texto_submit="Guardar",
            icono="tune",
        )

    def contenido() -> None:
        panel_config()

    @ui.refreshable
    def panel_config() -> None:
        if not _s["anio_id"]:
            empty_state(
                titulo="Sin año lectivo activo",
                descripcion="Configure un año lectivo para poder establecer umbrales de alertas.",
                icono="event_busy",
            )
            return

        ui.label(f"Año lectivo: {_s['anio_nombre']}").classes("text-sm color-secondary mb-md")

        for tipo in TipoAlerta:
            tipo_str = tipo.value
            config = _s["configs"].get(tipo_str)
            label = _TIPO_DISPLAY.get(tipo_str, tipo_str)
            hint = _TIPO_HINT.get(tipo_str, "")

            with ui.element("div").classes("config-alerta-row"):
                with ui.element("div").classes("config-alerta-info"):
                    ui.label(label).classes("config-alerta-label")
                    ui.label(hint).classes("config-alerta-hint")

                if config:
                    with ui.element("div").classes("config-alerta-values"):
                        umbral_display = f"{config.umbral:.1f}" if tipo_str == "promedio_bajo" else str(int(config.umbral))
                        ui.label(f"Umbral: {umbral_display}").classes("config-alerta-umbral")

                        estado_cls = "badge-activa" if config.activa else "badge-inactiva"
                        ui.label("Activa" if config.activa else "Inactiva").classes(f"config-alerta-badge {estado_cls}")

                        notif_parts = []
                        if config.notificar_docente:
                            notif_parts.append("Docente")
                        if config.notificar_director:
                            notif_parts.append("Director")
                        if config.notificar_acudiente:
                            notif_parts.append("Acudiente")
                        if notif_parts:
                            ui.label(f"Notifica: {', '.join(notif_parts)}").classes("config-alerta-notif")

                    btn_secondary(
                        "Editar",
                        on_click=lambda t=tipo_str: _abrir_editar(t),
                        icon="edit",
                        size="sm",
                    )
                else:
                    ui.label("Sin configurar").classes("config-alerta-sin")
                    btn_primary(
                        "Crear",
                        on_click=lambda t=tipo_str: _abrir_editar(t),
                        icon="add",
                        size="sm",
                    )

    app_layout(
        ctx,
        contenido,
        page_titulo="Configuración de alertas",
        page_subtitulo="Umbrales y notificaciones por tipo de alerta",
        page_icono="tune",
    )


__all__ = ["configuracion_alertas_page"]
