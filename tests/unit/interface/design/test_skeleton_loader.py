"""
test_skeleton_loader.py — Tests del skeleton_loader (paso_12b).
"""
from __future__ import annotations


def test_skeleton_table_importa():
    from src.interface.design.components import skeleton_table
    assert callable(skeleton_table)


def test_skeleton_cards_importa():
    from src.interface.design.components import skeleton_cards
    assert callable(skeleton_cards)


def test_skeleton_form_importa():
    from src.interface.design.components import skeleton_form
    assert callable(skeleton_form)


def test_skeleton_css_existe():
    """El archivo CSS del skeleton existe en styles/components/."""
    from pathlib import Path
    css = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src" / "interface" / "design" / "styles" / "components" / "skeleton_loader.css"
    )
    assert css.exists(), f"CSS no encontrado: {css}"


def test_skeleton_en_css_load_order():
    """skeleton_loader.css aparece en CSS_LOAD_ORDER de ThemeManager."""
    from src.interface.design.theme import ThemeManager
    assert any("skeleton_loader" in p for p in ThemeManager.CSS_LOAD_ORDER)
