"""
src/interface/pages/admin/asignaturas.py
=========================================
Página de administración de asignaturas y áreas de conocimiento.
Ruta: /admin/asignaturas
Acceso: admin, director

Permite:
 - CRUD de áreas de conocimiento.
 - CRUD de asignaturas filtradas por área.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_icon
from src.interface.design.components import (
    confirm_dialog, empty_state, form_dialog, pipeline_nav,
    toast_error, toast_success, toast_warning,
)
from src.services.infraestructura_service import AreaConocimiento, Asignatura

logger = logging.getLogger("ADMIN.ASIGNATURAS")

# Flujo de configuración del generador de horarios.
_PASOS_HORARIO = [
    ("asignaturas",  "Asignaturas",      "/admin/asignaturas"),
    ("plan",         "Plan de estudios", "/admin/plan-estudios"),
    ("asignaciones", "Asignaciones",     "/admin/asignaciones"),
    ("horarios",     "Horarios",         "/horarios"),
]


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def asignaturas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Asignaturas admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "areas":              [],
        "asignaturas":        [],
        "area_filtro_id":     None,
        "busqueda":           "",
        # formulario área
        "area_nombre":        "",
        "area_codigo":        "",
        # formulario asignatura
        "asig_nombre":        "",
        "asig_codigo":        "",
        "asig_area_id":       None,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_areas() -> None:
        try:
            _s["areas"] = Container.infraestructura_service().listar_areas()
        except Exception as exc:
            logger.error("Error al cargar áreas: %s", exc)
            _s["areas"] = []

    def _cargar_asignaturas() -> None:
        try:
            area_id = _s["area_filtro_id"] if _s["area_filtro_id"] else None
            _s["asignaturas"] = Container.infraestructura_service().listar_asignaturas(
                area_id=area_id
            )
        except Exception as exc:
            logger.error("Error al cargar asignaturas: %s", exc)
            _s["asignaturas"] = []

    _cargar_areas()
    _cargar_asignaturas()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _nombre_area(area_id) -> str:
        for a in _s["areas"]:
            if a.id == area_id:
                return a.nombre
        return "—"

    # ── CRUD Áreas ────────────────────────────────────────────────────────────
    def _crear_area() -> None:
        # AreaConocimiento valida nombre (no vacío) y normaliza el código.
        try:
            area = AreaConocimiento(
                id=None,
                nombre=_s["area_nombre"],
                codigo=_s["area_codigo"],
            )
            Container.infraestructura_service().guardar_area(area)
            toast_success(f"Área '{area.nombre}' creada")
            _s["area_nombre"] = ""
            _s["area_codigo"] = ""
            _cargar_areas()
            _cargar_asignaturas()
            tabla_areas.refresh()
            filtro_area.refresh()
            tabla_asignaturas.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al crear área: %s", exc)
            toast_error("Error al crear el área")

    def _confirmar_eliminar_area(area_id: int, nombre: str) -> None:
        try:
            Container.infraestructura_service().eliminar_area(area_id)
            toast_success(f"Área '{nombre}' eliminada")
            _cargar_areas()
            _cargar_asignaturas()
            tabla_areas.refresh()
            filtro_area.refresh()
            tabla_asignaturas.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al eliminar área %s: %s", area_id, exc)
            toast_error("Error al eliminar el área")

    def _eliminar_area(area_id: int, nombre: str) -> None:
        confirm_dialog(
            titulo          = "Eliminar área",
            mensaje         = f"¿Eliminar el área '{nombre}'? Esta acción es irreversible.",
            on_confirm      = lambda: _confirmar_eliminar_area(area_id, nombre),
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    def _editar_area(area: AreaConocimiento) -> None:
        def _guardar(datos: dict) -> "bool | None":
            # AreaConocimiento valida nombre y normaliza el código.
            try:
                area_act = AreaConocimiento(
                    id=area.id,
                    nombre=datos.get("nombre", ""),
                    codigo=datos.get("codigo"),
                )
                Container.infraestructura_service().actualizar_area(area_act)
                toast_success(f"Área '{area_act.nombre}' actualizada")
                _cargar_areas()
                _cargar_asignaturas()
                tabla_areas.refresh()
                filtro_area.refresh()
                tabla_asignaturas.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al actualizar área: %s", exc)
                toast_error("Error al actualizar el área")
                return False

        form_dialog(
            titulo    = "Editar área",
            campos    = [
                {"key": "nombre", "label": "Nombre *", "tipo": "text",
                 "valor": area.nombre, "requerido": True},
                {"key": "codigo", "label": "Código",   "tipo": "text",
                 "valor": area.codigo or ""},
            ],
            on_submit    = _guardar,
            max_width    = "max-w-md",
        )

    # ── CRUD Asignaturas ──────────────────────────────────────────────────────
    def _crear_asignatura() -> None:
        # Asignatura valida nombre y normaliza el código. Las horas por grado se
        # definen en Plan de estudios (las globales quedan como fallback = 1).
        try:
            asig = Asignatura(
                id=None,
                nombre=_s["asig_nombre"],
                codigo=_s["asig_codigo"],
                area_id=_s["asig_area_id"] or None,
            )
            Container.infraestructura_service().guardar_asignatura(asig)
            toast_success(f"Asignatura '{asig.nombre}' creada")
            _s["asig_nombre"]  = ""
            _s["asig_codigo"]  = ""
            _s["asig_area_id"] = None
            _cargar_asignaturas()
            tabla_asignaturas.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al crear asignatura: %s", exc)
            toast_error("Error al crear la asignatura")

    def _confirmar_eliminar_asig(asig_id: int, nombre: str) -> None:
        try:
            Container.infraestructura_service().eliminar_asignatura(asig_id)
            toast_success(f"Asignatura '{nombre}' eliminada")
            _cargar_asignaturas()
            tabla_asignaturas.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al eliminar asignatura %s: %s", asig_id, exc)
            toast_error("Error al eliminar la asignatura")

    def _eliminar_asignatura(asig_id: int, nombre: str) -> None:
        confirm_dialog(
            titulo          = "Eliminar asignatura",
            mensaje         = f"¿Eliminar la asignatura '{nombre}'? Esta acción es irreversible.",
            on_confirm      = lambda: _confirmar_eliminar_asig(asig_id, nombre),
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    def _editar_asignatura(asig: Asignatura) -> None:
        areas_dict = {a.id: a.nombre for a in _s["areas"]}

        def _guardar(datos: dict) -> "bool | None":
            try:
                # Reconstruir vía constructor para re-validar (model_copy no dispara
                # validadores); conserva horas/tipo_sala/bloque_doble del registro.
                asig_act = Asignatura(**{
                    **asig.model_dump(),
                    "nombre": datos.get("nombre", ""),
                    "codigo": datos.get("codigo"),
                    "area_id": datos.get("area_id") or None,
                })
                Container.infraestructura_service().actualizar_asignatura(asig_act)
                toast_success(f"Asignatura '{asig_act.nombre}' actualizada")
                _cargar_asignaturas()
                tabla_asignaturas.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al actualizar asignatura: %s", exc)
                toast_error("Error al actualizar la asignatura")
                return False

        form_dialog(
            titulo    = "Editar asignatura",
            campos    = [
                {"key": "nombre", "label": "Nombre *", "tipo": "text",
                 "valor": asig.nombre, "requerido": True},
                {"key": "codigo", "label": "Código", "tipo": "text",
                 "valor": asig.codigo or ""},
                {"key": "area_id", "label": "Área", "tipo": "select",
                 "valor": asig.area_id, "opciones": areas_dict},
            ],
            on_submit    = _guardar,
            max_width    = "max-w-md",
        )

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def filtro_area() -> None:
        areas_opts = {None: "Todas las áreas"}
        for a in _s["areas"]:
            areas_opts[a.id] = a.nombre

        def _on_filtro_change(v) -> None:
            _s["area_filtro_id"] = v
            _cargar_asignaturas()
            tabla_asignaturas.refresh()

        ui.select(
            areas_opts,
            value=_s["area_filtro_id"],
            label="Filtrar por área",
            on_change=lambda e: _on_filtro_change(e.value),
        ).classes("w-56")

        def _on_buscar(v) -> None:
            _s["busqueda"] = (v or "").strip().lower()
            tabla_asignaturas.refresh()

        ui.input(
            placeholder="Buscar por nombre o código…",
            value=_s["busqueda"],
            on_change=lambda e: _on_buscar(e.value),
        ).props("dense outlined clearable debounce=250").classes("w-64")

    @ui.refreshable
    def tabla_areas() -> None:
        areas = _s["areas"]
        if not areas:
            empty_state(
                titulo="No hay áreas registradas",
                descripcion="Crea la primera área con el formulario de arriba.",
            )
            return
        for a in areas:
            with ui.element("div").classes("lista-fila"):
                ui.label(a.nombre).classes("flex-1 font-medium")
                if a.codigo:
                    ui.badge(a.codigo).classes("badge-neutral")
                with ui.row().classes("gap-1 ml-auto"):
                    btn_icon("edit", on_click=lambda area=a: _editar_area(area), tooltip="Editar")
                    btn_icon("delete", on_click=lambda aid=a.id, nom=a.nombre: _eliminar_area(aid, nom), tooltip="Eliminar", variante="danger")

    @ui.refreshable
    def tabla_asignaturas() -> None:
        asigs = _s["asignaturas"]
        q = _s["busqueda"]
        if q:
            asigs = [
                a for a in asigs
                if q in a.nombre.lower() or q in (a.codigo or "").lower()
            ]
        if not asigs:
            if q:
                empty_state(
                    variante="search",
                    titulo="Sin coincidencias",
                    descripcion="No hay asignaturas que coincidan con la búsqueda.",
                )
            else:
                empty_state(
                    titulo="No hay asignaturas en esta área",
                    descripcion="Crea una asignatura con el formulario de arriba.",
                )
            return
        with ui.element("div").classes("w-full"):
            with ui.element("div").classes("lista-head"):
                ui.label("Nombre").classes("flex-1")
                ui.label("Código").classes("w-24")
                ui.label("Área").classes("w-44")
                ui.label("Acciones").classes("w-24 text-right")
            for a in asigs:
                with ui.element("div").classes("lista-fila"):
                    ui.label(a.nombre).classes("flex-1")
                    ui.label(a.codigo or "—").classes("w-24 font-mono text-sm")
                    ui.label(_nombre_area(a.area_id)).classes("w-44 text-sm")
                    with ui.row().classes("w-24 gap-1 justify-end"):
                        btn_icon("edit", on_click=lambda asig=a: _editar_asignatura(asig), tooltip="Editar")
                        btn_icon("delete", on_click=lambda aid=a.id, nom=a.nombre: _eliminar_asignatura(aid, nom), tooltip="Eliminar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            pipeline_nav(
                _PASOS_HORARIO, activo="asignaturas",
                hint="Paso 1 · Define las materias (nombre, código, área). "
                     "Las horas de cada una se asignan por grado en «Plan de estudios».",
            )

            # ── Sección: Áreas de conocimiento ───────────────────────────────
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ThemeManager.icono("category", size=20, color="var(--color-info)")
                    ui.label("Áreas de conocimiento").classes("text-lg font-bold")

                ui.label("Nueva área").classes("text-sm font-semibold mb-1")
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input("Nombre *", placeholder="Matemáticas").classes("w-48").bind_value(
                        _s, "area_nombre"
                    )
                    ui.input("Código", placeholder="MAT").classes("w-28").bind_value(
                        _s, "area_codigo"
                    )
                    btn_primary("Crear área", on_click=_crear_area, icon="add")

                ui.separator().classes("my-3")
                tabla_areas()

            # ── Sección: Asignaturas ─────────────────────────────────────────
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-2 mb-3 flex-wrap"):
                    ThemeManager.icono(Icons.GRADES, size=20, color="var(--color-primary)")
                    ui.label("Asignaturas").classes("text-lg font-bold")
                    filtro_area()
                    btn_icon("refresh", on_click=lambda: (
                        _cargar_areas(),
                        _cargar_asignaturas(),
                        tabla_areas.refresh(),
                        filtro_area.refresh(),
                        tabla_asignaturas.refresh(),
                    ), tooltip="Recargar")

                ui.label("Nueva asignatura").classes("text-sm font-semibold mb-1")
                ui.label(
                    "Las horas de cada asignatura se definen por grado en «Plan de estudios»."
                ).classes("text-caption text-secondary mb-1")
                areas_opts = {a.id: a.nombre for a in _s["areas"]}
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input("Nombre *", placeholder="Álgebra").classes("w-48").bind_value(
                        _s, "asig_nombre"
                    )
                    ui.input("Código", placeholder="ALG").classes("w-28").bind_value(
                        _s, "asig_codigo"
                    )
                    ui.select(
                        areas_opts,
                        label="Área",
                    ).classes("w-44").bind_value(_s, "asig_area_id")
                    btn_primary("Crear asignatura", on_click=_crear_asignatura, icon="add")

                ui.separator().classes("my-3")
                tabla_asignaturas()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Gestión de Asignaturas",
        page_subtitulo = "Áreas de conocimiento y asignaturas del currículo",
        page_icono     = Icons.SUBJECTS,
        mostrar_contexto = False,
    )


__all__ = ["asignaturas_page"]
