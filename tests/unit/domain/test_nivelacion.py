"""Tests unitarios del dominio de nivelación."""
import pytest
from src.domain.models.nivelacion import (
    ActividadNivelacion,
    CalculadorNivelacion,
    CierreNivelacion,
    NotaNivelacion,
    NuevaActividadNivelacionDTO,
    CalificarNotaNivelacionDTO,
)
from datetime import date


# ── ActividadNivelacion ───────────────────────────────────────────────────────

class TestActividadNivelacion:
    def _act(self, **kw):
        defaults = dict(id=1, asignacion_id=1, periodo_id=1, nombre="Taller 1", peso=0.5)
        return ActividadNivelacion(**{**defaults, **kw})

    def test_peso_valido(self):
        a = self._act(peso=0.4)
        assert a.peso == 0.4

    def test_peso_fuera_rango_lanza(self):
        with pytest.raises(ValueError, match="peso"):
            self._act(peso=0.0)
        with pytest.raises(ValueError, match="peso"):
            self._act(peso=1.1)

    def test_nombre_vacio_lanza(self):
        with pytest.raises(ValueError):
            self._act(nombre="   ")

    def test_nombre_muy_largo_lanza(self):
        with pytest.raises(ValueError):
            self._act(nombre="x" * 121)


# ── NotaNivelacion ────────────────────────────────────────────────────────────

class TestNotaNivelacion:
    def _nota(self, **kw):
        defaults = dict(
            actividad_nivelacion_id=1, estudiante_id=10,
            asignacion_id=1, periodo_id=1,
        )
        return NotaNivelacion(**{**defaults, **kw})

    def test_valor_none_pendiente(self):
        n = self._nota()
        assert not n.calificada

    def test_valor_registrado(self):
        n = self._nota(valor=75.5)
        assert n.calificada
        assert n.valor == 75.5

    def test_valor_fuera_rango_lanza(self):
        with pytest.raises(ValueError):
            self._nota(valor=-1)
        with pytest.raises(ValueError):
            self._nota(valor=101)


# ── CalculadorNivelacion ──────────────────────────────────────────────────────

class TestCalculadorNivelacion:
    def _act(self, id_, peso):
        return ActividadNivelacion(
            id=id_, asignacion_id=1, periodo_id=1,
            nombre=f"Act {id_}", peso=peso,
        )

    def _nota(self, act_id, est_id, valor):
        return NotaNivelacion(
            actividad_nivelacion_id=act_id,
            estudiante_id=est_id,
            asignacion_id=1, periodo_id=1,
            valor=valor,
        )

    def test_promedio_ponderado_correcto(self):
        actos = [self._act(1, 0.4), self._act(2, 0.6)]
        notas = [self._nota(1, 10, 80.0), self._nota(2, 10, 70.0)]
        resultado = CalculadorNivelacion.nota_definitiva(notas, actos)
        # 80*0.4 + 70*0.6 = 32 + 42 = 74
        assert resultado == pytest.approx(74.0, abs=0.05)

    def test_nota_pendiente_retorna_none(self):
        actos = [self._act(1, 0.5), self._act(2, 0.5)]
        notas = [self._nota(1, 10, 80.0), self._nota(2, 10, None)]
        assert CalculadorNivelacion.nota_definitiva(notas, actos) is None

    def test_sin_actividades_retorna_none(self):
        assert CalculadorNivelacion.nota_definitiva([], []) is None

    def test_pesos_completos(self):
        actos = [self._act(1, 0.4), self._act(2, 0.6)]
        assert CalculadorNivelacion.pesos_completos(actos) is True

    def test_pesos_incompletos(self):
        actos = [self._act(1, 0.3), self._act(2, 0.3)]
        assert CalculadorNivelacion.pesos_completos(actos) is False

    def test_suma_pesos(self):
        actos = [self._act(1, 0.3), self._act(2, 0.7)]
        assert CalculadorNivelacion.suma_pesos(actos) == pytest.approx(1.0)


# ── DTOs ─────────────────────────────────────────────────────────────────────

class TestDTOs:
    def test_nueva_actividad_dto_peso_en_porcentaje_correcto(self):
        dto = NuevaActividadNivelacionDTO(
            asignacion_id=1, periodo_id=1, nombre="X", peso=0.3
        )
        assert dto.peso == 0.3

    def test_nueva_actividad_dto_peso_invalido(self):
        with pytest.raises(ValueError):
            NuevaActividadNivelacionDTO(
                asignacion_id=1, periodo_id=1, nombre="X", peso=0.0
            )

    def test_calificar_dto_redondea(self):
        dto = CalificarNotaNivelacionDTO(valor=75.555)
        assert dto.valor == pytest.approx(75.56, abs=0.01)

    def test_calificar_dto_fuera_rango(self):
        with pytest.raises(ValueError):
            CalificarNotaNivelacionDTO(valor=101)
