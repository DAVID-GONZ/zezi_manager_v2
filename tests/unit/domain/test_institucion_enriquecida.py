"""
Tests de dominio para Institucion enriquecida (mejora_06).
"""
import pytest
from pydantic import ValidationError

from src.domain.models.institucion import (
    Institucion,
    JornadaPrincipal,
    TipoInstitucion,
    Calendario,
    ActualizarInstitucionDTO,
)
from src.domain.models.configuracion import InformacionInstitucionalDTO


# ---------------------------------------------------------------------------
# Institucion — campos opcionales
# ---------------------------------------------------------------------------

def test_institucion_campos_opcionales_vacios():
    """Crear Institucion sin campos nuevos no lanza."""
    inst = Institucion(nombre="IE Test")
    assert inst.nombre_oficial is None
    assert inst.codigo_dane is None
    assert inst.rector is None
    assert inst.jornada_principal is None
    assert inst.tipo_institucion is None
    assert inst.calendario is None


# ---------------------------------------------------------------------------
# Validador codigo_dane
# ---------------------------------------------------------------------------

def test_codigo_dane_invalido_lanza():
    """codigo_dane con menos de 12 dígitos → ValidationError."""
    with pytest.raises(ValidationError):
        Institucion(nombre="IE Test", codigo_dane="12345")


def test_codigo_dane_no_numerico_lanza():
    """codigo_dane con letras → ValidationError."""
    with pytest.raises(ValidationError):
        Institucion(nombre="IE Test", codigo_dane="1234567890ab")


def test_codigo_dane_valido():
    """codigo_dane con exactamente 12 dígitos → OK."""
    inst = Institucion(nombre="IE Test", codigo_dane="123456789012")
    assert inst.codigo_dane == "123456789012"


# ---------------------------------------------------------------------------
# Validador nombre_oficial
# ---------------------------------------------------------------------------

def test_nombre_oficial_vacio_lanza():
    """nombre_oficial vacío (cadena vacía) → ValidationError."""
    with pytest.raises(ValidationError):
        Institucion(nombre="IE Test", nombre_oficial="")


def test_nombre_oficial_demasiado_largo_lanza():
    """nombre_oficial > 200 chars → ValidationError."""
    with pytest.raises(ValidationError):
        Institucion(nombre="IE Test", nombre_oficial="A" * 201)


# ---------------------------------------------------------------------------
# ActualizarInstitucionDTO.aplicar_a
# ---------------------------------------------------------------------------

def test_actualizar_dto_aplica_solo_no_nulos():
    """aplicar_a() cambia rector, no toca nombre_oficial None."""
    inst = Institucion(nombre="IE Test", nombre_oficial="Inst. Oficial")
    dto = ActualizarInstitucionDTO(rector="Dr. López")
    inst2 = dto.aplicar_a(inst)
    assert inst2.rector == "Dr. López"
    assert inst2.nombre_oficial == "Inst. Oficial"  # no tocado


# ---------------------------------------------------------------------------
# InformacionInstitucionalDTO.desde_institucion
# ---------------------------------------------------------------------------

def _institucion_completa() -> Institucion:
    return Institucion(
        nombre="IE Corta",
        nombre_oficial="Inst. Educativa Completa",
        codigo_dane="123456789012",
        rector="Rectora Ana",
        direccion="Calle 1",
        municipio="Bogotá",
        telefono="3001234567",
    )


def test_informacion_institucional_desde_institucion_ok():
    """Institucion con DANE + rector construye DTO correctamente."""
    inst = _institucion_completa()
    dto = InformacionInstitucionalDTO.desde_institucion(
        inst, anio=2026, nota_minima_aprobacion=60.0
    )
    assert dto.anio == 2026
    assert dto.dane_code == "123456789012"
    assert dto.rector == "Rectora Ana"
    assert dto.nota_minima_aprobacion == 60.0


def test_informacion_institucional_desde_institucion_sin_dane_lanza():
    """Institucion sin codigo_dane → ValueError."""
    inst = Institucion(nombre="IE Test", rector="Dr. X")
    with pytest.raises(ValueError, match="código DANE"):
        InformacionInstitucionalDTO.desde_institucion(inst, anio=2026, nota_minima_aprobacion=60.0)


def test_informacion_institucional_desde_institucion_sin_rector_lanza():
    """Institucion sin rector → ValueError."""
    inst = Institucion(nombre="IE Test", codigo_dane="123456789012")
    with pytest.raises(ValueError, match="rector"):
        InformacionInstitucionalDTO.desde_institucion(inst, anio=2026, nota_minima_aprobacion=60.0)


def test_informacion_usa_nombre_oficial_si_presente():
    """nombre_oficial prevalece sobre nombre en el DTO."""
    inst = _institucion_completa()
    dto = InformacionInstitucionalDTO.desde_institucion(inst, anio=2026, nota_minima_aprobacion=60.0)
    assert dto.nombre_institucion == "Inst. Educativa Completa"
