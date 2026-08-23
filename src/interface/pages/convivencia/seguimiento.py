"""
src/interface/pages/convivencia/seguimiento.py
==============================================
Hub de Seguimiento (maestro-detalle) — ZECI Manager v2.0.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Los DTOs se acceden a través del módulo de servicios (src.services.*).
  Solo usa Container (servicios) e imports de la capa de interfaz.

Patrón de selector (igual que comportamiento/observaciones):
  El inline_periodo_grupo va FUERA del @ui.refreshable.
  on_sel_change actualiza _s y llama panel_hub.refresh().
  El refreshable nunca re-renderiza el selector.

Flujo:
  1. Guard de autenticación → redirige a /login si no hay sesión (SIN gate de rol
     a la entrada: la ruta es de aula; la sección Alertas/360° se limita a
     dir/coord dentro de la página).
  2. inline_periodo_grupo pre-selecciona periodo y grupo.
  3. on_sel_change carga estudiantes + resumen_convivencia_grupo (una sola llamada).
  4. Maestro (page-col-main): lista de ResumenConvivenciaDTO por estudiante.
  5. Detalle (page-col-side, al seleccionar estudiante):
     - Fila de counter_card (nota, #obs, #registros neg, estado alerta).
     - mini_chart con serie_notas_comportamiento (evolución).
     - Lista de observaciones con acciones de gestión (migradas de observaciones).
     - Lista de registros de comportamiento con badges por tipo.
     - Sección Alertas + Vista 360° (solo dir/coord).
"""

from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    confirm_dialog,
    counter_card,
    empty_state,
    form_dialog,
    mini_chart,
    stat_card,
    status_badge,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import (
    btn_danger,
    btn_ghost,
    btn_primary,
    btn_secondary,
)
from src.interface.design.components.inline_selectors import inline_periodo_grupo
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.interface.presenters.convivencia.seguimiento_presenter import SeguimientoPresenter
from src.services.convivencia_service import (
    FiltroConvivenciaDTO,
    NuevaAlertaSeguimientoDTO,
    NuevaObservacionDTO,
)

logger = logging.getLogger("SEGUIMIENTO")

_ROLES_ALERTAS = ("director", "coordinador")

_NIVEL_DISPLAY: dict[str, str] = {
    "advertencia": "Advertencia",
    "critica": "Crítica",
    "info": "Información",
}

# Presentación de registros de comportamiento — strings literales (NO importan
# TipoRegistro del dominio). Espejo de comportamiento.py (_TIPOS_DISPLAY / _CLASE_BADGE).
_TIPOS_DISPLAY: dict[str, str] = {
    "fortaleza": "Fortaleza",
    "dificultad": "Dificultad",
    "compromiso": "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo": "Descargo",
}

_CLASE_BADGE: dict[str, str] = {
    "fortaleza": "badge-fortaleza",
    "dificultad": "badge-dificultad",
    "compromiso": "badge-compromiso",
    "citacion_acudiente": "badge-citacion",
    "descargo": "badge-descargo",
}


# ── Estado ────────────────────────────────────────────────────────────────────


def _estado_inicial() -> dict:
    return {
        # sel_* gestionados por el inline selector
        "sel_periodo_id": None,
        "sel_periodo_nombre": "",
        "sel_grupo_id": None,
        "sel_grupo_nombre": "",
        "anio_id": None,
        "estudiantes": [],  # list[Estudiante]
        "resumen": [],  # list[ResumenConvivenciaDTO]
        "docentes": [],  # list[Usuario]
        # detalle del estudiante seleccionado
        "sel_estudiante_id": None,
        "sel_seccion": "evolucion",  # evolucion|observaciones|registros|alertas
        "serie": [],  # list[PuntoSerieDTO]
        "observaciones_est": [],  # list[ObservacionPeriodo]
        "registros_est": [],  # list[RegistroComportamiento]
        "resultado_360": None,
        "alertas": [],  # list[Alerta] del estudiante
    }


def _cargar_anio(_s: dict) -> None:
    try:
        config = Container.configuracion_service().get_activa()
        _s["anio_id"] = getattr(config, "id", None) if config else None
    except Exception as exc:
        logger.warning("Sin configuración activa: %s", exc)
        _s["anio_id"] = None


