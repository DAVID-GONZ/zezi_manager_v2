"""
test_toast.py — Tests del componente toast (paso_12b).
"""
from __future__ import annotations


def test_toast_importa():
    from src.interface.design.components import toast
    assert callable(toast)


def test_toast_atajos_importan():
    from src.interface.design.components import (
        toast_info,
        toast_success,
        toast_warning,
        toast_error,
    )
    for fn in (toast_info, toast_success, toast_warning, toast_error):
        assert callable(fn)


def test_toast_success_usa_tipo_positive(monkeypatch):
    """toast_success mapea a type='positive' de Quasar."""
    from src.interface.design.components.toast import toast_success
    from nicegui import ui

    capturado: dict = {}

    def fake_notify(msg, **kw):
        capturado["msg"] = msg
        capturado["kw"] = kw

    monkeypatch.setattr(ui, "notify", fake_notify)
    toast_success("Guardado correctamente")

    assert capturado["kw"]["type"] == "positive"
    assert capturado["kw"]["position"] == "bottom-right"
    assert capturado["msg"] == "Guardado correctamente"


def test_toast_error_usa_tipo_negative(monkeypatch):
    """toast_error mapea a type='negative' de Quasar."""
    from src.interface.design.components.toast import toast_error
    from nicegui import ui

    capturado: dict = {}

    def fake_notify(msg, **kw):
        capturado["msg"] = msg
        capturado["kw"] = kw

    monkeypatch.setattr(ui, "notify", fake_notify)
    toast_error("Error al guardar")

    assert capturado["kw"]["type"] == "negative"


def test_toast_warning_usa_tipo_warning(monkeypatch):
    """toast_warning mapea a type='warning' de Quasar."""
    from src.interface.design.components.toast import toast_warning
    from nicegui import ui

    capturado: dict = {}

    def fake_notify(msg, **kw):
        capturado["msg"] = msg
        capturado["kw"] = kw

    monkeypatch.setattr(ui, "notify", fake_notify)
    toast_warning("Periodo ya cerrado")

    assert capturado["kw"]["type"] == "warning"


def test_toast_con_titulo(monkeypatch):
    """El título se antepone al mensaje con salto de línea."""
    from src.interface.design.components.toast import toast as toast_fn
    from nicegui import ui

    capturado: dict = {}

    def fake_notify(msg, **kw):
        capturado["msg"] = msg
        capturado["kw"] = kw

    monkeypatch.setattr(ui, "notify", fake_notify)
    toast_fn("Descripción", tipo="info", titulo="Mi título")

    assert "Mi título" in capturado["msg"]
    assert "Descripción" in capturado["msg"]


def test_toast_css_existe():
    """El archivo CSS del toast existe en styles/components/."""
    from pathlib import Path
    css = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src" / "interface" / "design" / "styles" / "components" / "toast.css"
    )
    assert css.exists(), f"CSS no encontrado: {css}"


def test_toast_en_css_load_order():
    """toast.css aparece en CSS_LOAD_ORDER de ThemeManager."""
    from src.interface.design.theme import ThemeManager
    assert any("toast" in p for p in ThemeManager.CSS_LOAD_ORDER)
