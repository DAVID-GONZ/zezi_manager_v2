"""
src/interface/pages/convivencia/observaciones.py
================================================
Página de observaciones de periodo — ZECI Manager v2.0.

Vista dual (convivencia_37):
  - ZONA SUPERIOR: observador cronológico del estudiante con exportación
    PDF/Excel. Selector grupo → estudiante → periodo (opcional).
  - ZONA INFERIOR: formulario de creación de observaciones y registros.

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
  4. ZONA SUPERIOR: ui.select estudiante → carga observador → timeline.
  5. ZONA INFERIOR: panel_grid renderiza picker de estudiantes con acciones.
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
from src.interface.design.components.inline_selectors import (
    inline_periodo_grupo_asignatura,
)
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.interface.pages.convivencia._shared_observacion_form import (
    abrir_crear_observacion_dialog,
)
from src.interface.presenters.convivencia.observaciones_presenter import ObservacionesPresenter
from src.services.convivencia_service import NuevoRegistroComportamientoDTO

logger = logging.getLogger("OBSERVACIONES")


# ── Constantes de visualización ────────────────────────────────────────────────

_TIPOS_DISPLAY: dict[str, str] = {
    "fortaleza": "Fortaleza",
    "dificultad": "Dificultad",
    "compromiso": "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo": "Descargo",
}

_TIPO_ICONO: dict[str, str] = {
    "fortaleza": "star",
    "dificultad": "warning",
    "compromiso": "handshake",
    "citacion_acudiente": "groups",
    "descargo": "gavel",
    "observacion": "description",
}

_MSG_NO_AUTORIZADO = (
    "Solo el director de grupo, la coordinación o la dirección pueden "
    "gestionar el comportamiento de este grupo."
)


def _autorizado_para_grupo(ctx: SessionContext, grupo_id: int | None) -> bool:
    if not grupo_id:
        return False
    try:
        return Container.catalogo_academico_service().puede_gestionar_comportamiento_en_grupo(
            ctx.usuario_rol, ctx.usuario_id, int(grupo_id)
        )
    except Exception as exc:
        logger.warning("No se pudo resolver autorización de comportamiento: %s", exc)
        return False


# ── Estado ─────────────────────────────────────────────────────────────────────


def _estado_inicial() -> dict:
    return {
        "estudiantes": [],
        "periodos": [],
        "anio_id": None,
        "sel_estudiante_ids": [],
        "sel_periodo_id": None,
        "sel_grupo_id": None,
        "sel_grupo_nombre": "",
        "sel_asignacion_id": None,
        "sel_asignacion_nombre": "",
        "plantilla_id": None,
        "asignaciones_grupo": [],
        "observador_estudiante_id": None,
        "observador_periodo_filter": None,
        "observador_entradas": [],
        "observador_resumen": {},
        "observador_cargando": False,
        "observador_error": None,
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
    filas = []
    for est in _s["estudiantes"]:
        est_id = getattr(est, "id", None)
        nombre = f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
        filas.append({"estudiante_id": est_id, "nombre_completo": nombre})
    return filas


def _fecha_display(fecha) -> str:
    if fecha is None:
        return "—"
    try:
        return fecha.strftime("%d/%m/%Y")
    except Exception:
        return str(fecha)


_SUBTIPO_LABEL: dict[str, str] = {
    **_TIPOS_DISPLAY,
    "publica": "Obs. pública",
    "privada": "Obs. privada",
    "observacion": "Observación",
}

_TIPO_COLOR: dict[str, str] = {
    "fortaleza": "text-green-700",
    "dificultad": "text-red-700",
    "compromiso": "text-yellow-700",
    "citacion_acudiente": "text-orange-700",
    "descargo": "text-purple-700",
    "publica": "text-blue-700",
    "privada": "text-gray-600",
}


# ── Página ─────────────────────────────────────────────────────────────────────


def observaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    presenter = ObservacionesPresenter()
    _s = presenter.estado
    _cargar_periodos(_s)

    _refs: dict = {}

    def _refrescar_picker() -> None:
        panel_grid.refresh()

    def _refrescar_observador() -> None:
        panel_observador.refresh()

    # ── Handlers: observador ───────────────────────────────────────────────────

    def _cargar_observador_para(est_id: int | None) -> None:
        if not est_id:
            _s["observador_estudiante_id"] = None
            _s["observador_entradas"] = []
            _s["observador_resumen"] = {}
            _refrescar_observador()
            return
        try:
            presenter.cargar_observador(
                estudiante_id=est_id,
                anio_id=_s["anio_id"],
                periodo_id=_s.get("observador_periodo_filter"),
                convivencia_service=Container.convivencia_service(),
            )
        except Exception as exc:
            logger.error("Error en cargar_observador: %s", exc, exc_info=True)
        _refrescar_observador()

    def _exportar_observador(formato: str) -> None:
        est_id = _s.get("observador_estudiante_id")
        if not est_id or not presenter.puede_exportar():
            toast_warning("No hay datos del observador para exportar.")
            return
        try:
            datos_bytes = Container.convivencia_service().exportar_observador(
                estudiante_id=est_id,
                anio_id=_s["anio_id"],
                formato=formato,
                periodo_id=_s.get("observador_periodo_filter"),
            )
            nombre_est = _nombre_estudiante(_s, est_id).replace(" ", "_") or str(est_id)
            ext = "pdf" if formato == "pdf" else "xlsx"
            filename = f"observador_{nombre_est}.{ext}"
            ui.download(src=datos_bytes, filename=filename)
            toast_success(f"Descargando {filename}…")
        except Exception as exc:
            logger.error("Error exportando observador: %s", exc, exc_info=True)
            toast_error(f"Error al exportar: {exc}")

    # ── Handlers: observaciones ────────────────────────────────────────────────

    def _abrir_crear_observacion(
        texto_prefill: str = "",
        categoria_id_prefill: int | None = None,
        plantilla_id: int | None = None,
    ) -> None:
        sel_ids = _s["sel_estudiante_ids"]
        if not sel_ids:
            toast_warning("Selecciona al menos un estudiante.")
            return
        periodo_id = _s.get("sel_periodo_id")
        if not periodo_id:
            toast_warning("Selecciona un periodo.")
            return
        asignaciones = _s.get("asignaciones_grupo", [])
        nombre_unico = None
        if len(sel_ids) == 1:
            nombre_unico = _nombre_estudiante(_s, sel_ids[0]) or None

        def _on_obs_success(ex, er):
            _refrescar_picker()
            # Si el estudiante creado coincide con el del observador, recargar
            est_id_obs = _s.get("observador_estudiante_id")
            if est_id_obs and est_id_obs in sel_ids:
                _cargar_observador_para(est_id_obs)

        abrir_crear_observacion_dialog(
            ctx=ctx,
            estudiante_ids=sel_ids,
            periodo_id=int(periodo_id),
            asignaciones=asignaciones,
            on_success=_on_obs_success,
            plantilla_id=plantilla_id,
            texto_prefill=texto_prefill,
            categoria_id_prefill=categoria_id_prefill,
            nombre_unico=nombre_unico,
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
        opciones_plt = {getattr(p, "id", None): getattr(p, "texto", "") for p in todas_plantillas}

        def _on_submit_plantilla(datos: dict) -> bool | None:
            plantilla_id = datos.get("plantilla_id")
            if not plantilla_id:
                toast_warning("Selecciona una plantilla.")
                return False
            plantilla = next(
                (p for p in todas_plantillas if getattr(p, "id", None) == plantilla_id), None
            )
            if plantilla is None:
                toast_warning("Plantilla no encontrada.")
                return False
            _abrir_crear_observacion(
                texto_prefill=getattr(plantilla, "texto", ""),
                categoria_id_prefill=getattr(plantilla, "categoria_id", None),
                plantilla_id=getattr(plantilla, "id", None),
            )
            return None

        form_dialog(
            titulo="Usar plantilla",
            campos=[
                {
                    "key": "plantilla_id",
                    "label": "Seleccionar plantilla",
                    "tipo": "select",
                    "opciones": opciones_plt,
                    "requerido": True,
                }
            ],
            on_submit=_on_submit_plantilla,
            texto_submit="Usar plantilla",
            max_width="max-w-lg",
        )

    # ── Handlers: registro de comportamiento ───────────────────────────────────

    def _crear_registro(datos: dict) -> bool | None:
        est_id = datos.get("estudiante_id")
        tipo_str = datos.get("tipo", "")
        descripcion = str(datos.get("descripcion", "")).strip()
        requiere_firma = bool(datos.get("requiere_firma", False))
        fecha_str = datos.get("fecha", str(date.today()))
        tipo_situacion_id = datos.get("tipo_situacion_id") or None
        if tipo_situacion_id is not None:
            try:
                tipo_situacion_id = int(tipo_situacion_id)
            except (ValueError, TypeError):
                tipo_situacion_id = None
        medida_id = datos.get("medida_id") or None
        if medida_id is not None:
            try:
                medida_id = int(medida_id)
            except (ValueError, TypeError):
                medida_id = None

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
                tipo_situacion_id=tipo_situacion_id,
                medida_id=medida_id,
            )
            Container.convivencia_service().registrar_comportamiento(
                dto,
                ctx.usuario_id,
                _s["anio_id"],
                usuario_rol=ctx.usuario_rol,
            )
            toast_success("Registro guardado.")
            _refrescar_picker()
            # Recargar observador si corresponde al mismo estudiante
            est_id_obs = _s.get("observador_estudiante_id")
            if est_id_obs and est_id_obs == int(est_id):
                _cargar_observador_para(est_id_obs)
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

        try:
            tipos_sit = Container.convivencia_service().listar_tipos_situacion(solo_activas=True)
            opciones_tipo_sit: dict = {None: "Sin clasificar (opcional)"}
            for t in tipos_sit:
                opciones_tipo_sit[getattr(t, "id", None)] = getattr(t, "nombre", "")
        except Exception:
            opciones_tipo_sit = {None: "Sin clasificar (opcional)"}

        try:
            medidas = Container.convivencia_service().listar_medidas_pedagogicas(solo_activas=True)
            opciones_medida: dict = {None: "Sin medida (opcional)"}
            for m in medidas:
                opciones_medida[getattr(m, "id", None)] = getattr(m, "nombre", "")
        except Exception:
            opciones_medida = {None: "Sin medida (opcional)"}

        campos = [
            {"key": "estudiante_id", "label": "Estudiante", "tipo": "select", "opciones": opciones_est, "valor": est_prefill, "requerido": True},
            {"key": "tipo", "label": "Tipo de registro", "tipo": "select", "opciones": opciones_tipo, "requerido": True},
            {"key": "descripcion", "label": "Descripción", "tipo": "textarea", "placeholder": "Máximo 1000 caracteres...", "requerido": True},
            {"key": "tipo_situacion_id", "label": "Tipo de situación (Ley 1620)", "tipo": "select", "opciones": opciones_tipo_sit, "valor": None},
            {"key": "medida_id", "label": "Medida pedagógica aplicada", "tipo": "select", "opciones": opciones_medida, "valor": None},
            {"key": "requiere_firma", "label": "¿Requiere firma del acudiente?", "tipo": "checkbox", "valor": False},
            {"key": "fecha", "label": "Fecha", "tipo": "text", "valor": str(date.today())},
        ]
        form_dialog(
            titulo="Nuevo registro de comportamiento",
            campos=campos,
            on_submit=_crear_registro,
            texto_submit="Guardar",
            max_width="max-w-lg",
        )

    # ── Refreshable: observador superior ──────────────────────────────────────

    @ui.refreshable
    def panel_observador() -> None:
        grupo_id = _s.get("sel_grupo_id")
        estudiantes = _s.get("estudiantes", [])
        est_obs_id = _s.get("observador_estudiante_id")

        with ui.element("div").classes("panel-card"):
            # Toolbar: título + selectores + botones de exportación
            with ui.element("div").classes("panel-toolbar"):
                ui.label("Observador del estudiante").classes("panel-toolbar-title text-sm font-semibold")
                ui.element("div").classes("panel-toolbar-spacer")
                if presenter.puede_exportar():
                    btn_ghost(
                        "Exportar Excel",
                        on_click=lambda: _exportar_observador("excel"),
                        icon="table_view",
                    )
                    btn_ghost(
                        "Exportar PDF",
                        on_click=lambda: _exportar_observador("pdf"),
                        icon="picture_as_pdf",
                    )

            if not grupo_id:
                empty_state(
                    icono="person_search",
                    titulo="Selecciona un grupo",
                    descripcion="Elige grupo en el selector de arriba para ver el observador de un estudiante.",
                )
                return

            # Selectores: estudiante + periodo opcional
            with ui.element("div").classes("flex flex-wrap gap-3 px-4 pb-3"):
                opciones_est: dict = {}
                for est in estudiantes:
                    eid = getattr(est, "id", None)
                    enombre = f"{getattr(est, 'apellido', '')} {getattr(est, 'nombre', '')}".strip()
                    if eid is not None:
                        opciones_est[eid] = enombre

                sel_est_widget = (
                    ui.select(
                        opciones_est,
                        label="Estudiante",
                        value=est_obs_id,
                        clearable=True,
                    )
                    .classes("min-w-48")
                    .props("dense outlined")
                )

                periodos = _s.get("periodos", [])
                opciones_per: dict = {None: "Año completo"}
                for p in periodos:
                    if getattr(p, "id", None) is not None:
                        opciones_per[p.id] = p.nombre

                sel_per_widget = (
                    ui.select(
                        opciones_per,
                        label="Periodo (opcional)",
                        value=_s.get("observador_periodo_filter"),
                    )
                    .classes("min-w-40")
                    .props("dense outlined")
                )

                def _on_estudiante_change(e) -> None:
                    _s["observador_periodo_filter"] = sel_per_widget.value
                    _cargar_observador_para(sel_est_widget.value)

                def _on_periodo_obs_change(e) -> None:
                    _s["observador_periodo_filter"] = sel_per_widget.value or None
                    est_id = sel_est_widget.value
                    if est_id:
                        _cargar_observador_para(est_id)

                sel_est_widget.on_value_change(_on_estudiante_change)
                sel_per_widget.on_value_change(_on_periodo_obs_change)

            # Estado: error, sin selección, o timeline
            error = _s.get("observador_error")
            if error:
                empty_state(
                    icono="error_outline",
                    titulo="Error al cargar el observador",
                    descripcion=str(error),
                )
                return

            if not est_obs_id:
                empty_state(
                    icono="manage_accounts",
                    titulo="Selecciona un estudiante",
                    descripcion="Elige un estudiante del selector para ver su observador cronológico.",
                )
                return

            entradas = _s.get("observador_entradas", [])
            if not entradas:
                empty_state(
                    icono="inbox",
                    titulo="Sin entradas",
                    descripcion="Este estudiante no tiene observaciones ni registros en el período seleccionado.",
                )
                return

            # Timeline
            with ui.element("div").classes("px-4 pb-4 space-y-2"):
                for entrada in entradas:
                    _render_entrada_card(entrada)

            # Mini resumen
            resumen = _s.get("observador_resumen", {})
            if resumen:
                _render_resumen(resumen)

    # ── Helpers de renderizado de entradas ─────────────────────────────────────

    def _render_entrada_card(entrada: dict) -> None:
        tipo = entrada.get("tipo", "")
        subtipo = entrada.get("subtipo", "")
        descripcion = entrada.get("descripcion", "")
        fecha = entrada.get("fecha")
        responsable = entrada.get("responsable", "—")
        tipo_sit = entrada.get("tipo_situacion")
        medida = entrada.get("medida")
        seguimientos = entrada.get("seguimiento_entries", [])
        categoria = entrada.get("categoria")

        label = _SUBTIPO_LABEL.get(subtipo, subtipo)
        icono = _TIPO_ICONO.get(subtipo, _TIPO_ICONO.get(tipo, "circle"))
        color_cls = _TIPO_COLOR.get(subtipo, "text-gray-700")

        with ui.element("div").classes("border border-gray-200 rounded-md p-3 bg-white hover:bg-gray-50"):
            # Cabecera
            with ui.element("div").classes("flex items-center gap-2 mb-1"):
                ui.icon(icono, size="sm").classes(f"{color_cls} text-base")
                ui.label(f"{label}").classes(f"text-xs font-semibold {color_cls}")
                if tipo_sit:
                    ui.badge(tipo_sit, color="orange").props("dense")
                ui.element("div").classes("flex-1")
                ui.label(_fecha_display(fecha)).classes("text-xs text-gray-400")

            # Descripción
            ui.label(descripcion).classes("text-sm text-gray-700 leading-snug")

            # Metadatos opcionales
            meta_parts = []
            asignatura = entrada.get("asignatura")
            if asignatura:
                meta_parts.append(asignatura)
            if medida:
                meta_parts.append(f"Medida: {medida}")
            if categoria:
                meta_parts.append(f"Categoría: {categoria}")
            if meta_parts:
                ui.label(" · ".join(meta_parts)).classes("text-xs text-gray-400 mt-1")

            ui.label(f"Registrado por: {responsable}").classes("text-xs text-gray-400 mt-0.5")

            # Sub-entradas de seguimiento
            if seguimientos:
                with ui.element("div").classes("mt-2 pl-4 border-l-2 border-blue-200 space-y-1"):
                    for seg in seguimientos:
                        with ui.element("div").classes("text-xs text-gray-600"):
                            seg_fecha = _fecha_display(seg.get("fecha"))
                            seg_texto = seg.get("texto", "")
                            seg_resp = seg.get("responsable", "—")
                            ui.label(f"→ {seg_fecha}: {seg_texto}").classes("leading-snug")
                            ui.label(f"Responsable: {seg_resp}").classes("text-gray-400")

    def _render_resumen(resumen: dict) -> None:
        with ui.element("div").classes("px-4 pb-4 mt-3"):
            with ui.element("div").classes("grid grid-cols-3 gap-2 text-center"):
                campos = [
                    ("Fortalezas", resumen.get("fortalezas", 0), "text-green-700"),
                    ("Dificultades", resumen.get("dificultades", 0), "text-red-700"),
                    ("Compromisos", resumen.get("compromisos", 0), "text-yellow-700"),
                    ("Citaciones", resumen.get("citaciones", 0), "text-orange-700"),
                    ("Descargos", resumen.get("descargos", 0), "text-purple-700"),
                    ("Observaciones", resumen.get("num_observaciones", 0), "text-blue-700"),
                ]
                for nombre, valor, color in campos:
                    with ui.element("div").classes("border rounded p-2 bg-gray-50"):
                        ui.label(str(valor)).classes(f"text-lg font-bold {color}")
                        ui.label(nombre).classes("text-xs text-gray-500")

    # ── Refreshable: picker de estudiantes (zona inferior) ─────────────────────

    @ui.refreshable
    def panel_grid() -> None:
        col_defs = [
            {"headerName": "", "field": "check", "checkboxSelection": True, "headerCheckboxSelection": True, "width": 50, "sortable": False, "filter": False},
            {"headerName": "Estudiante", "field": "nombre_completo", "flex": 1, "sortable": True, "filter": True},
        ]

        grid_rows = _construir_filas_picker(_s)
        autorizado = _autorizado_para_grupo(ctx, _s.get("sel_grupo_id"))

        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("panel-toolbar"):
                ui.element("div").classes("panel-toolbar-spacer")
                if autorizado:
                    btn_ghost("Nuevo registro de comportamiento", on_click=_abrir_crear_registro, icon="flag")
                btn_ghost("Usar plantilla", on_click=_abrir_selector_plantilla, icon="description")
                btn_primary("Nueva observación", on_click=_abrir_crear_observacion, icon=Icons.ADD)

            if not _s.get("sel_grupo_id"):
                empty_state(icono="group", titulo="Selecciona un grupo", descripcion="Elige periodo, grupo y asignatura para ver los estudiantes.")
            elif not grid_rows:
                empty_state(icono="person_search", titulo="Sin estudiantes", descripcion="No hay estudiantes registrados en este grupo.")
            else:
                with ui.element("div").classes("aggrid-vh"):
                    grid = ui.aggrid(
                        {
                            "columnDefs": col_defs,
                            "rowData": grid_rows,
                            "rowSelection": "multiple",
                            "defaultColDef": {"resizable": True},
                            "suppressCellFocus": True,
                            "pagination": True,
                            "paginationPageSize": 20,
                        }
                    ).classes("w-full")
                _refs["grid"] = grid

                async def on_grid_selection(_e, _grid=grid) -> None:
                    rows = await _grid.get_selected_rows()
                    _s["sel_estudiante_ids"] = [r["estudiante_id"] for r in rows]

                grid.on("selectionChanged", on_grid_selection)

    # ── Contenido principal ────────────────────────────────────────────────────

    def contenido() -> None:
        def on_sel_change(s: dict) -> None:
            prev_grupo = _s.get("sel_grupo_id")
            presenter.aplicar_seleccion(s)
            if s["sel_grupo_id"]:
                try:
                    _s["estudiantes"] = Container.estudiante_service().listar_por_grupo(s["sel_grupo_id"])
                except Exception as exc:
                    logger.warning("Error cargando estudiantes: %s", exc)
                    _s["estudiantes"] = []
                try:
                    docente_filter = ctx.usuario_id if ctx.usuario_rol == "profesor" else None
                    _s["asignaciones_grupo"] = Container.asignacion_service().listar_por_grupo(
                        s["sel_grupo_id"], usuario_id=docente_filter,
                    )
                except Exception as exc:
                    logger.warning("Error cargando asignaciones: %s", exc)
                    _s["asignaciones_grupo"] = []
            else:
                _s["estudiantes"] = []
                _s["asignaciones_grupo"] = []
            # Si cambió el grupo, limpiar el observador
            if s["sel_grupo_id"] != prev_grupo:
                _s["observador_estudiante_id"] = None
                _s["observador_entradas"] = []
                _s["observador_resumen"] = {}
            panel_observador.refresh()
            panel_grid.refresh()

        inline_periodo_grupo_asignatura(
            _s,
            on_sel_change,
            usuario_id=ctx.usuario_id,
            institucion_id=ctx.institucion_id,
            usuario_rol=ctx.usuario_rol,
            preselect_periodo=True,
        )

        with ui.element("div").classes("page-stack"):
            panel_observador()
            panel_grid()

    app_layout(ctx, contenido, page_titulo="Observador del estudiante")


__all__ = ["observaciones_page"]
