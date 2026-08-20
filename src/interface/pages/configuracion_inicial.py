"""
configuracion_inicial.py — Wizard de configuración inicial obligatoria (mejora_09b).
=====================================================================================
Ruta: /configuracion-inicial  •  roles: {Rol.DIRECTOR}

Página SUELTA (sin app_layout/NAV) que el route_guard fuerza al director de un
tenant recién creado hasta que complete la configuración inicial.

Flujo (4 pasos):
  1. Identidad institucional  → institucion_service.actualizar
  2. Preferencias académicas  → preferencias_service.set (×4 claves)
  3. Módulos activos          → preferencias_service.set (×2 claves)
  4. Apariencia (colores)     → preferencias_service.set (×2 claves)
     + marcar_configuracion_inicial_completa → desbloquea gate

Reglas de capa:
  - NO importa src.domain.models.*  (DTOs desde módulos de servicio).
  - NO usa Container.*_repo()       (solo Container.*_service()).
  - Notificaciones: toast_warning / toast_success (no ui.notify).
  - Iconos: ThemeManager.icono (no ui.icon).
"""

from __future__ import annotations

import logging

from nicegui import app, ui

from container import Container
from src.interface.design.components.buttons import btn_ghost, btn_primary
from src.interface.design.components.toast import toast_success, toast_warning
from src.interface.design.theme import ThemeManager
from src.services.institucion_service import ActualizarInstitucionDTO
from src.services.preferencias_institucion_service import ActualizarPreferenciaDTO

logger = logging.getLogger("WIZARD_CONFIG")

# Opciones de selects — valores primitivos, sin importar enums del dominio.
_OPCIONES_JORNADA: list[str] = ["AM", "PM", "UNICA"]
_OPCIONES_TIPO: list[str] = ["publica", "privada"]
_OPCIONES_CAL: list[str] = ["A", "B"]
_TITULOS_PASO: list[str] = ["Identidad", "Preferencias", "Módulos", "Apariencia"]


