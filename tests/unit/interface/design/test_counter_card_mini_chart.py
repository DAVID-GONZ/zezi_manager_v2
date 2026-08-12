"""
test_counter_card_mini_chart.py — Tests de counter_card y mini_chart
(convivencia_22_componentes_visuales).

Verifican: importabilidad, mapa de variantes, estructura de la opción ECharts
(lógica pura), presencia del CSS y de la clase de tamaño echart-sm, registro
en CSS_LOAD_ORDER, y render sin excepción con datos de ejemplo.
"""
from __future__ import annotations

from pathlib import Path

_STYLES = (
    Path(__file__).parent.parent.parent.parent.parent
    / "src" / "interface" / "design" / "styles"
)


# ─── Importabilidad ──────────────────────────────────────────────────────────

def test_counter_card_importa():
    from src.interface.design.components import counter_card
    assert callable(counter_card)


def test_mini_chart_importa():
    from src.interface.design.components import mini_chart
    assert callable(mini_chart)


def test_importan_directo():
    from src.interface.design.components.counter_card import counter_card
    from src.interface.design.components.mini_chart import mini_chart
    assert callable(counter_card) and callable(mini_chart)


# ─── counter_card — variantes ────────────────────────────────────────────────

def test_counter_card_variantes_mapa():
    """Las 6 variantes tienen entrada en el mapa de color de icono."""
    from src.interface.design.components.counter_card import _VARIANTE_ICONO_COLOR
    for v in ("neutral", "primary", "success", "warning", "danger", "info"):
        assert v in _VARIANTE_ICONO_COLOR
        assert _VARIANTE_ICONO_COLOR[v].startswith("var(--")


# ─── mini_chart — lógica pura de la opción ECharts ───────────────────────────

def test_mini_chart_option_estructura():
    from src.interface.design.components.mini_chart import _build_option

    opt = _build_option(["S1", "S2", "S3"], [4, 7, 5], "")
    assert opt["xAxis"]["data"] == ["S1", "S2", "S3"]
    assert opt["series"][0]["type"] == "line"
    assert opt["series"][0]["data"] == [4, 7, 5]
    assert opt["series"][0]["smooth"] is True
    assert "tooltip" in opt
    assert "title" not in opt  # sin título → sin clave title


def test_mini_chart_option_con_titulo():
    from src.interface.design.components.mini_chart import _build_option

    opt = _build_option(["S1"], [1], "Seguimientos")
    assert opt["title"]["text"] == "Seguimientos"


# ─── CSS presente y registrado ───────────────────────────────────────────────

def test_counter_card_css_existe():
    css = _STYLES / "components" / "counter-card.css"
    assert css.exists(), f"CSS no encontrado: {css}"


def test_counter_card_en_css_load_order():
    from src.interface.design.theme import ThemeManager
    assert any("counter-card" in p for p in ThemeManager.CSS_LOAD_ORDER)


def test_echart_sm_definido():
    """La clase de tamaño echart-sm existe en los estilos."""
    txt = (_STYLES / "components" / "tables.css").read_text(encoding="utf-8")
    assert ".echart-sm" in txt


# ─── Render sin excepción (contexto auto-index de NiceGUI) ───────────────────

def test_render_sin_excepcion():
    from nicegui import ui

    from src.interface.design.components import counter_card, mini_chart

    with ui.card():
        counter_card("Seguimientos abiertos", 12, "flag",
                     variante="danger", alerta=True, subtitulo="del periodo")
        counter_card("Cerrados", 27, "task_alt", variante="success")
        mini_chart(["S1", "S2", "S3"], [4, 7, 5], titulo="Evolución")
