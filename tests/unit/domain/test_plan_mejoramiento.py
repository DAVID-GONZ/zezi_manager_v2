"""Tests unitarios para modelos del dominio Plan de Mejoramiento."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.models.plan_mejoramiento import (
    ActividadPlan,
    CalculadorPlan,
    CalificarNotaPlanDTO,
    CerrarPlanEstudianteDTO,
    CortePlan,
    EjecutarCorteDTO,
    EstadoNotaCorte,
    NotaActividadPlan,
    NotaCortePlan,
    NuevaActividadPlanDTO,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _act(id_=1, corte_id=1, peso=0.5) -> ActividadPlan:
    return ActividadPlan(
        id=id_, corte_id=corte_id, asignacion_id=1, periodo_id=1,
        nombre="Taller", peso=peso
    )

def _nota(act_id=1, est_id=1, valor=80.0) -> NotaActividadPlan:
    return NotaActividadPlan(
        actividad_plan_id=act_id, estudiante_id=est_id,
        asignacion_id=1, periodo_id=1, valor=valor
    )


# ===========================================================================
# Tests EstadoNotaCorte
# ===========================================================================

class TestEstadoNotaCorte:
    def test_valores_correctos(self):
        assert EstadoNotaCorte.SIN_PLAN.value == "sin_plan"
        assert EstadoNotaCorte.EN_PLAN.value  == "en_plan"
        assert EstadoNotaCorte.APROBADO.value == "aprobado"
        assert EstadoNotaCorte.REPROBADO.value == "reprobado"

    def test_es_str(self):
        assert isinstance(EstadoNotaCorte.EN_PLAN, str)


# ===========================================================================
# Tests ActividadPlan — validador de peso
# ===========================================================================

class TestActividadPlan:
    def test_peso_valido(self):
        a = ActividadPlan(
            corte_id=1, asignacion_id=1, periodo_id=1, nombre="Test", peso=0.5
        )
        assert a.peso == 0.5

    def test_peso_limite_superior_valido(self):
        a = ActividadPlan(
            corte_id=1, asignacion_id=1, periodo_id=1, nombre="Test", peso=1.0
        )
        assert a.peso == 1.0

    def test_peso_cero_invalido(self):
        with pytest.raises(ValidationError):
            ActividadPlan(corte_id=1, asignacion_id=1, periodo_id=1, nombre="Test", peso=0.0)

    def test_peso_negativo_invalido(self):
        with pytest.raises(ValidationError):
            ActividadPlan(corte_id=1, asignacion_id=1, periodo_id=1, nombre="Test", peso=-0.1)

    def test_peso_mayor_1_invalido(self):
        with pytest.raises(ValidationError):
            ActividadPlan(corte_id=1, asignacion_id=1, periodo_id=1, nombre="Test", peso=1.1)


# ===========================================================================
# Tests CalificarNotaPlanDTO — validador de valor
# ===========================================================================

class TestCalificarNotaPlanDTO:
    def test_valor_valido(self):
        dto = CalificarNotaPlanDTO(valor=75.0)
        assert dto.valor == 75.0

    def test_valor_cero_valido(self):
        dto = CalificarNotaPlanDTO(valor=0.0)
        assert dto.valor == 0.0

    def test_valor_100_valido(self):
        dto = CalificarNotaPlanDTO(valor=100.0)
        assert dto.valor == 100.0

    def test_valor_negativo_invalido(self):
        with pytest.raises(ValidationError):
            CalificarNotaPlanDTO(valor=-1.0)

    def test_valor_mayor_100_invalido(self):
        with pytest.raises(ValidationError):
            CalificarNotaPlanDTO(valor=101.0)


# ===========================================================================
# Tests NuevaActividadPlanDTO
# ===========================================================================

class TestNuevaActividadPlanDTO:
    def test_peso_invalido_lanza(self):
        with pytest.raises(ValidationError):
            NuevaActividadPlanDTO(
                corte_id=1, asignacion_id=1, periodo_id=1,
                nombre="T", peso=0.0
            )

    def test_to_actividad_sin_usuario(self):
        dto = NuevaActividadPlanDTO(
            corte_id=2, asignacion_id=3, periodo_id=4,
            nombre="Taller", descripcion="Desc", peso=0.4
        )
        act = dto.to_actividad()
        assert act.corte_id == 2
        assert act.asignacion_id == 3
        assert act.peso == 0.4
        assert act.usuario_id is None

    def test_to_actividad_con_usuario(self):
        dto = NuevaActividadPlanDTO(
            corte_id=1, asignacion_id=1, periodo_id=1, nombre="T", peso=0.3
        )
        act = dto.to_actividad(usuario_id=99)
        assert act.usuario_id == 99


# ===========================================================================
# Tests CalculadorPlan
# ===========================================================================

class TestCalculadorPlan:
    def test_nota_al_corte_simple(self):
        cats = [{"peso": 0.4, "promedio": 80.0}, {"peso": 0.3, "promedio": 60.0}]
        # 0.4*80 + 0.3*60 = 32 + 18 = 50
        assert CalculadorPlan.nota_al_corte(cats) == pytest.approx(50.0)

    def test_nota_al_corte_lista_vacia(self):
        assert CalculadorPlan.nota_al_corte([]) == 0.0

    def test_peso_registrado(self):
        cats = [{"peso": 0.4, "promedio": 80.0}, {"peso": 0.3, "promedio": 60.0}]
        assert CalculadorPlan.peso_registrado(cats) == pytest.approx(0.7)

    def test_nota_umbral(self):
        # 0.5 * 60 = 30
        assert CalculadorPlan.nota_umbral(0.5, 60.0) == pytest.approx(30.0)

    def test_nota_definitiva_aprobado_igual_umbral(self):
        # nota_definitiva_aprobado == nota_umbral (congelado en el mínimo proporcional)
        peso = 0.6
        minima = 60.0
        assert CalculadorPlan.nota_definitiva_aprobado(peso, minima) == pytest.approx(
            CalculadorPlan.nota_umbral(peso, minima)
        )

    def test_suma_pesos_actividades(self):
        acts = [_act(id_=1, peso=0.4), _act(id_=2, peso=0.6)]
        assert CalculadorPlan.suma_pesos_actividades(acts) == pytest.approx(1.0)

    def test_pesos_completos_true(self):
        acts = [_act(id_=1, peso=0.5), _act(id_=2, peso=0.5)]
        assert CalculadorPlan.pesos_completos(acts) is True

    def test_pesos_completos_false(self):
        acts = [_act(id_=1, peso=0.4)]
        assert CalculadorPlan.pesos_completos(acts) is False

    def test_pesos_completos_lista_vacia(self):
        # Suma = 0, no completos
        assert CalculadorPlan.pesos_completos([]) is False

    def test_nota_plan_estudiante_todas_calificadas(self):
        acts  = [_act(id_=1, peso=0.4), _act(id_=2, peso=0.6)]
        notas = [_nota(act_id=1, valor=80.0), _nota(act_id=2, valor=70.0)]
        # 0.4*80 + 0.6*70 = 32 + 42 = 74
        resultado = CalculadorPlan.nota_plan_estudiante(notas, acts)
        assert resultado == pytest.approx(74.0)

    def test_nota_plan_estudiante_nota_none_retorna_none(self):
        acts  = [_act(id_=1, peso=0.5), _act(id_=2, peso=0.5)]
        notas = [NotaActividadPlan(
            actividad_plan_id=1, estudiante_id=1,
            asignacion_id=1, periodo_id=1, valor=None
        )]
        assert CalculadorPlan.nota_plan_estudiante(notas, acts) is None

    def test_nota_plan_estudiante_sin_actividades_retorna_none(self):
        assert CalculadorPlan.nota_plan_estudiante([], []) is None


# ===========================================================================
# Tests CalculadorNotas.calcular_definitiva_con_corte
# ===========================================================================

class TestCalculadorNotasConCorte:
    """Verifica la integración backward-compatible del nuevo método."""

    def test_importa_correctamente(self):
        from src.domain.models.evaluacion import CalculadorNotas
        assert hasattr(CalculadorNotas, "calcular_definitiva_con_corte")

    def test_sin_categorias_retorna_nota_plan(self):
        from src.domain.models.evaluacion import CalculadorNotas
        resultado = CalculadorNotas.calcular_definitiva_con_corte(
            notas={}, actividades=[], categorias=[],
            nota_definitiva_plan=30.0,
            categoria_ids_en_corte={1, 2},
        )
        assert resultado == pytest.approx(30.0)

    def test_suma_correctamente_post_corte(self):
        from src.domain.models.evaluacion import CalculadorNotas, Categoria, Actividad, Nota
        cat1 = Categoria(id=1, nombre="C1", peso=0.4, asignacion_id=1, periodo_id=1)
        cat2 = Categoria(id=2, nombre="C2", peso=0.6, asignacion_id=1, periodo_id=1)
        act1 = Actividad(id=10, nombre="A1", categoria_id=1)
        act2 = Actividad(id=20, nombre="A2", categoria_id=2)

        # cat1 estuvo en el corte (excluida); cat2 es post-corte
        resultado = CalculadorNotas.calcular_definitiva_con_corte(
            notas={10: 80.0, 20: 70.0},
            actividades=[act1, act2],
            categorias=[cat1, cat2],
            nota_definitiva_plan=24.0,       # 0.4 * 60 = 24 (contribución congelada)
            categoria_ids_en_corte={1},      # solo cat1 en el corte
        )
        # 24.0 + (0.6 * 70.0) = 24.0 + 42.0 = 66.0
        assert resultado == pytest.approx(66.0)
