"""
src/interface/pages/academico/registro_asistencia.py
=====================================================
Página de registro de asistencia diaria — ZECI Manager v2.0.

Regla de capas (estricta):
  Esta página NO importa ningún símbolo de src.domain.models.*.
  Solo usa Container (servicios) e imports de la capa de interfaz.
  Los DTOs y enums de dominio los manejan internamente los servicios.

Integración con context_selector:
  El context_selector se usa en dos puntos:
    1. Topbar: a través de app_layout(ctx=..., on_context_change=...)
       → context_chip se renderiza automáticamente.
  Ambos puntos comparten el mismo callback on_context_change.

Flujo:
  1. Sin contexto → panel inline muestra CTA "Configurar contexto".
  2. Con contexto → grilla se pre-carga con la fecha de hoy.
     Registros existentes preservan su estado; nuevos defaulean a P.
  3. Botones P / FJ / FI / R / E actualizan _s en memoria.
     FJ y E ofrecen campo de observación.
  4. "Todos presentes / Todos ausentes" → marcado masivo en memoria.
  5. "Guardar" → AsistenciaService.guardar_asistencia_masiva() con lista
     de dicts primitivos. El servicio construye los DTOs de dominio.
  6. Periodo cerrado → grilla y toolbar en modo solo lectura.

Refreshables:
  ctx_refreshable()    re-renderiza el panel de contexto inline.
  stats_refreshable()  re-renderiza los 5 contadores.
  grilla_refreshable() re-renderiza el banner + filas de estudiantes.
"""
from __future__ import annotations

import logging
from datetime import date

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components.context_selector import abrir_selector
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.theme import ThemeManager
from src.interface.design.components.buttons import btn_primary, btn_ghost
from src.interface.design.components import date_input, toast_error, toast_success, toast_warning

logger = logging.getLogger("REGISTRO_ASISTENCIA")


# ── Constantes de UI ───────────────────────────────────────────────────────────
# Definidas aquí, en la capa de interfaz.
# Los códigos "P","FJ","FI","R","E" son los valores que el servicio espera;
# NO son imports del enum EstadoAsistencia — son strings literales del contrato.

_ESTADOS: list[tuple[str, str, str, str]] = [
    # (codigo, etiqueta_botón, clase_CSS_botón, etiqueta_larga)
    ("P",  "P",  "asis-btn-p",  "Presente"),
    ("FJ", "FJ", "asis-btn-fj", "Falta Justificada"),
    ("FI", "FI", "asis-btn-fi", "Falta Injustificada"),
    ("R",  "R",  "asis-btn-r",  "Retraso"),
    ("E",  "E",  "asis-btn-e",  "Excusa"),
]

# Estados que normalmente requieren texto de observación
_REQUIERE_OBS: frozenset[str] = frozenset({"FJ", "E"})

# Código por defecto cuando el estudiante no tiene registro previo
_ESTADO_DEFAULT = "P"


# ── Estado mutable de la página ────────────────────────────────────────────────

def _estado_inicial() -> dict:
    """
    Retorna el dict de estado mutable para una instancia de página.
    Un dict por petición HTTP → aislamiento entre usuarios.
    """
    return {
        "fecha":           date.today(),
        "registros":       {},   # {estudiante_id: str_codigo}
        "observaciones":   {},   # {estudiante_id: str}
        "estudiantes":     [],   # list[Estudiante] ordenados por apellido, nombre
        "periodo_cerrado": False,
        "pendiente":       False,
    }


