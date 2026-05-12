"""Tests unitarios para AsignacionService."""
from __future__ import annotations

import pytest

from src.domain.models.asignacion import (
    Asignacion, AsignacionInfo, FiltroAsignacionesDTO, NuevaAsignacionDTO,
)
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.services.asignacion_service import AsignacionService


# ===========================================================================
# Fake
# ===========================================================================

class FakeAsignacionRepo(IAsignacionRepository):
    def __init__(self):
        self._asigs: dict[int, Asignacion] = {}
        self._next_id = 1

    def guardar(self, a: Asignacion) -> Asignacion:
        a = a.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._asigs[a.id] = a
        return a

    def get_by_id(self, aid: int) -> Asignacion | None:
        return self._asigs.get(aid)

    def get_info(self, aid: int) -> AsignacionInfo | None:
        return None

    def existe(self, grupo_id: int, asignatura_id: int, usuario_id: int, periodo_id: int) -> bool:
        return any(
            a.grupo_id == grupo_id and a.asignatura_id == asignatura_id
            and a.usuario_id == usuario_id and a.periodo_id == periodo_id
            for a in self._asigs.values()
        )

    def desactivar(self, aid: int) -> None:
        a = self._asigs[aid]
        self._asigs[aid] = a.model_copy(update={"activo": False})

    def reactivar(self, aid: int) -> None:
        a = self._asigs[aid]
        self._asigs[aid] = a.model_copy(update={"activo": True})

    def reasignar_docente(self, aid: int, nuevo_usuario_id: int) -> None:
        a = self._asigs[aid]
        self._asigs[aid] = a.model_copy(update={"usuario_id": nuevo_usuario_id})

    def listar(self, filtro: FiltroAsignacionesDTO) -> list[Asignacion]:
        return list(self._asigs.values())

    def listar_info(self, filtro: FiltroAsignacionesDTO) -> list[AsignacionInfo]:
        return []

    def listar_por_docente(self, uid: int, periodo_id=None) -> list[AsignacionInfo]:
        return []

    def listar_por_grupo(self, grupo_id: int, periodo_id=None) -> list[Asignacion]:
        return [a for a in self._asigs.values() if a.grupo_id == grupo_id]


def _make_svc() -> tuple[AsignacionService, FakeAsignacionRepo]:
    repo = FakeAsignacionRepo()
    return AsignacionService(repo), repo


def _dto(usuario_id: int = 1) -> NuevaAsignacionDTO:
    return NuevaAsignacionDTO(
        grupo_id=10, asignatura_id=20, usuario_id=usuario_id, periodo_id=5
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestCrearAsignacion:
    def test_crea_asignacion_nueva(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto())
        assert a.id is not None

    def test_lanza_si_duplicada(self):
        svc, _ = _make_svc()
        svc.crear_asignacion(_dto())
        with pytest.raises(ValueError, match="Ya existe"):
            svc.crear_asignacion(_dto())

    def test_distintos_docentes_en_misma_asignatura(self):
        svc, _ = _make_svc()
        a1 = svc.crear_asignacion(_dto(usuario_id=1))
        a2 = svc.crear_asignacion(_dto(usuario_id=2))
        assert a1.id != a2.id


class TestDesactivar:
    def test_desactiva_asignacion_activa(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto())
        resultado = svc.desactivar(a.id)
        assert resultado.activo is False

    def test_lanza_si_ya_inactiva(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto())
        svc.desactivar(a.id)
        with pytest.raises(ValueError, match="ya está desactivada"):
            svc.desactivar(a.id)

    def test_lanza_si_no_existe(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.desactivar(999)


class TestReasignarDocente:
    def test_reasigna_a_nuevo_docente(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto(usuario_id=1))
        resultado = svc.reasignar_docente(a.id, nuevo_usuario_id=99)
        assert resultado.usuario_id == 99

    def test_lanza_si_mismo_docente(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto(usuario_id=1))
        with pytest.raises(ValueError, match="mismo"):
            svc.reasignar_docente(a.id, nuevo_usuario_id=1)
