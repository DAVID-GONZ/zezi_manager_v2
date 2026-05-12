"""Tests unitarios para EstudianteService."""
from __future__ import annotations

import pytest

from src.domain.models.estudiante import (
    Estudiante, EstadoMatricula, FiltroEstudiantesDTO,
    EstudianteResumenDTO, NuevoEstudianteDTO,
)
from src.domain.models.piar import PIAR, NuevoPIARDTO
from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.services.estudiante_service import EstudianteService


# ===========================================================================
# Fake
# ===========================================================================

class FakeEstudianteRepo(IEstudianteRepository):
    def __init__(self):
        self._ests: dict[int, Estudiante] = {}
        self._piars: list[PIAR] = []
        self._next_id = 1
        self._next_piar = 1

    def guardar(self, e: Estudiante) -> Estudiante:
        e = e.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._ests[e.id] = e
        return e

    def actualizar(self, e: Estudiante) -> Estudiante:
        self._ests[e.id] = e
        return e

    def actualizar_estado_matricula(self, eid: int, estado: str) -> None:
        e = self._ests[eid]
        self._ests[eid] = e.model_copy(update={"estado_matricula": estado})

    def get_by_id(self, eid: int) -> Estudiante | None:
        return self._ests.get(eid)

    def get_by_documento(self, doc: str) -> Estudiante | None:
        for e in self._ests.values():
            if e.numero_documento == doc:
                return e
        return None

    def existe_documento(self, doc: str) -> bool:
        return any(e.numero_documento == doc for e in self._ests.values())

    def asignar_grupo(self, eid: int, grupo_id: int) -> None:
        e = self._ests[eid]
        self._ests[eid] = e.model_copy(update={"grupo_id": grupo_id})

    def listar_por_grupo(self, grupo_id: int, solo_activos: bool = True) -> list[Estudiante]:
        return [e for e in self._ests.values() if e.grupo_id == grupo_id]

    def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]:
        return list(self._ests.values())

    def listar_resumenes(self, filtro: FiltroEstudiantesDTO) -> list[EstudianteResumenDTO]:
        return []

    def contar_por_grupo(self, grupo_id: int) -> int:
        return sum(1 for e in self._ests.values() if e.grupo_id == grupo_id)

    def get_resumen(self, eid: int) -> EstudianteResumenDTO | None:
        return None

    def existe_piar(self, eid: int, anio_id: int) -> bool:
        return any(p.estudiante_id == eid and p.anio_id == anio_id for p in self._piars)

    def guardar_piar(self, p: PIAR) -> PIAR:
        p = p.model_copy(update={"id": self._next_piar})
        self._next_piar += 1
        self._piars.append(p)
        return p

    def get_piar(self, eid: int, anio_id: int) -> PIAR | None:
        for p in self._piars:
            if p.estudiante_id == eid and p.anio_id == anio_id:
                return p
        return None

    def actualizar_piar(self, p: PIAR) -> PIAR:
        return p

    def listar_piars(self, eid: int) -> list[PIAR]:
        return [p for p in self._piars if p.estudiante_id == eid]


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> tuple[EstudianteService, FakeEstudianteRepo]:
    repo = FakeEstudianteRepo()
    return EstudianteService(repo), repo


def _dto(doc: str = "123456789") -> NuevoEstudianteDTO:
    return NuevoEstudianteDTO(
        numero_documento=doc,
        nombre="Carlos",
        apellido="Pérez",
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestMatricular:
    def test_matricula_estudiante_nuevo(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        assert est.id is not None
        assert est.numero_documento == "123456789"

    def test_lanza_si_documento_duplicado(self):
        svc, _ = _make_svc()
        svc.matricular(_dto("123456789"))
        with pytest.raises(ValueError, match="123456789"):
            svc.matricular(_dto("123456789"))

    def test_documentos_distintos_no_duplican(self):
        svc, _ = _make_svc()
        e1 = svc.matricular(_dto("111"))
        e2 = svc.matricular(_dto("222"))
        assert e1.id != e2.id


class TestRetirar:
    def test_retira_estudiante_activo(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        retirado = svc.retirar(est.id)
        assert retirado.estado_matricula == EstadoMatricula.RETIRADO

    def test_lanza_si_ya_retirado(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        svc.retirar(est.id)
        with pytest.raises(ValueError, match="RETIRADO"):
            svc.retirar(est.id)

    def test_lanza_si_no_existe(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.retirar(999)


class TestRegistrarPIAR:
    def test_registra_piar_nuevo(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        dto_piar = NuevoPIARDTO(
            estudiante_id=est.id,
            anio_id=1,
            descripcion_necesidad="Necesidades específicas de aprendizaje",
        )
        piar = svc.registrar_piar(dto_piar)
        assert piar.id is not None

    def test_lanza_si_piar_duplicado(self):
        svc, _ = _make_svc()
        est = svc.matricular(_dto())
        dto_piar = NuevoPIARDTO(
            estudiante_id=est.id, anio_id=1,
            descripcion_necesidad="Plan inicial",
        )
        svc.registrar_piar(dto_piar)
        with pytest.raises(ValueError, match="Ya existe un PIAR"):
            svc.registrar_piar(dto_piar)
