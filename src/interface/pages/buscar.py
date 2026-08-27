"""
src/interface/pages/buscar.py
==============================
Página de resultados de búsqueda global — ruta /buscar

Recibe el parámetro ?q= de la URL (escrito desde el topbar).
Muestra resultados paginados por tipo de entidad con tabs filtrables.

La autorización de qué se muestra es responsabilidad del BusquedaService,
que aplica scoping por rol e institución antes de devolver resultados.
"""

from __future__ import annotations

import logging

from nicegui import context as ng_context
from nicegui import ui

from container import Container
from src.domain.models.busqueda import TipoResultadoBusqueda
from src.interface.context.session_context import SessionContext
from src.interface.design.components import empty_state, toast_error
from src.interface.design.components.buttons import btn_ghost
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.presenters.buscar_presenter import BuscarPresenter
from src.services.busqueda_service import tipos_buscables

logger = logging.getLogger("BUSCAR")

_ICONO_POR_TIPO: dict[str, str] = {
    TipoResultadoBusqueda.ESTUDIANTE: "person",
    TipoResultadoBusqueda.USUARIO: "manage_accounts",
    TipoResultadoBusqueda.GRUPO: "groups",
    TipoResultadoBusqueda.ASIGNATURA: "book",
}

_LABEL_POR_TIPO: dict[str, str] = {
    TipoResultadoBusqueda.ESTUDIANTE: "Estudiantes",
    TipoResultadoBusqueda.USUARIO: "Usuarios",
    TipoResultadoBusqueda.GRUPO: "Grupos",
    TipoResultadoBusqueda.ASIGNATURA: "Asignaturas",
}

# NOTA: qué tipos puede buscar cada rol (RBAC) vive en el BACKEND
# (`busqueda_service.tipos_buscables`), fuente única compartida con el servicio.

_POR_PAGINA = 20


