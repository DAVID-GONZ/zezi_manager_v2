"""Tests unitarios para PlanEstudiosService — cascada de eliminación (Group 4)."""
from __future__ import annotations

from src.services.plan_estudios_service import PlanEstudiosService


class _FakeInfraRepo:
    def __init__(self):
        self.eliminados: list[tuple[int, int]] = []

    def eliminar_plan_estudios(self, grado: int, asignatura_id: int) -> bool:
        self.eliminados.append((grado, asignatura_id))
        return True


class _FakeAsignacionSvc:
    def __init__(self, n: int):
        self._n = n
        self.llamado_con = None

    def desactivar_por_grado_asignatura(self, grado, asignatura_id, usuario_id=None):
        self.llamado_con = (grado, asignatura_id, usuario_id)
        return self._n


def test_eliminar_con_cascade_propaga():
    repo = _FakeInfraRepo()
    asig = _FakeAsignacionSvc(n=3)
    svc = PlanEstudiosService(repo=repo, asignacion_svc_provider=lambda: asig)
    eliminado, n = svc.eliminar(6, 42, cascade=True, usuario_id=7)
    assert eliminado is True and n == 3
    assert repo.eliminados == [(6, 42)]
    assert asig.llamado_con == (6, 42, 7)


def test_eliminar_sin_cascade_no_toca_asignaciones():
    repo = _FakeInfraRepo()
    asig = _FakeAsignacionSvc(n=5)
    svc = PlanEstudiosService(repo=repo, asignacion_svc_provider=lambda: asig)
    eliminado, n = svc.eliminar(6, 42, cascade=False)
    assert eliminado is True and n == 0
    assert asig.llamado_con is None


def test_eliminar_sin_provider_no_falla():
    repo = _FakeInfraRepo()
    svc = PlanEstudiosService(repo=repo)
    eliminado, n = svc.eliminar(6, 42, cascade=True, usuario_id=1)
    assert eliminado is True and n == 0
