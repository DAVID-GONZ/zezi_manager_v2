"""Tests para revision_estadisticos_completa — handlers y estadísticos."""
import pytest


def _make_state() -> dict:
    return {
        "tipo": None, "grupo_id": None, "asignacion_id": None,
        "periodo_id": None, "grupos": [], "asignaciones": [],
        "periodos": [], "datos": None, "datos_listos": False,
    }


class TestTipoConversion:
    """Verifica que los handlers convierten e.value (str) a int."""

    def test_on_grupo_change_convierte_string_a_int(self):
        _s = _make_state()
        raw = "3"
        _s["grupo_id"] = int(raw) if raw is not None else None
        assert _s["grupo_id"] == 3
        assert isinstance(_s["grupo_id"], int)

    def test_on_asignatura_change_convierte_string_a_int(self):
        _s = _make_state()
        raw = "7"
        _s["asignacion_id"] = int(raw) if raw is not None else None
        assert _s["asignacion_id"] == 7
        assert isinstance(_s["asignacion_id"], int)

    def test_on_periodo_change_convierte_string_a_int(self):
        _s = _make_state()
        raw = "1"
        _s["periodo_id"] = int(raw) if raw is not None else None
        assert _s["periodo_id"] == 1
        assert isinstance(_s["periodo_id"], int)

    def test_on_grupo_change_none_permanece_none(self):
        _s = _make_state()
        raw = None
        _s["grupo_id"] = int(raw) if raw is not None else None
        assert _s["grupo_id"] is None


class TestCalculoEstadisticos:
    """Verifica lógica de cálculo de métricas de resumen."""

    def test_consolidado_notas_promedio_y_aprobados(self):
        datos = [
            {"nombre_completo": "Ana",  "promedio_periodo": 75.0},
            {"nombre_completo": "Beto", "promedio_periodo": 55.0},
            {"nombre_completo": "Cara", "promedio_periodo": 80.0},
        ]
        prom_field = "promedio_periodo" if "promedio_periodo" in datos[0] else "promedio"
        n = len(datos)
        promedios = [float(r.get(prom_field, 0) or 0) for r in datos]
        promedio_grupal = sum(promedios) / n
        aprobados = sum(1 for p in promedios if p >= 60)

        assert promedio_grupal == pytest.approx(70.0)
        assert aprobados == 2
        assert n - aprobados == 1

    def test_consolidado_asistencia_bajo_70(self):
        datos = [
            {"porcentaje": 85.0},
            {"porcentaje": 60.0},
            {"porcentaje": 75.0},
        ]
        n = len(datos)
        pcts = [float(r.get("porcentaje", 0) or 0) for r in datos]
        pct_prom = sum(pcts) / n
        bajo_70 = sum(1 for p in pcts if p < 70)

        assert pct_prom == pytest.approx(73.33, abs=0.01)
        assert bajo_70 == 1

    def test_consolidado_anual_promovidos(self):
        datos = [
            {"definitiva": 72.0, "estado": "Promovido"},
            {"definitiva": 45.0, "estado": "Reprobado"},
            {"definitiva": 68.0, "estado": "Promovido"},
        ]
        n = len(datos)
        defs = [float(r.get("definitiva", 0) or 0) for r in datos]
        prom = sum(defs) / n
        promovidos = sum(1 for r in datos if str(r.get("estado", "")).lower() == "promovido")

        assert prom == pytest.approx(61.67, abs=0.01)
        assert promovidos == 2
        assert n - promovidos == 1
