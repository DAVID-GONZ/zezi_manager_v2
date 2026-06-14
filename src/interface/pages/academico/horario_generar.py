"""
src/interface/pages/academico/horario_generar.py
=====================================================
Página de generación de horarios.
Ruta: /academico/generar-horario
Acceso: admin, director, coordinador

Secciones:
  1. Lista de configuraciones de generación (nombre, plantilla, grupos, estado).
  2. Crear / editar configuración con sliders de pesos.
  3. Ejecución del motor de generación (con estado de carga).
  4. Métricas de calidad del resultado + badge de validez.
  5. Incidencias del lote.
  6. Vista previa de la parrilla con toggle de perspectiva.
  7. Activación del escenario generado.

Reglas de capas:
  - Solo usa Container.*
  - No importa repositorios ni src.db ni src.domain.models.*
  - Todo estilo se define con clases CSS (domain/horario_generar.css);
    los iconos van vía ThemeManager.icono(Icons.X).
"""
from __future__ import annotations

import logging
from typing import Any

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary,
    btn_secondary,
    btn_danger,
    btn_ghost,
)
from src.interface.design.components import (
    confirm_dialog,
    empty_state,
    form_dialog,
    stat_card,
    status_badge,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.pages.academico.parrilla_widget import render_parrilla

logger = logging.getLogger("GENERADOR_HORARIO")

# Variantes de badge por estado de la configuración.
_ESTADO_BADGE = {
    "borrador": ("Borrador", "info"),
    "generado": ("Generado", "warning"),
    "aplicado": ("Aplicado", "success"),
}

# Definición de los tres pesos editables del motor.
_PESOS_DEF = [
    ("huecos",       "Huecos",       "Penaliza ventanas vacías en grupos y docentes."),
    ("distribucion", "Distribución", "Premia repartir las asignaturas a lo largo de la semana."),
    ("compactacion", "Compactación", "Premia jornadas compactas para los docentes."),
]


@ui.page("/academico/generar-horario")
def horario_generar_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director", "coordinador"):
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    if not ctx.anio_id or not ctx.periodo_id:
        toast_warning("Selecciona primero un año lectivo y un periodo activo")
        ui.navigate.to("/inicio")
        return

    _s: dict[str, Any] = {
        "configs": [],
        "config_sel": None,        # objeto ConfigGeneracion seleccionado
        "plantillas": [],
        "grupos": [],
        "resultado": None,         # ResultadoGeneracionDTO de la última corrida
        "datos_preview": None,     # datos de parrilla del escenario generado
        "perspectiva": "Grupo",    # Grupo | Docente | Sala
        "eje_sel": None,           # elemento concreto del eje en la preview
        "generando": False,        # estado de carga del motor
    }
    _generar_config_timer = ui.timer(0.1, lambda: None, active=False, once=True)

    # ── Carga de catálogos ────────────────────────────────────────────────────
    def _mapa_plantillas() -> dict:
        return {p.id: p.nombre for p in _s["plantillas"] if getattr(p, "id", None) is not None}

    def _cargar_plantillas() -> None:
        try:
            _s["plantillas"] = Container.infraestructura_service().listar_plantillas()
        except Exception as exc:
            logger.error("Error cargando plantillas: %s", exc)
            _s["plantillas"] = []

    def _cargar_grupos() -> None:
        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error cargando grupos: %s", exc)
            _s["grupos"] = []

    def _cargar_configs() -> None:
        try:
            _s["configs"] = Container.infraestructura_service().listar_configs_generacion(
                ctx.periodo_id
            )
        except Exception as exc:
            logger.error("Error cargando configuraciones de generación: %s", exc)
            _s["configs"] = []
        # Re-sincronizar el objeto seleccionado con la versión recién cargada.
        sel = _s.get("config_sel")
        if sel is not None and getattr(sel, "id", None) is not None:
            _s["config_sel"] = next(
                (c for c in _s["configs"] if c.id == sel.id), None
            )

    # ── Selección ─────────────────────────────────────────────────────────────
    def _seleccionar_config(config_id: int | None) -> None:
        if config_id is None:
            _s["config_sel"] = None
        else:
            _s["config_sel"] = next((c for c in _s["configs"] if c.id == config_id), None)
        _s["resultado"] = None
        _s["datos_preview"] = None
        _s["eje_sel"] = None
        contenido_refreshable.refresh()

    # ── Crear / editar configuración ──────────────────────────────────────────
    def _config_dialog(config: Any | None = None) -> None:
        if not _s["plantillas"]:
            toast_warning("Primero debes crear una plantilla horaria en Ajustes → Plantillas horarias")
            return

        es_edicion = config is not None
        plantilla_opts = _mapa_plantillas()
        grupo_opts = {g.id: g.codigo for g in _s["grupos"]}

        # Valores iniciales (edición) o por defecto (creación).
        nombre_ini = getattr(config, "nombre", "") if es_edicion else ""
        plantilla_ini = getattr(config, "plantilla_id", None) if es_edicion else None
        grupos_ini = list(getattr(config, "grupos", []) or []) if es_edicion else []
        pesos_obj = getattr(config, "pesos", None) if es_edicion else None
        pesos_val = {
            "huecos": getattr(pesos_obj, "huecos", 1.0) if pesos_obj else 1.0,
            "distribucion": getattr(pesos_obj, "distribucion", 1.0) if pesos_obj else 1.0,
            "compactacion": getattr(pesos_obj, "compactacion", 0.5) if pesos_obj else 0.5,
        }

        # form_dialog/base_form no soportan sliders → construimos un panel propio.
        with ui.dialog() as dlg, ui.card().classes("andes-card form-dialog-card max-w-lg"):
            titulo = "Editar configuración" if es_edicion else "Nueva configuración de generación"
            ui.label(titulo).classes("font-h3 form-dialog-title")

            in_nombre = ui.input(
                label="Nombre *", value=nombre_ini,
            ).classes("andes-input w-full").props("outlined")

            sel_plantilla = ui.select(
                options=plantilla_opts, label="Plantilla *",
                value=plantilla_ini,
            ).classes("andes-input w-full").props("outlined")

            sel_grupos = ui.select(
                options=grupo_opts, label="Grupos (vacío = todos)",
                value=grupos_ini, multiple=True,
            ).classes("andes-input w-full").props("outlined use-chips")

            # Panel de pesos con sliders.
            ui.label("Pesos del motor").classes("font-h3 q-mt-md")
            sliders: dict[str, Any] = {}
            with ui.element("div").classes("gen-pesos-grid q-mt-sm"):
                for key, label, hint in _PESOS_DEF:
                    with ui.element("div").classes("gen-peso-item"):
                        with ui.element("div").classes("gen-peso-head"):
                            ui.label(label).classes("gen-peso-label")
                            valor_lbl = ui.label(f"{pesos_val[key]:.1f}").classes("gen-peso-valor")
                        sl = ui.slider(
                            min=0.0, max=2.0, step=0.1, value=float(pesos_val[key]),
                        ).props("label")
                        sl.on(
                            "update:model-value",
                            lambda e, lbl=valor_lbl: lbl.set_text(f"{float(e.args):.1f}"),
                        )
                        ui.label(hint).classes("gen-peso-hint")
                        sliders[key] = sl

            def _guardar() -> None:
                nombre = str(in_nombre.value or "").strip()
                plantilla_id = sel_plantilla.value
                grupos = list(sel_grupos.value or [])
                pesos = {k: round(float(sliders[k].value), 1) for k in sliders}
                if not nombre:
                    toast_warning("El nombre de la configuración es obligatorio")
                    return
                if not plantilla_id:
                    toast_warning("Selecciona una plantilla")
                    return
                try:
                    infra = Container.infraestructura_service()
                    if es_edicion:
                        infra.actualizar_config_generacion(
                            config.id,
                            nombre=nombre,
                            plantilla_id=plantilla_id,
                            grupos=grupos,
                            pesos={
                                "huecos": pesos["huecos"],
                                "distribucion": pesos["distribucion"],
                                "compactacion": pesos["compactacion"],
                            },
                        )
                        toast_success("Configuración actualizada")
                    else:
                        infra.crear_config_generacion(
                            nombre=nombre,
                            periodo_id=ctx.periodo_id,
                            anio_id=ctx.anio_id,
                            plantilla_id=plantilla_id,
                            grupos=grupos if grupos else None,
                            pesos=pesos,
                        )
                        toast_success("Configuración creada")
                    dlg.close()
                    _cargar_configs()
                    contenido_refreshable.refresh()
                except Exception as exc:
                    logger.error("Error guardando configuración de generación: %s", exc)
                    toast_error("No se pudo guardar la configuración")

            with ui.row().classes("base-form-footer w-full gap-2 justify-end q-mt-md"):
                btn_secondary("Cancelar", on_click=dlg.close)
                btn_primary("Guardar", on_click=_guardar)

        dlg.open()

    def _duplicar_config(config_id: int) -> None:
        try:
            Container.infraestructura_service().duplicar_config_generacion(config_id)
            toast_success("Configuración duplicada")
            _cargar_configs()
            contenido_refreshable.refresh()
        except Exception as exc:
            logger.error("Error duplicando configuración: %s", exc)
            toast_error("No se pudo duplicar la configuración")

    def _eliminar_config(config: Any) -> None:
        def _confirmar() -> None:
            try:
                Container.infraestructura_service().eliminar_config_generacion(config.id)
                toast_success("Configuración eliminada")
                if _s.get("config_sel") and _s["config_sel"].id == config.id:
                    _seleccionar_config(None)
                    return
                _cargar_configs()
                contenido_refreshable.refresh()
            except Exception as exc:
                logger.error("Error eliminando configuración: %s", exc)
                toast_error("No se pudo eliminar la configuración")

        confirm_dialog(
            titulo="Eliminar configuración",
            mensaje=f"¿Eliminar «{getattr(config, 'nombre', '')}»? Esta acción no se puede deshacer.",
            on_confirm=_confirmar,
            variante="danger",
            texto_confirmar="Eliminar",
        )

    # ── Vista previa ──────────────────────────────────────────────────────────
    def _cargar_preview() -> None:
        resultado = _s.get("resultado")
        escenario_id = getattr(resultado, "escenario_id", None) if resultado else None
        if not escenario_id:
            _s["datos_preview"] = None
            return
        try:
            _s["datos_preview"] = Container.horario_service().datos_parrilla(escenario_id)
        except Exception as exc:
            logger.error("Error cargando datos de parrilla de vista previa: %s", exc)
            _s["datos_preview"] = None

    def _cambiar_perspectiva(valor: str) -> None:
        _s["perspectiva"] = valor
        _s["eje_sel"] = None
        contenido_refreshable.refresh()

    def _cambiar_eje(valor) -> None:
        _s["eje_sel"] = valor
        contenido_refreshable.refresh()

    # ── Ejecución del motor ───────────────────────────────────────────────────
    def _generar_config() -> None:
        config = _s.get("config_sel")
        if not config or getattr(config, "id", None) is None:
            toast_warning("Selecciona una configuración para generar")
            return
        # Mostrar estado de carga y diferir el trabajo pesado para que se pinte.
        _s["generando"] = True
        contenido_refreshable.refresh()

        def _trabajo() -> None:
            try:
                resultado = Container.generador_horario_service().generar(
                    config.id,
                    crear_escenario=True,
                    optimizar=True,
                )
                _s["resultado"] = resultado
                _s["eje_sel"] = None
                _cargar_configs()
                _cargar_preview()
                if getattr(resultado, "valido", False):
                    toast_success("Generación completada")
                else:
                    toast_warning("Generación parcial: revisa las incidencias")
            except Exception as exc:
                logger.error("Error ejecutando generador: %s", exc)
                toast_error("Error al generar el horario")
            finally:
                _s["generando"] = False
                contenido_refreshable.refresh()

        if _generar_config_timer.active:
            _generar_config_timer.cancel(with_current_invocation=False)
        _generar_config_timer.callback = _trabajo
        _generar_config_timer.active = True

    # ── Activación del escenario ──────────────────────────────────────────────
    def _activar_escenario(config: Any, escenario_id: int) -> None:
        def _confirmar() -> None:
            try:
                infra = Container.infraestructura_service()
                infra.activar_escenario(escenario_id)
                # Transicionar la config a "aplicado" si su estado lo permite.
                estado = getattr(config, "estado", "borrador")
                if estado == "generado":
                    try:
                        infra.cambiar_estado_config(config.id, "aplicado")
                    except Exception as exc:
                        logger.warning("No se pudo transicionar config a aplicado: %s", exc)
                toast_success("Escenario activado")
                _cargar_configs()
                contenido_refreshable.refresh()
            except Exception as exc:
                logger.error("Error activando escenario: %s", exc)
                toast_error("No se pudo activar el escenario")

        confirm_dialog(
            titulo="Activar escenario",
            mensaje="Al activar este escenario se desactivarán los demás del año lectivo. ¿Continuar?",
            on_confirm=_confirmar,
            variante="info",
            texto_confirmar="Activar",
        )

    _cargar_plantillas()
    _cargar_grupos()
    _cargar_configs()

    # ── Render ────────────────────────────────────────────────────────────────
    def _render_lista() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("gen-section-head"):
                ui.label("Configuraciones de generación").classes("text-subtitle1 font-semibold")
                with ui.row().classes("gap-2 flex-wrap"):
                    btn_primary("Nueva configuración", icon=Icons.ADD,
                                on_click=lambda: _config_dialog(None))
                    btn_secondary(
                        "Recargar", icon=Icons.REFRESH,
                        on_click=lambda: (_cargar_configs(), contenido_refreshable.refresh()),
                    )

            if not _s["configs"]:
                empty_state(
                    icono=Icons.AUTO_MODE,
                    titulo="Sin configuraciones de generación",
                    descripcion="Crea una configuración para generar un horario.",
                )
                return

            mapa_pl = _mapa_plantillas()
            sel = _s.get("config_sel")
            sel_id = getattr(sel, "id", None) if sel else None

            with ui.element("div").classes("overflow-auto"):
                with ui.element("table").classes("gen-config-table"):
                    with ui.element("thead"):
                        with ui.element("tr"):
                            for col in ("Nombre", "Plantilla", "Grupos", "Estado", "Acciones"):
                                ui.element("th").text = col
                    with ui.element("tbody"):
                        for config in _s["configs"]:
                            grupo_count = len(getattr(config, "grupos", []) or [])
                            plantilla_nombre = mapa_pl.get(
                                getattr(config, "plantilla_id", None), "—"
                            )
                            estado = getattr(config, "estado", "borrador")
                            badge_txt, badge_var = _ESTADO_BADGE.get(
                                estado, (estado.title(), "neutral")
                            )
                            fila_cls = "gen-config-row"
                            if config.id == sel_id:
                                fila_cls += " gen-config-sel"
                            with ui.element("tr").classes(fila_cls):
                                ui.element("td").text = getattr(config, "nombre", "")
                                ui.element("td").text = str(plantilla_nombre)
                                with ui.element("td"):
                                    ui.label(str(grupo_count) if grupo_count else "Todos")
                                with ui.element("td"):
                                    status_badge(badge_txt, variante=badge_var)
                                with ui.element("td"):
                                    with ui.element("div").classes("gen-config-acciones"):
                                        btn_secondary(
                                            "Seleccionar", size="sm", icon=Icons.CHECK,
                                            on_click=lambda _, c=config: _seleccionar_config(c.id),
                                        )
                                        btn_ghost(
                                            "Editar", size="sm", icon=Icons.EDIT,
                                            on_click=lambda _, c=config: _config_dialog(c),
                                        )
                                        btn_ghost(
                                            "Duplicar", size="sm", icon="content_copy",
                                            on_click=lambda _, c=config: _duplicar_config(c.id),
                                        )
                                        btn_danger(
                                            "Eliminar", size="sm", icon=Icons.DELETE,
                                            on_click=lambda _, c=config: _eliminar_config(c),
                                        )

    def _render_detalle() -> None:
        config = _s.get("config_sel")
        if not config:
            return

        estado = getattr(config, "estado", "borrador")
        badge_txt, badge_var = _ESTADO_BADGE.get(estado, (estado.title(), "neutral"))
        resultado = _s.get("resultado")
        escenario_id = getattr(resultado, "escenario_id", None) if resultado else None
        escenario_destino = getattr(config, "escenario_destino_id", None)
        valido = bool(getattr(resultado, "valido", False)) if resultado else False

        with ui.element("div").classes("panel-card q-mt-md"):
            with ui.element("div").classes("gen-section-head"):
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    ui.label(getattr(config, "nombre", "")).classes("text-subtitle1 font-semibold")
                    status_badge(badge_txt, variante=badge_var)
                with ui.row().classes("gap-2 flex-wrap"):
                    btn_primary(
                        "Generar horario", icon="play_arrow",
                        on_click=_generar_config, disabled=_s["generando"],
                    )
                    # Activar: solo si la corrida fue válida o la config ya tiene
                    # escenario destino en estado "generado".
                    puede_activar_resultado = bool(escenario_id) and valido
                    puede_activar_config = bool(escenario_destino) and estado == "generado"
                    if puede_activar_resultado or puede_activar_config:
                        target = escenario_id if puede_activar_resultado else escenario_destino
                        btn_secondary(
                            "Activar este escenario", icon="check_circle",
                            on_click=lambda c=config, e=target: _activar_escenario(c, e),
                        )

            # Estado de carga.
            if _s["generando"]:
                with ui.element("div").classes("gen-loading"):
                    ui.spinner(size="lg")
                    ui.label("Generando horario… esto puede tardar unos segundos.")
                return

            if not resultado:
                ui.label(
                    "Pulsa «Generar horario» para ejecutar el motor sobre esta configuración."
                ).classes("text-secondary text-sm")
                return

            _render_resultado(resultado)

    def _render_resultado(resultado: Any) -> None:
        total = int(getattr(resultado, "total_requeridos", 0) or 0)
        colocados = int(getattr(resultado, "colocados", 0) or 0)
        no_colocados = int(getattr(resultado, "no_colocados", 0) or 0)
        pct = round(colocados / total * 100, 1) if total else 0.0
        valido = bool(getattr(resultado, "valido", False))
        metricas = getattr(resultado, "metricas", None)
        huecos = (
            int(getattr(metricas, "huecos_grupo", 0) or 0)
            + int(getattr(metricas, "huecos_docente", 0) or 0)
            if metricas else 0
        )
        costo_final = float(getattr(metricas, "costo_final", 0.0) or 0.0) if metricas else 0.0

        # Badge de validez.
        with ui.row().classes("items-center gap-2 q-mb-sm"):
            ui.label("Resultado de la generación").classes("text-subtitle2 font-semibold")
            if valido:
                status_badge("Válido", variante="success")
            elif colocados > 0:
                status_badge("Parcial", variante="warning")
            else:
                status_badge("Inválido", variante="error")

        # KPIs.
        with ui.element("div").classes("gen-kpi-row"):
            stat_card("Requeridos", total, "list_alt", variante="info")
            stat_card("Colocados", colocados, "check_circle", variante="success")
            stat_card(
                "No colocados", no_colocados, "report",
                variante="error" if no_colocados else "success",
            )
            stat_card("% Colocado", f"{pct}%", "percent",
                      variante="success" if pct >= 100 else "warning")
            stat_card("Huecos", huecos, "grid_off",
                      variante="warning" if huecos else "success")
            stat_card("Costo final", f"{costo_final:.1f}", "speed", variante="primary")

        # Incidencias.
        incidencias = list(getattr(resultado, "incidencias", []) or [])
        if incidencias:
            with ui.element("div").classes("gen-incidencias q-mt-md"):
                with ui.row().classes("items-center gap-2"):
                    ThemeManager.icono(Icons.WARNING, size=18, color="var(--color-warning)")
                    ui.label(f"Incidencias ({len(incidencias)})").classes(
                        "text-sm font-semibold"
                    )
                for texto in incidencias:
                    with ui.element("div").classes("gen-incidencia-item"):
                        ui.label(str(texto))

        # Vista previa de la parrilla.
        if _s.get("datos_preview"):
            _render_preview()

    def _render_preview() -> None:
        datos = _s["datos_preview"]
        perspectiva = _s["perspectiva"]
        with ui.element("div").classes("panel-card q-mt-md"):
            ui.label("Vista previa del escenario generado").classes(
                "text-subtitle2 font-semibold"
            )
            with ui.element("div").classes("parrilla-toolbar q-mt-sm"):
                ui.toggle(
                    ["Grupo", "Docente", "Sala"],
                    value=perspectiva,
                    on_change=lambda e: _cambiar_perspectiva(e.value),
                )
                eje_opts = _opciones_eje(datos, perspectiva)
                if eje_opts:
                    eje_sel = _s["eje_sel"]
                    if eje_sel not in eje_opts:
                        eje_sel = next(iter(eje_opts))
                        _s["eje_sel"] = eje_sel
                    ui.select(
                        label=perspectiva,
                        options=eje_opts,
                        value=eje_sel,
                        on_change=lambda e: _cambiar_eje(e.value),
                    ).classes("w-44")

            render_parrilla(
                datos=datos,
                perspectiva=perspectiva,
                eje_sel=_s["eje_sel"],
            )

    def _opciones_eje(datos: dict, perspectiva: str) -> dict:
        opts: dict = {}
        for c in datos.get("celdas", []):
            if perspectiva == "Grupo":
                opts.setdefault(c["grupo_id"], c["grupo_codigo"])
            elif perspectiva == "Docente":
                opts.setdefault(c["usuario_id"], c["docente_nombre"])
            else:
                opts.setdefault(c["sala"], c["sala"])
        return dict(sorted(opts.items(), key=lambda kv: str(kv[1])))

    @ui.refreshable
    def contenido_refreshable() -> None:
        _render_lista()
        _render_detalle()

    app_layout(
        ctx,
        contenido_refreshable,
        page_titulo="Generar horario",
        page_subtitulo="Configura y ejecuta el generador de horarios",
        page_icono=Icons.AUTO_MODE,
    )


__all__ = ["horario_generar_page"]
