"""
Tests unitarios de dominio — modelos de convivencia (convivencia_09, convivencia_34).

Cubre CategoriaObservacion, NuevaCategoriaDTO, TipoSituacion, NuevoTipoSituacionDTO,
NotaComportamiento.aprobado y RegistroComportamiento.tipo_situacion_id.
"""
from __future__ import annotations

import pytest

from src.domain.models.convivencia import (
    CategoriaObservacion,
    MedidaPedagogica,
    NotaComportamiento,
    NuevaCategoriaDTO,
    NuevaMedidaPedagogicaDTO,
    NuevoTipoSituacionDTO,
    RegistroComportamiento,
    TipoSituacion,
)

# ---------------------------------------------------------------------------
# CategoriaObservacion
# ---------------------------------------------------------------------------

class TestCategoriaObservacion:

    def test_defaults(self):
        """Defaults: activa=True, es_comportamental=False, id=None."""
        c = CategoriaObservacion(nombre="Académico")
        assert c.id is None
        assert c.activa is True
        assert c.es_comportamental is False

    def test_comportamental_true(self):
        """es_comportamental puede ser True."""
        c = CategoriaObservacion(nombre="Convivencia y normas", es_comportamental=True)
        assert c.es_comportamental is True
        assert c.activa is True

    def test_inactiva(self):
        """activa puede ser False (categoría desactivada)."""
        c = CategoriaObservacion(nombre="Antigua", activa=False)
        assert c.activa is False

    def test_con_id(self):
        """El campo id se puede asignar (proveniente de la BD)."""
        c = CategoriaObservacion(id=5, nombre="Responsabilidad")
        assert c.id == 5

    def test_model_dump(self):
        """model_dump() devuelve el dict completo (sin .dict())."""
        c = CategoriaObservacion(id=1, nombre="Test", es_comportamental=True, activa=False)
        d = c.model_dump()
        assert d["id"] == 1
        assert d["nombre"] == "Test"
        assert d["es_comportamental"] is True
        assert d["activa"] is False


# ---------------------------------------------------------------------------
# NuevaCategoriaDTO
# ---------------------------------------------------------------------------

class TestNuevaCategoriaDTO:

    def test_defaults(self):
        """es_comportamental es False por defecto."""
        dto = NuevaCategoriaDTO(nombre="Participación")
        assert dto.nombre == "Participación"
        assert dto.es_comportamental is False

    def test_comportamental_true(self):
        """es_comportamental puede sobreescribirse."""
        dto = NuevaCategoriaDTO(nombre="Comportamiento positivo", es_comportamental=True)
        assert dto.es_comportamental is True

    def test_model_dump(self):
        """model_dump() incluye los dos campos."""
        dto = NuevaCategoriaDTO(nombre="X", es_comportamental=False)
        d = dto.model_dump()
        assert set(d.keys()) == {"nombre", "es_comportamental"}


# ---------------------------------------------------------------------------
# TipoSituacion (convivencia_34)
# ---------------------------------------------------------------------------

class TestTipoSituacion:

    def test_defaults(self):
        t = TipoSituacion(nombre="Tipo I")
        assert t.id is None
        assert t.nivel == 1
        assert t.activa is True
        assert t.descripcion is None
        assert t.protocolo is None
        assert t.institucion_id is None

    def test_nivel_personalizado(self):
        t = TipoSituacion(nombre="Tipo III", nivel=3)
        assert t.nivel == 3

    def test_inactivo(self):
        t = TipoSituacion(nombre="Tipo II", nivel=2, activa=False)
        assert t.activa is False

    def test_model_dump_incluye_todos_los_campos(self):
        t = TipoSituacion(id=1, nombre="Tipo I", nivel=1, descripcion="desc", activa=True, institucion_id=2)
        d = t.model_dump()
        assert d["id"] == 1
        assert d["nombre"] == "Tipo I"
        assert d["nivel"] == 1
        assert d["descripcion"] == "desc"
        assert d["institucion_id"] == 2


# ---------------------------------------------------------------------------
# NuevoTipoSituacionDTO (convivencia_34)
# ---------------------------------------------------------------------------

class TestNuevoTipoSituacionDTO:

    def test_nivel_valido_1(self):
        dto = NuevoTipoSituacionDTO(nombre="Tipo I", nivel=1)
        assert dto.nivel == 1

    def test_nivel_valido_3(self):
        dto = NuevoTipoSituacionDTO(nombre="Tipo III", nivel=3)
        assert dto.nivel == 3

    def test_nivel_cero_rechazado(self):
        with pytest.raises(Exception):
            NuevoTipoSituacionDTO(nombre="Inválido", nivel=0)

    def test_nivel_cuatro_rechazado(self):
        with pytest.raises(Exception):
            NuevoTipoSituacionDTO(nombre="Inválido", nivel=4)

    def test_nivel_default_es_uno(self):
        dto = NuevoTipoSituacionDTO(nombre="Sin nivel explícito")
        assert dto.nivel == 1


