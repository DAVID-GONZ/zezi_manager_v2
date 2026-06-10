"""
src/interface/pages/admin/configuracion_sie.py
==============================================
Configuración institucional SIEE completa.
Ruta:   /admin/configuracion
Acceso: admin, director, coordinador

Secciones:
  1 — Año lectivo activo (crear nuevo año)
  2 — Escala de notas (nota_minima_escala, nota_maxima_escala, nota_minima_aprobacion)
  3 — Niveles de desempeño (CRUD de NivelDesempeno)
  4 — Criterios de promoción (CriterioPromocion)
  5 — Modo SIEE (ModoSIEE + porcentaje_autonomia_docente)
  6 — Categorías institucionales (CRUD de Categoria institucional)
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
from src.interface.design.components import badge_estado_general, confirm_dialog, form_dialog, status_badge, toast_error, toast_success, toast_warning
from src.services.configuracion_service import (
    NuevaConfiguracionAnioDTO, ActualizarConfiguracionAnioDTO,
    NivelDesempeno, CriterioPromocion, NuevoNivelDesempenoDTO,
)
from src.services.evaluacion_service import (
    NuevaCategoriaInstitucionalDTO,
    ActualizarCategoriaDTO,
    NuevaConfiguracionSIEEDTO,
    ModoSIEE,
)

logger = logging.getLogger("ADMIN.CONFIG_SIEE")

_ROL_ADMIN = {"admin", "director", "coordinador"}

_MODO_LABELS: dict[str, str] = {
    "libre":               "Libre",
    "institucional_fijo":  "Institucional fijo",
    "mixto_subcategorias": "Mixto — sub-categorías",
    "mixto_autonomia":     "Mixto — autonomía docente",
}

_MODO_DESC: dict[str, str] = {
    "libre": "Cada docente distribuye el 100% del peso libremente.",
    "institucional_fijo": "Todas las categorías son institucionales e inamovibles. Los docentes solo añaden actividades dentro de ellas.",
    "mixto_subcategorias": "El admin fija macro-categorías. Los docentes pueden crear sub-categorías dentro de las que lo permitan.",
    "mixto_autonomia": "El admin fija un porcentaje institucional. Los docentes distribuyen libremente el porcentaje restante.",
}


@ui.page("/admin/configuracion")
def configuracion_sie_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in _ROL_ADMIN:
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    logger.info("Config SIEE: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    _s: dict = {
        "config_activa": None,
        "nuevo_anio":    2026,
        "niveles":       [],
        "criterios":     None,
        "siee_cfg":      None,
        "cats_inst":     [],
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_todo() -> None:
        try:
            _s["config_activa"] = Container.configuracion_service().get_activa()
        except Exception as exc:
            logger.warning("Sin año activo: %s", exc)
            _s["config_activa"] = None

        anio_id = _s["config_activa"].id if _s["config_activa"] else None
        if not anio_id:
            return

        try:
            _s["niveles"] = Container.configuracion_service().listar_niveles(anio_id)
        except Exception as exc:
            logger.error("Error niveles: %s", exc)
            _s["niveles"] = []

        try:
            _s["criterios"] = Container.configuracion_service().get_criterios(anio_id)
        except Exception as exc:
            logger.error("Error criterios: %s", exc)
            _s["criterios"] = None

        try:
            svc = Container.evaluacion_service()
            _s["siee_cfg"]  = svc.get_configuracion_siee(anio_id)
            _s["cats_inst"] = svc.listar_categorias_institucionales(anio_id)
        except Exception as exc:
            logger.error("Error SIEE: %s", exc)

    _cargar_todo()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _anio_id() -> int | None:
        return _s["config_activa"].id if _s["config_activa"] else None

    def _modo_actual() -> str:
        cfg = _s["siee_cfg"]
        return cfg.modo.value if cfg else "libre"

    # ── Acciones — año lectivo ────────────────────────────────────────────────
    def _crear_anio() -> None:
        try:
            anio = int(_s["nuevo_anio"])
            dto  = NuevaConfiguracionAnioDTO(anio=anio)
            Container.configuracion_service().crear_anio(dto)
            toast_success(f"Año lectivo {anio} creado")
            _cargar_todo()
            panel_anio.refresh()
            panel_escala.refresh()
            panel_niveles.refresh()
            panel_criterios.refresh()
            panel_modo_siee.refresh()
            panel_cats_inst.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error creando año: %s", exc)
            toast_error("Error al crear el año lectivo")

    # ── Acciones — escala ─────────────────────────────────────────────────────
    def _editar_escala() -> None:
        config = _s["config_activa"]
        if not config:
            return

        def _guardar(datos: dict) -> None:
            try:
                dto = ActualizarConfiguracionAnioDTO(
                    nota_minima_escala     = float(datos["nota_minima_escala"]),
                    nota_maxima_escala     = float(datos["nota_maxima_escala"]),
                    nota_minima_aprobacion = float(datos["nota_minima_aprobacion"]),
                )
                Container.configuracion_service().actualizar_configuracion_academica(
                    config.id, dto
                )
                toast_success("Escala de notas actualizada")
                _cargar_todo()
                panel_escala.refresh()
                panel_anio.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error escala: %s", exc)
                toast_error("Error al guardar la escala")

        form_dialog(
            titulo = "Escala de notas",
            campos = [
                {
                    "key": "nota_minima_escala",
                    "label": "Nota mínima de la escala *",
                    "tipo": "number",
                    "valor": config.nota_minima_escala,
                    "min": 0, "max": 100, "step": 0.5,
                },
                {
                    "key": "nota_maxima_escala",
                    "label": "Nota máxima de la escala *",
                    "tipo": "number",
                    "valor": config.nota_maxima_escala,
                    "min": 0, "max": 100, "step": 0.5,
                },
                {
                    "key": "nota_minima_aprobacion",
                    "label": "Nota de aprobación *",
                    "tipo": "number",
                    "valor": config.nota_minima_aprobacion,
                    "min": 0, "max": 100, "step": 0.5,
                },
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    # ── Acciones — niveles de desempeño ──────────────────────────────────────
    def _restablecer_niveles_default() -> None:
        anio_id = _anio_id()
        if not anio_id:
            return

        def _ejecutar() -> None:
            try:
                defaults = [
                    NuevoNivelDesempenoDTO(anio_id=anio_id, nombre="Bajo",     rango_min=0.0,  rango_max=59.9, orden=0),
                    NuevoNivelDesempenoDTO(anio_id=anio_id, nombre="Básico",   rango_min=60.0, rango_max=69.9, orden=1),
                    NuevoNivelDesempenoDTO(anio_id=anio_id, nombre="Alto",     rango_min=70.0, rango_max=84.9, orden=2),
                    NuevoNivelDesempenoDTO(anio_id=anio_id, nombre="Superior", rango_min=85.0, rango_max=100.0, orden=3),
                ]
                Container.configuracion_service().configurar_niveles(anio_id, defaults)
                toast_success("Niveles restablecidos")
                _cargar_todo()
                panel_niveles.refresh()
            except Exception as exc:
                logger.error("Error restableciendo niveles: %s", exc)
                toast_error("Error al restablecer niveles")

        confirm_dialog(
            titulo          = "Restablecer niveles por defecto",
            mensaje         = "Se reemplazarán todos los niveles actuales con los valores estándar (Bajo, Básico, Alto, Superior). ¿Continuar?",
            on_confirm      = _ejecutar,
            texto_confirmar = "Restablecer",
        )

    def _agregar_nivel() -> None:
        anio_id = _anio_id()
        if not anio_id:
            return

        def _guardar(datos: dict) -> None:
            try:
                nuevo = NuevoNivelDesempenoDTO(
                    anio_id     = anio_id,
                    nombre      = str(datos.get("nombre", "")).strip(),
                    rango_min   = float(datos["rango_min"]),
                    rango_max   = float(datos["rango_max"]),
                    descripcion = str(datos.get("descripcion", "")).strip() or None,
                )
                existentes = _s["niveles"]
                nuevos_dtos = [
                    NuevoNivelDesempenoDTO(
                        anio_id=anio_id, nombre=n.nombre,
                        rango_min=n.rango_min, rango_max=n.rango_max,
                        descripcion=n.descripcion, orden=n.orden,
                    )
                    for n in existentes
                ] + [nuevo]
                Container.configuracion_service().configurar_niveles(anio_id, nuevos_dtos)
                toast_success(f"Nivel '{nuevo.nombre}' agregado")
                _cargar_todo()
                panel_niveles.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error agregando nivel: %s", exc)
                toast_error("Error al agregar nivel")

        form_dialog(
            titulo = "Nuevo nivel de desempeño",
            campos = [
                {"key": "nombre",      "label": "Nombre *",         "tipo": "text",   "requerido": True, "placeholder": "Ej: Alto"},
                {"key": "rango_min",   "label": "Rango mínimo *",   "tipo": "number", "min": 0, "max": 100, "step": 0.1, "valor": 0.0},
                {"key": "rango_max",   "label": "Rango máximo *",   "tipo": "number", "min": 0, "max": 100, "step": 0.1, "valor": 100.0},
                {"key": "descripcion", "label": "Descripción",      "tipo": "text",   "placeholder": "Opcional"},
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    def _editar_nivel(nivel: NivelDesempeno) -> None:
        anio_id = _anio_id()
        if not anio_id:
            return

        def _guardar(datos: dict) -> None:
            try:
                actualizados = []
                for n in _s["niveles"]:
                    if n.id == nivel.id:
                        actualizados.append(NuevoNivelDesempenoDTO(
                            anio_id=anio_id,
                            nombre=str(datos.get("nombre", n.nombre)).strip() or n.nombre,
                            rango_min=float(datos["rango_min"]),
                            rango_max=float(datos["rango_max"]),
                            descripcion=str(datos.get("descripcion", "")).strip() or None,
                            orden=n.orden,
                        ))
                    else:
                        actualizados.append(NuevoNivelDesempenoDTO(
                            anio_id=anio_id, nombre=n.nombre,
                            rango_min=n.rango_min, rango_max=n.rango_max,
                            descripcion=n.descripcion, orden=n.orden,
                        ))
                Container.configuracion_service().configurar_niveles(anio_id, actualizados)
                toast_success("Nivel actualizado")
                _cargar_todo()
                panel_niveles.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error editando nivel: %s", exc)
                toast_error("Error al actualizar nivel")

        form_dialog(
            titulo = "Editar nivel de desempeño",
            campos = [
                {"key": "nombre",      "label": "Nombre *",       "tipo": "text",   "valor": nivel.nombre, "requerido": True},
                {"key": "rango_min",   "label": "Rango mínimo *", "tipo": "number", "valor": nivel.rango_min, "min": 0, "max": 100, "step": 0.1},
                {"key": "rango_max",   "label": "Rango máximo *", "tipo": "number", "valor": nivel.rango_max, "min": 0, "max": 100, "step": 0.1},
                {"key": "descripcion", "label": "Descripción",    "tipo": "text",   "valor": nivel.descripcion or ""},
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    def _eliminar_nivel(nivel: NivelDesempeno) -> None:
        anio_id = _anio_id()
        if not anio_id:
            return

        def _ejecutar() -> None:
            try:
                restantes = [
                    NuevoNivelDesempenoDTO(
                        anio_id=anio_id, nombre=n.nombre,
                        rango_min=n.rango_min, rango_max=n.rango_max,
                        descripcion=n.descripcion, orden=i,
                    )
                    for i, n in enumerate([x for x in _s["niveles"] if x.id != nivel.id])
                ]
                Container.configuracion_service().configurar_niveles(anio_id, restantes)
                toast_success(f"Nivel '{nivel.nombre}' eliminado")
                _cargar_todo()
                panel_niveles.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error eliminando nivel: %s", exc)
                toast_error("Error al eliminar nivel")

        confirm_dialog(
            titulo          = "Eliminar nivel",
            mensaje         = f"¿Eliminar el nivel '{nivel.nombre}'? Esta acción es irreversible.",
            on_confirm      = _ejecutar,
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    # ── Acciones — criterios de promoción ─────────────────────────────────────
    def _editar_criterios() -> None:
        anio_id = _anio_id()
        if not anio_id:
            return
        criterios = _s["criterios"]

        def _guardar(datos: dict) -> None:
            try:
                nuevo = CriterioPromocion(
                    anio_id                  = anio_id,
                    max_asignaturas_perdidas  = int(datos.get("max_asignaturas_perdidas", 2)),
                    permite_condicionada      = bool(datos.get("permite_condicionada", True)),
                    nota_minima_habilitacion  = float(datos["nota_minima_habilitacion"]),
                    nota_minima_anual         = float(datos["nota_minima_anual"]),
                )
                Container.configuracion_service().guardar_criterios(nuevo)
                toast_success("Criterios de promoción guardados")
                _cargar_todo()
                panel_criterios.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error criterios: %s", exc)
                toast_error("Error al guardar criterios")

        form_dialog(
            titulo = "Criterios de promoción",
            campos = [
                {
                    "key": "max_asignaturas_perdidas",
                    "label": "Máx. asignaturas perdidas para promoción *",
                    "tipo": "number", "min": 0, "max": 10, "step": 1,
                    "valor": criterios.max_asignaturas_perdidas if criterios else 2,
                },
                {
                    "key": "permite_condicionada",
                    "label": "Permite promoción condicionada",
                    "tipo": "checkbox",
                    "valor": criterios.permite_condicionada if criterios else True,
                },
                {
                    "key": "nota_minima_habilitacion",
                    "label": "Nota mínima para habilitación *",
                    "tipo": "number", "min": 0, "max": 100, "step": 0.5,
                    "valor": criterios.nota_minima_habilitacion if criterios else 60.0,
                },
                {
                    "key": "nota_minima_anual",
                    "label": "Nota mínima anual requerida *",
                    "tipo": "number", "min": 0, "max": 100, "step": 0.5,
                    "valor": criterios.nota_minima_anual if criterios else 60.0,
                },
            ],
            on_submit = _guardar,
            max_width = "max-w-lg",
        )

    # ── Acciones — modo SIEE ──────────────────────────────────────────────────
    def _abrir_dialog_modo_siee() -> None:
        cfg    = _s["siee_cfg"]
        modo_v = cfg.modo.value if cfg else "libre"
        pct_v  = round((cfg.porcentaje_autonomia_docente or 0) * 100, 1) if cfg else 0.0

        def _guardar(datos: dict) -> None:
            anio_id = _anio_id()
            if not anio_id:
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
                toast_success("Configuración SIEE guardada")
                _cargar_todo()
                panel_modo_siee.refresh()
                panel_cats_inst.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error SIEE: %s", exc)
                toast_error("Error al guardar la configuración SIEE")

        form_dialog(
            titulo = "Configurar modo SIEE",
            campos = [
                {
                    "key": "modo", "label": "Modo de distribución",
                    "tipo": "select", "valor": modo_v,
                    "opciones": {k: v for k, v in _MODO_LABELS.items()},
                    "requerido": True,
                },
                {
                    "key": "porcentaje_autonomia",
                    "label": "% autonomía docente (solo modo mixto-autonomía)",
                    "tipo": "number", "valor": pct_v,
                    "min": 1, "max": 99, "step": 1,
                    "placeholder": "Ej: 30 (para 30%)",
                },
            ],
            on_submit = _guardar,
            max_width = "max-w-lg",
        )

    # ── Acciones — categorías institucionales ─────────────────────────────────
    def _crear_cat_institucional() -> None:
        anio_id = _anio_id()
        if not anio_id:
            return

        def _guardar(datos: dict) -> None:
            nombre  = str(datos.get("nombre", "")).strip()
            peso_v  = datos.get("peso")
            permite = bool(datos.get("permite_subcategorias", False))
            if not nombre:
                toast_warning("El nombre es obligatorio")
                return
            try:
                peso = float(peso_v) / 100.0
                dto  = NuevaCategoriaInstitucionalDTO(
                    nombre=nombre, peso=peso,
                    anio_id=anio_id, permite_subcategorias=permite,
                )
                Container.evaluacion_service().agregar_categoria_institucional(
                    dto, usuario_id=ctx.usuario_id
                )
                toast_success(f"Categoría '{nombre}' creada")
                _cargar_todo()
                panel_cats_inst.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error creando cat. institucional: %s", exc)
                toast_error("Error al crear la categoría")

        form_dialog(
            titulo = "Nueva categoría institucional",
            campos = [
                {"key": "nombre",  "label": "Nombre *", "tipo": "text", "requerido": True, "placeholder": "Ej: Saber"},
                {"key": "peso",    "label": "Porcentaje (1–100) *", "tipo": "number", "min": 1, "max": 100, "step": 1, "valor": 10},
                {"key": "permite_subcategorias", "label": "Permite sub-categorías docente", "tipo": "checkbox", "valor": False},
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    def _editar_cat_institucional(cat) -> None:
        anio_id = _anio_id()

        def _guardar(datos: dict) -> None:
            nuevo_nombre = str(datos.get("nombre", "")).strip() or None
            peso_v       = datos.get("peso")
            if not nuevo_nombre:
                toast_warning("El nombre es obligatorio")
                return
            try:
                nuevo_peso = float(peso_v) / 100.0 if peso_v is not None else None
                dto        = ActualizarCategoriaDTO(nombre=nuevo_nombre, peso=nuevo_peso)
                Container.evaluacion_service().actualizar_categoria_institucional(
                    cat.id, dto, anio_id, usuario_id=ctx.usuario_id
                )
                toast_success("Categoría actualizada")
                _cargar_todo()
                panel_cats_inst.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error actualizando cat. institucional: %s", exc)
                toast_error("Error al actualizar")

        form_dialog(
            titulo = "Editar categoría institucional",
            campos = [
                {"key": "nombre", "label": "Nombre *", "tipo": "text", "valor": cat.nombre, "requerido": True},
                {"key": "peso",   "label": "Porcentaje (1–100) *", "tipo": "number", "valor": round(cat.peso * 100, 1), "min": 1, "max": 100, "step": 1},
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
                toast_success(f"'{cat.nombre}' eliminada")
                _cargar_todo()
                panel_cats_inst.refresh()
            except (ValueError, RuntimeError) as exc:
                toast_warning(str(exc))
            except Exception as exc:
                logger.error("Error eliminando cat. institucional: %s", exc)
                toast_error("Error al eliminar")

        confirm_dialog(
            titulo          = "Eliminar categoría institucional",
            mensaje         = f"¿Eliminar '{cat.nombre}'? Esta acción es irreversible.",
            on_confirm      = _ejecutar,
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    # ── Secciones refreshables ────────────────────────────────────────────────

    @ui.refreshable
    def panel_anio() -> None:
        config = _s["config_activa"]
        with ui.element("div").classes("panel-card"):
            ui.label("Año lectivo activo").classes("eyebrow-label mb-2")
            if config:
                with ui.row().classes("items-center gap-4 mb-3"):
                    ui.label(str(config.anio)).classes("text-4xl font-bold")
                    badge_estado_general(True)
                with ui.element("div").classes("grid grid-cols-2 gap-3"):
                    _dato("Inicio clases",
                          config.fecha_inicio_clases.strftime("%d/%m/%Y") if config.fecha_inicio_clases else "—")
                    _dato("Fin clases",
                          config.fecha_fin_clases.strftime("%d/%m/%Y") if config.fecha_fin_clases else "—")
                    if config.duracion_semanas:
                        _dato("Duración", f"{config.duracion_semanas} semanas")
                ui.separator().classes("my-4")

            # Crear nuevo año
            ui.label("Crear nuevo año lectivo").classes("text-sm font-semibold mb-2")
            ui.label(
                "Al crear un nuevo año, este se convierte en el activo."
            ).classes("text-xs text-grey-6 mb-3")
            with ui.row().classes("gap-3 items-end"):
                ui.number(
                    "Año *", value=_s["nuevo_anio"], min=2000, max=2100, step=1,
                ).classes("w-32").bind_value(_s, "nuevo_anio")
                btn_primary("Crear año", on_click=_crear_anio, icon="add_circle")

    @ui.refreshable
    def panel_escala() -> None:
        config = _s["config_activa"]
        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center gap-2 mb-4"):
                ThemeManager.icono("straighten", size=24, color="var(--color-primary)")
                ui.label("Escala de notas").classes("text-lg font-bold flex-1")
                if config:
                    btn_secondary("Editar", icon="edit", on_click=_editar_escala)

            if not config:
                ui.label("Sin año activo.").classes("text-empty text-sm")
                return

            # Validación visual
            aprobacion_en_rango = (
                config.nota_minima_escala
                <= config.nota_minima_aprobacion
                <= config.nota_maxima_escala
            )

            with ui.element("div").classes("grid grid-cols-3 gap-4"):
                with ui.element("div").classes("flex-col items-center p-3 bg-grey-1 rounded text-center"):
                    ui.label("Mínima escala").classes("text-xs text-grey-6 mb-1")
                    ui.label(f"{config.nota_minima_escala:.1f}").classes("text-2xl font-bold")

                with ui.element("div").classes("flex-col items-center p-3 bg-grey-1 rounded text-center"):
                    ui.label("Nota de aprobación").classes("text-xs text-grey-6 mb-1")
                    color_ap = "text-green-700" if aprobacion_en_rango else "text-red-600"
                    ui.label(f"{config.nota_minima_aprobacion:.1f}").classes(f"text-2xl font-bold {color_ap}")

                with ui.element("div").classes("flex-col items-center p-3 bg-grey-1 rounded text-center"):
                    ui.label("Máxima escala").classes("text-xs text-grey-6 mb-1")
                    ui.label(f"{config.nota_maxima_escala:.1f}").classes("text-2xl font-bold")

            if not aprobacion_en_rango:
                with ui.row().classes("items-center gap-2 mt-3 p-2 bg-red-50 rounded text-red-700 text-sm"):
                    ThemeManager.icono("warning", size=24, color="var(--color-error)")
                    ui.label("La nota de aprobación está fuera del rango de la escala.")

    @ui.refreshable
    def panel_niveles() -> None:
        niveles   = _s["niveles"]
        anio_id   = _anio_id()

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center gap-2 mb-4"):
                ThemeManager.icono("grade", size=24, color="var(--color-primary)")
                ui.label("Niveles de desempeño").classes("text-lg font-bold flex-1")
                if anio_id:
                    btn_icon("refresh", on_click=lambda: (_cargar_todo(), panel_niveles.refresh()), tooltip="Recargar")
                    btn_ghost("Defaults", icon="restart_alt", on_click=_restablecer_niveles_default)
                    btn_primary("Agregar nivel", icon="add", on_click=_agregar_nivel)

            if not anio_id:
                ui.label("Sin año activo.").classes("text-empty text-sm")
                return

            if not niveles:
                with ui.element("div").classes("flex items-center gap-3 p-3 bg-info-soft rounded"):
                    ThemeManager.icono("info", size=24, color="var(--color-info)")
                    ui.label(
                        "No hay niveles definidos. Usa 'Defaults' para cargar los estándar "
                        "(Bajo, Básico, Alto, Superior)."
                    ).classes("text-sm text-blue-700 flex-1")
                return

            with ui.element("div").classes("w-full"):
                with ui.element("div").classes("flex gap-3 px-2 py-1 font-semibold text-xs text-grey-7 border-b"):
                    ui.label("Nombre").classes("w-28")
                    ui.label("Rango").classes("w-32")
                    ui.label("Descripción").classes("flex-1")
                    ui.label("").classes("w-20")

                for nivel in niveles:
                    with ui.element("div").classes("flex items-center gap-3 px-2 py-2 border-b"):
                        ui.label(nivel.nombre).classes("w-28 font-medium text-sm")
                        ui.label(f"{nivel.rango_min:.1f} – {nivel.rango_max:.1f}").classes(
                            "w-32 text-sm font-mono text-grey-7"
                        )
                        ui.label(nivel.descripcion or "—").classes("flex-1 text-sm text-grey-6")
                        with ui.row().classes("w-20 justify-end gap-1"):
                            btn_icon("edit",   on_click=lambda n=nivel: _editar_nivel(n),   tooltip="Editar")
                            btn_icon("delete", on_click=lambda n=nivel: _eliminar_nivel(n), tooltip="Eliminar", variante="danger")

    @ui.refreshable
    def panel_criterios() -> None:
        criterios = _s["criterios"]
        anio_id   = _anio_id()

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center gap-2 mb-4"):
                ThemeManager.icono("how_to_reg", size=24, color="var(--color-primary)")
                ui.label("Criterios de promoción").classes("text-lg font-bold flex-1")
                if anio_id:
                    label_btn = "Editar" if criterios else "Configurar"
                    btn_secondary(label_btn, icon="edit", on_click=_editar_criterios)

            if not anio_id:
                ui.label("Sin año activo.").classes("text-empty text-sm")
                return

            if not criterios:
                with ui.element("div").classes("flex items-center gap-3 p-3 bg-warning-soft rounded border-warning-soft"):
                    ThemeManager.icono("warning", size=24, color="var(--color-warning)")
                    ui.label(
                        "No hay criterios de promoción configurados. Haz clic en 'Configurar'."
                    ).classes("text-sm text-amber-700 flex-1")
                return

            with ui.element("div").classes("grid grid-cols-2 gap-4"):
                _dato("Máx. asignaturas perdidas", str(criterios.max_asignaturas_perdidas))
                _dato("Promoción condicionada", "Sí" if criterios.permite_condicionada else "No")
                _dato("Nota mínima habilitación", f"{criterios.nota_minima_habilitacion:.1f}")
                _dato("Nota mínima anual", f"{criterios.nota_minima_anual:.1f}")

    @ui.refreshable
    def panel_modo_siee() -> None:
        cfg        = _s["siee_cfg"]
        anio_id    = _anio_id()
        modo_val   = cfg.modo.value if cfg else "libre"
        modo_label = _MODO_LABELS.get(modo_val, modo_val)
        modo_desc  = _MODO_DESC.get(modo_val, "")

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center gap-3 mb-4"):
                ThemeManager.icono("tune", size=24, color="var(--color-primary)")
                ui.label("Modo SIEE").classes("text-lg font-bold flex-1")
                _variante_modo = {
                    "libre":               "neutral",
                    "institucional_fijo":  "error",
                    "mixto_subcategorias": "info",
                    "mixto_autonomia":     "warning",
                }.get(modo_val, "neutral")
                status_badge(modo_label, variante=_variante_modo)
                if anio_id:
                    btn_secondary("Cambiar modo", icon="tune", on_click=_abrir_dialog_modo_siee)

            with ui.element("div").classes("bg-info-soft rounded p-3 mb-3 text-sm text-blue-800"):
                ui.label(modo_desc)

            if modo_val == "mixto_autonomia" and cfg and cfg.porcentaje_autonomia_docente:
                pct_inst = round((1.0 - cfg.porcentaje_autonomia_docente) * 100, 1)
                pct_doc  = round(cfg.porcentaje_autonomia_docente * 100, 1)
                with ui.row().classes("gap-4 text-sm"):
                    ui.label(f"Institucional: {pct_inst}%").classes("font-medium")
                    ui.label(f"Autonomía docente: {pct_doc}%").classes("font-medium text-primary")

    @ui.refreshable
    def panel_cats_inst() -> None:
        cats_inst  = _s["cats_inst"]
        anio_id    = _anio_id()
        suma_inst  = round(sum(c.peso for c in cats_inst) * 100, 1)

        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center gap-3 mb-4"):
                ThemeManager.icono("category", size=24, color="var(--color-primary)")
                ui.label("Categorías institucionales").classes("text-lg font-bold flex-1")
                ui.badge(f"{suma_inst:.0f}%").classes(
                    "badge-success" if suma_inst <= 100 else "badge-error"
                )
                if anio_id:
                    btn_icon("add_circle", on_click=_crear_cat_institucional, tooltip="Agregar categoría institucional")

            if not anio_id:
                ui.label("Sin año activo.").classes("text-empty text-sm")
                return

            if not cats_inst:
                ui.label("No hay categorías institucionales definidas.").classes("text-empty text-sm")
                return

            with ui.element("div").classes("w-full divider-y"):
                for cat in cats_inst:
                    with ui.row().classes("items-center gap-3 py-2"):
                        ThemeManager.icono("lock", size=20)
                        ui.label(cat.nombre).classes("flex-1 text-sm font-medium")
                        ui.label(f"{cat.peso_porcentaje:.1f}%").classes("text-sm font-mono w-14 text-right")
                        if cat.permite_subcategorias:
                            status_badge("sub-cats", variante="info")
                        with ui.row().classes("gap-1"):
                            btn_icon("edit",   on_click=lambda c=cat: _editar_cat_institucional(c), tooltip="Editar")
                            btn_icon("delete", on_click=lambda c=cat: _eliminar_cat_institucional(c), tooltip="Eliminar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            # Header
            with ui.element("div").classes("panel-card mb-0"):
                with ui.row().classes("items-center gap-2"):
                    ThemeManager.icono("school", size=22, color="var(--color-primary)")
                    ui.label("Configuración SIEE").classes("text-xl font-bold flex-1")
                    btn_ghost("Info. Institucional", icon="business",
                              on_click=lambda: ui.navigate.to("/admin/configuracion-institucion"))
                    btn_icon("refresh", on_click=lambda: (_cargar_todo(),
                             panel_anio.refresh(), panel_escala.refresh(),
                             panel_niveles.refresh(), panel_criterios.refresh(),
                             panel_modo_siee.refresh(), panel_cats_inst.refresh()),
                             tooltip="Recargar todo")

            panel_anio()

            if _s["config_activa"]:
                with ui.element("div").classes("grid-2-lg mt-4"):
                    panel_escala()
                    panel_criterios()

                with ui.element("div").classes("mt-4"):
                    panel_niveles()

                with ui.element("div").classes("mt-4"):
                    panel_modo_siee()

                with ui.element("div").classes("mt-4"):
                    panel_cats_inst()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Configuración SIEE",
        page_subtitulo = "Escala, niveles de desempeño, criterios de promoción y categorías institucionales",
        page_icono     = "school",
    )


def _dato(label: str, valor: str) -> None:
    with ui.element("div").classes("flex-col"):
        ui.label(label).classes("text-xs text-grey-6")
        ui.label(valor).classes("text-sm font-medium")


__all__ = ["configuracion_sie_page"]
