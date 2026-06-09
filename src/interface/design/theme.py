"""
theme.py — ThemeManager para ZECI Manager v2.0
================================================
Inyecta el CSS del design system en NiceGUI y provee
utilidades de renderizado de iconos Material Symbols.

Uso en main.py (llamar UNA VEZ antes de registrar páginas):

    from src.interface.design.theme import ThemeManager
    ThemeManager.aplicar()

Uso de iconos en cualquier página/componente:

    from src.interface.design.theme import ThemeManager
    ThemeManager.icono("space_dashboard", color="white")
    ThemeManager.icono(Icons.EDIT, size=20, fill=1)
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("THEME")


class ThemeManager:
    """
    Punto único de configuración visual de la aplicación.

    Responsabilidades:
      - Inyectar los módulos CSS del design system en el <head> de NiceGUI.
      - Exponer ThemeManager.icono() para renderizar Material Symbols
        con los parámetros correctos del design system.

    Notas de implementación (NiceGUI 3.x):
      - ui.add_head_html() inyecta HTML estático en el <head> de TODAS
        las páginas. Llamar una sola vez en main.py.
      - app.native.window_args solo aplica al modo nativo (pywebview).
        El acceso es seguro en modo web — simplemente no tiene efecto.
      - icono() usa ui.html() en vez de ui.element().text() porque
        NiceGUI 3.x no expone .text() como método chainable en Element.
    """

    CSS_BASE_DIR = Path(__file__).parent / "styles"
    CSS_LOAD_ORDER = [
        "tokens.css",
        "reset.css",
        "typography.css",
        "layout/sidebar.css",
        "layout/topbar.css",
        "layout/content.css",
        "components/buttons.css",
        "components/tables.css",
        "components/dialogs.css",
        "components/badges.css",
        "components/forms.css",
        "components/cards.css",
        "components/chips.css",
        "components/empty_state.css",
        "components/skeleton_loader.css",
        "components/toast.css",
        "domain/asistencia.css",
        "domain/desempeno.css",
    ]

    @classmethod
    def aplicar(cls) -> None:
        """
        Inyecta el design system en el head de NiceGUI.
        Llamar UNA SOLA VEZ en main.py antes de ui.run().
        """
        from nicegui import ui, app

        fragments: list[str] = []
        for rel in cls.CSS_LOAD_ORDER:
            path = cls.CSS_BASE_DIR / rel
            if not path.exists():
                logger.error("CSS faltante: %s", rel)
                continue
            fragments.append(f"/* === {rel} === */")
            fragments.append(path.read_text(encoding="utf-8"))

        if not fragments:
            logger.error("No se encontró ningún archivo CSS en %s", cls.CSS_BASE_DIR)
            return

        css = "\n".join(fragments)
        ui.add_head_html(f"<style>{css}</style>", shared=True)

        # Meta viewport para responsive
        ui.add_head_html(
            '<meta name="viewport" '
            'content="width=device-width, initial-scale=1.0">',
            shared=True
        )

        # Configuración para modo nativo (pywebview) — no-op en modo web
        try:
            app.native.window_args["background_color"] = "#F8FAFC"
        except Exception:
            pass  # Solo aplica cuando se corre con ui.run(native=True)

        logger.info("Design system 'Andes Minimal v2' aplicado")

    @classmethod
    def icono(
        cls,
        nombre: str,
        *,
        size: int = 24,
        fill: int = 0,
        weight: int = 300,
        color: str | None = None,
        clases: str = "",
    ):
        """
        Renderiza un Material Symbol Rounded con los parámetros del
        design system.

        Args:
            nombre:  Nombre del icono (ej: "space_dashboard", Icons.EDIT).
            size:    Tamaño óptico en px. Valores válidos: 20, 24, 40, 48.
            fill:    0 = outline (defecto), 1 = relleno.
            weight:  Grosor del trazo. Valores: 100–700 (defecto: 300).
            color:   Color CSS del icono (ej: "white", "#00509E", None).
            clases:  Clases CSS adicionales para el span.

        Returns:
            Elemento ui.html con el span del icono.

        Uso:
            ThemeManager.icono("space_dashboard")
            ThemeManager.icono(Icons.EDIT, size=20, fill=1, color="white")
            ThemeManager.icono(Icons.ALERTS, clases="text-warning")
        """
        from nicegui import ui

        font_variation = (
            f"font-variation-settings: 'FILL' {fill}, "
            f"'wght' {weight}, 'GRAD' 0, 'opsz' {size};"
        )
        estilos = [
            font_variation,
            f"font-size: {size}px;",
            "line-height: 1;",
            "vertical-align: middle;",
            "user-select: none;",
        ]
        if color:
            estilos.append(f"color: {color};")

        estilo_inline = " ".join(estilos)
        clases_span = f"material-symbols-rounded {clases}".strip()

        return ui.html(
            f'<span class="{clases_span}" style="{estilo_inline}">'
            f"{nombre}"
            f"</span>"
        )

    @classmethod
    def render_logo(
        cls,
        logo_url: str,
        max_height: int = 36,
        max_width: int = 120,
        clases: str = "",
    ):
        """
        Renderiza la imagen del logo institucional.

        Args:
            logo_url:   URL o ruta estática de la imagen.
            max_height: Alto máximo en px.
            max_width:  Ancho máximo en px.
            clases:     Clases CSS adicionales para el <img>.
        """
        from nicegui import ui

        estilo = (
            f"max-height:{max_height}px;"
            f"max-width:{max_width}px;"
            f"object-fit:contain;"
            f"border-radius:var(--radius-sm);"
        )
        clase_final = f"logo-institucional {clases}".strip()
        return ui.html(
            f'<img src="{logo_url}" alt="Logo institución" '
            f'class="{clase_final}" style="{estilo}" />'
        )


__all__ = ["ThemeManager"]
