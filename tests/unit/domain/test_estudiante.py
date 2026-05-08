"""
Tests unitarios — Estudiante
=============================

Validan las reglas de negocio encapsuladas en el modelo.
Sin BD, sin NiceGUI, sin infraestructura.

Ejecutar:
    pytest tests/unit/domain/test_estudiante.py -v
"""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from src.domain.models.estudiante import (
    Estudiante,
    EstadoMatricula,
    Genero,
    TipoDocumento,
    ActualizarEstudianteDTO,
    EstudianteResumenDTO,
    FiltroEstudiantesDTO,
    NuevoEstudianteDTO,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def estudiante_base() -> Estudiante:
    """Estudiante válido con datos mínimos."""
    return Estudiante(
        numero_documento="1098765432",
        nombre="Ana Sofía",
        apellido="García Pérez",
        fecha_nacimiento=date(2010, 6, 15),
    )


@pytest.fixture
def estudiante_completo() -> Estudiante:
    """Estudiante válido con todos los campos."""
    return Estudiante(
        id=1,
        id_publico="EST601001",
        tipo_documento=TipoDocumento.TI,
        numero_documento="1098765432",
        nombre="ana sofía",           # entra en minúscula
        apellido="GARCÍA PÉREZ",      # entra en mayúscula
        genero=Genero.F,
        fecha_nacimiento=date(2010, 6, 15),
        grupo_id=1,
        posee_piar=False,
        estado_matricula=EstadoMatricula.ACTIVO,
    )


# =============================================================================
# Construcción y normalización
# =============================================================================

class TestConstruccion:

    def test_estudiante_minimo_valido(self, estudiante_base):
        assert estudiante_base.numero_documento == "1098765432"
        assert estudiante_base.es_activo

    def test_nombre_normalizado_a_title_case(self, estudiante_completo):
        assert estudiante_completo.nombre   == "Ana Sofía"
        assert estudiante_completo.apellido == "García Pérez"

    def test_documento_normalizado_a_mayusculas(self):
        est = Estudiante(numero_documento="abc123", nombre="Luis", apellido="Pérez")
        assert est.numero_documento == "ABC123"

    def test_id_publico_normalizado(self):
        est = Estudiante(
            id_publico=" est601001 ",
            numero_documento="123",
            nombre="Luis",
            apellido="Pérez",
        )
        assert est.id_publico == "EST601001"

    def test_id_publico_vacio_se_convierte_en_none(self):
        est = Estudiante(
            id_publico="   ",
            numero_documento="123",
            nombre="Luis",
            apellido="Pérez",
        )
        assert est.id_publico is None

    def test_fecha_ingreso_defecto_es_hoy(self):
        est = Estudiante(numero_documento="123", nombre="Luis", apellido="Pérez")
        assert est.fecha_ingreso == date.today()


# =============================================================================
# Validadores de campo
# =============================================================================

class TestValidadoresDocumento:

    def test_documento_vacio_falla(self):
        with pytest.raises(ValidationError) as exc:
            Estudiante(numero_documento="   ", nombre="Luis", apellido="Pérez")
        assert "vacío" in str(exc.value).lower()

    def test_documento_con_caracteres_invalidos_falla(self):
        with pytest.raises(ValidationError) as exc:
            Estudiante(numero_documento="123$%&", nombre="Luis", apellido="Pérez")
        assert "inválidos" in str(exc.value).lower()

    def test_documento_con_guion_es_valido(self):
        est = Estudiante(numero_documento="98-765432", nombre="Luis", apellido="Pérez")
        assert est.numero_documento == "98-765432"


class TestValidadoresNombre:

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError):
            Estudiante(numero_documento="123", nombre="", apellido="Pérez")

    def test_apellido_vacio_falla(self):
        with pytest.raises(ValidationError):
            Estudiante(numero_documento="123", nombre="Luis", apellido="")

    def test_nombre_muy_largo_falla(self):
        with pytest.raises(ValidationError):
            Estudiante(numero_documento="123", nombre="A" * 101, apellido="Pérez")

    def test_nombre_solo_espacios_falla(self):
        with pytest.raises(ValidationError):
            Estudiante(numero_documento="123", nombre="   ", apellido="Pérez")


