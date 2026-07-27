"""
generate_uml.py — Generador de diagramas UML para ZECI Manager v2.0
====================================================================
Ejecutar desde la raíz del proyecto:
    python generate_uml.py

Produce en /docs/uml/:
  Clases (pyreverse):
    - class_domain.puml         → modelos del dominio
    - class_ports.puml          → interfaces de puertos
    - class_services.puml       → servicios de aplicación
    - class_repositories.puml   → repositorios SQLite
    - class_auth.puml           → autenticación (bcrypt/JWT)
    - class_context_init.puml   → inicializador de contexto
    - class_ui_components.puml  → componentes del design system
  Dependencias (pydeps):
    - deps_domain.svg           → grafo del dominio
    - deps_services.svg         → grafo de servicios
    - deps_infrastructure.svg   → grafo de infraestructura
  Otros:
    - er_domain.svg             → ER de modelos Pydantic (erdantic)
    - packages.puml             → diagrama de paquetes (AST)
    - arch_violations.txt       → reporte de violaciones arquitecturales
    - sequence_login.puml       → flujo de login
    - sequence_context.puml     → flujo de contexto académico
    - sequence_evaluacion.puml  → flujo de registro de nota

Requiere: pylint, pydeps, erdantic
    pip install pylint pydeps erdantic --break-system-packages
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT    = Path(__file__).parent
OUTDIR  = ROOT / "docs" / "uml"
OUTDIR.mkdir(parents=True, exist_ok=True)

OK  = "✅"
ERR = "❌"
WRN = "⚠️ "


# ═══════════════════════════════════════════════════════════════
# 1. DIAGRAMAS DE CLASES — pyreverse
# ═══════════════════════════════════════════════════════════════

PYREVERSE_TARGETS = {
    "domain": {
        "path":        "src/domain/models",
        "output":      "class_domain",
        "description": "Modelos del dominio (Entidades + DTOs + Enums)",
    },
    "ports": {
        "path":        "src/domain/ports",
        "output":      "class_ports",
        "description": "Interfaces de puertos (contratos del dominio)",
    },
    "services": {
        "path":        "src/services",
        "output":      "class_services",
        "description": "Servicios de aplicación",
    },
    "infra_repos": {
        "path":        "src/infrastructure/db/repositories",
        "output":      "class_repositories",
        "description": "Implementaciones de repositorios SQLite",
    },
    "infra_auth": {
        "path":        "src/infrastructure/auth",
        "output":      "class_auth",
        "description": "Capa de autenticación (bcrypt + JWT)",
    },
    "infra_context": {
        "path":        "src/infrastructure/context",
        "output":      "class_context_init",
        "description": "Inicializador de contexto académico",
    },
    "interface_components": {
        "path":        "src/interface/design/components",
        "output":      "class_ui_components",
        "description": "Componentes del design system",
    },
}


def run_pyreverse(name: str, config: dict) -> bool:
    path = ROOT / config["path"]
    if not path.exists():
        print(f"  {WRN} {name}: ruta no encontrada ({config['path']})")
        return False

    cmd = [
        "pyreverse",
        "--output",     "puml",
        "--output-directory", str(OUTDIR),
        "--project",    config["output"],
        "--all-ancestors",
        str(path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if result.returncode == 0:
        print(f"  {OK} {name}: {config['description']}")
        return True
    else:
        print(f"  {ERR} {name}: {result.stderr[:120]}")
        return False


def generar_class_diagrams() -> None:
    print("\n── Diagramas de clases (pyreverse) ──────────────────────")
    ok = 0
    for name, config in PYREVERSE_TARGETS.items():
        if run_pyreverse(name, config):
            ok += 1
    print(f"   {ok}/{len(PYREVERSE_TARGETS)} generados → {OUTDIR}/class_*.puml")


# ═══════════════════════════════════════════════════════════════
# 2. GRAFO DE DEPENDENCIAS — pydeps
# ═══════════════════════════════════════════════════════════════

PYDEPS_TARGETS = {
    "domain": {
        "path":        "src/domain",
        "only":        "src.domain",
        "description": "Verifica que el dominio no importa infraestructura",
        "max_bacon":   4,
        "cluster":     True,
    },
    "services": {
        "path":        "src/services",
        "only":        "src",
        "description": "Verifica que los servicios solo usan puertos",
        "max_bacon":   3,
        "cluster":     True,
    },
    "infrastructure": {
        "path":        "src/infrastructure",
        "only":        "src",
        "description": "Implementaciones de infraestructura",
        "max_bacon":   3,
        "cluster":     True,
    },
}


HAS_GRAPHVIZ = shutil.which("dot") is not None


def run_pydeps(name: str, config: dict) -> bool:
    """
    pydeps no resuelve `src.domain` como nombre punteado porque `src/` es un
    namespace package (sin __init__.py). Se pasa la ruta RELATIVA respecto a
    cwd=ROOT para que pydeps derive el módulo como `src.domain` en lugar de
    un dotted-name basura desde el path absoluto de Windows.

    Si Graphviz (`dot`) no está en el PATH, se emite un .dot en vez de .svg.
    """
    target_path = ROOT / config["path"]
    if not target_path.exists():
        print(f"  {WRN} {name}: ruta no encontrada ({config['path']})")
        return False

    ext     = "svg" if HAS_GRAPHVIZ else "dot"
    out_file = OUTDIR / f"deps_{name}.{ext}"
    cmd = [
        sys.executable, "-m", "pydeps",
        config["path"],                       # ruta RELATIVA, no absoluta
        "--no-show",
        "-o", str(out_file),
        "-T", ext,
        "--max-bacon", str(config["max_bacon"]),
        "--only", config["only"],
        "--reverse",
    ]
    if config.get("cluster"):
        cmd.append("--cluster")

    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)

    if result.returncode == 0 or out_file.exists():
        prefix = OK if result.returncode == 0 else WRN
        suffix = "" if HAS_GRAPHVIZ else "  (dot fallback — instala Graphviz para SVG)"
        print(f"  {prefix} {name}: {config['description']}{suffix}")
        return True

    err = (result.stderr or result.stdout or "").strip().splitlines()
    err_msg = next((l for l in err if l and not l.startswith("usage:")), "sin detalle")
    print(f"  {ERR} {name}: {err_msg[:160]}")
    return False


def generar_dep_graphs() -> None:
    print("\n── Grafos de dependencias (pydeps) ──────────────────────")
    if not HAS_GRAPHVIZ:
        print(f"  {WRN} Graphviz no detectado — se emitirá .dot en lugar de .svg")
        print("     Instala:  choco install graphviz   (o https://graphviz.org/download/)")
    ok = 0
    for name, config in PYDEPS_TARGETS.items():
        if run_pydeps(name, config):
            ok += 1
    ext = "svg" if HAS_GRAPHVIZ else "dot"
    print(f"   {ok}/{len(PYDEPS_TARGETS)} generados → {OUTDIR}/deps_*.{ext}")


# ═══════════════════════════════════════════════════════════════
# 3. DIAGRAMA ER DE MODELOS PYDANTIC — erdantic
# ═══════════════════════════════════════════════════════════════

def generar_er_pydantic() -> None:
    print("\n── Diagrama ER de modelos Pydantic (erdantic) ───────────")
    try:
        import importlib
        import sys as _sys

        import erdantic
        _sys.path.insert(0, str(ROOT))

        # Auto-descubrir módulos Pydantic del dominio
        models_dir = ROOT / "src" / "domain" / "models"
        modulos_dominio = [
            f"src.domain.models.{p.stem}"
            for p in sorted(models_dir.glob("*.py"))
            if not p.stem.startswith("_")
        ]

        modelos = []
        for modulo_str in modulos_dominio:
            try:
                mod = importlib.import_module(modulo_str)
                for attr in dir(mod):
                    obj = getattr(mod, attr)
                    try:
                        if (isinstance(obj, type) and
                            issubclass(obj, __import__("pydantic").BaseModel) and
                            obj.__module__ == modulo_str and
                            not attr.startswith("_")):
                            modelos.append(obj)
                    except Exception:
                        pass
            except ImportError as e:
                print(f"  {WRN} No se pudo importar {modulo_str}: {e}")

        if modelos:
            out = OUTDIR / "er_domain.svg"
            diagram = erdantic.create(*modelos)
            diagram.draw(str(out))
            print(f"  {OK} er_domain.svg — {len(modelos)} modelos Pydantic")
        else:
            print(f"  {WRN} Sin modelos Pydantic detectados")

    except ImportError:
        print(f"  {ERR} erdantic no instalado: pip install erdantic")
    except Exception as e:
        print(f"  {ERR} Error en erdantic: {e}")


# ═══════════════════════════════════════════════════════════════
# 4. DIAGRAMA DE PAQUETES — generado con AST (no requiere imports)
# ═══════════════════════════════════════════════════════════════

def generar_paquetes_puml() -> None:
    """
    Genera un diagrama de paquetes PlantUML analizando la estructura
    de directorios y detectando las importaciones entre capas con AST.
    No requiere que el proyecto sea importable.
    """
    print("\n── Diagrama de paquetes (AST) ───────────────────────────")

    # Capas en orden de dependencia (inner → outer)
    capas = [
        ("domain.models",           "src/domain/models",                   "#DBEAFE"),
        ("domain.ports",            "src/domain/ports",                    "#EDE9FE"),
        ("services",                "src/services",                        "#D1FAE5"),
        ("infrastructure.db",       "src/infrastructure/db/repositories",  "#FEF3C7"),
        ("infrastructure.auth",     "src/infrastructure/auth",             "#FEF3C7"),
        ("infrastructure.context",  "src/infrastructure/context",          "#FEF3C7"),
        ("interface.pages",         "src/interface/pages",                 "#F3F4F6"),
        ("interface.design",        "src/interface/design",                "#F3F4F6"),
    ]

    # Detectar imports entre capas con AST
    def get_imports(filepath: Path) -> list[str]:
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        imports.append(a.name)
            return imports
        except Exception:
            return []

    # Construir matriz de dependencias entre capas
    capa_imports: dict[str, set[str]] = {c[0]: set() for c in capas}

    for capa_id, rel_path, _ in capas:
        abs_path = ROOT / rel_path
        if not abs_path.exists():
            continue
        for py_file in abs_path.rglob("*.py"):
            for imp in get_imports(py_file):
                for otra_capa, otra_ruta, _ in capas:
                    if otra_capa != capa_id and otra_ruta.replace("/", ".").replace("src.", "") in imp:
                        capa_imports[capa_id].add(otra_capa)

    # Generar PlantUML
    lineas = [
        "@startuml ZECI_Packages",
        "!theme plain",
        "title ZECI Manager v2.0 — Diagrama de Paquetes",
        "",
        "skinparam packageStyle rectangle",
        "skinparam defaultFontName Inter",
        "skinparam defaultFontSize 12",
        "skinparam ArrowColor #475569",
        "skinparam PackageBorderColor #CBD5E1",
        "",
        "' ── Capas ──────────────────────────────────────────",
    ]

    for capa_id, _, color in capas:
        var = capa_id.replace(".", "_")
        lineas.append(f'package "{capa_id}" as {var} {color} {{')
        lineas.append('}')

    lineas += [
        "",
        "' ── Dependencias detectadas con AST ────────────────",
    ]

    for capa_id, deps in capa_imports.items():
        origen = capa_id.replace(".", "_")
        for dep in sorted(deps):
            destino = dep.replace(".", "_")
            lineas.append(f"{origen} --> {destino}")

    lineas += ["", "@enduml"]

    out = OUTDIR / "packages.puml"
    out.write_text("\n".join(lineas), encoding="utf-8")
    print(f"  {OK} packages.puml — {sum(len(v) for v in capa_imports.values())} dependencias entre capas")


# ═══════════════════════════════════════════════════════════════
# 5. VERIFICACIÓN DE REGLAS ARQUITECTURALES — AST
# ═══════════════════════════════════════════════════════════════

# Qué capas NO pueden importar qué
REGLAS_PROHIBIDAS = [
    # (capa_infractora, módulo_prohibido, descripción de la violación)
    ("src/domain",           "nicegui",                 "El dominio no puede depender de NiceGUI"),
    ("src/domain",           "src.infrastructure",      "El dominio no puede depender de infraestructura"),
    ("src/domain",           "src.services",            "El dominio no puede depender de servicios"),
    ("src/domain",           "sqlite3",                 "El dominio no puede acceder a la BD directamente"),
    ("src/services",         "nicegui",                 "Los servicios no pueden depender de NiceGUI"),
    ("src/services",         "sqlite3",                 "Los servicios no pueden acceder a la BD directamente"),
    ("src/services",         "src.infrastructure",      "Los servicios no pueden importar infraestructura directamente"),
    ("src/interface",        "sqlite3",                 "La interfaz no puede acceder a la BD directamente"),
    ("src/interface/design", "src.services",            "El design system no puede importar servicios"),
    ("src/interface/design", "src.infrastructure",      "El design system no puede importar infraestructura"),
    ("src/interface/pages",  "src.infrastructure.db.repositories", "Las páginas no pueden importar repositorios directamente"),
]


def verificar_arquitectura() -> tuple[int, int]:
    """
    Analiza con AST todos los .py del proyecto buscando violaciones
    de las reglas de importación de Clean Architecture.

    Retorna (violaciones, archivos_analizados).
    """
    print("\n── Verificación de reglas arquitecturales (AST) ─────────")

    # Cachear parseo AST e imports por archivo para no repetir trabajo por regla.
    # Set de archivos únicos analizados (contador correcto).
    imports_por_archivo: dict[Path, list[tuple[int, str]]] = {}
    capas_afectadas = {ROOT / capa for capa, _, _ in REGLAS_PROHIBIDAS if (ROOT / capa).exists()}

    for capa_abs in capas_afectadas:
        for py_file in capa_abs.rglob("*.py"):
            if py_file in imports_por_archivo:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                imports_por_archivo[py_file] = []
                continue

            entradas: list[tuple[int, str]] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    entradas.append((node.lineno, node.module))
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        entradas.append((node.lineno, a.name))
            imports_por_archivo[py_file] = entradas

    archivos = len(imports_por_archivo)
    violaciones = []

    for capa_path, modulo_prohibido, descripcion in REGLAS_PROHIBIDAS:
        capa_abs = ROOT / capa_path
        if not capa_abs.exists():
            continue

        for py_file, entradas in imports_por_archivo.items():
            try:
                py_file.relative_to(capa_abs)
            except ValueError:
                continue

            for lineno, import_str in entradas:
                if modulo_prohibido in import_str:
                    violaciones.append({
                        "archivo":     str(py_file.relative_to(ROOT)),
                        "linea":       lineno,
                        "import":      import_str,
                        "descripcion": descripcion,
                    })

    # Deduplicar
    viol_uniq = {f"{v['archivo']}:{v['linea']}:{v['import']}": v for v in violaciones}
    violaciones = list(viol_uniq.values())

    if not violaciones:
        print(f"  {OK} Sin violaciones arquitecturales en {archivos} archivos")
    else:
        print(f"  {ERR} {len(violaciones)} violación(es) encontrada(s):\n")
        for v in sorted(violaciones, key=lambda x: x["archivo"]):
            print(f"     {v['archivo']}:{v['linea']}")
            print(f"       import: {v['import']}")
            print(f"       regla:  {v['descripcion']}\n")

    # Escribir reporte
    reporte = OUTDIR / "arch_violations.txt"
    with reporte.open("w", encoding="utf-8") as f:
        f.write("REPORTE DE VIOLACIONES ARQUITECTURALES — ZECI Manager v2.0\n")
        f.write("=" * 60 + "\n\n")
        if not violaciones:
            f.write("✅ Sin violaciones detectadas.\n")
        else:
            for v in violaciones:
                f.write(f"❌ {v['archivo']}:{v['linea']}\n")
                f.write(f"   import:      {v['import']}\n")
                f.write(f"   descripción: {v['descripcion']}\n\n")

    return len(violaciones), archivos


# ═══════════════════════════════════════════════════════════════
# 6. DIAGRAMAS DE SECUENCIA MANUALES
# ═══════════════════════════════════════════════════════════════

SEQUENCE_LOGIN = """
@startuml Secuencia_Login
!theme plain
title Flujo de Login — ZECI Manager v2.0

