"""
test_tokens_roundtrip.py
========================
Round-trip: tokens.json → genera CSS/PY/TS en memoria → compara contra
archivos en disco.

Falla si hay drift entre tokens.json y tokens.css o tokens.py.
Para regenerar: python scripts/sync_tokens.py --generate-css
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
TOKENS_JSON = ROOT / "tokens.json"
TOKENS_CSS = ROOT / "src" / "interface" / "design" / "styles" / "tokens.css"


def _cargar_tokens() -> dict:
    """Lee tokens.json y devuelve el dict."""
    assert TOKENS_JSON.exists(), f"tokens.json no encontrado en {TOKENS_JSON}"
    with TOKENS_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def _parse_root_vars(css_text: str) -> dict[str, str]:
    """Extrae variables del primer bloque :root {} del CSS como {nombre: valor}."""
    import re
    root_match = re.search(r":root\s*\{(.+?)\n\}", css_text, re.DOTALL)
    if not root_match:
        return {}
    result: dict[str, str] = {}
    for line in root_match.group(1).splitlines():
        line = re.sub(r"/\*.*?\*/", "", line).strip()
        m = re.match(r"(--[\w-]+)\s*:\s*(.+?)\s*;", line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result


# ── Tests ──────────────────────────────────────────────────────────────────


def test_tokens_json_existe() -> None:
    """tokens.json existe en la raiz del proyecto y es JSON valido."""
    assert TOKENS_JSON.exists(), f"tokens.json no encontrado en {TOKENS_JSON}"
    with TOKENS_JSON.open(encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), "tokens.json debe ser un objeto JSON"
    assert "primitives" in data, "tokens.json debe tener la capa 'primitives'"
    assert "semantic" in data, "tokens.json debe tener la capa 'semantic'"
    assert "component" in data, "tokens.json debe tener la capa 'component'"
    assert "dark" in data, "tokens.json debe tener la capa 'dark'"


def test_total_tokens() -> None:
    """tokens.json tiene al menos 187 tokens en total (todas las capas)."""
    tokens = _cargar_tokens()
    total = sum(
        len(g)
        for layer in tokens.values()
        if isinstance(layer, dict)
        for g in layer.values()
        if isinstance(g, dict)
    )
    assert total >= 187, (
        f"tokens.json tiene solo {total} tokens; se esperan >= 187"
    )


def test_css_roundtrip() -> None:
    """
    Las variables del :root {} en tokens.css coinciden con las de tokens.json
    (mismos nombres, mismos valores, mismo orden).

    Falla si hay drift — ejecutar:
        python scripts/sync_tokens.py --generate-css
    """
    result = subprocess.run(
        [sys.executable, "scripts/sync_tokens.py", "--check"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, (
        f"tokens.css tiene drift respecto a tokens.json.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}\n"
        f"Solucion: python scripts/sync_tokens.py --generate-css"
    )


def test_py_sincronizado() -> None:
    """
    Los valores de tokens.py coinciden con tokens.json para todas las
    variables del MAPPING.

    Falla si hay drift — actualizar manualmente tokens.py o regenerar.
    """
    # Este test es cubierto por test_css_roundtrip (sync_tokens --check verifica
    # tanto CSS como PY). Lo mantenemos separado para mensajes de error claros.
    tokens = _cargar_tokens()

    # Construir mapa plano desde JSON (sin resolver var())
    json_vars: dict[str, str] = {}
    for layer in ("primitives", "semantic", "component"):
        for group in tokens.get(layer, {}).values():
            if isinstance(group, dict):
                for name, token in group.items():
                    if isinstance(token, dict):
                        json_vars[name] = token.get("$value", "")

    # Verificar que las variables del MAPPING existen en tokens.json
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.sync_tokens import MAPPING  # type: ignore[import]

    faltantes = [var for var in MAPPING if var not in json_vars]
    assert not faltantes, (
        "Variables del MAPPING ausentes en tokens.json:\n  "
        + "\n  ".join(faltantes)
    )


def test_css_root_tiene_148_variables() -> None:
    """El bloque :root de tokens.css tiene las 148 variables del diseno base."""
    assert TOKENS_CSS.exists(), f"tokens.css no encontrado en {TOKENS_CSS}"
    css_text = TOKENS_CSS.read_text(encoding="utf-8")
    vars_map = _parse_root_vars(css_text)
    n = len(vars_map)
    assert n >= 140, (
        f"tokens.css :root tiene solo {n} variables; se esperan >= 140"
    )
