"""
src/interface/pages/convivencia/comportamiento.py
=================================================
Página de registros de comportamiento — ZECI Manager v2.0.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Solo usa Container (servicios) e imports de la capa de interfaz.

Flujo:
  1. Guard de autenticación → redirige a /login si no hay sesión.
  2. _cargar_estado() carga grupos, periodos y anio_id desde configuracion_service.
  3. Filtros (grupo, periodo, tipo, solo_negativos) construyen FiltroConvivenciaDTO
     y llaman a listar_registros.
  4. aggrid muestra registros con badge por tipo (cellClass del dict _CLASE_BADGE).
  5. "Nuevo registro" → form_dialog con campos primitivos.
  6. "Notificar acudiente" → visible si requiere_firma y no notificado.
  7. "Agregar seguimiento" → form_dialog de una sola textarea.
  8. "Eliminar" → confirm_dialog antes de llamar al servicio.

Refreshables:
  _contenido() — re-renderiza todo el cuerpo de la página.
"""
from __future__ import annotations

import logging
from datetime import date

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_ghost, btn_danger, btn_icon
from src.interface.design.components.confirm_dialog import confirm_dialog
from src.interface.design.components.form_dialog import form_dialog
from src.interface.design.components import toast_error, toast_success, toast_warning

logger = logging.getLogger("COMPORTAMIENTO")


# ── Constantes de visualización ────────────────────────────────────────────────
# Strings literales — NO importan TipoRegistro del dominio

_TIPOS_DISPLAY: dict[str, str] = {
    "fortaleza":          "Fortaleza",
    "dificultad":         "Dificultad",
    "compromiso":         "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo":           "Descargo",
}

_CLASE_BADGE: dict[str, str] = {
    "fortaleza":          "badge-fortaleza",
    "dificultad":         "badge-dificultad",
    "compromiso":         "badge-compromiso",
    "citacion_acudiente": "badge-citacion",
    "descargo":           "badge-descargo",
}


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "filtro_grupo_id":       None,
        "filtro_periodo_id":     None,
        "filtro_tipo":           "",       # "" = todos
        "filtro_solo_negativos": False,
        "anio_id":               None,
        "registros":             [],       # list[RegistroComportamiento]
        "estudiantes":           [],       # list[Estudiante]
        "periodos":              [],       # list[Periodo]
    }


def _cargar_estado(ctx: SessionContext, _s: dict) -> None:
    """Carga grupos, periodos y anio_id. Aplica filtros iniciales."""
    # Año activo
    try:
        config = Container.configuracion_service().get_activa()
        _s["anio_id"] = getattr(config, "id", None) if config else None
    except Exception as exc:
        logger.warning("Sin configuración activa: %s", exc)
        _s["anio_id"] = None

    # Periodos
    try:
        if _s["anio_id"]:
            _s["periodos"] = Container.periodo_service().listar_por_anio(_s["anio_id"])
        else:
            _s["periodos"] = []
    except Exception as exc:
        logger.warning("Error cargando periodos: %s", exc)
        _s["periodos"] = []

    # Prefiltros del contexto
    if ctx.grupo_id and _s["filtro_grupo_id"] is None:
        _s["filtro_grupo_id"] = ctx.grupo_id
    if ctx.periodo_id and _s["filtro_periodo_id"] is None:
        _s["filtro_periodo_id"] = ctx.periodo_id

    # Estudiantes del grupo para el form de creación
    try:
        if _s["filtro_grupo_id"]:
            _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(
                _s["filtro_grupo_id"]
            )
        else:
            _s["estudiantes"] = []
    except Exception as exc:
        logger.warning("Error cargando estudiantes: %s", exc)
        _s["estudiantes"] = []

    # Cargar registros con filtros actuales
    _aplicar_filtros(_s)


def _aplicar_filtros(_s: dict) -> None:
    """Construye el filtro y llama a listar_registros."""
    import importlib
    _mod = importlib.import_module("src.domain.models.convivencia")

    tipo_valor = None
    if _s["filtro_tipo"]:
        # Pasar string — el DTO acepta TipoRegistro | None; string válido lo convierte pydantic
        try:
            tipo_valor = _mod.TipoRegistro(_s["filtro_tipo"])
        except Exception:
            tipo_valor = None

    try:
        filtro = _mod.FiltroConvivenciaDTO(
            grupo_id=_s["filtro_grupo_id"],
            periodo_id=_s["filtro_periodo_id"],
            tipo=tipo_valor,
            solo_negativos=_s["filtro_solo_negativos"],
        )
        _s["registros"] = Container.convivencia_service().listar_registros(filtro)
    except Exception as exc:
        logger.error("Error cargando registros de comportamiento: %s", exc)
        _s["registros"] = []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nombre_estudiante(_s: dict, est_id: int | None) -> str:
    for est in _s["estudiantes"]:
        if getattr(est, "id", None) == est_id:
            return f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
    return str(est_id) if est_id else "—"