def _cargar_docentes(_s: dict) -> None:
    try:
        _s["docentes"] = Container.usuario_service().listar_docentes()
    except Exception as exc:
        logger.warning("No se pudieron cargar docentes: %s", exc)
        _s["docentes"] = []


def _cargar_categorias() -> tuple[dict, dict]:
    """Carga categorías activas: (opciones {id: nombre}, es_comportamental {id: bool})."""
    try:
        categorias = Container.convivencia_service().listar_categorias(solo_activas=True)
        opciones = {getattr(c, "id", None): getattr(c, "nombre", "") for c in categorias}
        es_comportamental = {
            getattr(c, "id", None): bool(getattr(c, "es_comportamental", False)) for c in categorias
        }
        return opciones, es_comportamental
    except Exception as exc:
        logger.warning("Error cargando categorías: %s", exc)
        return {}, {}


def _cargar_resumen(_s: dict) -> None:
    grupo_id = _s["sel_grupo_id"]
    periodo_id = _s["sel_periodo_id"]
    if not grupo_id or not periodo_id:
        _s["resumen"] = []
        return
    try:
        _s["resumen"] = Container.convivencia_service().resumen_convivencia_grupo(
            int(grupo_id), int(periodo_id)
        )
    except Exception as exc:
        logger.error("Error cargando resumen de convivencia: %s", exc)
        _s["resumen"] = []


def _cargar_detalle(_s: dict, ctx: SessionContext) -> None:
    """Carga serie, observaciones y registros del estudiante seleccionado."""
    est_id = _s["sel_estudiante_id"]
    periodo_id = _s["sel_periodo_id"]
    if not est_id:
        _s["serie"] = []
        _s["observaciones_est"] = []
        _s["registros_est"] = []
        _s["alertas"] = []
        return

    # Serie de notas de comportamiento (evolución por periodos del año).
    try:
        if _s["anio_id"]:
            _s["serie"] = Container.convivencia_service().serie_notas_comportamiento(
                int(est_id), int(_s["anio_id"])
            )
        else:
            _s["serie"] = []
    except Exception as exc:
        logger.warning("Error cargando serie de notas: %s", exc)
        _s["serie"] = []

    # Observaciones del estudiante en el periodo.
    try:
        _s["observaciones_est"] = Container.convivencia_service().listar_observaciones(
            estudiante_id=int(est_id),
            periodo_id=int(periodo_id) if periodo_id else None,
            solo_publicas=False,
            usuario_id=ctx.usuario_id,
            usuario_rol=ctx.usuario_rol,
        )
    except Exception as exc:
        logger.error("Error cargando observaciones: %s", exc)
        _s["observaciones_est"] = []

    # Registros de comportamiento del estudiante en el periodo.
    try:
        filtro = FiltroConvivenciaDTO(
            estudiante_id=int(est_id),
            periodo_id=int(periodo_id) if periodo_id else None,
        )
        _s["registros_est"] = Container.convivencia_service().listar_registros(filtro)
    except Exception as exc:
        logger.error("Error cargando registros: %s", exc)
        _s["registros_est"] = []


def _cargar_alertas(_s: dict) -> None:
    """Carga alertas SEGUIMIENTO_REQUERIDO del estudiante seleccionado."""
    from src.services.alerta_service import FiltroAlertasDTO, TipoAlerta

    est_id = _s["sel_estudiante_id"]
    if not est_id:
        _s["alertas"] = []
        return
    try:
        filtro = FiltroAlertasDTO(
            estudiante_id=int(est_id),
            tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO,
            solo_pendientes=False,
        )
        _s["alertas"] = Container.alerta_service().listar_alertas(filtro)
    except Exception as exc:
        logger.error("Error cargando alertas: %s", exc)
        _s["alertas"] = []


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resumen_estudiante(_s: dict, est_id: int | None):
    for r in _s["resumen"]:
        if getattr(r, "estudiante_id", None) == est_id:
            return r
    return None


