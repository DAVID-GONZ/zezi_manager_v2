"""Tests del presenter de estadísticos — llaman al código REAL de producción.

Reemplazan a `tests/unit/interface/test_estadisticos_handlers.py`, que reimplementaba
la lógica en el propio test (tautología). Aquí se invoca `EstadisticosPresenter`, de
modo que estos asserts fallan si se rompe una transición o un cálculo de la página.
"""
from __future__ import annotations

import pytest

from src.interface.presenters.informes.estadisticos_presenter import (
    EstadisticosPresenter,
    estado_inicial,
)

# Catálogo mínimo de tipos (espejo de la forma real: cada tipo declara sus filtros).
_TIPOS = {
    "consolidado_notas": {"filtros": ["grupo", "periodo"]},
    "distribucion_desempenos": {"filtros": ["grupo", "asignatura", "periodo"]},
}


def _p() -> EstadisticosPresenter:
    return EstadisticosPresenter(_TIPOS)


def _val(metricas, titulo):
    return next(m.valor for m in metricas if m.titulo == titulo)


# ===========================================================================
# Estado inicial
# ===========================================================================

def test_estado_inicial_tiene_las_claves_esperadas():
    e = estado_inicial()
    assert e["tipo"] is None
    assert e["grupo_id"] is None and e["asignacion_id"] is None and e["periodo_id"] is None
    assert e["datos"] is None and e["datos_listos"] is False


# ===========================================================================
# Transiciones: coerción de tipos
# ===========================================================================

class TestCoercion:
    def test_set_grupo_convierte_str_a_int(self):
        p = _p()
        p.set_grupo("3")
        assert p.estado["grupo_id"] == 3
        assert isinstance(p.estado["grupo_id"], int)

    def test_set_grupo_none_permanece_none(self):
        p = _p()
        p.set_grupo(None)
        assert p.estado["grupo_id"] is None

    def test_set_asignacion_y_periodo_convierten_str_a_int(self):
        p = _p()
        p.set_asignacion("7")
        p.set_periodo("1")
        assert p.estado["asignacion_id"] == 7
        assert p.estado["periodo_id"] == 1


# ===========================================================================
# Transiciones: cascada de reseteos y limpieza de datos
# ===========================================================================

class TestCascada:
    def test_set_tipo_resetea_asignacion_y_periodo(self):
        p = _p()
        p.set_asignacion("7")
        p.set_periodo("2")
        p.set_tipo("consolidado_notas")
        assert p.estado["asignacion_id"] is None
        assert p.estado["periodo_id"] is None

    def test_set_grupo_resetea_asignacion_pero_no_periodo(self):
        p = _p()
        p.set_periodo("2")
        p.set_asignacion("7")
        p.set_grupo("10")
        assert p.estado["asignacion_id"] is None
        assert p.estado["periodo_id"] == 2  # el grupo NO toca el periodo

    def test_cualquier_transicion_invalida_los_datos_cargados(self):
        p = _p()
        p.estado["datos"] = [{"x": 1}]
        p.estado["datos_listos"] = True
        p.set_periodo("1")
        assert p.estado["datos"] is None
        assert p.estado["datos_listos"] is False


# ===========================================================================
# filtros_completos
# ===========================================================================

class TestFiltrosCompletos:
    def test_sin_tipo_no_esta_completo(self):
        assert _p().filtros_completos() is False

    def test_faltan_filtros_requeridos(self):
        p = _p()
        p.set_tipo("consolidado_notas")  # requiere grupo + periodo
        assert p.filtros_completos() is False
        p.set_grupo("10")
        assert p.filtros_completos() is False  # falta periodo
        p.set_periodo("1")
        assert p.filtros_completos() is True

    def test_tipo_con_asignatura_exige_asignacion(self):
        p = _p()
        p.set_tipo("distribucion_desempenos")  # grupo + asignatura + periodo
        p.set_grupo("10")
        p.set_periodo("1")
        assert p.filtros_completos() is False  # falta asignatura
        p.set_asignacion("7")
        assert p.filtros_completos() is True


# ===========================================================================
# resumen (cálculo de métricas — antes tautología)
# ===========================================================================

class TestResumen:
    def test_sin_datos_no_hay_metricas(self):
        assert EstadisticosPresenter.resumen("consolidado_notas", None) == []
        assert EstadisticosPresenter.resumen("consolidado_notas", []) == []

    def test_consolidado_notas_promedio_y_aprobados(self):
        datos = [
            {"promedio_periodo": 75.0},
            {"promedio_periodo": 55.0},
            {"promedio_periodo": 80.0},
        ]
        m = EstadisticosPresenter.resumen("consolidado_notas", datos)
        assert _val(m, "Estudiantes") == "3"
        assert _val(m, "Promedio grupal") == "70.0"
        assert _val(m, "Aprobados") == "2 (66%)"
        assert _val(m, "Reprobados") == "1"

    def test_ranking_agrega_mejor_y_menor(self):
        datos = [{"promedio": 90.0}, {"promedio": 40.0}]
        m = EstadisticosPresenter.resumen("ranking_grupo", datos)
        assert _val(m, "Mejor nota") == "90.0"
        assert _val(m, "Menor nota") == "40.0"

    def test_consolidado_asistencia_bajo_70(self):
        datos = [{"porcentaje": 85.0}, {"porcentaje": 60.0}, {"porcentaje": 75.0}]
        m = EstadisticosPresenter.resumen("consolidado_asistencia", datos)
        assert _val(m, "% Asistencia prom.") == "73.3%"
        assert _val(m, "Bajo 70%") == "1"

    def test_consolidado_anual_promovidos(self):
        datos = [
            {"definitiva": 72.0, "estado": "Promovido"},
            {"definitiva": 45.0, "estado": "Reprobado"},
            {"definitiva": 68.0, "estado": "Promovido"},
        ]
        m = EstadisticosPresenter.resumen("consolidado_anual", datos)
        assert _val(m, "Definitiva prom.") == "61.7"
        assert _val(m, "Promovidos") == "2"
        assert _val(m, "Reprobados") == "1"

    def test_dict_cuenta_total_de_valores(self):
        m = EstadisticosPresenter.resumen("distribucion_desempenos", {"alto": 4, "bajo": 6})
        assert _val(m, "Total registros") == "10"

    def test_iconos_son_claves_semanticas_no_tokens(self):
        # El presenter no depende del design system: devuelve claves, no iconos reales.
        m = EstadisticosPresenter.resumen("consolidado_notas", [{"promedio": 70.0}])
        assert {x.icono for x in m} <= {"students", "grades", "check", "warning"}


@pytest.mark.parametrize(
    "raw,esperado",
    [("0", 0), ("42", 42), (None, None)],
)
def test_coercion_borde(raw, esperado):
    p = _p()
    p.set_grupo(raw)
    assert p.estado["grupo_id"] == esperado
