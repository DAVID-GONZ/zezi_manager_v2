"""
src/interface/pages/institucion/hub_institucion.py
===================================================
Hub editable de gestión institucional (mejora_09c).
Ruta: /institucion/configuracion  •  roles: {Rol.DIRECTOR}

Permite al director editar en cualquier momento:
  1. Identidad institucional (todos los campos, sin logo)
  2. Preferencias académicas (nota mínima, escala, nº periodos)
  3. Módulos activos (convivencia, alertas)
  4. Apariencia (colores primario y secundario)

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.
  Solo usa Container (servicios) e imports de la capa de interfaz.

  Decisión sobre enums (T2): se usan strings crudos para jornada/tipo/calendario,
  igual que en configuracion_inicial.py (wizard). El DTO de servicio valida el
  valor al construirlo; si el valor no es válido lanzará ValueError, capturado
  por el handler. No se amplía institucion_service.__all__ (opción B).

  Decisión sobre CSS auxiliar: NO se crea hub_institucion.css. Se reusan las
  clases del design system existentes (base-form-grid, panel-card, form-box, etc.)

  Decisión sobre icono NAV: "settings" (no "business"). "settings" encaja mejor
  con la semántica de configuración del tenant y es consistente con page_icono.

  Fix bug color_input (09b): value=prefs.color_primario  —  el DTO garantiza
  que nunca es None para claves conocidas (default #2E3192 / #8B90F0).

Flujo:
  1. Prefill desde institucion_service.get + preferencias_service.get_dto
  2. 4 tabs independientes con persistencia atómica por sección
  3. Cada sección tiene botón Guardar propio y botón Recargar ghost

Refreshables:
  _panel_identidad()   — re-renderiza formulario de identidad
  _panel_preferencias() — re-renderiza formulario de preferencias
  _panel_modulos()     — re-renderiza formulario de módulos
  _panel_apariencia()  — re-renderiza formulario de apariencia
"""

