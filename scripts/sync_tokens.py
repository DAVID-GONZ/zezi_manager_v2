"""
sync_tokens.py — tokens.json como fuente canonica del design system
====================================================================
tokens.json (W3C Design Tokens, 3 capas + dark) es la FUENTE UNICA.
Este script lee tokens.json y puede:
  1. Verificar que tokens.css en disco coincide (semanticamente) con el JSON.
  2. Generar/regenerar tokens.css desde el JSON.
  3. Verificar que tokens.py esta sincronizado con el JSON.
  4. Emitir tokens.ts + tokens.json plano para el fork Vue (Etapa B).

Uso:
    python scripts/sync_tokens.py            # verifica; exit 1 si hay drift
    python scripts/sync_tokens.py --check    # idem (alias explícito para CI)
    python scripts/sync_tokens.py --generate-css  # genera/regenera tokens.css
    python scripts/sync_tokens.py --emit-ts  # emite tokens.ts para el fork Vue

Notas:
    - El modo por defecto (sin flags) ejecuta el check. Exit 0=OK, 1=drift.
    - --generate-css reescribe tokens.css desde tokens.json (regeneracion).
    - --check solo verifica; nunca escribe archivos.
    - --emit-ts genera src/interface/design/styles/tokens.ts (puente Vue).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# --- Consola UTF-8 (Windows) --------------------------------------------------
# En consolas cp1252 imprimir caracteres especiales tumbaba el script con
# UnicodeEncodeError. Se arregla aqui, en origen, para no depender de que
# cada invocacion recuerde PYTHONIOENCODING=utf-8.
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
# ------------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
TOKENS_JSON = ROOT / "tokens.json"
TOKENS_CSS = ROOT / "src" / "interface" / "design" / "styles" / "tokens.css"

# ── Mapping: variable CSS → (clase Python, atributo) ────────────────────
# Solo las variables que tienen un espejo directo en tokens.py.
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
    # Colors — semanticos
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
    # Navegacion
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
    # Desempeno
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

# ── Orden de emision para el bloque :root {} ─────────────────────────────────
# Debe coincidir con el orden de aparicion en tokens.css.
EMISSION_ORDER: list[tuple[str, str]] = [
    ("primitives", "color"),
    ("semantic", "color-primary"),
    ("semantic", "color-secondary"),
    ("semantic", "color-semantic"),
    ("semantic", "color-surface"),
    ("semantic", "nav"),
    ("semantic", "attend"),
    ("semantic", "desempeno"),
    ("semantic", "module"),
    ("primitives", "font"),
    ("primitives", "spacing"),
    ("primitives", "layout"),
    ("primitives", "radius"),
    ("primitives", "shadow-neutral"),
    ("semantic", "shadow"),
    ("component", "button"),
    ("component", "input"),
    ("component", "badge"),
    ("component", "table"),
    ("primitives", "z-index"),
    ("primitives", "transition"),
]

# Orden de emision de los grupos del bloque dark mode
DARK_ORDER: list[str] = [
    "color-surface",
    "color-text",
    "color-border",
    "color-semantic",
    "shadow",
    "nav",
    "color-primary",
    "module",
]

# ── Cabecera CSS ──────────────────────────────────────────────────────────────
_CSS_HEADER = """\
/* ═══════════════════════════════════════════════════════════════
   tokens.css — Aula Serena
   Paleta: tinta académica + ocre + neutros cálidos + semánticos desaturados
   Generado / sincronizado por scripts/sync_tokens.py
   ═══════════════════════════════════════════════════════════════ */

/* ── Google Fonts ────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300..900;1,8..60,300..900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,300,0,0');"""

# ── Bloques de accesibilidad (estaticos — raramente cambian) ─────────────────
_CSS_ACCESSIBILITY = """\
/* ── Accesibilidad: alto contraste ───────────────────────── */
@media (prefers-contrast: more) {
  :root {
    --color-primary:        var(--ink-900);   /* #1A1B6E — fix: era #0F1E3D de paleta anterior */
    --color-primary-dark:   var(--ink-900);
    --color-text-primary:   #000000;
    --color-text-secondary: #1A1A1A;
    --color-border:         #1A1A1A;
    --color-divider:        rgba(0, 0, 0, 0.25);
  }
}