class TestValidadoresFecha:

    def test_fecha_futura_falla(self):
        manana = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError) as exc:
            Estudiante(
                numero_documento="123",
                nombre="Luis",
                apellido="Pérez",
                fecha_nacimiento=manana,
            )
        assert "futura" in str(exc.value).lower()

    def test_fecha_que_implica_mas_de_25_anos_falla(self):
        hace_30_anos = date(date.today().year - 30, 1, 1)
        with pytest.raises(ValidationError) as exc:
            Estudiante(
                numero_documento="123",
                nombre="Luis",
                apellido="Pérez",
                fecha_nacimiento=hace_30_anos,
            )
        assert "25" in str(exc.value)

    def test_fecha_none_es_valida(self):
        est = Estudiante(
            numero_documento="123",
            nombre="Luis",
            apellido="Pérez",
            fecha_nacimiento=None,
        )
        assert est.fecha_nacimiento is None

    def test_fecha_como_string_isoformat(self):
        est = Estudiante(
            numero_documento="123",
            nombre="Luis",
            apellido="Pérez",
            fecha_nacimiento="2010-06-15",
        )
        assert est.fecha_nacimiento == date(2010, 6, 15)

    def test_fecha_string_invalida_falla(self):
        with pytest.raises(ValidationError):
            Estudiante(
                numero_documento="123",
                nombre="Luis",
                apellido="Pérez",
                fecha_nacimiento="15/06/2010",  # formato incorrecto
            )


# =============================================================================
# Validador de modelo (coherencia documento-edad)
# =============================================================================

class TestCoherenciaDocumentoEdad:

    def test_cc_con_menor_de_17_falla(self):
        fecha = date(date.today().year - 14, 1, 1)  # 14 años
        with pytest.raises(ValidationError) as exc:
            Estudiante(
                tipo_documento=TipoDocumento.CC,
                numero_documento="123456789",
                nombre="Luis",
                apellido="Pérez",
                fecha_nacimiento=fecha,
            )
        assert "CC" in str(exc.value)

    def test_ti_con_mayor_de_19_falla(self):
        fecha = date(date.today().year - 20, 1, 1)  # 20 años
        with pytest.raises(ValidationError) as exc:
            Estudiante(
                tipo_documento=TipoDocumento.TI,
                numero_documento="123456789",
                nombre="Luis",
                apellido="Pérez",
                fecha_nacimiento=fecha,
            )
        assert "TI" in str(exc.value)

    def test_ti_con_menor_es_valido(self, estudiante_base):
        # estudiante_base tiene TI y fecha_nacimiento ~ 14 años → válido
        assert estudiante_base.tipo_documento == TipoDocumento.TI

    def test_cc_con_adulto_es_valido(self):
        fecha = date(date.today().year - 20, 1, 1)  # 20 años
        est = Estudiante(
            tipo_documento=TipoDocumento.CC,
            numero_documento="1234567890",
            nombre="Carlos",
            apellido="López",
            fecha_nacimiento=fecha,
        )
        assert est.tipo_documento == TipoDocumento.CC

    def test_sin_fecha_nacimiento_no_valida_coherencia(self):
        # Sin fecha no hay validación de coherencia
        est = Estudiante(
            tipo_documento=TipoDocumento.CC,
            numero_documento="1234567890",
            nombre="Carlos",
            apellido="López",
            fecha_nacimiento=None,
        )
        assert est.tipo_documento == TipoDocumento.CC

    def test_nuip_acepta_cualquier_edad(self):
        fecha_menor = date(date.today().year - 14, 1, 1)
        est = Estudiante(
            tipo_documento=TipoDocumento.NUIP,
            numero_documento="987654321",
            nombre="María",
            apellido="Torres",
            fecha_nacimiento=fecha_menor,
        )
        assert est.tipo_documento == TipoDocumento.NUIP


# =============================================================================
# Propiedades computadas
# =============================================================================

class TestPropiedades:

    def test_nombre_completo(self, estudiante_completo):
        assert estudiante_completo.nombre_completo == "Ana Sofía García Pérez"

    def test_edad_calculada(self, estudiante_completo):
        # nacida 2010-06-15
        hoy = date.today()
        esperada = (hoy - date(2010, 6, 15)).days // 365
        assert estudiante_completo.edad == esperada

    def test_edad_sin_fecha_es_none(self):
        est = Estudiante(numero_documento="123", nombre="Luis", apellido="Pérez")
        assert est.edad is None

    def test_es_activo_verdadero(self, estudiante_base):
        assert estudiante_base.es_activo is True

    def test_es_activo_falso_si_retirado(self, estudiante_base):
        retirado = estudiante_base.retirar()
        assert retirado.es_activo is False

    def test_puede_recibir_calificaciones_activo(self, estudiante_base):
        assert estudiante_base.puede_recibir_calificaciones is True

    def test_puede_recibir_calificaciones_inactivo(self):
        est = Estudiante(
            numero_documento="123",
            nombre="Luis",
            apellido="Pérez",
            estado_matricula=EstadoMatricula.INACTIVO,
        )
        assert est.puede_recibir_calificaciones is True

    def test_no_puede_recibir_calificaciones_retirado(self):
        est = Estudiante(
            numero_documento="123",
            nombre="Luis",
            apellido="Pérez",
            estado_matricula=EstadoMatricula.RETIRADO,
        )
        assert est.puede_recibir_calificaciones is False

    def test_documento_display(self, estudiante_completo):
        assert estudiante_completo.documento_display == "TI 1098765432"

    def test_requiere_atencion_diferencial_con_piar(self):
        est = Estudiante(
            numero_documento="123",
            nombre="Luis",
            apellido="Pérez",
            posee_piar=True,
        )
        assert est.requiere_atencion_diferencial is True