actor Usuario
participant "login.py\\n(Interface)" as UI
participant "BcryptAuthService\\n(Infrastructure)" as Auth
participant "ContextInitializer\\n(Infrastructure)" as CI
participant "SessionContext\\n(Interface)" as SC
database "SQLite" as DB

Usuario -> UI : POST usuario + contraseña
activate UI

UI -> Auth : verificar_password(usuario, contraseña)
activate Auth
Auth -> DB : SELECT hash WHERE usuario=?
DB --> Auth : hash_bcrypt / hash_sha256
Auth -> Auth : bcrypt.verify() o sha256 fallback
Auth --> UI : True / False
deactivate Auth

alt Autenticación exitosa
    UI -> CI : inicializar(ctx_base)
    activate CI
    CI -> DB : ConfiguracionService.get_activa()
    CI -> DB : PeriodoService.get_activo(anio_id)
    CI -> DB : AsignacionRepo.listar_por_docente()
    CI --> UI : ctx con año+periodo+grupo+asignatura
    deactivate CI

    UI -> SC : ctx.guardar()
    SC -> SC : app.storage.user.update(...)

    UI --> Usuario : redirect /inicio
else Fallo de autenticación
    UI --> Usuario : notify("Credenciales incorrectas")
end

deactivate UI
@enduml
"""

SEQUENCE_CONTEXT = """
@startuml Secuencia_CambioContexto
!theme plain
title Cambio de Contexto Académico — context_selector

