"""
Tests unitarios — Identidad institucional fuente única (datos_06).

Cobertura:
  R4  — ConfiguracionService.get_info_institucional lee de Institucion cuando hay institucion_id.
  R5  — get_info_institucional retorna defaults sin lanzar cuando no hay institución.
  R7  — actualizar_info_institucional delega en InstitucionService.
  R8  — actualizar_info_institucional rechaza si el año no tiene institución.
  R9  — validación de 12 dígitos DANE vive en la entidad Institucion.
  R16 — InformeService.get_informacion_institucional delega y lanza sin provider.
  R2/R3 — ConfiguracionAnio no tiene campos de identidad.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.domain.exceptions import DependenciaNoDisponibleError, ReglaDeNegocioError
from src.domain.models.configuracion import (
    ActualizarInfoInstitucionalDTO,
    ConfiguracionAnio,
    InformacionInstitucionalDTO,
)
from src.domain.models.institucion import Institucion
from src.services.configuracion_service import ConfiguracionService
from src.services.informe_service import InformeService


# =============================================================================
# Helpers
# =============================================================================


def _make_config(institucion_id: int | None = None, anio: int = 2025) -> ConfiguracionAnio:
    """ConfiguracionAnio mínima para tests."""
    return ConfiguracionAnio(id=1, anio=anio, institucion_id=institucion_id)


def _make_institucion(**kwargs) -> Institucion:
    """Institucion con valores razonables por defecto."""
    defaults = dict(
        id=1,
        nombre="IE Test",
        nombre_oficial="Institución Educativa Test",
        codigo_dane="123456789012",
        rector="Dr. García",
    )
    defaults.update(kwargs)
    return Institucion(**defaults)


def _make_svc(config: ConfiguracionAnio | None = None) -> ConfiguracionService:
    """ConfiguracionService con repo mockeado que devuelve `config`."""
    repo = MagicMock()
    svc = ConfiguracionService(repo)
    if config is not None:
        repo.get_by_id.return_value = config
    return svc


# =============================================================================
# R2 / R3 — ConfiguracionAnio no tiene campos de identidad
# =============================================================================


class TestConfiguracionAnioSinIdentidad:
    """R2, R3: la entidad del año no almacena ni expone campos de identidad."""

    def test_configuracion_anio_no_tiene_campos_identidad(self):
        config = ConfiguracionAnio(anio=2025)
        for campo in (
            "nombre_institucion",
            "dane_code",
            "rector",
            "direccion",
            "municipio",
            "telefono_institucion",
            "logo_path",
            "logo_url",
            "resolucion_aprobacion",
            "tiene_informacion_institucional",
        ):
            assert not hasattr(config, campo), f"ConfiguracionAnio aún tiene el campo '{campo}'"

    def test_model_dump_no_incluye_identidad(self):
        config = ConfiguracionAnio(anio=2025)
        dump = config.model_dump()
        assert "nombre_institucion" not in dump
        assert "dane_code" not in dump
        assert "rector" not in dump


# =============================================================================
# R5 — get_info_institucional sin institución retorna defaults
# =============================================================================


class TestGetInfoInstitucionalSinInstitucion:

    def test_get_info_institucional_sin_institucion_retorna_defaults(self):
        """R5: cuando no hay institución asociada, retorna defaults y no lanza."""
        config = _make_config(institucion_id=None)
        svc = _make_svc(config)

        with patch("src.services.contexto_tenant.verificar_pertenencia"):
            info = svc.get_info_institucional(1)

        assert isinstance(info, InformacionInstitucionalDTO)
        assert info.nombre_institucion == "Institución Educativa"
        assert info.dane_code is None
        assert info.rector is None
        assert info.anio == 2025


# =============================================================================
# R4 — get_info_institucional con institución lee de Institucion
# =============================================================================


class TestGetInfoInstitucionalConInstitucion:

    def test_get_info_institucional_con_institucion_lee_de_institucion(self):
        """R4: cuando hay institución, el DTO se construye desde la entidad Institucion."""
        config = _make_config(institucion_id=7)
        svc = _make_svc(config)
        inst = _make_institucion(id=7)

        with (
            patch("src.services.contexto_tenant.verificar_pertenencia"),
            patch("container.Container") as mock_container,
        ):
            mock_container.institucion_service.return_value.get.return_value = inst
            info = svc.get_info_institucional(1)

        assert info.nombre_institucion == "Institución Educativa Test"
        assert info.dane_code == "123456789012"
        assert info.rector == "Dr. García"
        assert info.anio == 2025


# =============================================================================
# R8 — actualizar_info_institucional sin institución lanza
# =============================================================================


class TestActualizarInfoInstitucionalSinInstitucion:

    def test_actualizar_info_institucional_sin_institucion_lanza(self):
        """R8: actualizar identidad en un año sin institución lanza ReglaDeNegocioError."""
        config = _make_config(institucion_id=None)
        svc = _make_svc(config)
        dto = ActualizarInfoInstitucionalDTO(rector="Dr. Nuevo")

        with (
            patch("src.services.contexto_tenant.verificar_pertenencia"),
            pytest.raises(ReglaDeNegocioError),
        ):
            svc.actualizar_info_institucional(1, dto)


# =============================================================================
# R7 — actualizar_info_institucional delega en InstitucionService
# =============================================================================


class TestActualizarInfoInstitucionalDelegaEnInstitucion:

    def test_actualizar_info_institucional_delega_en_institucion_service(self):
        """R7: actualizar identidad delega en InstitucionService.actualizar."""
        config = _make_config(institucion_id=3)
        svc = _make_svc(config)
        dto = ActualizarInfoInstitucionalDTO(
            rector="Dr. Actualizado",
            dane_code="999999999999",
        )

        with (
            patch("src.services.contexto_tenant.verificar_pertenencia"),
            patch("container.Container") as mock_container,
        ):
            mock_inst_svc = MagicMock()
            mock_container.institucion_service.return_value = mock_inst_svc
            svc.actualizar_info_institucional(1, dto)

        mock_inst_svc.actualizar.assert_called_once()
        args = mock_inst_svc.actualizar.call_args
        inst_dto = args[0][1]  # segundo argumento posicional
        assert inst_dto.rector == "Dr. Actualizado"
        assert inst_dto.codigo_dane == "999999999999"


# =============================================================================
# R9 — validación DANE vive en la entidad Institucion
# =============================================================================


class TestValidacionDaneEnDominio:

    def test_dane_invalido_lanza_en_dominio(self):
        """R9: el código DANE se valida con exactamente 12 dígitos numéricos en Institucion."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="12 dígitos"):
            Institucion(nombre="IE Test", codigo_dane="ABCDEF")

    def test_dane_11_digitos_lanza(self):
        """R9: 11 dígitos también es inválido."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="12 dígitos"):
            Institucion(nombre="IE Test", codigo_dane="12345678901")

    def test_dane_12_digitos_valido(self):
        """R9: exactamente 12 dígitos numéricos es válido."""
        inst = Institucion(nombre="IE Test", codigo_dane="123456789012")
        assert inst.codigo_dane == "123456789012"


# =============================================================================
# R16 — InformeService.get_informacion_institucional
# =============================================================================


class TestInformeServiceGetInfoInstitucional:

    def test_informe_service_get_informacion_institucional_sin_provider_lanza(self):
        """R16: sin config_svc_provider, lanza DependenciaNoDisponibleError."""
        svc = InformeService(estadisticos_repo=MagicMock(), config_svc_provider=None)
        with pytest.raises(DependenciaNoDisponibleError):
            svc.get_informacion_institucional(1)

    def test_informe_service_get_informacion_institucional_delega(self):
        """R16: con provider, delega en ConfiguracionService.get_info_institucional."""
        expected = InformacionInstitucionalDTO(
            anio=2025,
            nombre_institucion="IE Test",
            dane_code="123456789012",
            rector="Dr. García",
            nota_minima_aprobacion=60,
        )
        mock_config_svc = MagicMock()
        mock_config_svc.get_info_institucional.return_value = expected

        svc = InformeService(
            estadisticos_repo=MagicMock(),
            config_svc_provider=lambda: mock_config_svc,
        )
        result = svc.get_informacion_institucional(5)

        mock_config_svc.get_info_institucional.assert_called_once_with(5)
        assert result is expected
