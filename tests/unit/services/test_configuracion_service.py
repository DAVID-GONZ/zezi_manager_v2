"""
Tests unitarios para ConfiguracionService.
Usa repositorios falsos en memoria (FakeRepository pattern).
"""
from __future__ import annotations

import pytest

from src.domain.models.configuracion import (
    ConfiguracionAnio,
    CriterioPromocion,
    NivelDesempeno,
    NuevaConfiguracionAnioDTO,
    NuevoNivelDesempenoDTO,
)
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.services.configuracion_service import ConfiguracionService


# ===========================================================================
# Repositorio falso
# ===========================================================================

class FakeConfigRepo(IConfiguracionRepository):
    def __init__(self):
        self._configs: dict[int, ConfiguracionAnio] = {}
        self._niveles: dict[int, list[NivelDesempeno]] = {}
        self._criterios: dict[int, CriterioPromocion] = {}
        self._next_id = 1

    def guardar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        config = config.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._configs[config.id] = config
        return config

    def actualizar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        self._configs[config.id] = config
        return config

    def get_by_id(self, anio_id: int) -> ConfiguracionAnio | None:
        return self._configs.get(anio_id)

    def get_by_anio(self, anio: int) -> ConfiguracionAnio | None:
        for c in self._configs.values():
            if c.anio == anio:
                return c
        return None

    def get_activa(self) -> ConfiguracionAnio | None:
        for c in self._configs.values():
            if c.activo:
                return c
        return None

    def activar(self, anio_id: int) -> None:
        for c in self._configs.values():
            self._configs[c.id] = c.model_copy(update={"activo": c.id == anio_id})

    def guardar_numero_periodos(self, anio_id: int, numero: int, pesos_iguales: bool = True) -> None:
        pass  # No-op en test

    def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]:
        return self._niveles.get(anio_id, [])

    def reemplazar_niveles(self, anio_id: int, niveles: list[NivelDesempeno]) -> list[NivelDesempeno]:
        self._niveles[anio_id] = niveles
        return niveles

    def clasificar_nota(self, nota: float, anio_id: int) -> NivelDesempeno | None:
        for nivel in self._niveles.get(anio_id, []):
            if nivel.rango_min <= nota <= nivel.rango_max:
                return nivel
        return None

    def get_nivel(self, nivel_id: int) -> NivelDesempeno | None:
        for niveles in self._niveles.values():
            for n in niveles:
                if n.id == nivel_id:
                    return n
        return None

    def guardar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        anio_id = nivel.anio_id
        self._niveles.setdefault(anio_id, []).append(nivel)
        return nivel

    def actualizar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        return nivel

    def eliminar_nivel(self, nivel_id: int) -> bool:
        for anio_id, niveles in self._niveles.items():
            for i, n in enumerate(niveles):
                if n.id == nivel_id:
                    self._niveles[anio_id].pop(i)
                    return True
        return False

    def listar(self) -> list[ConfiguracionAnio]:
        return list(self._configs.values())

    def get_numero_periodos(self, anio_id: int) -> int:
        return 4

    def get_criterios(self, anio_id: int) -> CriterioPromocion | None:
        return self._criterios.get(anio_id)

    def guardar_criterios(self, criterios: CriterioPromocion) -> CriterioPromocion:
        self._criterios[criterios.anio_id] = criterios
        return criterios


# ===========================================================================
# Tests
# ===========================================================================

def _make_service() -> tuple[ConfiguracionService, FakeConfigRepo]:
    repo = FakeConfigRepo()
    svc  = ConfiguracionService(repo)
    return svc, repo


class TestCrearAnio:
    def test_crea_anio_nuevo(self):
        svc, repo = _make_service()
        dto = NuevaConfiguracionAnioDTO(anio=2025)
        config = svc.crear_anio(dto)
        assert config.id is not None
        assert config.anio == 2025

    def test_lanza_si_anio_duplicado(self):
        svc, repo = _make_service()
        dto = NuevaConfiguracionAnioDTO(anio=2025)
        svc.crear_anio(dto)
        with pytest.raises(ValueError, match="2025"):
            svc.crear_anio(dto)

    def test_crea_diferentes_anios(self):
        svc, repo = _make_service()
        c1 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2024))
        c2 = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        assert c1.id != c2.id


class TestActivarAnio:
    def test_activa_anio_existente(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        result = svc.activar_anio(config.id)
        assert result is not None

    def test_lanza_si_anio_no_existe(self):
        svc, _ = _make_service()
        with pytest.raises(ValueError, match="999"):
            svc.activar_anio(999)


class TestGetActiva:
    def test_lanza_si_no_hay_activo(self):
        svc, repo = _make_service()
        with pytest.raises(ValueError, match="activo"):
            svc.get_activa()

    def test_retorna_config_activa(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        # config creada con activo=True
        activa = svc.get_activa()
        assert activa.anio == 2025


class TestConfigurarNiveles:
    def test_niveles_sin_solapamiento(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        niveles = [
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="Bajo",   rango_min=0,  rango_max=59),
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="Basico", rango_min=60, rango_max=79),
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="Alto",   rango_min=80, rango_max=100),
        ]
        resultado = svc.configurar_niveles(config.id, niveles)
        assert len(resultado) == 3

    def test_lanza_si_rangos_solapados(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        niveles = [
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="A", rango_min=0,  rango_max=60),
            NuevoNivelDesempenoDTO(anio_id=config.id, nombre="B", rango_min=55, rango_max=100),
        ]
        with pytest.raises(ValueError, match="solapan"):
            svc.configurar_niveles(config.id, niveles)

    def test_lanza_si_lista_vacia(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        with pytest.raises(ValueError, match="menos un nivel"):
            svc.configurar_niveles(config.id, [])


class TestGetCriterios:
    def test_retorna_none_si_no_existen(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        assert svc.get_criterios(config.id) is None

    def test_guarda_y_recupera_criterios(self):
        svc, repo = _make_service()
        config = svc.crear_anio(NuevaConfiguracionAnioDTO(anio=2025))
        criterios = CriterioPromocion(
            anio_id=config.id,
            max_asignaturas_perdidas=2,
            nota_minima_habilitacion=60.0,
        )
        guardados = svc.guardar_criterios(criterios)
        recuperados = svc.get_criterios(config.id)
        assert recuperados is not None
        assert recuperados.max_asignaturas_perdidas == 2