actor Profesor
participant "context_chip\\n(Interface)" as Chip
participant "abrir_selector()\\n(Interface)" as Selector
participant "SessionContext\\n(Interface)" as SC
participant "AsignacionRepo\\n(Infrastructure)" as Repo
participant "dashboard\\n(Interface)" as Dashboard

Profesor -> Chip : clic en chip topbar
Chip -> Selector : abrir_selector(ctx, on_change)

Selector -> Repo : listar_por_anio(anio_id) → periodos
Selector -> Selector : _render_periodos()
Profesor -> Selector : selecciona Periodo 2

note right of Selector
  Al cambiar periodo,
  guarda asignatura_id (estable)
  antes de limpiar asignacion_id
end note

Selector -> Repo : listar_por_docente(usuario_id, periodo_id)
Selector -> Selector : _render_grupos()
Profesor -> Selector : selecciona Grupo 601

Selector -> Repo : listar_por_grupo(grupo_id, periodo_id)
note right of Selector
  Busca asignación con mismo
  asignatura_id del periodo anterior
  → hint para restaurar automático
end note
Selector -> Selector : _render_asignaturas()
Profesor -> Selector : selecciona Matemáticas

Profesor -> Selector : clic "Aplicar contexto"
Selector -> SC : ctx.periodo_id = ...
Selector -> SC : ctx.grupo_id = ...
Selector -> SC : ctx.asignacion_id = ...
Selector -> SC : ctx.guardar()
SC -> SC : app.storage.user.update(...)