def _cargar_estado(ctx: SessionContext, _s: dict) -> None:
    """
    Recarga _s con los datos del grupo/fecha activos del contexto.

    Pasos:
      1. Verificar cierre del periodo (periodo_service).
      2. Cargar estudiantes activos del grupo (estudiante_service).
      3. Cargar estados existentes para la fecha (asistencia_service
         → estados_por_grupo_y_fecha → devuelve dict primitivo).
      4. Fusionar: existentes conservan estado; nuevos reciben P.

    Si falta grupo_id, asignacion_id o periodo_id en el contexto,
    deja _s en estado vacío sin lanzar excepción.
    """
    if not ctx.grupo_id or not ctx.asignacion_id or not ctx.periodo_id:
        _s.update(
            estudiantes=[],
            registros={},
            observaciones={},
            periodo_cerrado=False,
            pendiente=False,
        )
        return

    # 1. ¿Está el periodo cerrado?
    try:
        periodo = Container.periodo_service().get_by_id(ctx.periodo_id)
        _s["periodo_cerrado"] = bool(getattr(periodo, "cerrado", False))
    except Exception as exc:
        logger.warning("No se pudo verificar cierre del periodo %s: %s", ctx.periodo_id, exc)
        _s["periodo_cerrado"] = False

    # 2. Estudiantes del grupo, ordenados por apellido + nombre
    try:
        estudiantes = Container.estudiante_service().listar_por_grupo(ctx.grupo_id)
        estudiantes.sort(key=lambda e: (
            getattr(e, "apellido", "") or "",
            getattr(e, "nombre", "")   or "",
        ))
        _s["estudiantes"] = estudiantes
    except Exception as exc:
        logger.error("Error cargando estudiantes del grupo %s: %s", ctx.grupo_id, exc)
        _s["estudiantes"] = []

    if not _s["estudiantes"]:
        _s.update(registros={}, observaciones={}, pendiente=False)
        return

    # 3. Estados ya registrados para la fecha → dict primitivo del servicio
    existentes: dict[int, dict[str, str]] = {}
    try:
        existentes = Container.asistencia_service().estados_por_grupo_y_fecha(
            grupo_id      = ctx.grupo_id,
            asignacion_id = ctx.asignacion_id,
            fecha         = _s["fecha"],
        )
    except Exception as exc:
        logger.warning(
            "Error leyendo asistencia existente (grupo=%s, fecha=%s): %s",
            ctx.grupo_id, _s["fecha"], exc,
        )

    # 4. Fusionar
    _s["registros"] = {
        est.id: existentes[est.id]["estado"] if est.id in existentes else _ESTADO_DEFAULT
        for est in _s["estudiantes"]
    }
    _s["observaciones"] = {
        est.id: existentes[est.id]["observacion"] if est.id in existentes else ""
        for est in _s["estudiantes"]
    }
    _s["pendiente"] = False

                
def _s_cerrado_desde_ctx(ctx: SessionContext) -> bool:
    """
    Consulta el estado de cierre del periodo del contexto.
    Silencia excepciones — el peor caso es mostrar el botón Cambiar innecesariamente.
    """
    if not ctx.periodo_id:
        return False
    try:
        periodo = Container.periodo_service().get_by_id(ctx.periodo_id)
        return bool(getattr(periodo, "cerrado", False))
    except Exception:
        return False


# ── Stats ──────────────────────────────────────────────────────────────────────

def _stats_panel(_s: dict) -> None:
    """5 tarjetas de conteo: P / FJ / FI / R / E."""
    conteos = {c: 0 for c, *_ in _ESTADOS}
    for estado in _s["registros"].values():
        if estado in conteos:
            conteos[estado] += 1

    with ui.element("div").classes("asis-stats-row"):
        for codigo, _, _cls, larga in _ESTADOS:
            with ui.element("div").classes(f"asis-stat asis-stat-{codigo.lower()}"):
                ui.label(str(conteos[codigo])).classes("asis-stat-num")
                ui.label(larga).classes("asis-stat-desc")


# ── Fila de estudiante ─────────────────────────────────────────────────────────

def _fila_estudiante(
    est,
    estado_actual: str,
    obs_actual:    str,
    readonly:      bool,
    numero:        int,
    on_estado,
    on_obs,
) -> None:
    """
    Una fila de la grilla.

    Modo lectura (periodo cerrado): badge de color con el estado.
    Modo escritura: 5 botones P/FJ/FI/R/E; el activo con fondo sólido.
    FJ y E muestran un campo de observación junto a los botones.
    """
    apellidos = getattr(est, "apellido", "") or ""
    nombre    = getattr(est, "nombre", "")   or ""
    documento = getattr(est, "numero_documento", "") or ""

    with ui.element("div").classes("asis-row"):

        ui.label(str(numero)).classes("asis-cell asis-cell-num")

        with ui.element("div").classes("asis-cell asis-cell-nombre"):
            ui.label(f"{apellidos}, {nombre}").classes("asis-nombre-text")
            if documento:
                ui.label(documento).classes("asis-doc-text")

        with ui.element("div").classes("asis-cell asis-cell-estado"):
            if readonly:
                ui.label(estado_actual).classes(
                    f"asis-badge asis-badge-{estado_actual.lower()}"
                )
            else:
                with ui.element("div").classes("asis-btn-group"):
                    for codigo, etiqueta, clase_btn, larga in _ESTADOS:
                        activo = "asis-btn-active" if estado_actual == codigo else ""
                        (
                            btn_ghost(etiqueta)
                            .classes(f"asis-btn {clase_btn} {activo}".strip())
                            .tooltip(larga)
                            .on("click", lambda _, c=codigo, eid=est.id: on_estado(eid, c))
                        )

                if estado_actual in _REQUIERE_OBS:
                    ui.input(
                        placeholder="Observación (opcional)",
                        value=obs_actual,
                        on_change=lambda e, eid=est.id: on_obs(eid, e.value),
                    ).classes("asis-obs-input").props("dense")


