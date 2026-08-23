"""Tests de `resumen_consolidado` — lógica de negocio del resumen de consolidados.

Vive en el backend (estadisticos_service) porque aplica los UMBRALES de negocio
(aprobación y asistencia). Aquí se prueban los NÚMEROS; el mapeo a tarjetas de la
UI se prueba aparte, en el presenter.
"""
from __future__ import annotations

import pytest

from src.services.estadisticos_service import (
    UMBRAL_APROBACION,
    UMBRAL_ASISTENCIA,
    resumen_consolidado,
)


def test_sin_datos_devuelve_none():
    assert resumen_consolidado("consolidado_notas", None) is None
    assert resumen_consolidado("consolidado_notas", []) is None
    assert resumen_consolidado("consolidado_notas", {}) is None


class TestNotas:
    def test_promedio_y_aprobados(self):
        datos = [
            {"promedio_periodo": 75.0},
            {"promedio_periodo": 55.0},
            {"promedio_periodo": 80.0},
        ]
        r = resumen_consolidado("consolidado_notas", datos)
        assert r.clase == "notas"
        assert r.n == 3
        assert r.promedio_grupal == pytest.approx(70.0)
        assert r.aprobados == 2
        assert r.reprobados == 1

    def test_nota_en_el_umbral_exacto_cuenta_como_aprobado(self):
        # 60.0 == UMBRAL_APROBACION → aprobado (>=).
        r = resumen_consolidado("consolidado_notas", [{"promedio": UMBRAL_APROBACION}])
        assert r.aprobados == 1
        assert r.reprobados == 0

    def test_usa_promedio_si_no_hay_promedio_periodo(self):
        r = resumen_consolidado("consolidado_notas", [{"promedio": 90.0}])
        assert r.promedio_grupal == pytest.approx(90.0)


class TestRanking:
    def test_agrega_mejor_y_menor(self):
        r = resumen_consolidado("ranking_grupo", [{"promedio": 90.0}, {"promedio": 40.0}])
        assert r.clase == "ranking"
        assert r.mejor == pytest.approx(90.0)
        assert r.menor == pytest.approx(40.0)


class TestAsistencia:
    def test_promedio_y_bajo_umbral(self):
        datos = [{"porcentaje": 85.0}, {"porcentaje": 60.0}, {"porcentaje": 75.0}]
        r = resumen_consolidado("consolidado_asistencia", datos)
        assert r.clase == "asistencia"
        assert r.pct_asistencia_prom == pytest.approx(73.333, abs=0.01)
        assert r.bajo_umbral_asistencia == 1  # solo el 60

    def test_asistencia_en_el_umbral_exacto_no_cuenta_como_baja(self):
        # 70.0 == UMBRAL_ASISTENCIA → NO es "baja" (comparación estricta <).
        r = resumen_consolidado("consolidado_asistencia", [{"porcentaje": UMBRAL_ASISTENCIA}])
        assert r.bajo_umbral_asistencia == 0


class TestAnual:
    def test_promovidos_y_reprobados(self):
        datos = [
            {"definitiva": 72.0, "estado": "Promovido"},
            {"definitiva": 45.0, "estado": "Reprobado"},
            {"definitiva": 68.0, "estado": "Promovido"},
        ]
        r = resumen_consolidado("consolidado_anual", datos)
        assert r.clase == "anual"
        assert r.definitiva_prom == pytest.approx(61.667, abs=0.01)
        assert r.promovidos == 2
        assert r.reprobados == 1


class TestGenerico:
    def test_dict_suma_valores(self):
        r = resumen_consolidado("distribucion_desempenos", {"alto": 4, "bajo": 6})
        assert r.clase == "generico"
        assert r.total_registros == 10

    def test_lista_de_otro_tipo_cuenta_longitud(self):
        r = resumen_consolidado("tendencia_asistencia", [{"x": 1}, {"x": 2}])
        assert r.clase == "generico"
        assert r.total_registros == 2