/* ── Accesibilidad: movimiento reducido ──────────────────── */
@media (prefers-reduced-motion: reduce) {
  :root {
    --transition-fast: linear;
    --transition-base: linear;
    --transition-slow: linear;
  }
}"""

# ── Comentarios de seccion por grupo ─────────────────────────────────────────
_SECTION_COMMENTS: dict[tuple[str, str], str] = {
    ("primitives", "color"):       "  /* ── Familias internas ─────────────────────────────────── */",
    ("semantic", "color-primary"): "  /* ── API pública — Primario ─────────────────────────────── */",
    ("semantic", "color-secondary"): "  /* ── API pública — Secundario ───────────────────────────── */",
    ("semantic", "color-semantic"): "  /* ── API pública — Semánticos desaturados ───────────────── */",
    ("semantic", "color-surface"):  "  /* ── API pública — Superficies y Textos ─────────────────── */",
    ("semantic", "nav"):            "  /* ── Navegación — Sidebar claro ─────────────────────────── */",
    ("semantic", "attend"):         "  /* ── Dominio — Asistencia ────────────────────────────────── */",
    ("semantic", "desempeno"):      "  /* ── Dominio — Desempeño ─────────────────────────────────── */",
    ("semantic", "module"):         "  /* ── Identidad de módulos (más vibrante que los semánticos) ─ */",
    ("primitives", "font"):         "  /* ── Tipografía ──────────────────────────────────────────── */",
    ("primitives", "spacing"):      "  /* ── Espaciado ───────────────────────────────────────────── */",
    ("primitives", "layout"):       "  /* ── Layout ──────────────────────────────────────────────── */",
    ("primitives", "radius"):       "  /* ── Bordes ──────────────────────────────────────────────── */",
    ("primitives", "shadow-neutral"): (
        "  /* ── Sombras neutrales ─────────────────────────────────────\n"
        "     Primitivas: NO se sobrescriben en dark (igual que ink/paper/graphite).\n"
        "     Las consume cualquier superficie anclada a claro (p. ej. .mkt-page). */"
    ),
    ("semantic", "shadow"):         "  /* API publica de sombra — esta si se re-tinta en dark. */",
    ("component", "button"):        "  /* ── Componentes (compatibilidad) ────────────────────────── */",
    ("primitives", "z-index"):      "  /* ── Z-index (T2) ────────────────────────────────────────── */",
    ("primitives", "transition"):   "  /* ── Transiciones ────────────────────────────────────────── */",
}

# Comentarios de seccion para dark mode
_DARK_COMMENTS: dict[str, str] = {
    "color-surface": "  /* Fondos */",
    "color-text":    "  /* Texto */",
    "color-border":  "  /* Bordes */",
    "color-semantic": (
        "  /* Semánticos-light en dark — tintes oscuros en vez de pasteles claros */"
    ),
    "shadow":        "  /* Sombras con tinte índigo */",
    "nav":           "  /* Navegación — sidebar oscuro */",
    "color-primary": "  /* Primario — más claro en dark para mejores ratios */",
    "module":        "  /* Identidad de módulos — aclara acento, oscurece fondo como tinte */",
}


# ── Funciones principales ─────────────────────────────────────────────────────

def cargar_tokens() -> dict:
    """Lee y devuelve el contenido de tokens.json."""
    if not TOKENS_JSON.exists():
        print(f"ERROR: No se encontro {TOKENS_JSON}", file=sys.stderr)
        sys.exit(1)
    with TOKENS_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def resolver_valor(value: str, tokens: dict, _seen: tuple[str, ...] = ()) -> str:
    """Resuelve referencias var(--x) hasta el literal, buscando en todas las capas."""
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*\)", value.strip())
    if not m:
        return value.strip()
    ref = m.group(1)
    if ref in _seen:
        return value.strip()
    # Buscar en primitives primero, luego semantic
    for layer_name in ("primitives", "semantic", "component"):
        layer = tokens.get(layer_name, {})
        for group in layer.values():
            if isinstance(group, dict) and ref in group:
                nested = group[ref].get("$value", ref)
                return resolver_valor(nested, tokens, _seen + (ref,))
    return value.strip()


def _flat_root_vars(tokens: dict) -> list[tuple[str, str]]:
    """Genera la lista ordenada (nombre, valor) del bloque :root desde tokens.json."""
    result: list[tuple[str, str]] = []
    for layer_key, group_key in EMISSION_ORDER:
        group = tokens.get(layer_key, {}).get(group_key, {})
        for name, token in group.items():
            result.append((name, token["$value"]))
    return result


def _flat_dark_vars(tokens: dict) -> list[tuple[str, str]]:
    """Genera la lista ordenada (nombre, valor) del bloque dark desde tokens.json."""
    result: list[tuple[str, str]] = []
    dark = tokens.get("dark", {})
    for group_key in DARK_ORDER:
        group = dark.get(group_key, {})
        for name, token in group.items():
            result.append((name, token["$value"]))
    return result


def _parse_css_block(css_text: str, selector: str) -> list[tuple[str, str]]:
    """
    Extrae variables de un bloque CSS identificado por su selector.
    Devuelve lista ordenada de (nombre, valor).
    """
    # Escapar los caracteres especiales en el selector para regex
    sel_escaped = re.escape(selector)
    # Buscar el bloque del selector
    pattern = sel_escaped + r"\s*\{(.+?)\}"
    m = re.search(pattern, css_text, re.DOTALL)
    if not m:
        return []
    result: list[tuple[str, str]] = []
    for line in m.group(1).splitlines():
        line = re.sub(r"/\*.*?\*/", "", line).strip()
        mv = re.match(r"(--[\w-]+)\s*:\s*(.+?)\s*;", line)
        if mv:
            result.append((mv.group(1), mv.group(2).strip()))
    return result


def generar_css(tokens: dict) -> str:
    """Genera el string CSS completo desde tokens.json."""
    lines: list[str] = []
    lines.append(_CSS_HEADER)
    lines.append("")
    lines.append("/* ── Variables CSS del design system ────────────────────── */")
    lines.append(":root {")

    prev_layer = None
    for layer_key, group_key in EMISSION_ORDER:
        group = tokens.get(layer_key, {}).get(group_key, {})
        if not group:
            continue

        # Linea en blanco entre secciones (excepto la primera)
        if prev_layer is not None:
            lines.append("")

        comment = _SECTION_COMMENTS.get((layer_key, group_key))
        if comment:
            lines.append(comment)

        # Para la seccion nav, separar sidebar y topbar con comentario extra
        if layer_key == "semantic" and group_key == "nav":
            topbar_start = False
            for name, token in group.items():
                if name.startswith("--nav-topbar") and not topbar_start:
                    lines.append("")
                    lines.append(
                        "  /* ── Navegación — Topbar claro (paso_13a) ───────────────── */"
                    )
                    topbar_start = True
                lines.append(f"  {name}: {token['$value']};")
        # Para shadow-neutral, no hay distincion de subseccion
        else:
            for name, token in group.items():
                lines.append(f"  {name}: {token['$value']};")

        prev_layer = (layer_key, group_key)

    lines.append("}")
    lines.append("")
    lines.append(_CSS_ACCESSIBILITY)
    lines.append("")

    # Dark mode — bloque :root[data-theme="dark"]
    dark_vars = _flat_dark_vars(tokens)
    if dark_vars:
        dark = tokens.get("dark", {})
        lines.append('/* ── T6: Modo oscuro estructural (paso_13a) ──────────────── */')
        lines.append(
            '/* Solo sobrescribe la API pública semántica (--color-*, --nav-*, --shadow-*).\n'
            '   Los primitivos ink/paper/graphite y los colores de dominio permanecen\n'
            '   inalterados — la paleta académica se preserva en ambos modos. */'
        )
        lines.append(':root[data-theme="dark"] {')
        for group_key in DARK_ORDER:
            group = dark.get(group_key, {})
            if not group:
                continue
            comment = _DARK_COMMENTS.get(group_key)
            if comment:
                lines.append(comment)
            for name, token in group.items():
                lines.append(f"  {name}: {token['$value']};")
            lines.append("")
        # Quitar ultima linea en blanco extra y cerrar
        if lines[-1] == "":
            lines.pop()
        lines.append("")
        lines.append(
            "  /* Topbar — hereda automáticamente vía var(--color-surface) y var(--color-border) */"
        )
        lines.append("}")
        lines.append("")

        # Dark mode — @media prefers-color-scheme
        lines.append("@media (prefers-color-scheme: dark) {")
        lines.append("  :root:not([data-theme=\"light\"]) {")
        for group_key in DARK_ORDER:
            group = dark.get(group_key, {})
            if not group:
                continue
            comment = _DARK_COMMENTS.get(group_key)
            if comment:
                # Indentar el comentario un nivel extra dentro del media query
                lines.append("  " + comment.strip())
            for name, token in group.items():
                lines.append(f"    {name}: {token['$value']};")
            lines.append("")
        if lines[-1] == "":
            lines.pop()
        lines.append("  }")
        lines.append("}")

    return "\n".join(lines) + "\n"


def _load_tokens_classes() -> dict[str, type]:
    """Importa tokens.py y devuelve las clases relevantes."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.interface.design.styles import tokens  # type: ignore[import]
    return {
        "Colors": tokens.Colors,
        "AsistenciaColors": tokens.AsistenciaColors,
        "DesempenoColors": tokens.DesempenoColors,
        "Spacing": tokens.Spacing,
        "Layout": tokens.Layout,
    }


