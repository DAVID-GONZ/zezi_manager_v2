"""
audit_interface.py — Auditoría de componentes e interfaz
=========================================================
Verifica estructura, importaciones, coherencia con design system
y contratos mínimos de cada componente.

Exit code 0 si todo OK, 1 si hay errores.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

OK  = "✅"
ERR = "❌"
WRN = "⚠️ "

# ── Componentes esperados ─────────────────────────────────────────────────────

COMPONENTS_DIR = Path("src/interface/design/components")
CONTEXT_DIR    = Path("src/interface/context")

COMPONENTES_ESPERADOS = {
    "base_form.py": {
        "descripcion": "Formulario base reutilizable",
        "funciones_minimas": ["base_form"],
        "debe_usar": ["ui"],
    },
    "confirm_dialog.py": {
        "descripcion": "Diálogo de confirmación modal",
        "funciones_minimas": ["confirm_dialog"],
        "debe_usar": ["ui"],
    },
    "confirmation_card.py": {
        "descripcion": "Tarjeta de confirmación (alternativa inline al diálogo)",
        "funciones_minimas": ["confirmation_card"],
        "debe_usar": ["ui"],
    },
    "context_bar.py": {
        "descripcion": "Barra de contexto activo (año/periodo/grupo/asignación)",
        "funciones_minimas": ["context_bar"],
        "debe_usar": ["ui"],
    },
    "data_table.py": {
        "descripcion": "Tabla de datos estándar del sistema",
        "funciones_minimas": ["data_table"],
        "debe_usar": ["ui"],
    },
    "page_header.py": {
        "descripcion": "Encabezado estándar de página",
        "funciones_minimas": ["page_header"],
        "debe_usar": ["ui"],
    },
    "performance_indicator.py": {
        "descripcion": "Indicador de desempeño académico (barra o gauge)",
        "funciones_minimas": ["performance_indicator"],
        "debe_usar": ["ui"],
    },
    "stat_card.py": {
        "descripcion": "Tarjeta de estadística para dashboard",
        "funciones_minimas": ["stat_card"],
        "debe_usar": ["ui"],
    },
    "status_badge.py": {
        "descripcion": "Badge de estado (asistencia, desempeño, periodo)",
        "funciones_minimas": ["status_badge"],
        "debe_usar": ["ui"],
    },
}

CONTEXT_ESPERADOS = {
    "session_context.py": {
        "descripcion": "Gestión del contexto de sesión activa",
        "clases_o_funciones": ["SessionContext"],
        "atributos_minimos": [
            "usuario_id", "usuario_nombre", "usuario_rol",
            "anio_id", "periodo_id",
        ],
    },
}

# Tokens del design system que los componentes DEBEN referenciar
TOKENS_ESPERADOS = [
    "--color-primary", "--color-bg", "--color-surface",
    "--color-text-primary", "--color-text-secondary",
    "--color-divider",
]

# Imports prohibidos en la capa de interfaz
IMPORTS_PROHIBIDOS = {
    "sqlite3", "pandas", "bcrypt",
    "SqliteEstudianteRepository", "SqliteUsuarioRepository",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def titulo(texto: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {texto}")
    print(f"{'─' * 62}")


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"  {ERR} Error de sintaxis en {path.name}: {e}")
        return None


def _nombres_definidos(tree: ast.Module) -> set[str]:
    nombres = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nombres.add(node.name)
        elif isinstance(node, ast.ClassDef):
            nombres.add(node.name)
    return nombres


def _imports_usados(tree: ast.Module) -> set[str]:
    nombres = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                nombres.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                nombres.add(node.module.split(".")[0])
            for a in node.names:
                nombres.add(a.name)
    return nombres


def _usa_design_tokens(path: Path) -> bool:
    """True si el archivo referencia al menos un token CSS del design system."""
    contenido = path.read_text(encoding="utf-8")
    return any(token in contenido for token in TOKENS_ESPERADOS)


def _usa_nicegui(tree: ast.Module) -> bool:
    imports = _imports_usados(tree)
    return "nicegui" in imports or "ui" in imports


def _tiene_imports_prohibidos(tree: ast.Module) -> set[str]:
    imports = _imports_usados(tree)
    return imports & IMPORTS_PROHIBIDOS


def _init_exporta(init_path: Path, nombres: list[str]) -> list[str]:
    """Retorna los nombres que NO están exportados en __init__.py."""
    if not init_path.exists():
        return nombres
    contenido = init_path.read_text(encoding="utf-8")
    return [n for n in nombres if n not in contenido]


# ── Auditoría de componentes ──────────────────────────────────────────────────

def auditar_componente(path: Path, spec: dict) -> list[str]:
    errores = []
    nombre = path.name
    print(f"\n  📄 {nombre}  —  {spec['descripcion']}")

    # 1. Parse
    tree = _parse(path)
    if tree is None:
        errores.append(f"{nombre}: error de sintaxis")
        return errores

    # 2. Imports prohibidos
    prohibidos = _tiene_imports_prohibidos(tree)
    if prohibidos:
        print(f"  {ERR} Imports prohibidos: {prohibidos}")
        errores.append(f"{nombre}: imports prohibidos {prohibidos}")
    else:
        print(f"  {OK} Sin imports de infraestructura")

    # 3. Usa NiceGUI
    if _usa_nicegui(tree):
        print(f"  {OK} Importa NiceGUI")
    else:
        print(f"  {WRN} No importa NiceGUI (¿es un helper puro?)")

    # 4. Funciones/clases mínimas
    definidos = _nombres_definidos(tree)
    for fn in spec.get("funciones_minimas", []):
        if fn in definidos:
            print(f"  {OK} Define '{fn}'")
        else:
            print(f"  {ERR} Falta definir '{fn}'")
            errores.append(f"{nombre}: falta '{fn}'")

    # 5. Usa tokens de design system
    if _usa_design_tokens(path):
        print(f"  {OK} Referencia tokens CSS del design system")
    else:
        print(f"  {WRN} No referencia tokens CSS (--color-primary, etc.)")

    return errores


def auditar_contexto(path: Path, spec: dict) -> list[str]:
    errores = []
    nombre = path.name
    print(f"\n  📄 {nombre}  —  {spec['descripcion']}")

    tree = _parse(path)
    if tree is None:
        return [f"{nombre}: error de sintaxis"]

    # Clases/funciones mínimas
    definidos = _nombres_definidos(tree)
    for nombre_esperado in spec.get("clases_o_funciones", []):
        if nombre_esperado in definidos:
            print(f"  {OK} Define '{nombre_esperado}'")
        else:
            print(f"  {ERR} Falta definir '{nombre_esperado}'")
            errores.append(f"{nombre}: falta '{nombre_esperado}'")

    # Atributos mínimos esperados (buscar en el texto plano)
    contenido = path.read_text(encoding="utf-8")
    for attr in spec.get("atributos_minimos", []):
        if attr in contenido:
            print(f"  {OK} Contiene '{attr}'")
        else:
            print(f"  {ERR} No contiene '{attr}'")
            errores.append(f"{nombre}: falta atributo '{attr}'")

    # No debe importar infraestructura
    prohibidos = _tiene_imports_prohibidos(tree)
    if prohibidos:
        print(f"  {ERR} Imports prohibidos: {prohibidos}")
        errores.append(f"{nombre}: imports prohibidos {prohibidos}")
    else:
        print(f"  {OK} Sin imports de infraestructura")

    return errores


def auditar_init(directorio: Path, nombres_esperados: list[str]) -> list[str]:
    errores = []
    init = directorio / "__init__.py"
    if not init.exists():
        print(f"  {ERR} __init__.py no existe en {directorio}")
        return [f"{directorio}/__init__.py: no existe"]

    faltantes = _init_exporta(init, nombres_esperados)
    if faltantes:
        for f in faltantes:
            print(f"  {ERR} '{f}' no exportado en __init__.py")
            errores.append(f"__init__.py de {directorio.name}: falta exportar '{f}'")
    else:
        print(f"  {OK} __init__.py exporta todos los nombres esperados")

    return errores


def verificar_importacion(modulo_path: str, clase_o_fn: str) -> bool:
    try:
        mod = importlib.import_module(modulo_path)
        if hasattr(mod, clase_o_fn):
            print(f"  {OK} {modulo_path}.{clase_o_fn} importa en runtime")
            return True
        else:
            print(f"  {ERR} {clase_o_fn} no encontrado en {modulo_path}")
            return False
    except Exception as e:
        print(f"  {ERR} Error importando {modulo_path}: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 62)
    print("  AUDITORÍA DE INTERFAZ — ZECI Manager v2.0")
    print("=" * 62)

    todos_los_errores: list[str] = []

    # ── 1. Existencia de archivos ─────────────────────────────────────────────
    titulo("1. Existencia de archivos — Componentes")

    for archivo in sorted(COMPONENTES_ESPERADOS.keys()):
        path = COMPONENTS_DIR / archivo
        if path.exists():
            print(f"  {OK} {archivo}")
        else:
            print(f"  {ERR} {archivo} — NO ENCONTRADO")
            todos_los_errores.append(f"Faltante: components/{archivo}")

    init_comp = COMPONENTS_DIR / "__init__.py"
    if init_comp.exists():
        print(f"  {OK} __init__.py")
    else:
        print(f"  {ERR} __init__.py — NO ENCONTRADO")
        todos_los_errores.append("Faltante: components/__init__.py")

    titulo("2. Existencia de archivos — Context")

    if CONTEXT_DIR.exists():
        print(f"  {OK} Directorio context/ existe")
    else:
        print(f"  {ERR} Directorio context/ NO ENCONTRADO")
        todos_los_errores.append("Faltante: src/interface/context/")

    for archivo in sorted(CONTEXT_ESPERADOS.keys()):
        path = CONTEXT_DIR / archivo
        if path.exists():
            print(f"  {OK} {archivo}")
        else:
            print(f"  {ERR} {archivo} — NO ENCONTRADO")
            todos_los_errores.append(f"Faltante: context/{archivo}")

    # ── 2. Auditoría estática de componentes ─────────────────────────────────
    titulo("3. Auditoría estática — Componentes")

    for archivo, spec in COMPONENTES_ESPERADOS.items():
        path = COMPONENTS_DIR / archivo
        if path.exists():
            errores = auditar_componente(path, spec)
            todos_los_errores.extend(errores)

    # ── 3. Auditoría estática de context ─────────────────────────────────────
    titulo("4. Auditoría estática — Context")

    for archivo, spec in CONTEXT_ESPERADOS.items():
        path = CONTEXT_DIR / archivo
        if path.exists():
            errores = auditar_contexto(path, spec)
            todos_los_errores.extend(errores)

    # ── 4. Verificar __init__.py ──────────────────────────────────────────────
    titulo("5. Verificación de __init__.py")

    nombres_comp = [
        spec["funciones_minimas"][0]
        for spec in COMPONENTES_ESPERADOS.values()
        if spec.get("funciones_minimas")
    ]
    errores_init_comp = auditar_init(COMPONENTS_DIR, nombres_comp)
    todos_los_errores.extend(errores_init_comp)

    nombres_ctx = [
        n for spec in CONTEXT_ESPERADOS.values()
        for n in spec.get("clases_o_funciones", [])
    ]
    errores_init_ctx = auditar_init(CONTEXT_DIR, nombres_ctx)
    todos_los_errores.extend(errores_init_ctx)

    # ── 5. Verificar imports en runtime ──────────────────────────────────────
    titulo("6. Verificación de importación en runtime")

    runtime_checks = [
        ("src.interface.design.components.status_badge",      "status_badge"),
        ("src.interface.design.components.stat_card",         "stat_card"),
        ("src.interface.design.components.page_header",       "page_header"),
        ("src.interface.design.components.data_table",        "data_table"),
        ("src.interface.design.components.confirm_dialog",    "confirm_dialog"),
        ("src.interface.design.components.confirmation_card", "confirmation_card"),
        ("src.interface.design.components.context_bar",       "context_bar"),
        ("src.interface.design.components.performance_indicator", "performance_indicator"),
        ("src.interface.design.components.base_form",         "base_form"),
        ("src.interface.context.session_context",             "SessionContext"),
    ]

    for modulo, nombre in runtime_checks:
        path = Path(modulo.replace(".", "/") + ".py")
        if path.exists():
            ok = verificar_importacion(modulo, nombre)
            if not ok:
                todos_los_errores.append(f"Runtime: {modulo}.{nombre} no importable")

    # ── 6. Verificar coherencia con design system ─────────────────────────────
    titulo("7. Coherencia con design system — Tokens CSS")

    archivos_con_tokens = 0
    for archivo in COMPONENTES_ESPERADOS:
        path = COMPONENTS_DIR / archivo
        if path.exists() and _usa_design_tokens(path):
            archivos_con_tokens += 1

    total = len(COMPONENTES_ESPERADOS)
    pct = archivos_con_tokens / total * 100 if total else 0
    if pct >= 70:
        print(f"  {OK} {archivos_con_tokens}/{total} componentes usan tokens CSS ({pct:.0f}%)")
    else:
        print(f"  {WRN} Solo {archivos_con_tokens}/{total} componentes usan tokens CSS ({pct:.0f}%)")
        print(f"      Revisar que los componentes usen var(--color-primary) etc.")

    # ── 7. Verificar styles.css y tokens.py ──────────────────────────────────
    titulo("8. Archivos del design system")

    design_files = [
        Path("src/interface/design/styles.css"),
        Path("src/interface/design/tokens.py"),
        Path("src/interface/design/theme.py"),
        Path("src/interface/design/layout.py"),
        Path("src/interface/pages/login.py"),
    ]

    for f in design_files:
        if f.exists() and f.stat().st_size > 100:
            print(f"  {OK} {f}  ({f.stat().st_size:,} bytes)")
        elif f.exists():
            print(f"  {WRN} {f}  (archivo muy pequeño — ¿vacío?)")
        else:
            print(f"  {ERR} {f}  — NO ENCONTRADO")
            todos_los_errores.append(f"Faltante: {f}")

    # ── Resumen ───────────────────────────────────────────────────────────────
    print()
    print("=" * 62)
    print("  RESUMEN")
    print("=" * 62)

    faltantes     = [e for e in todos_los_errores if e.startswith("Faltante:")]
    otros_errores = [e for e in todos_los_errores if not e.startswith("Faltante:")]

    print(f"  Componentes auditados:  {len(COMPONENTES_ESPERADOS)}")
    print(f"  Archivos faltantes:     {len(faltantes)}")
    print(f"  Otros errores:          {len(otros_errores)}")
    print()

    if todos_los_errores:
        print(f"  {ERR} AUDITORÍA FALLIDA — {len(todos_los_errores)} problema(s):")
        for e in todos_los_errores:
            print(f"      • {e}")
        return 1
    else:
        print(f"  {OK} AUDITORÍA EXITOSA — todos los componentes son correctos")
        return 0


if __name__ == "__main__":
    sys.exit(main())
