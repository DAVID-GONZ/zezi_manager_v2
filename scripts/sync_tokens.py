"""
sync_tokens.py — Verifica que tokens.py sea espejo fiel de tokens.css
=====================================================================
tokens.css es la FUENTE CANÓNICA. tokens.py contiene las mismas constantes
en Python (para ag-grid, estilos calculados, etc.). Este script comprueba que
no haya drift entre ambos: resuelve las cadenas `var(--…)` de tokens.css hasta
su literal (hex / rgba / px) y las compara con los atributos de las clases de
tokens.py.

Uso:
    python scripts/sync_tokens.py            # verifica; exit 1 si hay drift
    python scripts/sync_tokens.py --check     # idéntico (alias explícito para CI)
    python scripts/sync_tokens.py --emit-ts   # emite tokens.ts + tokens.json para el fork Vue

`--emit-ts` genera `src/interface/design/tokens.ts` y `.json` resolviendo las
cadenas var(--…) de tokens.css. Es el puente para la Etapa B (Vue): el frontend
consume esos tokens sin depender de Python. Idempotente (verifica antes de emitir).

Nota histórica: versiones previas AUTOGENERABAN un bloque en tokens.py. Ese
mecanismo emitía las asignaciones con indentación de 4 espacios al final del
módulo, por lo que Python las absorbía dentro de la última clase (`Layout`),
contaminándola y sin sincronizar nunca las clases reales. Se sustituyó por esta
verificación no destructiva: tokens.py se mantiene a mano y el drift se detecta.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# --- Consola UTF-8 (Windows) --------------------------------------------------
# En consolas cp1252 imprimir «✅» tumbaba el script con UnicodeEncodeError y el
# rojo parecía del proyecto cuando era del terminal. Se arregla aquí, en origen,
# para no depender de que cada invocación recuerde PYTHONIOENCODING=utf-8.
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
# ------------------------------------------------------------------------------


# ── Rutas ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
TOKENS_CSS = ROOT / "src" / "interface" / "design" / "styles" / "tokens.css"

# ── Mapping: variable CSS → (clase Python, atributo) ────────────────────
# Solo las variables que tienen un espejo directo en tokens.py.
# Variables complejas (gradientes, sombras) se omiten.
MAPPING: dict[str, tuple[str, str]] = {
    # Colors — primario
    "--color-primary":           ("Colors", "PRIMARY"),
    "--color-primary-dark":      ("Colors", "PRIMARY_DARK"),
    "--color-primary-darker":    ("Colors", "PRIMARY_DARKER"),
    "--color-primary-light":     ("Colors", "PRIMARY_LIGHT"),
    "--color-primary-lighter":   ("Colors", "PRIMARY_LIGHTER"),
    "--color-primary-hover":     ("Colors", "PRIMARY_HOVER"),
    "--color-primary-disabled":  ("Colors", "PRIMARY_DISABLED"),
    "--color-primary-contrast":  ("Colors", "PRIMARY_CONTRAST"),
    # Colors — secundario
    "--color-secondary":         ("Colors", "SECONDARY"),
    "--color-secondary-dark":    ("Colors", "SECONDARY_DARK"),
    "--color-secondary-light":   ("Colors", "SECONDARY_LIGHT"),
    # Colors — semánticos
    "--color-error":             ("Colors", "ERROR"),
    "--color-error-light":       ("Colors", "ERROR_LIGHT"),
    "--color-error-dark":        ("Colors", "ERROR_DARK"),
    "--color-warning":           ("Colors", "WARNING"),
    "--color-warning-light":     ("Colors", "WARNING_LIGHT"),
    "--color-success":           ("Colors", "SUCCESS"),
    "--color-success-light":     ("Colors", "SUCCESS_LIGHT"),
    "--color-info":              ("Colors", "INFO"),
    "--color-info-light":        ("Colors", "INFO_LIGHT"),
    # Colors — neutros
    "--color-bg":                ("Colors", "BG"),
    "--color-surface":           ("Colors", "SURFACE"),
    "--color-surface-alt":       ("Colors", "SURFACE_ALT"),
    "--color-border":            ("Colors", "BORDER"),
    "--color-text-primary":      ("Colors", "TEXT_PRIMARY"),
    "--color-text-secondary":    ("Colors", "TEXT_SECONDARY"),
    "--color-text-disabled":     ("Colors", "TEXT_DISABLED"),
    "--color-text-inverse":      ("Colors", "TEXT_INVERSE"),
    "--color-disabled-bg":       ("Colors", "DISABLED_BG"),
    "--color-disabled-text":     ("Colors", "DISABLED_TEXT"),
    # Navegación
    "--nav-sidebar-text":        ("Colors", "SIDEBAR_TEXT"),
    "--nav-sidebar-hover":       ("Colors", "SIDEBAR_HOVER"),
    "--nav-sidebar-active-bg":   ("Colors", "SIDEBAR_ACTIVE_BG"),
    # Asistencia
    "--attend-presente":         ("AsistenciaColors", "PRESENTE"),
    "--attend-presente-bg":      ("AsistenciaColors", "PRESENTE_BG"),
    "--attend-fj":               ("AsistenciaColors", "FJ"),
    "--attend-fj-bg":            ("AsistenciaColors", "FJ_BG"),
    "--attend-fi":               ("AsistenciaColors", "FI"),
    "--attend-fi-bg":            ("AsistenciaColors", "FI_BG"),
    "--attend-retraso":          ("AsistenciaColors", "RETRASO"),
    "--attend-retraso-bg":       ("AsistenciaColors", "RETRASO_BG"),
    "--attend-excusa":           ("AsistenciaColors", "EXCUSA"),
    "--attend-excusa-bg":        ("AsistenciaColors", "EXCUSA_BG"),
    # Desempeño
    "--desempeno-bajo":          ("DesempenoColors", "BAJO"),
    "--desempeno-bajo-bg":       ("DesempenoColors", "BAJO_BG"),
    "--desempeno-basico":        ("DesempenoColors", "BASICO"),
    "--desempeno-basico-bg":     ("DesempenoColors", "BASICO_BG"),
    "--desempeno-alto":          ("DesempenoColors", "ALTO"),
    "--desempeno-alto-bg":       ("DesempenoColors", "ALTO_BG"),
    "--desempeno-superior":      ("DesempenoColors", "SUPERIOR"),
    "--desempeno-superior-bg":   ("DesempenoColors", "SUPERIOR_BG"),
    # Espaciado
    "--space-xs":                ("Spacing", "XS"),
    "--space-sm":                ("Spacing", "SM"),
    "--space-md":                ("Spacing", "MD"),
    "--space-lg":                ("Spacing", "LG"),
    "--space-xl":                ("Spacing", "XL"),
    "--space-xxl":               ("Spacing", "XXL"),
    # Layout (int — se compara sin la unidad "px")
    "--sidebar-width":           ("Layout", "SIDEBAR_WIDTH"),
    "--sidebar-collapsed":       ("Layout", "SIDEBAR_COLLAPSED"),
    "--topbar-height":           ("Layout", "TOPBAR_HEIGHT"),
    "--content-padding":         ("Layout", "CONTENT_PADDING"),
}

# Atributos de Layout almacenados como int (se compara tras quitar "px")
LAYOUT_PX_ATTRS = {"SIDEBAR_WIDTH", "SIDEBAR_COLLAPSED", "TOPBAR_HEIGHT", "CONTENT_PADDING"}


def _parse_css_vars(css_text: str) -> dict[str, str]:
    """Extrae todas las variables del primer bloque :root { ... } de tokens.css."""
    root_match = re.search(r":root\s*\{(.+?)\n\}", css_text, re.DOTALL)
    if not root_match:
        raise ValueError("No se encontró el bloque :root en tokens.css")

    vars_map: dict[str, str] = {}
    for line in root_match.group(1).splitlines():
        line = re.sub(r"/\*.*?\*/", "", line).strip()   # sin comentarios inline
        m = re.match(r"(--[\w-]+)\s*:\s*(.+?)\s*;", line)
        if m:
            vars_map[m.group(1)] = m.group(2).strip()
    return vars_map


def _resolve(value: str, vars_map: dict[str, str], _seen: tuple[str, ...] = ()) -> str:
    """Resuelve una cadena `var(--x)` (posiblemente encadenada) hasta su literal."""
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*\)", value.strip())
    if not m:
        return value.strip()
    ref = m.group(1)
    if ref in _seen or ref not in vars_map:
        return value.strip()
    return _resolve(vars_map[ref], vars_map, _seen + (ref,))


def _load_tokens_classes() -> dict[str, type]:
    """Importa tokens.py y devuelve las clases relevantes."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.interface.design.styles import tokens
    return {
        "Colors": tokens.Colors,
        "AsistenciaColors": tokens.AsistenciaColors,
        "DesempenoColors": tokens.DesempenoColors,
        "Spacing": tokens.Spacing,
        "Layout": tokens.Layout,
    }