def _norm(value: str) -> str:
    """Normaliza para comparar (hex en minusculas, sin espacios sobrantes)."""
    v = str(value).strip()
    return v.lower() if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", v) else v


def verificar_tokens_py(tokens: dict) -> list[str]:
    """
    Compara tokens.py contra tokens.json (resolviendo var(--x)).
    Devuelve lista de mensajes de drift (vacia si OK).
    """
    classes = _load_tokens_classes()
    drift: list[str] = []
    faltantes: list[str] = []

    # Construir mapa plano de la fuente canonica (JSON)
    json_vars: dict[str, str] = {}
    for layer in ("primitives", "semantic", "component"):
        for group in tokens.get(layer, {}).values():
            if isinstance(group, dict):
                for name, token in group.items():
                    if isinstance(token, dict):
                        json_vars[name] = token.get("$value", "")

    for css_var, (cls_name, attr) in MAPPING.items():
        if css_var not in json_vars:
            faltantes.append(
                f"  {css_var} no existe en tokens.json (esperado por {cls_name}.{attr})"
            )
            continue
        expected = resolver_valor(json_vars[css_var], tokens)
        if cls_name == "Layout" and attr in LAYOUT_PX_ATTRS:
            expected = expected.replace("px", "").strip()
            actual = str(getattr(classes[cls_name], attr, None))
        else:
            actual = str(getattr(classes[cls_name], attr, None))
        if _norm(actual) != _norm(expected):
            drift.append(
                f"  {cls_name}.{attr}: tokens.py={actual!r}  !=  tokens.json[{css_var}]={expected!r}"
            )

    return drift + faltantes