# ---------------------------------------------------------------------------
# NotaComportamiento.aprobado (fix R11 — convivencia_34)
# ---------------------------------------------------------------------------

class TestNotaComportamientoAprobado:

    def test_aprobado_igual_al_minimo(self):
        nota = NotaComportamiento(estudiante_id=1, grupo_id=1, periodo_id=1, valor=60.0)
        assert nota.aprobado is True

    def test_aprobado_por_encima(self):
        nota = NotaComportamiento(estudiante_id=1, grupo_id=1, periodo_id=1, valor=80.0)
        assert nota.aprobado is True

    def test_reprobado_por_debajo(self):
        nota = NotaComportamiento(estudiante_id=1, grupo_id=1, periodo_id=1, valor=59.9)
        assert nota.aprobado is False

    def test_reprobado_en_cero(self):
        nota = NotaComportamiento(estudiante_id=1, grupo_id=1, periodo_id=1, valor=0.0)
        assert nota.aprobado is False


# ---------------------------------------------------------------------------
# RegistroComportamiento.tipo_situacion_id (convivencia_34)
# ---------------------------------------------------------------------------

class TestRegistroComportamientoTipoSituacion:

    def test_tipo_situacion_id_none_por_defecto(self):
        r = RegistroComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            tipo="dificultad", descripcion="test",
        )
        assert r.tipo_situacion_id is None

    def test_tipo_situacion_id_asignable(self):
        r = RegistroComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            tipo="fortaleza", descripcion="test", tipo_situacion_id=3,
        )
        assert r.tipo_situacion_id == 3


# ---------------------------------------------------------------------------
# MedidaPedagogica (convivencia_36)
# ---------------------------------------------------------------------------

class TestMedidaPedagogica:

    def test_defaults(self):
        m = MedidaPedagogica(nombre="Dialogo pedagogico")
        assert m.id is None
        assert m.nivel_minimo == 1
        assert m.activa is True
        assert m.descripcion is None
        assert m.institucion_id is None

    def test_nivel_minimo_tres(self):
        m = MedidaPedagogica(nombre="No renovacion", nivel_minimo=3)
        assert m.nivel_minimo == 3

    def test_inactiva(self):
        m = MedidaPedagogica(nombre="Antigua", activa=False)
        assert m.activa is False

    def test_model_dump(self):
        m = MedidaPedagogica(id=5, nombre="X", nivel_minimo=2, activa=True, institucion_id=1)
        d = m.model_dump()
        assert d["id"] == 5
        assert d["nivel_minimo"] == 2
        assert d["institucion_id"] == 1


# ---------------------------------------------------------------------------
# NuevaMedidaPedagogicaDTO (convivencia_36)
# ---------------------------------------------------------------------------

class TestNuevaMedidaPedagogicaDTO:

    def test_nivel_valido_1(self):
        dto = NuevaMedidaPedagogicaDTO(nombre="Dialogo", nivel_minimo=1)
        assert dto.nivel_minimo == 1

    def test_nivel_valido_3(self):
        dto = NuevaMedidaPedagogicaDTO(nombre="No renovacion", nivel_minimo=3)
        assert dto.nivel_minimo == 3

    def test_nivel_cero_rechazado(self):
        with pytest.raises(Exception):
            NuevaMedidaPedagogicaDTO(nombre="Inválido", nivel_minimo=0)

    def test_nivel_cuatro_rechazado(self):
        with pytest.raises(Exception):
            NuevaMedidaPedagogicaDTO(nombre="Inválido", nivel_minimo=4)

    def test_nivel_default_es_uno(self):
        dto = NuevaMedidaPedagogicaDTO(nombre="Sin nivel explícito")
        assert dto.nivel_minimo == 1


# ---------------------------------------------------------------------------
# RegistroComportamiento.medida_id (convivencia_36)
# ---------------------------------------------------------------------------

class TestRegistroComportamientoMedidaId:

    def test_medida_id_none_por_defecto(self):
        r = RegistroComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            tipo="dificultad", descripcion="test",
        )
        assert r.medida_id is None

    def test_medida_id_asignable(self):
        r = RegistroComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            tipo="dificultad", descripcion="test", medida_id=2,
        )
        assert r.medida_id == 2

    def test_medida_id_independiente_de_tipo_situacion(self):
        r = RegistroComportamiento(
            estudiante_id=1, grupo_id=1, periodo_id=1,
            tipo="citacion_acudiente", descripcion="test",
            tipo_situacion_id=1, medida_id=3,
        )
        assert r.tipo_situacion_id == 1
        assert r.medida_id == 3