def _norm(value: str) -> str:
    """Normaliza para comparar (hex en minúsculas, sin espacios sobrantes)."""
    v = str(value).strip()
    return v.lower() if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", v) else v


def run(check_only: bool = False) -> int:
    """Verifica que tokens.py refleje tokens.css. Devuelve 0 si OK, 1 si hay drift."""
    if not TOKENS_CSS.exists():
        print(f"ERROR: No se encontró {TOKENS_CSS}")
        return 1

    try:
        css_vars = _parse_css_vars(TOKENS_CSS.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"ERROR parseando tokens.css: {exc}")
        return 1

    classes = _load_tokens_classes()
    drift: list[str] = []
    faltantes: list[str] = []

    for css_var, (cls_name, attr) in MAPPING.items():
        if css_var not in css_vars:
            faltantes.append(f"  {css_var} no existe en tokens.css (esperado por {cls_name}.{attr})")
            continue
        expected = _resolve(css_vars[css_var], css_vars)
        if cls_name == "Layout" and attr in LAYOUT_PX_ATTRS:
            expected = expected.replace("px", "").strip()
            actual = str(getattr(classes[cls_name], attr, None))
        else:
            actual = str(getattr(classes[cls_name], attr, None))
        if _norm(actual) != _norm(expected):
            drift.append(
                f"  {cls_name}.{attr}: tokens.py={actual!r}  ≠  tokens.css[{css_var}]={expected!r}"
            )

    if drift or faltantes:
        print("CHECK FAIL: tokens.py está desincronizado con tokens.css\n")
        for d in drift:
            print(d)
        for f in faltantes:
            print(f)
        print("\n  → Corrige los valores en src/interface/design/tokens.py para que coincidan.")
        return 1

    n = sum(1 for v in MAPPING if v in css_vars)
    print(f"CHECK OK: tokens.py está sincronizado con tokens.css ({n} variables verificadas)")
    return 0


