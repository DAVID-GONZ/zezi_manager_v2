"""
Tests unitarios para los métodos de conteo de clases de AsistenciaService.

Cubre:
  R1 / R5 — un (asignacion_id, fecha) = 1 clase sin importar el número de estudiantes
  R4      — mes sin registros retorna 0
  R6      — desglose por asignación correcto
  ValueError para mes fuera de rango
"""
from __future__ import annotations

from datetime import date

import pytest

from src.domain.models.asistencia import (
    ControlDiario,
    EstadoAsistencia,
    ResumenAsistenciaDTO,
)
from src.domain.ports.asistencia_repo import IAsistenciaRepository
from src.services.asistencia_service import AsistenciaService


# ===========================================================================
# FakeAsistenciaRepo con lógica de conteo en memoria
# ===========================================================================

class FakeAsistenciaRepoConteo(IAsistenciaRepository):
    """
    Implementación mínima para probar los métodos de conteo.
    Almacena (usuario_id -> lista de (asignacion_id, fecha)) para simular la BD.
    """

    def __init__(self, registros: list[tuple[int, int, date]] | None = None):
        # Lista de (usuario_id, asignacion_id, fecha)
        self._registros: list[tuple[int, int, date]] = registros or []

    # ---- métodos de conteo (los que se prueban) ----------------------------

    def contar_clases_dictadas_docente(self, usuario_id: int, anio: int, mes: int) -> int:
        pares = {
            (asig_id, fecha)
            for uid, asig_id, fecha in self._registros
            if uid == usuario_id and fecha.year == anio and fecha.month == mes
        }
        return len(pares)

    def clases_dictadas_por_asignacion(self, usuario_id: int, anio: int, mes: int) -> dict[int, int]:
        from collections import defaultdict
        conteos: dict[int, set[date]] = defaultdict(set)
        for uid, asig_id, fecha in self._registros:
            if uid == usuario_id and fecha.year == anio and fecha.month == mes:
                conteos[asig_id].add(fecha)
        return {asig_id: len(fechas) for asig_id, fechas in conteos.items()}

    # ---- stubs para el resto de métodos abstractos -------------------------

    def registrar(self, c: ControlDiario) -> ControlDiario:
        return c

    def registrar_masivo(self, controles: list[ControlDiario]) -> int:
        return len(controles)

    def get_por_fecha_estudiante(self, est_id: int, asig_id: int, fecha: date) -> ControlDiario | None:
        return None

    def listar_por_grupo_y_fecha(self, grupo_id: int, asig_id: int, fecha: date) -> list[ControlDiario]:
        return []

    def listar_por_estudiante_y_periodo(self, est_id: int, per_id: int) -> list[ControlDiario]:
        return []

    def listar_por_asignacion_y_rango(self, asig_id: int, desde: date, hasta: date) -> list[ControlDiario]:
        return []

    def resumen_por_estudiante(self, est_id: int, per_id: int, asig_id=None) -> ResumenAsistenciaDTO:
        return ResumenAsistenciaDTO(estudiante_id=est_id)

    def resumen_por_grupo(self, grupo_id: int, asig_id: int, per_id: int) -> list[ResumenAsistenciaDTO]:
        return []

    def contar_faltas_injustificadas(self, est_id: int, per_id: int) -> int:
        return 0

    def fechas_con_registro(self, asig_id: int, per_id: int) -> list[date]:
        return []

    def porcentaje_asistencia_grupo(self, grupo_id: int, asig_id: int, per_id: int) -> float:
        return 0.0

    def estudiantes_en_riesgo(self, grupo_id: int, asig_id: int, per_id: int, umbral_pct: float = 80.0) -> list[int]:
        return []


# ===========================================================================
# Helpers
# ===========================================================================

USUARIO_ID = 10
ANIO = 2025
MES = 3  # marzo


def _svc(registros: list[tuple[int, int, date]]) -> AsistenciaService:
    return AsistenciaService(FakeAsistenciaRepoConteo(registros))


