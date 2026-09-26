"""
src/interface/pages/institucion/auditoria.py
============================================
Bitácora institucional — solo lectura.
Ruta: /institucion/auditoria
Acceso: director y coordinador del colegio (roles=_DIR_COORD).

Muestra los cambios y eventos de sesión de la institución del usuario.
El scope es inmutable: lo fija el constructor del presenter desde
``ctx.institucion_id``. La UI nunca puede ensancharlo (obs_11, R4).

Diferencias frente a /admin/auditoria:
  - Sin filtro de institución (R5).
  - Sin verificación de integridad (R5).
  - Sin opción «Sin institución» (R5).
  - Encabezados de entidad con etiquetas de negocio (R7).
  - Sin exportación (llega en obs_12).

Flujo:
  1. Guard: sesión válida + rol (en main.py vía registrar_pagina).
  2. Si ctx.institucion_id is None → estado vacío explicativo (R12).
  3. Presenter con scope = ctx.institucion_id.
  4. Carga inicial de cambios y sesiones.
  5. Pestañas Cambios / Sesiones con filtros, paginación y detalle.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.domain.tablas_auditables import ETIQUETAS_TABLA
from src.interface.context.session_context import SessionContext
from src.domain.policies.rbac_auditoria import puede_exportar_bitacora
from src.interface.design.components import (
    custom_dialog,
    data_table,
    date_range_input,
    empty_state,
    status_badge,
    toast_error,
    toast_success,
)
from src.interface.design.components.buttons import btn_icon, btn_secondary
from src.interface.design.components.form_fields import filter_input, filter_select
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.presenters.institucion.auditoria_presenter import (
    AuditoriaInstitucionalPresenter,
)
from src.services.auditoria_service import (
    AccionCambio,
    SeveridadEvento,
    TipoEventoSesion,
)

logger = logging.getLogger("INSTITUCION.AUDITORIA")

_ACCIONES_OPCIONES = {a.value: a.value.capitalize() for a in AccionCambio}
_EVENTOS_OPCIONES = {t.value: t.value.replace("_", " ").capitalize() for t in TipoEventoSesion}

_SEVERIDAD_OPCIONES = {
    None: "Todas las severidades",
    SeveridadEvento.INFO.value: "Info",
    SeveridadEvento.ADVERTENCIA.value: "Advertencia",
    SeveridadEvento.CRITICA.value: "Crítica",
}
_SEVERIDAD_VARIANTE: dict[str, str] = {
    SeveridadEvento.INFO.value: "neutral",
    SeveridadEvento.ADVERTENCIA.value: "warning",
    SeveridadEvento.CRITICA.value: "error",
}

# Opciones de entidad con vocabulario de negocio (R7, T8) — sin nombres de tabla física
_TABLA_OPCIONES: dict = {None: "Todas las entidades"}
_TABLA_OPCIONES.update(sorted(ETIQUETAS_TABLA.items(), key=lambda kv: kv[1]))

# Mapa tipo-cambio → (variante badge, etiqueta legible)
_DIFF_TIPO_VARIANTE: dict[str, tuple[str, str]] = {
    "ANADIDO": ("success", "Añadido"),
    "MODIFICADO": ("info", "Modificado"),
    "ELIMINADO": ("error", "Eliminado"),
    "SIN_CAMBIO": ("neutral", "Sin cambio"),
}

_POR_PAGINA = 50


def _render_sin_tenant(ctx) -> None:
    """Estado vacío explicativo cuando la sesión no tiene institución (R12)."""
    def _contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                empty_state(
                    variante="default",
                    icono="domain_disabled",
                    titulo="Sin institución asignada",
                    descripcion=(
                        "Tu cuenta no tiene una institución asociada. "
                        "Contacta al administrador del sistema para poder "
                        "ver la bitácora de tu colegio."
                    ),
                )

    app_layout(
        ctx,
        _contenido,
        page_titulo="Auditoría institucional",
        page_subtitulo="Bitácora de cambios y sesiones",
        page_icono="history",
    )


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def auditoria_institucional_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    # R12: sin tenant, sin bitácora
    if ctx.institucion_id is None:
        _render_sin_tenant(ctx)
        return

    logger.info(
        "Bitácora institucional: %s (%s) inst=%s",
        ctx.usuario_nombre, ctx.usuario_rol, ctx.institucion_id,
    )

    presenter = AuditoriaInstitucionalPresenter(ctx.institucion_id)
    _s = presenter.estado

    _dlg_holder: list = []

    # ── Carga de datos ────────────────────────────────────────────────────────

    def _cargar_cambios() -> None:
        try:
            svc = Container.auditoria_service()
            filtro = presenter.construir_filtro(_POR_PAGINA + 1)
            raw = list(svc.listar_cambios(filtro, scope=presenter.scope))
            _s["hay_siguiente_cambios"] = len(raw) > _POR_PAGINA
            cambios_pagina = raw[:_POR_PAGINA]
            presenter.set_cambios(cambios_pagina)
            try:
                presenter.set_actores(svc.resolver_actores(cambios_pagina))
            except Exception:
                presenter.set_actores({})
            try:
                presenter.set_total_cambios(
                    svc.contar_cambios(presenter.construir_filtro(_POR_PAGINA))
                )
            except Exception:
                presenter.set_total_cambios(0)
        except Exception as exc:
            logger.error("Error al cargar cambios de bitácora institucional: %s", exc)
            presenter.set_cambios([])
            presenter.set_actores({})
            _s["hay_siguiente_cambios"] = False
            presenter.set_total_cambios(0)

    def _cargar_sesiones() -> None:
        try:
            svc = Container.auditoria_service()
            filtro = presenter.construir_filtro(_POR_PAGINA + 1)
            raw = list(svc.listar_eventos_sesion(filtro, scope=presenter.scope))
            _s["hay_siguiente_sesiones"] = len(raw) > _POR_PAGINA
            presenter.set_sesiones(raw[:_POR_PAGINA])
            try:
                presenter.set_total_sesiones(
                    svc.contar_eventos(presenter.construir_filtro(_POR_PAGINA))
                )
            except Exception:
                presenter.set_total_sesiones(0)
        except Exception as exc:
            logger.error("Error al cargar sesiones de bitácora institucional: %s", exc)
            presenter.set_sesiones([])
            _s["hay_siguiente_sesiones"] = False
            presenter.set_total_sesiones(0)

    def _cargar_todo() -> None:
        _cargar_cambios()
        _cargar_sesiones()

    _cargar_todo()

    # ── Diálogo de detalle de cambio ─────────────────────────────────────────

    @ui.refreshable
    def _cuerpo_detalle() -> None:
        dto = _s.get("detalle")
        if dto is None:
            return
        cambio = dto.cambio

        with ui.row().classes("form-row-between u-mb-sm"):
            with ui.column().classes("u-stack-xs"):
                ui.label(dto.actor_nombre).classes("form-dialog-title")
                ui.label(dto.etiqueta_tabla).classes("text-sm text-secondary")
            if _dlg_holder:
                btn_icon("close", on_click=_dlg_holder[0].close, tooltip="Cerrar")

        ts = getattr(cambio, "timestamp_display", None) or "—"
        accion_str = cambio.accion.value if hasattr(cambio.accion, "value") else str(cambio.accion)
        with ui.row().classes("form-row-inline u-mb-sm"):
            ui.label(ts).classes("text-sm text-secondary")
            status_badge(accion_str, variante="neutral")
            reg_id = cambio.registro_id
            ui.label(
                f"Registro #{reg_id}" if reg_id is not None else "—"
            ).classes("text-sm text-secondary")

        if dto.campos:
            ui.label("Campos modificados").classes("text-sm font-semibold u-mb-sm")
            with ui.row().classes("form-row-inline u-mb-sm"):
                ui.label("Campo").classes("text-xs font-semibold text-secondary").style("min-width:130px")
                ui.label("Antes").classes("text-xs font-semibold text-secondary flex-1")
                ui.label("Después").classes("text-xs font-semibold text-secondary flex-1")
                ui.label("Tipo").classes("text-xs font-semibold text-secondary").style("min-width:100px")

            for campo in dto.campos:
                tipo_str = campo.tipo.value if hasattr(campo.tipo, "value") else str(campo.tipo)
                variante, etiqueta_tipo = _DIFF_TIPO_VARIANTE.get(tipo_str, ("neutral", tipo_str.lower()))
                valor_ant = "•••" if campo.oculto else (campo.valor_anterior or "—")
                valor_nue = "•••" if campo.oculto else (campo.valor_nuevo or "—")
                with ui.row().classes("form-row-inline items-start py-1"):
                    ui.label(campo.nombre).classes("text-sm font-mono").style(
                        "min-width:130px;word-break:break-all"
                    )
                    ui.label(valor_ant).classes("text-sm text-secondary flex-1").style(
                        "word-break:break-all"
                    )
                    ui.label(valor_nue).classes("text-sm flex-1").style("word-break:break-all")
                    ui.label(etiqueta_tipo).classes(f"badge badge-{variante}")
        else:
            empty_state(
                variante="default",
                icono="compare",
                titulo="Sin datos de diff",
                descripcion="No hay detalle de campos para este registro.",
            )

        with ui.row().classes("form-dialog-actions"):
            btn_secondary(
                "Cerrar",
                on_click=_dlg_holder[0].close if _dlg_holder else lambda: None,
            )

    def _abrir_detalle_row(fila: dict) -> None:
        cambio_id = fila.get("id")
        if not cambio_id:
            return
        try:
            dto = Container.auditoria_service().detalle_cambio(int(cambio_id))
        except Exception as exc:
            logger.error("Error al cargar detalle de cambio %s: %s", cambio_id, exc)
            toast_error("No se pudo cargar el detalle")
            return
        presenter.abrir_detalle(dto)
        _cuerpo_detalle.refresh()
        if _dlg_holder:
            _dlg_holder[0].open()

    # ── Exportación (obs_12, R1, T16) ────────────────────────────────────────

    def _exportar(formato: str) -> None:
        """Exporta el filtro activo al formato indicado, respetando el scope institucional."""
        if not puede_exportar_bitacora(ctx.usuario_rol):
            toast_error("No tienes permiso para exportar la bitácora.")
            return
        try:
            svc = Container.auditoria_export_service()
            filtro = presenter.construir_filtro(50_000)
            scope = presenter.scope  # scope institucional fijado por el presenter
            # Obtener nombre de la institución para la hoja de verificación
            inst_nombre: str | None = None
            try:
                inst = Container.institucion_service().get_by_id(ctx.institucion_id)
                if inst:
                    inst_nombre = inst.nombre
            except Exception:
                pass
            datos = svc.exportar(
                tabla="audit_log",
                filtro=filtro,
                scope=scope,
                formato=formato,
                actor=ctx.usuario_nombre or str(ctx.usuario_id or "director"),
                actor_id=ctx.usuario_id,
                institucion_nombre=inst_nombre,
            )
            ext = "csv" if formato == "csv" else "pdf"
            nombre = f"bitacora_institucional.{ext}"
            ui.download(datos, filename=nombre)
            toast_success(f"Exportación {formato.upper()} generada.")
        except Exception as exc:
            codigo = getattr(exc, "codigo", None)
            if str(codigo) == "AUDITORIA_EXPORT_TOPE":
                toast_error(str(exc))
            else:
                logger.error("Error al exportar bitácora institucional: %s", exc)
                toast_error("Error al generar la exportación.")

    # ── Handlers de filtros y paginación ─────────────────────────────────────

    def _on_filtros_cambio() -> None:
        presenter.reset_pagina()
        _cargar_todo()
        tabla_cambios.refresh()
        tabla_sesiones.refresh()

    def _ir_pagina(nueva: int, tab: str) -> None:
        presenter.set_pagina(max(1, nueva))
        if tab == "cambios":
            _cargar_cambios()
            tabla_cambios.refresh()
        else:
            _cargar_sesiones()
            tabla_sesiones.refresh()

    # ── Tablas (refreshable, solo lectura) ───────────────────────────────────

    @ui.refreshable
    def tabla_cambios() -> None:
        cambios = _s["cambios"]
        pagina = _s["pagina"]
        hay_sig = _s["hay_siguiente_cambios"]
        total_cambios = _s.get("total_cambios", 0)

        if not cambios:
            empty_state(
                variante="search",
                icono="history",
                titulo="No hay cambios registrados",
                descripcion="Ajusta el rango de fechas, la entidad o la acción para ver más resultados.",
            )
        else:
            columnas = [
                {"name": "timestamp", "label": "Fecha y hora", "field": "timestamp", "sortable": True},
                {"name": "accion", "label": "Acción", "field": "accion", "sortable": True},
                # R7: etiqueta de negocio, no nombre de tabla física
                {"name": "entidad", "label": "Entidad", "field": "entidad", "sortable": True},
                {"name": "registro", "label": "Registro", "field": "registro"},
                {"name": "actor", "label": "Actor", "field": "actor"},
            ]
            filas = [
                {
                    "id": c.id,
                    "timestamp": c.timestamp_display,
                    "accion": c.accion.value if hasattr(c.accion, "value") else str(c.accion),
                    "entidad": ETIQUETAS_TABLA.get(c.tabla, c.tabla),  # R7
                    "registro": c.registro_id if c.registro_id is not None else "—",
                    "actor": presenter.nombre_actor(c),
                }
                for c in cambios
            ]
            data_table(
                columnas,
                filas,
                titulo="Cambios registrados",
                filas_por_pagina=15,
                on_row_click=_abrir_detalle_row,
            )

        if pagina > 1 or hay_sig:
            with ui.row().classes("form-row-center u-mt-md"):
                btn_secondary(
                    "Anterior",
                    on_click=lambda: _ir_pagina(pagina - 1, "cambios"),
                    icon="chevron_left",
                    size="sm",
                ).set_enabled(pagina > 1)
                ui.label(f"Página {pagina}").classes("text-sm self-center px-2")
                if total_cambios > 0:
                    ui.label(f"{total_cambios} resultados").classes(
                        "text-sm text-secondary self-center px-2"
                    )
                btn_secondary(
                    "Siguiente",
                    on_click=lambda: _ir_pagina(pagina + 1, "cambios"),
                    icon="chevron_right",
                    size="sm",
                ).set_enabled(hay_sig)

    @ui.refreshable
    def tabla_sesiones() -> None:
        sesiones = _s["sesiones"]
        pagina = _s["pagina"]
        hay_sig = _s["hay_siguiente_sesiones"]
        total_sesiones = _s.get("total_sesiones", 0)

        if not sesiones:
            empty_state(
                variante="search",
                icono="history",
                titulo="No hay eventos de sesión",
                descripcion="Ajusta el rango de fechas, el usuario o el tipo de evento para ver más resultados.",
            )
        else:
            columnas = [
                {"name": "fecha", "label": "Fecha y hora", "field": "fecha", "sortable": True},
                {"name": "tipo_evento", "label": "Tipo", "field": "tipo_evento", "sortable": True},
                {"name": "usuario", "label": "Usuario", "field": "usuario", "sortable": True},
                {"name": "ip", "label": "IP", "field": "ip"},
                {"name": "detalles", "label": "Detalles", "field": "detalles"},
                {"name": "severidad", "label": "Severidad", "field": "severidad", "sortable": True},
            ]
            filas = [
                {
                    "fecha": e.fecha_display,
                    "tipo_evento": e.tipo_evento.value
                    if hasattr(e.tipo_evento, "value")
                    else str(e.tipo_evento),
                    "usuario": e.usuario,
                    "ip": e.ip_address or "—",
                    "detalles": e.detalles or "—",
                    "severidad": e.severidad.value if hasattr(e.severidad, "value") else str(e.severidad or ""),
                    "sev_variante": _SEVERIDAD_VARIANTE.get(
                        e.severidad.value if hasattr(e.severidad, "value") else "", "neutral"
                    ),
                }
                for e in sesiones
            ]
            tbl = data_table(columnas, filas, titulo="Eventos de sesión", filas_por_pagina=15)
            tbl.add_slot("body-cell-severidad", r"""
