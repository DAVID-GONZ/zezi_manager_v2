"""
Tests unitarios — paso_15b
Modelos: PesosGeneracion, DisponibilidadDocente, ConfigGeneracion,
         NuevaDisponibilidadDTO, NuevaConfigGeneracionDTO.
"""
from __future__ import annotations

import pytest

from src.domain.models.infraestructura import (
    ConfigGeneracion,
    DisponibilidadDocente,
    NuevaConfigGeneracionDTO,
    NuevaDisponibilidadDTO,
    PesosGeneracion,
    TRANSICIONES_CONFIG,
)


# =============================================================================
# PesosGeneracion
# =============================================================================

class TestPesosGeneracion:

    def test_defaults_correctos(self):
        p = PesosGeneracion()
        assert p.huecos == 1.0
        assert p.distribucion == 1.0
        assert p.compactacion == 0.5

    def test_valores_en_rango_validos(self):
        p = PesosGeneracion(huecos=0.0, distribucion=2.0, compactacion=1.0)
        assert p.huecos == 0.0
        assert p.distribucion == 2.0

    def test_valor_inferior_invalido(self):
        with pytest.raises(Exception):
            PesosGeneracion(huecos=-0.1)

    def test_valor_superior_invalido(self):
        with pytest.raises(Exception):
            PesosGeneracion(distribucion=2.01)

    def test_cero_es_valido(self):
        p = PesosGeneracion(compactacion=0.0)
        assert p.compactacion == 0.0

    def test_dos_es_valido(self):
        p = PesosGeneracion(huecos=2.0)
        assert p.huecos == 2.0


# =============================================================================
# DisponibilidadDocente
# =============================================================================

class TestDisponibilidadDocente:

    def test_creacion_correcta(self):
        d = DisponibilidadDocente(usuario_id=1, dia_semana="Lunes", franja_orden=2)
        assert d.disponible is True
        assert d.franja_orden == 2

    def test_dia_invalido(self):
        with pytest.raises(Exception):
            DisponibilidadDocente(usuario_id=1, dia_semana="Domingo", franja_orden=1)

    def test_franja_orden_minimo(self):
        with pytest.raises(Exception):
            DisponibilidadDocente(usuario_id=1, dia_semana="Lunes", franja_orden=0)

    def test_usuario_id_positivo_requerido(self):
        with pytest.raises(Exception):
            DisponibilidadDocente(usuario_id=0, dia_semana="Lunes", franja_orden=1)

    def test_disponible_false(self):
        d = DisponibilidadDocente(
            usuario_id=5, dia_semana="Miércoles", franja_orden=3, disponible=False
        )
        assert d.disponible is False

    def test_todos_los_dias_validos(self):
        for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]:
            d = DisponibilidadDocente(usuario_id=1, dia_semana=dia, franja_orden=1)
            assert d.dia_semana == dia


# =============================================================================
# ConfigGeneracion
# =============================================================================

class TestConfigGeneracion:

    def _config(self, estado="borrador") -> ConfigGeneracion:
        return ConfigGeneracion(
            nombre="Test config",
            periodo_id=1,
            anio_id=1,
            plantilla_id=1,
            estado=estado,
        )

    def test_creacion_defaults(self):
        c = self._config()
        assert c.estado == "borrador"
        assert c.grupos == []
        assert c.pesos.huecos == 1.0

    def test_estado_invalido(self):
        with pytest.raises(Exception):
            ConfigGeneracion(
                nombre="X", periodo_id=1, anio_id=1, plantilla_id=1,
                estado="invalido"
            )

    def test_puede_transicionar_borrador_a_generado(self):
        c = self._config("borrador")
        assert c.puede_transicionar_a("generado") is True

    def test_no_puede_transicionar_borrador_a_aplicado(self):
        c = self._config("borrador")
        assert c.puede_transicionar_a("aplicado") is False

    def test_puede_transicionar_generado_a_aplicado(self):
        c = self._config("generado")
        assert c.puede_transicionar_a("aplicado") is True

    def test_puede_transicionar_generado_a_borrador(self):
        c = self._config("generado")
        assert c.puede_transicionar_a("borrador") is True

    def test_no_puede_transicionar_aplicado_a_nada(self):
        c = self._config("aplicado")
        assert c.puede_transicionar_a("borrador") is False
        assert c.puede_transicionar_a("generado") is False
        assert c.puede_transicionar_a("aplicado") is False

    def test_transiciones_config_dict(self):
        assert "generado" in TRANSICIONES_CONFIG["borrador"]
        assert TRANSICIONES_CONFIG["aplicado"] == set()

    def test_nombre_vacio_invalido(self):
        with pytest.raises(Exception):
            ConfigGeneracion(
                nombre="  ", periodo_id=1, anio_id=1, plantilla_id=1
            )


# =============================================================================
# DTOs
# =============================================================================

class TestDTOs:

    def test_nueva_disponibilidad_to_modelo(self):
        dto = NuevaDisponibilidadDTO(
            usuario_id=3, dia_semana="Viernes", franja_orden=4, disponible=False
        )
        m = dto.to_modelo()
        assert isinstance(m, DisponibilidadDocente)
        assert m.usuario_id == 3
        assert m.disponible is False

    def test_nueva_config_to_config_estado_borrador(self):
        dto = NuevaConfigGeneracionDTO(
            nombre="Mi config",
            periodo_id=2,
            anio_id=1,
            plantilla_id=3,
        )
        c = dto.to_config()
        assert isinstance(c, ConfigGeneracion)
        assert c.estado == "borrador"
        assert c.nombre == "Mi config"

    def test_nueva_config_with_pesos(self):
        pesos = PesosGeneracion(huecos=0.5, distribucion=1.5, compactacion=0.0)
        dto = NuevaConfigGeneracionDTO(
            nombre="Config pesos",
            periodo_id=1,
            anio_id=1,
            plantilla_id=1,
            pesos=pesos,
        )
        c = dto.to_config()
        assert c.pesos.huecos == 0.5
        assert c.pesos.distribucion == 1.5
