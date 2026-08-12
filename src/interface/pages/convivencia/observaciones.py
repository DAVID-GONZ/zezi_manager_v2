"""
src/interface/pages/convivencia/observaciones.py
================================================
Página de observaciones de periodo — ZECI Manager v2.0.

Superficie de CREACIÓN pura:
  - Crear observaciones para uno o más estudiantes seleccionados.
  - Crear registros de comportamiento (gated a director de grupo/coord/dir).
  La visualización/gestión de observaciones existentes vive en Seguimiento
  (convivencia_25), NO aquí.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
  Los DTOs se acceden a través del módulo de servicios.
  Solo usa Container (servicios) e imports de la capa de interfaz.

Patrón de selector (igual que planilla_notas):
  El inline_periodo_grupo_asignatura va FUERA del @ui.refreshable.
  on_sel_change actualiza _s y llama panel_grid.refresh().
  El refreshable nunca re-renderiza el selector.

Flujo:
  1. Guard de autenticación → redirige a /login si no hay sesión.
  2. inline_periodo_grupo_asignatura pre-selecciona periodo, grupo y asignatura.
  3. on_sel_change carga estudiantes del grupo.
  4. panel_grid renderiza un picker de estudiantes (checkbox + nombre).
  5. "Nueva observación" / "Usar plantilla": aplica a todos los seleccionados.
  6. "Nuevo registro de comportamiento": visible solo si el usuario está
     autorizado sobre el grupo activo.
"""
from __future__ import annotations

import logging
from datetime import date

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
from src.interface.design.components.buttons import btn_ghost, btn_primary
from src.interface.design.components.inline_selectors import inline_periodo_grupo_asignatura
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.services.convivencia_service import (
    NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO,
)

logger = logging.getLogger("OBSERVACIONES")


# ── Constantes de visualización ────────────────────────────────────────────────
# Strings literales — NO importan TipoRegistro del dominio

_TIPOS_DISPLAY: dict[str, str] = {
    "fortaleza":          "Fortaleza",
    "dificultad":         "Dificultad",
    "compromiso":         "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo":           "Descargo",
}

_MSG_NO_AUTORIZADO = (
    "Solo el director de grupo, la coordinación o la dirección pueden "
    "gestionar el comportamiento de este grupo."
)


def _autorizado_para_grupo(ctx: SessionContext, grupo_id: int | None) -> bool:
    """Autorización por objeto: ¿puede el usuario gestionar el comportamiento
    del grupo activo? Delega en CatalogoAcademicoService (directivo siempre;
    profesor solo si dirige el grupo; admin False). Pasa primitivos; la página
    no importa dominio. Sin grupo → False."""
    if not grupo_id:
        return False
    try:
        return Container.catalogo_academico_service().puede_gestionar_comportamiento_en_grupo(
            ctx.usuario_rol, ctx.usuario_id, int(grupo_id)
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed ante error de resolución
        logger.warning("No se pudo resolver autorización de comportamiento: %s", exc)
        return False


# ── Estado ─────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "estudiantes":           [],
        "periodos":              [],
        "anio_id":               None,
        "sel_estudiante_ids":    [],
        "sel_periodo_id":        None,
        "sel_grupo_id":          None,
        "sel_grupo_nombre":      "",
        "sel_asignacion_id":     None,
        "sel_asignacion_nombre": "",
        "plantilla_id":          None,
    }


def _cargar_periodos(_s: dict) -> None:
    try:
        config = Container.configuracion_service().get_activa()
        anio_id = getattr(config, "id", None) if config else None
        _s["anio_id"] = anio_id
        if anio_id:
            _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id)
        else:
            _s["periodos"] = []
    except Exception as exc:
        logger.warning("Error cargando periodos: %s", exc)
        _s["periodos"] = []


def _cargar_categorias() -> tuple[dict, dict]:
    try:
        cats = Container.convivencia_service().listar_categorias(solo_activas=True)
        opciones = {getattr(c, "id", None): getattr(c, "nombre", "") for c in cats}
        es_comp = {
            getattr(c, "id", None): bool(getattr(c, "es_comportamental", False))
            for c in cats
        }
        return opciones, es_comp
    except Exception as exc:
        logger.warning("Error cargando categorias: %s", exc)
        return {}, {}