# page-delegate: ruta registrada en main.py vía registrar_pagina (mejora_09b)
def configuracion_inicial_page() -> None:
    ui.add_body_html("<style>body{margin:0;padding:0;}</style>", shared=True)

    inst_id = app.storage.user.get("institucion_id")

    # ── Pre-cargar datos actuales para prefill ────────────────────────────────
    try:
        inst = Container.institucion_service().get(inst_id) if inst_id else None
    except Exception:
        inst = None

    try:
        prefs = Container.preferencias_service().get_dto(inst_id) if inst_id else None
    except Exception:
        prefs = None

    # ── Estado del paso activo ────────────────────────────────────────────────
    _paso: list[int] = [1]

    with ui.element("div").classes("andes-login-bg w-full"):
        with ui.element("div").classes("wizard-wide-card"):
            # ── Cabecera ──────────────────────────────────────────────────────
            with ui.element("div").classes("andes-login-logo"):
                with ui.element("div").classes("andes-login-icon-wrap"):
                    ThemeManager.icono("domain", size=40, color="var(--color-primary)")
                ui.label("Configuración inicial").classes("andes-login-logo-title")
                ui.label("Completa estos pasos para activar tu institución.").classes(
                    "andes-login-logo-subtitle"
                )

            # ── Indicador de pasos (pipeline) ─────────────────────────────────
            @ui.refreshable
            def _indicador() -> None:
                with ui.element("div").classes("pipeline"):
                    for i, titulo in enumerate(_TITULOS_PASO, 1):
                        if i > 1:
                            ui.label("→").classes("pipeline-sep")
                        cls = (
                            "pipeline-paso pipeline-paso-activo"
                            if _paso[0] == i
                            else "pipeline-paso"
                        )
                        with ui.element("div").classes(cls):
                            ui.label(str(i)).classes("pipeline-num")
                            ui.label(titulo)

            _indicador()

            # ── Contenidos de pasos ───────────────────────────────────────────
            # Todos se renderizan al cargar la página; solo el del paso activo
            # es visible. set_visibility() preserva los valores de los inputs.

            # -----------------------------------------------------------------
            # PASO 1 — Identidad institucional
            # -----------------------------------------------------------------
            with ui.column().classes("w-full") as _contenido_p1:
                with ui.element("div").classes("base-form-grid base-form-grid-2col"):
                    with ui.element("div").classes("base-form-field-col"):
                        with ui.element("div").classes("form-field-label-row"):
                            ui.label("Nombre oficial").classes("form-field-label")
                            ui.label("*").classes("form-field-req")
                        nombre_i = (
                            ui.input()
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        nombre_i.value = getattr(inst, "nombre_oficial", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        with ui.element("div").classes("form-field-label-row"):
                            ui.label("Rector/a").classes("form-field-label")
                            ui.label("*").classes("form-field-req")
                        rector_i = (
                            ui.input()
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        rector_i.value = getattr(inst, "rector", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        with ui.element("div").classes("form-field-label-row"):
                            ui.label("Municipio").classes("form-field-label")
                            ui.label("*").classes("form-field-req")
                        municipio_i = (
                            ui.input()
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        municipio_i.value = getattr(inst, "municipio", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Código DANE (12 dígitos)").classes("form-field-label")
                        dane_i = (
                            ui.input(placeholder="123456789012")
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        dane_i.value = getattr(inst, "codigo_dane", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Dirección").classes("form-field-label")
                        dir_i = (
                            ui.input()
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        dir_i.value = getattr(inst, "direccion", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Teléfono").classes("form-field-label")
                        tel_i = (
                            ui.input()
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        tel_i.value = getattr(inst, "telefono", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Email institucional").classes("form-field-label")
                        email_i = (
                            ui.input(placeholder="correo@institucion.edu.co")
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        email_i.value = getattr(inst, "email_institucional", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Resolución de aprobación").classes("form-field-label")
                        resol_i = (
                            ui.input()
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        resol_i.value = getattr(inst, "resolucion_aprobacion", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Lema institucional").classes("form-field-label")
                        lema_i = (
                            ui.input()
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        lema_i.value = getattr(inst, "lema", "") or ""

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Jornada principal").classes("form-field-label")
                        _jornada_raw = getattr(inst, "jornada_principal", None)
                        _jornada_val = _jornada_raw.value if _jornada_raw else None
                        jornada_i = (
                            ui.select(_OPCIONES_JORNADA, value=_jornada_val)
                            .classes("andes-input w-full")
                            .props("borderless dense clearable")
                        )

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Tipo de institución").classes("form-field-label")
                        _tipo_raw = getattr(inst, "tipo_institucion", None)
                        _tipo_val = _tipo_raw.value if _tipo_raw else None
                        tipo_i = (
                            ui.select(_OPCIONES_TIPO, value=_tipo_val)
                            .classes("andes-input w-full")
                            .props("borderless dense clearable")
                        )

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Calendario").classes("form-field-label")
                        _cal_raw = getattr(inst, "calendario", None)
                        _cal_val = _cal_raw.value if _cal_raw else None
                        cal_i = (
                            ui.select(_OPCIONES_CAL, value=_cal_val)
                            .classes("andes-input w-full")
                            .props("borderless dense clearable")
                        )

                def _guardar_paso1() -> None:
                    nombre = (nombre_i.value or "").strip()
                    rector = (rector_i.value or "").strip()
                    mun = (municipio_i.value or "").strip()
                    if not nombre or not rector or not mun:
                        toast_warning(
                            "Completa los campos obligatorios: "
                            "Nombre oficial, Rector/a y Municipio."
                        )
                        return
                    try:
                        dto = ActualizarInstitucionDTO(
                            nombre_oficial=nombre,
                            rector=rector,
                            municipio=mun,
                            codigo_dane=(dane_i.value or "").strip() or None,
                            direccion=(dir_i.value or "").strip() or None,
                            telefono=(tel_i.value or "").strip() or None,
                            email_institucional=(email_i.value or "").strip() or None,
                            resolucion_aprobacion=(resol_i.value or "").strip() or None,
                            lema=(lema_i.value or "").strip() or None,
                            jornada_principal=jornada_i.value or None,
                            tipo_institucion=tipo_i.value or None,
                            calendario=cal_i.value or None,
                        )
                        Container.institucion_service().actualizar(inst_id, dto)
                        _paso[0] = 2
                        _indicador.refresh()
                        _contenido_p1.set_visibility(False)
                        _contenido_p2.set_visibility(True)
                    except ValueError as exc:
                        toast_warning(str(exc))

                with ui.element("div").classes("form-row-actions u-mt-lg"):
                    btn_primary("Siguiente →", on_click=_guardar_paso1)

            # -----------------------------------------------------------------
            # PASO 2 — Preferencias académicas
            # -----------------------------------------------------------------
            with ui.column().classes("w-full") as _contenido_p2:
                with ui.element("div").classes("base-form-grid base-form-grid-2col"):
                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Nota mínima de aprobación").classes("form-field-label")
                        nota_apro_i = (
                            ui.number(
                                value=getattr(prefs, "nota_minima_aprobacion_default", 60.0)
                                or 60.0,
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
                                value=getattr(prefs, "numero_periodos_default", 4) or 4,
                                min=1,
                                max=6,
                                step=1,
                                format="%.0f",
                            )
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )

                    with ui.element("div").classes("base-form-field-col"):
                        ui.label("Nota mínima de escala").classes("form-field-label")
                        nota_min_i = (
                            ui.number(
                                value=getattr(prefs, "nota_minima_escala_default", 0.0) or 0.0,
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
                                value=getattr(prefs, "nota_maxima_escala_default", 100.0) or 100.0,
                                min=0,
                                max=100,
                                step=0.5,
                                format="%.1f",
                            )
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )

                def _guardar_paso2() -> None:
                    try:
                        min_apro = float(nota_apro_i.value or 0)
                        min_esc = float(nota_min_i.value or 0)
                        max_esc = float(nota_max_i.value or 100)
                        periodos = round(float(periodos_i.value or 4))
                        if min_esc >= max_esc:
                            toast_warning("La nota mínima de escala debe ser menor que la máxima.")
                            return
                        if not (min_esc <= min_apro <= max_esc):
                            toast_warning(
                                "La nota de aprobación debe estar dentro del rango de escala."
                            )
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
                            ActualizarPreferenciaDTO(
                                clave="numero_periodos_default", valor=str(periodos)
                            ),
                        )
                        _paso[0] = 3
                        _indicador.refresh()
                        _contenido_p2.set_visibility(False)
                        _contenido_p3.set_visibility(True)
                    except ValueError as exc:
                        toast_warning(str(exc))

                with ui.element("div").classes("form-row-between u-mt-lg"):

                    def _anterior_p2() -> None:
                        _paso[0] = 1
                        _indicador.refresh()
                        _contenido_p2.set_visibility(False)
                        _contenido_p1.set_visibility(True)

                    btn_ghost("← Anterior", on_click=_anterior_p2)
                    btn_primary("Siguiente →", on_click=_guardar_paso2)

            _contenido_p2.set_visibility(False)

            # -----------------------------------------------------------------
            # PASO 3 — Módulos activos
            # -----------------------------------------------------------------
            with ui.column().classes("w-full") as _contenido_p3:
                ui.label(
                    "Activa o desactiva los módulos de tu institución. "
                    "Podrás cambiarlos después desde la configuración."
                ).classes("andes-login-logo-subtitle u-mb-sm")

                with ui.element("div").classes("u-stack-sm"):
                    with ui.element("div").classes("form-row-between form-box"):
                        with ui.element("div").classes("u-stack-xs flex-1"):
                            ui.label("Módulo de convivencia").classes("section-subtitle")
                            ui.label(
                                "Gestión de observaciones, comportamiento y seguimiento."
                            ).classes("andes-login-logo-subtitle")
                        conv_toggle = ui.switch(
                            "", value=getattr(prefs, "modulo_convivencia_activo", True)
                        )

                    with ui.element("div").classes("form-row-between form-box"):
                        with ui.element("div").classes("u-stack-xs flex-1"):
                            ui.label("Módulo de alertas").classes("section-subtitle")
                            ui.label("Notificaciones y alertas de asistencia.").classes(
                                "andes-login-logo-subtitle"
                            )
                        alertas_toggle = ui.switch(
                            "", value=getattr(prefs, "modulo_alertas_activo", True)
                        )

                def _guardar_paso3() -> None:
                    try:
                        svc = Container.preferencias_service()
                        svc.set(
                            inst_id,
                            ActualizarPreferenciaDTO(
                                clave="modulo_convivencia_activo",
                                valor=str(bool(conv_toggle.value)).lower(),
                            ),
                        )
                        svc.set(
                            inst_id,
                            ActualizarPreferenciaDTO(
                                clave="modulo_alertas_activo",
                                valor=str(bool(alertas_toggle.value)).lower(),
                            ),
                        )
                        _paso[0] = 4
                        _indicador.refresh()
                        _contenido_p3.set_visibility(False)
                        _contenido_p4.set_visibility(True)
                    except ValueError as exc:
                        toast_warning(str(exc))

                with ui.element("div").classes("form-row-between u-mt-lg"):

                    def _anterior_p3() -> None:
                        _paso[0] = 2
                        _indicador.refresh()
                        _contenido_p3.set_visibility(False)
                        _contenido_p2.set_visibility(True)

                    btn_ghost("← Anterior", on_click=_anterior_p3)
                    btn_primary("Siguiente →", on_click=_guardar_paso3)

            _contenido_p3.set_visibility(False)

            # -----------------------------------------------------------------
            # PASO 4 — Apariencia (colores)
            # -----------------------------------------------------------------
            with ui.column().classes("w-full") as _contenido_p4:
                ui.label(
                    "Define los colores principales de tu institución en la plataforma."
                ).classes("andes-login-logo-subtitle u-mb-sm")

                with ui.element("div").classes("u-stack-sm"):
                    with ui.element("div").classes("form-row-between form-box"):
                        ui.label("Color primario").classes("section-subtitle")
                        color_prim_i = ui.color_input(
                            value=getattr(prefs, "color_primario", None) or ""
                        )

                    with ui.element("div").classes("form-row-between form-box"):
                        ui.label("Color secundario").classes("section-subtitle")
                        color_sec_i = ui.color_input(
                            value=getattr(prefs, "color_secundario", None) or ""
                        )

                def _finalizar() -> None:
                    try:
                        Container.aprovisionamiento_service().finalizar_configuracion_inicial(
                            inst_id,
                            color_primario=(color_prim_i.value or "").strip() or None,
                            color_secundario=(color_sec_i.value or "").strip() or None,
                        )
                        app.storage.user["institucion_config_completa"] = True
                        toast_success("¡Configuración completada! Ya puedes usar la plataforma.")
                        ui.navigate.to("/inicio")
                    except ValueError as exc:
                        toast_warning(str(exc))

                with ui.element("div").classes("form-row-between u-mt-lg"):

                    def _anterior_p4() -> None:
                        _paso[0] = 3
                        _indicador.refresh()
                        _contenido_p4.set_visibility(False)
                        _contenido_p3.set_visibility(True)

                    btn_ghost("← Anterior", on_click=_anterior_p4)
                    btn_primary("Finalizar configuración", on_click=_finalizar)

            _contenido_p4.set_visibility(False)

            # ── Pie ───────────────────────────────────────────────────────────
            ui.link("Cerrar sesión", "/logout").classes("andes-login-footer w-full")


__all__ = ["configuracion_inicial_page"]
