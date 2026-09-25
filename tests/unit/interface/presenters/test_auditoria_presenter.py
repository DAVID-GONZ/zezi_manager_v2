"""Tests del AuditoriaPresenter — helpers puros + construcción del filtro DTO.

obs_09 T11: cubre set_registro, set_institucion (centinela), set_actores,
abrir_detalle/cerrar_detalle, nombre_actor y la propagación de registro_id /
sin_institucion en construir_filtro.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from src.interface.presenters.admin.auditoria_presenter import (
    AuditoriaPresenter,
    _SIN_INSTITUCION_SENTINEL,
)


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


# ---------------------------------------------------------------------------
# obs_09 T11 — nuevas transiciones y filtros
# ---------------------------------------------------------------------------

class TestSetInstitucionConCentinela:
    def test_centinela_activa_sin_institucion(self):
        p = AuditoriaPresenter()
        p.set_institucion(_SIN_INSTITUCION_SENTINEL)
        assert p.estado["sin_institucion"] is True
        assert p.estado["institucion_id"] is None

    def test_entero_limpia_sin_institucion(self):
        """Tras activar el centinela, pasar un ID normal deshabilita sin_institucion."""
        p = AuditoriaPresenter()
        p.set_institucion(_SIN_INSTITUCION_SENTINEL)
        p.set_institucion("5")
        assert p.estado["sin_institucion"] is False
        assert p.estado["institucion_id"] == 5

    def test_none_limpia_ambos(self):
        p = AuditoriaPresenter()
        p.set_institucion(_SIN_INSTITUCION_SENTINEL)
        p.set_institucion(None)
        assert p.estado["sin_institucion"] is False
        assert p.estado["institucion_id"] is None


class TestSetRegistro:
    def test_coerciona_a_int(self):
        p = AuditoriaPresenter()
        p.set_registro("42")
        assert p.estado["registro_id"] == 42

    def test_vacio_es_none(self):
        p = AuditoriaPresenter()
        p.set_registro("")
        assert p.estado["registro_id"] is None

    def test_none_es_none(self):
        p = AuditoriaPresenter()
        p.set_registro(None)
        assert p.estado["registro_id"] is None


class TestDetalleDialog:
    def test_abrir_almacena_dto(self):
        p = AuditoriaPresenter()
        dto_ficticio = object()
        p.abrir_detalle(dto_ficticio)
        assert p.estado["detalle"] is dto_ficticio

    def test_cerrar_limpia_detalle(self):
        p = AuditoriaPresenter()
        p.abrir_detalle(object())
        p.cerrar_detalle()
        assert p.estado["detalle"] is None


class TestSetActores:
    def test_almacena_mapa(self):
        p = AuditoriaPresenter()
        p.set_actores({1: "Ana", 2: "Pedro"})
        assert p.estado["actores"] == {1: "Ana", 2: "Pedro"}

    def test_copia_defensiva(self):
        """set_actores no debe guardar la misma referencia que se pasó."""
        p = AuditoriaPresenter()
        original = {1: "Ana"}
        p.set_actores(original)
        original[2] = "intruso"
        assert 2 not in p.estado["actores"]


class TestNombreActor:
    """nombre_actor: cascada repo → snapshot → #ID → «—»."""

    def _cambio(self, usuario_id=None, usuario=None):
        return SimpleNamespace(usuario_id=usuario_id, usuario=usuario)

    def test_resuelve_desde_mapa_actores(self):
        p = AuditoriaPresenter()
        p.set_actores({7: "María Docente"})
        cambio = self._cambio(usuario_id=7, usuario="snap")
        assert p.nombre_actor(cambio) == "María Docente"

    def test_fallback_snapshot_si_no_en_mapa(self):
        p = AuditoriaPresenter()
        p.set_actores({})
        cambio = self._cambio(usuario_id=99, usuario="snap_user")
        assert p.nombre_actor(cambio) == "snap_user"

    def test_fallback_id_si_solo_hay_usuario_id(self):
        p = AuditoriaPresenter()
        cambio = self._cambio(usuario_id=55, usuario=None)
        assert p.nombre_actor(cambio) == "Usuario #55"

    def test_fallback_dash_si_nada(self):
        p = AuditoriaPresenter()
        cambio = self._cambio(usuario_id=None, usuario=None)
        assert p.nombre_actor(cambio) == "—"


class TestConstruirFiltroObs09:
    def test_registro_id_se_propaga(self):
        p = AuditoriaPresenter()
        p.set_registro("10")
        f = p.construir_filtro(por_pagina=25)
        assert f.registro_id == 10

    def test_sin_institucion_se_propaga(self):
        p = AuditoriaPresenter()
        p.set_institucion(_SIN_INSTITUCION_SENTINEL)
        f = p.construir_filtro(por_pagina=25)
        assert f.sin_institucion is True
        assert f.institucion_id is None

    def test_sin_filtros_obs09_defaults(self):
        """Por defecto registro_id es None y sin_institucion es False."""
        p = AuditoriaPresenter()
        f = p.construir_filtro(por_pagina=25)
        assert f.registro_id is None
        assert f.sin_institucion is False
