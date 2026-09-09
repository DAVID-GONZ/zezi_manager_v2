"""
Tests para scripts/check_auditoria.py — puerta de cobertura de huella.

T1: test_puerta_en_verde — verifica que el script sale con codigo 0 en el estado actual.
T2: test_detecta_mutador_sin_huella — verifica que las funciones internas detectan
    un mutador sin huella correctamente usando datos sinteticos.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent.parent


# ============================================================
# Importacion dinamica de check_auditoria como modulo
# ============================================================

def _load_check_auditoria():
    """Carga scripts/check_auditoria.py como modulo Python importable."""
    spec = importlib.util.spec_from_file_location(
        "_check_auditoria_mod",
        ROOT / "scripts" / "check_auditoria.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ============================================================
# T1 — Puerta en verde
# ============================================================

def test_puerta_en_verde() -> None:
    """
    check_auditoria.py debe salir con codigo 0 en el estado actual del proyecto.

    Si alguien agrega un metodo mutador sin huella fuera del dict SERVICIOS_SIN_HUELLA_DEUDA,
    o si una entrada del dict queda completamente cubierta, este test falla.
    """
    result = subprocess.run(
        [sys.executable, "scripts/check_auditoria.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, (
        "check_auditoria.py detecto problemas de cobertura de huella:\n"
        f"{result.stdout}\n{result.stderr}"
    )


# ============================================================
# T2 — Deteccion de mutador sin huella (datos sinteticos)
# ============================================================

def test_detecta_mutador_sin_huella(tmp_path: Path) -> None:
    """
    Verifica que el algoritmo de deteccion identifica un servicio con mutador sin huella.

    Usa las funciones internas de check_auditoria.py con datos sinteticos:
    - Un repo ficticio con un metodo que contiene INSERT INTO.
    - Un servicio ficticio con un metodo publico que llama a ese metodo de repo.
    - El metodo del servicio NO llama a auditar_cambio.
    """
    mod = _load_check_auditoria()

    # ── Pasada 1: repo ficticio con metodo de escritura ──
    repo_code = dedent("""\
        class FakeRepo:
            def guardar_fake(self, obj):
                conn.execute("INSERT INTO tabla_fake (nombre) VALUES (?)", (obj.nombre,))
    """)
    repo_path = tmp_path / "fake_repo.py"
    repo_path.write_text(repo_code, encoding="utf-8")

    # Construir inventario de repos desde el archivo ficticio
    write_methods: set[str] = set()
    tree = ast.parse(repo_code)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                if mod._is_sql_write(child.value):
                    write_methods.add(node.name)
                    break

    assert "guardar_fake" in write_methods, (
        "El inventario de repos debe detectar 'guardar_fake' como metodo de escritura "
        "(contiene INSERT INTO)"
    )

    # ── Pasada 2: servicio ficticio que llama al repo sin auditar_cambio ──
    service_code = dedent("""\
        class FakeService:
            def __init__(self, repo):
                self._repo = repo

            def crear_fake(self, obj):
                \"\"\"Crea un objeto fake — mutador sin huella.\"\"\"
                self._repo.guardar_fake(obj)
                return obj
    """)

    service_path = tmp_path / "fake_service.py"
    service_path.write_text(service_code, encoding="utf-8")

    analisis = mod._analizar_servicio(service_path, write_methods)

    assert "crear_fake" in analisis, (
        "El analizador debe detectar 'crear_fake' como metodo mutador "
        "(llama a guardar_fake que tiene INSERT INTO)"
    )
    assert analisis["crear_fake"]["is_mutator"] is True
    assert analisis["crear_fake"]["has_huella"] is False, (
        "crear_fake no llama a auditar_cambio, por lo tanto no debe tener huella"
    )


def test_detecta_metodo_con_huella(tmp_path: Path) -> None:
    """
    Verifica que el algoritmo reconoce un metodo que SI llama a auditar_cambio.
    """
    mod = _load_check_auditoria()

    # Inventario con un metodo de escritura
    write_methods = {"guardar_fake"}

    # Servicio con metodo que llama auditar_cambio
    service_code = dedent("""\
        from src.services.auditoria_helpers import auditar_cambio

        class ServiceConHuella:
            def __init__(self, repo, auditoria):
                self._repo = repo
                self._auditoria = auditoria

            def crear_con_huella(self, obj):
                resultado = self._repo.guardar_fake(obj)
                auditar_cambio(
                    self._auditoria,
                    accion="CREATE",
                    tabla="tabla_fake",
                    nuevo={"id": resultado.id},
                )
                return resultado
    """)

    service_path = tmp_path / "service_con_huella.py"
    service_path.write_text(service_code, encoding="utf-8")

    analisis = mod._analizar_servicio(service_path, write_methods)

    assert "crear_con_huella" in analisis
    assert analisis["crear_con_huella"]["is_mutator"] is True
    assert analisis["crear_con_huella"]["has_huella"] is True, (
        "crear_con_huella llama a auditar_cambio, debe tener huella"
    )


def test_no_detecta_metodo_lectura(tmp_path: Path) -> None:
    """
    Verifica que metodos de solo lectura (sin SQL de escritura) no se incluyen.
    """
    mod = _load_check_auditoria()

    write_methods = {"guardar_fake"}

    service_code = dedent("""\
        class ServiceLectura:
            def __init__(self, repo):
                self._repo = repo

            def listar(self):
                return self._repo.listar_todos()

            def get_by_id(self, id):
                return self._repo.get_by_id(id)
    """)

    service_path = tmp_path / "service_lectura.py"
    service_path.write_text(service_code, encoding="utf-8")

    analisis = mod._analizar_servicio(service_path, write_methods)

    # Ninguno de los metodos de lectura debe detectarse como mutador
    assert "listar" not in analisis, "listar es solo lectura, no debe ser mutador"
    assert "get_by_id" not in analisis, "get_by_id es solo lectura, no debe ser mutador"


def test_inventario_repos_detecta_sql_escritura(tmp_path: Path) -> None:
    """
    Verifica que _inventario_repos detecta correctamente metodos con SQL de escritura.
    """
    mod = _load_check_auditoria()

    repo_code = dedent("""\
        class TestRepo:
            def insertar(self):
                conn.execute("INSERT INTO t (a) VALUES (?)", (1,))

            def actualizar(self):
                conn.execute("UPDATE t SET a = ? WHERE id = ?", (1, 2))

            def eliminar(self):
                conn.execute("DELETE FROM t WHERE id = ?", (1,))

            def buscar(self):
                return conn.execute("SELECT * FROM t").fetchall()
    """)

    repo_dir = tmp_path / "repos"
    repo_dir.mkdir()
    (repo_dir / "test_repo.py").write_text(repo_code, encoding="utf-8")

    write_methods = mod._inventario_repos(repo_dir)

    assert "insertar" in write_methods
    assert "actualizar" in write_methods
    assert "eliminar" in write_methods
    assert "buscar" not in write_methods, "buscar es solo lectura, no debe estar en inventario"
