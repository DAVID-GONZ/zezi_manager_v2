"""
src/interface/pages/evaluacion/configuracion_evaluacion.py
===========================================================
Configuración del SIEE (Sistema Institucional de Evaluación) y categorías
de evaluación por asignación y periodo.

Ruta:   /evaluacion/configuracion
Acceso: todos los autenticados

Secciones:
  A — SIEE institucional
      - Admin / director / coordinador: configuran el modo SIEE y gestionan
        las categorías institucionales (crear, editar, eliminar).
      - Docentes: ven las categorías institucionales en modo solo lectura.

  B — Mis categorías (solo si modo != INSTITUCIONAL_FIJO)
      - Docentes gestionan sus propias categorías dentro del peso disponible.
      - En modo MIXTO_SUBCATEGORIAS pueden anclar una categoría como
        sub-categoría de una institucional que lo permita.
      - En modo MIXTO_AUTONOMIA se muestra la barra de peso autónomo.

La gestión de actividades (crear, publicar, cerrar, eliminar) se delega
completamente a /evaluacion/planilla.
"""
from __future__ import annotations

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
from src.interface.design.components import confirm_dialog, form_dialog
from src.services.evaluacion_service import (
    NuevaCategoriaDTO,
    ActualizarCategoriaDTO,
    NuevaConfiguracionSIEEDTO,
    NuevaCategoriaInstitucionalDTO,
    ModoSIEE,
    ContextoAcademicoDTO,
)
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("EVALUACION.CONFIGURACION")

_ROL_ADMIN = {"admin", "director", "coordinador"}

_MODO_LABELS: dict[str, str] = {
    "libre":               "Libre",
    "institucional_fijo":  "Institucional fijo",
    "mixto_subcategorias": "Mixto — sub-categorías",
    "mixto_autonomia":     "Mixto — autonomía docente",
}

_MODO_DESC: dict[str, str] = {
    "libre": (
        "Cada docente distribuye el 100% del peso libremente."
    ),
    "institucional_fijo": (
        "Todas las categorías son institucionales e inamovibles. "
        "Los docentes solo añaden actividades dentro de ellas."
    ),
    "mixto_subcategorias": (
        "El admin fija macro-categorías. Los docentes pueden crear "
        "sub-categorías dentro de las que lo permitan."
    ),
    "mixto_autonomia": (
        "El admin fija un porcentaje institucional. Los docentes "
        "distribuyen libremente el porcentaje restante."
    ),
}