# ── Grilla ─────────────────────────────────────────────────────────────────────

def _grilla(_s: dict, on_estado, on_obs) -> None:
    """
    Banner de periodo cerrado (si aplica) + grilla de estudiantes.
    Vive dentro de grilla_refreshable().
    """
    if _s["periodo_cerrado"]:
        with ui.element("div").classes("asis-banner-cerrado"):
            ThemeManager.icono(Icons.CLOSE_PERIOD, size=16, clases="asis-banner-icon")
            ui.label(
                "Periodo cerrado — modo solo lectura."
            ).classes("asis-banner-text")

    with ui.element("div").classes("asis-grid-wrap"):
        with ui.element("div").classes("asis-grid"):

            if not _s["estudiantes"]:
                with ui.element("div").classes("asis-empty"):
                    ThemeManager.icono(Icons.STUDENTS, size=40, clases="asis-empty-icon")
                    ui.label("Sin estudiantes en este grupo").classes("asis-empty-text")
                    ui.label(
                        "Configura el contexto académico para cargar la lista."
                    ).classes("asis-empty-hint")
                return

            with ui.element("div").classes("asis-row asis-header-row"):
                ui.label("#").classes("asis-cell asis-cell-num")
                ui.label("Estudiante").classes("asis-cell asis-cell-nombre")
                ui.label("Estado").classes("asis-cell asis-cell-estado")

            for i, est in enumerate(_s["estudiantes"], start=1):
                _fila_estudiante(
                    est           = est,
                    estado_actual = _s["registros"].get(est.id, _ESTADO_DEFAULT),
                    obs_actual    = _s["observaciones"].get(est.id, ""),
                    readonly      = _s["periodo_cerrado"],
                    numero        = i,
                    on_estado     = on_estado,
                    on_obs        = on_obs,
                )


# ── Toolbar ────────────────────────────────────────────────────────────────────

def _toolbar(
    fecha_valor:     str,
    readonly:        bool,
    on_fecha_cambio,
    on_marcar_todos,
    on_guardar,
) -> None:
    """
    Selector de fecha + acciones masivas + botón Guardar.
    En modo solo lectura solo muestra el selector de fecha.
    """
    with ui.element("div").classes("asis-toolbar"):

        with ui.element("div").classes("asis-date-wrap"):
            ThemeManager.icono(Icons.SCHEDULE, size=18, clases="asis-date-icon")
            date_input(
                label="",
                value=fecha_valor,
                on_change=lambda v: on_fecha_cambio(v or ""),
                classes="asis-date-input",
            )

        if not readonly:
            with ui.element("div").classes("asis-actions"):
                btn_ghost(
                    "Todos presentes",
                    on_click=lambda: on_marcar_todos("P"),
                ).classes("asis-action-btn asis-action-p")

                btn_ghost(
                    "Todos ausentes",
                    on_click=lambda: on_marcar_todos("FI"),
                ).classes("asis-action-btn asis-action-fi")

                ui.element("div").classes("asis-toolbar-sep")

                btn_primary(
                    "Guardar",
                    on_click=on_guardar,
                    size="sm",
                )


# ── Persistencia ───────────────────────────────────────────────────────────────

def _guardar(_s: dict, ctx: SessionContext) -> None:
    """
    Persiste la asistencia llamando a AsistenciaService.guardar_asistencia_masiva()
    con una lista de dicts primitivos. El servicio construye internamente
    los DTOs de dominio — esta función no importa ningún modelo de dominio.
    """
    if not ctx.grupo_id or not ctx.asignacion_id or not ctx.periodo_id:
        toast_warning("Contexto incompleto — configura periodo, grupo y asignatura.")
        return

    if not _s["estudiantes"]:
        toast_warning("No hay estudiantes para guardar.")
        return

    if _s["periodo_cerrado"]:
        toast_error("El periodo está cerrado. No se pueden registrar cambios.")
        return

    try:
        lista = [
            {
                "estudiante_id": est.id,
                "estado":        _s["registros"].get(est.id, _ESTADO_DEFAULT),
                "observacion":   _s["observaciones"].get(est.id) or None,
            }
            for est in _s["estudiantes"]
        ]

        conteo = Container.asistencia_service().guardar_asistencia_masiva(
            grupo_id      = ctx.grupo_id,
            asignacion_id = ctx.asignacion_id,
            periodo_id    = ctx.periodo_id,
            fecha         = _s["fecha"],
            lista         = lista,
            usuario_id    = ctx.usuario_id,
            anio_id       = ctx.anio_id,
        )

        _s["pendiente"] = False
        toast_success(f"Asistencia guardada — {conteo} estudiante(s).")
        logger.info(
            "Asistencia guardada: grupo=%s asignacion=%s fecha=%s n=%d usuario=%s",
            ctx.grupo_id, ctx.asignacion_id, _s["fecha"], conteo, ctx.usuario_id,
        )

    except ValueError as exc:
        toast_error(f"Error de validación: {exc}")
        logger.warning("Validación guardar asistencia: %s", exc)
    except Exception as exc:
        toast_error("Error al guardar. Intenta de nuevo.")
        logger.error("Error guardando asistencia: %s", exc, exc_info=True)


