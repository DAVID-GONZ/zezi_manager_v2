"""Tests del ObservacionesPresenter."""
from __future__ import annotations

import pytest

from src.interface.presenters.convivencia.observaciones_presenter import ObservacionesPresenter


def test_aplicar_seleccion_copia_y_resetea_estudiantes():
    p = ObservacionesPresenter()
    p.estado["sel_estudiante_ids"] = [1, 2]
    p.aplicar_seleccion({
        "sel_periodo_id": 3,
        "sel_grupo_id": 10,
        "sel_asignacion_id": 7,
        "sel_asignacion_nombre": "Matemáticas",
    })
    assert p.estado["sel_periodo_id"] == 3
    assert p.estado["sel_grupo_id"] == 10
    assert p.estado["sel_asignacion_id"] == 7
    assert p.estado["sel_asignacion_nombre"] == "Matemáticas"
    assert p.estado["sel_estudiante_ids"] == []


# ===========================================================================
# Tests del observador (convivencia_37)
# ===========================================================================

class _FakeConvivenciaService:
    """Stub mínimo del ConvivenciaService para el presenter."""

    def __init__(self, entradas=None, resumen=None, lanzar=False):
        self._entradas = entradas or []
        self._resumen = resumen or {}
        self._lanzar = lanzar
        self.llamadas: list[tuple] = []

    def observador_estudiante(self, estudiante_id, anio_id, periodo_id=None):
        self.llamadas.append((estudiante_id, anio_id, periodo_id))
        if self._lanzar:
            raise RuntimeError("Fallo simulado")
        return {
            "estudiante": {"nombre": "Test Est"},
            "institucion": {},
            "anio": str(anio_id),
            "periodo": None,
            "entradas": self._entradas,
            "resumen": self._resumen,
        }


class TestCargarObservador:
    def test_actualiza_entradas_y_resumen(self):
        svc = _FakeConvivenciaService(
            entradas=[{"tipo": "registro", "fecha": None}],
            resumen={"fortalezas": 1},
        )
        p = ObservacionesPresenter()
        p.cargar_observador(estudiante_id=1, anio_id=2026, convivencia_service=svc)

        assert p.estado["observador_estudiante_id"] == 1
        assert len(p.estado["observador_entradas"]) == 1
        assert p.estado["observador_resumen"]["fortalezas"] == 1
        assert p.estado["observador_error"] is None
        assert p.estado["observador_cargando"] is False

    def test_puede_exportar_true_cuando_hay_entradas(self):
        svc = _FakeConvivenciaService(entradas=[{"tipo": "registro"}])
        p = ObservacionesPresenter()
        p.cargar_observador(estudiante_id=1, anio_id=2026, convivencia_service=svc)
        assert p.puede_exportar() is True

    def test_puede_exportar_false_sin_entradas(self):
        p = ObservacionesPresenter()
        assert p.puede_exportar() is False

    def test_error_en_servicio_pone_error_y_no_lanza(self):
        svc = _FakeConvivenciaService(lanzar=True)
        p = ObservacionesPresenter()
        # No debe propagar la excepción
        p.cargar_observador(estudiante_id=1, anio_id=2026, convivencia_service=svc)
        assert p.estado["observador_error"] is not None
        assert p.estado["observador_entradas"] == []

    def test_sin_servicio_pone_error(self):
        p = ObservacionesPresenter()
        p.cargar_observador(estudiante_id=1, anio_id=2026, convivencia_service=None)
        assert p.estado["observador_error"] is not None
        assert p.puede_exportar() is False

    def test_aplicar_seleccion_resetea_observador(self):
        svc = _FakeConvivenciaService(entradas=[{"tipo": "registro"}])
        p = ObservacionesPresenter()
        p.cargar_observador(estudiante_id=1, anio_id=2026, convivencia_service=svc)
        assert p.puede_exportar() is True

        # Cambiar grupo limpia el observador
        p.aplicar_seleccion({
            "sel_periodo_id": 3,
            "sel_grupo_id": 20,
            "sel_asignacion_id": 7,
        })
        assert p.estado["observador_estudiante_id"] is None
        assert p.estado["observador_entradas"] == []
        assert p.puede_exportar() is False

    def test_cargar_observador_llama_servicio_con_periodo(self):
        svc = _FakeConvivenciaService()
        p = ObservacionesPresenter()
        p.cargar_observador(
            estudiante_id=5, anio_id=2026, periodo_id=3, convivencia_service=svc
        )
        assert svc.llamadas == [(5, 2026, 3)]
