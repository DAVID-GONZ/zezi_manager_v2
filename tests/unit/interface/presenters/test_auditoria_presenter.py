"""Tests del AuditoriaPresenter — helpers puros + construcción del filtro DTO."""
from __future__ import annotations

from datetime import datetime

from src.interface.presenters.admin.auditoria_presenter import AuditoriaPresenter


class TestAInt:
    def test_convierte_y_tolera_basura(self):
        assert AuditoriaPresenter.a_int("42") == 42
        assert AuditoriaPresenter.a_int("  7 ") == 7
        assert AuditoriaPresenter.a_int("") is None
        assert AuditoriaPresenter.a_int(None) is None
        assert AuditoriaPresenter.a_int("abc") is None


class TestParsearFecha:
    def test_none_o_invalida(self):
        assert AuditoriaPresenter.parsear_fecha(None) is None
        assert AuditoriaPresenter.parsear_fecha("no-fecha") is None

    def test_inicio_de_dia(self):
        d = AuditoriaPresenter.parsear_fecha("2026-08-23")
        assert d == datetime(2026, 8, 23, 0, 0, 0)

    def test_fin_de_dia(self):
        d = AuditoriaPresenter.parsear_fecha("2026-08-23", fin_de_dia=True)
        assert d == datetime(2026, 8, 23, 23, 59, 59)


class TestTransiciones:
    def test_set_usuario_coerciona(self):
        p = AuditoriaPresenter()
        p.set_usuario("  5 ")
        assert p.estado["usuario_id"] == 5

    def test_set_tabla_normaliza_vacio_a_none(self):
        p = AuditoriaPresenter()
        p.set_tabla("   ")
        assert p.estado["tabla"] is None
        p.set_tabla(" usuarios ")
        assert p.estado["tabla"] == "usuarios"

    def test_reset_pagina(self):
        p = AuditoriaPresenter()
        p.set_pagina(4)
        p.reset_pagina()
        assert p.estado["pagina"] == 1


class TestConstruirFiltro:
    def test_mapea_estado_al_dto(self):
        p = AuditoriaPresenter()
        p.set_rango("2026-01-01", "2026-01-31")
        p.set_usuario("3")
        p.set_tabla("notas")
        p.set_pagina(2)
        f = p.construir_filtro(por_pagina=50)
        assert f.usuario_id == 3
        assert f.tabla == "notas"
        assert f.desde == datetime(2026, 1, 1, 0, 0, 0)
        assert f.hasta == datetime(2026, 1, 31, 23, 59, 59)
        assert f.pagina == 2
        assert f.por_pagina == 50
