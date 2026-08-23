"""Guarda de pureza de la capa de presenters.

Regla dura: ningún módulo de `src/interface/presenters/` puede importar NiceGUI.
El presenter debe ser lógica pura (estado + decisión), testeable sin harness y
portable a otro frontend (p. ej. el fork a Vue). Este test recorre el paquete y
falla si algún archivo referencia `nicegui`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_PRESENTERS_DIR = (
    Path(__file__).resolve().parents[4]
    / "src" / "interface" / "presenters"
)

# rglob: la carpeta de presenters espeja la estructura de pages/ (admin/, informes/,
# convivencia/, …), así que se recorre recursivamente.
_ARCHIVOS = sorted(p for p in _PRESENTERS_DIR.rglob("*.py") if p.name != "__init__.py")


def test_hay_al_menos_un_presenter():
    assert _ARCHIVOS, f"No se encontraron presenters en {_PRESENTERS_DIR}"


@pytest.mark.parametrize("archivo", _ARCHIVOS, ids=lambda p: p.name)
def test_presenter_no_importa_nicegui(archivo: Path):
    fuente = archivo.read_text(encoding="utf-8")
    assert "import nicegui" not in fuente and "from nicegui" not in fuente, (
        f"{archivo.name} importa NiceGUI: un presenter debe ser puro (sin UI)."
    )
