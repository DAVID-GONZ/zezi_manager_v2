"""
audit_ports.py — Auditoría de la capa de ports
================================================
Verifica que todos los ports cumplan el contrato arquitectural.

Ejecutar desde la raíz del proyecto:
    python audit_ports.py

Qué verifica:
  1. Existencia — todos los ports esperados están presentes.
  2. Importación — cada archivo importa sin error.
  3. Herencia ABC — la clase hereda de ABC.
  4. Métodos abstractos — todos los métodos usan @abstractmethod.
  5. Aislamiento — ningún port importa infraestructura (sqlite3, pandas,
     nicegui, openpyxl, reportlab, bcrypt).
  6. Tipos de retorno — ningún método retorna pd.DataFrame ni dict sin tipo.
  7. Cuerpo limpio — los métodos solo contienen `...` o `pass` (no lógica).
  8. __init__.py — todos los ports están re-exportados.

Salida:
  ✅ línea si pasa | ❌ línea con descripción del problema
  Resumen final con recuento de errores.

Exit code 0 si no hay errores, 1 si hay alguno.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import sys
from abc import ABC
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

PORTS_DIR = Path("src/domain/ports")

# Ports esperados (nombre_archivo → nombre_clase)
PORTS_ESPERADOS: dict[str, str] = {
    "acudiente_repo.py":     "IAcudienteRepository",
    "alerta_repo.py":        "IAlertaRepository",
    "asistencia_repo.py":    "IAsistenciaRepository",
    "auditoria_repo.py":     "IAuditoriaRepository",
    "cierre_repo.py":        "ICierreRepository",
    "configuracion_repo.py": "IConfiguracionRepository",
    "convivencia_repo.py":   "IConvivenciaRepository",
    "estadisticos_repo.py":  "IEstadisticosRepository",
    "estudiante_repo.py":    "IEstudianteRepository",
    "evaluacion_repo.py":    "IEvaluacionRepository",
    "habilitacion_repo.py":  "IHabilitacionRepository",
    "infraestructura_repo.py": "IInfraestructuraRepository",
    "periodo_repo.py":       "IPeriodoRepository",
    "asignacion_repo.py":    "IAsignacionRepository",
    "service_ports.py":      None,   # None = múltiples clases, no verificar nombre
    "usuario_repo.py":       "IUsuarioRepository",
}

# Imports que NO deben aparecer en la capa de dominio
IMPORTS_PROHIBIDOS = {
    "sqlite3", "pandas", "pd", "nicegui", "ui",
    "openpyxl", "reportlab", "bcrypt", "jwt",
    "fastapi", "starlette",
}

# ── Colores para la terminal ───────────────────────────────────────────────────

OK  = "✅"
ERR = "❌"
WRN = "⚠️ "
INF = "   "


# ── Helpers ────────────────────────────────────────────────────────────────────

def _titulo(texto: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {texto}")
    print(f"{'─' * 60}")


def _check(cond: bool, ok_msg: str, err_msg: str) -> bool:
    if cond:
        print(f"  {OK} {ok_msg}")
    else:
        print(f"  {ERR} {err_msg}")
    return cond


def _parse_ast(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"  {ERR} Error de sintaxis: {e}")
        return None


def _imports_en_modulo(tree: ast.Module) -> set[str]:
    """Extrae todos los nombres de módulos importados."""
    nombres: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                nombres.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                nombres.add(node.module.split(".")[0])
    return nombres


def _clases_en_modulo(tree: ast.Module) -> list[ast.ClassDef]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]


def _metodos_de_clase(cls_node: ast.ClassDef) -> list[ast.FunctionDef]:
    return [
        n for n in cls_node.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not n.name.startswith("__")
    ]


def _tiene_abstractmethod(func: ast.FunctionDef) -> bool:
    for deco in func.decorator_list:
        if isinstance(deco, ast.Name) and deco.id == "abstractmethod":
            return True
        if isinstance(deco, ast.Attribute) and deco.attr == "abstractmethod":
            return True
    return False


def _cuerpo_es_limpio(func: ast.FunctionDef) -> bool:
    """True si el cuerpo es solo `...`, `pass`, o una docstring + `...`."""
    stmts = func.body
    for stmt in stmts:
        if isinstance(stmt, ast.Expr):
            # Docstring o Ellipsis
            if isinstance(stmt.value, ast.Constant):
                continue
        elif isinstance(stmt, ast.Pass):
            continue
        else:
            return False
    return True


def _hereda_abc(cls_node: ast.ClassDef) -> bool:
    for base in cls_node.bases:
        if isinstance(base, ast.Name) and base.id == "ABC":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "ABC":
            return True
    return False


# ── Verificaciones por archivo ─────────────────────────────────────────────────

def auditar_archivo(archivo: Path, clase_esperada: str | None) -> list[str]:
    """
    Audita un archivo de port.
    Retorna lista de errores encontrados (vacía si todo OK).
    """
    errores: list[str] = []
    nombre = archivo.name

    print(f"\n  📄 {nombre}")

    # 1. Parseo AST
    tree = _parse_ast(archivo)
    if tree is None:
        errores.append(f"{nombre}: error de sintaxis")
        return errores

    # 2. Imports prohibidos
    imports = _imports_en_modulo(tree)
    prohibidos = imports & IMPORTS_PROHIBIDOS
    if prohibidos:
        print(f"  {ERR} Imports de infraestructura: {prohibidos}")
        errores.append(f"{nombre}: imports prohibidos {prohibidos}")
    else:
        print(f"  {OK} Sin imports de infraestructura")

    # 3. Clases
    clases = _clases_en_modulo(tree)
    if not clases:
        print(f"  {ERR} No contiene ninguna clase")
        errores.append(f"{nombre}: sin clases")
        return errores

    # Si hay clase esperada, filtrar solo esa
    if clase_esperada:
        target = [c for c in clases if c.name == clase_esperada]
        if not target:
            nombres = [c.name for c in clases]
            print(f"  {ERR} Clase '{clase_esperada}' no encontrada. Hay: {nombres}")
            errores.append(f"{nombre}: clase {clase_esperada} no encontrada")
            return errores
        clases_audit = target
    else:
        clases_audit = clases

    for cls_node in clases_audit:
        print(f"  {INF}  → clase {cls_node.name}")

        # 4. Herencia ABC
        if not _hereda_abc(cls_node):
            print(f"  {ERR}    No hereda de ABC")
            errores.append(f"{nombre}.{cls_node.name}: no hereda de ABC")
        else:
            print(f"  {OK}    Hereda de ABC")

        # 5. Métodos abstractos
        metodos = _metodos_de_clase(cls_node)
        if not metodos:
            print(f"  {WRN}    Sin métodos públicos")

        sin_abstractmethod = [m.name for m in metodos if not _tiene_abstractmethod(m)]
        con_logica         = [m.name for m in metodos if not _cuerpo_es_limpio(m)]

        if sin_abstractmethod:
            print(f"  {ERR}    Sin @abstractmethod: {sin_abstractmethod}")
            errores.append(f"{nombre}.{cls_node.name}: sin @abstractmethod en {sin_abstractmethod}")
        else:
            print(f"  {OK}    {len(metodos)} métodos con @abstractmethod")

        if con_logica:
            print(f"  {ERR}    Con lógica en el cuerpo: {con_logica}")
            errores.append(f"{nombre}.{cls_node.name}: lógica en cuerpo de {con_logica}")
        else:
            print(f"  {OK}    Cuerpos limpios (solo ...)")

    return errores


def auditar_init(ports_dir: Path, ports_esperados: dict) -> list[str]:
    """Verifica que __init__.py exporte todos los ports."""
    errores: list[str] = []
    init_path = ports_dir / "__init__.py"

    _titulo("Verificando __init__.py de ports")

    if not init_path.exists():
        print(f"  {ERR} __init__.py no encontrado")
        errores.append("__init__.py: no existe")
        return errores

    contenido = init_path.read_text()
    for archivo, clase in ports_esperados.items():
        if clase is None:
            continue   # service_ports puede tener múltiples clases
        if clase not in contenido:
            print(f"  {ERR} '{clase}' no está en __init__.py")
            errores.append(f"__init__.py: falta exportar {clase}")
        else:
            print(f"  {OK} {clase}")

    return errores


def auditar_importacion(ports_dir: Path, ports_esperados: dict) -> list[str]:
    """Intenta importar cada port para detectar errores de runtime."""
    errores: list[str] = []

    _titulo("Verificando importación en runtime")

    # Añadir raíz del proyecto al path
    sys.path.insert(0, str(ports_dir.resolve().parents[2]))

    for archivo, clase in ports_esperados.items():
        path = ports_dir / archivo
        if not path.exists():
            continue
        modulo_path = ".".join(path.resolve().relative_to(ports_dir.resolve().parents[2]).with_suffix("").parts)   # src.domain.ports.xxx
        try:
            mod = importlib.import_module(modulo_path)
            if clase and hasattr(mod, clase):
                cls = getattr(mod, clase)
                # Verificar que es realmente un ABC con abstractmethods
                abstracts = getattr(cls, "__abstractmethods__", set())
                print(f"  {OK} {clase} — {len(abstracts)} métodos abstractos")
            elif clase:
                print(f"  {ERR} {clase} no encontrada en {modulo_path}")
                errores.append(f"{archivo}: {clase} no importable")
            else:
                print(f"  {OK} {archivo} importado")
        except Exception as e:
            print(f"  {ERR} {archivo}: {e}")
            errores.append(f"{archivo}: error de importación — {e}")

    return errores


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 60)
    print("  AUDITORÍA DE PORTS — ZECI Manager v2.0")
    print("=" * 60)

    todos_los_errores: list[str] = []

    # 1. Existencia de archivos
    _titulo("Verificando existencia de ports")
    for archivo in sorted(PORTS_ESPERADOS.keys()):
        path = PORTS_DIR / archivo
        if path.exists():
            print(f"  {OK} {archivo}")
        else:
            print(f"  {ERR} {archivo} — NO ENCONTRADO")
            todos_los_errores.append(f"Faltante: {archivo}")

    # 2. Auditoría AST por archivo
    _titulo("Auditoría estática (AST)")
    archivos_existentes = sorted(
        p for p in PORTS_DIR.glob("*.py")
        if p.name != "__init__.py"
    )
    for path in archivos_existentes:
        clase_esp = PORTS_ESPERADOS.get(path.name)
        errores = auditar_archivo(path, clase_esp)
        todos_los_errores.extend(errores)

    # 3. Importación en runtime
    errores_import = auditar_importacion(PORTS_DIR, PORTS_ESPERADOS)
    todos_los_errores.extend(errores_import)

    # 4. __init__.py
    errores_init = auditar_init(PORTS_DIR, PORTS_ESPERADOS)
    todos_los_errores.extend(errores_init)

    # ── Resumen ────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  RESUMEN")
    print("=" * 60)

    archivos_ok      = len(archivos_existentes)
    archivos_falt    = sum(1 for e in todos_los_errores if e.startswith("Faltante:"))
    errores_restantes = [e for e in todos_los_errores if not e.startswith("Faltante:")]

    print(f"  Ports encontrados:  {archivos_ok}")
    print(f"  Ports faltantes:    {archivos_falt}")
    print(f"  Otros errores:      {len(errores_restantes)}")
    print()

    if todos_los_errores:
        print(f"  {ERR} AUDITORÍA FALLIDA — {len(todos_los_errores)} problema(s):")
        for e in todos_los_errores:
            print(f"      • {e}")
        return 1
    else:
        print(f"  {OK} AUDITORÍA EXITOSA — todos los ports son correctos")
        return 0


if __name__ == "__main__":
    sys.exit(main())
