"""
src/interface/pages/admin/salas.py
====================================
Página de administración de salas físicas.
Ruta: /admin/salas
Acceso: admin, director
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
    confirm_dialog,
    form_dialog,
    toast_error,
    toast_success,
    toast_warning,
)
from src.services.infraestructura_service import Sala

logger = logging.getLogger("ADMIN.SALAS")

_TIPOS_SALA = {
    "aula":        "Aula",
    "laboratorio": "Laboratorio",
    "computo":     "Sala de Cómputo",
    "ed_fisica":   "Ed. Física / Cancha",
    "otro":        "Otro",
}


@ui.page("/admin/salas")
def salas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    logger.info("Salas admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "salas":     [],
        "grupos":    [],
        "nombre":    "",
        "tipo":      "aula",
        "capacidad": 30,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_salas() -> None:
        try:
            _s["salas"] = Container.infraestructura_service().listar_salas()
        except Exception as exc:
            logger.error("Error cargando salas: %s", exc)
            _s["salas"] = []

    def _cargar_grupos() -> None:
        try:
            _s["grupos"] = sorted(
                Container.infraestructura_service().listar_grupos(),
                key=lambda g: g.codigo,
            )
        except Exception as exc:
            logger.error("Error cargando grupos: %s", exc)
            _s["grupos"] = []

    _cargar_salas()
    _cargar_grupos()

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def _crear_sala() -> None:
        try:
            nombre = str(_s["nombre"]).strip()
            if not nombre:
                toast_warning("El nombre de la sala no puede estar vacío")
                return
            sala = Sala(
                nombre=nombre,
                tipo=_s["tipo"] or "aula",
                capacidad=int(_s["capacidad"] or 30),
            )
            Container.infraestructura_service().crear_sala(sala)
            toast_success(f"Sala '{nombre}' creada")
            _s["nombre"]    = ""
            _s["tipo"]      = "aula"
            _s["capacidad"] = 30
            _cargar_salas()
            tabla_salas.refresh()
            tabla_grupos_aula.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al crear sala: %s", exc)
            toast_error("Error al crear la sala")

    def _confirmar_eliminar_sala(sala_id: int, nombre: str) -> None:
        try:
            Container.infraestructura_service().eliminar_sala(sala_id)
            toast_success(f"Sala '{nombre}' eliminada")
            _cargar_salas()
            _cargar_grupos()
            tabla_salas.refresh()
            tabla_grupos_aula.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al eliminar sala %s: %s", sala_id, exc)
            toast_error("Error al eliminar la sala")

    def _eliminar_sala(sala_id: int, nombre: str) -> None:
        confirm_dialog(
            titulo          = "Eliminar sala",
            mensaje         = f"¿Eliminar la sala '{nombre}'? Esta acción es irreversible.",
            on_confirm      = lambda: _confirmar_eliminar_sala(sala_id, nombre),
            variante        = "danger",
            texto_confirmar = "Eliminar",
        )

    def _editar_sala(sala: Sala) -> None:
        def _guardar(datos: dict) -> "bool | None":
            try:
                nombre = str(datos.get("nombre", "")).strip()
                if not nombre:
                    toast_warning("El nombre es obligatorio")
                    return False
                sala_act = Sala(
                    id=sala.id,
                    nombre=nombre,
                    tipo=datos.get("tipo") or "aula",
                    capacidad=int(datos.get("capacidad") or 1),
                )
                Container.infraestructura_service().actualizar_sala(sala_act)
                toast_success(f"Sala '{sala_act.nombre}' actualizada")
                _cargar_salas()
                tabla_salas.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al actualizar sala: %s", exc)
                toast_error("Error al actualizar la sala")
                return False

        form_dialog(
            titulo = "Editar sala",
            campos = [
                {"key": "nombre",    "label": "Nombre *",  "tipo": "text",
                 "valor": sala.nombre, "requerido": True},
                {"key": "tipo",      "label": "Tipo",      "tipo": "select",
                 "valor": sala.tipo,   "opciones": _TIPOS_SALA},
                {"key": "capacidad", "label": "Capacidad", "tipo": "number",
                 "valor": sala.capacidad, "min": 1},
            ],
            on_submit = _guardar,
            max_width = "max-w-md",
        )

    # ── Tabla refreshable ─────────────────────────────────────────────────────
    @ui.refreshable
    def tabla_salas() -> None:
        salas = _s["salas"]
        if not salas:
            ui.label("No hay salas registradas.").classes("text-empty mt-2")
            return
        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-4 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Nombre").classes("flex-1")
                ui.label("Tipo").classes("w-36")
                ui.label("Capacidad").classes("w-24")
                ui.label("Acciones").classes("w-24 text-right")
            for s in salas:
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    ui.label(s.nombre).classes("flex-1 font-medium")
                    ui.label(_TIPOS_SALA.get(s.tipo, s.tipo)).classes("w-36 text-sm")
                    ui.label(str(s.capacidad)).classes("w-24 text-sm")
                    with ui.row().classes("w-24 gap-1 justify-end"):
                        btn_icon(
                            "edit",
                            on_click=lambda sala=s: _editar_sala(sala),
                            tooltip="Editar",
                        )
                        btn_icon(
                            "delete",
                            on_click=lambda sid=s.id, nom=s.nombre: _eliminar_sala(sid, nom),
                            tooltip="Eliminar",
                            variante="danger",
                        )

    # ── Aula propia por grupo ─────────────────────────────────────────────────
    def _asignar_aula(grupo_id: int, sala_id: int | None) -> None:
        try:
            Container.infraestructura_service().asignar_sala_a_grupo(grupo_id, sala_id)
            toast_success("Aula del grupo actualizada")
        except Exception as exc:
            logger.error("Error asignando aula a grupo %s: %s", grupo_id, exc)
            toast_error("No se pudo asignar el aula")
        finally:
            _cargar_grupos()
            tabla_grupos_aula.refresh()

    @ui.refreshable
    def tabla_grupos_aula() -> None:
        grupos = _s["grupos"]
        if not grupos:
            ui.label("No hay grupos registrados.").classes("text-empty mt-2")
            return
        sala_opts = {0: "— Sin asignar —"}
        sala_opts.update({s.id: s.nombre for s in _s["salas"]})
        with ui.element("div").classes("w-full"):
            with ui.element("div").classes("flex gap-4 p-2 font-semibold text-sm border-b"):
                ui.label("Grupo").classes("w-40")
                ui.label("Aula propia (salón base)").classes("flex-1")
            for g in grupos:
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    with ui.element("div").classes("w-40"):
                        ui.label(g.codigo).classes("font-medium")
                        if g.nombre:
                            ui.label(g.nombre).classes("text-xs text-secondary")
                    ui.select(
                        sala_opts,
                        value=g.sala_id if g.sala_id in sala_opts else 0,
                        on_change=lambda e, gid=g.id: _asignar_aula(gid, e.value or None),
                    ).classes("flex-1").props("dense outlined")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ThemeManager.icono("meeting_room", size=20, color="var(--color-primary)")
                    ui.label("Salas físicas").classes("text-lg font-bold")

                ui.label("Nueva sala").classes("text-sm font-semibold mb-1")
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input("Nombre *", placeholder="Sala 101").classes("w-48").bind_value(
                        _s, "nombre"
                    )
                    ui.select(
                        _TIPOS_SALA, label="Tipo"
                    ).classes("w-40").bind_value(_s, "tipo")
                    ui.number("Capacidad", min=1).classes("w-24").bind_value(
                        _s, "capacidad"
                    )
                    btn_primary("Crear sala", icon="add", on_click=_crear_sala)

                ui.separator().classes("my-3")
                tabla_salas()

            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ThemeManager.icono("groups", size=20, color="var(--color-primary)")
                    ui.label("Aula por grupo").classes("text-lg font-bold")
                ui.label(
                    "Asigna el salón base de cada grupo. El generador ubicará allí las "
                    "clases que no requieran una sala especial (laboratorio, cómputo…)."
                ).classes("text-caption text-secondary mb-2")
                tabla_grupos_aula()

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Gestión de Salas",
        page_subtitulo = "Espacios físicos disponibles para asignación de clases",
        page_icono     = "meeting_room",
    )


__all__ = ["salas_page"]
