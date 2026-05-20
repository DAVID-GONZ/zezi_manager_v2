"""
src/interface/pages/academico/estudiantes.py
=============================================
Página de gestión de estudiantes y PIAR — ZECI Manager v2.0
Ruta: /estudiantes

Secciones:
  1. Panel de filtros (grupo, estado, PIAR, búsqueda)
  2. Botones de acción (Matricular, Carga CSV)
  3. Tabla de estudiantes (@ui.refreshable)
  4. Dialog de matrícula individual
  5. Dialog de carga masiva CSV
  6. Sección resultado masivo (@ui.refreshable)
  7. Dialog de PIAR (ver / registrar)

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
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger, btn_ghost
from src.interface.design.components import stat_card, page_header, confirm_dialog
from src.services.estudiante_service import (
    NuevoEstudianteDTO,
    ActualizarEstudianteDTO,
    FiltroEstudiantesDTO,
    NuevoPIARDTO,
    MatriculaMasivaResultadoDTO,
)

logger = logging.getLogger("ESTUDIANTES")

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
        "estudiantes": [],
        "filtro_grupo_id": None,
        "filtro_estado": None,       # None = todos, "activo", "retirado", etc.
        "filtro_piar": None,         # None = todos, True = solo con PIAR
        "filtro_busqueda": "",
        "grupos": [],                # list[Grupo] para selector de filtro
        "config": None,              # ConfiguracionAnio activa
        "resultado_masivo": None,    # MatriculaMasivaResultadoDTO | None
    }

    # ── Carga inicial de datos de soporte ─────────────────────────────────────
    try:
        _s["grupos"] = Container.infraestructura_service().listar_grupos()
    except Exception as exc:
        logger.error("Error cargando grupos: %s", exc)
        _s["grupos"] = []

    try:
        cfg_service = Container.configuracion_service()
        _s["config"] = cfg_service.get_activa()
    except Exception as exc:
        logger.error("Error cargando configuración activa: %s", exc)
        _s["config"] = None

    # ── Función de carga de estudiantes ──────────────────────────────────────

    def _cargar_estudiantes() -> None:
        """Recarga la lista de estudiantes con los filtros activos."""
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

    # Carga inicial
    _cargar_estudiantes()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _grupo_codigo(grupo_id: int | None) -> str:
        """Devuelve el código del grupo o '—' si no está asignado."""
        if grupo_id is None:
            return "—"
        for g in _s["grupos"]:
            if g.id == grupo_id:
                return g.codigo
        return str(grupo_id)

    def _estado_label(estado_str: str) -> str:
        """Convierte el valor string del estado a etiqueta para mostrar."""
        _mapa = {
            "activo": "Activo",
            "inactivo": "Inactivo",
            "retirado": "Retirado",
            "graduado": "Graduado",
        }
        return _mapa.get(str(estado_str).lower(), str(estado_str))

    # ── Procesador CSV ────────────────────────────────────────────────────────

    def _procesar_csv(content: bytes) -> None:
        """
        Procesa el contenido de un CSV de matrícula masiva.

        Formato esperado:
            tipo_documento,numero_documento,nombre,apellido,genero,grupo_codigo
        """
        # Decodificación con fallback
        try:
            texto = content.decode("utf-8")
        except UnicodeDecodeError:
            texto = content.decode("latin-1")

        reader = csv.DictReader(io.StringIO(texto))
        filas = list(reader)

        resultado = MatriculaMasivaResultadoDTO(
            total_procesadas=len(filas),
            exitosas=0,
            fallidas=0,
            errores=[],
        )

        # Mapa grupo_codigo → grupo_id para resolver el campo del CSV
        _mapa_grupos: dict[str, int] = {
            g.codigo: g.id for g in _s["grupos"]
        }

        svc = Container.estudiante_service()

        for i, fila in enumerate(filas, start=2):  # start=2: fila 1 = cabeceras
            num_doc = fila.get("numero_documento", "").strip()
            try:
                # Resolver grupo_id desde grupo_codigo si está presente
                codigo_grupo = fila.get("grupo_codigo", "").strip()
                grupo_id = _mapa_grupos.get(codigo_grupo) if codigo_grupo else None

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

            except (ValueError, Exception) as exc:
                resultado.agregar_error(
                    fila=i,
                    dato=num_doc or "?",
                    motivo=str(exc),
                )

        _s["resultado_masivo"] = resultado
        _cargar_estudiantes()
        tabla_refreshable.refresh()
        resultado_refreshable.refresh()

        if resultado.fue_exitosa:
            ui.notify(
                f"Carga completada: {resultado.exitosas} estudiantes matriculados.",
                type="positive",
            )
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

            # Construir filas para ui.table
            filas = []
            for est in estudiantes:
                estado_val = (
                    est.estado_matricula.value
                    if hasattr(est.estado_matricula, "value")
                    else str(est.estado_matricula)
                )
                filas.append({
                    "id": est.id,
                    "nombre_completo": est.nombre_completo,
                    "documento_display": est.documento_display,
                    "grupo_codigo": _grupo_codigo(est.grupo_id),
                    "estado_str": _estado_label(estado_val),
                    "estado_raw": estado_val,
                    "piar_badge": "Sí" if est.posee_piar else "No",
                    "posee_piar": est.posee_piar,
                })

            columnas = [
                {
                    "name": "nombre",
                    "label": "Estudiante",
                    "field": "nombre_completo",
                    "align": "left",
                    "sortable": True,
                },
                {
                    "name": "doc",
                    "label": "Documento",
                    "field": "documento_display",
                    "align": "left",
                },
                {
                    "name": "grupo",
                    "label": "Grupo",
                    "field": "grupo_codigo",
                    "align": "center",
                },
                {
                    "name": "estado",
                    "label": "Estado",
                    "field": "estado_str",
                    "align": "center",
                    "sortable": True,
                },
                {
                    "name": "piar",
                    "label": "PIAR",
                    "field": "piar_badge",
                    "align": "center",
                },
                {
                    "name": "acciones",
                    "label": "Acciones",
                    "field": "id",
                    "align": "center",
                },
            ]

            tabla = ui.table(
                columns=columnas,
                rows=filas,
                row_key="id",
            ).classes("w-full")

            # Slot para columna de acciones con botones inline
            tabla.add_slot("body-cell-acciones", """
                <q-td :props="props" class="q-gutter-xs">
                    <q-btn
                        flat dense size="sm" icon="edit" color="primary"
                        @click="$emit('editar', props.row)"
                    />
                    <q-btn
                        v-if="props.row.estado_raw !== 'retirado'"
                        flat dense size="sm" icon="person_remove" color="negative"
                        @click="$emit('retirar', props.row)"
                    />
                    <q-btn
                        flat dense size="sm" icon="description" color="secondary"
                        @click="$emit('piar', props.row)"
                    />
                </q-td>
            """)

            # Slot para columna de PIAR con badge visual
            tabla.add_slot("body-cell-piar", """
                <q-td :props="props" class="text-center">
                    <q-badge
                        :color="props.row.posee_piar ? 'teal' : 'grey-4'"
                        :label="props.row.piar_badge"
                        :text-color="props.row.posee_piar ? 'white' : 'grey-7'"
                    />
                </q-td>
            """)

            # Handlers de eventos de los botones
            tabla.on("editar", lambda e: _abrir_dialog_edicion(e.args))
            tabla.on("retirar", lambda e: _confirmar_retiro(e.args))
            tabla.on("piar", lambda e: _abrir_dialog_piar(e.args))

        @ui.refreshable
        def resultado_refreshable() -> None:
            """Sección de resultado de carga masiva."""
            resultado = _s.get("resultado_masivo")
            if resultado is None:
                return

            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("panel-header"):
                    ThemeManager.icono("upload_file", size=20)
                    ui.label("Resultado de carga masiva").classes("panel-title")

                with ui.element("div").classes("tablero-kpi-row"):
                    stat_card("Total procesadas", resultado.total_procesadas, "check_circle", variante="info")
                    stat_card("Exitosas", resultado.exitosas, "check",
                              variante="success" if resultado.exitosas > 0 else "info")
                    stat_card("Fallidas", resultado.fallidas, "error",
                              variante="danger" if resultado.fallidas > 0 else "success")

                if resultado.errores:
                    ui.label("Detalle de errores (máx. 10):").classes("text-weight-medium q-mt-md")
                    errores_mostrar = resultado.errores[:10]
                    for err in errores_mostrar:
                        with ui.element("div").classes("q-mb-xs"):
                            ui.label(
                                f"Fila {err['fila']} — Doc: {err['dato']} — {err['motivo']}"
                            ).classes("text-caption text-negative")

                btn_secondary(
                    "Limpiar resultado",
                    icon="close",
                    on_click=lambda: _limpiar_resultado(),
                ).classes("q-mt-sm")

        # ── Funciones de acción ───────────────────────────────────────────────

        def _limpiar_resultado() -> None:
            _s["resultado_masivo"] = None
            resultado_refreshable.refresh()

        def _abrir_dialog_matricula() -> None:
            """Dialog para matricular un estudiante individual."""
            _grupos_select: dict = {None: "Sin grupo"}
            for g in _s["grupos"]:
                _grupos_select[g.id] = f"{g.codigo} — {g.grado}"

            with ui.dialog() as dlg, ui.card().classes("w-full"):
                ui.label("Matricular estudiante").classes("text-h6 q-mb-md")

                tipo_doc = ui.select(
                    label="Tipo documento",
                    options={"TI": "TI", "CC": "CC", "CE": "CE", "NUIP": "NUIP"},
                    value="TI",
                ).classes("w-full")

                num_doc = ui.input(label="Número de documento").classes("w-full")
                nombre_inp = ui.input(label="Nombre").classes("w-full")
                apellido_inp = ui.input(label="Apellido").classes("w-full")

                grupo_sel = ui.select(
                    label="Grupo",
                    options=_grupos_select,
                    value=None,
                ).classes("w-full")

                genero_sel = ui.select(
                    label="Género",
                    options={None: "No especificado", "M": "Masculino", "F": "Femenino", "OTRO": "Otro"},
                    value=None,
                ).classes("w-full")

                piar_chk = ui.checkbox("Posee PIAR")

                with ui.row().classes("q-mt-md justify-end gap-sm"):
                    btn_ghost("Cancelar", on_click=dlg.close)

                    def _guardar_matricula() -> None:
                        try:
                            dto = NuevoEstudianteDTO(
                                tipo_documento=tipo_doc.value,
                                numero_documento=num_doc.value,
                                nombre=nombre_inp.value,
                                apellido=apellido_inp.value,
                                grupo_id=grupo_sel.value,
                                genero=genero_sel.value,
                                posee_piar=piar_chk.value,
                            )
                            Container.estudiante_service().matricular(
                                dto, usuario_id=ctx.usuario_id
                            )
                            ui.notify("Estudiante matriculado exitosamente.", type="positive")
                            dlg.close()
                            _cargar_estudiantes()
                            tabla_refreshable.refresh()
                        except ValueError as exc:
                            ui.notify(str(exc), type="warning")
                        except Exception as exc:
                            logger.error("Error matriculando estudiante: %s", exc)
                            ui.notify("Error inesperado al matricular.", type="negative")

                    btn_primary("Guardar", on_click=_guardar_matricula)

            dlg.open()

        def _abrir_dialog_csv() -> None:
            """Dialog para carga masiva de estudiantes por CSV."""
            with ui.dialog() as dlg, ui.card().classes("w-full"):
                ui.label("Carga masiva por CSV").classes("text-h6")
                ui.label(
                    "Formato: tipo_documento, numero_documento, nombre, apellido, "
                    "genero, grupo_codigo"
                ).classes("text-caption text-grey q-mb-md")

                ui.upload(
                    label="Seleccionar archivo CSV",
                    on_upload=lambda e: (
                        _procesar_csv(e.content.read()),
                        dlg.close(),
                    ),
                    auto_upload=True,
                ).props("accept=.csv").classes("w-full")

                with ui.row().classes("q-mt-md justify-end"):
                    btn_ghost("Cerrar", on_click=dlg.close)

            dlg.open()

        def _abrir_dialog_edicion(fila: dict) -> None:
            """Dialog para editar datos de un estudiante existente."""
            est_id = fila.get("id")
            if not est_id:
                return

            _grupos_select: dict = {None: "Sin grupo"}
            for g in _s["grupos"]:
                _grupos_select[g.id] = f"{g.codigo} — {g.grado}"

            # Buscar datos completos del estudiante
            try:
                est = Container.estudiante_service().get_by_id(est_id)
            except Exception as exc:
                logger.error("Error cargando estudiante %s: %s", est_id, exc)
                ui.notify("No se pudo cargar el estudiante.", type="negative")
                return

            with ui.dialog() as dlg, ui.card().classes("w-full"):
                ui.label(f"Editar — {est.nombre_completo}").classes("text-h6 q-mb-md")

                nombre_inp = ui.input(
                    label="Nombre", value=est.nombre
                ).classes("w-full")
                apellido_inp = ui.input(
                    label="Apellido", value=est.apellido
                ).classes("w-full")

                estado_raw = (
                    est.estado_matricula.value
                    if hasattr(est.estado_matricula, "value")
                    else str(est.estado_matricula)
                )
                estado_sel = ui.select(
                    label="Estado",
                    options={
                        "activo": "Activo",
                        "inactivo": "Inactivo",
                        "retirado": "Retirado",
                        "graduado": "Graduado",
                    },
                    value=estado_raw,
                ).classes("w-full")

                grupo_id_actual = est.grupo_id
                grupo_sel = ui.select(
                    label="Grupo",
                    options=_grupos_select,
                    value=grupo_id_actual,
                ).classes("w-full")

                genero_actual = (
                    est.genero.value
                    if est.genero and hasattr(est.genero, "value")
                    else (str(est.genero) if est.genero else None)
                )
                genero_sel = ui.select(
                    label="Género",
                    options={
                        None: "No especificado",
                        "M": "Masculino",
                        "F": "Femenino",
                        "OTRO": "Otro",
                    },
                    value=genero_actual,
                ).classes("w-full")

                piar_chk = ui.checkbox("Posee PIAR", value=est.posee_piar)

                with ui.row().classes("q-mt-md justify-end gap-sm"):
                    btn_ghost("Cancelar", on_click=dlg.close)

                    def _guardar_edicion() -> None:
                        try:
                            dto = ActualizarEstudianteDTO(
                                nombre=nombre_inp.value or None,
                                apellido=apellido_inp.value or None,
                                genero=genero_sel.value,
                                grupo_id=grupo_sel.value,
                                posee_piar=piar_chk.value,
                                estado_matricula=estado_sel.value,
                            )
                            Container.estudiante_service().actualizar(
                                est_id, dto, usuario_id=ctx.usuario_id
                            )
                            ui.notify("Estudiante actualizado.", type="positive")
                            dlg.close()
                            _cargar_estudiantes()
                            tabla_refreshable.refresh()
                        except ValueError as exc:
                            ui.notify(str(exc), type="warning")
                        except Exception as exc:
                            logger.error("Error actualizando estudiante %s: %s", est_id, exc)
                            ui.notify("Error inesperado al actualizar.", type="negative")

                    btn_primary("Guardar", on_click=_guardar_edicion)

            dlg.open()

        def _confirmar_retiro(fila: dict) -> None:
            """Dialog de confirmación antes de retirar un estudiante."""
            est_id = fila.get("id")
            nombre = fila.get("nombre_completo", "este estudiante")
            if not est_id:
                return

            def _ejecutar_retiro(eid=est_id, nom=nombre) -> None:
                try:
                    Container.estudiante_service().retirar(
                        eid,
                        motivo=None,
                        usuario_id=ctx.usuario_id,
                    )
                    ui.notify(f"{nom} retirado.", type="positive")
                    _cargar_estudiantes()
                    tabla_refreshable.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error retirando estudiante %s: %s", eid, exc)
                    ui.notify("Error inesperado al retirar.", type="negative")

            confirm_dialog(
                titulo          = "Retirar estudiante",
                mensaje         = f"¿Retirar a {nombre} de la matrícula? El estado cambiará a Retirado.",
                on_confirm      = _ejecutar_retiro,
                variante        = "danger",
                texto_confirmar = "Retirar",
            )

        def _abrir_dialog_piar(fila: dict) -> None:
            """Dialog para ver o registrar el PIAR de un estudiante."""
            est_id = fila.get("id")
            nombre = fila.get("nombre_completo", "Estudiante")
            if not est_id:
                return

            anio_id = _s["config"].id if _s["config"] else None
            if not anio_id:
                ui.notify(
                    "No hay año escolar activo configurado. "
                    "Contacta al administrador.",
                    type="warning",
                )
                return

            # Cargar PIAR existente si hay
            piar = None
            try:
                piar = Container.estudiante_service().get_piar(est_id, anio_id)
            except Exception as exc:
                logger.error("Error cargando PIAR est=%s anio=%s: %s", est_id, anio_id, exc)

            with ui.dialog() as dlg, ui.card().classes("w-full"):
                ui.label(f"PIAR — {nombre}").classes("text-h6 q-mb-md")

                if piar is not None:
                    # Modo lectura — PIAR ya registrado
                    ui.label("PIAR registrado (solo lectura en esta versión).").classes(
                        "text-caption text-grey q-mb-sm"
                    )

                    ui.label("Descripción de necesidades:").classes("text-weight-medium")
                    ui.label(piar.descripcion_necesidad or "—").classes(
                        "text-body2 q-mb-sm"
                    )

                    ui.label("Ajustes evaluativos:").classes("text-weight-medium")
                    ui.label(piar.ajustes_evaluativos or "—").classes(
                        "text-body2 q-mb-sm"
                    )

                    ui.label("Ajustes pedagógicos:").classes("text-weight-medium")
                    ui.label(piar.ajustes_pedagogicos or "—").classes(
                        "text-body2 q-mb-sm"
                    )

                    ui.label("Profesionales de apoyo:").classes("text-weight-medium")
                    ui.label(piar.profesionales_apoyo or "—").classes(
                        "text-body2 q-mb-sm"
                    )

                    fecha_elab = (
                        piar.fecha_elaboracion.strftime("%d/%m/%Y")
                        if piar.fecha_elaboracion
                        else "—"
                    )
                    ui.label(f"Fecha elaboración: {fecha_elab}").classes("text-caption text-grey")

                    with ui.row().classes("q-mt-md justify-end"):
                        btn_ghost("Cerrar", on_click=dlg.close)

                else:
                    # Modo registro — nuevo PIAR
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

                    with ui.row().classes("q-mt-md justify-end gap-sm"):
                        btn_ghost("Cancelar", on_click=dlg.close)

                        def _guardar_piar() -> None:
                            try:
                                dto = NuevoPIARDTO(
                                    estudiante_id=est_id,
                                    anio_id=anio_id,
                                    descripcion_necesidad=descripcion_ta.value,
                                    ajustes_evaluativos=ajustes_eval_ta.value or None,
                                    ajustes_pedagogicos=ajustes_ped_ta.value or None,
                                    profesionales_apoyo=profesionales_inp.value or None,
                                )
                                Container.estudiante_service().registrar_piar(
                                    dto, usuario_id=ctx.usuario_id
                                )
                                ui.notify("PIAR registrado exitosamente.", type="positive")
                                dlg.close()
                                # Recargar para actualizar badge posee_piar
                                _cargar_estudiantes()
                                tabla_refreshable.refresh()
                            except ValueError as exc:
                                ui.notify(str(exc), type="warning")
                            except Exception as exc:
                                logger.error(
                                    "Error registrando PIAR est=%s: %s", est_id, exc
                                )
                                ui.notify("Error inesperado al registrar el PIAR.", type="negative")

                        btn_primary("Registrar PIAR", on_click=_guardar_piar)

            dlg.open()

        # ── Renderizado de la página ──────────────────────────────────────────

        with ui.element("div").classes("page-stack"):

            page_header(
                titulo    = "Gestión de Estudiantes",
                subtitulo = "Matrícula, estado y PIAR de estudiantes",
                icono     = Icons.STUDENTS,
                acciones  = [
                    {"label": "Matricular",  "on_click": _abrir_dialog_matricula, "icono": "person_add",  "variante": "primary"},
                    {"label": "Carga CSV",   "on_click": _abrir_dialog_csv,       "icono": "upload_file", "variante": "secondary"},
                ],
            )

            # ── 1. Panel de filtros ───────────────────────────────────────────
            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("panel-header"):
                    ThemeManager.icono("filter_list", size=20)
                    ui.label("Filtros").classes("panel-title")

                with ui.row().classes("w-full q-col-gutter-md items-end"):

                    _grupos_opts: dict = {None: "Todos los grupos"}
                    for g in _s["grupos"]:
                        _grupos_opts[g.id] = g.codigo

                    grupo_filtro = ui.select(
                        label="Grupo",
                        options=_grupos_opts,
                        value=None,
                        on_change=lambda e: _s.update({"filtro_grupo_id": e.value}),
                    ).classes("col-3")

                    estado_filtro = ui.select(
                        label="Estado",
                        options={
                            None: "Todos",
                            "activo": "Activo",
                            "inactivo": "Inactivo",
                            "retirado": "Retirado",
                            "graduado": "Graduado",
                        },
                        value=None,
                        on_change=lambda e: _s.update({"filtro_estado": e.value}),
                    ).classes("col-3")

                    piar_filtro = ui.checkbox(
                        "Solo con PIAR",
                        on_change=lambda e: _s.update(
                            {"filtro_piar": True if e.value else None}
                        ),
                    )

                    busqueda_inp = ui.input(
                        label="Buscar (nombre / documento)",
                        on_change=lambda e: _s.update({"filtro_busqueda": e.value}),
                    ).classes("col-4")

                    def _aplicar_filtros() -> None:
                        _cargar_estudiantes()
                        tabla_refreshable.refresh()

                    btn_primary(
                        "Buscar",
                        icon=Icons.SEARCH,
                        on_click=_aplicar_filtros,
                    )

            # ── 3. Tabla de estudiantes ───────────────────────────────────────
            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("panel-header"):
                    ThemeManager.icono(Icons.STUDENTS, size=20)
                    with ui.element("div"):
                        ui.label("Estudiantes").classes("panel-title")
                        ui.label(
                            f"{len(_s['estudiantes'])} resultado(s)"
                        ).classes("tablero-panel-subtitle")

                tabla_refreshable()

            # ── 4. Sección resultado masivo ───────────────────────────────────
            resultado_refreshable()

    # ── Layout principal ──────────────────────────────────────────────────────
    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        titulo_pagina="Estudiantes",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/estudiantes",
        contenido=contenido,
        ctx=ctx,
        on_context_change=on_context_change,
    )


__all__ = ["estudiantes_page"]
