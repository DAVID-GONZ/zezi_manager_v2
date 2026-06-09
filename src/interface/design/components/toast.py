"""
toast.py — Notificaciones toast unificadas del design system (paso_12b).

Wrapper sobre ui.notify con tipos semánticos del sistema.

Uso:
    from src.interface.design.components import toast_success, toast_error

    toast_success("Grupo guardado correctamente")
    toast_error("No se pudo conectar al servidor", titulo="Error de red")
    toast_warning("El periodo ya está cerrado")
    toast_info("Exportando PDF...", duracion_ms=0)   # sin timeout — requiere cierre manual

API verificada con NiceGUI 3.6.1:
    ui.notify(message, *, position, close_button, type, color, multi_line, **kwargs)
    - type: 'positive' | 'negative' | 'warning' | 'info' | 'ongoing'
    - timeout y icon pasan por **kwargs a Quasar QNotify
    - actions pasan por **kwargs pero requieren handlers JavaScript en NiceGUI 3.x;
      por ello solo se soporta close_button como acción desde Python.
"""
from __future__ import annotations

from nicegui import ui

_TIPO_CONFIG: dict[str, dict] = {
    "info":    {"color": "info",     "icon": "info"},
    "success": {"color": "positive", "icon": "check_circle"},
    "warning": {"color": "warning",  "icon": "warning"},
    "error":   {"color": "negative", "icon": "error"},
}


def toast(
    mensaje: str,
    *,
    tipo: str = "info",
    duracion_ms: int = 4000,
    titulo: str | None = None,
) -> None:
    """
    Muestra una notificación toast en la esquina inferior derecha.

    Args:
        mensaje:     Texto principal del toast.
        tipo:        "info" | "success" | "warning" | "error".
        duracion_ms: Milisegundos antes de cerrar automáticamente.
                     0 = no cierra solo (muestra botón Cerrar).
        titulo:      Línea de título opcional (antepuesta al mensaje).
    """
    cfg = _TIPO_CONFIG.get(tipo, _TIPO_CONFIG["info"])
    contenido = f"{titulo}\n{mensaje}" if titulo else mensaje

    kwargs: dict = {
        "position": "bottom-right",
        "timeout":  duracion_ms,
        "icon":     cfg["icon"],
        "classes":  f"andes-toast andes-toast--{tipo}",
    }

    if duracion_ms == 0:
        ui.notify(
            contenido,
            type=cfg["color"],
            close_button="Cerrar",
            **kwargs,
        )
    else:
        ui.notify(
            contenido,
            type=cfg["color"],
            **kwargs,
        )


def toast_info(mensaje: str, **kw) -> None:
    """Toast informativo (azul tinta)."""
    toast(mensaje, tipo="info", **kw)


def toast_success(mensaje: str, **kw) -> None:
    """Toast de éxito (verde bosque)."""
    toast(mensaje, tipo="success", **kw)


def toast_warning(mensaje: str, **kw) -> None:
    """Toast de advertencia (ámbar)."""
    toast(mensaje, tipo="warning", **kw)


def toast_error(mensaje: str, **kw) -> None:
    """Toast de error (terracota). Duración extendida por defecto."""
    kw.setdefault("duracion_ms", 6000)
    toast(mensaje, tipo="error", **kw)
