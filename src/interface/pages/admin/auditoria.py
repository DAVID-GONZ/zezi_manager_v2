"""
src/interface/pages/admin/auditoria.py
=======================================
Vista de auditoría (solo lectura).
Ruta: /admin/auditoria
Acceso: admin (rol de plataforma — auditor de lectura global).

Dos secciones:
 - Cambios:  operaciones CRUD del audit_log (tabla, acción, timestamp).
 - Sesiones: eventos de autenticación/acceso (login, logout, accesos denegados).

Solo lectura: no expone acciones de escritura. La escritura de auditoría
la realizan otros servicios vía IAuditoriaRepository.

obs_09: tabla dropdown, filtro registro_id, opción «Sin institución»,
columna actor con cascada de fallback (R9), diálogo de detalle con diff (T12/T13).
"""

from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.domain.tablas_auditables import ETIQUETAS_TABLA
from src.interface.context.session_context import SessionContext
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
from src.interface.presenters.admin.auditoria_presenter import (
    AuditoriaPresenter,
    _SIN_INSTITUCION_SENTINEL,
)
from src.services.auditoria_service import (
    AccionCambio,
    SeveridadEvento,
    TipoEventoSesion,
)

logger = logging.getLogger("ADMIN.AUDITORIA")

_ACCIONES_OPCIONES = {a.value: a.value.capitalize() for a in AccionCambio}
_EVENTOS_OPCIONES = {t.value: t.value.replace("_", " ").capitalize() for t in TipoEventoSesion}

# obs_07 T12: opciones y mapa de variante de badge para severidad
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

# obs_09 T12: opciones para el selector de tabla (dropdown en lugar de input libre)
_TABLA_OPCIONES: dict = {None: "Todas las tablas"}
_TABLA_OPCIONES.update(sorted(ETIQUETAS_TABLA.items(), key=lambda kv: kv[1]))

# obs_09 T13: mapa tipo-cambio → (variante badge, etiqueta legible)
_DIFF_TIPO_VARIANTE: dict[str, tuple[str, str]] = {
    "ANADIDO": ("success", "Añadido"),
    "MODIFICADO": ("info", "Modificado"),
    "ELIMINADO": ("error", "Eliminado"),
    "SIN_CAMBIO": ("neutral", "Sin cambio"),
}

