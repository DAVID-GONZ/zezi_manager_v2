"""Tests unitarios para AsistenciaService."""
from __future__ import annotations

from datetime import date

import pytest

from src.domain.models.asistencia import (
    ControlDiario, EstadoAsistencia,
    RegistrarAsistenciaDTO, RegistrarAsistenciaMasivaDTO,
    ResumenAsistenciaDTO,
)
from src.domain.ports.asistencia_repo import IAsistenciaRepository
from src.services.asistencia_service import AsistenciaService


# ===========================================================================
# Fake
# ===========================================================================

class FakeAsistenciaRepo(IAsistenciaRepository):
    def __init__(self):
        self._registros: list[ControlDiario] = []

    def registrar(self, c: ControlDiario) -> ControlDiario:
        self._registros.append(c)
        return c

    def registrar_masivo(self, controles: list[ControlDiario]) -> int:
        self._registros.extend(controles)
        return len(controles)

    def get_por_fecha(self, est_id: int, grupo_id: int, asig_id: int, fecha: date) -> ControlDiario | None:
        return None

    def get_por_fecha_estudiante(self, est_id: int, asig_id: int, fecha: date) -> ControlDiario | None:
        return None

    def listar_por_estudiante_y_periodo(self, est_id: int, asig_id: int, per_id: int) -> list[ControlDiario]:
        return []

    def listar_por_asignacion_y_rango(self, asig_id: int, desde: date, hasta: date) -> list[ControlDiario]:
        return []

    def listar_por_grupo_y_fecha(self, grupo_id: int, asig_id: int, fecha: date) -> list[ControlDiario]:
        return []

    def resumen_por_estudiante(self, est_id: int, per_id: int, asig_id=None) -> ResumenAsistenciaDTO:
        return ResumenAsistenciaDTO(
            estudiante_id=est_id, asignacion_id=asig_id or 1, periodo_id=per_id,
        )

    def resumen_por_grupo(self, grupo_id: int, asig_id: int, per_id: int) -> list[ResumenAsistenciaDTO]:
        return []

    def contar_faltas_injustificadas(self, est_id: int, per_id: int) -> int:
        return sum(
            1 for c in self._registros
            if c.estudiante_id == est_id and c.periodo_id == per_id
            and c.estado == EstadoAsistencia.FALTA_INJUSTIFICADA
        )

    def porcentaje_asistencia_grupo(self, grupo_id: int, asig_id: int, per_id: int) -> float:
        return 0.0

    def estudiantes_en_riesgo(self, grupo_id: int, per_id: int, umbral: int) -> list[int]:
        return []

    def fechas_con_registro(self, asig_id: int, per_id: int) -> list[date]:
        return []


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> AsistenciaService:
    return AsistenciaService(FakeAsistenciaRepo())


def _dto_individual() -> RegistrarAsistenciaDTO:
    return RegistrarAsistenciaDTO(
        estudiante_id=1, grupo_id=10, asignacion_id=3,
        periodo_id=5, fecha=date.today(), estado=EstadoAsistencia.PRESENTE,
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestRegistrar:
    def test_registra_asistencia_individual(self):
        svc = _make_svc()
        ctrl = svc.registrar(_dto_individual())
        assert ctrl.estado == EstadoAsistencia.PRESENTE

    def test_registra_falta_injustificada(self):
        svc = _make_svc()
        dto = RegistrarAsistenciaDTO(
            estudiante_id=1, grupo_id=10, asignacion_id=3,
            periodo_id=5, fecha=date.today(), estado=EstadoAsistencia.FALTA_INJUSTIFICADA,
        )
        ctrl = svc.registrar(dto)
        assert ctrl.estado == EstadoAsistencia.FALTA_INJUSTIFICADA


class TestRegistrarMasivo:
    def test_registra_multiples_estudiantes(self):
        svc = _make_svc()
        dto = RegistrarAsistenciaMasivaDTO(
            grupo_id=10, asignacion_id=3, periodo_id=5, fecha=date.today(),
            registros=[
                {"estudiante_id": 1, "estado": EstadoAsistencia.PRESENTE},
                {"estudiante_id": 2, "estado": EstadoAsistencia.PRESENTE},
                {"estudiante_id": 3, "estado": EstadoAsistencia.FALTA_INJUSTIFICADA},
            ],
        )
        conteo = svc.registrar_masivo(dto)
        assert conteo == 3

    def test_registra_uno_solo(self):
        svc = _make_svc()
        dto = RegistrarAsistenciaMasivaDTO(
            grupo_id=10, asignacion_id=3, periodo_id=5,
            fecha=date.today(),
            registros=[{"estudiante_id": 1, "estado": EstadoAsistencia.PRESENTE}],
        )
        assert svc.registrar_masivo(dto) == 1


class TestResumen:
    def test_resumen_estudiante_retorna_dto(self):
        svc = _make_svc()
        resumen = svc.resumen_estudiante(estudiante_id=1, periodo_id=5, asignacion_id=3)
        assert resumen.estudiante_id == 1

    def test_resumen_grupo_retorna_lista(self):
        svc = _make_svc()
        resumenes = svc.resumen_grupo(grupo_id=10, asignacion_id=3, periodo_id=5)
        assert isinstance(resumenes, list)