@ui.page("/evaluacion/configuracion")
def configuracion_evaluacion_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Config evaluación: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    es_admin = ctx.usuario_rol in _ROL_ADMIN

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "anio_id":            None,
        "periodos":           [],
        "asignaciones":       [],
        "periodo_id":         None,
        "asignacion_id":      None,
        # SIEE
        "siee_cfg":           None,    # ConfiguracionSIEE
        "cats_inst":          [],      # list[Categoria] institucionales
        # Categorías del docente (para la asignacion+periodo activos)
        "cats_docente":       [],      # list[Categoria] es_institucional=False
        # formulario nueva cat docente
        "form_nombre":        "",
        "form_peso":          0.10,
        "form_padre_id":      None,    # solo MIXTO_SUBCATEGORIAS
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            _s["anio_id"] = config.id if config else None
            _s["periodos"] = (
                Container.periodo_service().listar_por_anio(_s["anio_id"])
                if _s["anio_id"] else []
            )
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)
            _s["periodos"] = []

        try:
            filtro = FiltroAsignacionesDTO(
                usuario_id=ctx.usuario_id if ctx.usuario_rol == "profesor" else None,
                solo_activas=True,
            )
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error cargando asignaciones: %s", exc)
            _s["asignaciones"] = []

    def _cargar_siee() -> None:
        anio_id = _s["anio_id"]
        if not anio_id:
            return
        try:
            svc = Container.evaluacion_service()
            _s["siee_cfg"]   = svc.get_configuracion_siee(anio_id)
            _s["cats_inst"]  = svc.listar_categorias_institucionales(anio_id)
        except Exception as exc:
            logger.error("Error cargando SIEE: %s", exc)

    def _cargar_cats_docente() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["cats_docente"] = []
            return
        try:
            todas = Container.evaluacion_service().listar_categorias(asig_id, per_id)
            _s["cats_docente"] = [c for c in todas if not c.es_institucional]
        except Exception as exc:
            logger.error("Error cargando categorías docente: %s", exc)
            _s["cats_docente"] = []

    _cargar_estado()
    _cargar_siee()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _modo_actual() -> str:
        cfg = _s["siee_cfg"]
        return cfg.modo.value if cfg else "libre"

    def _ctx_dto() -> ContextoAcademicoDTO | None:
        anio_id = _s["anio_id"]
        per_id  = _s["periodo_id"]
        if not anio_id or not per_id:
            return None
        return ContextoAcademicoDTO(
            usuario_id    = ctx.usuario_id,
            anio_id       = anio_id,
            periodo_id    = per_id,
            asignacion_id = _s["asignacion_id"],
        )

    def _peso_disponible_docente() -> float:
        anio_id = _s["anio_id"]
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        if not anio_id or not asig_id or not per_id:
            return 1.0
        try:
            return Container.evaluacion_service().peso_autonomia_disponible(
                asig_id, per_id, anio_id
            )
        except Exception:
            return 1.0

    # ── Acciones — SIEE (admin) ───────────────────────────────────────────────
    def _guardar_modo_siee(datos: dict) -> None:
        anio_id = _s["anio_id"]
        if not anio_id:
            ui.notify("No hay año activo", type="warning")
            return
        modo_val = datos.get("modo", "libre")
        pct_raw  = datos.get("porcentaje_autonomia")
        pct      = float(pct_raw) / 100.0 if pct_raw else None

        try:
            dto = NuevaConfiguracionSIEEDTO(
                anio_id                      = anio_id,
                modo                         = ModoSIEE(modo_val),
                porcentaje_autonomia_docente = pct,
            )
            Container.evaluacion_service().guardar_configuracion_siee(dto, ctx.usuario_id)
            ui.notify("Configuración SIEE guardada", type="positive")
            _cargar_siee()
            seccion_institucional.refresh()
            seccion_docente.refresh()
        except (ValueError, RuntimeError) as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error guardando SIEE: %s", exc)
            ui.notify("Error al guardar la configuración", type="negative")

    def _abrir_dialog_modo_siee() -> None:
        cfg     = _s["siee_cfg"]
        modo_v  = cfg.modo.value if cfg else "libre"
        pct_v   = round((cfg.porcentaje_autonomia_docente or 0) * 100, 1) if cfg else 0.0

        form_dialog(
            titulo    = "Configurar modo SIEE",
            campos    = [
                {
                    "key":     "modo",
                    "label":   "Modo de distribución",
                    "tipo":    "select",
                    "valor":   modo_v,
                    "opciones": {k: v for k, v in _MODO_LABELS.items()},
                    "requerido": True,
                },
                {
                    "key":         "porcentaje_autonomia",
                    "label":       "% autonomía docente (solo modo mixto-autonomía)",
                    "tipo":        "number",
                    "valor":       pct_v,
                    "min":         1,
                    "max":         99,
                    "step":        1,
                    "placeholder": "Ej: 30 (para 30%)",
                },
            ],
            on_submit = _guardar_modo_siee,
            max_width = "max-w-lg",
        )

    def _crear_cat_institucional() -> None:
        anio_id = _s["anio_id"]
        if not anio_id:
            ui.notify("Sin año activo", type="warning")
            return

        def _guardar(datos: dict) -> None:
            nombre  = str(datos.get("nombre", "")).strip()
            peso_v  = datos.get("peso")
            permite = bool(datos.get("permite_subcategorias", False))
            if not nombre:
                ui.notify("El nombre es obligatorio", type="warning")
                return
            try:
                peso = float(peso_v) / 100.0  # la UI muestra porcentaje
                dto  = NuevaCategoriaInstitucionalDTO(
                    nombre                = nombre,
                    peso                  = peso,
                    anio_id               = anio_id,
                    permite_subcategorias = permite,
                )
                Container.evaluacion_service().agregar_categoria_institucional(
                    dto, usuario_id=ctx.usuario_id
                )
                ui.notify(f"Categoría '{nombre}' creada", type="positive")
                _cargar_siee()
                seccion_institucional.refresh()
                seccion_docente.refresh()
            except (ValueError, RuntimeError) as exc:
                ui.notify(str(exc), type="warning")
            except Exception as exc:
                logger.error("Error creando cat. institucional: %s", exc)
                ui.notify("Error al crear la categoría", type="negative")

        form_dialog(
            titulo    = "Nueva categoría institucional",
            campos    = [
                {"key": "nombre",  "label": "Nombre *", "tipo": "text",
                 "requerido": True, "placeholder": "Ej: Saber"},
                {"key": "peso",    "label": "Porcentaje (1–100) *", "tipo": "number",
                 "min": 1, "max": 100, "step": 1, "valor": 10},
                {"key": "permite_subcategorias", "label": "Permite sub-categorías docente",
                 "tipo": "checkbox", "valor": False},
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    def _editar_cat_institucional(cat) -> None:
        anio_id = _s["anio_id"]

        def _guardar(datos: dict) -> None:
            nuevo_nombre = str(datos.get("nombre", "")).strip() or None
            peso_v       = datos.get("peso")
            if not nuevo_nombre:
                ui.notify("El nombre es obligatorio", type="warning")
                return
            try:
                nuevo_peso = float(peso_v) / 100.0 if peso_v is not None else None
                dto        = ActualizarCategoriaDTO(nombre=nuevo_nombre, peso=nuevo_peso)
                Container.evaluacion_service().actualizar_categoria_institucional(
                    cat.id, dto, anio_id, usuario_id=ctx.usuario_id
                )
                ui.notify("Categoría actualizada", type="positive")
                _cargar_siee()
                seccion_institucional.refresh()
                seccion_docente.refresh()
            except (ValueError, RuntimeError) as exc:
                ui.notify(str(exc), type="warning")
            except Exception as exc:
                logger.error("Error actualizando cat. institucional: %s", exc)
                ui.notify("Error al actualizar", type="negative")

        form_dialog(
            titulo    = "Editar categoría institucional",
            campos    = [
                {"key": "nombre", "label": "Nombre *", "tipo": "text",
                 "valor": cat.nombre, "requerido": True},
                {"key": "peso",   "label": "Porcentaje (1–100) *", "tipo": "number",
                 "valor": round(cat.peso * 100, 1), "min": 1, "max": 100, "step": 1},
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    def _eliminar_cat_institucional(cat) -> None:
        def _ejecutar() -> None:
            try:
                Container.evaluacion_service().eliminar_categoria_institucional(
                    cat.id, usuario_id=ctx.usuario_id
                )
                ui.notify(f"'{cat.nombre}' eliminada", type="positive")
                _cargar_siee()
                seccion_institucional.refresh()
                seccion_docente.refresh()
            except (ValueError, RuntimeError) as exc:
                ui.notify(str(exc), type="warning")
            except Exception as exc:
                logger.error("Error eliminando cat. institucional: %s", exc)
                ui.notify("Error al eliminar", type="negative")

        confirm_dialog(
            titulo          = "Eliminar categoría institucional",
            mensaje         = (
                f"¿Eliminar '{cat.nombre}'? Esta categoría es institucional. "
                "Si hay sub-categorías asociadas quedarán sin padre."
            ),
            on_confirm      = _ejecutar,
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    # ── Acciones — categorías docente ─────────────────────────────────────────
    def _crear_cat_docente() -> None:
        asig_id = _s["asignacion_id"]
        per_id  = _s["periodo_id"]
        cdt     = _ctx_dto()
        if not asig_id or not per_id or not cdt:
            ui.notify("Seleccione periodo y asignación primero", type="warning")
            return

        nombre = str(_s["form_nombre"]).strip()
        if not nombre:
            ui.notify("El nombre no puede estar vacío", type="warning")
            return
        try:
            peso = float(_s["form_peso"])
        except (TypeError, ValueError):
            ui.notify("El peso debe ser un número", type="warning")
            return

        padre_id = _s["form_padre_id"] if _modo_actual() == "mixto_subcategorias" else None

        try:
            dto = NuevaCategoriaDTO(
                nombre             = nombre,
                peso               = peso,
                asignacion_id      = asig_id,
                periodo_id         = per_id,
                categoria_padre_id = padre_id,
            )
            Container.evaluacion_service().agregar_categoria(
                dto, cdt, usuario_id=ctx.usuario_id
            )
            ui.notify(f"Categoría '{nombre}' creada", type="positive")
            _s["form_nombre"]   = ""
            _s["form_peso"]     = 0.10
            _s["form_padre_id"] = None
            _cargar_cats_docente()
            seccion_docente.refresh()
        except PermissionError as exc:
            ui.notify(str(exc), type="warning")
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al crear categoría: %s", exc)
            ui.notify("Error al crear la categoría", type="negative")

    def _editar_cat_docente(cat) -> None:
        def _guardar(datos: dict) -> "bool | None":
            try:
                nuevo_nombre = str(datos.get("nombre", "")).strip() or None
                if not nuevo_nombre:
                    ui.notify("El nombre es obligatorio", type="warning")
                    return False
                nuevo_peso = float(datos["peso"]) if datos.get("peso") is not None else None
                dto_act = ActualizarCategoriaDTO(nombre=nuevo_nombre, peso=nuevo_peso)
                Container.evaluacion_service().actualizar_categoria(
                    cat.id, dto_act, usuario_id=ctx.usuario_id
                )
                ui.notify("Categoría actualizada", type="positive")
                _cargar_cats_docente()
                seccion_docente.refresh()
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
                return False
            except Exception as exc:
                logger.error("Error al actualizar categoría: %s", exc)
                ui.notify("Error al actualizar", type="negative")
                return False

        form_dialog(
            titulo    = "Editar categoría",
            campos    = [
                {"key": "nombre", "label": "Nombre *", "tipo": "text",
                 "valor": cat.nombre, "requerido": True},
                {"key": "peso",   "label": "Peso (0.01–1.0) *", "tipo": "number",
                 "valor": cat.peso, "min": 0.01, "max": 1.0, "step": 0.01, "format": "%.2f"},
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    def _eliminar_cat_docente(cat) -> None:
        def _ejecutar() -> None:
            try:
                Container.evaluacion_service().eliminar_categoria(
                    cat.id, usuario_id=ctx.usuario_id
                )
                ui.notify(f"'{cat.nombre}' eliminada", type="positive")
                _cargar_cats_docente()
                seccion_docente.refresh()
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
            except Exception as exc:
                logger.error("Error al eliminar categoría: %s", exc)
                ui.notify("Error al eliminar", type="negative")

        confirm_dialog(
            titulo          = "Eliminar categoría",
            mensaje         = f"¿Eliminar '{cat.nombre}'? Esta acción es irreversible.",
            on_confirm      = _ejecutar,
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    def _on_selector_cambio() -> None:
        _cargar_cats_docente()
        seccion_docente.refresh()

    # ── Secciones refreshables ────────────────────────────────────────────────

    @ui.refreshable
    def seccion_institucional() -> None:
        """Sección A — SIEE institucional (solo lectura para docentes)."""
        cfg        = _s["siee_cfg"]
        cats_inst  = _s["cats_inst"]
        modo_val   = cfg.modo.value if cfg else "libre"
        modo_label = _MODO_LABELS.get(modo_val, modo_val)
        modo_desc  = _MODO_DESC.get(modo_val, "")
        suma_inst  = round(sum(c.peso for c in cats_inst) * 100, 1)

        with ui.element("div").classes("panel-card"):
            # Cabecera
            with ui.row().classes("items-center gap-3 mb-4"):
                ui.icon("school").classes("text-primary text-xl")
                ui.label("Configuración SIEE").classes("text-lg font-bold flex-1")
                # Badge modo
                color_badge = {
                    "libre":               "grey",
                    "institucional_fijo":  "negative",
                    "mixto_subcategorias": "primary",
                    "mixto_autonomia":     "warning",
                }.get(modo_val, "grey")
                ui.badge(modo_label).props(f"color={color_badge}")
                if es_admin:
                    btn_secondary(
                        "Cambiar modo",
                        icon="tune",
                        on_click=_abrir_dialog_modo_siee,
                    )

            # Descripción del modo activo
            with ui.element("div").classes("bg-blue-50 rounded p-3 mb-4 text-sm text-blue-800"):
                ui.label(modo_desc)

            # Datos extra para MIXTO_AUTONOMIA
            if modo_val == "mixto_autonomia" and cfg and cfg.porcentaje_autonomia_docente:
                pct_inst  = round((1.0 - cfg.porcentaje_autonomia_docente) * 100, 1)
                pct_doc   = round(cfg.porcentaje_autonomia_docente * 100, 1)
                with ui.row().classes("gap-4 mb-3 text-sm"):
                    ui.label(f"Institucional: {pct_inst}%").classes("font-medium")
                    ui.label(f"Autonomía docente: {pct_doc}%").classes(
                        "font-medium text-primary"
                    )

            # Sub-cabecera categorías institucionales
            with ui.row().classes("items-center gap-2 mb-3"):
                ui.label("Categorías institucionales").classes("font-semibold text-sm")
                ui.badge(f"{suma_inst:.0f}%").classes(
                    "badge-success" if suma_inst <= 100 else "badge-error"
                )
                if es_admin:
                    btn_icon(
                        "add_circle",
                        on_click=_crear_cat_institucional,
                        tooltip="Agregar categoría institucional",
                    )

            if not cats_inst:
                ui.label("No hay categorías institucionales definidas.").classes(
                    "text-empty text-sm"
                )
            else:
                with ui.element("div").classes("w-full divide-y divide-grey-3"):
                    for cat in cats_inst:
                        with ui.row().classes("items-center gap-3 py-2"):
                            ui.icon("lock").classes("text-grey-5 text-base")
                            ui.label(cat.nombre).classes("flex-1 text-sm font-medium")
                            ui.label(f"{cat.peso_porcentaje:.1f}%").classes(
                                "text-sm font-mono w-14 text-right"
                            )
                            if cat.permite_subcategorias:
                                ui.badge("sub-cats").props("color=teal outline").classes(
                                    "text-xs"
                                )
                            if es_admin:
                                with ui.row().classes("gap-1"):
                                    btn_icon(
                                        "edit",
                                        on_click=lambda c=cat: _editar_cat_institucional(c),
                                        tooltip="Editar",
                                    )
                                    btn_icon(
                                        "delete",
                                        on_click=lambda c=cat: _eliminar_cat_institucional(c),
                                        tooltip="Eliminar",
                                        variante="danger",
                                    )

    @ui.refreshable
    def seccion_docente() -> None:
        """Sección B — Categorías propias del docente."""
        modo      = _modo_actual()
        cats_doc  = _s["cats_docente"]
        asig_id   = _s["asignacion_id"]
        per_id    = _s["periodo_id"]

        # En modo INSTITUCIONAL_FIJO: solo mostramos info
        if modo == "institucional_fijo":
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-2 text-amber-700 bg-amber-50 rounded p-3"):
                    ui.icon("info").classes("text-lg")
                    ui.label(
                        "El SIEE está en modo Institucional fijo. "
                        "Las categorías son gestionadas exclusivamente por administración."
                    ).classes("text-sm")
            return

        with ui.element("div").classes("panel-card mt-4"):
            with ui.row().classes("items-center gap-2 mb-4"):
                ui.icon("edit_note").classes("text-primary text-xl")
                ui.label("Mis categorías").classes("text-lg font-bold flex-1")

            # Selector de contexto
            periodos_opts   = {p.id: p.nombre for p in _s["periodos"]}
            asigs_opts      = {a.asignacion_id: a.display_corto for a in _s["asignaciones"]}

            with ui.row().classes("gap-4 items-center flex-wrap mb-4"):
                ui.select(
                    periodos_opts or {"": "Sin periodos"},
                    value=_s["periodo_id"],
                    label="Periodo *",
                    on_change=lambda e: (
                        _s.__setitem__("periodo_id", e.value),
                        _on_selector_cambio(),
                    ),
                ).classes("w-48")
                ui.select(
                    asigs_opts or {"": "Sin asignaciones"},
                    value=_s["asignacion_id"],
                    label="Asignación *",
                    on_change=lambda e: (
                        _s.__setitem__("asignacion_id", e.value),
                        _on_selector_cambio(),
                    ),
                ).classes("w-64")

            if not asig_id or not per_id:
                ui.label("Selecciona periodo y asignación para gestionar tus categorías.").classes(
                    "text-empty text-sm"
                )
                return

            # Barra de peso disponible
            disponible = _peso_disponible_docente()
            usado      = round((1.0 - disponible) * 100, 1)
            total_pct  = round(disponible * 100, 1)

            with ui.element("div").classes("mb-4"):
                with ui.row().classes("items-center gap-3 mb-1"):
                    ui.label("Peso disponible:").classes("text-sm font-semibold")
                    ui.label(f"{total_pct:.1f}%").classes(
                        f"font-bold {'text-green-700' if disponible > 0.001 else 'text-grey-5'}"
                    )
                    ui.label(f"(usado: {usado:.1f}%)").classes("text-sm text-grey-6")

                # Barra visual
                with ui.element("div").classes("w-full rounded h-2 bg-grey-2 overflow-hidden"):
                    ancho_usado = min(100, round(usado))
                    color_bar   = "bg-green-500" if usado <= 100 else "bg-red-500"
                    ui.element("div").classes(f"{color_bar} h-full").style(
                        f"width: {ancho_usado}%"
                    )

            # Formulario nueva categoría docente
            if modo == "mixto_subcategorias":
                cats_inst = _s["cats_inst"]
                padres_permitidos = {c.id: c.nombre for c in cats_inst if c.permite_subcategorias}

            with ui.element("div").classes("bg-grey-1 rounded p-3 mb-4"):
                ui.label("Nueva categoría").classes("text-sm font-semibold mb-2")
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input(
                        "Nombre *",
                        placeholder="Ej: Quizzes",
                    ).classes("w-44").bind_value(_s, "form_nombre")
                    ui.number(
                        "Peso (0.01–1.0)",
                        value=0.10,
                        min=0.01,
                        max=1.0,
                        step=0.01,
                        format="%.2f",
                    ).classes("w-32").bind_value(_s, "form_peso")

                    # Selector de padre solo en MIXTO_SUBCATEGORIAS
                    if modo == "mixto_subcategorias" and padres_permitidos:
                        ui.select(
                            {None: "— Sin padre —", **padres_permitidos},
                            value=None,
                            label="Sub-categoría de",
                            on_change=lambda e: _s.__setitem__("form_padre_id", e.value),
                        ).classes("w-44")

                    btn_primary("Agregar", icon="add", on_click=_crear_cat_docente)

            # Tabla de categorías docente
            if not cats_doc:
                ui.label("No has creado categorías propias para este periodo y asignación.").classes(
                    "text-empty text-sm"
                )
                return

            with ui.element("div").classes("w-full"):
                with ui.element("div").classes(
                    "flex gap-3 px-2 py-1 font-semibold text-xs text-grey-7 border-b"
                ):
                    ui.label("Nombre").classes("flex-1")
                    ui.label("Padre").classes("w-28")
                    ui.label("Peso").classes("w-20 text-right")
                    ui.label("").classes("w-20 text-right")

                cats_inst_map = {c.id: c.nombre for c in _s["cats_inst"]}
                for cat in cats_doc:
                    padre_nombre = (
                        cats_inst_map.get(cat.categoria_padre_id, "—")
                        if cat.categoria_padre_id else "—"
                    )
                    with ui.element("div").classes("flex items-center gap-3 px-2 py-2 border-b"):
                        ui.label(cat.nombre).classes("flex-1 text-sm")
                        ui.label(padre_nombre).classes("w-28 text-xs text-grey-6")
                        ui.label(f"{cat.peso_porcentaje:.1f}%").classes(
                            "w-20 text-right font-mono text-sm"
                        )
                        with ui.row().classes("w-20 justify-end gap-1"):
                            btn_icon(
                                "edit",
                                on_click=lambda c=cat: _editar_cat_docente(c),
                                tooltip="Editar",
                            )
                            btn_icon(
                                "delete",
                                on_click=lambda c=cat: _eliminar_cat_docente(c),
                                tooltip="Eliminar",
                                variante="danger",
                            )

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Header de página
            with ui.element("div").classes("panel-card mb-0"):
                with ui.row().classes("items-center gap-2"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Configuración de Evaluación").classes("text-xl font-bold flex-1")
                    btn_ghost(
                        "Ir a Planilla de notas",
                        icon="table_chart",
                        on_click=lambda: ui.navigate.to("/evaluacion/planilla"),
                    )

            with ui.element("div").classes("mt-4"):
                ui.label(
                    "Aquí configuras las categorías de evaluación. "
                    "Para gestionar actividades y registrar notas, ve a "
                    "Planilla de notas."
                ).classes("text-sm text-grey-7 mb-4")

            # Sección A — institucional
            seccion_institucional()

            # Sección B — docente (si aplica según modo)
            seccion_docente()

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        titulo_pagina    = "Evaluación · Configuración",
        usuario_nombre   = ctx.usuario_nombre,
        usuario_rol      = ctx.usuario_rol,
        ruta_activa      = "/evaluacion/configuracion",
        contenido        = contenido,
        ctx              = ctx,
        on_context_change = on_context_change,
    )


__all__ = ["configuracion_evaluacion_page"]
