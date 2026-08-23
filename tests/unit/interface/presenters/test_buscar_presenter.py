"""Tests del BuscarPresenter — view-model de `/buscar` (llaman al código real)."""
from __future__ import annotations

from types import SimpleNamespace

from src.interface.presenters.buscar_presenter import BuscarPresenter


def _resultado(total_por_tipo: dict[str, int]):
    return SimpleNamespace(total_por_tipo=total_por_tipo)


class TestInicial:
    def test_termino_inicial_se_normaliza(self):
        assert BuscarPresenter("  ana  ").estado["termino"] == "ana"

    def test_estado_arranca_en_todos_y_pagina_1(self):
        p = BuscarPresenter()
        assert p.estado["tipo_filtro"] is None
        assert p.estado["pagina"] == 1
        assert p.estado["resultados"] is None


class TestTransiciones:
    def test_set_termino_normaliza_y_resetea_pagina(self):
        p = BuscarPresenter()
        p.set_pagina(3)
        p.set_termino("  juan  ")
        assert p.estado["termino"] == "juan"
        assert p.estado["pagina"] == 1

    def test_set_tab_resetea_pagina(self):
        p = BuscarPresenter()
        p.set_pagina(4)
        p.set_tab("estudiante")
        assert p.estado["tipo_filtro"] == "estudiante"
        assert p.estado["pagina"] == 1

    def test_set_pagina_y_resultados(self):
        p = BuscarPresenter()
        p.set_pagina(2)
        p.set_resultados(_resultado({"estudiante": 3}))
        assert p.estado["pagina"] == 2
        assert p.estado["resultados"] is not None


class TestTerminoBuscable:
    def test_menos_de_dos_caracteres_no_es_buscable(self):
        p = BuscarPresenter("a")
        assert p.termino_buscable() is False

    def test_dos_o_mas_es_buscable(self):
        assert BuscarPresenter("ab").termino_buscable() is True


class TestTotalTexto:
    def test_none_es_cadena_vacia(self):
        assert BuscarPresenter().total_texto(None) == ""

    def test_todos_suma_todos_los_tipos(self):
        p = BuscarPresenter()  # tipo_filtro None → "Todos"
        assert p.total_texto(_resultado({"estudiante": 2, "grupo": 3})) == "5 resultados"

    def test_pestana_activa_cuenta_solo_ese_tipo(self):
        p = BuscarPresenter()
        p.set_tab("grupo")
        assert p.total_texto(_resultado({"estudiante": 2, "grupo": 3})) == "3 resultados"

    def test_singular_sin_s(self):
        p = BuscarPresenter()
        assert p.total_texto(_resultado({"estudiante": 1})) == "1 resultado"
