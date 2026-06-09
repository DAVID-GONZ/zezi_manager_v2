"""
test_empty_state.py — Tests del componente empty_state (paso_12b).
"""
from __future__ import annotations


def test_empty_state_importa():
    """El componente es importable desde el paquete de componentes."""
    from src.interface.design.components import empty_state
    assert callable(empty_state)


def test_empty_state_importa_directo():
    """El módulo empty_state.py es importable directamente."""
    from src.interface.design.components.empty_state import empty_state
    assert callable(empty_state)


def test_empty_state_variantes_icono_color():
    """Las 3 variantes tienen una entrada en el mapa de color de icono."""
    from src.interface.design.components.empty_state import _VARIANTE_ICONO_COLOR
    assert "default" in _VARIANTE_ICONO_COLOR
    assert "search"  in _VARIANTE_ICONO_COLOR
    assert "error"   in _VARIANTE_ICONO_COLOR


def test_empty_state_css_existe():
    """El archivo CSS del componente existe en styles/components/."""
    from pathlib import Path
    css = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src" / "interface" / "design" / "styles" / "components" / "empty_state.css"
    )
    assert css.exists(), f"CSS no encontrado: {css}"


def test_empty_state_en_css_load_order():
    """empty_state.css aparece en CSS_LOAD_ORDER de ThemeManager."""
    from src.interface.design.theme import ThemeManager
    assert any("empty_state" in p for p in ThemeManager.CSS_LOAD_ORDER)