def _nombre_estudiante(_s: dict, est_id: int | None) -> str:
    r = _resumen_estudiante(_s, est_id)
    if r is not None:
        return getattr(r, "nombre", str(est_id))
    for est in _s["estudiantes"]:
        if getattr(est, "id", None) == est_id:
            return f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
    return str(est_id) if est_id else "—"


def _nombre_docente(_s: dict, docente_id: int | None) -> str:
    for d in _s["docentes"]:
        if getattr(d, "id", None) == docente_id:
            return f"{getattr(d, 'apellido', '')} {getattr(d, 'nombre', '')}".strip() or getattr(
                d, "email", str(docente_id)
            )
    return str(docente_id) if docente_id else "—"


def _texto_truncado(texto: str, max_chars: int = 80) -> str:
    if not texto:
        return ""
    return texto[:max_chars] + "..." if len(texto) > max_chars else texto


def _fila_observacion(obs, opciones_cat: dict) -> dict:
    cat_id = getattr(obs, "categoria_id", None)
    texto = getattr(obs, "texto", "")
    es_publica = getattr(obs, "es_publica", True)
    fecha = getattr(obs, "fecha_registro", None)
    fecha_str = str(fecha)[:10] if fecha is not None else ""
    return {
        "id": getattr(obs, "id", None),
        "estudiante_id": getattr(obs, "estudiante_id", None),
        "asignacion_id": getattr(obs, "asignacion_id", None),
        "periodo_id": getattr(obs, "periodo_id", None),
        "categoria_id": cat_id,
        "categoria_nombre": opciones_cat.get(cat_id, "Sin categoría"),
        "registro_comportamiento_id": getattr(obs, "registro_comportamiento_id", None),
        "texto_completo": texto,
        "texto": _texto_truncado(texto),
        "es_publica": es_publica,
        "fecha": fecha_str,
    }


def _fila_registro(reg) -> dict:
    tipo_raw = str(getattr(reg, "tipo", "")).lower()
    if "." in tipo_raw:
        tipo_raw = tipo_raw.split(".")[-1]
    return {
        "id": getattr(reg, "id", None),
        "fecha": str(getattr(reg, "fecha", ""))[:10],
        "tipo_raw": tipo_raw,
        "tipo_display": _TIPOS_DISPLAY.get(tipo_raw, tipo_raw),
        "tipo_badge_class": _CLASE_BADGE.get(tipo_raw, "badge-neutral"),
        "descripcion": str(getattr(reg, "descripcion", "")),
    }


def _construir_filas_alertas(_s: dict) -> list[dict]:
    filas = []
    for alerta in _s["alertas"]:
        nivel_raw = str(getattr(alerta, "nivel", "")).lower()
        if "." in nivel_raw:
            nivel_raw = nivel_raw.split(".")[-1]
        filas.append(
            {
                "fecha": str(getattr(alerta, "fecha_generacion", ""))[:10],
                "descripcion": str(getattr(alerta, "descripcion", "")),
                "nivel_raw": nivel_raw,
                "nivel_display": _NIVEL_DISPLAY.get(nivel_raw, nivel_raw),
                "destinatario": _nombre_docente(_s, getattr(alerta, "usuario_destino_id", None)),
                "estado": "Resuelta" if getattr(alerta, "resuelta", False) else "Pendiente",
            }
        )
    return filas


# ── Página ────────────────────────────────────────────────────────────────────