def _parse_root_from_disk() -> list[tuple[str, str]]:
    """Lee tokens.css del disco y extrae las variables del bloque :root {}."""
    if not TOKENS_CSS.exists():
        return []
    css_text = TOKENS_CSS.read_text(encoding="utf-8")
    return _parse_css_block(css_text, ":root")


def run() -> int:
    """
    Verifica que tokens.css y tokens.py reflejen tokens.json.
    Devuelve 0 si OK, 1 si hay drift.
    """
    tokens = cargar_tokens()

    # 1. Comparar bloque :root del CSS en disco contra lo que genera el JSON
    disk_vars = dict(_parse_root_from_disk())
    json_vars_ordered = _flat_root_vars(tokens)

    css_drift: list[str] = []
    for name, json_val in json_vars_ordered:
        if name not in disk_vars:
            css_drift.append(f"  {name}: existe en tokens.json pero NO en tokens.css")
        elif disk_vars[name] != json_val:
            css_drift.append(
                f"  {name}: tokens.css={disk_vars[name]!r}  !=  tokens.json={json_val!r}"
            )

    for name in disk_vars:
        if name not in dict(json_vars_ordered):
            css_drift.append(f"  {name}: existe en tokens.css pero NO en tokens.json")

    # 2. Comparar tokens.py
    py_drift = verificar_tokens_py(tokens)

    if css_drift or py_drift:
        if css_drift:
            print("CHECK FAIL: tokens.css no coincide con tokens.json\n")
            for d in css_drift:
                print(d)
        if py_drift:
            print("\nCHECK FAIL: tokens.py desincronizado con tokens.json\n")
            for d in py_drift:
                print(d)
        print(
            "\n  Para regenerar tokens.css: python scripts/sync_tokens.py --generate-css"
        )
        return 1

    n_css = len(json_vars_ordered)
    n_py = sum(1 for v in MAPPING if v in dict(json_vars_ordered))
    print(
        f"CHECK OK: tokens.css sincronizado con tokens.json ({n_css} variables en :root)\n"
        f"          tokens.py sincronizado ({n_py} variables verificadas)"
    )
    return 0


