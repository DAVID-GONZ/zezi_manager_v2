from src.interface.pages.evaluacion.planilla_notas import _build_grid_options


def test_planilla_grid_keyboard_navigation_is_enabled() -> None:
    grid_options = _build_grid_options()

    assert grid_options["suppressCellFocus"] is False
    assert grid_options["enableCellTextSelection"] is True
    assert grid_options["navigateToNextCell"] is True