def _construir_filas(_s: dict) -> list[dict]:
    filas = []
    for reg in _s["registros"]:
        tipo_raw = str(getattr(reg, "tipo", "")).lower()
        # Obtener valor string del tipo (puede ser enum o string)
        if hasattr(tipo_raw, "value"):
            tipo_raw = tipo_raw.value
        # Limpiar prefijo de enum si viene como "TipoRegistro.fortaleza"
        if "." in tipo_raw:
            tipo_raw = tipo_raw.split(".")[-1]

        filas.append({
            "id":                  getattr(reg, "id", None),
            "estudiante_id":       getattr(reg, "estudiante_id", None),
            "grupo_id":            getattr(reg, "grupo_id", None),
            "periodo_id":          getattr(reg, "periodo_id", None),
            "fecha":               str(getattr(reg, "fecha", ""))[:10],
            "estudiante":          _nombre_estudiante(_s, getattr(reg, "estudiante_id", None)),
            "tipo_raw":            tipo_raw,
            "tipo_display":        _TIPOS_DISPLAY.get(tipo_raw, tipo_raw),
            "tipo_badge_class":    _CLASE_BADGE.get(tipo_raw, "badge-neutral"),
            "descripcion":         str(getattr(reg, "descripcion", "")),
            "requiere_firma":      "Sí" if getattr(reg, "requiere_firma", False) else "No",
            "requiere_firma_bool": getattr(reg, "requiere_firma", False),
            "notificado":          "Sí" if getattr(reg, "acudiente_notificado", False) else "Pendiente",
            "acudiente_notificado_bool": getattr(reg, "acudiente_notificado", False),
            "pendiente_notificacion": getattr(reg, "pendiente_notificacion", False),
            "seguimiento":         "Sí" if getattr(reg, "tiene_seguimiento", False) else "—",
            "tiene_seguimiento_bool": getattr(reg, "tiene_seguimiento", False),
        })
    return filas


