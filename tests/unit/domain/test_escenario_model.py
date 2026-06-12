"""
Tests unitarios — EscenarioHorario y NuevoEscenarioDTO
=======================================================

Ejecutar:
    pytest tests/unit/domain/test_escenario_model.py -v
"""

import pytest
from pydantic import ValidationError

from src.domain.models.infraestructura import (
    EscenarioHorario,
    NuevoEscenarioDTO,
    Horario,
    NuevoHorarioDTO,
    DiaSemana,
)
from src.domain.models.usuario import Usuario, Rol
from datetime import time


# =============================================================================
# EscenarioHorario
# =============================================================================

class TestEscenarioHorario:

    def test_escenario_valido(self):
        esc = EscenarioHorario(anio_id=1, nombre="Horario base")
        assert esc.nombre == "Horario base"
        assert esc.activo is False
        assert esc.id is None
        assert esc.descripcion is None

    def test_escenario_activo(self):
        esc = EscenarioHorario(anio_id=1, nombre="Horario base", activo=True)
        assert esc.activo is True

    def test_anio_id_cero_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            EscenarioHorario(anio_id=0, nombre="Test")

    def test_anio_id_negativo_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            EscenarioHorario(anio_id=-1, nombre="Test")

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            EscenarioHorario(anio_id=1, nombre="   ")

    def test_nombre_se_normaliza_strip(self):
        esc = EscenarioHorario(anio_id=1, nombre="  Horario base  ")
        assert esc.nombre == "Horario base"

    def test_descripcion_opcional(self):
        esc = EscenarioHorario(anio_id=1, nombre="Horario base", descripcion="Horario normal")
        assert esc.descripcion == "Horario normal"

    def test_created_at_optional(self):
        esc = EscenarioHorario(anio_id=1, nombre="Horario base", created_at="2025-01-01 00:00:00")
        assert esc.created_at == "2025-01-01 00:00:00"

    def test_model_dump_usa_model_dump(self):
        esc = EscenarioHorario(anio_id=1, nombre="Horario base", activo=True)
        data = esc.model_dump()
        assert "anio_id" in data
        assert "nombre" in data
        assert "activo" in data
        assert data["activo"] is True


# =============================================================================
# NuevoEscenarioDTO
# =============================================================================

class TestNuevoEscenarioDTO:

    def test_dto_valido(self):
        dto = NuevoEscenarioDTO(anio_id=1, nombre="Horario base")
        assert dto.anio_id == 1
        assert dto.nombre == "Horario base"
        assert dto.descripcion is None

    def test_dto_con_descripcion(self):
        dto = NuevoEscenarioDTO(
            anio_id=1,
            nombre="Plan alterno",
            descripcion="Escenario para semanas especiales",
        )
        assert dto.descripcion == "Escenario para semanas especiales"

    def test_anio_id_cero_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            NuevoEscenarioDTO(anio_id=0, nombre="Test")

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            NuevoEscenarioDTO(anio_id=1, nombre="")

    def test_to_escenario_retorna_instancia(self):
        dto = NuevoEscenarioDTO(anio_id=2, nombre="Plan alterno", descripcion="Desc")
        esc = dto.to_escenario()
        assert isinstance(esc, EscenarioHorario)
        assert esc.anio_id == 2
        assert esc.nombre == "Plan alterno"
        assert esc.descripcion == "Desc"
        assert esc.activo is False
        assert esc.id is None

    def test_to_escenario_model_dump_consistente(self):
        dto = NuevoEscenarioDTO(anio_id=1, nombre="Horario base")
        esc = dto.to_escenario()
        data = esc.model_dump()
        assert data["anio_id"] == 1
        assert data["nombre"] == "Horario base"


# =============================================================================
# Horario con escenario_id
# =============================================================================

class TestHorarioConEscenario:

    def test_horario_valido_con_escenario(self):
        h = Horario(
            grupo_id=1,
            asignatura_id=2,
            usuario_id=3,
            escenario_id=1,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(7, 0),
            hora_fin=time(7, 55),
        )
        assert h.escenario_id == 1
        assert h.periodo_id is None

    def test_escenario_id_cero_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Horario(
                grupo_id=1,
                asignatura_id=2,
                usuario_id=3,
                escenario_id=0,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(7, 0),
                hora_fin=time(7, 55),
            )

    def test_periodo_id_nullable(self):
        h = Horario(
            grupo_id=1,
            asignatura_id=2,
            usuario_id=3,
            escenario_id=5,
            dia_semana=DiaSemana.MARTES,
            hora_inicio=time(8, 0),
            hora_fin=time(8, 55),
            periodo_id=None,
        )
        assert h.periodo_id is None

    def test_nuevo_horario_dto_con_escenario(self):
        dto = NuevoHorarioDTO(
            grupo_id=1,
            asignatura_id=2,
            usuario_id=3,
            escenario_id=1,
            dia_semana=DiaSemana.MIERCOLES,
            hora_inicio="07:00",
            hora_fin="07:55",
        )
        h = dto.to_horario()
        assert isinstance(h, Horario)
        assert h.escenario_id == 1
        assert h.periodo_id is None


# =============================================================================
# Usuario con carga_horaria_max
# =============================================================================

class TestUsuarioConCargaHorariaMax:

    def test_usuario_con_carga_horaria_max(self):
        u = Usuario(
            usuario="prof001",
            nombre_completo="Juan Pérez",
            rol=Rol.PROFESOR,
            carga_horaria_max=22,
        )
        assert u.carga_horaria_max == 22

    def test_carga_horaria_max_none_por_defecto(self):
        u = Usuario(
            usuario="prof002",
            nombre_completo="Ana García",
            rol=Rol.PROFESOR,
        )
        assert u.carga_horaria_max is None

    def test_carga_horaria_max_negativa_falla(self):
        with pytest.raises(ValidationError, match="negativo"):
            Usuario(
                usuario="prof003",
                nombre_completo="Luis Torres",
                carga_horaria_max=-1,
            )

    def test_carga_horaria_max_cero_permitido(self):
        u = Usuario(
            usuario="prof004",
            nombre_completo="María López",
            carga_horaria_max=0,
        )
        assert u.carga_horaria_max == 0
