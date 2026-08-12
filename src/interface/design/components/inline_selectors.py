"""
inline_selectors.py — Pills de selección en cascada (periodo / grupo / asignatura).

Dos funciones públicas:
  inline_periodo_grupo_asignatura(s, on_change, usuario_id, institucion_id,
                                  usuario_rol, preselect_periodo=True)
  inline_periodo_grupo(s, on_change, institucion_id, preselect_periodo=True)

Las funciones modifican `s` in-place con las claves:
  sel_periodo_id / sel_periodo_nombre
  sel_grupo_id / sel_grupo_nombre
  sel_asignacion_id / sel_asignacion_nombre  (solo en la versión 3D)

`on_change(s)` se llama cuando la selección está completa (todas las
dimensiones requeridas tienen valor).

Restricciones de arquitectura:
  - Solo vía Container (nunca import directo de src.domain ni src.infrastructure).
  - No escribe a SessionContext.
  - No usa ui.select — los pills son ui.button + ui.menu.
  - No usa ui.icon() — icono vía ThemeManager.icono().
  - No CSS inline — todo en styles/components/inline_selectors.css.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from nicegui import ui

from container import Container
from src.interface.design.theme import ThemeManager

logger = logging.getLogger("INLINE_SELECTORS")


# ─── Lógica pura (testeable sin NiceGUI) ─────────────────────────────────────

def _estado_inicial(s: dict) -> None:
    """
    Garantiza que las claves de selección existen en s.
    No sobrescribe valores existentes.
    """
    defaults: dict = {
        "sel_periodo_id": None,
        "sel_periodo_nombre": "",
        "sel_grupo_id": None,
        "sel_grupo_nombre": "",
        "sel_asignacion_id": None,
        "sel_asignacion_nombre": "",
    }
    for k, v in defaults.items():
        if k not in s:
            s[k] = v


def _preseleccionar_periodo(s: dict, institucion_id: int) -> None:
    """
    Carga periodos del año en curso y pre-selecciona el primero con
    activo=True y no cerrado.
    Si no hay ninguno, no modifica s.
    """
    try:
        config = Container.configuracion_service().get_activa(institucion_id)
        anio_id = getattr(config, "id", None) if config else None
        if not anio_id:
            return
        periodos = Container.periodo_service().listar_por_anio(anio_id)
        primer_abierto = next(
            (p for p in periodos if p.activo and not p.cerrado),
            None,
        )
        if primer_abierto is not None:
            s["sel_periodo_id"] = primer_abierto.id
            s["sel_periodo_nombre"] = primer_abierto.nombre
    except Exception as exc:
        logger.warning("Error pre-seleccionando periodo: %s", exc)


def _on_periodo_cambio(s: dict, periodo_id: int, periodo_nombre: str) -> None:
    """Establece el periodo y limpia cascada (grupo + asignación)."""
    s["sel_periodo_id"] = periodo_id
    s["sel_periodo_nombre"] = periodo_nombre
    s["sel_grupo_id"] = None
    s["sel_grupo_nombre"] = ""
    s["sel_asignacion_id"] = None
    s["sel_asignacion_nombre"] = ""


def _on_grupo_cambio(s: dict, grupo_id: int, grupo_nombre: str) -> None:
    """Establece el grupo y limpia asignación."""
    s["sel_grupo_id"] = grupo_id
    s["sel_grupo_nombre"] = grupo_nombre
    s["sel_asignacion_id"] = None
    s["sel_asignacion_nombre"] = ""


def _on_asignacion_cambio(s: dict, asig_id: int, asig_nombre: str) -> None:
    """Establece la asignación seleccionada."""
    s["sel_asignacion_id"] = asig_id
    s["sel_asignacion_nombre"] = asig_nombre


def _seleccion_completa_3d(s: dict) -> bool:
    """True si periodo, grupo y asignación están seleccionados."""
    return (
        s.get("sel_periodo_id") is not None
        and s.get("sel_grupo_id") is not None
        and s.get("sel_asignacion_id") is not None
    )


def _seleccion_completa_2d(s: dict) -> bool:
    """True si periodo y grupo están seleccionados."""
    return (
        s.get("sel_periodo_id") is not None
        and s.get("sel_grupo_id") is not None
    )


# ─── Carga de datos (wrappean servicios) ─────────────────────────────────────

def _cargar_periodos(institucion_id: int) -> list:
    """Retorna lista de Periodo del año activo. Vacía si falla."""
    try:
        config = Container.configuracion_service().get_activa(institucion_id)
        anio_id = getattr(config, "id", None) if config else None
        if not anio_id:
            return []
        return Container.periodo_service().listar_por_anio(anio_id)
    except Exception as exc:
        logger.warning("Error cargando periodos: %s", exc)
        return []


def _cargar_grupos(
    periodo_id: int,
    usuario_id: int | None,
    usuario_rol: str,
) -> list[tuple[int, str]]:
    """
    Retorna [(grupo_id, grupo_codigo), ...] de grupos con asignaciones activas
    en el periodo. Si usuario_rol == 'profesor', filtra por usuario_id.
    """
    from src.services.asignacion_service import FiltroAsignacionesDTO
    try:
        filtro = FiltroAsignacionesDTO(periodo_id=periodo_id, solo_activas=True)
        infos = Container.asignacion_service().listar_con_info(filtro)
        if usuario_rol == "profesor" and usuario_id is not None:
            infos = [i for i in infos if i.usuario_id == usuario_id]
        seen: set[int] = set()
        grupos: list[tuple[int, str]] = []
        for info in infos:
            if info.grupo_id not in seen:
                seen.add(info.grupo_id)
                grupos.append((info.grupo_id, info.grupo_codigo))
        return grupos
    except Exception as exc:
        logger.warning("Error cargando grupos: %s", exc)
        return []


def _cargar_asignaciones(
    grupo_id: int,
    periodo_id: int,
    usuario_id: int | None,
    usuario_rol: str,
) -> list[tuple[int, str]]:
    """
    Retorna [(asignacion_id, asignatura_nombre), ...] de asignaciones activas
    para (grupo, periodo). Si usuario_rol == 'profesor', filtra por usuario_id.
    """
    from src.services.asignacion_service import FiltroAsignacionesDTO
    try:
        filtro = FiltroAsignacionesDTO(
            grupo_id=grupo_id,
            periodo_id=periodo_id,
            solo_activas=True,
        )
        infos = Container.asignacion_service().listar_con_info(filtro)
        if usuario_rol == "profesor" and usuario_id is not None:
            infos = [i for i in infos if i.usuario_id == usuario_id]
        return [(i.asignacion_id, i.asignatura_nombre) for i in infos]
    except Exception as exc:
        logger.warning("Error cargando asignaciones: %s", exc)
        return []


# ─── Render NiceGUI ───────────────────────────────────────────────────────────

def inline_periodo_grupo_asignatura(
    s: dict,
    on_change: Callable,
    usuario_id: int,
    institucion_id: int,
    usuario_rol: str,
    preselect_periodo: bool = True,
) -> None:
    """
    Renderiza 3 pills en cascada: [Periodo ▾]  [Grupo ▾]  [Asignatura ▾].

    Args:
        s:                Estado local de la página. Se modifica in-place.
        on_change:        Callable(s) llamado cuando los 3 valores están
                          seleccionados.
        usuario_id:       ID del usuario autenticado.
        institucion_id:   ID de la institución (para cargar periodos).
        usuario_rol:      Rol del usuario. 'profesor' filtra grupos y
                          asignaturas propios.
        preselect_periodo: Si True, pre-selecciona el primer periodo
                           activo del año. Default True.
    """
    _estado_inicial(s)
    if preselect_periodo:
        _preseleccionar_periodo(s, institucion_id)

    @ui.refreshable
    def _fila() -> None:
        # ── Handlers definidos DENTRO de _fila para capturar _fila.refresh ──
        def _handle_periodo(pid: int, pnombre: str) -> None:
            _on_periodo_cambio(s, pid, pnombre)
            _fila.refresh()

        def _handle_grupo(gid: int, gnombre: str) -> None:
            _on_grupo_cambio(s, gid, gnombre)
            _fila.refresh()

        def _handle_asignacion(aid: int, anombre: str) -> None:
            _on_asignacion_cambio(s, aid, anombre)
            if _seleccion_completa_3d(s):
                on_change(s)
            _fila.refresh()

        with ui.element("div").classes("inline-sel-row"):

            # ── Pill Periodo ─────────────────────────────────────────────
            has_p = s["sel_periodo_id"] is not None
            p_cls = "inline-sel-pill sel-active" if has_p else "inline-sel-pill"
            p_text = s["sel_periodo_nombre"] if has_p else "Periodo"
            with ui.button(p_text, color=None).classes(p_cls):
                ThemeManager.icono("expand_more", size=18)
                with ui.menu():
                    for p in _cargar_periodos(institucion_id):
                        ui.menu_item(
                            p.nombre,
                            on_click=lambda e, _p=p: _handle_periodo(_p.id, _p.nombre),
                        )

            # ── Pill Grupo ───────────────────────────────────────────────
            has_g = s["sel_grupo_id"] is not None
            g_cls = "inline-sel-pill sel-active" if has_g else "inline-sel-pill"
            g_text = s["sel_grupo_nombre"] if has_g else "Grupo"
            btn_g = ui.button(g_text, color=None).classes(g_cls)
            if not has_p:
                btn_g.props("disable")
            with btn_g:
                ThemeManager.icono("expand_more", size=18)
                if has_p:
                    with ui.menu():
                        for gid, gnombre in _cargar_grupos(
                            s["sel_periodo_id"], usuario_id, usuario_rol
                        ):
                            ui.menu_item(
                                gnombre,
                                on_click=lambda e, _id=gid, _n=gnombre: _handle_grupo(_id, _n),
                            )

            # ── Pill Asignatura ──────────────────────────────────────────
            has_a = s["sel_asignacion_id"] is not None
            a_cls = "inline-sel-pill sel-active" if has_a else "inline-sel-pill"
            a_text = s["sel_asignacion_nombre"] if has_a else "Asignatura"
            btn_a = ui.button(a_text, color=None).classes(a_cls)
            if not has_g:
                btn_a.props("disable")
            with btn_a:
                ThemeManager.icono("expand_more", size=18)
                if has_g:
                    with ui.menu():
                        for aid, anombre in _cargar_asignaciones(
                            s["sel_grupo_id"],
                            s["sel_periodo_id"],
                            usuario_id,
                            usuario_rol,
                        ):
                            ui.menu_item(
                                anombre,
                                on_click=lambda e, _id=aid, _n=anombre: _handle_asignacion(
                                    _id, _n
                                ),
                            )

    _fila()


def inline_periodo_grupo(
    s: dict,
    on_change: Callable,
    institucion_id: int,
    preselect_periodo: bool = True,
    usuario_id: int | None = None,
    usuario_rol: str = "directivo",
) -> None:
    """
    Renderiza 2 pills en cascada: [Periodo ▾]  [Grupo ▾].

    Args:
        s:                Estado local de la página. Se modifica in-place.
        on_change:        Callable(s) llamado cuando periodo y grupo están
                          seleccionados.
        institucion_id:   ID de la institución (para cargar periodos).
        preselect_periodo: Si True, pre-selecciona el primer periodo activo.
        usuario_id:       ID del usuario. Si usuario_rol == 'profesor', filtra grupos propios.
        usuario_rol:      Rol del usuario. Default 'directivo' (ve todos los grupos).
    """
    _estado_inicial(s)
    if preselect_periodo:
        _preseleccionar_periodo(s, institucion_id)

    @ui.refreshable
    def _fila() -> None:
        def _handle_periodo(pid: int, pnombre: str) -> None:
            _on_periodo_cambio(s, pid, pnombre)
            _fila.refresh()

        def _handle_grupo(gid: int, gnombre: str) -> None:
            _on_grupo_cambio(s, gid, gnombre)
            if _seleccion_completa_2d(s):
                on_change(s)
            _fila.refresh()

        with ui.element("div").classes("inline-sel-row"):

            # ── Pill Periodo ─────────────────────────────────────────────
            has_p = s["sel_periodo_id"] is not None
            p_cls = "inline-sel-pill sel-active" if has_p else "inline-sel-pill"
            p_text = s["sel_periodo_nombre"] if has_p else "Periodo"
            with ui.button(p_text, color=None).classes(p_cls):
                ThemeManager.icono("expand_more", size=18)
                with ui.menu():
                    for p in _cargar_periodos(institucion_id):
                        ui.menu_item(
                            p.nombre,
                            on_click=lambda e, _p=p: _handle_periodo(_p.id, _p.nombre),
                        )

            # ── Pill Grupo ───────────────────────────────────────────────
            has_g = s["sel_grupo_id"] is not None
            g_cls = "inline-sel-pill sel-active" if has_g else "inline-sel-pill"
            g_text = s["sel_grupo_nombre"] if has_g else "Grupo"
            btn_g = ui.button(g_text, color=None).classes(g_cls)
            if not has_p:
                btn_g.props("disable")
            with btn_g:
                ThemeManager.icono("expand_more", size=18)
                if has_p:
                    with ui.menu():
                        for gid, gnombre in _cargar_grupos(
                            s["sel_periodo_id"], usuario_id, usuario_rol
                        ):
                            ui.menu_item(
                                gnombre,
                                on_click=lambda e, _id=gid, _n=gnombre: _handle_grupo(_id, _n),
                            )

    _fila()


__all__ = ["inline_periodo_grupo", "inline_periodo_grupo_asignatura"]
