"""
tests/unit/interface/presenters/test_observabilidad_presenter.py
=================================================================
Tests del presenter de observabilidad (obs_13 — T13).

Importa y llama al presenter REAL (no reimplementa la lógica).

Cubre:
  - Un bloque con error no borra los datos de los demás.
  - Los filtros de log se reflejan en el estado.
  - bloques_con_error() lista solo los bloques fallidos.
"""
from __future__ import annotations

import pytest

from src.interface.presenters.admin.observabilidad_presenter import ObservabilidadPresenter


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def presenter():
    return ObservabilidadPresenter()


# ── Tests: estado inicial ──────────────────────────────────────────────────────

class TestEstadoInicial:
    def test_estado_inicial_todos_los_bloques_vacios(self, presenter):
        estado = presenter.estado
        assert estado["salud"] is None
        assert estado["eventos"] == []
        assert estado["alertas"] == []
        assert estado["uso"] == []

    def test_estado_inicial_sin_errores(self, presenter):
        assert presenter.bloques_con_error() == []

    def test_filtros_iniciales_son_none(self, presenter):
        assert presenter.estado["filtro_nivel"] is None
        assert presenter.estado["filtro_tipo"] is None
        assert presenter.filtros_activos() is False


# ── Tests: aislamiento de errores (R13) ───────────────────────────────────────

class TestAislamientoErrores:
    """Un bloque con error no borra los datos de los demás."""

    def test_error_salud_no_borra_eventos(self, presenter):
        """Error en salud deja los eventos intactos."""
        entradas = [{"tipo_evento": "LOGIN_EXITOSO"}]
        presenter.cargar_eventos(entradas, disponible=True)
        presenter.error_salud("BD inaccesible")

        assert presenter.estado["error_salud"] is not None
        assert presenter.estado["eventos"] == entradas  # intacto

    def test_error_eventos_no_borra_salud(self, presenter):
        """Error en eventos deja el bloque de salud intacto."""
        from src.domain.models.observabilidad import SaludDTO
        salud = SaludDTO(
            integra=True,
            version="2.0.0",
            uptime_segundos=100.0,
            tamanio_db_bytes=1024,
            ultimo_backup=None,
        )
        presenter.cargar_salud(salud)
        presenter.error_eventos("Archivo no legible")

        assert presenter.estado["salud"] is salud  # intacto
        assert presenter.estado["error_eventos"] is not None
        assert presenter.estado["eventos"] == []

    def test_error_alertas_no_borra_uso(self, presenter):
        """Error en alertas deja el bloque de uso intacto."""
        uso_data = [{"fecha": "2026-09-26", "logins": 5, "denegados": 0}]
        presenter.cargar_uso(uso_data)
        presenter.error_alertas("Error de política")

        assert presenter.estado["uso"] == uso_data  # intacto
        assert presenter.estado["error_alertas"] is not None

    def test_error_uso_no_borra_alertas(self, presenter):
        """Error en uso deja las alertas intactas."""
        alertas_data = [{"ip": "10.0.0.1", "fallos": 5, "segundos_restantes": 120.0}]
        presenter.cargar_alertas(alertas_data)
        presenter.error_uso("Fallo SQL")

        assert presenter.estado["alertas"] == alertas_data  # intacto
        assert presenter.estado["error_uso"] is not None

    def test_multiples_errores_reportados_correctamente(self, presenter):
        """bloques_con_error() lista todos los bloques con error."""
        presenter.error_salud("err1")
        presenter.error_eventos("err2")
        errores = presenter.bloques_con_error()
        assert "salud" in errores
        assert "eventos" in errores
        assert "alertas" not in errores
        assert "uso" not in errores


# ── Tests: filtros ─────────────────────────────────────────────────────────────

class TestFiltros:
    """Los filtros de log se reflejan en el estado."""

    def test_set_filtro_tipo_actualiza_estado(self, presenter):
        presenter.set_filtro_tipo("LOGIN_FALLIDO")
        assert presenter.estado["filtro_tipo"] == "LOGIN_FALLIDO"
        assert presenter.filtros_activos() is True

    def test_set_filtro_nivel_actualiza_estado(self, presenter):
        presenter.set_filtro_nivel("WARNING")
        assert presenter.estado["filtro_nivel"] == "WARNING"
        assert presenter.filtros_activos() is True

    def test_filtro_vacio_limpia_filtro(self, presenter):
        presenter.set_filtro_tipo("LOGIN_EXITOSO")
        presenter.set_filtro_tipo("")  # limpiar
        assert presenter.estado["filtro_tipo"] is None

    def test_filtros_activos_ninguno(self, presenter):
        assert presenter.filtros_activos() is False

    def test_filtros_activos_uno_basta(self, presenter):
        presenter.set_filtro_tipo("LOGIN_EXITOSO")
        assert presenter.filtros_activos() is True


# ── Tests: cargar datos ────────────────────────────────────────────────────────

class TestCargarDatos:

    def test_cargar_salud_limpia_error_previo(self, presenter):
        presenter.error_salud("error anterior")
        from src.domain.models.observabilidad import SaludDTO
        salud = SaludDTO(integra=True, version="2.0", uptime_segundos=1.0, tamanio_db_bytes=0)
        presenter.cargar_salud(salud)
        assert presenter.estado["error_salud"] is None
        assert presenter.estado["salud"] is salud

    def test_cargar_eventos_actualiza_disponible(self, presenter):
        presenter.cargar_eventos([], disponible=False)
        assert presenter.estado["log_disponible"] is False

    def test_cargar_alertas_limpia_error_previo(self, presenter):
        presenter.error_alertas("err")
        presenter.cargar_alertas([])
        assert presenter.estado["error_alertas"] is None

    def test_cargar_uso_limpia_error_previo(self, presenter):
        presenter.error_uso("err")
        presenter.cargar_uso([{"fecha": "2026-09-26", "logins": 1, "denegados": 0}])
        assert presenter.estado["error_uso"] is None