Selector -> Dashboard : on_change()
Dashboard -> Dashboard : tablero_refreshable.refresh()

@enduml
"""

SEQUENCE_EVALUACION = """
@startuml Secuencia_RegistroNota
!theme plain
title Registro de Nota — Flujo Clean Architecture

actor Profesor
participant "planilla_notas.py\\n(Interface)" as UI
participant "EvaluacionService\\n(Services)" as Svc
participant "CalculadorNotas\\n(Domain)" as Calc
participant "IEvaluacionRepo\\n(Port)" as Port
participant "SqliteEvalRepo\\n(Infrastructure)" as Repo
database "SQLite" as DB

Profesor -> UI : ingresa nota (actividad_id, est_id, valor)
UI -> UI : validar ctx.asignacion_id
UI -> Svc : registrar_nota(dto, ctx)
activate Svc

Svc -> Svc : validar valor (0-100)
Svc -> Port : get_actividad(actividad_id)
Port -> Repo : SELECT actividades WHERE id=?
Repo -> DB
DB --> Repo : actividad
Repo --> Port
Port --> Svc : Actividad

Svc -> Port : upsert_nota(RegistrarNotaDTO)
Port -> Repo
Repo -> DB : INSERT OR REPLACE notas ...
DB --> Repo : OK

note right of Svc
  El servicio NO calcula el promedio.
  CalculadorNotas solo se invoca
  cuando la UI necesita mostrar
  el promedio ajustado.
