"""
tests/unit/interface/test_hub_institucion_smoke.py
===================================================
Smoke tests para hub_institucion_page (mejora_09c).

Verifica sin levantar NiceGUI:
  1. La página importa sin errores.
  2. hub_institucion_page es callable.
  3. El archivo del hub NO importa src.domain.models.* (refuerzo de capa).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


HUB_PATH = (
    Path(__file__).resolve().parents[3]
    / "src" / "interface" / "pages" / "institucion" / "hub_institucion.py"
)


def test_hub_importa_sin_error() -> None:
    """La página puede importarse sin que NiceGUI levante un servidor."""
    from src.interface.pages.institucion.hub_institucion import hub_institucion_page  # noqa: F401


def test_hub_es_callable() -> None:
    """hub_institucion_page es una función invocable."""
    from src.interface.pages.institucion.hub_institucion import hub_institucion_page

    assert callable(hub_institucion_page)


def test_hub_no_importa_domain_models() -> None:
    """El hub no contiene 'from src.domain.models' — refuerzo del linter de capas."""
    fuente = HUB_PATH.read_text(encoding="utf-8")
    assert re.search(r"from\s+src\.domain\.models\b", fuente) is None, (
        "hub_institucion.py importa src.domain.models.* — violación de capas."
    )