def _resolved_groups() -> dict[str, list[tuple[str, object]]]:
    """Devuelve {clase: [(attr, valor_resuelto), ...]} desde tokens.css.
    Reutiliza el mismo parser/resolver que la verificación → una sola fuente."""
    css_vars = _parse_css_vars(TOKENS_CSS.read_text(encoding="utf-8"))
    groups: dict[str, list[tuple[str, object]]] = {}
    for css_var, (cls_name, attr) in MAPPING.items():
        if css_var not in css_vars:
            continue
        val: object = _resolve(css_vars[css_var], css_vars)
        if cls_name == "Layout" and attr in LAYOUT_PX_ATTRS:
            val = int(str(val).replace("px", "").strip())
        groups.setdefault(cls_name, []).append((attr, val))
    return groups


def emit_ts() -> int:
    """Emite tokens.ts + tokens.json para consumo del futuro frontend Vue."""
    if run(check_only=True) != 0:
        print("\nNo se emite: corrige el drift primero.")
        return 1

    groups = _resolved_groups()
    order = ["Colors", "AsistenciaColors", "DesempenoColors", "Spacing", "Layout"]

    # ── tokens.ts ──
    lines = [
        "// ⚠️  AUTOGENERADO por scripts/sync_tokens.py --emit-ts desde tokens.css.",
        "// NO EDITAR A MANO. Fuente única: src/interface/design/styles/tokens.css.",
        "// Puente de tokens para la migración del frontend a Vue (Etapa B).",
        "",
    ]
    data: dict[str, dict[str, object]] = {}
    for cls in order:
        if cls not in groups:
            continue
        lines.append(f"export const {cls} = {{")
        data[cls] = {}
        for attr, val in groups[cls]:
            ts_val = val if isinstance(val, int) else f'"{val}"'
            lines.append(f"  {attr}: {ts_val},")
            data[cls][attr] = val
        lines.append("} as const;")
        lines.append("")

    ts_path = ROOT / "src" / "interface" / "design" / "styles" / "tokens.ts"
    ts_path.write_text("\n".join(lines), encoding="utf-8")

    # ── tokens.json ──
    import json
    json_path = ROOT / "src" / "interface" / "design" / "styles" / "tokens.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    n = sum(len(v) for v in groups.values())
    print(f"OK: emitidos {n} tokens → tokens.ts y tokens.json")
    return 0


if __name__ == "__main__":
    if "--emit-ts" in sys.argv:
        sys.exit(emit_ts())
    # --check se mantiene por compatibilidad; el comportamiento es el mismo.
    sys.exit(run(check_only="--check" in sys.argv))
