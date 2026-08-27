"""Tests unitarios de PreferenciasInstitucionService."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.models.preferencia_institucion import (
    ActualizarPreferenciaDTO,
    CategoriaPreferencia,
    PreferenciaInstitucion,
    PreferenciasDTO,
    TipoValor,
)
from src.services.preferencias_institucion_service import PreferenciasInstitucionService


def _make_service(prefs: list[PreferenciaInstitucion] | None = None):
    repo = MagicMock()
    repo.get_all.return_value = prefs or []
    repo.get.return_value = None
    return PreferenciasInstitucionService(repo), repo


def test_get_dto_defaults():
    svc, _ = _make_service()
    dto = svc.get_dto(1)
    assert isinstance(dto, PreferenciasDTO)
    assert dto.nota_minima_aprobacion_default == 60.0
    assert dto.modulo_convivencia_activo is True


def test_set_y_get_round_trip():
    svc, repo = _make_service()
    repo.set.return_value = PreferenciaInstitucion(
        id=1, institucion_id=1, categoria=CategoriaPreferencia.ACADEMICAS,
        clave="nota_minima_aprobacion_default", valor="70.0", tipo_valor=TipoValor.FLOAT,
    )
    resultado = svc.set(1, ActualizarPreferenciaDTO(clave="nota_minima_aprobacion_default", valor="70.0"))
    assert resultado.clave == "nota_minima_aprobacion_default"
    repo.set.assert_called_once()


def test_modulo_activo_sin_clave_es_true():
    svc, repo = _make_service()
    repo.get.return_value = None
    assert svc.modulo_activo(1, "convivencia") is True


def test_modulo_inactivo_devuelve_false():
    svc, repo = _make_service()
    pref = PreferenciaInstitucion(
        id=1, institucion_id=1, categoria=CategoriaPreferencia.CONVIVENCIA,
        clave="modulo_convivencia_activo", valor="false", tipo_valor=TipoValor.BOOL,
    )
    repo.get.return_value = pref
    assert svc.modulo_activo(1, "convivencia") is False


def test_clave_desconocida_rechazada():
    svc, _ = _make_service()
    with pytest.raises(ValueError, match="Clave desconocida"):
        svc.set(1, ActualizarPreferenciaDTO(clave="clave_inventada", valor="x"))


def test_modulo_inexistente_es_true():
    svc, _ = _make_service()
    assert svc.modulo_activo(1, "modulo_que_no_existe") is True


def test_get_dto_sobrescribe_defaults_con_bd():
    pref = PreferenciaInstitucion(
        id=1, institucion_id=1, categoria=CategoriaPreferencia.ACADEMICAS,
        clave="numero_periodos_default", valor="3", tipo_valor=TipoValor.INT,
    )
    svc, _ = _make_service(prefs=[pref])
    dto = svc.get_dto(1)
    assert dto.numero_periodos_default == 3


def test_tipo_situacion_obligatorio_es_clave_conocida():
    """tipo_situacion_obligatorio debe ser aceptada por el servicio (convivencia_34)."""
    from unittest.mock import MagicMock
    repo = MagicMock()
    pref_guardada = PreferenciaInstitucion(
        id=10, institucion_id=1, categoria=CategoriaPreferencia.CONVIVENCIA,
        clave="tipo_situacion_obligatorio", valor="true", tipo_valor=TipoValor.BOOL,
    )
    repo.get.return_value = None
    repo.set.return_value = pref_guardada
    svc = PreferenciasInstitucionService(repo)
    resultado = svc.set(1, ActualizarPreferenciaDTO(clave="tipo_situacion_obligatorio", valor="true"))
    assert resultado.clave == "tipo_situacion_obligatorio"


def test_tipo_situacion_obligatorio_default_es_false():
    """PreferenciasDTO tiene tipo_situacion_obligatorio=False por defecto."""
    svc, _ = _make_service()
    dto = svc.get_dto(1)
    assert dto.tipo_situacion_obligatorio is False


def test_tipo_situacion_obligatorio_categoria_es_convivencia():
    """tipo_situacion_obligatorio debe categorizarse como CONVIVENCIA."""
    from src.services.preferencias_institucion_service import _inferir_categoria
    assert _inferir_categoria("tipo_situacion_obligatorio") == CategoriaPreferencia.CONVIVENCIA
