"""
src/interface/pages/academico/estudiantes.py
=============================================
Página de gestión de estudiantes y PIAR — ZECI Manager v2.0
Ruta: /estudiantes

Secciones:
  1. Panel de filtros (grupo, estado, PIAR, búsqueda)
  2. Botones de acción (Matricular, Carga CSV) en cabecera del panel
  3. Tabla de estudiantes (@ui.refreshable)
  4. Dialog de matrícula individual
  5. Dialog de carga masiva CSV
  6. Sección resultado masivo (@ui.refreshable)
  7. Dialog de PIAR (ver / registrar / editar)

Reglas de capas:
  - NUNCA llama repositorios directamente (solo Container.*_service()).
  - NINGÚN color, tamaño ni propiedad visual en Python — solo clases CSS.
  - No importa EstadoMatricula, Estudiante ni PIAR directamente.
    Pydantic v2 coerce strings automáticamente en los DTOs.
"""
from __future__ import annotations

import csv
import io
import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary, btn_secondary, btn_danger, btn_ghost, btn_icon,
)
from src.interface.design.components import stat_card, confirm_dialog, form_dialog
from src.services.estudiante_service import (
    NuevoEstudianteDTO,
    ActualizarEstudianteDTO,
    FiltroEstudiantesDTO,
    NuevoPIARDTO,
    MatriculaMasivaResultadoDTO,
)

logger = logging.getLogger("ESTUDIANTES")


# ── Helper de args de tabla ───────────────────────────────────────────────────

def _row_from_args(args) -> dict:
    """
    Extrae el dict de fila de un evento de tabla de NiceGUI.
    Admite tanto e.args = dict como e.args = [dict] según la versión.
    """
    if isinstance(args, list):
        return args[0] if args else {}
    if isinstance(args, dict):
        return args
    return {}


# =============================================================================
# Página principal
# =============================================================================

