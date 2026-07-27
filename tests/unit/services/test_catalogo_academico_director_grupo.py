"""Tests unitarios para CatalogoAcademicoService — director de grupo (convivencia_02).

Cubren:
  - candidatos_director_grupo devuelve solo docentes con asignación en el grupo
    (deduplicados por usuario_id), y {} sin provider.
  - asignar_director_grupo acepta un docente candidato válido y persiste el id.
  - asignar_director_grupo rechaza un usuario sin asignación en el grupo.
  - asignar_director_grupo con None desasigna (director_grupo_id -> None).
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.domain.models.infraestructura import Grupo
from src.services.catalogo_academico_service import CatalogoAcademicoService


@dataclass
class _InfoFake:
    """Sustituto mínimo de AsignacionInfo (solo lo que usa el servicio)."""
    usuario_id: int
    docente_nombre: str


class _FakeInfraRepo:
    def __init__(self, grupo: Grupo, otros: list[Grupo] | None = None) -> None:
        self._grupo = grupo
        # Otros grupos del catálogo (para probar la unicidad de director).
        self._otros = list(otros or [])
        self.actualizado: Grupo | None = None

    def _catalogo(self) -> list[Grupo]:
        return [self._grupo, *self._otros]

    def get_grupo(self, grupo_id: int) -> Grupo | None:
        return next((g for g in self._catalogo() if g.id == grupo_id), None)

    def listar_grupos(self, grado=None, institucion_id=None) -> list[Grupo]:
        return list(self._catalogo())

    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        self.actualizado = grupo
        self._grupo = grupo
        return grupo


class _FakeAsignacionSvc:
    def __init__(self, infos: list[_InfoFake]) -> None:
        self._infos = infos
        self.llamado_con: tuple | None = None

    def listar_por_grupo(self, grupo_id: int, solo_activas: bool = True):
        self.llamado_con = (grupo_id, solo_activas)
        return self._infos


def _grupo() -> Grupo:
    return Grupo(id=7, codigo="601", grado=6, institucion_id=1)


# ── candidatos_director_grupo ──────────────────────────────────────────────

def test_candidatos_devuelve_docentes_del_grupo_deduplicados():
    asig = _FakeAsignacionSvc([
        _InfoFake(usuario_id=10, docente_nombre="Ana"),
        _InfoFake(usuario_id=10, docente_nombre="Ana"),   # 2ª materia mismo docente
        _InfoFake(usuario_id=20, docente_nombre="Beto"),
    ])
    svc = CatalogoAcademicoService(
        repo=_FakeInfraRepo(_grupo()), asignacion_svc_provider=lambda: asig
    )
    cand = svc.candidatos_director_grupo(7)
    assert cand == {10: "Ana", 20: "Beto"}
    assert asig.llamado_con == (7, True)


def test_candidatos_sin_provider_devuelve_vacio():
    svc = CatalogoAcademicoService(repo=_FakeInfraRepo(_grupo()))
    assert svc.candidatos_director_grupo(7) == {}


# ── asignar_director_grupo ──────────────────────────────────────────────────

def test_asignar_director_valido_persiste():
    repo = _FakeInfraRepo(_grupo())
    asig = _FakeAsignacionSvc([_InfoFake(usuario_id=10, docente_nombre="Ana")])
    svc = CatalogoAcademicoService(repo=repo, asignacion_svc_provider=lambda: asig)
    resultado = svc.asignar_director_grupo(7, 10)
    assert resultado.director_grupo_id == 10
    assert repo.actualizado is not None
    assert repo.actualizado.director_grupo_id == 10


def test_asignar_director_sin_asignacion_rechaza():
    repo = _FakeInfraRepo(_grupo())
    asig = _FakeAsignacionSvc([_InfoFake(usuario_id=10, docente_nombre="Ana")])
    svc = CatalogoAcademicoService(repo=repo, asignacion_svc_provider=lambda: asig)
    with pytest.raises(ValueError):
        svc.asignar_director_grupo(7, 99)   # 99 no tiene asignación en el grupo
    assert repo.actualizado is None


def test_asignar_director_none_desasigna():
    grupo = _grupo().model_copy(update={"director_grupo_id": 10})
    repo = _FakeInfraRepo(grupo)
    asig = _FakeAsignacionSvc([_InfoFake(usuario_id=10, docente_nombre="Ana")])
    svc = CatalogoAcademicoService(repo=repo, asignacion_svc_provider=lambda: asig)
    resultado = svc.asignar_director_grupo(7, None)
    assert resultado.director_grupo_id is None
    assert repo.actualizado.director_grupo_id is None


# ── Unicidad: un docente dirige un solo grupo (convivencia_02b) ──────────────

def test_asignar_director_que_ya_dirige_otro_grupo_rechaza_y_no_persiste():
    # El docente 10 ya es director del grupo 9; intentar asignarlo también al
    # grupo 7 (donde sí tiene asignación) debe bloquearse y no persistir.
    otro = Grupo(id=9, codigo="602", grado=6, institucion_id=1, director_grupo_id=10)
    repo = _FakeInfraRepo(_grupo(), otros=[otro])
    asig = _FakeAsignacionSvc([_InfoFake(usuario_id=10, docente_nombre="Ana")])
    svc = CatalogoAcademicoService(repo=repo, asignacion_svc_provider=lambda: asig)
    with pytest.raises(ValueError):
        svc.asignar_director_grupo(7, 10)
    assert repo.actualizado is None


def test_reasignar_director_del_mismo_grupo_permitido():
    # El docente 10 ya dirige el grupo 7; reemplazarlo por otro candidato (20)
    # del mismo grupo debe ser permitido (no dispara la unicidad).
    grupo = _grupo().model_copy(update={"director_grupo_id": 10})
    repo = _FakeInfraRepo(grupo)
    asig = _FakeAsignacionSvc([
        _InfoFake(usuario_id=10, docente_nombre="Ana"),
        _InfoFake(usuario_id=20, docente_nombre="Beto"),
    ])
    svc = CatalogoAcademicoService(repo=repo, asignacion_svc_provider=lambda: asig)
    resultado = svc.asignar_director_grupo(7, 20)
    assert resultado.director_grupo_id == 20
    assert repo.actualizado.director_grupo_id == 20


def test_desasignar_permitido_aunque_dirija_otro_grupo():
    # Desasignar (None) siempre permitido, sin importar la unicidad.
    otro = Grupo(id=9, codigo="602", grado=6, institucion_id=1, director_grupo_id=10)
    grupo = _grupo().model_copy(update={"director_grupo_id": 10})
    repo = _FakeInfraRepo(grupo, otros=[otro])
    asig = _FakeAsignacionSvc([_InfoFake(usuario_id=10, docente_nombre="Ana")])
    svc = CatalogoAcademicoService(repo=repo, asignacion_svc_provider=lambda: asig)
    resultado = svc.asignar_director_grupo(7, None)
    assert resultado.director_grupo_id is None
