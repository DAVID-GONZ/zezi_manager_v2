"""Tests del AlertasPresenter — view-model de la página de alertas."""
from __future__ import annotations

from types import SimpleNamespace

from src.interface.presenters.convivencia.alertas_presenter import AlertasPresenter


def _alerta(nivel, resuelta=False):
    return SimpleNamespace(nivel=nivel, resuelta=resuelta)


class TestFiltros:
    def test_cadena_vacia_se_vuelve_none(self):
        p = AlertasPresenter()
        p.set_tipo("")
        p.set_nivel("")
        assert p.estado["filtro_tipo"] is None
        assert p.estado["filtro_nivel"] is None

    def test_valores_se_guardan(self):
        p = AlertasPresenter()
        p.set_tipo("promedio_bajo")
        p.set_nivel("critica")
        p.set_pendientes(False)
        assert p.estado["filtro_tipo"] == "promedio_bajo"
        assert p.estado["filtro_nivel"] == "critica"
        assert p.estado["solo_pendientes"] is False


class TestNivelClave:
    def test_normaliza_enum_str(self):
        assert AlertasPresenter.nivel_clave("NivelAlerta.critica") == "critica"

    def test_normaliza_valor_plano(self):
        assert AlertasPresenter.nivel_clave("ADVERTENCIA") == "advertencia"


class TestKpis:
    def test_cuenta_total_criticas_y_pendientes(self):
        alertas = [
            _alerta("NivelAlerta.critica", resuelta=False),
            _alerta("critica", resuelta=True),
            _alerta("info", resuelta=False),
        ]
        k = AlertasPresenter.kpis(alertas)
        assert k["total"] == 3
        assert k["criticas"] == 2       # ambas formas de 'critica'
        assert k["pendientes"] == 2     # las dos no resueltas

    def test_lista_vacia(self):
        k = AlertasPresenter.kpis([])
        assert k == {"total": 0, "criticas": 0, "pendientes": 0}