def _cargar_plantillas(categoria_id: int | None = None, limite: int = 20) -> list:
    try:
        return Container.convivencia_service().listar_plantillas_sugeridas(
            categoria_id=categoria_id, limite=limite
        )
    except Exception as exc:
        logger.warning("Error cargando plantillas: %s", exc)
        return []


# ── Helpers ────────────────────────────────────────────────────────────────────

def _nombre_estudiante(_s: dict, est_id: int | None) -> str:
    for est in _s["estudiantes"]:
        if getattr(est, "id", None) == est_id:
            return f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
    return "—"


def _construir_filas_picker(_s: dict) -> list[dict]:
    """Genera filas para el picker de estudiantes (checkbox + nombre)."""
    filas = []
    for est in _s["estudiantes"]:
        est_id = getattr(est, "id", None)
        nombre = f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
        filas.append({
            "estudiante_id":   est_id,
            "nombre_completo": nombre,
        })
    return filas


# ── Página ─────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py
def observaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _cargar_periodos(_s)

    _refs: dict = {}

    def _refrescar_picker() -> None:
        """Refresca solo el picker de estudiantes tras crear."""
        panel_grid.refresh()

    # ── Handlers: observaciones ────────────────────────────────────────────────

    def _crear_observacion(datos: dict) -> bool | None:
        """Crea una observación por cada estudiante seleccionado en el picker."""
        periodo_id = datos.get("periodo_id")
        texto = str(datos.get("texto", "")).strip()
        es_publica = bool(datos.get("es_publica", True))
        categoria_id = datos.get("categoria_id")

        if not texto:
            toast_warning("El texto de la observación es requerido.")
            return False
        if not periodo_id:
            toast_warning("Selecciona un periodo.")
            return False
        if not categoria_id:
            toast_warning("Selecciona una categoría para la observación.")
            return False

        sel_ids = _s["sel_estudiante_ids"]
        if not sel_ids:
            toast_warning("No hay estudiantes seleccionados.")
            return False

        asignacion_id = _s.get("sel_asignacion_id")
        if not asignacion_id:
            toast_warning("Selecciona una asignatura en el contexto.")
            return False

        exitos = 0
        errores = 0
        svc = Container.convivencia_service()
        plantilla_id = _s.get("plantilla_id")

        for est_id in sel_ids:
            try:
                dto = NuevaObservacionDTO(
                    estudiante_id=int(est_id),
                    asignacion_id=int(asignacion_id),
                    periodo_id=int(periodo_id),
                    texto=texto,
                    categoria_id=int(categoria_id),
                    es_publica=es_publica,
                )
                if plantilla_id:
                    svc.registrar_observacion_desde_plantilla(
                        dto, plantilla_id, ctx.usuario_id, ctx.usuario_rol
                    )
                else:
                    svc.registrar_observacion(dto, ctx.usuario_id, ctx.usuario_rol)
                exitos += 1
            except PermissionError as exc:
                toast_warning(f"Sin permiso ({_nombre_estudiante(_s, est_id)}): {exc}")
                errores += 1
            except ValueError as exc:
                toast_warning(f"Validación: {exc}")
                errores += 1
            except Exception as exc:
                logger.error("Error creando obs est=%s: %s", est_id, exc, exc_info=True)
                errores += 1

        _s["plantilla_id"] = None

        if exitos > 0:
            msg = f"Observación guardada ({exitos})." if exitos == 1 else f"Observaciones guardadas ({exitos} de {len(sel_ids)})."
            toast_success(msg)
            _refrescar_picker()
            return None

        toast_error(f"No se pudo guardar ninguna observación ({errores} error(es)).")
        return False

    def _abrir_crear_observacion(
        texto_prefill: str = "",
        categoria_id_prefill: int | None = None,
    ) -> None:
        sel_ids = _s["sel_estudiante_ids"]
        if not sel_ids:
            toast_warning("Selecciona al menos un estudiante.")
            return

        opciones_per = {
            getattr(p, "id", None): getattr(p, "nombre", f"Periodo {getattr(p, 'id', '')}")
            for p in _s["periodos"]
        }
        opciones_cat, _ = _cargar_categorias()

        if len(sel_ids) == 1:
            sub = _nombre_estudiante(_s, sel_ids[0])
        else:
            sub = f"Se aplicará a {len(sel_ids)} estudiantes seleccionados."

        campos = [
            {
                "key":       "periodo_id",
                "label":     "Periodo",
                "tipo":      "select",
                "opciones":  opciones_per,
                "valor":     _s["sel_periodo_id"],
                "requerido": True,
            },
            {
                "key":       "categoria_id",
                "label":     "Categoría",
                "tipo":      "select",
                "opciones":  opciones_cat,
                "valor":     categoria_id_prefill,
                "requerido": True,
            },
            {
                "key":         "texto",
                "label":       "Texto de la observación",
                "tipo":        "textarea",
                "placeholder": "Máximo 2000 caracteres...",
                "valor":       texto_prefill,
                "requerido":   True,
            },
            {
                "key":   "es_publica",
                "label": "¿Pública? (aparece en boletín)",
                "tipo":  "checkbox",
                "valor": True,
            },
        ]

        form_dialog(
            titulo="Nueva observación",
            subtitulo=sub,
            campos=campos,
            on_submit=_crear_observacion,
            texto_submit="Guardar",
            max_width="max-w-lg",
        )

    def _abrir_selector_plantilla() -> None:
        sel_ids = _s["sel_estudiante_ids"]
        if not sel_ids:
            toast_warning("Selecciona al menos un estudiante.")
            return

        todas_plantillas = _cargar_plantillas(None)
        if not todas_plantillas:
            toast_warning("No hay plantillas disponibles.")
            return
        opciones_plt = {
            getattr(p, "id", None): getattr(p, "texto", "")
            for p in todas_plantillas
        }

        def _on_submit_plantilla(datos: dict) -> bool | None:
            plantilla_id = datos.get("plantilla_id")
            if not plantilla_id:
                toast_warning("Selecciona una plantilla.")
                return False
            plantilla = next(
                (p for p in todas_plantillas if getattr(p, "id", None) == plantilla_id),
                None,
            )
            if plantilla is None:
                toast_warning("Plantilla no encontrada.")
                return False
            _s["plantilla_id"] = getattr(plantilla, "id", None)
            _abrir_crear_observacion(
                texto_prefill=getattr(plantilla, "texto", ""),
                categoria_id_prefill=getattr(plantilla, "categoria_id", None),
            )
            return None

        form_dialog(
            titulo="Usar plantilla",
            campos=[{
                "key":       "plantilla_id",
                "label":     "Seleccionar plantilla",
                "tipo":      "select",
                "opciones":  opciones_plt,
                "requerido": True,
            }],
            on_submit=_on_submit_plantilla,
            texto_submit="Usar plantilla",
            max_width="max-w-lg",
        )

    # ── Handlers: registro de comportamiento (migrado de comportamiento.py) ─────

    def _crear_registro(datos: dict) -> bool | None:
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
        if not _s.get("sel_grupo_id"):
            toast_warning("Selecciona un grupo.")
            return False
        if not _s.get("sel_periodo_id"):
            toast_warning("Selecciona un periodo.")
            return False

        try:
            dto = NuevoRegistroComportamientoDTO(
                estudiante_id=int(est_id),
                grupo_id=int(_s["sel_grupo_id"]),
                periodo_id=int(_s["sel_periodo_id"]),
                tipo=tipo_str,
                descripcion=descripcion,
                requiere_firma=requiere_firma,
                fecha=fecha_str,
            )
            Container.convivencia_service().registrar_comportamiento(
                dto, ctx.usuario_id, _s["anio_id"],
                usuario_rol=ctx.usuario_rol,
            )
            toast_success("Registro guardado.")
            _refrescar_picker()
            return None
        except PermissionError as exc:
            toast_warning(f"Sin permiso: {exc}")
            return False
        except ValueError as exc:
            toast_warning(f"Error de validación: {exc}")
            return False
        except Exception as exc:
            logger.error("Error creando registro: %s", exc, exc_info=True)
            toast_error(f"Error: {exc}")
            return False

    def _abrir_crear_registro() -> None:
        if not _autorizado_para_grupo(ctx, _s.get("sel_grupo_id")):
            toast_warning(_MSG_NO_AUTORIZADO)
            return

        opciones_est = {
            getattr(e, "id", None): f"{getattr(e, 'apellido', '')} {getattr(e, 'nombre', '')}".strip()
            for e in _s["estudiantes"]
        }
        sel_ids = _s.get("sel_estudiante_ids", [])
        est_prefill = sel_ids[0] if len(sel_ids) == 1 else None
        opciones_tipo = dict(_TIPOS_DISPLAY)

        campos = [
            {
                "key":       "estudiante_id",
                "label":     "Estudiante",
                "tipo":      "select",
                "opciones":  opciones_est,
                "valor":     est_prefill,
                "requerido": True,
            },
            {
                "key":       "tipo",
                "label":     "Tipo de registro",
                "tipo":      "select",
                "opciones":  opciones_tipo,
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

    # ── Refreshable: picker de estudiantes ─────────────────────────────────────

    @ui.refreshable
    def panel_grid() -> None:
        col_defs = [
            {
                "headerName":              "",
                "field":                   "check",
                "checkboxSelection":       True,
                "headerCheckboxSelection": True,
                "width":                   50,
                "sortable":                False,
                "filter":                  False,
            },
            {
                "headerName": "Estudiante",
                "field":      "nombre_completo",
                "flex":       1,
                "sortable":   True,
                "filter":     True,
            },
        ]

        grid_rows = _construir_filas_picker(_s)
        autorizado = _autorizado_para_grupo(ctx, _s.get("sel_grupo_id"))

        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("panel-toolbar"):
                ui.element("div").classes("panel-toolbar-spacer")
                if autorizado:
                    btn_ghost(
                        "Nuevo registro de comportamiento",
                        on_click=_abrir_crear_registro,
                        icon="flag",
                    )
                btn_ghost(
                    "Usar plantilla",
                    on_click=_abrir_selector_plantilla,
                    icon="description",
                )
                btn_primary(
                    "Nueva observación",
                    on_click=_abrir_crear_observacion,
                    icon=Icons.ADD,
                )

            if not _s.get("sel_grupo_id"):
                empty_state(
                    icono="group",
                    titulo="Selecciona un grupo",
                    descripcion="Elige periodo, grupo y asignatura para ver los estudiantes.",
                )
            elif not grid_rows:
                empty_state(
                    icono="person_search",
                    titulo="Sin estudiantes",
                    descripcion="No hay estudiantes registrados en este grupo.",
                )
            else:
                with ui.element("div").classes("aggrid-vh"):
                    grid = ui.aggrid({
                        "columnDefs":  col_defs,
                        "rowData":     grid_rows,
                        "rowSelection": "multiple",
                        "defaultColDef": {"resizable": True},
                        "suppressCellFocus": True,
                    }).classes("w-full")
                _refs["grid"] = grid

                async def on_grid_selection(_e, _grid=grid) -> None:
                    rows = await _grid.get_selected_rows()
                    _s["sel_estudiante_ids"] = [r["estudiante_id"] for r in rows]

                grid.on("selectionChanged", on_grid_selection)

    # ── Contenido principal (selector FUERA del refreshable) ────────────────────

    def contenido() -> None:
        def on_sel_change(s: dict) -> None:
            _s["sel_periodo_id"]        = s["sel_periodo_id"]
            _s["sel_grupo_id"]          = s["sel_grupo_id"]
            _s["sel_asignacion_id"]     = s["sel_asignacion_id"]
            _s["sel_asignacion_nombre"] = s.get("sel_asignacion_nombre", "")
            _s["sel_estudiante_ids"]    = []
            if s["sel_grupo_id"]:
                try:
                    _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(
                        s["sel_grupo_id"]
                    )
                except Exception as exc:
                    logger.warning("Error cargando estudiantes: %s", exc)
                    _s["estudiantes"] = []
            else:
                _s["estudiantes"] = []
            panel_grid.refresh()

        inline_periodo_grupo_asignatura(
            _s, on_sel_change,
            usuario_id=ctx.usuario_id,
            institucion_id=ctx.institucion_id,
            usuario_rol=ctx.usuario_rol,
            preselect_periodo=True,
        )

        with ui.element("div").classes("page-stack"):
            panel_grid()

    app_layout(ctx, contenido, page_titulo="Observaciones")


__all__ = ["observaciones_page"]