end note

Svc -> Svc : _auditar(evento, ctx)
Svc --> UI : Nota (con id)
deactivate Svc

UI -> Calc : calcular_promedio_ajustado(notas, actividades, categorias)
activate Calc
Calc -> Calc : renormalizar pesos
Calc --> UI : float (promedio ponderado)
deactivate Calc

UI --> Profesor : mostrar promedio actualizado

@enduml
"""


def generar_sequencias() -> None:
    print("\n── Diagramas de secuencia (PlantUML manual) ─────────────")
    secuencias = {
        "sequence_login.puml":       SEQUENCE_LOGIN,
        "sequence_context.puml":     SEQUENCE_CONTEXT,
        "sequence_evaluacion.puml":  SEQUENCE_EVALUACION,
    }
    for nombre, contenido in secuencias.items():
        (OUTDIR / nombre).write_text(contenido.strip(), encoding="utf-8")
        print(f"  {OK} {nombre}")
    print(f"   → {OUTDIR}/sequence_*.puml")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 60)
    print("  UML GENERATOR — ZECI Manager v2.0")
    print(f"  Output: {OUTDIR}")
    print("=" * 60)

    generar_class_diagrams()
    generar_dep_graphs()
    generar_er_pydantic()
    generar_paquetes_puml()
    violaciones, archivos = verificar_arquitectura()
    generar_sequencias()

    print("\n" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    print(f"  Archivos analizados:     {archivos}")
    print(f"  Violaciones detectadas:  {violaciones}")
    print(f"  Diagramas generados en:  {OUTDIR}")
    print("\n  Para renderizar .puml:")
    print("    - VS Code: extensión 'PlantUML' (jebbs.plantuml)")
    print("    - Online:  https://www.plantuml.com/plantuml/uml/")
    print("    - CLI:     java -jar plantuml.jar docs/uml/*.puml")
    print("\n  Para ver grafos .svg:")
    print("    - Cualquier navegador: abrir docs/uml/deps_*.svg")

    return 0 if violaciones == 0 else 1


if __name__ == "__main__":
    sys.exit(main())