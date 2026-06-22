"""
src/interface/pages/admin/diagnostico.py
=========================================
Página de herramientas de plataforma (admin). Dos bloques:

  1. Diagnóstico del Container — instancia todos los servicios y reporta
     OK / ERROR por componente (Container.diagnostico()).
  2. Lanzador "Ver como…" — selector de doble filtrado (institución → usuario)
     que inicia el modo de impersonación solo lectura. Reubicado desde el
     dashboard (inicio.py) en paso_38.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.
  Solo usa Container (servicios) e imports de la capa de interfaz.
  La autorización (admin-only) la aplica el wrapper de ruta (registrar_pagina).

Refreshables:
  ninguno — la página es estática (snapshot del Container + diálogo modal).
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import form_dialog
from src.interface.design.components.buttons import btn_primary
from src.interface.design.components.status_badge import status_badge
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons

logger = logging.getLogger("DIAGNOSTICO")


# ── "Ver como" — etiquetas de rol (reubicado desde inicio.py) ─────────────────
_ROLES_LABEL = {
    "admin":       "Administradores",
    "director":    "Directores",
    "coordinador": "Coordinadores",
    "profesor":    "Profesores",
}


def _abrir_selector_ver_como(ctx: SessionContext) -> None:
    """
    Selector 'Ver como' de doble filtrado (institución → usuario),
    preparado para multi-tenant.

    Nivel 1 — Institución: hoy single-tenant, una sola opción = la institución
    activa (config). Se construye como un dict de opciones (no se quema el
    literal de la única institución) para que añadir tenants sea natural.

    Nivel 2 — Usuario: lista filtrada por la institución elegida vía el hook de
    scope `usuario_service.listar_para_ver_como(institucion_id=...)` (no-op en
    single-tenant). Se excluye al propio admin.
    """
    from src.interface.design.components import toast_success, toast_warning, toast_error

    # ── Nivel 1: institución activa (multi-tenant-ready) ────────────────────
    institucion_id: int | None = None
    institucion_opciones: dict = {}
    try:
        config = Container.configuracion_service().get_activa(ctx.institucion_id)
        institucion_id = getattr(config, "id", None)
        nombre_inst = getattr(config, "nombre_institucion", "Institución")
        # Clave estable aunque id sea None (single-tenant sin id persistido).
        clave_inst = institucion_id if institucion_id is not None else 0
        institucion_opciones[clave_inst] = nombre_inst
    except Exception as e:
        logger.warning("Error al obtener la institución activa para 'Ver como': %s", e)
        institucion_opciones = {0: "Institución activa"}

    institucion_preseleccionada = next(iter(institucion_opciones), 0)

    # ── Nivel 2: usuarios filtrados por la institución elegida ──────────────
    try:
        usuarios = Container.usuario_service().listar_para_ver_como(
            institucion_id=institucion_id
        )
    except Exception as e:
        logger.warning("Error al listar usuarios para 'Ver como': %s", e)
        usuarios = []

    candidatos = [u for u in usuarios if u.id != ctx.usuario_id]
    if not candidatos:
        toast_warning("No hay otros usuarios para ver como")
        return

    _index = {}
    usuario_opciones: dict = {}
    for u in candidatos:
        rol_str = u.rol.value if hasattr(u.rol, "value") else str(u.rol)
        usuario_opciones[u.id] = f"{u.nombre_completo} · {_ROLES_LABEL.get(rol_str, rol_str)}"
        _index[u.id] = (u.nombre_completo, rol_str)

    def _aplicar(datos: dict) -> "bool | None":
        uid = datos.get("usuario_id")
        if uid is None:
            toast_warning("Selecciona un usuario")
            return False
        nombre, rol_str = _index.get(uid, ("usuario", "profesor"))
        try:
            ctx.iniciar_ver_como(
                target_usuario_id=uid,
                target_rol=rol_str,
                target_nombre=nombre,
            )
            toast_success(f"Viendo como '{nombre}' (solo lectura)")
            ui.navigate.to("/inicio")
        except Exception as e:
            logger.error("Error al iniciar 'Ver como': %s", e)
            toast_error("No se pudo iniciar el modo 'Ver como'")
            return False

    form_dialog(
        titulo="Ver como…",
        campos=[
            {"key": "institucion_id", "label": "Institución",
             "tipo": "select", "opciones": institucion_opciones,
             "valor": institucion_preseleccionada},
            {"key": "usuario_id", "label": "Usuario a impersonar (solo lectura) *",
             "tipo": "select", "opciones": usuario_opciones, "requerido": True},
        ],
        on_submit=_aplicar,
        texto_submit="Ver como",
        max_width="max-w-md",
    )


# ── Secciones de UI ───────────────────────────────────────────────────────────

def _seccion_ver_como(ctx: SessionContext) -> None:
    """Lanzador del selector 'Ver como' (impersonación solo lectura)."""
    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono("visibility", size=20, color="var(--color-primary)")
            ui.label("Ver como…").classes("panel-title")

        ui.label(
            "Impersona a otro usuario en modo solo lectura para diagnosticar "
            "su vista. La sesión real no se modifica."
        ).classes("text-hint")

        with ui.element("div").classes("action-text-col"):
            btn_primary(
                "Ver como…",
                on_click=lambda: _abrir_selector_ver_como(ctx),
                icon="visibility",
            )


def _seccion_container(resultado: dict) -> None:
    """Estado por servicio del Container: OK / ERROR con badges del design system."""
    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono("monitor_heart", size=20, color="var(--color-primary)")
            ui.label("Diagnóstico del Container").classes("panel-title")

        if not resultado:
            ui.label("Sin componentes que diagnosticar").classes("text-empty")
            return

        total = len(resultado)
        ok = sum(1 for estado in resultado.values() if estado == "OK")
        errores = total - ok

        if errores == 0:
            status_badge(f"{ok}/{total} servicios OK", "success")
        else:
            status_badge(f"{errores} con error · {ok}/{total} OK", "error")

        for nombre, estado in resultado.items():
            es_ok = estado == "OK"
            with ui.element("div").classes("hito-item"):
                if es_ok:
                    ThemeManager.icono(
                        "check_circle", size=18, color="var(--color-success)"
                    )
                else:
                    ThemeManager.icono(
                        "error", size=18, color="var(--color-error)"
                    )
                with ui.element("div").classes("hito-text-col"):
                    ui.label(nombre).classes("hito-desc")
                    if not es_ok:
                        ui.label(str(estado)).classes("hito-date")
                status_badge("OK", "success") if es_ok else status_badge("Error", "error")


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (paso_35/paso_38).
def diagnostico_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Diagnóstico/herramientas admin: %s", ctx.usuario_nombre)

    try:
        resultado = Container.diagnostico()
    except Exception as e:
        logger.error("Container.diagnostico() falló: %s", e)
        resultado = {}

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            _seccion_ver_como(ctx)
            _seccion_container(resultado)

    app_layout(
        ctx,
        contenido,
        page_titulo="Diagnóstico",
        page_subtitulo="Herramientas de plataforma",
        page_icono="monitor_heart",
        mostrar_contexto=False,
    )


__all__ = ["diagnostico_page"]