# page-delegate: ruta y guard registrados en main.py
def seguimiento_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    puede_alertas = ctx.usuario_rol in _ROLES_ALERTAS

    presenter = SeguimientoPresenter()
    _s = presenter.estado  # misma referencia: los refreshables leen el estado del presenter
    _cargar_anio(_s)
    _cargar_docentes(_s)

    # ── Handlers de selección ────────────────────────────────────────────────

    def on_estudiante_change(est_id) -> None:
        presenter.seleccionar_estudiante(est_id)
        _cargar_detalle(_s, ctx)
        _cargar_alertas(_s)
        panel_hub.refresh()

    def _set_seccion(sec: str) -> None:
        """Cambia la sección visible del detalle (tabs por botones)."""
        presenter.set_seccion(sec)
        panel_hub.refresh()

    # ── Handlers de gestión de observaciones (migrados de observaciones.py) ───

    def _toggle_visibilidad(fila: dict) -> None:
        asignacion_id = fila.get("asignacion_id")
        categoria_id = fila.get("categoria_id")
        if categoria_id is None:
            toast_warning("Esta observación no tiene categoría asignada. Edítala primero.")
            return
        try:
            dto = NuevaObservacionDTO(
                estudiante_id=int(fila["estudiante_id"]),
                asignacion_id=asignacion_id,
                periodo_id=int(fila["periodo_id"]),
                texto=fila["texto_completo"],
                categoria_id=int(categoria_id),
                es_publica=not fila["es_publica"],
            )
            Container.convivencia_service().registrar_observacion(dto, ctx.usuario_id)
            toast_success("Visibilidad actualizada.")
            _cargar_detalle(_s, ctx)
            panel_hub.refresh()
        except Exception as exc:
            logger.error("Error cambiando visibilidad: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")

    def _promover_a_plantilla(obs_id: int) -> None:
        def _ejecutar() -> None:
            try:
                Container.convivencia_service().promover_observacion_a_plantilla(
                    obs_id,
                    usuario_id=ctx.usuario_id,
                    usuario_rol=ctx.usuario_rol,
                )
                toast_success("Observación guardada como plantilla.")
            except PermissionError as exc:
                toast_warning(f"Sin permiso: {exc}")
            except Exception as exc:
                logger.error("Error promoviendo observación %s: %s", obs_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Promover a plantilla",
            mensaje="¿Deseas guardar esta observación como plantilla del catálogo?",
            on_confirm=_ejecutar,
            variante="info",
        )

    def _promover_a_comportamiento(obs_id: int) -> None:
        def _ejecutar() -> None:
            try:
                Container.convivencia_service().promover_a_comportamiento(
                    obs_id,
                    usuario_id=ctx.usuario_id,
                    usuario_rol=ctx.usuario_rol,
                )
                toast_success("Observación promovida a registro de comportamiento.")
                _cargar_detalle(_s, ctx)
                _cargar_resumen(_s)
                panel_hub.refresh()
            except PermissionError as exc:
                toast_warning(f"Sin permiso: {exc}")
            except ValueError as exc:
                toast_warning(f"No se puede promover: {exc}")
            except Exception as exc:
                logger.error(
                    "Error promoviendo obs %s a comportamiento: %s", obs_id, exc, exc_info=True
                )
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Promover a comportamiento",
            mensaje=("¿Deseas crear un registro de comportamiento a partir de esta observación?"),
            on_confirm=_ejecutar,
            variante="info",
        )

    def _eliminar_observacion(obs_id: int) -> None:
        def _ejecutar() -> None:
            try:
                Container.convivencia_service().eliminar_observacion(obs_id)
                toast_success("Observación eliminada.")
                _cargar_detalle(_s, ctx)
                panel_hub.refresh()
            except Exception as exc:
                logger.error("Error eliminando observación %s: %s", obs_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Eliminar observación",
            mensaje="¿Confirmas la eliminación de esta observación? Esta acción no se puede deshacer.",
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Handlers Alertas + Vista 360° (solo dir/coord) ───────────────────────

    def _ver_360() -> None:
        est_id = _s["sel_estudiante_id"]
        per_id = _s["sel_periodo_id"]
        if not est_id:
            toast_warning("Selecciona un estudiante para ver la vista 360°.")
            return
        if not per_id:
            toast_warning("Selecciona un periodo.")
            return
        try:
            _s["resultado_360"] = Container.convivencia_service().vista_360(
                estudiante_id=int(est_id),
                periodo_id=int(per_id),
                usuario_id=ctx.usuario_id,
                usuario_rol=ctx.usuario_rol,
            )
            panel_hub.refresh()
        except PermissionError as exc:
            toast_error(f"Sin permiso: {exc}")
        except Exception as exc:
            logger.error("Error en vista 360°: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")

    def _enviar_alerta(datos: dict) -> bool | None:
        est_id = datos.get("estudiante_id")
        docente_id = datos.get("usuario_destino_id")
        descripcion = str(datos.get("descripcion", "")).strip()
        nivel_str = datos.get("nivel", "advertencia")

        if not est_id:
            toast_warning("Selecciona un estudiante.")
            return False
        if not docente_id:
            toast_warning("Selecciona el profesor destinatario.")
            return False
        if not descripcion:
            toast_warning("La descripción es requerida.")
            return False

        def _ejecutar() -> None:
            try:
                dto = NuevaAlertaSeguimientoDTO(
                    estudiante_id=int(est_id),
                    usuario_destino_id=int(docente_id),
                    descripcion=descripcion,
                    nivel=nivel_str,
                )
                Container.convivencia_service().crear_alerta_seguimiento_manual(
                    dto,
                    usuario_id=ctx.usuario_id,
                    usuario_rol=ctx.usuario_rol,
                )
                toast_success("Alerta de seguimiento enviada.")
                _cargar_alertas(_s)
                panel_hub.refresh()
            except PermissionError as exc:
                toast_error(f"Sin permiso: {exc}")
            except Exception as exc:
                logger.error("Error creando alerta: %s", exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Enviar alerta de seguimiento",
            mensaje="¿Confirmas el envío de la alerta al profesor seleccionado?",
            on_confirm=_ejecutar,
        )
        return None

    def _abrir_crear_alerta() -> None:
        opciones_doc = {
            getattr(d, "id", None): (
                f"{getattr(d, 'apellido', '')} {getattr(d, 'nombre', '')}".strip()
                or getattr(d, "email", str(getattr(d, "id", "")))
            )
            for d in _s["docentes"]
        }
        form_dialog(
            titulo="Nueva alerta de seguimiento",
            campos=[
                {
                    "key": "usuario_destino_id",
                    "label": "Profesor destinatario",
                    "tipo": "select",
                    "opciones": opciones_doc,
                    "requerido": True,
                },
                {
                    "key": "descripcion",
                    "label": "Descripción",
                    "tipo": "textarea",
                    "placeholder": "Describe el motivo del seguimiento...",
                    "requerido": True,
                },
                {
                    "key": "nivel",
                    "label": "Nivel de alerta",
                    "tipo": "select",
                    "opciones": {"advertencia": "Advertencia", "critica": "Crítica"},
                    "valor": "advertencia",
                },
            ],
            on_submit=lambda datos: _enviar_alerta(
                {**datos, "estudiante_id": _s["sel_estudiante_id"]}
            ),
            texto_submit="Enviar alerta",
            max_width="max-w-lg",
        )

    # ── Sub-render: Maestro ──────────────────────────────────────────────────

    def _render_maestro() -> None:
        with ui.element("div").classes("panel-card"):
            ui.label("Estudiantes del grupo").classes("panel-title")
            if not _s["resumen"]:
                empty_state(
                    icono="group",
                    titulo="Sin estudiantes",
                    descripcion="No hay estudiantes en el grupo/periodo seleccionado.",
                )
                return
            with ui.element("div").classes("seg-master-scroll"):
                for r in _s["resumen"]:
                    est_id = getattr(r, "estudiante_id", None)
                    nota = getattr(r, "nota", None)
                    nota_txt = f"{nota}" if nota is not None else "—"
                    fila = ui.element("div").classes("config-list-row cursor-pointer")
                    fila.on("click", lambda _e=None, _id=est_id: on_estudiante_change(_id))
                    with fila:
                        ui.label(getattr(r, "nombre", str(est_id))).classes("config-col-name")
                        ui.label(
                            f"Obs: {getattr(r, 'num_observaciones', 0)} · "
                            f"Neg: {getattr(r, 'num_registros_negativos', 0)} · "
                            f"Nota: {nota_txt}"
                        ).classes("text-xs-meta")
                        with ui.element("div").classes("config-col-status"):
                            if getattr(r, "supera_umbral", False):
                                status_badge("Alerta", variante="error")

    # ── Sub-render: Resumen global del grupo (sin estudiante seleccionado) ──

    def _render_grupo_global() -> None:
        """Estadísticas globales del grupo/periodo. Se muestra hasta que el
        usuario selecciona un estudiante en el listado maestro."""
        resumen = _s["resumen"]
        with ui.element("div").classes("panel-card"):
            ui.label("Resumen del grupo").classes("panel-title")
            if not resumen:
                empty_state(
                    icono="group",
                    titulo="Sin estudiantes",
                    descripcion="No hay estudiantes en el grupo/periodo seleccionado.",
                )
                return
            notas = [
                getattr(r, "nota", None) for r in resumen if getattr(r, "nota", None) is not None
            ]
            estudiantes = len(resumen)
            con_nota = len(notas)
            promedio = round(sum(notas) / len(notas), 1) if notas else "—"
            con_alerta = sum(1 for r in resumen if getattr(r, "supera_umbral", False))
            total_obs = sum(getattr(r, "num_observaciones", 0) for r in resumen)
            total_neg = sum(getattr(r, "num_registros_negativos", 0) for r in resumen)
            with ui.element("div").classes("seg-kpis seg-kpis-3"):
                counter_card("Estudiantes", estudiantes, "group", variante="primary")
                counter_card("Con nota", con_nota, "grade", variante="info")
                counter_card("Promedio", promedio, "bar_chart", variante="neutral")
                counter_card(
                    "Con alerta",
                    con_alerta,
                    "flag",
                    variante="danger" if con_alerta > 0 else "success",
                    alerta=con_alerta > 0,
                )
                counter_card("Observaciones", total_obs, "sticky_note_2", variante="info")
                counter_card("Registros neg.", total_neg, "report_problem", variante="warning")
            ui.label("Selecciona un estudiante del listado para ver su detalle.").classes(
                "text-xs-meta"
            )

    # ── Sub-render: Detalle del estudiante ──────────────────────────────────

    def _render_detalle(opciones_cat: dict, es_comp_map: dict) -> None:
        est_id = _s["sel_estudiante_id"]
        if not est_id:
            _render_grupo_global()
            return

        r = _resumen_estudiante(_s, est_id)
        nombre = _nombre_estudiante(_s, est_id)

        # Header compacto: nombre + KPIs (info general + estado de alerta).
        with ui.element("div").classes("panel-card"):
            ui.label(nombre).classes("panel-title")
            supera = bool(getattr(r, "supera_umbral", False)) if r else False
            nota = getattr(r, "nota", None) if r else None
            with ui.element("div").classes("seg-kpis"):
                counter_card(
                    "Nota comportamiento",
                    f"{nota}" if nota is not None else "—",
                    "grade",
                    variante="primary",
                )
                counter_card(
                    "Observaciones",
                    getattr(r, "num_observaciones", 0) if r else 0,
                    "sticky_note_2",
                    variante="info",
                )
                counter_card(
                    "Registros negativos",
                    getattr(r, "num_registros_negativos", 0) if r else 0,
                    "report_problem",
                    variante="warning",
                )
                counter_card(
                    "Estado",
                    "Alerta" if supera else "Normal",
                    "flag",
                    variante="danger" if supera else "success",
                    alerta=supera,
                )

        # Secciones conmutables por botones (evita el scroll largo): solo se
        # muestra la sección activa (_s["sel_seccion"]).
        secciones = [
            ("evolucion", "Evolución", "insights"),
            ("observaciones", "Observaciones", "sticky_note_2"),
            ("registros", "Registros", "rule"),
        ]
        if puede_alertas:
            secciones.append(("alertas", "Alertas y 360°", "notification_important"))

        with ui.element("div").classes("panel-card"), ui.element("div").classes("seg-tabs"):
            for _key, _label, _icon in secciones:
                _activa = _s["sel_seccion"] == _key
                (btn_secondary if _activa else btn_ghost)(
                    _label,
                    icon=_icon,
                    size="sm",
                    on_click=lambda k=_key: _set_seccion(k),
                )

        sec = _s["sel_seccion"]
        if sec == "alertas" and not puede_alertas:
            sec = "evolucion"
        if sec == "observaciones":
            _render_observaciones(opciones_cat, es_comp_map)
        elif sec == "registros":
            _render_registros()
        elif sec == "alertas":
            _render_alertas_360()
        else:
            _render_evolucion()

    def _render_evolucion() -> None:
        with ui.element("div").classes("panel-card"):
            ui.label("Evolución de la nota").classes("panel-title")
            serie = _s["serie"]
            if serie and any(getattr(p, "valor", None) is not None for p in serie):
                labels = [getattr(p, "periodo_nombre", "") for p in serie]
                valores = [getattr(p, "valor", None) for p in serie]
                mini_chart(labels, valores)
            else:
                empty_state(
                    titulo="Sin datos de evolución",
                    descripcion="No hay notas de comportamiento registradas en el año.",
                )

    def _render_observaciones(opciones_cat: dict, es_comp_map: dict) -> None:
        with ui.element("div").classes("panel-card"):
            ui.label("Observaciones").classes("panel-title")
            filas_obs = [_fila_observacion(o, opciones_cat) for o in _s["observaciones_est"]]
            if not filas_obs:
                empty_state(
                    icono="sticky_note_2",
                    titulo="Sin observaciones",
                    descripcion="No hay observaciones para este estudiante en el periodo.",
                )
            else:
                with ui.element("div").classes("seg-detalle-lista"):
                    for fila in filas_obs:
                        with ui.element("div").classes("config-list-row"):
                            with ui.element("div").classes("config-col-badge"):
                                status_badge(fila["categoria_nombre"], variante="info")
                            with ui.element("div").classes("config-col-status"):
                                if fila["es_publica"]:
                                    status_badge("Pública", variante="success")
                                else:
                                    status_badge("Privada", variante="neutral")
                            with ui.label(fila["texto"]).classes("config-col-name"):
                                if fila["texto_completo"]:
                                    ui.tooltip(fila["texto_completo"])
                            with ui.element("div").classes("config-col-status"):
                                ui.label(fila["fecha"]).classes("text-xs-meta")
                            with ui.element("div").classes("config-col-actions"):
                                _render_acciones_obs(fila, es_comp_map)

    def _render_registros() -> None:
        with ui.element("div").classes("panel-card"):
            ui.label("Registros de comportamiento").classes("panel-title")
            filas_reg = [_fila_registro(reg) for reg in _s["registros_est"]]
            if not filas_reg:
                empty_state(
                    titulo="Sin registros",
                    descripcion="No hay registros de comportamiento para este estudiante en el periodo.",
                )
            else:
                for fila in filas_reg:
                    with ui.element("div").classes("config-list-row"):
                        ui.label(fila["fecha"]).classes("text-xs-meta")
                        with ui.element("div").classes("config-col-badge"):
                            ui.label(fila["tipo_display"]).classes(
                                f"badge {fila['tipo_badge_class']}"
                            )
                        ui.label(_texto_truncado(fila["descripcion"])).classes("config-col-name")

    def _render_acciones_obs(fila: dict, es_comp_map: dict) -> None:
        btn_ghost(
            "",
            on_click=lambda f=fila: _toggle_visibilidad(f),
            icon="visibility_off" if fila["es_publica"] else "visibility",
            size="sm",
        )
        if ctx.usuario_rol in _ROLES_ALERTAS:
            btn_ghost(
                "",
                on_click=lambda oid=fila["id"]: _promover_a_plantilla(oid),
                icon="upload",
                size="sm",
            )
            _cat_id = fila.get("categoria_id")
            _ya_promovida = fila.get("registro_comportamiento_id") is not None
            if _cat_id is not None and es_comp_map.get(_cat_id, False) and not _ya_promovida:
                btn_ghost(
                    "",
                    on_click=lambda oid=fila["id"]: _promover_a_comportamiento(oid),
                    icon="flag",
                    size="sm",
                )
            btn_danger(
                "",
                on_click=lambda oid=fila["id"]: _eliminar_observacion(oid),
                icon="delete",
                size="sm",
            )

    def _render_alertas_360() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("panel-toolbar"):
                ui.label("Alertas y Vista 360°").classes("panel-title")
                ui.element("div").classes("panel-toolbar-spacer")
                btn_ghost("Cargar 360°", on_click=_ver_360, icon="refresh")
                btn_primary("Nueva alerta", on_click=_abrir_crear_alerta, icon=Icons.ADD)

            # Alertas de seguimiento del estudiante
            filas_alertas = _construir_filas_alertas(_s)
            if filas_alertas:
                for fa in filas_alertas:
                    with ui.element("div").classes(f"alerta-item alerta-{fa['nivel_raw']}"):
                        with ui.element("div").classes("panel-toolbar"):
                            ui.label(fa["nivel_display"]).classes("config-col-name")
                            ui.label(fa["fecha"]).classes("text-xs-meta")
                            badge_var = (
                                "badge-success" if fa["estado"] == "Resuelta" else "badge-warning"
                            )
                            ui.label(fa["estado"]).classes(f"badge {badge_var}")
                        ui.label(fa["descripcion"]).classes("alerta-item-text")
                        ui.label(f"→ {fa['destinatario']}").classes("text-xs-meta")
            else:
                empty_state(
                    titulo="Sin alertas",
                    descripcion="No hay alertas de seguimiento para este estudiante.",
                )

            # Vista 360°
            res = _s.get("resultado_360")
            if res is not None:
                _tiene_datos = (
                    res.nota_comportamiento is not None
                    or res.promedio_notas is not None
                    or res.observaciones
                    or res.alertas_activas
                )
                if not _tiene_datos:
                    empty_state(
                        titulo="Sin datos de seguimiento",
                        descripcion="No hay datos registrados para este estudiante.",
                    )
                else:
                    with ui.element("div").classes("form-row-inline"):
                        if res.nota_comportamiento is not None:
                            stat_card(
                                "Nota comportamiento",
                                res.nota_comportamiento,
                                "grade",
                                subtitulo=res.nivel_comportamiento or "",
                                variante="primary",
                            )
                        if res.promedio_notas is not None:
                            stat_card(
                                "Promedio académico",
                                res.promedio_notas,
                                "bar_chart",
                                variante="info",
                            )
                        if res.concepto:
                            with ui.element("div").classes("stat-card-wrapper info"):
                                ui.label("Concepto").classes("stat-card-label")
                                ui.label(res.concepto).classes("stat-card-value")

                    if res.observaciones:
                        ui.label("Observaciones del periodo").classes("panel-title")
                        for obs_txt in res.observaciones:
                            with ui.element("div").classes("config-list-row"):
                                ui.label(obs_txt).classes("config-col-name")

                    if res.alertas_activas:
                        ui.label("Alertas activas").classes("panel-title")
                        for alerta_txt in res.alertas_activas:
                            with ui.element("div").classes("alerta-item alerta-advertencia"):
                                ui.label(alerta_txt).classes("alerta-item-text")

    # ── Refreshable del hub ─────────────────────────────────────────────────

    @ui.refreshable
    def panel_hub() -> None:
        opciones_cat, es_comp_map = _cargar_categorias()

        if not _s.get("sel_grupo_id"):
            with ui.element("div").classes("panel-card"):
                empty_state(
                    icono="group",
                    titulo="Selecciona un grupo",
                    descripcion="Elige periodo y grupo para ver el seguimiento.",
                )
            return

        with ui.element("div").classes("page-body"):
            # Detalle / seguimiento en la columna ANCHA izquierda; listado de
            # estudiantes en la columna estrecha derecha (click para cambiar).
            with ui.element("div").classes("page-col-main"):
                _render_detalle(opciones_cat, es_comp_map)
            with ui.element("div").classes("page-col-side"):
                _render_maestro()

    # ── Contenido principal (selector FUERA del refreshable) ────────────────

    def contenido() -> None:
        def on_sel_change(s: dict) -> None:
            # Copia selección y limpia el detalle del estudiante (en el presenter).
            presenter.aplicar_seleccion(s)
            if s["sel_grupo_id"]:
                try:
                    _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(
                        s["sel_grupo_id"]
                    )
                except Exception as exc:
                    logger.error("Error cargando estudiantes: %s", exc)
                    _s["estudiantes"] = []
            else:
                _s["estudiantes"] = []
            _cargar_resumen(_s)
            panel_hub.refresh()

        inline_periodo_grupo(
            _s,
            on_sel_change,
            institucion_id=ctx.institucion_id,
            usuario_id=ctx.usuario_id,
            usuario_rol=ctx.usuario_rol,
            preselect_periodo=True,
        )

        panel_hub()

    app_layout(ctx, contenido, page_titulo="Seguimiento de convivencia")


__all__ = ["seguimiento_page"]