@ui.page("/estudiantes")
def estudiantes_page() -> None:
    """Página de gestión de estudiantes — ruta /estudiantes."""

    # ── Guard de autenticación ────────────────────────────────────────────────
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    # ── Estado mutable de la página ───────────────────────────────────────────
    _s: dict = {
        "estudiantes":     [],
        "filtro_grupo_id": None,
        "filtro_estado":   None,
        "filtro_piar":     None,
        "filtro_busqueda": "",
        "grupos":          [],
        "config":          None,
        "resultado_masivo": None,
    }

    # ── Carga inicial de datos de soporte ─────────────────────────────────────
    try:
        _s["grupos"] = Container.infraestructura_service().listar_grupos()
    except Exception as exc:
        logger.error("Error cargando grupos: %s", exc)

    try:
        _s["config"] = Container.configuracion_service().get_activa()
    except Exception as exc:
        logger.error("Error cargando configuración activa: %s", exc)

    # ── Función de carga de estudiantes ──────────────────────────────────────

    def _cargar_estudiantes() -> None:
        try:
            filtro = FiltroEstudiantesDTO(
                grupo_id=_s["filtro_grupo_id"],
                estado_matricula=_s["filtro_estado"],
                posee_piar=_s["filtro_piar"],
                busqueda=_s["filtro_busqueda"] or None,
                por_pagina=200,
            )
            _s["estudiantes"] = Container.estudiante_service().listar_resumenes(filtro)
        except Exception as exc:
            logger.error("Error cargando estudiantes: %s", exc)
            _s["estudiantes"] = []

    _cargar_estudiantes()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _grupo_codigo(grupo_id: int | None) -> str:
        if grupo_id is None:
            return "—"
        for g in _s["grupos"]:
            if g.id == grupo_id:
                return g.codigo
        return str(grupo_id)

    def _estado_label(estado_str: str) -> str:
        return {
            "activo":   "Activo",
            "inactivo": "Inactivo",
            "retirado": "Retirado",
            "graduado": "Graduado",
        }.get(str(estado_str).lower(), str(estado_str))

    def _grupos_select() -> dict:
        opts: dict = {None: "Sin grupo"}
        for g in _s["grupos"]:
            opts[g.id] = f"{g.codigo} — {g.grado}"
        return opts

    # ── Procesador CSV ────────────────────────────────────────────────────────

    def _procesar_csv(content: bytes) -> None:
        try:
            texto = content.decode("utf-8")
        except UnicodeDecodeError:
            texto = content.decode("latin-1")

        reader = csv.DictReader(io.StringIO(texto))
        filas  = list(reader)

        resultado = MatriculaMasivaResultadoDTO(
            total_procesadas=len(filas),
            exitosas=0,
            fallidas=0,
            errores=[],
        )
        _mapa_grupos: dict[str, int] = {g.codigo: g.id for g in _s["grupos"]}
        svc = Container.estudiante_service()

        for i, fila in enumerate(filas, start=2):
            num_doc = fila.get("numero_documento", "").strip()
            try:
                codigo_grupo = fila.get("grupo_codigo", "").strip()
                grupo_id     = _mapa_grupos.get(codigo_grupo) if codigo_grupo else None
                dto = NuevoEstudianteDTO(
                    tipo_documento=fila.get("tipo_documento", "TI").strip() or "TI",
                    numero_documento=num_doc,
                    nombre=fila.get("nombre", "").strip(),
                    apellido=fila.get("apellido", "").strip(),
                    genero=fila.get("genero", "").strip() or None,
                    grupo_id=grupo_id,
                )
                svc.matricular(dto, usuario_id=ctx.usuario_id)
                resultado.exitosas += 1
            except Exception as exc:
                resultado.agregar_error(fila=i, dato=num_doc or "?", motivo=str(exc))

        _s["resultado_masivo"] = resultado
        _cargar_estudiantes()
        tabla_refreshable.refresh()
        resultado_refreshable.refresh()

        if resultado.fue_exitosa:
            ui.notify(f"Carga completada: {resultado.exitosas} estudiantes matriculados.", type="positive")
        else:
            ui.notify(
                f"{resultado.exitosas} exitosas, {resultado.fallidas} fallidas. "
                "Revisa la sección de resultados.",
                type="warning",
            )

    # =========================================================================
    # CONSTRUCCIÓN DE LA UI
    # =========================================================================

    def contenido() -> None:

        # ── Refreshables ──────────────────────────────────────────────────────

        @ui.refreshable
        def tabla_refreshable() -> None:
            """Tabla de estudiantes con acciones inline."""
            estudiantes = _s["estudiantes"]

            if not estudiantes:
                with ui.element("div").classes("tablero-empty panel-card"):
                    with ui.element("div").classes("tablero-empty-icon"):
                        ThemeManager.icono(Icons.STUDENTS, size=40)
                    ui.label("Sin estudiantes").classes("panel-title")
                    ui.label(
                        "No hay estudiantes con los filtros seleccionados."
                    ).classes("tablero-panel-subtitle")
                return

            filas = []
            for est in estudiantes:
                estado_val = (
                    est.estado_matricula.value
                    if hasattr(est.estado_matricula, "value")
                    else str(est.estado_matricula)
                )
                filas.append({
                    "id":              est.id,
                    "nombre_completo": est.nombre_completo,
                    "documento_display": est.documento_display,
                    "grupo_codigo":    _grupo_codigo(est.grupo_id),
                    "estado_str":      _estado_label(estado_val),
                    "estado_raw":      estado_val,
                    "piar_badge":      "Sí" if est.posee_piar else "No",
                    "posee_piar":      est.posee_piar,
                })

            columnas = [
                {"name": "nombre",   "label": "Estudiante", "field": "nombre_completo",   "align": "left",   "sortable": True},
                {"name": "doc",      "label": "Documento",  "field": "documento_display",  "align": "left"},
                {"name": "grupo",    "label": "Grupo",      "field": "grupo_codigo",        "align": "center"},
                {"name": "estado",   "label": "Estado",     "field": "estado_str",          "align": "center", "sortable": True},
                {"name": "piar",     "label": "PIAR",       "field": "piar_badge",          "align": "center"},
                {"name": "acciones", "label": "Acciones",   "field": "id",                  "align": "center"},
            ]

            tabla = ui.table(columns=columnas, rows=filas, row_key="id").classes("w-full")

            tabla.add_slot("body-cell-acciones", """
                <q-td :props="props" class="q-gutter-xs">
                    <q-btn flat dense size="sm" icon="edit" color="primary"
                           @click="$emit('editar', props.row)" />
                    <q-btn v-if="props.row.estado_raw !== 'retirado'"
                           flat dense size="sm" icon="person_remove" color="negative"
                           @click="$emit('retirar', props.row)" />
                    <q-btn flat dense size="sm" icon="description" color="secondary"
                           @click="$emit('piar', props.row)" />
                </q-td>
            """)

            tabla.add_slot("body-cell-piar", """
                <q-td :props="props" class="text-center">
                    <q-badge
                        :color="props.row.posee_piar ? 'teal' : 'grey-4'"
                        :label="props.row.piar_badge"
                        :text-color="props.row.posee_piar ? 'white' : 'grey-7'"
                    />
                </q-td>
            """)

            tabla.on("editar",  lambda e: _abrir_dialog_edicion(_row_from_args(e.args)))
            tabla.on("retirar", lambda e: _confirmar_retiro(_row_from_args(e.args)))
            tabla.on("piar",    lambda e: _abrir_dialog_piar(_row_from_args(e.args)))

        @ui.refreshable
        def resultado_refreshable() -> None:
            resultado = _s.get("resultado_masivo")
            if resultado is None:
                return

            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("panel-header"):
                    ThemeManager.icono("upload_file", size=20)
                    ui.label("Resultado de carga masiva").classes("panel-title")

                with ui.element("div").classes("tablero-kpi-row"):
                    stat_card("Total procesadas", resultado.total_procesadas, "check_circle", variante="info")
                    stat_card("Exitosas",  resultado.exitosas,  "check",
                              variante="success" if resultado.exitosas > 0 else "info")
                    stat_card("Fallidas",  resultado.fallidas,  "error",
                              variante="danger"  if resultado.fallidas > 0 else "success")

                if resultado.errores:
                    ui.label("Detalle de errores (máx. 10):").classes("text-weight-medium q-mt-md")
                    for err in resultado.errores[:10]:
                        ui.label(
                            f"Fila {err['fila']} — Doc: {err['dato']} — {err['motivo']}"
                        ).classes("text-caption text-negative q-mb-xs")

                btn_secondary("Limpiar resultado", icon="close",
                              on_click=lambda: (_s.update({"resultado_masivo": None}),
                                                resultado_refreshable.refresh())).classes("q-mt-sm")

        # ── Acciones de página ────────────────────────────────────────────────

        def _abrir_dialog_matricula() -> None:
            def _guardar(datos: dict) -> "bool | None":
                try:
                    dto = NuevoEstudianteDTO(
                        tipo_documento=datos.get("tipo_documento") or "TI",
                        numero_documento=str(datos.get("numero_documento", "")).strip(),
                        nombre=str(datos.get("nombre", "")).strip(),
                        apellido=str(datos.get("apellido", "")).strip(),
                        grupo_id=datos.get("grupo_id"),
                        genero=datos.get("genero"),
                        posee_piar=bool(datos.get("posee_piar", False)),
                    )
                    Container.estudiante_service().matricular(dto, usuario_id=ctx.usuario_id)
                    ui.notify("Estudiante matriculado exitosamente.", type="positive")
                    _cargar_estudiantes()
                    tabla_refreshable.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                    return False
                except Exception as exc:
                    logger.error("Error matriculando: %s", exc)
                    ui.notify("Error inesperado al matricular.", type="negative")
                    return False

            form_dialog(
                titulo="Matricular estudiante",
                campos=[
                    {"key": "tipo_documento",   "label": "Tipo documento",    "tipo": "select",
                     "opciones": {"TI": "TI", "CC": "CC", "CE": "CE", "NUIP": "NUIP"}, "valor": "TI"},
                    {"key": "numero_documento", "label": "Número documento",  "tipo": "text",   "requerido": True},
                    {"key": "nombre",           "label": "Nombre",            "tipo": "text",   "requerido": True},
                    {"key": "apellido",         "label": "Apellido",          "tipo": "text",   "requerido": True},
                    {"key": "grupo_id",         "label": "Grupo",             "tipo": "select", "opciones": _grupos_select()},
                    {"key": "genero",           "label": "Género",            "tipo": "select",
                     "opciones": {None: "No especificado", "M": "Masculino", "F": "Femenino", "OTRO": "Otro"}},
                    {"key": "posee_piar",       "label": "Posee PIAR",        "tipo": "checkbox", "valor": False},
                ],
                on_submit=_guardar,
                texto_submit="Matricular",
                max_width="max-w-lg",
                columnas=2,
            )

        def _abrir_dialog_csv() -> None:
            with ui.dialog() as dlg, ui.card().classes("w-full"):
                ui.label("Carga masiva por CSV").classes("text-h6")
                ui.label(
                    "Formato: tipo_documento, numero_documento, nombre, apellido, genero, grupo_codigo"
                ).classes("text-caption text-grey q-mb-md")
                ui.upload(
                    label="Seleccionar archivo CSV",
                    on_upload=lambda e: (_procesar_csv(e.content.read()), dlg.close()),
                    auto_upload=True,
                ).props("accept=.csv").classes("w-full")
                with ui.row().classes("q-mt-md justify-end"):
                    btn_ghost("Cerrar", on_click=dlg.close)
            dlg.open()

        def _abrir_dialog_edicion(fila: dict) -> None:
            est_id = fila.get("id")
            if not est_id:
                return
            try:
                est = Container.estudiante_service().get_by_id(est_id)
            except Exception as exc:
                logger.error("Error cargando estudiante %s: %s", est_id, exc)
                ui.notify("No se pudo cargar el estudiante.", type="negative")
                return

            estado_raw  = est.estado_matricula.value if hasattr(est.estado_matricula, "value") else str(est.estado_matricula)
            genero_actual = (
                est.genero.value if est.genero and hasattr(est.genero, "value")
                else (str(est.genero) if est.genero else None)
            )

            def _guardar_edicion(datos: dict) -> "bool | None":
                try:
                    dto = ActualizarEstudianteDTO(
                        nombre=str(datos.get("nombre", "")).strip() or None,
                        apellido=str(datos.get("apellido", "")).strip() or None,
                        genero=datos.get("genero"),
                        grupo_id=datos.get("grupo_id"),
                        posee_piar=bool(datos.get("posee_piar", False)),
                        estado_matricula=datos.get("estado"),
                    )
                    Container.estudiante_service().actualizar(est_id, dto, usuario_id=ctx.usuario_id)
                    ui.notify("Estudiante actualizado.", type="positive")
                    _cargar_estudiantes()
                    tabla_refreshable.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                    return False
                except Exception as exc:
                    logger.error("Error actualizando %s: %s", est_id, exc)
                    ui.notify("Error inesperado al actualizar.", type="negative")
                    return False

            form_dialog(
                titulo=f"Editar — {est.nombre_completo}",
                campos=[
                    {"key": "nombre",     "label": "Nombre",    "tipo": "text",     "valor": est.nombre,   "requerido": True},
                    {"key": "apellido",   "label": "Apellido",  "tipo": "text",     "valor": est.apellido, "requerido": True},
                    {"key": "estado",     "label": "Estado",    "tipo": "select",   "valor": estado_raw,
                     "opciones": {"activo": "Activo", "inactivo": "Inactivo", "retirado": "Retirado", "graduado": "Graduado"}},
                    {"key": "grupo_id",   "label": "Grupo",     "tipo": "select",   "valor": est.grupo_id, "opciones": _grupos_select()},
                    {"key": "genero",     "label": "Género",    "tipo": "select",   "valor": genero_actual,
                     "opciones": {None: "No especificado", "M": "Masculino", "F": "Femenino", "OTRO": "Otro"}},
                    {"key": "posee_piar", "label": "Posee PIAR","tipo": "checkbox", "valor": est.posee_piar},
                ],
                on_submit=_guardar_edicion,
                max_width="max-w-lg",
                columnas=2,
            )

        def _confirmar_retiro(fila: dict) -> None:
            est_id = fila.get("id")
            nombre = fila.get("nombre_completo", "este estudiante")
            if not est_id:
                return

            def _ejecutar() -> None:
                try:
                    Container.estudiante_service().retirar(est_id, motivo=None, usuario_id=ctx.usuario_id)
                    ui.notify(f"{nombre} retirado.", type="positive")
                    _cargar_estudiantes()
                    tabla_refreshable.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error retirando %s: %s", est_id, exc)
                    ui.notify("Error inesperado al retirar.", type="negative")

            confirm_dialog(
                titulo="Retirar estudiante",
                mensaje=f"¿Retirar a {nombre} de la matrícula? El estado cambiará a Retirado.",
                on_confirm=_ejecutar,
                variante="danger",
                texto_confirmar="Retirar",
            )

        def _abrir_dialog_piar(fila: dict) -> None:
            est_id = fila.get("id")
            nombre = fila.get("nombre_completo", "Estudiante")
            if not est_id:
                return

            anio_id = _s["config"].id if _s["config"] else None
            if not anio_id:
                ui.notify("No hay año escolar activo configurado.", type="warning")
                return

            piar = None
            try:
                piar = Container.estudiante_service().get_piar(est_id, anio_id)
            except Exception as exc:
                logger.error("Error cargando PIAR est=%s anio=%s: %s", est_id, anio_id, exc)

            with ui.dialog() as dlg, ui.card().classes("w-full max-w-lg"):
                with ui.row().classes("items-center justify-between w-full q-mb-md"):
                    ui.label(f"PIAR — {nombre}").classes("text-h6")
                    btn_icon("close", on_click=dlg.close, variante="ghost")

                if piar is not None:
                    # ── Modo edición de PIAR existente ────────────────────────
                    ui.label("PIAR registrado — puedes actualizar los campos:").classes(
                        "text-caption text-grey q-mb-sm"
                    )

                    descripcion_ta = ui.textarea(
                        label="Descripción de necesidades",
                        value=piar.descripcion_necesidad or "",
                    ).classes("w-full q-mb-sm")

                    ajustes_eval_ta = ui.textarea(
                        label="Ajustes evaluativos",
                        value=piar.ajustes_evaluativos or "",
                    ).classes("w-full q-mb-sm")

                    ajustes_ped_ta = ui.textarea(
                        label="Ajustes pedagógicos",
                        value=piar.ajustes_pedagogicos or "",
                    ).classes("w-full q-mb-sm")

                    profesionales_inp = ui.input(
                        label="Profesionales de apoyo",
                        value=piar.profesionales_apoyo or "",
                    ).classes("w-full")

                    fecha_elab = (
                        piar.fecha_elaboracion.strftime("%d/%m/%Y")
                        if getattr(piar, "fecha_elaboracion", None)
                        else "—"
                    )
                    ui.label(f"Fecha elaboración: {fecha_elab}").classes("text-caption text-grey q-mt-xs")

                    def _actualizar_piar() -> None:
                        try:
                            dto = NuevoPIARDTO(
                                estudiante_id=est_id,
                                anio_id=anio_id,
                                descripcion_necesidad=descripcion_ta.value,
                                ajustes_evaluativos=ajustes_eval_ta.value or None,
                                ajustes_pedagogicos=ajustes_ped_ta.value or None,
                                profesionales_apoyo=profesionales_inp.value or None,
                            )
                            Container.estudiante_service().registrar_piar(dto, usuario_id=ctx.usuario_id)
                            ui.notify("PIAR actualizado.", type="positive")
                            dlg.close()
                            _cargar_estudiantes()
                            tabla_refreshable.refresh()
                        except ValueError as exc:
                            # Si ya existe, intentar actualizar (servicio puede lanzar ValueError)
                            ui.notify(str(exc), type="warning")
                        except Exception as exc:
                            logger.error("Error actualizando PIAR est=%s: %s", est_id, exc)
                            ui.notify("Error inesperado al actualizar el PIAR.", type="negative")

                    with ui.row().classes("q-mt-md justify-end gap-2"):
                        btn_ghost("Cancelar", on_click=dlg.close)
                        btn_primary("Actualizar PIAR", on_click=_actualizar_piar)

                else:
                    # ── Modo registro de PIAR nuevo ───────────────────────────
                    ui.label("Registrar PIAR nuevo").classes("text-subtitle2 q-mb-sm")

                    descripcion_ta = ui.textarea(
                        label="Descripción de necesidades *",
                        placeholder="Describe las necesidades educativas del estudiante...",
                    ).classes("w-full")

                    ajustes_eval_ta = ui.textarea(
                        label="Ajustes evaluativos",
                        placeholder="Ajustes en la forma de evaluar...",
                    ).classes("w-full")

                    ajustes_ped_ta = ui.textarea(
                        label="Ajustes pedagógicos",
                        placeholder="Estrategias pedagógicas diferenciadas...",
                    ).classes("w-full")

                    profesionales_inp = ui.input(
                        label="Profesionales de apoyo",
                        placeholder="Fonoaudióloga, psicóloga, etc.",
                    ).classes("w-full")

                    def _guardar_piar() -> None:
                        if not descripcion_ta.value.strip():
                            ui.notify("La descripción de necesidades es obligatoria.", type="warning")
                            return
                        try:
                            dto = NuevoPIARDTO(
                                estudiante_id=est_id,
                                anio_id=anio_id,
                                descripcion_necesidad=descripcion_ta.value,
                                ajustes_evaluativos=ajustes_eval_ta.value or None,
                                ajustes_pedagogicos=ajustes_ped_ta.value or None,
                                profesionales_apoyo=profesionales_inp.value or None,
                            )
                            Container.estudiante_service().registrar_piar(dto, usuario_id=ctx.usuario_id)
                            ui.notify("PIAR registrado exitosamente.", type="positive")
                            dlg.close()
                            _cargar_estudiantes()
                            tabla_refreshable.refresh()
                        except ValueError as exc:
                            ui.notify(str(exc), type="warning")
                        except Exception as exc:
                            logger.error("Error registrando PIAR est=%s: %s", est_id, exc)
                            ui.notify("Error inesperado al registrar el PIAR.", type="negative")

                    with ui.row().classes("q-mt-md justify-end gap-2"):
                        btn_ghost("Cancelar", on_click=dlg.close)
                        btn_primary("Registrar PIAR", on_click=_guardar_piar)

            dlg.open()

        # ── Renderizado de la página ──────────────────────────────────────────

        with ui.element("div").classes("page-stack"):

            # ── 1. Panel de filtros ───────────────────────────────────────────
            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("panel-header"):
                    ThemeManager.icono("filter_list", size=20)
                    ui.label("Filtros").classes("panel-title")

                with ui.row().classes("w-full q-col-gutter-md items-end"):
                    _grupos_opts: dict = {None: "Todos los grupos"}
                    for g in _s["grupos"]:
                        _grupos_opts[g.id] = g.codigo

                    ui.select(
                        label="Grupo",
                        options=_grupos_opts,
                        value=None,
                        on_change=lambda e: _s.update({"filtro_grupo_id": e.value}),
                    ).classes("col-3")

                    ui.select(
                        label="Estado",
                        options={None: "Todos", "activo": "Activo", "inactivo": "Inactivo",
                                 "retirado": "Retirado", "graduado": "Graduado"},
                        value=None,
                        on_change=lambda e: _s.update({"filtro_estado": e.value}),
                    ).classes("col-3")

                    ui.checkbox(
                        "Solo con PIAR",
                        on_change=lambda e: _s.update({"filtro_piar": True if e.value else None}),
                    )

                    ui.input(
                        label="Buscar (nombre / documento)",
                        on_change=lambda e: _s.update({"filtro_busqueda": e.value}),
                    ).classes("col-4")

                    btn_primary(
                        "Buscar",
                        icon=Icons.SEARCH,
                        on_click=lambda: (_cargar_estudiantes(), tabla_refreshable.refresh()),
                    )

            # ── 2. Tabla de estudiantes (con botones de acción en cabecera) ───
            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("panel-header"):
                    ThemeManager.icono(Icons.STUDENTS, size=20)
                    with ui.element("div").classes("flex-1"):
                        ui.label("Estudiantes").classes("panel-title")
                        ui.label(
                            f"{len(_s['estudiantes'])} resultado(s)"
                        ).classes("tablero-panel-subtitle")

                    # ── 2a. Botones de acción ─────────────────────────────────
                    with ui.row().classes("gap-2"):
                        btn_primary(
                            "Matricular",
                            icon="person_add",
                            on_click=_abrir_dialog_matricula,
                            size="sm",
                        )
                        btn_secondary(
                            "Carga CSV",
                            icon="upload_file",
                            on_click=_abrir_dialog_csv,
                            size="sm",
                        )

                tabla_refreshable()

            # ── 3. Sección resultado masivo ───────────────────────────────────
            resultado_refreshable()

    # ── Layout principal ──────────────────────────────────────────────────────
    app_layout(
        ctx,
        contenido,
        page_titulo    = "Gestión de Estudiantes",
        page_subtitulo = "Matrícula, estado y PIAR",
        page_icono     = Icons.STUDENTS,
    )


__all__ = ["estudiantes_page"]
