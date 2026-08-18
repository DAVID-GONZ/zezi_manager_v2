"""
Tests para ConfiguracionService.sincronizar_snapshot_desde_institucion (mejora_06).
"""
import pytest

from src.domain.models.configuracion import (
    ConfiguracionAnio,
    CriterioPromocion,
    NivelDesempeno,
)
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.services.configuracion_service import ConfiguracionService

# ---------------------------------------------------------------------------
# FakeConfigRepo
# ---------------------------------------------------------------------------

class FakeConfigRepo(IConfiguracionRepository):
    """Repositorio falso mínimo para tests de ConfiguracionService."""

    def __init__(self):
        self._data: dict[int, ConfiguracionAnio] = {}

    def get_activa(self, institucion_id=None) -> ConfiguracionAnio | None:
        for c in self._data.values():
            if c.activo and (institucion_id is None or c.institucion_id == institucion_id):
                return c
        return None

    def get_by_id(self, anio_id: int) -> ConfiguracionAnio | None:
        return self._data.get(anio_id)

    def get_by_anio(self, institucion_id, anio: int) -> ConfiguracionAnio | None:
        for c in self._data.values():
            if c.anio == anio and (institucion_id is None or c.institucion_id == institucion_id):
                return c
        return None

    def listar(self, institucion_id=None) -> list[ConfiguracionAnio]:
        return list(self._data.values())

    def guardar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        new_id = max(self._data.keys(), default=0) + 1
        config = config.model_copy(update={"id": new_id})
        self._data[new_id] = config
        return config

    def actualizar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        self._data[config.id] = config
        return config

    def activar(self, anio_id: int) -> bool:
        if anio_id not in self._data:
            return False
        for c in self._data.values():
            self._data[c.id] = c.model_copy(update={"activo": False})
        self._data[anio_id] = self._data[anio_id].model_copy(update={"activo": True})
        return True

    def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]:
        return []

    def get_nivel(self, nivel_id: int) -> NivelDesempeno | None:
        return None

    def guardar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        return nivel

    def actualizar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        return nivel

    def eliminar_nivel(self, nivel_id: int) -> bool:
        return False

    def reemplazar_niveles(self, anio_id: int, niveles: list[NivelDesempeno]) -> list[NivelDesempeno]:
        return niveles

    def clasificar_nota(self, nota: float, anio_id: int) -> NivelDesempeno | None:
        return None

    def get_criterios(self, anio_id: int) -> CriterioPromocion | None:
        return None

    def guardar_criterios(self, criterios: CriterioPromocion) -> CriterioPromocion:
        return criterios

    def get_numero_periodos(self, anio_id: int) -> int:
        return 4

    def guardar_numero_periodos(self, anio_id: int, numero_periodos: int, pesos_iguales: bool = True) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sincronizar_snapshot_anio_inexistente_lanza():
    """sincronizar_snapshot_desde_institucion con anio_id inexistente → ValueError."""
    repo = FakeConfigRepo()
    svc = ConfiguracionService(repo)
    with pytest.raises(ValueError, match="No existe configuración con id"):
        svc.sincronizar_snapshot_desde_institucion(999)