def emit_ts(tokens: dict) -> int:
    """Emite tokens.ts para consumo del futuro frontend Vue."""
    # Construir grupos desde el MAPPING
    json_vars: dict[str, str] = {}
    for layer in ("primitives", "semantic", "component"):
        for group in tokens.get(layer, {}).values():
            if isinstance(group, dict):
                for name, token in group.items():
                    if isinstance(token, dict):
                        json_vars[name] = token.get("$value", "")

    groups: dict[str, list[tuple[str, object]]] = {}
    for css_var, (cls_name, attr) in MAPPING.items():
        if css_var not in json_vars:
            continue
        val: object = resolver_valor(json_vars[css_var], tokens)
        if cls_name == "Layout" and attr in LAYOUT_PX_ATTRS:
            val = int(str(val).replace("px", "").strip())
        groups.setdefault(cls_name, []).append((attr, val))

    order = ["Colors", "AsistenciaColors", "DesempenoColors", "Spacing", "Layout"]
    lines = [
        "// AUTOGENERADO por scripts/sync_tokens.py --emit-ts desde tokens.json.",
        "// NO EDITAR A MANO. Fuente unica: tokens.json (W3C Design Tokens).",
        "// Puente de tokens para la migracion del frontend a Vue (Etapa B).",
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

    n = sum(len(v) for v in groups.values())
    print(f"OK: emitidos {n} tokens → {ts_path}")
    return 0


if __name__ == "__main__":
    tokens_data = cargar_tokens()

    if "--generate-css" in sys.argv:
        css_content = generar_css(tokens_data)
        TOKENS_CSS.write_text(css_content, encoding="utf-8")
        print(f"OK: tokens.css regenerado desde tokens.json ({TOKENS_CSS})")
        sys.exit(0)

    if "--emit-ts" in sys.argv:
        sys.exit(emit_ts(tokens_data))

    # --check es alias del modo por defecto
    sys.exit(run())
