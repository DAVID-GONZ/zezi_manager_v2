"""Tests de autorización por objeto (director de grupo) en
CatalogoAcademicoService — convivencia_03, T2.

Cubren la resolución de datos (`es_director_de_grupo`) y la conveniencia
(`puede_gestionar_comportamiento_en_grupo`) que combina esa resolución con la
política pura de convivencia. El repo se mockea con un fake mínimo.
"""
from __future__ import annotations

from src.domain.models.infraestructura import Grupo
from src.services.catalogo_academico_service import CatalogoAcademicoService


class _FakeInfraRepo:
    def __init__(self, grupo: Grupo | None) -> None:
        self._grupo = grupo

    def get_grupo(self, grupo_id: int) -> Grupo | None:
        if self._grupo is not None and self._grupo.id == grupo_id:
            return self._grupo
        return None


def _svc(grupo: Grupo | None) -> CatalogoAcademicoService:
    return CatalogoAcademicoService(repo=_FakeInfraRepo(grupo))


def _grupo(director_grupo_id: int | None = None) -> Grupo:
    return Grupo(
        id=7, codigo="601", grado=6, institucion_id=1,
        director_grupo_id=director_grupo_id,
    )


# ── es_director_de_grupo ─────────────────────────────────────────────────────

class TestEsDirectorDeGrupo:
    def test_director_del_grupo_true(self):
        assert _svc(_grupo(director_grupo_id=10)).es_director_de_grupo(10, 7) is True

    def test_otro_usuario_false(self):
        assert _svc(_grupo(director_grupo_id=10)).es_director_de_grupo(99, 7) is False

    def test_grupo_sin_director_false(self):
        assert _svc(_grupo(director_grupo_id=None)).es_director_de_grupo(10, 7) is False

    def test_grupo_inexistente_false_sin_excepcion(self):
        assert _svc(None).es_director_de_grupo(10, 7) is False

    def test_usuario_none_false(self):
        assert _svc(_grupo(director_grupo_id=10)).es_director_de_grupo(None, 7) is False


# ── puede_gestionar_comportamiento_en_grupo ──────────────────────────────────

class TestPuedeGestionarComportamientoEnGrupo:
    def test_coordinador_pasa_aunque_no_dirija(self):
        svc = _svc(_grupo(director_grupo_id=None))
        assert svc.puede_gestionar_comportamiento_en_grupo("coordinador", 5, 7) is True

    def test_director_pasa_aunque_no_dirija(self):
        svc = _svc(_grupo(director_grupo_id=None))
        assert svc.puede_gestionar_comportamiento_en_grupo("director", 5, 7) is True

    def test_profesor_director_del_grupo_pasa(self):
        svc = _svc(_grupo(director_grupo_id=10))
        assert svc.puede_gestionar_comportamiento_en_grupo("profesor", 10, 7) is True

    def test_profesor_de_otro_grupo_no_pasa(self):
        svc = _svc(_grupo(director_grupo_id=10))
        assert svc.puede_gestionar_comportamiento_en_grupo("profesor", 99, 7) is False

    def test_profesor_grupo_inexistente_no_pasa(self):
        assert _svc(None).puede_gestionar_comportamiento_en_grupo("profesor", 10, 7) is False
