"""Tests unitarios — PlantillaFranja, Franja, DTOs (paso_15a)."""
import pytest
from pydantic import ValidationError

from src.domain.models.infraestructura import (
    DIAS_VALIDOS,
    Franja,
    NuevaFranjaDTO,
    NuevaPlantillaFranjaDTO,
    PlantillaFranja,
)


# ---------------------------------------------------------------------------
# Franja — validadores
# ---------------------------------------------------------------------------

def test_franja_valida_basica():
    f = Franja(plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="07:55")
    assert f.es_lectiva
    assert f.tipo == "lectiva"


def test_franja_tipo_descanso():
    f = Franja(plantilla_id=1, orden=4, hora_inicio="09:45", hora_fin="10:15",
               tipo="descanso", etiqueta="Recreo")
    assert not f.es_lectiva
    assert f.etiqueta == "Recreo"


def test_franja_tipo_almuerzo():
    f = Franja(plantilla_id=1, orden=6, hora_inicio="12:00", hora_fin="13:00",
               tipo="almuerzo")
    assert not f.es_lectiva


def test_franja_tipo_invalido():
    with pytest.raises(ValidationError):
        Franja(plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="07:55",
               tipo="libre")


def test_franja_orden_cero_invalido():
    with pytest.raises(ValidationError):
        Franja(plantilla_id=1, orden=0, hora_inicio="07:00", hora_fin="07:55")


def test_franja_orden_negativo_invalido():
    with pytest.raises(ValidationError):
        Franja(plantilla_id=1, orden=-1, hora_inicio="07:00", hora_fin="07:55")


def test_franja_hora_inicio_igual_hora_fin():
    with pytest.raises(ValidationError):
        Franja(plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="07:00")


def test_franja_hora_inicio_mayor_que_hora_fin():
    with pytest.raises(ValidationError):
        Franja(plantilla_id=1, orden=1, hora_inicio="08:00", hora_fin="07:00")


def test_franja_etiqueta_strip():
    f = Franja(plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="07:55",
               etiqueta="  Recreo  ")
    assert f.etiqueta == "Recreo"


def test_franja_etiqueta_vacia_queda_none():
    f = Franja(plantilla_id=1, orden=1, hora_inicio="07:00", hora_fin="07:55",
               etiqueta="   ")
    assert f.etiqueta is None


def test_franja_plantilla_id_invalido():
    with pytest.raises(ValidationError):
        Franja(plantilla_id=0, orden=1, hora_inicio="07:00", hora_fin="07:55")


# ---------------------------------------------------------------------------
# PlantillaFranja — validadores
# ---------------------------------------------------------------------------

def test_plantilla_valida():
    p = PlantillaFranja(
        nombre="Jornada única",
        jornada="UNICA",
        dias_activos=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
    )
    assert p.activa is False
    assert len(p.dias_activos) == 5


def test_plantilla_nombre_vacio_invalido():
    with pytest.raises(ValidationError):
        PlantillaFranja(nombre="   ", jornada="UNICA",
                        dias_activos=["Lunes"])


def test_plantilla_jornada_invalida():
    with pytest.raises(ValidationError):
        PlantillaFranja(nombre="Jornada X", jornada="COMPLETA",
                        dias_activos=["Lunes"])


def test_plantilla_dia_invalido():
    with pytest.raises(ValidationError):
        PlantillaFranja(nombre="Test", jornada="AM",
                        dias_activos=["Lunes", "Sunday"])


def test_plantilla_dias_vacios():
    with pytest.raises(ValidationError):
        PlantillaFranja(nombre="Test", jornada="AM", dias_activos=[])


def test_plantilla_dias_como_csv_string():
    p = PlantillaFranja(nombre="AM", jornada="AM",
                        dias_activos="Lunes,Martes,Jueves")
    assert p.dias_activos == ["Lunes", "Martes", "Jueves"]


def test_plantilla_jornada_lowercase_normalizada():
    p = PlantillaFranja(nombre="PM", jornada="pm",
                        dias_activos=["Lunes"])
    assert p.jornada == "PM"


def test_dias_validos_coherente_con_diasemana():
    assert "Lunes" in DIAS_VALIDOS
    assert "Sábado" in DIAS_VALIDOS
    assert len(DIAS_VALIDOS) == 6


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

def test_nueva_plantilla_dto_to_plantilla():
    dto = NuevaPlantillaFranjaDTO(
        nombre="Jornada tarde",
        jornada="PM",
        dias_activos=["Lunes", "Miércoles", "Viernes"],
    )
    p = dto.to_plantilla()
    assert isinstance(p, PlantillaFranja)
    assert p.nombre == "Jornada tarde"
    assert p.jornada == "PM"
    assert p.id is None


def test_nueva_franja_dto_to_franja():
    dto = NuevaFranjaDTO(
        plantilla_id=5,
        orden=2,
        hora_inicio="08:00",
        hora_fin="08:55",
        tipo="lectiva",
    )
    f = dto.to_franja()
    assert isinstance(f, Franja)
    assert f.plantilla_id == 5
    assert f.orden == 2
    assert f.es_lectiva
