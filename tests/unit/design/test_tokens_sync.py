"""
test_tokens_sync.py — Verifica que tokens.py esté sincronizado con tokens.css.

Este test falla si hay drift entre las variables CSS y los valores Python,
lo que indicaría que alguien editó un archivo sin actualizar el otro.

Para corregir un fallo aquí, ejecutar:
    python scripts/sync_tokens.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent


def test_tokens_py_sincronizado_con_css() -> None:
    """
    Ejecuta sync_tokens.py --check y verifica que retorna exit code 0.

    Falla si tokens.py está desincronizado con tokens.css.
    Solución: python scripts/sync_tokens.py
    """
    result = subprocess.run(
        [sys.executable, "scripts/sync_tokens.py", "--check"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"tokens.py está desincronizado con tokens.css.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}\n"
        f"Solución: ejecutar `python scripts/sync_tokens.py`"
    )


def test_tokens_css_existe() -> None:
    """Verifica que el archivo tokens.css exista en su ruta esperada."""
    tokens_css = ROOT / "src" / "interface" / "design" / "styles" / "tokens.css"
    assert tokens_css.exists(), f"tokens.css no encontrado en {tokens_css}"


def test_css_load_order_archivos_existen() -> None:
    """Verifica que todos los archivos en CSS_LOAD_ORDER existen."""
    styles_dir = ROOT / "src" / "interface" / "design" / "styles"
    expected = [
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
        "domain/asistencia.css",
        "domain/desempeno.css",
    ]
    missing = []
    for rel in expected:
        path = styles_dir / rel
        if not path.exists():
            missing.append(rel)

    assert not missing, (
        f"Archivos CSS faltantes en styles/:\n  "
        + "\n  ".join(missing)
    )


def test_styles_css_monolith_eliminado() -> None:
    """Verifica que el monolito styles.css fue eliminado."""
    monolith = ROOT / "src" / "interface" / "design" / "styles.css"
    assert not monolith.exists(), (
        "styles.css monolítico sigue presente — debe ser eliminado tras el split en módulos"
    )