def _nuevo_registro_dto(datos: dict) -> object:
    """Construye NuevoRegistroComportamientoDTO sin imports de módulos de dominio en nivel de módulo."""
    import importlib
    _mod = importlib.import_module("src.domain.models.convivencia")
    return _mod.NuevoRegistroComportamientoDTO(**datos)


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/convivencia/comportamiento")
def comportamiento_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _ROLES_VALIDOS = {"admin", "director", "coordinador", "profesor"}
    if ctx.usuario_rol not in _ROLES_VALIDOS:
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    es_profesor = ctx.usuario_rol == "profesor"

    _s = _estado_inicial()
    # Para profesores: forzar al grupo del contexto (sus grupos asignados)
    if es_profesor and ctx.grupo_id:
        _s["filtro_grupo_id"] = ctx.grupo_id
    _cargar_estado(ctx, _s)

    # ── Handlers ───────────────────────────────────────────────────────────

    def on_context_change() -> None:
        nuevo_ctx = SessionContext.desde_storage()
        if nuevo_ctx:
            _s["filtro_grupo_id"] = nuevo_ctx.grupo_id
            _s["filtro_periodo_id"] = nuevo_ctx.periodo_id
            _cargar_estado(nuevo_ctx, _s)
        _contenido.refresh()

    def on_grupo_change(valor) -> None:
        _s["filtro_grupo_id"] = valor
        # Recargar estudiantes del nuevo grupo
        try:
            if valor:
                _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(int(valor))
            else:
                _s["estudiantes"] = []
        except Exception as exc:
            logger.warning("Error recargando estudiantes: %s", exc)
        _aplicar_filtros(_s)
        _contenido.refresh()

    def on_periodo_change(valor) -> None:
        _s["filtro_periodo_id"] = valor
        _aplicar_filtros(_s)
        _contenido.refresh()

    def on_tipo_change(valor) -> None:
        _s["filtro_tipo"] = valor if valor else ""
        _aplicar_filtros(_s)
        _contenido.refresh()

    def on_solo_negativos_change(valor: bool) -> None:
        _s["filtro_solo_negativos"] = valor
        _aplicar_filtros(_s)
        _contenido.refresh()

    def _crear_registro(datos: dict) -> bool | None:
        ctx_actual = SessionContext.desde_storage() or ctx
        est_id = datos.get("estudiante_id")
        tipo_str = datos.get("tipo", "")
        descripcion = str(datos.get("descripcion", "")).strip()
        requiere_firma = bool(datos.get("requiere_firma", False))
        fecha_str = datos.get("fecha", str(date.today()))

        if not descripcion:
            toast_warning("La descripción es requerida.")
            return False
        if not est_id:
            toast_warning("Selecciona un estudiante.")
            return False
        if not tipo_str:
            toast_warning("Selecciona el tipo de registro.")
            return False
        if not _s["filtro_grupo_id"]:
            toast_warning("Selecciona un grupo.")
            return False
        if not _s["filtro_periodo_id"]:
            toast_warning("Selecciona un periodo.")
            return False

        try:
            dto = _nuevo_registro_dto({
                "estudiante_id":  int(est_id),
                "grupo_id":       int(_s["filtro_grupo_id"]),
                "periodo_id":     int(_s["filtro_periodo_id"]),
                "tipo":           tipo_str,
                "descripcion":    descripcion,
                "requiere_firma": requiere_firma,
                "fecha":          fecha_str,
            })
            Container.convivencia_service().registrar_comportamiento(
                dto, ctx_actual.usuario_id, _s["anio_id"]
            )
            toast_success("Registro guardado.")
            _aplicar_filtros(_s)
            _contenido.refresh()
            return None
        except ValueError as exc:
            toast_warning(f"Error de validación: {exc}")
            return False
        except Exception as exc:
            logger.error("Error creando registro: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _abrir_crear_registro() -> None:
        opciones_est = {
            getattr(e, "id", None): f"{getattr(e, 'apellido', '')} {getattr(e, 'nombre', '')}".strip()
            for e in _s["estudiantes"]
        }
        opciones_tipo = dict(_TIPOS_DISPLAY)

        campos = [
            {
                "key":      "estudiante_id",
                "label":    "Estudiante",
                "tipo":     "select",
                "opciones": opciones_est,
                "requerido": True,
            },
            {
                "key":      "tipo",
                "label":    "Tipo de registro",
                "tipo":     "select",
                "opciones": opciones_tipo,
                "requerido": True,
            },
            {
                "key":         "descripcion",
                "label":       "Descripción",
                "tipo":        "textarea",
                "placeholder": "Máximo 1000 caracteres...",
                "requerido":   True,
            },
            {
                "key":   "requiere_firma",
                "label": "¿Requiere firma del acudiente?",
                "tipo":  "checkbox",
                "valor": False,
            },
            {
                "key":   "fecha",
                "label": "Fecha",
                "tipo":  "text",
                "valor": str(date.today()),
            },
        ]
        form_dialog(
            titulo="Nuevo registro de comportamiento",
            campos=campos,
            on_submit=_crear_registro,
            texto_submit="Guardar",
            max_width="max-w-lg",
        )

    def _notificar_acudiente(registro_id: int) -> None:
        try:
            Container.convivencia_service().notificar_acudiente(registro_id)
            toast_success("Acudiente marcado como notificado.")
            _aplicar_filtros(_s)
            _contenido.refresh()
        except Exception as exc:
            logger.error("Error notificando acudiente: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")

    def _agregar_seguimiento(registro_id: int) -> None:
        def _submit_seguimiento(datos: dict) -> bool | None:
            texto = str(datos.get("seguimiento", "")).strip()
            if not texto:
                toast_warning("El seguimiento no puede estar vacío.")
                return False
            try:
                Container.convivencia_service().agregar_seguimiento(registro_id, texto)
                toast_success("Seguimiento agregado.")
                _aplicar_filtros(_s)
                _contenido.refresh()
                return None
            except Exception as exc:
                logger.error("Error agregando seguimiento: %s", exc, exc_info=True)
                toast_error(f"Error: {exc}")
                return False

        form_dialog(
            titulo="Agregar seguimiento",
            campos=[
                {
                    "key":         "seguimiento",
                    "label":       "Descripción del seguimiento",
                    "tipo":        "textarea",
                    "placeholder": "Detalla las acciones tomadas...",
                    "requerido":   True,
                }
            ],
            on_submit=_submit_seguimiento,
            texto_submit="Guardar seguimiento",
        )

    def _eliminar_registro(registro_id: int) -> None:
        def _ejecutar() -> None:
            try:
                Container.convivencia_service().eliminar_registro(registro_id)
                toast_success("Registro eliminado.")
                _aplicar_filtros(_s)
                _contenido.refresh()
            except Exception as exc:
                logger.error("Error eliminando registro %s: %s", registro_id, exc, exc_info=True)
                toast_error(f"Error: {exc}")

        confirm_dialog(
            titulo="Eliminar registro",
            mensaje="¿Confirmas la eliminación de este registro de comportamiento?",
            on_confirm=_ejecutar,
            variante="danger",
        )

    # ── Refreshable ────────────────────────────────────────────────────────

    @ui.refreshable
    def _contenido() -> None:
        ctx_actual = SessionContext.desde_storage() or ctx
        filas = _construir_filas(_s)

        # Opciones para filtros
        opciones_periodos = {
            getattr(p, "id", None): getattr(p, "nombre", f"Periodo {getattr(p, 'id', '')}")
            for p in _s["periodos"]
        }
        opciones_tipo = {"": "Todos"} | {k: v for k, v in _TIPOS_DISPLAY.items()}

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):
                # Filtros
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                        ui.select(
                            options=opciones_periodos,
                            label="Periodo",
                            value=_s["filtro_periodo_id"],
                            on_change=lambda e: on_periodo_change(e.value),
                        ).classes("andes-input").props("outlined dense").style("min-width:180px")  # DYNAMIC: ancho mínimo del selector

                        ui.select(
                            options=opciones_tipo,
                            label="Tipo",
                            value=_s["filtro_tipo"] or "",
                            on_change=lambda e: on_tipo_change(e.value),
                        ).classes("andes-input").props("outlined dense").style("min-width:180px")  # DYNAMIC: ancho mínimo del selector

                        ui.checkbox(
                            "Solo negativos",
                            value=_s["filtro_solo_negativos"],
                            on_change=lambda e: on_solo_negativos_change(e.value),
                        )

                        ui.element("div").classes("flex-1")
                        btn_primary(
                            "Nuevo registro",
                            on_click=_abrir_crear_registro,
                            icon=Icons.ADD,
                        )

                # Tabla de registros
                with ui.element("div").classes("panel-card"):
                    if not filas:
                        ui.label(
                            "Sin registros para los filtros seleccionados."
                        ).classes("text-empty py-4")
                    else:
                        col_defs = [
                            {"headerName": "Fecha",        "field": "fecha",         "width": 110, "sortable": True},
                            {"headerName": "Estudiante",   "field": "estudiante",    "flex": 1, "sortable": True},
                            {
                                "headerName": "Tipo",
                                "field":      "tipo_display",
                                "width":      160,
                                "cellClass":  "tipo_badge_class",
                            },
                            {"headerName": "Descripción",  "field": "descripcion",   "flex": 2},
                            {"headerName": "Req. Firma",   "field": "requiere_firma", "width": 110},
                            {"headerName": "Notificado",   "field": "notificado",    "width": 110},
                            {"headerName": "Seguimiento",  "field": "seguimiento",   "width": 110},
                        ]
                        ui.aggrid({
                            "columnDefs":        col_defs,
                            "rowData":           filas,
                            "defaultColDef":     {"resizable": True},
                            "suppressCellFocus": True,
                            "rowSelection":      "single",
                        }).classes("w-full")

                        # Acciones por fila
                        with ui.element("div").classes("flex flex-col gap-1 mt-2"):
                            for fila in filas:
                                with ui.row().classes("items-center gap-2 py-1"):
                                    ui.label(fila["estudiante"]).classes("w-40 text-sm font-medium")
                                    ui.label(fila["tipo_display"]).classes(
                                        f"text-sm {fila['tipo_badge_class']}"
                                    )

                                    # Notificar acudiente: solo si requiere firma y no notificado
                                    if fila["pendiente_notificacion"]:
                                        btn_ghost(
                                            "Notificar acudiente",
                                            on_click=lambda rid=fila["id"]: _notificar_acudiente(rid),
                                            size="sm",
                                        )

                                    btn_ghost(
                                        "Seguimiento",
                                        on_click=lambda rid=fila["id"]: _agregar_seguimiento(rid),
                                        size="sm",
                                    )

                                    btn_danger(
                                        "Eliminar",
                                        on_click=lambda rid=fila["id"]: _eliminar_registro(rid),
                                        size="sm",
                                    )

        app_layout(
            ctx_actual, contenido_pagina,
            page_titulo="Comportamiento",
            on_context_change=on_context_change,
        )

    _contenido()


__all__ = ["comportamiento_page"]
