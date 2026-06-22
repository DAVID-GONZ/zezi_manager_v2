"""
src/interface/pages/academico/estudiantes.py
=============================================
Página de gestión de estudiantes y PIAR — ZECI Manager v2.0
Ruta: /estudiantes

Secciones:
  1. Panel de filtros (grupo, estado, PIAR, búsqueda)
  2. Botones de acción (Matricular, Carga CSV, Plantilla CSV) en cabecera del panel
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

Nota técnica — botones de tabla:
  NiceGUI crea un componente Vue anónimo por cada slot template. Usar
  $emit() dentro de ese componente emite DESDE ÉL, no desde la tabla,
  por lo que tabla.on() nunca lo recibe. La solución es emitir explícitamente
  desde el componente NiceGUI correcto usando getElement(tabla.id).$emit().
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
    btn_primary, btn_secondary, btn_ghost, btn_icon,
)
from src.interface.design.components import confirm_dialog, empty_state, form_dialog, stat_card, status_badge, toast_error, toast_success, toast_warning
from src.services.estudiante_service import (
    NuevoEstudianteDTO,
    ActualizarEstudianteDTO,
    FiltroEstudiantesDTO,
    NuevoPIARDTO,
    ActualizarPIARDTO,
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

# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
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
            _s["estudiantes"] = Container.estudiante_service().listar_resumenes_plano(filtro)
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

    # ── Generador de plantilla CSV descargable ───────────────────────────────

    def _descargar_plantilla_csv() -> None:
        """Genera y descarga un CSV de ejemplo con el formato correcto."""
        cabeceras = [
            "tipo_documento", "numero_documento", "nombre",
            "apellido", "genero", "grupo_codigo",
        ]
        ejemplos = [
            ["TI", "1020304050", "Maria Fernanda", "Lopez Torres", "F", "A1"],
            ["TI", "1020304051", "Carlos Andres",  "Ramirez Ruiz",  "M", "A2"],
            ["CC", "98765432",   "Ana Lucia",      "Gomez Prada",  "F", ""],
        ]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(cabeceras)
        writer.writerows(ejemplos)
        csv_bytes = buf.getvalue().encode("utf-8-sig")   # BOM para Excel
        ui.download(csv_bytes, "plantilla_estudiantes.csv")

    # ── Procesador CSV ────────────────────────────────────────────────────────

    def _procesar_csv(content: bytes) -> None:
        try:
            texto = content.decode("utf-8")
        except UnicodeDecodeError:
            texto = content.decode("latin-1")

        filas = list(csv.DictReader(io.StringIO(texto)))
        mapa_grupos: dict[str, int] = {g.codigo: g.id for g in _s["grupos"]}

        resultado = Container.estudiante_service().matricular_masivo_csv(
            filas=filas,
            mapa_grupos=mapa_grupos,
            usuario_id=ctx.usuario_id,
        )

        _s["resultado_masivo"] = resultado
        _cargar_estudiantes()
        tabla_refreshable.refresh()
        resultado_refreshable.refresh()

        if resultado.fue_exitosa:
            toast_success(f"Carga completada: {resultado.exitosas} estudiantes matriculados.")
        else:
            toast_warning(f"{resultado.exitosas} exitosas, {resultado.fallidas} fallidas. " "Revisa la sección de resultados.")

    # =========================================================================
    # CONSTRUCCIÓN DE LA UI
    # =========================================================================

    def contenido() -> None:

        # ── Refreshables ──────────────────────────────────────────────────────

        @ui.refreshable
        def tabla_refreshable() -> None:
            """
            Lista de estudiantes renderizada en Python puro.

            Se abandonó ui.table + slots + $emit porque NiceGUI crea un
            componente Vue anónimo por cada slot template y ningún mecanismo
            de $emit desde ese contexto llega al handler Python registrado
            con tabla.on(). En su lugar se renderiza una tabla HTML con
            ui.element + bucle Python, lo que permite usar ui.button con
            on_click directo — sin ningún puente JavaScript.
            """
            estudiantes = _s["estudiantes"]

            if not estudiantes:
                empty_state(
                    icono=Icons.STUDENTS,
                    titulo="Sin estudiantes",
                    descripcion="No hay estudiantes con los filtros seleccionados.",
                    cta_label="Limpiar filtros",
                    cta_on_click=lambda: ui.navigate.reload(),
                )
                return

            # ── Cabecera de la tabla ──────────────────────────────────────────
            with ui.element("div").classes("est-table w-full overflow-auto"):
                with ui.element("table").classes("w-full est-table__table"):

                    # thead
                    with ui.element("thead"):
                        with ui.element("tr").classes("est-table__head-row"):
                            for label, extra in [
                                ("Estudiante",  "est-table__th--left est-table__th--wide"),
                                ("Documento",   "est-table__th--left"),
                                ("Grupo",       "est-table__th--center"),
                                ("Estado",      "est-table__th--center"),
                                ("PIAR",        "est-table__th--center"),
                                ("Acciones",    "est-table__th--center"),
                            ]:
                                with ui.element("th").classes(f"est-table__th {extra}"):
                                    ui.label(label)

                    # tbody — una fila por estudiante
                    # estudiantes es list[dict] (primitivos puros, sin enums)
                    with ui.element("tbody"):
                        for est in estudiantes:
                            estado_raw = est["estado_matricula"]   # str plano del servicio
                            fila = {
                                "id":               est["id"],
                                "nombre_completo":  est["nombre_completo"],
                                "documento_display": est["documento_display"],
                                "grupo_codigo":     _grupo_codigo(est["grupo_id"]),
                                "estado_str":       _estado_label(estado_raw),
                                "estado_raw":       estado_raw,
                                "posee_piar":       est["posee_piar"],
                            }

                            # Captura de la fila en la closure — crítico en bucles
                            def _fila_editar(_, f=fila):
                                _abrir_dialog_edicion(f)

                            def _fila_retirar(_, f=fila):
                                _confirmar_retiro(f)

                            def _fila_piar(_, f=fila):
                                _abrir_dialog_piar(f)

                            with ui.element("tr").classes("est-table__row"):

                                # Nombre
                                with ui.element("td").classes("est-table__td est-table__td--left"):
                                    ui.label(fila["nombre_completo"]).classes("est-table__nombre")

                                # Documento
                                with ui.element("td").classes("est-table__td est-table__td--left"):
                                    ui.label(fila["documento_display"]).classes("est-table__doc")

                                # Grupo
                                with ui.element("td").classes("est-table__td est-table__td--center"):
                                    ui.label(fila["grupo_codigo"]).classes("est-table__grupo")

                                # Estado
                                with ui.element("td").classes("est-table__td est-table__td--center"):
                                    _variante = {
                                        "activo":   "success",
                                        "inactivo": "neutral",
                                        "retirado": "error",
                                        "graduado": "info",
                                    }.get(fila["estado_raw"], "neutral")
                                    status_badge(fila["estado_str"], variante=_variante)

                                # PIAR
                                with ui.element("td").classes("est-table__td est-table__td--center"):
                                    status_badge(
                                        "Sí" if fila["posee_piar"] else "No",
                                        variante="info" if fila["posee_piar"] else "neutral",
                                    )

                                # Acciones — botones Python reales, sin slots ni $emit
                                with ui.element("td").classes("est-table__td est-table__td--center"):
                                    with ui.row().classes("gap-1 justify-center"):
                                        es_retirado = fila["estado_raw"] == "retirado"

                                        if not es_retirado:
                                            btn_icon("edit", on_click=_fila_editar, tooltip="Editar estudiante", variante="primary")
                                            btn_icon("person_remove", on_click=_fila_retirar, tooltip="Retirar matrícula", variante="danger")
                                            btn_icon("description", on_click=_fila_piar, tooltip="Ver / registrar PIAR", variante="secondary")

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
                    ui.label("Detalle de errores (máx. 10):").classes("text-weight-medium u-mt-md")
                    for err in resultado.errores[:10]:
                        ui.label(
                            f"Fila {err['fila']} — Doc: {err['dato']} — {err['motivo']}"
                        ).classes("text-caption text-error u-mb-xs")

                btn_secondary("Limpiar resultado", icon="close",
                              on_click=lambda: (_s.update({"resultado_masivo": None}),
                                                resultado_refreshable.refresh())).classes("u-mt-sm")

        # ── Acciones de página ────────────────────────────────────────────────

        def _abrir_dialog_matricula() -> None:
            def _guardar(datos: dict) -> "bool | None":
                # NuevoEstudianteDTO valida documento/nombre/apellido (strip, no vacío)
                # y coacciona tipo_documento/genero.
                try:
                    dto = NuevoEstudianteDTO(
                        tipo_documento=datos.get("tipo_documento") or "TI",
                        numero_documento=datos.get("numero_documento", ""),
                        nombre=datos.get("nombre", ""),
                        apellido=datos.get("apellido", ""),
                        grupo_id=datos.get("grupo_id"),
                        genero=datos.get("genero"),
                        posee_piar=datos.get("posee_piar", False),
                    )
                    Container.estudiante_service().matricular(dto, usuario_id=ctx.usuario_id)
                    toast_success("Estudiante matriculado exitosamente.")
                    _cargar_estudiantes()
                    tabla_refreshable.refresh()
                except ValueError as exc:
                    toast_warning(str(exc))
                    return False
                except Exception as exc:
                    logger.error("Error matriculando: %s", exc)
                    toast_error("Error inesperado al matricular.")
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
            with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
                with ui.row().classes("items-center justify-between w-full u-mb-sm"):
                    ui.label("Carga masiva por CSV").classes("text-h6")
                    btn_icon("close", on_click=dlg.close, variante="ghost")

                with ui.element("div").classes("u-mb-md"):
                    ui.label("Columnas requeridas en el archivo:").classes(
                        "text-caption text-weight-medium u-mb-xs"
                    )
                    for col, desc in [
                        ("tipo_documento",   "TI · CC · CE · NUIP"),
                        ("numero_documento", "Identificador único del estudiante"),
                        ("nombre",           "Nombres del estudiante"),
                        ("apellido",         "Apellidos del estudiante"),
                        ("genero",           "M · F · OTRO  (opcional)"),
                        ("grupo_codigo",     "Código del grupo, ej: A1  (opcional)"),
                    ]:
                        with ui.row().classes("u-mb-xs gap-2"):
                            ui.label(col).classes(
                                "text-caption text-weight-bold text-primary csv-col-label"
                            )
                            ui.label(desc).classes("text-caption text-muted")

                    ui.label(
                        "Descarga la plantilla con el botón 'Plantilla' para evitar errores de formato."
                    ).classes("text-caption text-warning u-mt-sm")

                ui.upload(
                    label="Seleccionar archivo CSV",
                    on_upload=lambda e: (_procesar_csv(e.content.read()), dlg.close()),
                    auto_upload=True,
                ).props("accept=.csv").classes("w-full")

                with ui.row().classes("u-mt-md justify-end gap-2"):
                    btn_ghost("Cancelar", on_click=dlg.close)
                    btn_secondary(
                        "Descargar plantilla",
                        icon="download",
                        on_click=_descargar_plantilla_csv,
                    )
            dlg.open()

        def _abrir_dialog_edicion(fila: dict) -> None:
            est_id = fila.get("id")
            if not est_id:
                return
            try:
                # get_para_edicion devuelve dict plano (strings, no enums)
                # — la interfaz no necesita conocer ningún tipo del dominio.
                est = Container.estudiante_service().get_para_edicion(est_id)
            except Exception as exc:
                logger.error("Error cargando estudiante %s: %s", est_id, exc)
                toast_error("No se pudo cargar el estudiante.")
                return

            def _guardar_edicion(datos: dict) -> "bool | None":
                # ActualizarEstudianteDTO valida nombre/apellido y coacciona enums;
                # `or None` conserva la semántica "solo actualiza lo provisto".
                try:
                    dto = ActualizarEstudianteDTO(
                        nombre=datos.get("nombre") or None,
                        apellido=datos.get("apellido") or None,
                        genero=datos.get("genero"),
                        grupo_id=datos.get("grupo_id"),
                        posee_piar=datos.get("posee_piar", False),
                        estado_matricula=datos.get("estado"),
                    )
                    Container.estudiante_service().actualizar(est_id, dto, usuario_id=ctx.usuario_id)
                    toast_success("Estudiante actualizado.")
                    _cargar_estudiantes()
                    tabla_refreshable.refresh()
                except ValueError as exc:
                    toast_warning(str(exc))
                    return False
                except Exception as exc:
                    logger.error("Error actualizando %s: %s", est_id, exc)
                    toast_error("Error inesperado al actualizar.")
                    return False

            form_dialog(
                titulo=f"Editar — {est['nombre_completo']}",
                campos=[
                    {"key": "nombre",     "label": "Nombre",    "tipo": "text",     "valor": est["nombre"],   "requerido": True},
                    {"key": "apellido",   "label": "Apellido",  "tipo": "text",     "valor": est["apellido"], "requerido": True},
                    {"key": "estado",     "label": "Estado",    "tipo": "select",   "valor": est["estado_matricula"],
                     "opciones": {"activo": "Activo", "inactivo": "Inactivo", "retirado": "Retirado", "graduado": "Graduado"}},
                    {"key": "grupo_id",   "label": "Grupo",     "tipo": "select",   "valor": est["grupo_id"], "opciones": _grupos_select()},
                    {"key": "genero",     "label": "Género",    "tipo": "select",   "valor": est["genero"],
                     "opciones": {None: "No especificado", "M": "Masculino", "F": "Femenino", "OTRO": "Otro"}},
                    {"key": "posee_piar", "label": "Posee PIAR","tipo": "checkbox", "valor": est["posee_piar"]},
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
                    toast_success(f"{nombre} retirado.")
                    _cargar_estudiantes()
                    tabla_refreshable.refresh()
                except ValueError as exc:
                    toast_warning(str(exc))
                except Exception as exc:
                    logger.error("Error retirando %s: %s", est_id, exc)
                    toast_error("Error inesperado al retirar.")

            confirm_dialog(
                titulo="Retirar estudiante",
                mensaje=(
                    f"Estás a punto de retirar a {nombre} de la matrícula.\n\n"
                    "Esta acción cambiará el estado a Retirado e impedirá "
                    "registrar asistencia o notas para este estudiante. "
                    "No se puede deshacer desde esta pantalla."
                ),
                on_confirm=_ejecutar,
                variante="danger",
                texto_confirmar="Sí, retirar",
                texto_cancelar="Cancelar",
            )

        def _abrir_dialog_piar(fila: dict) -> None:
            est_id = fila.get("id")
            nombre = fila.get("nombre_completo", "Estudiante")
            if not est_id:
                return

            anio_id = _s["config"].id if _s["config"] else None
            if not anio_id:
                toast_warning("No hay año escolar activo configurado.")
                return

            piar = None
            try:
                piar = Container.estudiante_service().get_piar(est_id, anio_id)
            except Exception as exc:
                logger.error("Error cargando PIAR est=%s anio=%s: %s", est_id, anio_id, exc)

            is_edit = piar is not None

            def _submit_piar(datos: dict) -> "bool | None":
                # La descripción (obligatoria, no vacía) la validan los DTOs de PIAR.
                try:
                    if is_edit:
                        dto = ActualizarPIARDTO(
                            descripcion_necesidad=datos.get("descripcion_necesidad"),
                            ajustes_evaluativos=datos.get("ajustes_evaluativos") or None,
                            ajustes_pedagogicos=datos.get("ajustes_pedagogicos") or None,
                            profesionales_apoyo=datos.get("profesionales_apoyo") or None,
                        )
                        Container.estudiante_service().actualizar_piar(
                            est_id, anio_id, dto, usuario_id=ctx.usuario_id,
                        )
                        toast_success("PIAR actualizado.")
                    else:
                        dto = NuevoPIARDTO(
                            estudiante_id=est_id,
                            anio_id=anio_id,
                            descripcion_necesidad=datos.get("descripcion_necesidad"),
                            ajustes_evaluativos=datos.get("ajustes_evaluativos") or None,
                            ajustes_pedagogicos=datos.get("ajustes_pedagogicos") or None,
                            profesionales_apoyo=datos.get("profesionales_apoyo") or None,
                        )
                        Container.estudiante_service().registrar_piar(dto, usuario_id=ctx.usuario_id)
                        toast_success("PIAR registrado exitosamente.")
                    _cargar_estudiantes()
                    tabla_refreshable.refresh()
                except ValueError as exc:
                    toast_warning(str(exc))
                    return False
                except Exception as exc:
                    logger.error("Error %s PIAR est=%s: %s", "actualizando" if is_edit else "registrando", est_id, exc)
                    toast_error(f"Error inesperado al {'actualizar' if is_edit else 'registrar'} el PIAR.")
                    return False

            form_dialog(
                titulo=f"{'Actualizar' if is_edit else 'Registrar'} PIAR — {nombre}",
                campos=[
                    {
                        "key": "descripcion_necesidad",
                        "label": "Descripción de necesidades",
                        "tipo": "textarea",
                        "requerido": True,
                        "valor": piar.descripcion_necesidad if piar else "",
                        "placeholder": "Describe las necesidades educativas del estudiante...",
                    },
                    {
                        "key": "ajustes_evaluativos",
                        "label": "Ajustes evaluativos",
                        "tipo": "textarea",
                        "valor": (piar.ajustes_evaluativos or "") if piar else "",
                        "placeholder": "Ajustes en la forma de evaluar...",
                    },
                    {
                        "key": "ajustes_pedagogicos",
                        "label": "Ajustes pedagógicos",
                        "tipo": "textarea",
                        "valor": (piar.ajustes_pedagogicos or "") if piar else "",
                        "placeholder": "Estrategias pedagógicas diferenciadas...",
                    },
                    {
                        "key": "profesionales_apoyo",
                        "label": "Profesionales de apoyo",
                        "tipo": "text",
                        "valor": (piar.profesionales_apoyo or "") if piar else "",
                        "placeholder": "Fonoaudióloga, psicóloga, etc.",
                    },
                ],
                on_submit=_submit_piar,
                texto_submit="Actualizar PIAR" if is_edit else "Registrar PIAR",
                max_width="max-w-lg",
            )

        # ── Renderizado de la página ──────────────────────────────────────────

        with ui.element("div").classes("page-stack"):

            # ── 1. Panel de filtros ───────────────────────────────────────────
            with ui.element("div").classes("panel-card"):
                with ui.element("div").classes("panel-header"):
                    ThemeManager.icono("filter_list", size=20)
                    ui.label("Filtros").classes("panel-title")

                with ui.row().classes("w-full u-col-gutter-md items-end"):
                    _grupos_opts: dict = {None: "Todos los grupos"}
                    for g in _s["grupos"]:
                        _grupos_opts[g.id] = g.codigo

                    ui.select(
                        label="Grupo",
                        options=_grupos_opts,
                        value=None,
                        on_change=lambda e: _s.update({"filtro_grupo_id": e.value}),
                    ).classes("flex-3")

                    ui.select(
                        label="Estado",
                        options={None: "Todos", "activo": "Activo", "inactivo": "Inactivo",
                                 "retirado": "Retirado", "graduado": "Graduado"},
                        value=None,
                        on_change=lambda e: _s.update({"filtro_estado": e.value}),
                    ).classes("flex-3")

                    ui.checkbox(
                        "Solo con PIAR",
                        on_change=lambda e: _s.update({"filtro_piar": True if e.value else None}),
                    )

                    ui.input(
                        label="Buscar (nombre / documento)",
                        on_change=lambda e: _s.update({"filtro_busqueda": e.value}),
                    ).classes("flex-4")

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
                        btn_ghost(
                            "Plantilla",
                            icon="download",
                            on_click=_descargar_plantilla_csv,
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
        mostrar_contexto = False,
    )


__all__ = ["estudiantes_page"]
