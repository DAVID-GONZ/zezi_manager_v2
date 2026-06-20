"""Tests unitarios del modelo de dominio Institucion (paso_24)."""
from __future__ import annotations

import pytest
from datetime import date

from src.domain.models.institucion import (
    Institucion,
    InstitucionResumenDTO,
    NuevaInstitucionDTO,
)


class TestInstitucion:

    def test_crea_con_defaults(self):
        i = Institucion(nombre="Colegio X")
        assert i.id is None
        assert i.activa is True
        assert i.nit is None and i.codigo is None
        assert i.fecha_creacion == date.today()

    def test_normaliza_nombre(self):
        i = Institucion(nombre="  Colegio Y  ")
        assert i.nombre == "Colegio Y"

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValueError):
            Institucion(nombre="   ")

    def test_nombre_muy_largo_falla(self):
        with pytest.raises(ValueError):
            Institucion(nombre="x" * 201)

    def test_opcionales_vacios_a_none(self):
        i = Institucion(nombre="C", nit="  ", codigo="")
        assert i.nit is None
        assert i.codigo is None

    def test_nombre_display(self):
        assert Institucion(nombre="C").nombre_display == "C"
        assert Institucion(nombre="C", activa=False).nombre_display == "C (inactiva)"


class TestNuevaInstitucionDTO:

    def test_to_institucion(self):
        dto = NuevaInstitucionDTO(nombre="Nueva", nit="900", codigo="111")
        i = dto.to_institucion()
        assert isinstance(i, Institucion)
        assert i.nombre == "Nueva"
        assert i.nit == "900"
        assert i.codigo == "111"

    def test_nombre_invalido_falla(self):
        with pytest.raises(ValueError):
            NuevaInstitucionDTO(nombre="")


class TestInstitucionResumenDTO:

    def test_desde_institucion(self):
        i = Institucion(id=5, nombre="Resumen", activa=False)
        r = InstitucionResumenDTO.desde_institucion(i)
        assert r.id == 5
        assert r.nombre == "Resumen"
        assert r.activa is False

    def test_sin_id_falla(self):
        with pytest.raises(ValueError):
            InstitucionResumenDTO.desde_institucion(Institucion(nombre="X"))