from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.domain.modulos import modulos_desactivables as _modulos_desactivables
from src.interface.context.session_context import SessionContext
from src.interface.design.components.buttons import btn_ghost, btn_primary
from src.interface.design.components.toast import (
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.layout import app_layout
from src.interface.presenters.institucion.hub_institucion_presenter import HubInstitucionPresenter
from src.services.institucion_service import ActualizarInstitucionDTO
from src.services.preferencias_institucion_service import ActualizarPreferenciaDTO

logger = logging.getLogger("HUB_INSTITUCION")

# Opciones de selects — strings crudos, sin importar enums del dominio (opción B).
_OPCIONES_JORNADA: list[str] = ["AM", "PM", "UNICA"]
_OPCIONES_TIPO: list[str] = ["publica", "privada"]
_OPCIONES_CAL: list[str] = ["A", "B"]

# Mapa de tipos de registro para el multi-select del boletín (convivencia_29).
# Espejo de TIPO_REGISTRO_DISPLAY del dominio — sin importar src.domain.models.*.
_OPCIONES_TIPO_REGISTRO: dict[str, str] = {
    "fortaleza": "Fortaleza",
    "dificultad": "Dificultad",
    "compromiso": "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo": "Descargo",
}


# ── Estado inicial ────────────────────────────────────────────────────────────


def _estado_inicial() -> dict:
    return {
        "identidad": {
            "nombre": "",
            "nombre_oficial": "",
            "rector": "",
            "municipio": "",
            "codigo_dane": "",
            "nit": "",
            "direccion": "",
            "telefono": "",
            "email_institucional": "",
            "resolucion_aprobacion": "",
            "lema": "",
            "jornada_principal": None,
            "tipo_institucion": None,
            "calendario": None,
        },
        "preferencias": {
            "nota_minima_aprobacion_default": 60.0,
            "nota_minima_escala_default": 0.0,
            "nota_maxima_escala_default": 100.0,
            "numero_periodos_default": 4,
        },
        "modulos": {d.clave_preferencia: True for d in _modulos_desactivables()},
        "apariencia": {
            "color_primario": None,
            "color_secundario": None,
        },
        # Política de registros de convivencia en el boletín (convivencia_29).
        "convivencia": {
            "registros_boletin_tipos": ["fortaleza", "compromiso", "citacion_acudiente"],
            "registros_boletin_dificultad_requiere_notificacion": True,
            "registros_boletin_incluye_descargo": False,
            "registros_boletin_dedup_observaciones": True,
        },
    }


def _cargar_estado(inst_id: int, _s: dict) -> None:
    """Carga datos actuales desde los servicios. No lanza excepciones al exterior."""
    try:
        inst = Container.institucion_service().get(inst_id)
        _jornada_raw = getattr(inst, "jornada_principal", None)
        _tipo_raw = getattr(inst, "tipo_institucion", None)
        _cal_raw = getattr(inst, "calendario", None)
        _s["identidad"].update(
            {
                "nombre": inst.nombre or "",
                "nombre_oficial": inst.nombre_oficial or "",
                "rector": inst.rector or "",
                "municipio": inst.municipio or "",
                "codigo_dane": inst.codigo_dane or "",
                "nit": inst.nit or "",
                "direccion": inst.direccion or "",
                "telefono": inst.telefono or "",
                "email_institucional": inst.email_institucional or "",
                "resolucion_aprobacion": inst.resolucion_aprobacion or "",
                "lema": inst.lema or "",
                "jornada_principal": _jornada_raw.value if _jornada_raw else None,
                "tipo_institucion": _tipo_raw.value if _tipo_raw else None,
                "calendario": _cal_raw.value if _cal_raw else None,
            }
        )
    except Exception as exc:
        logger.error("Error cargando identidad institucional: %s", exc)

    try:
        prefs = Container.preferencias_service().get_dto(inst_id)
        _s["preferencias"].update(
            {
                "nota_minima_aprobacion_default": prefs.nota_minima_aprobacion_default,
                "nota_minima_escala_default": prefs.nota_minima_escala_default,
                "nota_maxima_escala_default": prefs.nota_maxima_escala_default,
                "numero_periodos_default": prefs.numero_periodos_default,
            }
        )
        for d in _modulos_desactivables():
            clave = d.clave_preferencia
            _s["modulos"][clave] = getattr(prefs, clave, True)
        _s["apariencia"].update(
            {
                "color_primario": prefs.color_primario,
                "color_secundario": prefs.color_secundario,
            }
        )
        _s["convivencia"].update(
            {
                "registros_boletin_tipos": prefs.registros_boletin_tipos,
                "registros_boletin_dificultad_requiere_notificacion": prefs.registros_boletin_dificultad_requiere_notificacion,
                "registros_boletin_incluye_descargo": prefs.registros_boletin_incluye_descargo,
                "registros_boletin_dedup_observaciones": prefs.registros_boletin_dedup_observaciones,
            }
        )
    except Exception as exc:
        logger.error("Error cargando preferencias: %s", exc)


# ── Página ────────────────────────────────────────────────────────────────────


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def hub_institucion_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    inst_id = ctx.institucion_id
    logger.info("Hub institucional: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    presenter = HubInstitucionPresenter()
    _s = presenter.estado  # misma referencia: bind_value/refreshables usan el estado del presenter
    _cargar_estado(inst_id, _s)

    # ── Sección Identidad ─────────────────────────────────────────────────────
    @ui.refreshable
    def _panel_identidad() -> None:

        with ui.element("div").classes("base-form-grid base-form-grid-2col"):
            with ui.element("div").classes("base-form-field-col"):
                with ui.element("div").classes("form-field-label-row"):
                    ui.label("Nombre corto").classes("form-field-label")
                    ui.label("*").classes("form-field-req")
                nombre_i = (
                    ui.input()
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                nombre_i.value = _s["identidad"]["nombre"]

            with ui.element("div").classes("base-form-field-col"):
                with ui.element("div").classes("form-field-label-row"):
                    ui.label("Nombre oficial").classes("form-field-label")
                    ui.label("*").classes("form-field-req")
                nombre_oficial_i = (
                    ui.input()
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                nombre_oficial_i.value = _s["identidad"]["nombre_oficial"]

            with ui.element("div").classes("base-form-field-col"):
                with ui.element("div").classes("form-field-label-row"):
                    ui.label("Rector(a)").classes("form-field-label")
                    ui.label("*").classes("form-field-req")
                rector_i = (
                    ui.input()
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                rector_i.value = _s["identidad"]["rector"]

            with ui.element("div").classes("base-form-field-col"):
                with ui.element("div").classes("form-field-label-row"):
                    ui.label("Municipio").classes("form-field-label")
                    ui.label("*").classes("form-field-req")
                municipio_i = (
                    ui.input()
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                municipio_i.value = _s["identidad"]["municipio"]

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Código DANE (12 dígitos)").classes("form-field-label")
                codigo_dane_i = (
                    ui.input(placeholder="123456789012")
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                codigo_dane_i.value = _s["identidad"]["codigo_dane"]

            with ui.element("div").classes("base-form-field-col"):
                ui.label("NIT").classes("form-field-label")
                nit_i = (
                    ui.input(placeholder="Ej: 900123456-7")
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                nit_i.value = _s["identidad"]["nit"]

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Dirección").classes("form-field-label")
                direccion_i = (
                    ui.input()
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                direccion_i.value = _s["identidad"]["direccion"]

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Teléfono").classes("form-field-label")
                telefono_i = (
                    ui.input()
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                telefono_i.value = _s["identidad"]["telefono"]

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Email institucional").classes("form-field-label")
                email_i = (
                    ui.input(placeholder="correo@institucion.edu.co")
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                email_i.value = _s["identidad"]["email_institucional"]

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Resolución de aprobación").classes("form-field-label")
                resol_i = (
                    ui.input()
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                resol_i.value = _s["identidad"]["resolucion_aprobacion"]

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Lema institucional").classes("form-field-label")
                lema_i = (
                    ui.input()
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )
                lema_i.value = _s["identidad"]["lema"]

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Jornada principal").classes("form-field-label")
                jornada_i = (
                    ui.select(_OPCIONES_JORNADA, value=_s["identidad"]["jornada_principal"])
                    .classes("andes-input w-full")
                    .props("borderless dense clearable")
                )

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Tipo de institución").classes("form-field-label")
                tipo_i = (
                    ui.select(_OPCIONES_TIPO, value=_s["identidad"]["tipo_institucion"])
                    .classes("andes-input w-full")
                    .props("borderless dense clearable")
                )

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Calendario").classes("form-field-label")
                calendario_i = (
                    ui.select(_OPCIONES_CAL, value=_s["identidad"]["calendario"])
                    .classes("andes-input w-full")
                    .props("borderless dense clearable")
                )

        def _guardar_identidad() -> None:
            nombre = (nombre_i.value or "").strip()
            nombre_oficial = (nombre_oficial_i.value or "").strip()
            rector = (rector_i.value or "").strip()
            municipio = (municipio_i.value or "").strip()
            if not nombre or not nombre_oficial or not rector or not municipio:
                toast_warning(
                    "Completa los campos obligatorios: "
                    "Nombre corto, Nombre oficial, Rector/a y Municipio."
                )
                return
            try:
                dto = ActualizarInstitucionDTO(
                    nombre=nombre,
                    nombre_oficial=nombre_oficial,
                    rector=rector,
                    municipio=municipio,
                    codigo_dane=(codigo_dane_i.value or "").strip() or None,
                    nit=(nit_i.value or "").strip() or None,
                    direccion=(direccion_i.value or "").strip() or None,
                    telefono=(telefono_i.value or "").strip() or None,
                    email_institucional=(email_i.value or "").strip() or None,
                    resolucion_aprobacion=(resol_i.value or "").strip() or None,
                    lema=(lema_i.value or "").strip() or None,
                    jornada_principal=jornada_i.value or None,
                    tipo_institucion=tipo_i.value or None,
                    calendario=calendario_i.value or None,
                )
                Container.institucion_service().actualizar(inst_id, dto)
                # Mantener _s en sinc con lo guardado
                _s["identidad"].update(
                    {
                        "nombre": nombre,
                        "nombre_oficial": nombre_oficial,
                        "rector": rector,
                        "municipio": municipio,
                    }
                )
                toast_success("Identidad institucional actualizada correctamente.")
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error guardando identidad: %s", exc, exc_info=True)
                toast_error("Error al guardar la identidad. Intenta de nuevo.")

        def _recargar_identidad() -> None:
            try:
                inst = Container.institucion_service().get(inst_id)
                _jornada_raw = getattr(inst, "jornada_principal", None)
                _tipo_raw = getattr(inst, "tipo_institucion", None)
                _cal_raw = getattr(inst, "calendario", None)
                _s["identidad"].update(
                    {
                        "nombre": inst.nombre or "",
                        "nombre_oficial": inst.nombre_oficial or "",
                        "rector": inst.rector or "",
                        "municipio": inst.municipio or "",
                        "codigo_dane": inst.codigo_dane or "",
                        "nit": inst.nit or "",
                        "direccion": inst.direccion or "",
                        "telefono": inst.telefono or "",
                        "email_institucional": inst.email_institucional or "",
                        "resolucion_aprobacion": inst.resolucion_aprobacion or "",
                        "lema": inst.lema or "",
                        "jornada_principal": _jornada_raw.value if _jornada_raw else None,
                        "tipo_institucion": _tipo_raw.value if _tipo_raw else None,
                        "calendario": _cal_raw.value if _cal_raw else None,
                    }
                )
            except Exception as exc:
                logger.error("Error recargando identidad: %s", exc)
            _panel_identidad.refresh()

        with ui.element("div").classes("form-row-actions u-mt-lg"):
            btn_ghost("Recargar", on_click=_recargar_identidad, icon="refresh")
            btn_primary("Guardar cambios", on_click=_guardar_identidad, icon="save")

    # ── Sección Preferencias ──────────────────────────────────────────────────
    @ui.refreshable
    def _panel_preferencias() -> None:

        with ui.element("div").classes("base-form-grid base-form-grid-2col"):
            with ui.element("div").classes("base-form-field-col"):
                ui.label("Nota mínima de aprobación").classes("form-field-label")
                nota_apro_i = (
                    ui.number(
                        value=_s["preferencias"]["nota_minima_aprobacion_default"],
                        min=0,
                        max=100,
                        step=0.5,
                        format="%.1f",
                    )
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Nota mínima de escala").classes("form-field-label")
                nota_min_i = (
                    ui.number(
                        value=_s["preferencias"]["nota_minima_escala_default"],
                        min=0,
                        max=100,
                        step=0.5,
                        format="%.1f",
                    )
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Nota máxima de escala").classes("form-field-label")
                nota_max_i = (
                    ui.number(
                        value=_s["preferencias"]["nota_maxima_escala_default"],
                        min=0,
                        max=100,
                        step=0.5,
                        format="%.1f",
                    )
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )

            with ui.element("div").classes("base-form-field-col"):
                ui.label("Número de periodos").classes("form-field-label")
                periodos_i = (
                    ui.number(
                        value=_s["preferencias"]["numero_periodos_default"],
                        min=1,
                        max=6,
                        step=1,
                        format="%.0f",
                    )
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )

        def _guardar_preferencias() -> None:
            try:
                min_apro = float(nota_apro_i.value or 0)
                min_esc = float(nota_min_i.value or 0)
                max_esc = float(nota_max_i.value or 100)
                periodos = round(float(periodos_i.value or 4))
                if min_esc >= max_esc:
                    toast_warning("La nota mínima de escala debe ser menor que la máxima.")
                    return
                if not (min_esc <= min_apro <= max_esc):
                    toast_warning("La nota de aprobación debe estar dentro del rango de escala.")
                    return
                svc = Container.preferencias_service()
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="nota_minima_aprobacion_default", valor=str(min_apro)
                    ),
                )
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="nota_minima_escala_default", valor=str(min_esc)
                    ),
                )
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="nota_maxima_escala_default", valor=str(max_esc)
                    ),
                )
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(clave="numero_periodos_default", valor=str(periodos)),
                )
                _s["preferencias"].update(
                    {
                        "nota_minima_aprobacion_default": min_apro,
                        "nota_minima_escala_default": min_esc,
                        "nota_maxima_escala_default": max_esc,
                        "numero_periodos_default": periodos,
                    }
                )
                toast_success("Preferencias académicas actualizadas correctamente.")
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error guardando preferencias: %s", exc, exc_info=True)
                toast_error("Error al guardar las preferencias. Intenta de nuevo.")

        def _recargar_preferencias() -> None:
            try:
                prefs = Container.preferencias_service().get_dto(inst_id)
                _s["preferencias"].update(
                    {
                        "nota_minima_aprobacion_default": prefs.nota_minima_aprobacion_default,
                        "nota_minima_escala_default": prefs.nota_minima_escala_default,
                        "nota_maxima_escala_default": prefs.nota_maxima_escala_default,
                        "numero_periodos_default": prefs.numero_periodos_default,
                    }
                )
            except Exception as exc:
                logger.error("Error recargando preferencias: %s", exc)
            _panel_preferencias.refresh()

        with ui.element("div").classes("form-row-actions u-mt-lg"):
            btn_ghost("Recargar", on_click=_recargar_preferencias, icon="refresh")
            btn_primary("Guardar cambios", on_click=_guardar_preferencias, icon="save")

    # ── Sección Módulos ───────────────────────────────────────────────────────
    @ui.refreshable
    def _panel_modulos() -> None:

        ui.label(
            "Al desactivar un módulo, sus páginas y su ítem de NAV se ocultan "
            "hasta reactivarlo. Los cambios se aplican en la siguiente navegación."
        ).classes("text-muted u-mb-sm")

        desactivables = _modulos_desactivables()
        toggles: dict[str, ui.switch] = {}

        with ui.element("div").classes("u-stack-sm"):
            for d in desactivables:
                clave = d.clave_preferencia
                with ui.element("div").classes("form-row-between form-box"):
                    with ui.element("div").classes("u-stack-xs flex-1"):
                        ui.label(f"Módulo de {d.label.lower()}").classes("section-subtitle")
                        ui.label(d.descripcion).classes("text-muted")
                    toggles[clave] = ui.switch("", value=_s["modulos"].get(clave, True))

        def _guardar_modulos() -> None:
            try:
                svc = Container.preferencias_service()
                for clave, toggle in toggles.items():
                    svc.set(
                        inst_id,
                        ActualizarPreferenciaDTO(
                            clave=clave,
                            valor=str(bool(toggle.value)).lower(),
                        ),
                    )
                    _s["modulos"][clave] = bool(toggle.value)
                toast_success("Configuración de módulos actualizada correctamente.")
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error guardando módulos: %s", exc, exc_info=True)
                toast_error("Error al guardar la configuración de módulos.")

        def _recargar_modulos() -> None:
            try:
                prefs = Container.preferencias_service().get_dto(inst_id)
                for d in desactivables:
                    clave = d.clave_preferencia
                    _s["modulos"][clave] = getattr(prefs, clave, True)
            except Exception as exc:
                logger.error("Error recargando módulos: %s", exc)
            _panel_modulos.refresh()

        with ui.element("div").classes("form-row-actions u-mt-lg"):
            btn_ghost("Recargar", on_click=_recargar_modulos, icon="refresh")
            btn_primary("Guardar cambios", on_click=_guardar_modulos, icon="save")

    # ── Sección Apariencia ────────────────────────────────────────────────────
    @ui.refreshable
    def _panel_apariencia() -> None:

        ui.label("Los cambios de color se aplican al recargar la aplicación.").classes(
            "text-muted u-mb-sm"
        )

        with ui.element("div").classes("u-stack-sm"):
            with ui.element("div").classes("form-row-between form-box"):
                ui.label("Color primario").classes("section-subtitle")
                color_prim_i = ui.color_input(value=_s["apariencia"]["color_primario"])

            with ui.element("div").classes("form-row-between form-box"):
                ui.label("Color secundario").classes("section-subtitle")
                color_sec_i = ui.color_input(value=_s["apariencia"]["color_secundario"])

        def _guardar_apariencia() -> None:
            try:
                svc = Container.preferencias_service()
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="color_primario",
                        valor=(color_prim_i.value or "").strip() or None,
                    ),
                )
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="color_secundario",
                        valor=(color_sec_i.value or "").strip() or None,
                    ),
                )
                _s["apariencia"].update(
                    {
                        "color_primario": (color_prim_i.value or "").strip() or None,
                        "color_secundario": (color_sec_i.value or "").strip() or None,
                    }
                )
                toast_success("Colores actualizados. Recarga la página para aplicarlos.")
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error guardando apariencia: %s", exc, exc_info=True)
                toast_error("Error al guardar los colores. Intenta de nuevo.")

        def _recargar_apariencia() -> None:
            try:
                prefs = Container.preferencias_service().get_dto(inst_id)
                _s["apariencia"].update(
                    {
                        "color_primario": prefs.color_primario,
                        "color_secundario": prefs.color_secundario,
                    }
                )
            except Exception as exc:
                logger.error("Error recargando apariencia: %s", exc)
            _panel_apariencia.refresh()

        with ui.element("div").classes("form-row-actions u-mt-lg"):
            btn_ghost("Recargar", on_click=_recargar_apariencia, icon="refresh")
            btn_primary("Guardar cambios", on_click=_guardar_apariencia, icon="save")

    # ── Sección Convivencia — Eventos en el boletín (convivencia_29) ─────────
    @ui.refreshable
    def _panel_convivencia() -> None:
        import json as _json

        ui.label(
            "Configura qué eventos de convivencia aparecen en el boletín del estudiante."
        ).classes("text-muted u-mb-sm")

        with ui.element("div").classes("u-stack-sm"):
            with ui.element("div").classes("base-form-field-col"):
                ui.label("Tipos de evento incluidos en el boletín").classes("section-subtitle")
                tipos_select = (
                    ui.select(
                        options=_OPCIONES_TIPO_REGISTRO,
                        multiple=True,
                        value=_s["convivencia"]["registros_boletin_tipos"],
                    )
                    .classes("andes-input w-full")
                    .props("borderless dense")
                )

            with ui.element("div").classes("form-box"):
                dificultad_notif_cb = ui.checkbox(
                    "Solo incluir dificultades cuando el acudiente ha sido notificado",
                    value=_s["convivencia"]["registros_boletin_dificultad_requiere_notificacion"],
                )

            with ui.element("div").classes("form-box"):
                descargo_cb = ui.checkbox(
                    "Incluir descargos",
                    value=_s["convivencia"]["registros_boletin_incluye_descargo"],
                )

            with ui.element("div").classes("form-box"):
                dedup_cb = ui.checkbox(
                    "No duplicar eventos que ya aparecen como observación pública",
                    value=_s["convivencia"]["registros_boletin_dedup_observaciones"],
                )

        def _guardar_convivencia() -> None:
            try:
                svc = Container.preferencias_service()
                tipos = list(tipos_select.value) if tipos_select.value else []
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="registros_boletin_tipos",
                        valor=_json.dumps(tipos),
                    ),
                )
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="registros_boletin_dificultad_requiere_notificacion",
                        valor=str(bool(dificultad_notif_cb.value)).lower(),
                    ),
                )
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="registros_boletin_incluye_descargo",
                        valor=str(bool(descargo_cb.value)).lower(),
                    ),
                )
                svc.set(
                    inst_id,
                    ActualizarPreferenciaDTO(
                        clave="registros_boletin_dedup_observaciones",
                        valor=str(bool(dedup_cb.value)).lower(),
                    ),
                )
                _s["convivencia"].update(
                    {
                        "registros_boletin_tipos": tipos,
                        "registros_boletin_dificultad_requiere_notificacion": bool(
                            dificultad_notif_cb.value
                        ),
                        "registros_boletin_incluye_descargo": bool(descargo_cb.value),
                        "registros_boletin_dedup_observaciones": bool(dedup_cb.value),
                    }
                )
                toast_success("Configuración de convivencia en boletín actualizada.")
            except ValueError as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error guardando convivencia: %s", exc, exc_info=True)
                toast_error("Error al guardar la configuración de convivencia.")

        def _recargar_convivencia() -> None:
            try:
                prefs = Container.preferencias_service().get_dto(inst_id)
                _s["convivencia"].update(
                    {
                        "registros_boletin_tipos": prefs.registros_boletin_tipos,
                        "registros_boletin_dificultad_requiere_notificacion": prefs.registros_boletin_dificultad_requiere_notificacion,
                        "registros_boletin_incluye_descargo": prefs.registros_boletin_incluye_descargo,
                        "registros_boletin_dedup_observaciones": prefs.registros_boletin_dedup_observaciones,
                    }
                )
            except Exception as exc:
                logger.error("Error recargando convivencia: %s", exc)
            _panel_convivencia.refresh()

        with ui.element("div").classes("form-row-actions u-mt-lg"):
            btn_ghost("Recargar", on_click=_recargar_convivencia, icon="refresh")
            btn_primary("Guardar cambios", on_click=_guardar_convivencia, icon="save")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                with ui.tabs().classes("w-full") as tabs:
                    tab_id = ui.tab("identidad", label="Identidad")
                    tab_pref = ui.tab("preferencias", label="Preferencias")
                    tab_mod = ui.tab("modulos", label="Módulos")
                    tab_ap = ui.tab("apariencia", label="Apariencia")
                    tab_conv = ui.tab("convivencia", label="Convivencia")

                with ui.tab_panels(tabs, value=tab_id).classes("w-full"):
                    with ui.tab_panel(tab_id):
                        _panel_identidad()
                    with ui.tab_panel(tab_pref):
                        _panel_preferencias()
                    with ui.tab_panel(tab_mod):
                        _panel_modulos()
                    with ui.tab_panel(tab_ap):
                        _panel_apariencia()
                    with ui.tab_panel(tab_conv):
                        _panel_convivencia()

    app_layout(
        ctx,
        contenido,
        page_titulo="Configuración institucional",
        page_subtitulo="Identidad, preferencias, módulos y apariencia",
        page_icono="settings",
    )


__all__ = ["hub_institucion_page"]