# page-delegate: ruta y guard de rol registrados en main.py
def buscar_page() -> None:
    """Página de resultados de búsqueda global — ruta /buscar."""
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    # Leer término de la URL query string (?q=...)
    termino_inicial = ""
    try:
        termino_inicial = ng_context.client.request.query_params.get("q", "") or ""
    except Exception:
        pass

    tipos_visibles = tipos_buscables(ctx.usuario_rol)

    presenter = BuscarPresenter(termino_inicial)
    _s = presenter.estado  # misma referencia: los refreshables leen el estado del presenter

    def contenido() -> None:

        # ── Barra de búsqueda ─────────────────────────────────────────────────
        with ui.element("div").classes("buscar-searchbar panel-card mb-4"):
            with ui.row().classes("items-center gap-3 w-full"):
                ThemeManager.icono("search", size=20)
                search_input = (
                    ui.input(
                        placeholder="Buscar estudiantes, grupos, usuarios...",
                        value=_s["termino"],
                    )
                    .classes("andes-input buscar-input flex-1")
                    .props("borderless dense")
                )
                search_input.on(
                    "update:model-value",
                    lambda e: _on_termino_change(e.args),
                )
                search_input.on(
                    "keydown.enter",
                    lambda: _on_termino_change(search_input.value),
                )

        def _on_termino_change(valor) -> None:
            presenter.set_termino(valor)
            _cargar_resultados()
            try:
                ui.run_javascript(
                    f"window.history.replaceState(null, '', '/buscar?q={_s['termino']}')"
                )
            except Exception:
                pass

        # ── Tabs por tipo ─────────────────────────────────────────────────────
        with ui.row().classes("buscar-tabs gap-2 mb-4"):

            def _on_tab(tipo_valor: str | None) -> None:
                presenter.set_tab(tipo_valor)
                _cargar_resultados()

            ui.button(
                "Todos",
                on_click=lambda: _on_tab(None),
            ).classes(
                "buscar-tab buscar-tab--activo"
                if _s["tipo_filtro"] is None
                else "buscar-tab"
            )
            for tipo in tipos_visibles:
                activo = _s["tipo_filtro"] == tipo
                ui.button(
                    _LABEL_POR_TIPO[tipo],
                    on_click=lambda t=tipo: _on_tab(t),
                ).classes(f"buscar-tab {'buscar-tab--activo' if activo else ''}")

        # ── Resultados (refreshable) ──────────────────────────────────────────

        @ui.refreshable
        def tabla_resultados() -> None:
            resultado = _s["resultados"]
            termino = (_s["termino"] or "").strip()

            if resultado is None:
                if termino and not presenter.termino_buscable():
                    empty_state(
                        icono="search",
                        titulo="Escribe al menos 2 caracteres",
                        descripcion="Ingresa más caracteres para buscar.",
                        variante="search",
                    )
                else:
                    empty_state(
                        icono="search",
                        titulo="Busca estudiantes, grupos y más",
                        descripcion="Escribe en el campo de arriba para comenzar.",
                        variante="search",
                    )
                return

            if not resultado.resultados:
                empty_state(
                    icono="search_off",
                    titulo=f'Sin resultados para "{termino}"',
                    descripcion="Intenta con otro término o revisa la ortografía.",
                    variante="search",
                )
                return

            # Totales (formato en el presenter)
            total_txt = presenter.total_texto(resultado)

            with ui.row().classes("buscar-totales items-center mb-3"):
                ui.label(total_txt).classes("buscar-total-label")

            # Lista de resultados
            tipo_actual: str | None = None
            for item in resultado.resultados:
                tipo_str = item.tipo.value

                if tipo_str != tipo_actual and _s["tipo_filtro"] is None:
                    tipo_actual = tipo_str
                    with ui.row().classes(
                        "buscar-seccion-header items-center gap-2 mt-4 mb-2"
                    ):
                        ThemeManager.icono(_ICONO_POR_TIPO.get(tipo_str, "label"), size=16)
                        ui.label(_LABEL_POR_TIPO.get(tipo_str, tipo_str)).classes(
                            "buscar-seccion-titulo"
                        )

                ruta = item.ruta
                with ui.element("div").classes("buscar-result-item").on(
                    "click", lambda r=ruta: ui.navigate.to(r) if r else None
                ), ui.row().classes("items-center gap-3"):
                    ThemeManager.icono(
                        _ICONO_POR_TIPO.get(tipo_str, "label"), size=20
                    )
                    with ui.column().classes("gap-0 flex-1 buscar-result-text"):
                        ui.label(item.titulo).classes("buscar-result-titulo")
                        if item.subtitulo:
                            ui.label(item.subtitulo).classes(
                                "buscar-result-subtitulo"
                            )
                    if ruta:
                        ThemeManager.icono("chevron_right", size=16)

            # Paginación
            if resultado.limitado or _s["pagina"] > 1:
                with ui.row().classes("buscar-paginacion justify-center mt-4 gap-2"):
                    if _s["pagina"] > 1:
                        btn_ghost(
                            "Anterior",
                            on_click=lambda: _paginar(_s["pagina"] - 1),
                            icon="arrow_back",
                        )
                    if resultado.limitado:
                        btn_ghost(
                            "Siguiente",
                            on_click=lambda: _paginar(_s["pagina"] + 1),
                            icon="arrow_forward",
                        )

        def _cargar_resultados() -> None:
            if not presenter.termino_buscable():
                presenter.set_resultados(None)
                tabla_resultados.refresh()
                return
            termino = _s["termino"]
            try:
                svc = Container.busqueda_service()
                tipo_filtro = _s["tipo_filtro"]
                tipo_enum = TipoResultadoBusqueda(tipo_filtro) if tipo_filtro else None
                presenter.set_resultados(
                    svc.buscar_completo(
                        termino,
                        rol=ctx.usuario_rol,
                        usuario_id=ctx.usuario_id,
                        tipo_filtro=tipo_enum,
                        pagina=_s["pagina"],
                        por_pagina=_POR_PAGINA,
                    )
                )
            except Exception as exc:
                logger.error("Error en búsqueda '%s': %s", termino, exc)
                toast_error("Error al realizar la búsqueda.")
                presenter.set_resultados(None)
            tabla_resultados.refresh()

        def _paginar(pagina: int) -> None:
            presenter.set_pagina(pagina)
            _cargar_resultados()

        # Ejecutar búsqueda inicial si viene un término válido en la URL
        if presenter.termino_buscable():
            _cargar_resultados()

        tabla_resultados()

    app_layout(
        ctx,
        contenido,
        page_titulo="Búsqueda",
        page_subtitulo=f'"{_s["termino"]}"' if _s["termino"] else "Global",
        page_icono="search",
    )