_POR_PAGINA = 50  # MODIFICADO: reducido de 100 a 50 (R5)


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def auditoria_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Auditoría: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    _periodo_desde: str | None = None
    _periodo_hasta: str | None = None
    try:
        _cfg = Container.configuracion_service().get_activa()
        if _cfg.fecha_inicio_clases:
            _periodo_desde = _cfg.fecha_inicio_clases.isoformat()
        if _cfg.fecha_fin_clases:
            _periodo_hasta = _cfg.fecha_fin_clases.isoformat()
    except Exception as exc:
        logger.warning("No se pudo obtener el periodo activo: %s", exc)

    presenter = AuditoriaPresenter()
    _s = presenter.estado

    # obs_09 T13: referencia al diálogo de detalle (capturada al construir la UI)
    _dlg_holder: list = []

    # ── Carga de datos con look-ahead (R3) + conteos (R11 obs_08) ─────────────
    def _cargar_cambios() -> None:
        try:
            svc = Container.auditoria_service()
            filtro = presenter.construir_filtro(_POR_PAGINA + 1)
            raw = list(svc.listar_cambios(filtro))
            presenter.estado["hay_siguiente_cambios"] = len(raw) > _POR_PAGINA
            cambios_pagina = raw[:_POR_PAGINA]
            presenter.set_cambios(cambios_pagina)
            # obs_09 T12: resolver actores de la página (R8 — una sola consulta)
            try:
                presenter.set_actores(svc.resolver_actores(cambios_pagina))
            except Exception:
                presenter.set_actores({})
            # obs_08 R11: contar sin techo de paginación
            try:
                presenter.set_total_cambios(
                    svc.contar_cambios(presenter.construir_filtro(_POR_PAGINA))
                )
            except Exception:
                presenter.set_total_cambios(0)
        except Exception as exc:
            logger.error("Error al cargar cambios de auditoría: %s", exc)
            presenter.set_cambios([])
            presenter.set_actores({})
            presenter.estado["hay_siguiente_cambios"] = False
            presenter.set_total_cambios(0)

    def _cargar_sesiones() -> None:
        try:
            svc = Container.auditoria_service()
            filtro = presenter.construir_filtro(_POR_PAGINA + 1)
            raw = list(svc.listar_eventos_sesion(filtro))
            presenter.estado["hay_siguiente_sesiones"] = len(raw) > _POR_PAGINA
            presenter.set_sesiones(raw[:_POR_PAGINA])
            # obs_08 R11: contar sin techo de paginación
            try:
                presenter.set_total_sesiones(
                    svc.contar_eventos(presenter.construir_filtro(_POR_PAGINA))
                )
            except Exception:
                presenter.set_total_sesiones(0)
        except Exception as exc:
            logger.error("Error al cargar eventos de sesión: %s", exc)
            presenter.set_sesiones([])
            presenter.estado["hay_siguiente_sesiones"] = False
            presenter.set_total_sesiones(0)

    def _cargar_todo() -> None:
        _cargar_cambios()
        _cargar_sesiones()

    _cargar_todo()

    # obs_09 T13: diálogo de detalle de un cambio ────────────────────────────

    @ui.refreshable
    def _cuerpo_detalle() -> None:
        """Cuerpo del diálogo de detalle (solo lectura, R7)."""
        dto = _s.get("detalle")
        if dto is None:
            return
        cambio = dto.cambio

        # Encabezado: actor + tabla
        with ui.row().classes("form-row-between u-mb-sm"):
            with ui.column().classes("u-stack-xs"):
                ui.label(dto.actor_nombre).classes("form-dialog-title")
                ui.label(dto.etiqueta_tabla).classes("text-sm text-secondary")
            if _dlg_holder:
                btn_icon("close", on_click=_dlg_holder[0].close, tooltip="Cerrar")

        # Metadatos: fecha, acción, registro, IP, institución
        ts = getattr(cambio, "timestamp_display", None) or "—"
        accion_str = cambio.accion.value if hasattr(cambio.accion, "value") else str(cambio.accion)
        with ui.row().classes("form-row-inline u-mb-sm"):
            ui.label(ts).classes("text-sm text-secondary")
            status_badge(accion_str, variante="neutral")
            reg_id = cambio.registro_id
            ui.label(f"Registro #{reg_id}" if reg_id is not None else "—").classes("text-sm text-secondary")

        with ui.row().classes("form-row-inline u-mb-md"):
            ip = getattr(cambio, "ip_address", None)
            if ip:
                ui.label(f"IP: {ip}").classes("text-sm text-secondary")
            inst = getattr(cambio, "institucion_id", None)
            if inst is not None:
                ui.label(f"Institución: #{inst}").classes("text-sm text-secondary")

        # Grid de diff
        if dto.campos:
            ui.label("Campos modificados").classes("text-sm font-semibold u-mb-sm")
            # cabecera de columnas
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
                    ui.label(campo.nombre).classes("text-sm font-mono").style("min-width:130px;word-break:break-all")
                    ui.label(valor_ant).classes("text-sm text-secondary flex-1").style("word-break:break-all")
                    ui.label(valor_nue).classes("text-sm flex-1").style("word-break:break-all")
                    ui.label(etiqueta_tipo).classes(f"badge badge-{variante}")
        else:
            empty_state(
                variante="default",
                icono="compare",
                titulo="Sin datos de diff",
                descripcion="No hay detalle de campos para este registro.",
            )

        # Botón de cierre
        with ui.row().classes("form-dialog-actions"):
            btn_secondary(
                "Cerrar",
                on_click=_dlg_holder[0].close if _dlg_holder else lambda: None,
            )

    def _abrir_detalle_row(fila: dict) -> None:
        """obs_09 T13: callback de row-click en la tabla de cambios."""
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

    def _on_filtros_cambio() -> None:
        presenter.reset_pagina()
        _cargar_todo()
        tabla_cambios.refresh()
        tabla_sesiones.refresh()

    # NUEVO: navegación de página por tab (R3)
    def _ir_pagina(nueva: int, tab: str) -> None:
        presenter.set_pagina(max(1, nueva))
        if tab == "cambios":
            _cargar_cambios()
            tabla_cambios.refresh()
        else:
            _cargar_sesiones()
            tabla_sesiones.refresh()

    # ── Integridad de la bitácora (read-only) ──────────────────────────────
    @ui.refreshable
    def badge_integridad() -> None:
        estado = _s["integridad"]
        if estado is None:
            status_badge("Sin verificar", variante="neutral")
            return
        ok = estado["eventos_ok"] and estado["cambios_ok"]
        alcance = estado.get("alcance", "incremental")
        verificado_en = estado.get("verificado_en")
        fecha_str = verificado_en[:16].replace("T", " ") if verificado_en else ""

        if ok:
            # obs_08 R9: distinguir verificación incremental de completa
            if alcance == "completa":
                status_badge("Íntegra (completa)", variante="success")
            else:
                desde_ev = estado.get("desde_id_eventos")
                desde_ch = estado.get("desde_id_cambios")
                if desde_ev is not None or desde_ch is not None:
                    desde_str = f"#{desde_ev or desde_ch}"
                    status_badge(
                        f"Íntegra desde {desde_str} · {fecha_str}",
                        variante="success",
                    )
                else:
                    status_badge(f"Íntegra · {fecha_str}", variante="success")
            return

        rotos = []
        if not estado["eventos_ok"] and estado["evento_roto_id"] is not None:
            rotos.append(f"sesión #{estado['evento_roto_id']}")
        if not estado["cambios_ok"] and estado["cambio_roto_id"] is not None:
            rotos.append(f"cambio #{estado['cambio_roto_id']}")
        detalle = ", ".join(rotos) if rotos else "registro desconocido"
        status_badge(f"Alterada ({detalle})", variante="error")

    def _verificar_integridad(completa: bool = False) -> None:
        try:
            _s["integridad"] = Container.auditoria_service().verificar_integridad(
                completa=completa
            )
        except Exception as exc:
            logger.error("Error al verificar integridad de auditoría: %s", exc)
            _s["integridad"] = None
            toast_error("No se pudo verificar la integridad")
            badge_integridad.refresh()
            return
        badge_integridad.refresh()
        estado = _s["integridad"]
        if estado["eventos_ok"] and estado["cambios_ok"]:
            alcance = estado.get("alcance", "incremental")
            if alcance == "completa":
                toast_success("Bitácora íntegra (verificación completa desde el origen)")
            else:
                toast_success("Bitácora íntegra: la cadena de hashes cuadra")

    # ── Tablas (refreshable, solo lectura) ─────────────────────────────────
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
                descripcion="Ajusta el rango de fechas, la tabla o la acción para ver más resultados.",
            )
        else:
            columnas = [
                {"name": "timestamp", "label": "Fecha y hora", "field": "timestamp", "sortable": True},
                {"name": "accion", "label": "Acción", "field": "accion", "sortable": True},
                # obs_09 T12: etiqueta legible de tabla (R10) en lugar del nombre físico
                {"name": "tabla", "label": "Tabla", "field": "tabla", "sortable": True},
                {"name": "registro", "label": "Registro", "field": "registro"},
                # obs_09 T12: actor con cascada de fallback (R9) en lugar de «Usuario ID»
                {"name": "actor", "label": "Actor", "field": "actor"},
            ]
            filas = [
                {
                    "id": c.id,          # obs_09 T13: necesario para el row-click
                    "timestamp": c.timestamp_display,
                    "accion": c.accion.value if hasattr(c.accion, "value") else str(c.accion),
                    # obs_09 T12: mostrar etiqueta legible de la tabla (R10)
                    "tabla": ETIQUETAS_TABLA.get(c.tabla, c.tabla),
                    "registro": c.registro_id if c.registro_id is not None else "—",
                    # obs_09 T12: nombre del actor con cascada de fallback (R9)
                    "actor": presenter.nombre_actor(c),
                }
                for c in cambios
            ]
            # obs_09 T13: on_row_click abre el diálogo de detalle
            data_table(
                columnas,
                filas,
                titulo="Cambios (audit_log)",
                filas_por_pagina=15,
                on_row_click=_abrir_detalle_row,
            )

        # obs_08 R11: mostrar total de resultados junto a la paginación
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
                    ui.label(f"{total_cambios} resultados").classes("text-sm text-secondary self-center px-2")
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
            # obs_07 T12: columna de severidad con badge
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
            tbl_sesiones = data_table(columnas, filas, titulo="Sesiones (auditoría)", filas_por_pagina=15)
            # Badge por fila usando slot de Quasar table (sin CSS nuevo).
            tbl_sesiones.add_slot("body-cell-severidad", r"""
<q-td :props="props">
    <span :class="`badge badge-${props.row.sev_variante}`">{{ props.row.severidad }}</span>
</q-td>
""")

        # obs_08 R11: mostrar total de resultados junto a la paginación
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
                    ui.label(f"{total_sesiones} resultados").classes("text-sm text-secondary self-center px-2")
                btn_secondary(
                    "Siguiente",
                    on_click=lambda: _ir_pagina(pagina + 1, "sesiones"),
                    icon="chevron_right",
                    size="sm",
                ).set_enabled(hay_sig)

    # ── Filtros comunes ────────────────────────────────────────────────────
    def _on_rango_cambio(desde: str | None, hasta: str | None) -> None:
        presenter.set_rango(desde, hasta)
        _on_filtros_cambio()

    def _render_filtros_comunes() -> None:
        with ui.row().classes("form-row-inline u-mb-lg"):
            date_range_input(
                desde=_s["desde"],
                hasta=_s["hasta"],
                on_change=_on_rango_cambio,
                periodo_desde=_periodo_desde,
                periodo_hasta=_periodo_hasta,
            )
            filter_input(
                label="Usuario ID",
                placeholder="Opcional",
                on_change=lambda e: (
                    presenter.set_usuario(e.value),
                    _on_filtros_cambio(),
                ),
                cls_extra="w-32",
            )

            # NUEVO: filtro de institución — solo admin (R1, R2)
            if ctx.usuario_rol == "admin":
                _instituciones = []
                try:
                    _instituciones = Container.institucion_service().listar()
                except Exception:
                    pass
                inst_opts = {None: "Todas las instituciones"}
                inst_opts.update({i.id: i.nombre for i in _instituciones})
                # obs_09 T12: opción «Sin institución» con centinela (R12)
                inst_opts[_SIN_INSTITUCION_SENTINEL] = "Sin institución"
                filter_select(
                    label="Institución",
                    options=inst_opts,
                    value=None,
                    on_change=lambda e: (
                        presenter.set_institucion(e.value),
                        _on_filtros_cambio(),
                    ),
                    cls_extra="w-52",
                )

            btn_icon("refresh", on_click=_on_filtros_cambio, tooltip="Recargar")

    # ── Contenido principal ────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"), ui.element("div").classes("panel-card"):
                with ui.row().classes("form-row-center u-mb-sm"):
                    ThemeManager.icono("history", size=22, color="var(--color-primary)")
                    ui.label("Registro de auditoría").classes("text-xl font-bold")
                    ui.label("Solo lectura").classes("text-sm text-secondary ml-2")
                    with ui.row().classes("form-row-center ml-auto"):
                        btn_secondary(
                            "Verificar integridad",
                            on_click=lambda: _verificar_integridad(completa=False),
                            icon="verified",
                            size="sm",
                        )
                        btn_secondary(
                            "Verificación completa",
                            on_click=lambda: _verificar_integridad(completa=True),
                            icon="verified_user",
                            size="sm",
                        )
                        badge_integridad()

                _render_filtros_comunes()

                with ui.tabs().classes("w-full") as tabs:
                    ui.tab("cambios", label="Cambios", icon="edit_note")
                    ui.tab("sesiones", label="Sesiones", icon="login")

                with ui.tab_panels(tabs, value="cambios").classes("w-full mt-0"):
                    with ui.tab_panel("cambios"):
                        with ui.row().classes("form-row-center-md u-mb-lg"):
                            ui.label("Filtros:").classes("text-sm font-semibold")
                            # obs_09 T12: selector dropdown de tabla (R10) —
                            # reemplaza el filter_input libre
                            filter_select(
                                label="Tabla",
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
                            # obs_09 T12: filtro por registro_id (R11)
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
                            # obs_07 T12: filtro por severidad
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

    # obs_09 T13: crear el diálogo de detalle una sola vez en el contexto de la
    # página, para que _cuerpo_detalle.refresh() funcione correctamente.
    def _crear_dialogo_detalle() -> None:
        with custom_dialog(max_width="lg", persistent=False) as dlg:
            _dlg_holder.append(dlg)
            _cuerpo_detalle()

    _crear_dialogo_detalle()

    app_layout(
        ctx,
        contenido,
        page_titulo="Auditoría",
        page_subtitulo="Registro de cambios y eventos de sesión (solo lectura)",
        page_icono="history",
    )


__all__ = ["auditoria_page"]