<q-td :props="props">
    <span :class="`badge badge-${props.row.sev_variante}`">{{ props.row.severidad }}</span>
</q-td>
""")

        if pagina > 1 or hay_sig:
            with ui.row().classes("form-row-center u-mt-md"):
                btn_secondary(
                    "Anterior",
                    on_click=lambda: _ir_pagina(pagina - 1, "sesiones"),
                    icon="chevron_left",
                    size="sm",
                ).set_enabled(pagina > 1)
                ui.label(f"Página {pagina}").classes("text-sm self-center px-2")
                if total_sesiones > 0:
                    ui.label(f"{total_sesiones} resultados").classes(
                        "text-sm text-secondary self-center px-2"
                    )
                btn_secondary(
                    "Siguiente",
                    on_click=lambda: _ir_pagina(pagina + 1, "sesiones"),
                    icon="chevron_right",
                    size="sm",
                ).set_enabled(hay_sig)

    # ── Filtros comunes ───────────────────────────────────────────────────────

    def _on_rango_cambio(desde: str | None, hasta: str | None) -> None:
        presenter.set_rango(desde, hasta)
        _on_filtros_cambio()

    def _render_filtros_comunes() -> None:
        with ui.row().classes("form-row-inline u-mb-lg"):
            date_range_input(
                desde=_s["desde"],
                hasta=_s["hasta"],
                on_change=_on_rango_cambio,
            )
            filter_input(
                label="ID de usuario",
                placeholder="Opcional",
                on_change=lambda e: (
                    presenter.set_usuario(e.value),
                    _on_filtros_cambio(),
                ),
                cls_extra="w-32",
            )
            btn_icon("refresh", on_click=_on_filtros_cambio, tooltip="Recargar")

    # ── Contenido principal ───────────────────────────────────────────────────

    def contenido() -> None:
        with ui.element("div").classes("page-stack"), ui.element("div").classes("panel-card"):
            with ui.row().classes("form-row-center u-mb-sm"):
                ThemeManager.icono("history", size=22, color="var(--color-primary)")
                ui.label("Bitácora institucional").classes("text-xl font-bold")
                ui.label("Solo lectura").classes("text-sm text-secondary ml-2")
                # obs_12 T16: botones de exportación (R1) — solo exportar, sin purga
                if puede_exportar_bitacora(ctx.usuario_rol):
                    with ui.row().classes("form-row-center ml-auto"):
                        with ui.button_group():
                            btn_secondary(
                                "CSV",
                                on_click=lambda: _exportar("csv"),
                                icon="download",
                                size="sm",
                            )
                            btn_secondary(
                                "PDF",
                                on_click=lambda: _exportar("pdf"),
                                icon="picture_as_pdf",
                                size="sm",
                            )

            _render_filtros_comunes()

            with ui.tabs().classes("w-full") as tabs:
                ui.tab("cambios", label="Cambios", icon="edit_note")
                ui.tab("sesiones", label="Sesiones", icon="login")

            with ui.tab_panels(tabs, value="cambios").classes("w-full mt-0"):
                with ui.tab_panel("cambios"):
                    with ui.row().classes("form-row-center-md u-mb-lg"):
                        ui.label("Filtros:").classes("text-sm font-semibold")
                        # R7: selector con etiquetas de negocio (T8)
                        filter_select(
                            label="Entidad",
                            options=_TABLA_OPCIONES,
                            value=None,
                            on_change=lambda e: (
                                presenter.set_tabla(e.value),
                                _on_filtros_cambio(),
                            ),
                            cls_extra="w-52",
                        )
                        accion_opts = {None: "Todas las acciones"}
                        accion_opts.update(_ACCIONES_OPCIONES)
                        filter_select(
                            label="Acción",
                            options=accion_opts,
                            value=None,
                            on_change=lambda e: (
                                presenter.set_accion(e.value),
                                _on_filtros_cambio(),
                            ),
                            cls_extra="w-40",
                        )
                        filter_input(
                            label="ID registro",
                            placeholder="Opcional",
                            on_change=lambda e: (
                                presenter.set_registro(e.value),
                                _on_filtros_cambio(),
                            ),
                            cls_extra="w-32",
                        )
                    tabla_cambios()

                with ui.tab_panel("sesiones"):
                    with ui.row().classes("form-row-center-md u-mb-lg"):
                        ui.label("Filtros:").classes("text-sm font-semibold")
                        evento_opts = {None: "Todos los eventos"}
                        evento_opts.update(_EVENTOS_OPCIONES)
                        filter_select(
                            label="Tipo de evento",
                            options=evento_opts,
                            value=None,
                            on_change=lambda e: (
                                presenter.set_tipo_evento(e.value),
                                _on_filtros_cambio(),
                            ),
                            cls_extra="w-48",
                        )
                        filter_select(
                            label="Severidad",
                            options=_SEVERIDAD_OPCIONES,
                            value=None,
                            on_change=lambda e: (
                                presenter.set_severidad(e.value),
                                _on_filtros_cambio(),
                            ),
                            cls_extra="w-40",
                        )
                    tabla_sesiones()

    def _crear_dialogo_detalle() -> None:
        with custom_dialog(max_width="lg", persistent=False) as dlg:
            _dlg_holder.append(dlg)
            _cuerpo_detalle()

    _crear_dialogo_detalle()

    app_layout(
        ctx,
        contenido,
        page_titulo="Auditoría institucional",
        page_subtitulo="Bitácora de cambios y sesiones (solo lectura)",
        page_icono="history",
    )


__all__ = ["auditoria_institucional_page"]
