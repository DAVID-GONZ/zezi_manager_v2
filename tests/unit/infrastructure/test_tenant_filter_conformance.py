"""
Test de conformidad: repos que acceden a tablas con institucion_id
deben filtrar por tenant.

Este test NO es exhaustivo de cada query individual; verifica que
los repos tienen al menos una referencia a institucion_id en su
implementación, lo cual indica que aplican el filtro de tenant.

Repos excluidos de esta lista (sin filtro directo por diseño):
  - sqla_asistencia_repo   → filtra por asignacion_id/grupo_id (indirecto)
  - sqla_cierre_repo       → filtra por estudiante_id/asignacion_id
  - sqla_evaluacion_repo   → filtra por asignacion_id
  - sqla_estadisticos_repo → agrega datos ya filtrados
  - sqla_nivelacion_repo   → filtra por asignacion_id
  - sqla_periodo_repo      → sin scope de tenant (catálogo por institución
                              pero la institución se pasa como argumento)
  - sqla_plan_mejoramiento_repo → filtra por evaluacion_id
  - sqla_siee_repo         → catálogo global
"""

import pathlib

import pytest

REPOS_DIR = pathlib.Path("src/infrastructure/db/repositories")

# Repos que tienen tenant scope DIRECTO (tabla con institucion_id).
# Verificado contra sqla_*_repo.py con grep de institucion_id (occurrencias > 0).
REPOS_CON_TENANT = [
    "sqla_configuracion_repo.py",
    "sqla_asignacion_repo.py",
    "sqla_habilitacion_repo.py",
    "sqla_alerta_repo.py",
    "sqla_acudiente_repo.py",
    "sqla_convivencia_repo.py",
    "sqla_infraestructura_repo.py",
    "sqla_usuario_repo.py",
    "sqla_estudiante_repo.py",
    "sqla_auditoria_repo.py",
    "sqla_preferencias_repo.py",
    "sqla_institucion_repo.py",
]


def _contains_tenant_filter(source: str) -> bool:
    """Verifica que el source contiene al menos una referencia a institucion_id."""
    return "institucion_id" in source


class TestTenantFilterConformance:
    """R18-R19: repos con scope de tenant deben filtrar por institucion_id."""

    @pytest.mark.parametrize("filename", REPOS_CON_TENANT)
    def test_repo_contiene_filtro_tenant(self, filename):
        # R18, R19
        path = REPOS_DIR / filename
        assert path.exists(), f"Repo no encontrado: {path}"
        source = path.read_text(encoding="utf-8")
        assert _contains_tenant_filter(source), (
            f"{filename} no contiene ningún filtro de institucion_id. "
            "Todo repo con scope de tenant debe filtrar por institucion_id."
        )

    def test_lista_repos_con_tenant_no_vacia(self):
        """Verificación de cordura: la lista de repos con tenant debe ser no vacía."""
        assert len(REPOS_CON_TENANT) > 0

    def test_todos_los_repos_de_la_lista_existen(self):
        """Todos los archivos de la lista deben existir en el directorio."""
        faltantes = [f for f in REPOS_CON_TENANT if not (REPOS_DIR / f).exists()]
        assert not faltantes, f"Repos no encontrados: {faltantes}"
