"""
src/interface/pages/academico/horarios_hub.py
=============================================
Hub unificado de horarios — ZECI Manager v2.0
Ruta: /academico/horarios-hub
Acceso: todos los roles autenticados

Secciones:
  preparar   → Links a disponibilidad, salas, plantillas y generador.
  generar    → Configuraciones de generación + motor (de horario_generar.py).
  visualizar → Parrilla de horarios (solo lectura para coordinador/profesor).
  editar     → Parrilla con edición + carga masiva (admin/director).

Reglas de capas:
  - Solo Container.*  (no repositorios directos).
  - No importa src.db.
  - No usa dict() serializer — siempre model_dump().
  - Estado mutable en _s dict (aislamiento por petición HTTP).
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import date, timedelta
from typing import Any

from nicegui import background_tasks, context as ng_context, ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary, btn_secondary, btn_danger, btn_ghost,
)
from src.interface.design.components import (
    confirm_dialog, empty_state, form_dialog, status_badge,
    toast_error, toast_success, toast_warning,
)
from src.interface.pages.academico.parrilla_widget import (
    render_parrilla, render_tablero_maestro, _opciones_eje,
)
from src.interface.pages.academico.plantilla_editor_widget import (
    plantilla_form_dialog,
    franja_form_dialog,
    render_franjas_editor,
    render_plantilla_preview,
)
from src.services.infraestructura_service import DiaSemana
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("HORARIOS_HUB")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
# Gestión completa de horarios (ver, editar, generar): admin, director y
# coordinador. Los docentes solo tienen vista de su propio horario.
_ROLES_ESCRITURA = frozenset({"director", "coordinador"})
_ROLES_SELECTOR_VISTA = frozenset({"director", "coordinador"})

_DIAS_BASE = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
_DIA_MAP = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo",
}
_MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

_ESTADO_BADGE = {
    "borrador": ("Borrador", "info"),
    "generado": ("Generado", "warning"),
    "aplicado": ("Aplicado", "success"),
}

_SECCION_META = {
    "preparar":   ("Preparar",   "checklist"),
    "generar":    ("Generar",    Icons.AUTO_MODE),
    "visualizar": ("Visualizar", Icons.SCHEDULE),
    "editar":     ("Editar",     Icons.EDIT),
}


# ---------------------------------------------------------------------------
# Helper: mensaje de error legible
# ---------------------------------------------------------------------------

def _texto_error(exc: Exception) -> str:
    """Mensaje legible para mostrar en un toast a partir de una excepción.

    Las validaciones de dominio se construyen con Pydantic, cuyo
    ``ValidationError`` envuelve el mensaje útil con ruido técnico (tipo,
    valor de entrada, URL de documentación). Aquí se extrae solo el/los
    mensaje(s) del validador, sin el prefijo «Value error,».
    """
    errores = getattr(exc, "errors", None)
    if callable(errores):
        try:
            mensajes = [
                str(e.get("msg", "")).split("Value error, ", 1)[-1].strip()
                for e in exc.errors()
            ]
            mensajes = [m for m in mensajes if m]
            if mensajes:
                return " · ".join(mensajes)
        except Exception:
            pass
    return str(exc)


def _magnitud_peso(v: float) -> str:
    """Traduce un peso 0.0–2.0 a una magnitud entendible para el usuario."""
    if v <= 0.0:
        return "Ignorar"
    if v < 0.8:
        return "Bajo"
    if v < 1.4:
        return "Medio"
    if v < 2.0:
        return "Alto"
    return "Máximo"


# ---------------------------------------------------------------------------
# Page function
# ---------------------------------------------------------------------------

# page-delegate: ruta y guard registrados en main.py
def horarios_hub_page(seccion_inicial: str = "visualizar") -> None:
    """Punto de entrada del hub unificado de horarios."""

    # ── Guard de autenticación ────────────────────────────────────────────────
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    rol = ctx.usuario_rol or ""
    puede_escribir = rol in _ROLES_ESCRITURA
    puede_cambiar_vista = rol in _ROLES_SELECTOR_VISTA
    es_profesor = (rol == "profesor")

    # ── Secciones visibles por rol ────────────────────────────────────────────
    # Admin, director y coordinador: gestión completa (ver, editar, generar).
    # Docente: solo vista de su propio horario y sus asignaciones.
    if es_profesor:
        _secciones_visibles = ["visualizar"]
    else:
        _secciones_visibles = ["preparar", "generar", "visualizar", "editar"]

    # Validar seccion_inicial
    if seccion_inicial not in _secciones_visibles:
        seccion_inicial = _secciones_visibles[0]

    # ── Estado mutable unificado ──────────────────────────────────────────────
    _hoy = date.today()
    _dia_hoy_es = _DIA_MAP.get(_hoy.strftime("%A"), "Lunes")
    if _dia_hoy_es not in _DIAS_BASE:
        _dia_hoy_es = "Lunes"

    _s: dict = {
        # Sección activa
        "seccion": seccion_inicial,
        # Shared / visualizar-editar
        "config": None,
        "anio_id": None,
        "periodo_id": None,
        "grupos": [],
        "docentes": [],
        "escenarios": [],
        "escenario_sel": None,
        "bloques": [],
        "asignaciones": [],
        "parrilla_perspectiva": "Grupo",
        "parrilla_eje_sel": None,
        "parrilla_filtro_areas": None,
        "parrilla_filtro_dias": None,
        "parrilla_modo": "Por entidad",
        "parrilla_dia_maestro": None,
        "grupo_id": None,
        # Carga masiva
        "lote_reporte": None,
        "lote_filas_raw": [],
        # Generar (gen_ prefix)
        "gen_configs": [],
        "gen_config_sel": None,
        "gen_plantillas": [],
        "gen_plantilla_sel": None,
        "gen_franjas_sel": [],
        "gen_resultado": None,
        "gen_datos_preview": None,
        "gen_perspectiva": "Grupo",
        "gen_eje_sel": None,
        "gen_generando": False,
        "gen_anio_id": None,
        "gen_periodo_id": None,
        "gen_error_contexto": None,
        "gen_tab": "generacion",
        # Docente (doc_ prefix)
        "doc_vista_grid": "semana",
        "doc_dia_sel": _dia_hoy_es,
        "doc_parrilla_datos": {"dias": [], "franjas": [], "celdas": []},
        "doc_asignaciones": [],
    }

    # ── Carga inicial shared ──────────────────────────────────────────────────
    try:
        _s["config"] = Container.configuracion_service().get_activa()
    except Exception as exc:
        logger.error("Error cargando configuración activa: %s", exc)

    if _s["config"]:
        _s["anio_id"] = _s["config"].id
        try:
            periodos = Container.periodo_service().listar_por_anio(_s["config"].id)
            activos = [p for p in periodos if not getattr(p, "cerrado", False)]
            periodo_sel = activos[0] if activos else (periodos[0] if periodos else None)
            if periodo_sel:
                _s["periodo_id"] = periodo_sel.id
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)

    if not es_profesor:
        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error cargando grupos: %s", exc)
        try:
            _s["docentes"] = Container.usuario_service().listar_docentes()
        except Exception as exc:
            logger.error("Error cargando docentes: %s", exc)
        if _s["grupos"]:
            _s["grupo_id"] = _s["grupos"][0].id
        elif hasattr(ctx, "grupo_id") and ctx.grupo_id:
            _s["grupo_id"] = ctx.grupo_id

    # ── Carga contexto generador ──────────────────────────────────────────────
    if not es_profesor:
        gen_anio_id: int | None = None
        gen_periodo_id: int | None = None
        gen_error_contexto: str | None = None
        try:
            anio = Container.configuracion_service().get_activa()
            if anio is None:
                gen_error_contexto = "No hay un año lectivo activo. Actívalo en Configuración."
            else:
                gen_anio_id = anio.id
                periodo = Container.periodo_service().get_activo(gen_anio_id)
                if periodo is None:
                    periodos2 = Container.periodo_service().listar_por_anio(gen_anio_id)
                    activos2 = [p for p in periodos2 if not getattr(p, "cerrado", False)]
                    periodo = activos2[0] if activos2 else (periodos2[0] if periodos2 else None)
                gen_periodo_id = periodo.id if periodo else None
                if gen_periodo_id is None:
                    gen_error_contexto = "No hay periodos en el año activo. Crea o activa uno en Configuración."
        except Exception as exc:
            logger.error("Error derivando contexto del generador: %s", exc)
            gen_error_contexto = "No se pudo cargar el contexto académico."

        _s["gen_anio_id"] = ctx.anio_id or gen_anio_id
        _s["gen_periodo_id"] = ctx.periodo_id or gen_periodo_id
        _s["gen_error_contexto"] = gen_error_contexto

        # Deep-link opcional a una pestaña de la sección Generar (lo usan los
        # enlaces "Corregir" del panel Preparar para llevar a Plantillas).
        try:
            _tab_q = ng_context.client.request.query_params.get("tab")
        except Exception:
            _tab_q = None
        if _tab_q in ("plantillas", "generacion"):
            _s["gen_tab"] = _tab_q

    # =========================================================================
    # Load functions — shared / visualizar-editar
    # =========================================================================

    def _cargar_escenarios() -> None:
        anio_id = _s["anio_id"]
        if not anio_id:
            _s["escenarios"] = []
            _s["escenario_sel"] = None
            return
        try:
            svc = Container.infraestructura_service()
            _s["escenarios"] = svc.listar_escenarios(anio_id)
            activo = next((e for e in _s["escenarios"] if e.activo), None)
            _s["escenario_sel"] = activo or (_s["escenarios"][0] if _s["escenarios"] else None)
        except Exception as exc:
            logger.error("Error cargando escenarios: %s", exc)
            _s["escenarios"] = []
            _s["escenario_sel"] = None

    def _cargar_bloques_escenario() -> None:
        esc = _s["escenario_sel"]
        grp = _s["grupo_id"]
        if not esc or not grp:
            _s["bloques"] = []
            return
        try:
            _s["bloques"] = Container.infraestructura_service().listar_horario_grupo_escenario(
                grp, esc.id
            )
        except Exception as exc:
            logger.error("Error cargando bloques escenario: %s", exc)
            _s["bloques"] = []

    def _preseleccionar_escenario_query() -> None:
        try:
            esc_q = ng_context.client.request.query_params.get("escenario")
        except Exception:
            esc_q = None
        if not esc_q:
            return
        try:
            esc_id = int(esc_q)
        except (ValueError, TypeError):
            return
        forzado = next((e for e in _s["escenarios"] if e.id == esc_id), None)
        if forzado:
            _s["escenario_sel"] = forzado
            _cargar_bloques_escenario()

    def _cargar_parrilla_docente() -> None:
        """Carga la parrilla del escenario activo para filtrarla al docente.

        Usa la misma fuente que la vista de directivos (datos_parrilla del
        escenario activo) para garantizar idéntico renderizado y datos.
        """
        _cargar_escenarios()
        _s["doc_parrilla_datos"] = _parrilla_cargar_datos()

    def _cargar_asignaciones_docente() -> None:
        if not _s["periodo_id"]:
            _s["doc_asignaciones"] = []
            return
        try:
            _s["doc_asignaciones"] = Container.asignacion_service().listar_por_docente(
                ctx.usuario_id, _s["periodo_id"]
            )
        except Exception as exc:
            logger.error("Error cargando asignaciones docente: %s", exc)
            _s["doc_asignaciones"] = []

    def _parrilla_cargar_datos() -> dict:
        esc = _s["escenario_sel"]
        if not esc:
            return {"dias": [], "franjas": [], "celdas": []}
        try:
            return Container.horario_service().datos_parrilla(esc.id)
        except Exception as exc:
            logger.error("Error cargando datos de parrilla: %s", exc)
            return {"dias": [], "franjas": [], "celdas": []}

    def _parrilla_cargar_metricas() -> dict:
        esc = _s["escenario_sel"]
        vacio = {
            "total_bloques": 0, "n_grupos": 0, "n_docentes": 0,
            "n_salas": 0, "huecos_grupo": 0, "ocupacion_pct": 0,
        }
        if not esc:
            return vacio
        try:
            return Container.horario_service().metricas_parrilla(esc.id)
        except Exception as exc:
            logger.error("Error cargando métricas de parrilla: %s", exc)
            return vacio

    def _parrilla_cargar_areas() -> list[dict]:
        esc = _s["escenario_sel"]
        if not esc:
            return []
        try:
            return Container.horario_service().areas_parrilla(esc.id)
        except Exception as exc:
            logger.error("Error cargando áreas de parrilla: %s", exc)
            return []

    # =========================================================================
    # Load functions — generar
    # =========================================================================

    def _gen_mapa_plantillas() -> dict:
        return {p.id: p.nombre for p in _s["gen_plantillas"] if getattr(p, "id", None) is not None}

    def _gen_cargar_plantillas() -> None:
        try:
            _s["gen_plantillas"] = Container.infraestructura_service().listar_plantillas()
        except Exception as exc:
            logger.error("Error cargando plantillas: %s", exc)
            _s["gen_plantillas"] = []

    def _gen_cargar_grupos() -> None:
        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error cargando grupos (gen): %s", exc)
            _s["grupos"] = []

    def _gen_cargar_configs() -> None:
        try:
            _s["gen_configs"] = Container.infraestructura_service().listar_configs_generacion(
                _s["gen_periodo_id"]
            )
        except Exception as exc:
            logger.error("Error cargando configuraciones de generación: %s", exc)
            _s["gen_configs"] = []
        sel = _s.get("gen_config_sel")
        if sel is not None and getattr(sel, "id", None) is not None:
            _s["gen_config_sel"] = next(
                (c for c in _s["gen_configs"] if c.id == sel.id), None
            )

    def _gen_cargar_franjas_sel() -> None:
        p = _s.get("gen_plantilla_sel")
        if p is None:
            _s["gen_franjas_sel"] = []
            return
        try:
            _s["gen_franjas_sel"] = Container.infraestructura_service().listar_franjas(p.id)
        except Exception as exc:
            logger.error("Error cargando franjas: %s", exc)
            _s["gen_franjas_sel"] = []

    def _gen_cargar_preview() -> None:
        resultado = _s.get("gen_resultado")
        escenario_id = getattr(resultado, "escenario_id", None) if resultado else None
        if not escenario_id:
            _s["gen_datos_preview"] = None
            return
        try:
            _s["gen_datos_preview"] = Container.horario_service().datos_parrilla(escenario_id)
        except Exception as exc:
            logger.error("Error cargando datos de parrilla de vista previa: %s", exc)
            _s["gen_datos_preview"] = None

    # ── Carga inicial ─────────────────────────────────────────────────────────
    if es_profesor:
        _cargar_parrilla_docente()
        _cargar_asignaciones_docente()
    else:
        _cargar_escenarios()
        _preseleccionar_escenario_query()
        _cargar_bloques_escenario()
        _gen_cargar_plantillas()
        _gen_cargar_grupos()
        _gen_cargar_configs()

    # =========================================================================
    # Segmented control helpers
    # =========================================================================

    def _segmento(opciones: list[str], valor_actual: str, on_change) -> None:
        """Control segmentado con lista de strings."""
        with ui.element("div").classes("parrilla-segmento"):
            for _op in opciones:
                _cls = "parrilla-seg-btn" + (" parrilla-seg-btn-activo" if _op == valor_actual else "")
                _btn = ui.element("div").classes(_cls)
                _btn.on("click", lambda _, o=_op: on_change(o))
                with _btn:
                    ui.label(str(_op))

    def _gen_segmento(opciones: list[tuple[str, str]], valor_actual: str, on_change) -> None:
        """Control segmentado con lista de (clave, etiqueta)."""
        with ui.element("div").classes("parrilla-segmento"):
            for clave, etiqueta in opciones:
                cls = "parrilla-seg-btn" + (" parrilla-seg-btn-activo" if clave == valor_actual else "")
                btn = ui.element("div").classes(cls)
                btn.on("click", lambda _, c=clave: on_change(c))
                with btn:
                    ui.label(str(etiqueta))

    # =========================================================================
    # Handlers — visualizar/editar
    # =========================================================================

    def _toggle_vista_doc(valor: str) -> None:
        # Refresca toda la rama docente: el selector de día vive fuera de la
        # grilla y debe aparecer/ocultarse al cambiar de vista.
        _s["doc_vista_grid"] = valor
        hub_refreshable.refresh()

    def _cambiar_dia_doc(dia: str) -> None:
        _s["doc_dia_sel"] = dia
        hub_refreshable.refresh()

    def _seleccionar_escenario(esc) -> None:
        _s["escenario_sel"] = esc
        _cargar_bloques_escenario()
        escenarios_refreshable.refresh()
        parrilla_unificada_refreshable.refresh()

    def _crear_escenario_dialog() -> None:
        def _guardar(datos: dict) -> "bool | None":
            nombre = (datos.get("nombre") or "").strip()
            if not nombre:
                toast_warning("El nombre es obligatorio.")
                return False
            try:
                nuevo = Container.infraestructura_service().crear_escenario_simple(
                    anio_id=_s["anio_id"],
                    nombre=nombre,
                    descripcion=datos.get("descripcion") or None,
                )
                _s["escenarios"].append(nuevo)
                _s["escenario_sel"] = nuevo
                _cargar_bloques_escenario()
                escenarios_refreshable.refresh()
                parrilla_unificada_refreshable.refresh()
                toast_success(f"Escenario '{nuevo.nombre}' creado")
            except ValueError as exc:
                toast_warning(_texto_error(exc))
                return False
            except Exception as exc:
                logger.error("Error creando escenario: %s", exc)
                toast_error("Error al crear el escenario")
                return False

        form_dialog(
            titulo="Nuevo escenario",
            campos=[
                {"key": "nombre", "label": "Nombre *", "tipo": "text", "requerido": True},
                {"key": "descripcion", "label": "Descripción", "tipo": "text"},
            ],
            on_submit=_guardar,
        )

    def _vis_activar_escenario(escenario_id: int) -> None:
        try:
            Container.infraestructura_service().activar_escenario(escenario_id)
            _cargar_escenarios()
            escenarios_refreshable.refresh()
            toast_success("Escenario activado")
        except Exception as exc:
            logger.error("Error activando escenario: %s", exc)
            toast_error(_texto_error(exc))

    def _renombrar_escenario_dialog(esc) -> None:
        def _guardar(datos: dict) -> "bool | None":
            nombre = (datos.get("nombre") or "").strip()
            if not nombre:
                toast_warning("El nombre es obligatorio.")
                return False
            try:
                Container.infraestructura_service().renombrar_escenario(
                    esc_existente=esc,
                    nombre=nombre,
                    descripcion=datos.get("descripcion") or None,
                )
                _cargar_escenarios()
                escenarios_refreshable.refresh()
                toast_success("Escenario renombrado")
            except ValueError as exc:
                toast_warning(_texto_error(exc))
                return False
            except Exception as exc:
                logger.error("Error renombrando escenario: %s", exc)
                toast_error("Error al renombrar")
                return False

        form_dialog(
            titulo="Renombrar escenario",
            campos=[
                {"key": "nombre", "label": "Nombre *", "tipo": "text",
                 "valor": esc.nombre, "requerido": True},
                {"key": "descripcion", "label": "Descripción", "tipo": "text",
                 "valor": esc.descripcion or ""},
            ],
            on_submit=_guardar,
        )

    def _duplicar_escenario_dialog(esc) -> None:
        def _guardar(datos: dict) -> "bool | None":
            nombre = (datos.get("nombre") or "").strip()
            if not nombre:
                toast_warning("El nombre es obligatorio.")
                return False
            try:
                nuevo = Container.infraestructura_service().duplicar_escenario(esc.id, nombre)
                _cargar_escenarios()
                _s["escenario_sel"] = nuevo
                _cargar_bloques_escenario()
                escenarios_refreshable.refresh()
                parrilla_unificada_refreshable.refresh()
                toast_success(f"Escenario duplicado como '{nuevo.nombre}'")
            except ValueError as exc:
                toast_warning(_texto_error(exc))
                return False
            except Exception as exc:
                logger.error("Error duplicando escenario: %s", exc)
                toast_error("Error al duplicar")
                return False

        form_dialog(
            titulo="Duplicar escenario",
            campos=[
                {"key": "nombre", "label": "Nombre del nuevo escenario *", "tipo": "text",
                 "valor": f"Copia de {esc.nombre}", "requerido": True},
            ],
            on_submit=_guardar,
        )

    def _eliminar_escenario_confirm(esc) -> None:
        def _ok() -> None:
            try:
                Container.infraestructura_service().eliminar_escenario(esc.id)
                _cargar_escenarios()
                escenarios_refreshable.refresh()
                _s["bloques"] = []
                parrilla_unificada_refreshable.refresh()
                toast_success("Escenario eliminado")
            except Exception as exc:
                logger.error("Error eliminando escenario: %s", exc)
                toast_error(_texto_error(exc))

        confirm_dialog(
            titulo="Eliminar escenario",
            mensaje=f"¿Eliminar el escenario '{esc.nombre}'? Se eliminarán todos sus bloques.",
            on_confirm=_ok,
            variante="danger",
            texto_confirmar="Eliminar",
            texto_cancelar="Cancelar",
        )

    def _confirmar_eliminar(horario_id: int) -> None:
        def _ok() -> None:
            try:
                Container.horario_service().eliminar_bloque(horario_id)
                toast_success("Bloque eliminado")
                _cargar_bloques_escenario()
                parrilla_unificada_refreshable.refresh()
            except Exception as exc:
                logger.error("Error eliminando bloque: %s", exc)
                toast_error(_texto_error(exc))

        confirm_dialog(
            titulo="Eliminar bloque",
            mensaje="¿Eliminar este bloque del horario?",
            on_confirm=_ok,
            variante="danger",
            texto_confirmar="Eliminar",
            texto_cancelar="Cancelar",
        )

    def _abrir_dialog_crear(dia_prefill: str = "", hora_prefill: str = "") -> None:
        esc = _s["escenario_sel"]
        if not esc:
            toast_warning("Selecciona un escenario primero.")
            return
        _s["asignaciones"] = []
        if _s["periodo_id"]:
            try:
                _s["asignaciones"] = Container.asignacion_service().listar_con_info(
                    FiltroAsignacionesDTO(periodo_id=_s["periodo_id"])
                )
            except Exception as exc:
                logger.error("Error cargando asignaciones: %s", exc)
        if not _s["asignaciones"]:
            toast_warning("No hay asignaciones activas en este periodo.")
            return
        asig_opts = {
            a.asignacion_id: f"{a.grupo_codigo} – {a.asignatura_nombre} ({a.docente_nombre})"
            for a in _s["asignaciones"]
        }

        def _guardar(datos: dict) -> "bool | None":
            asig_id = datos.get("asignacion_id")
            if not asig_id:
                toast_warning("Selecciona una asignación.")
                return False
            try:
                Container.horario_service().crear_bloque(
                    escenario_id=esc.id,
                    asignacion_id=asig_id,
                    dia=datos.get("dia", DiaSemana.LUNES.value),
                    hora_inicio=datos.get("hora_inicio", "07:00"),
                    hora_fin=datos.get("hora_fin", "07:55"),
                    sala=str(datos.get("sala", "") or "Aula"),
                )
                toast_success("Bloque guardado")
                _cargar_bloques_escenario()
                parrilla_unificada_refreshable.refresh()
            except ValueError as exc:
                toast_warning(_texto_error(exc))
                return False
            except Exception as exc:
                logger.error("Error guardando bloque: %s", exc)
                toast_error("Error al guardar el bloque")
                return False

        form_dialog(
            titulo="Agregar bloque de horario",
            campos=[
                {"key": "asignacion_id", "label": "Asignación *", "tipo": "select",
                 "opciones": asig_opts, "requerido": True},
                {"key": "dia", "label": "Día *", "tipo": "select",
                 "opciones": {d.value: d.value for d in DiaSemana},
                 "valor": dia_prefill or DiaSemana.LUNES.value, "requerido": True},
                {"key": "hora_inicio", "label": "Hora inicio", "tipo": "time",
                 "valor": hora_prefill or "07:00"},
                {"key": "hora_fin", "label": "Hora fin", "tipo": "time", "valor": "07:55"},
                {"key": "sala", "label": "Sala", "tipo": "text",
                 "valor": "Aula", "placeholder": "Aula, Lab. Química..."},
            ],
            on_submit=_guardar,
            max_width="max-w-lg",
            columnas=2,
        )

    def _abrir_dialog_editar(horario_id: int) -> None:
        bloque = next((b for b in _s["bloques"] if b.id == horario_id), None)
        if not bloque:
            esc = _s["escenario_sel"]
            if esc:
                try:
                    todos = Container.infraestructura_service().listar_horario_escenario(esc.id)
                    bloque = next((b for b in todos if b.id == horario_id), None)
                except Exception as exc:
                    logger.error("Error obteniendo bloque del escenario: %s", exc)
        if not bloque:
            toast_warning("Bloque no encontrado.")
            return

        def _guardar(datos: dict) -> "bool | None":
            try:
                Container.horario_service().actualizar_bloque(
                    horario_id,
                    dia=datos.get("dia", bloque.dia_semana.value if hasattr(bloque.dia_semana, "value") else bloque.dia_semana),
                    hora_inicio=datos.get("hora_inicio", bloque.hora_inicio.strftime("%H:%M")),
                    hora_fin=datos.get("hora_fin", bloque.hora_fin.strftime("%H:%M")),
                    sala=str(datos.get("sala", "") or "Aula"),
                )
                toast_success("Bloque actualizado")
                _cargar_bloques_escenario()
                parrilla_unificada_refreshable.refresh()
            except ValueError as exc:
                toast_warning(_texto_error(exc))
                return False
            except Exception as exc:
                logger.error("Error editando bloque: %s", exc)
                toast_error("Error al editar el bloque")
                return False

        hora_inicio_str = bloque.hora_inicio.strftime("%H:%M") if hasattr(bloque.hora_inicio, "strftime") else str(bloque.hora_inicio)
        hora_fin_str = bloque.hora_fin.strftime("%H:%M") if hasattr(bloque.hora_fin, "strftime") else str(bloque.hora_fin)
        dia_val = bloque.dia_semana.value if hasattr(bloque.dia_semana, "value") else str(bloque.dia_semana)

        form_dialog(
            titulo="Editar bloque",
            campos=[
                {"key": "dia", "label": "Día *", "tipo": "select",
                 "opciones": {d.value: d.value for d in DiaSemana},
                 "valor": dia_val, "requerido": True},
                {"key": "hora_inicio", "label": "Hora inicio", "tipo": "time",
                 "valor": hora_inicio_str},
                {"key": "hora_fin", "label": "Hora fin", "tipo": "time",
                 "valor": hora_fin_str},
                {"key": "sala", "label": "Sala", "tipo": "text",
                 "valor": bloque.sala or "Aula"},
            ],
            on_submit=_guardar,
            max_width="max-w-md",
            columnas=2,
        )

    def _cambiar_modo(valor: str) -> None:
        _s["parrilla_modo"] = valor
        parrilla_unificada_refreshable.refresh()

    def _cambiar_perspectiva(valor: str) -> None:
        _s["parrilla_perspectiva"] = valor
        _s["parrilla_eje_sel"] = None
        parrilla_unificada_refreshable.refresh()

    def _cambiar_eje(valor) -> None:
        _s["parrilla_eje_sel"] = valor
        parrilla_unificada_refreshable.refresh()

    def _cambiar_dia_maestro(valor: str) -> None:
        _s["parrilla_dia_maestro"] = valor
        parrilla_unificada_refreshable.refresh()

    def _cambiar_filtro_areas(valores) -> None:
        _s["parrilla_filtro_areas"] = set(valores) if valores else None
        parrilla_unificada_refreshable.refresh()

    def _cambiar_filtro_dias(valores) -> None:
        _s["parrilla_filtro_dias"] = set(valores) if valores else None
        parrilla_unificada_refreshable.refresh()

    def _editar_color_area(area: dict) -> None:
        def _guardar(datos: dict) -> "bool | None":
            color = (datos.get("color") or "").strip() or None
            try:
                Container.infraestructura_service().set_color_area(area["area_id"], color)
                toast_success(f"Color de '{area['area_nombre']}' actualizado")
                parrilla_unificada_refreshable.refresh()
            except ValueError as exc:
                toast_warning(_texto_error(exc))
                return False
            except Exception as exc:
                logger.error("Error actualizando color de área: %s", exc)
                toast_error("No se pudo actualizar el color")
                return False

        form_dialog(
            titulo=f"Color de «{area['area_nombre']}»",
            campos=[
                {"key": "color", "label": "Color", "tipo": "color",
                 "valor": area.get("color") or ""},
            ],
            on_submit=_guardar,
            max_width="max-w-xs",
        )

    def _on_celda_click(ctx_celda: dict) -> None:
        if not puede_escribir:
            return
        if ctx_celda.get("tipo") == "ocupada":
            celda = ctx_celda.get("celda") or {}
            bid = celda.get("id")
            if bid is None:
                return
            with ui.menu() as menu:
                with ui.menu_item(on_click=lambda: (menu.close(), _abrir_dialog_editar(bid))):
                    with ui.row().classes("items-center gap-2"):
                        ThemeManager.icono(Icons.EDIT)
                        ui.label("Editar")
                with ui.menu_item(on_click=lambda: (menu.close(), _confirmar_eliminar(bid))):
                    with ui.row().classes("items-center gap-2"):
                        ThemeManager.icono(Icons.DELETE)
                        ui.label("Eliminar")
            menu.open()
        else:
            grupo_id = ctx_celda.get("grupo_id")
            if grupo_id is not None:
                _s["grupo_id"] = grupo_id
            _abrir_dialog_crear(
                dia_prefill=ctx_celda.get("dia", ""),
                hora_prefill=ctx_celda.get("hora_inicio", ""),
            )

    # =========================================================================
    # Handlers — generar
    # =========================================================================

    def _gen_seleccionar_plantilla(plantilla) -> None:
        _s["gen_plantilla_sel"] = plantilla
        _gen_cargar_franjas_sel()
        gen_refreshable.refresh()

    def _gen_plantilla_en_uso(plantilla_id: int) -> list:
        return [c for c in _s["gen_configs"]
                if getattr(c, "plantilla_id", None) == plantilla_id]

    def _gen_plantilla_generable(plantilla_id: int | None) -> tuple[bool, str]:
        try:
            return Container.generador_horario_service().plantilla_generable(plantilla_id)
        except Exception as exc:
            logger.error("Error verificando generabilidad de plantilla %s: %s", plantilla_id, exc)
            return False, "No se pudo verificar la plantilla de la configuración."

    def _gen_crear_plantilla(on_creada=None) -> None:
        def _guardar(datos: dict) -> "bool | None":
            nombre = (datos.get("nombre") or "").strip()
            if not nombre:
                toast_warning("El nombre de la plantilla es obligatorio")
                return False
            try:
                nueva = Container.infraestructura_service().crear_plantilla_simple(
                    nombre, datos.get("jornada", "UNICA"), list(datos.get("dias") or []),
                )
                _gen_cargar_plantillas()
                _s["gen_plantilla_sel"] = nueva
                _gen_cargar_franjas_sel()
                toast_success(f"Plantilla '{nombre}' creada")
                gen_refreshable.refresh()
                if on_creada:
                    on_creada(nueva)
            except ValueError as exc:
                toast_warning(_texto_error(exc))
                return False
            except Exception as exc:
                logger.error("Error creando plantilla: %s", exc)
                toast_error("No se pudo crear la plantilla")
                return False

        plantilla_form_dialog(on_submit=_guardar)

    def _gen_eliminar_plantilla(plantilla) -> None:
        usos = _gen_plantilla_en_uso(plantilla.id)
        if usos:
            nombres = ", ".join(getattr(c, "nombre", "?") for c in usos)
            toast_warning(f"No se puede eliminar: la usan las configuraciones: {nombres}")
            return

        def _ok() -> None:
            try:
                Container.infraestructura_service().eliminar_plantilla(plantilla.id)
                if _s.get("gen_plantilla_sel") and _s["gen_plantilla_sel"].id == plantilla.id:
                    _s["gen_plantilla_sel"] = None
                    _s["gen_franjas_sel"] = []
                _gen_cargar_plantillas()
                toast_success(f"Plantilla '{plantilla.nombre}' eliminada")
                gen_refreshable.refresh()
            except Exception as exc:
                logger.error("Error eliminando plantilla: %s", exc)
                toast_error("No se pudo eliminar la plantilla")

        confirm_dialog(
            titulo="Eliminar plantilla",
            mensaje=f"¿Eliminar la plantilla '{plantilla.nombre}'? Se eliminarán sus franjas.",
            on_confirm=_ok,
            variante="danger",
            texto_confirmar="Eliminar",
        )

    def _gen_activar_plantilla(plantilla) -> None:
        try:
            Container.infraestructura_service().activar_plantilla(plantilla.id)
            _gen_cargar_plantillas()
            _s["gen_plantilla_sel"] = next(
                (p for p in _s["gen_plantillas"] if p.id == plantilla.id), plantilla
            )
            toast_success(f"Plantilla '{plantilla.nombre}' activada")
            gen_refreshable.refresh()
        except Exception as exc:
            logger.error("Error activando plantilla: %s", exc)
            toast_error("No se pudo activar la plantilla")

    def _gen_filas_franjas_actuales() -> list[dict]:
        return [
            {
                "orden": f.orden,
                "hora_inicio": f.hora_inicio,
                "hora_fin": f.hora_fin,
                "tipo": f.tipo if isinstance(f.tipo, str) else f.tipo.value,
                "etiqueta": f.etiqueta,
            }
            for f in _s["gen_franjas_sel"]
        ]

    def _gen_guardar_franjas(filas: list[dict]) -> bool:
        p = _s.get("gen_plantilla_sel")
        if p is None:
            return False
        try:
            Container.infraestructura_service().guardar_franjas(p.id, filas)
            _gen_cargar_franjas_sel()
            toast_success("Franjas guardadas")
            gen_refreshable.refresh()
            return True
        except ValueError as exc:
            toast_warning(_texto_error(exc))
            return False
        except Exception as exc:
            logger.error("Error guardando franjas: %s", exc)
            toast_error("No se pudieron guardar las franjas")
            return False

    def _gen_agregar_franja() -> None:
        if _s.get("gen_plantilla_sel") is None:
            toast_warning("Selecciona o crea una plantilla primero")
            return

        def _submit(datos: dict) -> "bool | None":
            if not datos.get("hora_inicio") or not datos.get("hora_fin"):
                toast_warning("La hora de inicio y fin son obligatorias")
                return False
            siguiente = max((f.orden for f in _s["gen_franjas_sel"]), default=0) + 1
            filas = _gen_filas_franjas_actuales()
            filas.append({
                "orden": siguiente,
                "hora_inicio": datos["hora_inicio"], "hora_fin": datos["hora_fin"],
                "tipo": datos["tipo"], "etiqueta": datos["etiqueta"],
            })
            return _gen_guardar_franjas(filas)

        franja_form_dialog(None, on_submit=_submit)

    def _gen_editar_franja(orden: int) -> None:
        franja = next((f for f in _s["gen_franjas_sel"] if f.orden == orden), None)
        if franja is None:
            return

        def _submit(datos: dict) -> "bool | None":
            if not datos.get("hora_inicio") or not datos.get("hora_fin"):
                toast_warning("La hora de inicio y fin son obligatorias")
                return False
            filas = []
            for f in _s["gen_franjas_sel"]:
                if f.orden == orden:
                    filas.append({
                        "orden": orden,
                        "hora_inicio": datos["hora_inicio"], "hora_fin": datos["hora_fin"],
                        "tipo": datos["tipo"], "etiqueta": datos["etiqueta"],
                    })
                else:
                    filas.append({
                        "orden": f.orden, "hora_inicio": f.hora_inicio,
                        "hora_fin": f.hora_fin,
                        "tipo": f.tipo if isinstance(f.tipo, str) else f.tipo.value,
                        "etiqueta": f.etiqueta,
                    })
            return _gen_guardar_franjas(filas)

        franja_form_dialog(franja, on_submit=_submit)

    def _gen_eliminar_franja(orden: int) -> None:
        filas = [
            {
                "orden": idx + 1, "hora_inicio": f.hora_inicio, "hora_fin": f.hora_fin,
                "tipo": f.tipo if isinstance(f.tipo, str) else f.tipo.value,
                "etiqueta": f.etiqueta,
            }
            for idx, f in enumerate(
                sorted([f for f in _s["gen_franjas_sel"] if f.orden != orden], key=lambda x: x.orden)
            )
        ]
        _gen_guardar_franjas(filas)

    def _gen_cambiar_tab(valor: str) -> None:
        _s["gen_tab"] = valor
        gen_refreshable.refresh()

    def _gen_seleccionar_config(config_id: int | None) -> None:
        if config_id is None:
            _s["gen_config_sel"] = None
        else:
            _s["gen_config_sel"] = next((c for c in _s["gen_configs"] if c.id == config_id), None)
        _s["gen_resultado"] = None
        _s["gen_datos_preview"] = None
        _s["gen_eje_sel"] = None
        gen_refreshable.refresh()

    def _gen_config_dialog(config: Any | None = None) -> None:
        if not _s["gen_plantillas"]:
            toast_warning("Crea primero una plantilla horaria.")
            _gen_cambiar_tab("plantillas")
            _gen_crear_plantilla()
            return

        es_edicion = config is not None
        plantilla_opts = _gen_mapa_plantillas()
        grupo_opts = {g.id: g.codigo for g in _s["grupos"]}

        nombre_ini = getattr(config, "nombre", "") if es_edicion else ""
        plantilla_ini = getattr(config, "plantilla_id", None) if es_edicion else None
        grupos_ini = list(getattr(config, "grupos", []) or []) if es_edicion else []
        pesos_obj = getattr(config, "pesos", None) if es_edicion else None
        pesos_val = {
            "huecos": getattr(pesos_obj, "huecos", 1.0) if pesos_obj else 1.0,
            "distribucion": getattr(pesos_obj, "distribucion", 1.0) if pesos_obj else 1.0,
            "compactacion": getattr(pesos_obj, "compactacion", 0.5) if pesos_obj else 0.5,
        }
        pesos_extra_val = {
            "balance_diario":   getattr(pesos_obj, "balance_diario",   0.0) if pesos_obj else 0.0,
            "franja_preferida": getattr(pesos_obj, "franja_preferida", 0.0) if pesos_obj else 0.0,
            "dia_libre":        getattr(pesos_obj, "dia_libre",        0.0) if pesos_obj else 0.0,
            "hueco_comun":      getattr(pesos_obj, "hueco_comun",      0.0) if pesos_obj else 0.0,
        }
        restricciones_ini = getattr(config, "restricciones", {}) if es_edicion else {}
        restricciones_ini = restricciones_ini or {}
        min_max_ini = restricciones_ini.get("min_max_diario", {"modo": "preferente", "min": 0, "max": 8})

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

            def _nueva_plantilla_desde_config() -> None:
                dlg.close()
                _gen_cambiar_tab("plantillas")
                _gen_crear_plantilla()

            btn_ghost("Crear plantilla nueva…", icon=Icons.ADD,
                      on_click=_nueva_plantilla_desde_config)

            sel_grupos = ui.select(
                options=grupo_opts, label="Grupos (vacío = todos)",
                value=grupos_ini, multiple=True,
            ).classes("andes-input w-full").props("outlined use-chips")

            ui.label("Pesos del motor").classes("font-h3 u-mt-md")
            ui.label(
                "Indican cuánto prioriza el motor cada criterio de calidad al armar el "
                "horario: 0 = ignorar · mayor = más importante. Son preferencias, no "
                "reglas obligatorias."
            ).classes("text-caption text-muted u-mb-sm")

            def _peso_item(key: str, label: str, hint: str, valor: float, destino: dict) -> None:
                with ui.element("div").classes("gen-peso-item"):
                    with ui.element("div").classes("gen-peso-head"):
                        ui.label(label).classes("gen-peso-label")
                        vlbl = ui.label(
                            f"{_magnitud_peso(valor)} · {valor:.1f}"
                        ).classes("gen-peso-valor")
                    sl = ui.slider(min=0.0, max=2.0, step=0.1, value=float(valor)).props("label")
                    sl.on(
                        "update:model-value",
                        lambda e, l=vlbl: l.set_text(
                            f"{_magnitud_peso(float(e.args))} · {float(e.args):.1f}"
                        ),
                    )
                    ui.label(hint).classes("gen-peso-hint")
                    destino[key] = sl

            catalogo_pesos = Container.generador_horario_service().catalogo_pesos()
            pesos_def = catalogo_pesos["principales"]
            pesos_extra = catalogo_pesos["avanzados"]

            sliders: dict[str, Any] = {}
            with ui.element("div").classes("gen-pesos-grid u-mt-sm"):
                for key, label, hint in pesos_def:
                    _peso_item(key, label, hint, pesos_val[key], sliders)

            ui.separator().classes("my-3")
            ui.label("Optimización avanzada (opcional)").classes("font-h3 u-mt-md")
            ui.label(
                "Ajustes finos de calidad para los docentes. Déjalos en 0 si no los necesitas."
            ).classes("text-caption text-muted u-mb-sm")
            sliders_extra: dict[str, Any] = {}
            with ui.element("div").classes("gen-pesos-grid u-mt-sm"):
                for key, label, hint in pesos_extra:
                    _peso_item(key, label, hint, pesos_extra_val[key], sliders_extra)

            ui.separator().classes("my-3")
            ui.label("Restricción de horas diarias por docente").classes("font-h3")
            ui.label(
                "Permite limitar cuántas horas puede tener un docente en un solo día."
            ).classes("text-caption text-muted")
            with ui.row().classes("gap-4 items-end mt-2"):
                sel_modo_minmax = ui.select(
                    {"preferente": "Preferente (coste blando)", "estricta": "Estricta (dura)"},
                    label="Modo",
                    value=min_max_ini.get("modo", "preferente"),
                ).classes("andes-input w-48").props("outlined")
                in_min_horas = ui.number(
                    label="Mín. horas/día docente",
                    value=min_max_ini.get("min", 0),
                    min=0, max=10, step=1,
                ).classes("andes-input w-40").props("outlined")
                in_max_horas = ui.number(
                    label="Máx. horas/día docente",
                    value=min_max_ini.get("max", 8),
                    min=1, max=12, step=1,
                ).classes("andes-input w-40").props("outlined")

            def _guardar() -> None:
                nombre = str(in_nombre.value or "").strip()
                plantilla_id = sel_plantilla.value
                grupos = list(sel_grupos.value or [])
                pesos = {k: round(float(sliders[k].value), 1) for k in sliders}
                pesos_ext = {k: round(float(sliders_extra[k].value), 1) for k in sliders_extra}
                pesos_completo = {**pesos, **pesos_ext}

                infra = Container.infraestructura_service()
                restricciones = infra.construir_restricciones(
                    in_min_horas.value or 0,
                    in_max_horas.value if in_max_horas.value is not None else 8,
                    sel_modo_minmax.value,
                )

                if not nombre:
                    toast_warning("El nombre de la configuración es obligatorio")
                    return
                if not plantilla_id:
                    toast_warning("Selecciona una plantilla")
                    return
                try:
                    if es_edicion:
                        infra.actualizar_config_generacion(
                            config.id,
                            nombre=nombre,
                            plantilla_id=plantilla_id,
                            grupos=grupos,
                            pesos=pesos_completo,
                            restricciones=restricciones,
                        )
                        toast_success("Configuración actualizada")
                    else:
                        infra.crear_config_generacion(
                            nombre=nombre,
                            periodo_id=_s["gen_periodo_id"],
                            anio_id=_s["gen_anio_id"],
                            plantilla_id=plantilla_id,
                            grupos=grupos if grupos else None,
                            pesos=pesos_completo,
                            restricciones=restricciones,
                        )
                        toast_success("Configuración creada")
                    dlg.close()
                    _gen_cargar_configs()
                    gen_refreshable.refresh()
                except Exception as exc:
                    logger.error("Error guardando configuración de generación: %s", exc)
                    toast_error("No se pudo guardar la configuración")

            with ui.row().classes("base-form-footer w-full gap-2 justify-end u-mt-md"):
                btn_secondary("Cancelar", on_click=dlg.close)
                btn_primary("Guardar", on_click=_guardar)

        dlg.open()

    def _gen_duplicar_config(config_id: int) -> None:
        try:
            Container.infraestructura_service().duplicar_config_generacion(config_id)
            toast_success("Configuración duplicada")
            _gen_cargar_configs()
            gen_refreshable.refresh()
        except Exception as exc:
            logger.error("Error duplicando configuración: %s", exc)
            toast_error("No se pudo duplicar la configuración")

    def _gen_eliminar_config(config: Any) -> None:
        def _confirmar() -> None:
            try:
                Container.infraestructura_service().eliminar_config_generacion(config.id)
                toast_success("Configuración eliminada")
                if _s.get("gen_config_sel") and _s["gen_config_sel"].id == config.id:
                    _gen_seleccionar_config(None)
                    return
                _gen_cargar_configs()
                gen_refreshable.refresh()
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

    def _gen_cambiar_perspectiva(valor: str) -> None:
        _s["gen_perspectiva"] = valor
        _s["gen_eje_sel"] = None
        gen_refreshable.refresh()

    def _gen_cambiar_eje(valor) -> None:
        _s["gen_eje_sel"] = valor
        gen_refreshable.refresh()

    def _gen_generar_config() -> None:
        config = _s.get("gen_config_sel")
        if not config or getattr(config, "id", None) is None:
            toast_warning("Selecciona una configuración para generar")
            return
        if _s["gen_generando"]:
            return
        _s["gen_generando"] = True
        gen_refreshable.refresh()

        client = ng_context.client

        async def _trabajo_coro() -> None:
            resultado = None
            error = False
            try:
                loop = asyncio.get_event_loop()
                resultado = await loop.run_in_executor(
                    None,
                    lambda: Container.generador_horario_service().generar(
                        config.id,
                        crear_escenario=True,
                        optimizar=True,
                    ),
                )
            except Exception as exc:
                logger.error("Error ejecutando generador: %s", exc)
                error = True

            _s["gen_generando"] = False
            with client:
                if error:
                    toast_error("Error al generar el horario")
                else:
                    _s["gen_resultado"] = resultado
                    _s["gen_eje_sel"] = None
                    _gen_cargar_configs()
                    _gen_cargar_preview()
                    if getattr(resultado, "valido", False):
                        toast_success("Generación completada")
                    else:
                        toast_warning("Generación parcial: revisa las incidencias")
                gen_refreshable.refresh()

        background_tasks.create(_trabajo_coro())

    def _gen_activar_escenario(config: Any, escenario_id: int) -> None:
        def _confirmar() -> None:
            try:
                infra = Container.infraestructura_service()
                infra.activar_escenario(escenario_id)
                estado = getattr(config, "estado", "borrador")
                if estado == "generado":
                    try:
                        infra.cambiar_estado_config(config.id, "aplicado")
                    except Exception as exc:
                        logger.warning("No se pudo transicionar config a aplicado: %s", exc)
                toast_success("Escenario activado")
                _gen_cargar_configs()
                gen_refreshable.refresh()
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

    # =========================================================================
    # Navigation helper (hub level)
    # =========================================================================

    def _cambiar_seccion(sec: str) -> None:
        _s["seccion"] = sec
        hub_refreshable.refresh()

    # =========================================================================
    # Render helpers — generar
    # =========================================================================

    def _gen_render_tab_plantillas() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("gen-section-head"):
                ui.label("Plantillas horarias").classes("text-subtitle1 font-semibold")
                if puede_escribir:
                    btn_primary("Nueva plantilla", icon=Icons.ADD,
                                on_click=lambda: _gen_crear_plantilla())

            if not _s["gen_plantillas"]:
                empty_state(
                    icono=Icons.SCHEDULE,
                    titulo="Sin plantillas horarias",
                    descripcion="Crea una plantilla para definir la rejilla de franjas.",
                )
                return

            sel = _s.get("gen_plantilla_sel")
            with ui.element("div").classes("parrilla-chips u-mt-sm"):
                for p in _s["gen_plantillas"]:
                    is_sel = sel and sel.id == p.id
                    chip_cls = "parrilla-chip" + (" parrilla-chip-activo" if is_sel else "")
                    chip = ui.element("div").classes(chip_cls)
                    chip.on("click", lambda _, pl=p: _gen_seleccionar_plantilla(pl))
                    with chip:
                        with ui.row().classes("items-center gap-1"):
                            ui.label(f"{p.nombre} ({p.jornada})")
                            if getattr(p, "activa", False):
                                status_badge("Activa", variante="success")

        sel = _s.get("gen_plantilla_sel")
        if sel is None:
            return

        with ui.element("div").classes("panel-card u-mt-md"):
            with ui.element("div").classes("gen-section-head"):
                ui.label(f"Franjas — {sel.nombre}").classes("text-subtitle1 font-semibold")
                if puede_escribir:
                    with ui.row().classes("gap-2"):
                        if not getattr(sel, "activa", False):
                            btn_primary("Activar", icon="check_circle",
                                        on_click=lambda: _gen_activar_plantilla(sel))
                        btn_danger("Eliminar plantilla", icon=Icons.DELETE,
                                   on_click=lambda: _gen_eliminar_plantilla(sel))
            dias_txt = ", ".join(sel.dias_activos) if getattr(sel, "dias_activos", None) else "—"
            ui.label(f"Jornada {sel.jornada} · Días: {dias_txt}").classes(
                "text-xs text-secondary u-mb-sm"
            )
            render_franjas_editor(
                _s["gen_franjas_sel"],
                on_add=_gen_agregar_franja,
                on_edit=_gen_editar_franja,
                on_delete=_gen_eliminar_franja,
                puede_editar=puede_escribir,
            )

        with ui.element("div").classes("panel-card u-mt-md"):
            ui.label("Vista previa de la rejilla").classes("text-subtitle2 font-semibold")
            render_plantilla_preview(sel, _s["gen_franjas_sel"])

    def _gen_render_lista() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("gen-section-head"):
                ui.label("Configuraciones de generación").classes("text-subtitle1 font-semibold")
                with ui.row().classes("gap-2 flex-wrap"):
                    btn_primary("Nueva configuración", icon=Icons.ADD,
                                on_click=lambda: _gen_config_dialog(None))
                    btn_secondary(
                        "Recargar", icon=Icons.REFRESH,
                        on_click=lambda: (_gen_cargar_configs(), gen_refreshable.refresh()),
                    )

            if not _s["gen_configs"]:
                empty_state(
                    icono=Icons.AUTO_MODE,
                    titulo="Sin configuraciones de generación",
                    descripcion="Crea una configuración para generar un horario.",
                )
                return

            mapa_pl = _gen_mapa_plantillas()
            sel = _s.get("gen_config_sel")
            sel_id = getattr(sel, "id", None) if sel else None

            with ui.element("div").classes("overflow-auto"):
                with ui.element("table").classes("gen-config-table"):
                    with ui.element("thead"):
                        with ui.element("tr"):
                            for col in ("Nombre", "Plantilla", "Grupos", "Estado", "Acciones"):
                                ui.element("th").text = col
                    with ui.element("tbody"):
                        for config in _s["gen_configs"]:
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
                                            on_click=lambda _, c=config: _gen_seleccionar_config(c.id),
                                        )
                                        btn_ghost(
                                            "Editar", size="sm", icon=Icons.EDIT,
                                            on_click=lambda _, c=config: _gen_config_dialog(c),
                                        )
                                        btn_ghost(
                                            "Duplicar", size="sm", icon="content_copy",
                                            on_click=lambda _, c=config: _gen_duplicar_config(c.id),
                                        )
                                        btn_danger(
                                            "Eliminar", size="sm", icon=Icons.DELETE,
                                            on_click=lambda _, c=config: _gen_eliminar_config(c),
                                        )

    def _gen_render_resultado(resultado: Any) -> None:
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

        with ui.row().classes("items-center gap-2 u-mb-sm"):
            ui.label("Resultado de la generación").classes("text-subtitle2 font-semibold")
            if valido:
                status_badge("Válido", variante="success")
            elif colocados > 0:
                status_badge("Parcial", variante="warning")
            else:
                status_badge("Inválido", variante="error")

        with ui.element("div").classes("parrilla-metricas"):
            for _val, _lbl in [
                (str(total), "Requeridos"),
                (str(colocados), "Colocados"),
                (str(no_colocados), "No colocados"),
                (f"{pct}%", "% Colocado"),
                (str(huecos), "Huecos"),
                (f"{costo_final:.1f}", "Costo final"),
            ]:
                with ui.element("div").classes("parrilla-metrica"):
                    ui.label(_val).classes("parrilla-metrica-valor")
                    ui.label(_lbl).classes("parrilla-metrica-label")

        incidencias = list(getattr(resultado, "incidencias", []) or [])
        if incidencias:
            with ui.element("div").classes("gen-incidencias u-mt-md"):
                with ui.row().classes("items-center gap-2"):
                    ThemeManager.icono(Icons.WARNING, size=18, color="var(--color-warning)")
                    ui.label(f"Incidencias ({len(incidencias)})").classes(
                        "text-sm font-semibold"
                    )
                for texto in incidencias:
                    with ui.element("div").classes("gen-incidencia-item"):
                        ui.label(str(texto))

        if _s.get("gen_datos_preview"):
            _gen_render_preview()

    def _gen_render_preview() -> None:
        datos = _s["gen_datos_preview"]
        perspectiva = _s["gen_perspectiva"]
        with ui.element("div").classes("panel-card u-mt-md"):
            ui.label("Vista previa del escenario generado").classes(
                "text-subtitle2 font-semibold"
            )
            with ui.element("div").classes("parrilla-toolbar u-mt-sm"):
                _gen_segmento(
                    [("Grupo", "Grupo"), ("Docente", "Docente"), ("Sala", "Sala")],
                    perspectiva,
                    _gen_cambiar_perspectiva,
                )
            eje_opts = _opciones_eje(datos, perspectiva)
            if eje_opts:
                eje_sel = _s["gen_eje_sel"]
                if eje_sel not in eje_opts:
                    eje_sel = next(iter(eje_opts))
                    _s["gen_eje_sel"] = eje_sel
                _nombre_eje = {"Grupo": "grupo", "Docente": "docente", "Sala": "sala"}[perspectiva]
                ui.label(f"Selecciona un {_nombre_eje} para ver su horario").classes(
                    "parrilla-chips-label"
                )
                with ui.element("div").classes("parrilla-chips"):
                    for clave, etiqueta in eje_opts.items():
                        activo = (clave == eje_sel)
                        chip_cls = "parrilla-chip" + (" parrilla-chip-activo" if activo else "")
                        _chip = ui.element("div").classes(chip_cls)
                        _chip.on("click", lambda _, c=clave: _gen_cambiar_eje(c))
                        with _chip:
                            ui.label(str(etiqueta))

            render_parrilla(
                datos=datos,
                perspectiva=perspectiva,
                eje_sel=_s["gen_eje_sel"],
            )

    def _gen_render_detalle() -> None:
        config = _s.get("gen_config_sel")
        if not config:
            return

        estado = getattr(config, "estado", "borrador")
        badge_txt, badge_var = _ESTADO_BADGE.get(estado, (estado.title(), "neutral"))
        resultado = _s.get("gen_resultado")
        escenario_id = getattr(resultado, "escenario_id", None) if resultado else None
        escenario_destino = getattr(config, "escenario_destino_id", None)
        valido = bool(getattr(resultado, "valido", False)) if resultado else False
        generable, motivo_no_generable = _gen_plantilla_generable(
            getattr(config, "plantilla_id", None)
        )

        with ui.element("div").classes("panel-card u-mt-md"):
            with ui.element("div").classes("gen-section-head"):
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    ui.label(getattr(config, "nombre", "")).classes("text-subtitle1 font-semibold")
                    status_badge(badge_txt, variante=badge_var)
                with ui.row().classes("gap-2 flex-wrap"):
                    btn_primary(
                        "Generar horario", icon="play_arrow",
                        on_click=_gen_generar_config,
                        disabled=_s["gen_generando"] or not generable,
                    )
                    puede_activar_resultado = bool(escenario_id) and valido
                    puede_activar_config = bool(escenario_destino) and estado == "generado"
                    if puede_activar_resultado or puede_activar_config:
                        target = escenario_id if puede_activar_resultado else escenario_destino
                        btn_secondary(
                            "Activar este escenario", icon="check_circle",
                            on_click=lambda c=config, e=target: _gen_activar_escenario(c, e),
                        )
                        btn_ghost(
                            "Ver en horarios", icon="calendar_today",
                            on_click=lambda e=target: ui.navigate.to(f"/horarios?escenario={e}"),
                        )

            if not generable:
                with ui.row().classes("items-center gap-2 u-mt-sm"):
                    ThemeManager.icono(Icons.WARNING, size=18, color="var(--color-warning)")
                    ui.label(
                        f"No se puede generar: {motivo_no_generable} "
                        "Ajusta la plantilla en la pestaña «Plantillas»."
                    ).classes("text-sm text-warning")

            if _s["gen_generando"]:
                with ui.element("div").classes("gen-loading"):
                    ui.spinner(size="lg")
                    ui.label("Generando horario… esto puede tardar unos segundos.")
                return

            if not resultado:
                ui.label(
                    "Pulsa «Generar horario» para ejecutar el motor sobre esta configuración."
                ).classes("text-secondary text-sm")
                return

            _gen_render_resultado(resultado)

    # =========================================================================
    # Render helper — preparar
    # =========================================================================

    def _render_preparar() -> None:
        anio_id    = _s["anio_id"]
        periodo_id = _s["periodo_id"]

        # Intentar obtener plantilla_id desde la config seleccionada o la plantilla activa
        plantilla_id: int = 0
        try:
            if _s.get("gen_plantilla_sel"):
                plantilla_id = _s["gen_plantilla_sel"].id
            elif _s.get("gen_config_sel"):
                plantilla_id = getattr(_s["gen_config_sel"], "plantilla_id", 0) or 0
            else:
                plantillas = Container.infraestructura_service().listar_plantillas()
                activas = [p for p in plantillas if getattr(p, "activa", False)]
                if activas:
                    plantilla_id = activas[0].id
                elif plantillas:
                    plantilla_id = plantillas[0].id
        except Exception as exc:
            logger.error("Error obteniendo plantilla para preparar: %s", exc)

        # Ejecutar validadores
        reporte = []
        error_validacion = None
        if anio_id and periodo_id:
            try:
                svc = Container.preparacion_horario_service()
                reporte = svc.validar(anio_id, periodo_id, plantilla_id)
            except Exception as exc:
                logger.error("Error en validación de preparación: %s", exc)
                error_validacion = str(exc)
        else:
            error_validacion = "No hay año o periodo activo configurado."

        puede_gen = Container.preparacion_horario_service().puede_generar(reporte) if reporte else False

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center justify-between u-mb-sm"):
                ui.label("Preparar la generación").classes("text-subtitle1 font-semibold")
                btn_ghost(
                    "Actualizar",
                    icon="refresh",
                    on_click=lambda: hub_refreshable.refresh(),
                )

            if error_validacion:
                ui.label(error_validacion).classes("text-xs text-secondary u-mb-md")

            if not reporte:
                ui.label(
                    "Selecciona un año y periodo activo para ver el estado de preparación."
                ).classes("text-sm text-secondary")
            else:
                for puerta in reporte:
                    _color = (
                        "var(--color-success)" if puerta.ok
                        else ("var(--color-error)" if puerta.severidad == "dura"
                              else "var(--color-warning)")
                    )
                    _icono = (
                        "check_circle" if puerta.ok
                        else ("cancel" if puerta.severidad == "dura" else "warning")
                    )
                    with ui.row().classes("items-start gap-3 py-3 border-b"):
                        ThemeManager.icono(_icono, size=20, color=_color)  # DYNAMIC: color según estado de la puerta
                        with ui.element("div").classes("flex-1"):
                            with ui.row().classes("items-center gap-2"):
                                ui.label(puerta.titulo).classes("font-semibold text-sm")
                                if puerta.severidad == "advertencia":
                                    status_badge("advertencia", variante="warning")
                            ui.label(puerta.detalle).classes("text-xs text-secondary")
                        if not puerta.ok and puerta.fix_ruta:
                            btn_ghost(
                                "Corregir",
                                icon="arrow_forward",
                                on_click=lambda _, r=puerta.fix_ruta: ui.navigate.to(r),
                            )

                with ui.row().classes("u-mt-md"):
                    if puede_gen:
                        btn_primary(
                            "Generar horario",
                            icon=Icons.AUTO_MODE,
                            on_click=lambda: _cambiar_seccion("generar"),
                        )
                    else:
                        with ui.element("div"):
                            btn_primary(
                                "Generar horario",
                                icon=Icons.AUTO_MODE,
                                on_click=lambda: None,
                            ).props("disable")
                            ui.label(
                                "Resuelve las puertas rojas para habilitar la generación."
                            ).classes("text-xs text-secondary u-mt-xs")

    # =========================================================================
    # Render helper — docente
    # =========================================================================

    def _render_docente() -> None:
        with ui.element("div").classes("panel-card"):
            _segmento(
                ["Semana", "Día"],
                "Día" if _s["doc_vista_grid"] == "dia" else "Semana",
                lambda v: _toggle_vista_doc("dia" if v == "Día" else "semana"),
            )
            # Al elegir "Día" se muestran chips de día (mismo control que la
            # vista de directivos) por si se quiere cambiar el día visualizado.
            if _s["doc_vista_grid"] == "dia":
                with ui.element("div").classes("parrilla-chips u-mt-sm"):
                    for d in _DIAS_BASE:
                        chip_cls = "parrilla-chip" + (
                            " parrilla-chip-activo" if d == _s["doc_dia_sel"] else ""
                        )
                        _chip = ui.element("div").classes(chip_cls)
                        _chip.on("click", lambda _, dd=d: _cambiar_dia_doc(dd))
                        with _chip:
                            ui.label(d)

        doc_grilla_refreshable()

        # Asignaciones propias (solo lectura)
        with ui.element("div").classes("panel-card"):
            ui.label("Mis asignaciones").classes("text-subtitle1 font-semibold u-mb-sm")
            asigs = _s["doc_asignaciones"]
            if not asigs:
                empty_state(
                    icono=Icons.SUBJECTS,
                    titulo="Sin asignaciones",
                    descripcion="No tienes asignaciones registradas en el periodo activo.",
                )
            else:
                for a in asigs:
                    with ui.row().classes("items-center gap-3 py-2 border-b"):
                        ThemeManager.icono(Icons.SUBJECTS, size=18)
                        with ui.element("div"):
                            ui.label(a.asignatura_nombre).classes("text-sm font-semibold")
                            ui.label(f"Grupo {a.grupo_codigo}").classes("text-xs text-secondary")

    # =========================================================================
    # Carga masiva (inline, uses _s["lote_*"])
    # =========================================================================

    def _seccion_carga_masiva() -> None:

        @ui.refreshable
        def reporte_lote_refreshable() -> None:
            reporte = _s["lote_reporte"]
            if reporte is None:
                return
            with ui.element("div").classes("u-mt-sm"):
                ui.label(
                    f"Análisis: {reporte.validas} válidas, {reporte.invalidas} con error"
                ).classes("text-sm text-muted u-mb-xs")
                with ui.element("div").classes("overflow-auto"):
                    with ui.element("table").classes("w-full border-collapse text-xs"):
                        with ui.element("thead"):
                            with ui.element("tr"):
                                for col in ("#", "Estado", "Resumen", "Motivo"):
                                    with ui.element("th").classes(
                                        "border px-2 py-1 text-left bg-surface-alt"
                                    ):
                                        ui.label(str(col))
                        with ui.element("tbody"):
                            for f in reporte.filas:
                                with ui.element("tr"):
                                    with ui.element("td").classes("border px-2 py-1"):
                                        ui.label(str(f.indice + 1))
                                    with ui.element("td").classes("border px-2 py-1"):
                                        status_badge(
                                            "OK" if f.ok else "Error",
                                            variante="success" if f.ok else "danger",
                                        )
                                    with ui.element("td").classes("border px-2 py-1"):
                                        ui.label(str(f.resumen))
                                    with ui.element("td").classes("border px-2 py-1"):
                                        ui.label(str(f.motivo or ""))
                with ui.row().classes("gap-2 u-mt-sm"):
                    if reporte.todo_ok:
                        btn_primary("Aplicar todo", icon="upload",
                                    on_click=lambda: _aplicar_lote(False))
                    if reporte.validas > 0:
                        btn_secondary(f"Aplicar solo válidas ({reporte.validas})",
                                      icon="check", on_click=lambda: _aplicar_lote(True))

        def _descargar_plantilla() -> None:
            periodo_id = _s.get("periodo_id")
            if not periodo_id:
                toast_warning("No hay periodo activo seleccionado.")
                return
            filas = Container.horario_service().plantilla_filas(periodo_id)
            if not filas:
                toast_warning("No hay asignaciones activas en el periodo.")
                return
            data = Container.exporter_service().exportar_csv(filas)
            ui.download(data, filename="plantilla_horario.csv")

        def _descargar_horario() -> None:
            esc = _s.get("escenario_sel")
            if esc is None:
                toast_warning("No hay escenario seleccionado.")
                return
            filas = Container.horario_service().filas_exportables(esc.id)
            if not filas:
                toast_warning("El escenario no tiene bloques para exportar.")
                return
            data = Container.exporter_service().exportar_csv(filas)
            ui.download(data, filename=f"horario_{esc.nombre}.csv")

        def _on_upload(e) -> None:
            try:
                raw = e.content.read()
                text = raw.decode("utf-8-sig")
                filas = list(csv.DictReader(io.StringIO(text)))
                if not filas:
                    toast_warning("El archivo no tiene filas de datos.")
                    return
                esc = _s.get("escenario_sel")
                if not esc:
                    toast_warning("Selecciona un escenario primero.")
                    return
                _s["lote_filas_raw"] = filas
                reporte = Container.horario_service().analizar_lote(
                    esc.id, _s.get("periodo_id") or 0, filas
                )
                _s["lote_reporte"] = reporte
                reporte_lote_refreshable.refresh()
            except Exception as exc:
                logger.error("Error procesando archivo: %s", exc)
                toast_error(f"Error al procesar el archivo: {exc}")

        def _aplicar_lote(solo_validas: bool) -> None:
            esc = _s.get("escenario_sel")
            if not esc or not _s["lote_filas_raw"]:
                toast_warning("Sin datos para aplicar.")
                return
            try:
                resultado = Container.horario_service().aplicar_lote(
                    esc.id, _s.get("periodo_id") or 0,
                    _s["lote_filas_raw"], solo_validas=solo_validas,
                )
                if resultado.creados == 0 and not solo_validas:
                    toast_warning("No se creó ningún bloque. Revisa los errores del reporte.")
                else:
                    toast_success(f"{resultado.creados} bloques creados, {resultado.omitidos} omitidos.")
                    _s["lote_reporte"] = None
                    _s["lote_filas_raw"] = []
                    _cargar_bloques_escenario()
                    parrilla_unificada_refreshable.refresh()
                    reporte_lote_refreshable.refresh()
            except Exception as exc:
                logger.error("Error aplicando lote: %s", exc)
                toast_error(_texto_error(exc))

        with ui.element("div").classes("panel-card u-mt-sm"):
            with ui.row().classes("items-center justify-between u-mb-sm"):
                ui.label("Carga masiva de bloques").classes("text-subtitle1 font-semibold")
                with ui.row().classes("gap-2"):
                    btn_secondary("Descargar plantilla", icon="download",
                                  on_click=_descargar_plantilla)
                    if puede_escribir:
                        btn_secondary("Descargar horario", icon="table_view",
                                      on_click=_descargar_horario)
            ui.label(
                "Columnas requeridas: asignacion_id, dia_semana, hora_inicio, hora_fin, sala"
            ).classes("text-caption text-muted u-mb-xs")
            ui.upload(label="Subir CSV", on_upload=_on_upload, auto_upload=True).classes("w-full")
            reporte_lote_refreshable()

    # =========================================================================
    # @ui.refreshable functions — ALL defined at TOP LEVEL of page function
    # =========================================================================

    @ui.refreshable
    def escenarios_refreshable() -> None:
        escenarios = _s["escenarios"]
        sel = _s["escenario_sel"]
        # Edición solo en la sección "Editar"; "Visualizar" es de solo lectura.
        editable = puede_escribir and _s["seccion"] == "editar"

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center justify-between flex-wrap gap-2"):
                ui.label("Escenarios de horario").classes("text-subtitle1 font-semibold")
                if editable:
                    btn_secondary("Nuevo escenario", icon="add", on_click=_crear_escenario_dialog)

            if not escenarios:
                ui.label("No hay escenarios creados para este año.").classes("text-caption text-muted u-mt-sm")
                return

            with ui.element("div").classes("parrilla-chips u-mt-sm"):
                for esc in escenarios:
                    is_sel = sel and sel.id == esc.id
                    chip_cls = "parrilla-chip" + (" parrilla-chip-activo" if is_sel else "")
                    with ui.element("div").classes(chip_cls).on("click", lambda _, e=esc: _seleccionar_escenario(e)):
                        with ui.row().classes("items-center gap-1"):
                            ui.label(esc.nombre)
                            if esc.activo:
                                status_badge("Activo", variante="success")

            if sel and editable:
                with ui.row().classes("gap-2 u-mt-sm flex-wrap"):
                    if not sel.activo:
                        btn_primary("Activar", icon="check_circle",
                                    on_click=lambda: _vis_activar_escenario(sel.id))
                    btn_secondary("Renombrar", icon="edit",
                                  on_click=lambda: _renombrar_escenario_dialog(sel))
                    btn_secondary("Duplicar", icon="content_copy",
                                  on_click=lambda: _duplicar_escenario_dialog(sel))
                    btn_danger("Eliminar", icon="delete",
                               on_click=lambda: _eliminar_escenario_confirm(sel))

    @ui.refreshable
    def parrilla_unificada_refreshable() -> None:
        esc = _s["escenario_sel"]
        # Edición solo en la sección "Editar"; "Visualizar" es de solo lectura.
        editable = puede_escribir and _s["seccion"] == "editar"
        with ui.element("div").classes("panel-card u-mt-sm"):
            with ui.row().classes("items-center justify-between flex-wrap gap-2"):
                ui.label("Parrilla").classes("text-subtitle1 font-semibold")
                with ui.row().classes("items-center gap-2"):
                    _segmento(
                        ["Por entidad", "Tablero maestro"],
                        _s["parrilla_modo"],
                        _cambiar_modo,
                    )
                    if editable:
                        btn_secondary("Agregar bloque", icon="add",
                                      on_click=lambda: _abrir_dialog_crear())

            if not esc:
                empty_state(
                    icono=Icons.SCHEDULE,
                    titulo="Sin escenario seleccionado",
                    descripcion="Selecciona un escenario para ver la parrilla.",
                )
                return

            datos = _parrilla_cargar_datos()
            m = _parrilla_cargar_metricas()
            with ui.element("div").classes("parrilla-metricas"):
                for _val, _lbl in [
                    (str(m["total_bloques"]), "Bloques"),
                    (str(m["n_grupos"]), "Grupos"),
                    (str(m["n_docentes"]), "Docentes"),
                    (str(m["huecos_grupo"]), "Huecos"),
                    (f"{m['ocupacion_pct']}%", "Ocupación"),
                ]:
                    with ui.element("div").classes("parrilla-metrica"):
                        ui.label(_val).classes("parrilla-metrica-valor")
                        ui.label(_lbl).classes("parrilla-metrica-label")

            if not datos["celdas"] or not datos["franjas"]:
                empty_state(
                    icono=Icons.SCHEDULE,
                    titulo="Escenario sin bloques",
                    descripcion="No hay bloques para visualizar en la parrilla.",
                    cta_label="Agregar bloque" if editable else None,
                    cta_on_click=(lambda: _abrir_dialog_crear()) if editable else None,
                    cta_icono="add",
                )
                return

            areas = _parrilla_cargar_areas()
            dias_activos = datos["dias"] or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
            f_areas = _s["parrilla_filtro_areas"]

            if _s["parrilla_modo"] == "Tablero maestro":
                dia_maestro = _s["parrilla_dia_maestro"]
                if dia_maestro not in dias_activos:
                    dia_maestro = dias_activos[0]
                    _s["parrilla_dia_maestro"] = dia_maestro

                ui.label("Selecciona el día").classes("parrilla-chips-label")
                with ui.element("div").classes("parrilla-chips"):
                    for d in dias_activos:
                        activo = (d == dia_maestro)
                        chip_cls = "parrilla-chip" + (" parrilla-chip-activo" if activo else "")
                        _chip = ui.element("div").classes(chip_cls)
                        _chip.on("click", lambda _, dd=d: _cambiar_dia_maestro(dd))
                        with _chip:
                            ui.label(str(d))

                with ui.element("div").classes("parrilla-toolbar"):
                    ui.label("Filtrar:").classes("parrilla-filtro-label")
                    if areas:
                        area_opts = {a["area_id"]: a["area_nombre"] for a in areas}
                        area_val = (
                            [aid for aid in f_areas if aid in area_opts]
                            if f_areas is not None else list(area_opts)
                        )
                        ui.select(
                            label="Áreas",
                            options=area_opts,
                            value=area_val,
                            multiple=True,
                            on_change=lambda e: _cambiar_filtro_areas(e.value),
                        ).classes("w-64")

                render_tablero_maestro(
                    datos=datos,
                    dia=dia_maestro,
                    areas_filtro=f_areas,
                    on_celda_click=_on_celda_click,
                    puede_editar=editable,
                )

            else:
                perspectiva = _s["parrilla_perspectiva"]
                f_dias = _s["parrilla_filtro_dias"]

                with ui.element("div").classes("parrilla-toolbar"):
                    _segmento(
                        ["Grupo", "Docente", "Sala"],
                        perspectiva,
                        _cambiar_perspectiva,
                    )

                eje_opts = _opciones_eje(datos, perspectiva)
                if eje_opts:
                    eje_sel = _s["parrilla_eje_sel"]
                    if eje_sel not in eje_opts:
                        eje_sel = next(iter(eje_opts))
                        _s["parrilla_eje_sel"] = eje_sel
                    _nombre_eje = {"Grupo": "grupo", "Docente": "docente", "Sala": "sala"}[perspectiva]
                    ui.label(f"Selecciona un {_nombre_eje} para ver su horario").classes("parrilla-chips-label")
                    with ui.element("div").classes("parrilla-chips"):
                        for clave, etiqueta in eje_opts.items():
                            activo = (clave == eje_sel)
                            chip_cls = "parrilla-chip" + (" parrilla-chip-activo" if activo else "")
                            _chip = ui.element("div").classes(chip_cls)
                            _chip.on("click", lambda _, c=clave: _cambiar_eje(c))
                            with _chip:
                                ui.label(str(etiqueta))

                with ui.element("div").classes("parrilla-toolbar"):
                    ui.label("Filtrar:").classes("parrilla-filtro-label")
                    if areas:
                        area_opts = {a["area_id"]: a["area_nombre"] for a in areas}
                        area_val = (
                            [aid for aid in f_areas if aid in area_opts]
                            if f_areas is not None else list(area_opts)
                        )
                        ui.select(
                            label="Áreas",
                            options=area_opts,
                            value=area_val,
                            multiple=True,
                            on_change=lambda e: _cambiar_filtro_areas(e.value),
                        ).classes("w-64")
                    dia_opts = {d: d for d in dias_activos}
                    dia_val = (
                        [d for d in f_dias if d in dia_opts]
                        if f_dias is not None else list(dia_opts)
                    )
                    ui.select(
                        label="Días",
                        options=dia_opts,
                        value=dia_val,
                        multiple=True,
                        on_change=lambda e: _cambiar_filtro_dias(e.value),
                    ).classes("w-64")

                render_parrilla(
                    datos=datos,
                    perspectiva=perspectiva,
                    eje_sel=_s["parrilla_eje_sel"],
                    dias_filtro=f_dias,
                    areas_filtro=f_areas,
                    on_celda_click=_on_celda_click,
                    puede_editar=editable,
                )

            if areas:
                ui.label("Áreas (clic para cambiar color)").classes(
                    "text-xs text-muted u-mt-sm"
                )
                with ui.element("div").classes("parrilla-leyenda"):
                    for a in areas:
                        item = ui.element("div").classes("parrilla-leyenda-item")
                        with item:
                            color = a.get("color")
                            if color:
                                sw = ui.element("span").classes("parrilla-swatch")
                                sw.style(f"background-color:{color}")  # DYNAMIC: color por área de conocimiento
                            else:
                                aid = a["area_id"] or 0
                                ui.element("span").classes(
                                    f"parrilla-swatch parrilla-area-{aid % 10}"
                                )
                            ui.label(a["area_nombre"]).classes("parrilla-leyenda-label")
                        item.on("click", lambda _, ar=a: _editar_color_area(ar))

    @ui.refreshable
    def gen_refreshable() -> None:
        """Wraps ALL generar content."""
        if _s["gen_error_contexto"]:
            empty_state(
                icono=Icons.WARNING,
                titulo="No se puede generar todavía",
                descripcion=_s["gen_error_contexto"],
            )
            return

        with ui.element("div").classes("parrilla-toolbar u-mb-md"):
            _gen_segmento(
                [("plantillas", "Plantillas"), ("generacion", "Generación")],
                _s["gen_tab"],
                _gen_cambiar_tab,
            )

        if _s["gen_tab"] == "plantillas":
            _gen_render_tab_plantillas()
            return

        if not _s["gen_plantillas"]:
            empty_state(
                icono=Icons.SCHEDULE,
                titulo="Sin plantillas horarias",
                descripcion="Crea una plantilla horaria antes de configurar una generación.",
                cta_label="Crear plantilla",
                cta_on_click=lambda: _gen_crear_plantilla(),
                cta_icono=Icons.ADD,
            )
            return

        _gen_render_lista()
        _gen_render_detalle()

    @ui.refreshable
    def doc_grilla_refreshable() -> None:
        datos = _s["doc_parrilla_datos"]
        mi_id = ctx.usuario_id

        # Sin bloques propios en el escenario activo → estado vacío
        # (evita que render_parrilla caiga al eje de otro docente).
        tiene_bloques = any(
            c.get("usuario_id") == mi_id for c in datos.get("celdas", [])
        )
        if not tiene_bloques:
            empty_state(
                icono=Icons.SCHEDULE,
                titulo="Sin horario registrado",
                descripcion="No tienes bloques asignados en el horario activo.",
            )
            return

        if _s["doc_vista_grid"] == "dia":
            # Encabezado con el día y la fecha reales de la semana en curso.
            hoy = date.today()
            dia_sel = _s["doc_dia_sel"]
            try:
                idx_dia = _DIAS_BASE.index(dia_sel)
            except ValueError:
                idx_dia = 0
            fecha_dia = hoy + timedelta(days=idx_dia - hoy.weekday())
            encabezado = (
                f"{dia_sel}, {fecha_dia.day} de "
                f"{_MESES_ES[fecha_dia.month - 1]} de {fecha_dia.year}"
            )
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2"):
                    ThemeManager.icono(Icons.SCHEDULE, size=18)
                    ui.label(encabezado).classes("text-subtitle1 font-semibold")
            render_parrilla(
                datos,
                perspectiva="Docente",
                eje_sel=mi_id,
                dias_filtro={dia_sel},
                puede_editar=False,
            )
        else:
            render_parrilla(
                datos,
                perspectiva="Docente",
                eje_sel=mi_id,
                puede_editar=False,
            )

    @ui.refreshable
    def hub_refreshable() -> None:
        """Control segmentado + contenido de la sección activa.

        El segmentado se renderiza AQUÍ (no en contenido) para que su estado
        activo se actualice al cambiar de sección con hub_refreshable.refresh().
        """
        # Control segmentado del hub. Con una sola sección visible (docente) es
        # redundante: solo se visualiza, así que se omite.
        if len(_secciones_visibles) > 1:
            with ui.element("div").classes("parrilla-toolbar"):
                with ui.element("div").classes("parrilla-segmento"):
                    for sec in _secciones_visibles:
                        lbl, icon = _SECCION_META[sec]
                        activo = _s["seccion"] == sec
                        cls = "parrilla-seg-btn" + (" parrilla-seg-btn-activo" if activo else "")
                        btn = ui.element("div").classes(cls)
                        btn.on("click", lambda _, s=sec: _cambiar_seccion(s))
                        with btn:
                            ThemeManager.icono(icon, size=14)
                            ui.label(lbl)

        sec = _s["seccion"]
        if sec == "preparar":
            _render_preparar()
        elif sec == "generar":
            gen_refreshable()
        elif sec in ("visualizar", "editar"):
            if es_profesor:
                _render_docente()
            else:
                escenarios_refreshable()
                parrilla_unificada_refreshable()
                if sec == "editar" and puede_escribir:
                    _seccion_carga_masiva()

    # =========================================================================
    # contenido() — hub dispatch
    # =========================================================================

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            hub_refreshable()

    app_layout(
        ctx,
        contenido,
        page_titulo="Horarios",
        page_subtitulo="Gestión unificada de horarios",
        page_icono=Icons.SCHEDULE,
        mostrar_contexto=False,  # hub sobre contexto activo; no depende del chip (paso_41)
    )


__all__ = ["horarios_hub_page"]