# ── Página ─────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def registro_asistencia_page() -> None:
    """
    Punto de entrada de /asistencia.

    Guards:
      - Sin sesión activa → redirige a /login.
      - Sin contexto configurado → panel inline muestra CTA;
        grilla vacía hasta que el usuario configure.

    Arquitectura de refreshables:
      ctx_refreshable()    Lee desde_storage() fresco; actualiza el panel
                           inline con el contexto más reciente.
      stats_refreshable()  Conteos por estado; se refresca en cada cambio.
      grilla_refreshable() Banner + filas; se refresca en cambios de estado,
                           fecha y contexto.

    on_context_change se inyecta en dos lugares:
      - app_layout(on_context_change=...) → topbar context_chip
    Ambos ejecutan el mismo callback, garantizando consistencia.
    """
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _cargar_estado(ctx, _s)

    # ── @ui.refreshable ────────────────────────────────────────────────────

    @ui.refreshable
    def ctx_refreshable() -> None:
        ctx_actual = SessionContext.desde_storage()

    @ui.refreshable
    def stats_refreshable() -> None:
        _stats_panel(_s)

    @ui.refreshable
    def grilla_refreshable() -> None:
        _grilla(_s, on_estado=on_estado, on_obs=on_obs)

    # ── Handlers ───────────────────────────────────────────────────────────

    def on_context_change() -> None:
        """Llamado desde el topbar chip O desde el panel inline."""
        nuevo_ctx = SessionContext.desde_storage()
        if nuevo_ctx:
            _cargar_estado(nuevo_ctx, _s)
        ctx_refreshable.refresh()
        stats_refreshable.refresh()
        grilla_refreshable.refresh()

    def on_fecha_cambio(valor: str) -> None:
        try:
            nueva = date.fromisoformat(valor)
        except (ValueError, TypeError):
            return
        if nueva == _s["fecha"]:
            return
        if nueva > date.today():
            toast_warning("No se puede registrar asistencia para fechas futuras.")
            return
        _s["fecha"] = nueva
        _cargar_estado(SessionContext.desde_storage() or ctx, _s)
        stats_refreshable.refresh()
        grilla_refreshable.refresh()

    def on_estado(estudiante_id: int, nuevo_estado: str) -> None:
        _s["registros"][estudiante_id] = nuevo_estado
        _s["pendiente"] = True
        stats_refreshable.refresh()
        grilla_refreshable.refresh()

    def on_obs(estudiante_id: int, texto: str) -> None:
        # Sin refresh: no interrumpir el foco del input mientras el usuario escribe
        _s["observaciones"][estudiante_id] = texto

    def on_marcar_todos(estado: str) -> None:
        for est in _s["estudiantes"]:
            _s["registros"][est.id] = estado
        _s["pendiente"] = True
        stats_refreshable.refresh()
        grilla_refreshable.refresh()

    def on_guardar() -> None:
        _guardar(_s, SessionContext.desde_storage() or ctx)

    # ── Contenido ──────────────────────────────────────────────────────────

    def contenido() -> None:
        with ui.element("div").classes("asis-page"):
            ctx_refreshable()       # Panel: periodo · grupo · asignatura [Cambiar]
            _toolbar(               # Fecha + acciones masivas + guardar
                fecha_valor     = str(_s["fecha"]),
                readonly        = _s["periodo_cerrado"],
                on_fecha_cambio = on_fecha_cambio,
                on_marcar_todos = on_marcar_todos,
                on_guardar      = on_guardar,
            )
            stats_refreshable()     # Contadores P / FJ / FI / R / E
            grilla_refreshable()    # Banner cerrado + grilla

    app_layout(
        ctx, contenido,
        page_titulo       = "Asistencia",
        on_context_change = on_context_change,
    )


__all__ = ["registro_asistencia_page"]
