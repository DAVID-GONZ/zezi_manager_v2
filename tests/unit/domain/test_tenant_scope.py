"""
Guardarrail: los métodos críticos de repositorio no tienen default en institucion_id.
Si alguien agrega '= None' a estos parámetros, este test falla inmediatamente.
"""

import ast
import inspect
import pathlib

from src.domain.ports.alerta_repo import IAlertaRepository
from src.domain.ports.habilitacion_repo import IHabilitacionRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.ports.usuario_repo import IUsuarioRepository


def _tiene_default(cls, method_name: str, param_name: str) -> bool:
    sig = inspect.signature(getattr(cls, method_name))
    param = sig.parameters.get(param_name)
    return param is not None and param.default is not inspect.Parameter.empty


def test_listar_asignaciones_docente_no_tiene_default():
    assert not _tiene_default(IUsuarioRepository, "listar_asignaciones_docente", "institucion_id")


def test_contar_pendientes_no_tiene_default():
    assert not _tiene_default(IAlertaRepository, "contar_pendientes", "institucion_id")


def test_listar_habilitaciones_dto_no_tiene_default():
    from src.domain.models.habilitacion import FiltroHabilitacionesDTO

    field = FiltroHabilitacionesDTO.model_fields["institucion_id"]
    assert field.is_required(), "FiltroHabilitacionesDTO.institucion_id debe ser obligatorio"


def test_listar_alertas_dto_no_tiene_default():
    from src.domain.models.alerta import FiltroAlertasDTO

    field = FiltroAlertasDTO.model_fields["institucion_id"]
    assert field.is_required(), "FiltroAlertasDTO.institucion_id debe ser obligatorio"


def test_listar_planes_por_seguimiento_no_tiene_default():
    assert not _tiene_default(IHabilitacionRepository, "listar_planes_por_seguimiento", "institucion_id")


def test_listar_grados_no_tiene_default():
    assert not _tiene_default(IInfraestructuraRepository, "listar_grados", "institucion_id")


def test_listar_ventanas_grupo_no_tiene_default():
    assert not _tiene_default(IInfraestructuraRepository, "listar_ventanas_grupo", "institucion_id")


def test_listar_limites_docente_no_tiene_default():
    assert not _tiene_default(IInfraestructuraRepository, "listar_limites_docente", "institucion_id")


def test_listar_configs_generacion_no_tiene_default():
    assert not _tiene_default(IInfraestructuraRepository, "listar_configs_generacion", "institucion_id")


# =============================================================================
# T9 — Guardarrail estructural: AST scan de TODOS los puertos
# =============================================================================

# Métodos con `institucion_id: X | None = None` aún pendientes de migración
# (LOW priority). Elimina una entrada solo cuando el método ya use TenantScope.
_WHITELIST_DEFAULTS_PENDIENTES: set[tuple[str, str]] = {
    ("infraestructura_repo.py", "get_grupo_por_codigo"),  # pendiente migración LOW
    ("infraestructura_repo.py", "set_horas_plan"),        # pendiente migración LOW
}

_PORTS_DIR = pathlib.Path(__file__).resolve().parents[3] / "src" / "domain" / "ports"


def _ast_check_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    filepath: pathlib.Path,
    violations: list[str],
) -> None:
    """Detecta default=None en parámetros 'institucion_id' de una función/método."""
    if (filepath.name, node.name) in _WHITELIST_DEFAULTS_PENDIENTES:
        return

    args = node.args
    # Argumentos posicionales (positional-only + normales)
    pos_args = args.posonlyargs + args.args
    n_pos = len(pos_args)
    n_defaults = len(args.defaults)

    for i, arg in enumerate(pos_args):
        if arg.arg != "institucion_id":
            continue
        default_idx = i - (n_pos - n_defaults)
        if default_idx >= 0:
            default = args.defaults[default_idx]
            if isinstance(default, ast.Constant) and default.value is None:
                violations.append(
                    f"{filepath.name}::{node.name}() — "
                    f"parámetro posicional 'institucion_id' tiene default None "
                    f"(línea {arg.lineno})"
                )

    # Argumentos keyword-only
    for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults):
        if arg.arg != "institucion_id":
            continue
        if (
            kw_default is not None
            and isinstance(kw_default, ast.Constant)
            and kw_default.value is None
        ):
            violations.append(
                f"{filepath.name}::{node.name}() — "
                f"parámetro kwonly 'institucion_id' tiene default None "
                f"(línea {arg.lineno})"
            )


def _ast_check_class(
    class_node: ast.ClassDef,
    filepath: pathlib.Path,
    violations: list[str],
) -> None:
    """Detecta default=None en anotaciones de clase con nombre 'institucion_id'."""
    # Solo hijos directos del cuerpo de la clase (no métodos anidados)
    for item in class_node.body:
        if not isinstance(item, ast.AnnAssign):
            continue
        if not isinstance(item.target, ast.Name):
            continue
        if item.target.id != "institucion_id":
            continue
        if (
            item.value is not None
            and isinstance(item.value, ast.Constant)
            and item.value.value is None
        ):
            violations.append(
                f"{filepath.name}::{class_node.name}.institucion_id — "
                f"campo de clase con default None (línea {item.target.lineno})"
            )


def test_no_hay_defaults_none_en_puertos():
    """
    Guardarrail estructural (T9): ningún parámetro 'institucion_id' en
    src/domain/ports/ puede tener default None.

    Si este test falla, alguien añadió 'institucion_id: X | None = None' en
    un puerto sin completar la migración a TenantScope. Opciones:
      - Migrar el parámetro a TenantScope obligatorio (correcto).
      - Si es una migración inacabada, añadir una entrada temporal en
        _WHITELIST_DEFAULTS_PENDIENTES con un comentario que explique el estado.
    """
    violations: list[str] = []

    for filepath in sorted(_PORTS_DIR.glob("*.py")):
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _ast_check_function(node, filepath, violations)
            elif isinstance(node, ast.ClassDef):
                _ast_check_class(node, filepath, violations)

    assert not violations, (
        "Parámetros 'institucion_id' con default None en src/domain/ports/:\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\n\nMigra a TenantScope o añade entrada en _WHITELIST_DEFAULTS_PENDIENTES."
    )