# ===========================================================================
# Tests
# ===========================================================================

class TestContarClasesMes:

    def test_docente_con_dos_asignaciones_mismo_dia_cuenta_dos(self):
        """
        R1 / R5: docente con 2 asignaciones distintas el mismo día → total = 2.
        No debe duplicar por número de estudiantes.
        """
        fecha = date(ANIO, MES, 5)
        registros = [
            # asig 1, varios estudiantes
            (USUARIO_ID, 1, fecha),
            (USUARIO_ID, 1, fecha),
            (USUARIO_ID, 1, fecha),
            # asig 2, varios estudiantes
            (USUARIO_ID, 2, fecha),
            (USUARIO_ID, 2, fecha),
        ]
        svc = _svc(registros)
        assert svc.contar_clases_mes(USUARIO_ID, ANIO, MES) == 2

    def test_misma_asignacion_multiples_estudiantes_mismo_dia_cuenta_una_clase(self):
        """
        R5: misma asignación, varios estudiantes, mismo día → 1 clase.
        """
        fecha = date(ANIO, MES, 10)
        registros = [
            (USUARIO_ID, 5, fecha),
            (USUARIO_ID, 5, fecha),
            (USUARIO_ID, 5, fecha),
            (USUARIO_ID, 5, fecha),
        ]
        svc = _svc(registros)
        assert svc.contar_clases_mes(USUARIO_ID, ANIO, MES) == 1

    def test_mes_sin_registros_retorna_cero(self):
        """R4: mes sin registros → 0."""
        # registros en mes distinto
        registros = [
            (USUARIO_ID, 1, date(ANIO, 4, 1)),  # abril, no marzo
        ]
        svc = _svc(registros)
        assert svc.contar_clases_mes(USUARIO_ID, ANIO, MES) == 0

    def test_mes_fuera_de_rango_lanza_valueerror(self):
        """Mes 0 y 13 deben lanzar ValueError."""
        svc = _svc([])
        with pytest.raises(ValueError, match="Mes fuera de rango"):
            svc.contar_clases_mes(USUARIO_ID, ANIO, 0)
        with pytest.raises(ValueError, match="Mes fuera de rango"):
            svc.contar_clases_mes(USUARIO_ID, ANIO, 13)


class TestClasesMesPorAsignacion:

    def test_desglose_correcto_por_asignacion(self):
        """
        R6: desglose por asignación correcto.
        asig 1 → 2 días distintos; asig 2 → 1 día.
        """
        registros = [
            (USUARIO_ID, 1, date(ANIO, MES, 3)),
            (USUARIO_ID, 1, date(ANIO, MES, 3)),  # mismo día → no duplica
            (USUARIO_ID, 1, date(ANIO, MES, 7)),  # día distinto → suma
            (USUARIO_ID, 2, date(ANIO, MES, 5)),
            (USUARIO_ID, 2, date(ANIO, MES, 5)),  # mismo día → no duplica
        ]
        svc = _svc(registros)
        resultado = svc.clases_mes_por_asignacion(USUARIO_ID, ANIO, MES)
        assert resultado == {1: 2, 2: 1}

    def test_mes_sin_registros_retorna_dict_vacio(self):
        """Mes vacío → dict vacío."""
        svc = _svc([])
        assert svc.clases_mes_por_asignacion(USUARIO_ID, ANIO, MES) == {}

    def test_mes_fuera_de_rango_lanza_valueerror(self):
        """Mes 0 y 13 deben lanzar ValueError."""
        svc = _svc([])
        with pytest.raises(ValueError, match="Mes fuera de rango"):
            svc.clases_mes_por_asignacion(USUARIO_ID, ANIO, 0)
        with pytest.raises(ValueError, match="Mes fuera de rango"):
            svc.clases_mes_por_asignacion(USUARIO_ID, ANIO, 13)
