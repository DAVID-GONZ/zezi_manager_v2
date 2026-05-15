"""
performance_indicator.py — Indicador de desempeño académico del design system Andes Minimal.

Visualiza el nivel de desempeño como barra de progreso con etiqueta y color semántico.
Compatible con los niveles del sistema: Bajo, Básico, Alto, Superior.
"""
from __future__ import annotations

from nicegui import ui

from src.interface.design.tokens import DesempenoColors


_NIVEL_PORCENTAJE = {
    "Bajo":     25,
    "Básico":   50,
    "Alto":     75,
    "Superior": 100,
}


def performance_indicator(
    valor: float | None = None,
    nivel: str | None = None,
    label: str = "Desempeño",
    mostrar_valor: bool = True,
    mostrar_nivel: bool = True,
    altura: int = 8,
) -> ui.element:
    """
    Indicador de desempeño académico con barra de progreso coloreada.

    Puede recibir un valor numérico (nota, porcentaje) o un nivel textual.
    Si recibe ambos, el porcentaje de la barra se calcula desde `valor`.

    Args:
        valor:         Nota o porcentaje (0.0 – 5.0 para notas, 0 – 100 para %).
                       Si es nota (≤ 5.0), se convierte internamente a %.
        nivel:         "Bajo" | "Básico" | "Alto" | "Superior".
                       Si se omite y hay `valor`, se infiere del valor.
        label:         Etiqueta descriptiva (ej: "Promedio general", "Asistencia").
        mostrar_valor: Muestra el valor numérico junto a la barra.
        mostrar_nivel: Muestra la etiqueta del nivel (Bajo, Básico, etc.).
        altura:        Altura en píxeles de la barra (default: 8).

    Returns:
        El elemento raíz (ui.element div) para encadenamiento.

    Ejemplo:
        performance_indicator(valor=3.8, label="Promedio del periodo")
        performance_indicator(nivel="Alto", label="Nivel de convivencia")
        performance_indicator(valor=92, label="Asistencia", mostrar_nivel=False)
    """
    # Determinar nivel a partir del valor si no se proporcionó
    nivel_resuelto = nivel
    if nivel_resuelto is None and valor is not None:
        nivel_resuelto = DesempenoColors.para_nota(valor)

    # Calcular porcentaje para la barra
    if valor is not None:
        if valor <= 5.0:
            pct = min(100, max(0, (valor / 5.0) * 100))
        else:
            pct = min(100, max(0, valor))
    elif nivel_resuelto:
        pct = _NIVEL_PORCENTAJE.get(nivel_resuelto, 50)
    else:
        pct = 0

    # Colores del nivel
    if nivel_resuelto:
        color_info = DesempenoColors.css_badge(nivel_resuelto)
        barra_color = color_info.get("color", "var(--color-primary)")
    else:
        barra_color = "var(--color-primary)"

    contenedor = ui.element("div").style("width:100%;")
    with contenedor:
        # Fila superior: label + valor/nivel
        with ui.row().classes("items-center justify-between").style(
            "width:100%;margin-bottom:4px;"
        ):
            ui.label(label).style(
                "color:var(--color-text-secondary);"
                "font-size:var(--font-size-small);"
                "font-weight:500;"
            )
            with ui.row().classes("items-center gap-2"):
                if mostrar_valor and valor is not None:
                    valor_texto = f"{valor:.1f}" if valor <= 5.0 else f"{valor:.0f}%"
                    ui.label(valor_texto).style(
                        "color:var(--color-text-primary);"
                        "font-size:var(--font-size-small);"
                        "font-weight:600;"
                    )
                if mostrar_nivel and nivel_resuelto:
                    ui.label(nivel_resuelto).style(
                        f"color:{barra_color};"
                        "font-size:var(--font-size-small);"
                        "font-weight:500;"
                    )

        # Barra de progreso
        with ui.element("div").style(
            f"height:{altura}px;"
            "width:100%;"
            "background:var(--color-bg);"
            "border-radius:999px;"
            "overflow:hidden;"
            "border:1px solid var(--color-divider);"
        ):
            ui.element("div").style(
                f"height:100%;"
                f"width:{pct:.1f}%;"
                f"background:{barra_color};"
                "border-radius:999px;"
                "transition:width 0.4s ease;"
            )

    return contenedor


__all__ = ["performance_indicator"]