# =============================================================================
# Transiciones de estado
# =============================================================================

class TestTransicionesEstado:

    def test_retirar_estudiante_activo(self, estudiante_base):
        retirado = estudiante_base.retirar()
        assert retirado.estado_matricula == EstadoMatricula.RETIRADO
        # El original no se modifica (inmutabilidad)
        assert estudiante_base.es_activo is True

    def test_retirar_estudiante_ya_retirado_falla(self, estudiante_base):
        retirado = estudiante_base.retirar()
        with pytest.raises(ValueError, match="retirado"):
            retirado.retirar()

    def test_reactivar_estudiante_retirado(self, estudiante_base):
        retirado = estudiante_base.retirar()
        reactivado = retirado.reactivar()
        assert reactivado.es_activo is True

    def test_reactivar_estudiante_activo_falla(self, estudiante_base):
        with pytest.raises(ValueError, match="RETIRADO"):
            estudiante_base.reactivar()

    def test_asignar_grupo(self, estudiante_base):
        con_grupo = estudiante_base.asignar_grupo(5)
        assert con_grupo.grupo_id == 5
        assert estudiante_base.grupo_id is None  # original intacto

    def test_asignar_grupo_invalido_falla(self, estudiante_base):
        with pytest.raises(ValueError, match="positivo"):
            estudiante_base.asignar_grupo(-1)


# =============================================================================
# DTOs
# =============================================================================

class TestNuevoEstudianteDTO:

    def test_dto_valido(self):
        dto = NuevoEstudianteDTO(
            numero_documento="1098765432",
            nombre="Ana",
            apellido="García",
        )
        assert dto.numero_documento == "1098765432"

    def test_to_estudiante(self):
        dto = NuevoEstudianteDTO(
            numero_documento="1098765432",
            nombre="Ana",
            apellido="García",
            fecha_nacimiento=date(2010, 6, 15),
        )
        est = dto.to_estudiante()
        assert isinstance(est, Estudiante)
        assert est.nombre == "Ana"
        assert est.es_activo


class TestActualizarEstudianteDTO:

    def test_aplicar_a_estudiante(self, estudiante_base):
        dto = ActualizarEstudianteDTO(nombre="Luisa", grupo_id=3)
        actualizado = dto.aplicar_a(estudiante_base)
        assert actualizado.nombre   == "Luisa"
        assert actualizado.grupo_id == 3
        assert actualizado.apellido == estudiante_base.apellido  # sin cambios

    def test_dto_vacio_no_cambia_nada(self, estudiante_base):
        dto = ActualizarEstudianteDTO()
        sin_cambios = dto.aplicar_a(estudiante_base)
        assert sin_cambios == estudiante_base

    def test_nombre_vacio_en_dto_falla(self):
        with pytest.raises(ValidationError):
            ActualizarEstudianteDTO(nombre="")


class TestEstudianteResumenDTO:

    def test_desde_estudiante(self, estudiante_completo):
        resumen = EstudianteResumenDTO.desde_estudiante(estudiante_completo)
        assert resumen.nombre_completo == "Ana Sofía García Pérez"
        assert resumen.documento_display == "TI 1098765432"

    def test_desde_estudiante_sin_id_falla(self, estudiante_base):
        # estudiante_base no tiene id
        with pytest.raises(ValueError, match="sin id"):
            EstudianteResumenDTO.desde_estudiante(estudiante_base)


class TestFiltroEstudiantesDTO:

    def test_valores_por_defecto(self):
        filtro = FiltroEstudiantesDTO()
        assert filtro.pagina    == 1
        assert filtro.por_pagina == 50

    def test_busqueda_limpia_espacios(self):
        filtro = FiltroEstudiantesDTO(busqueda="  Ana  ")
        assert filtro.busqueda == "Ana"

    def test_busqueda_solo_espacios_es_none(self):
        filtro = FiltroEstudiantesDTO(busqueda="   ")
        assert filtro.busqueda is None

    def test_pagina_invalida_falla(self):
        with pytest.raises(ValidationError):
            FiltroEstudiantesDTO(pagina=0)

    def test_por_pagina_maxima(self):
        with pytest.raises(ValidationError):
            FiltroEstudiantesDTO(por_pagina=201)