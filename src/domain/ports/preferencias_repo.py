"""Puerto abstracto para el repositorio de preferencias de institución."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.preferencia_institucion import PreferenciaInstitucion


class IPreferenciasRepository(ABC):

    @abstractmethod
    def get(self, institucion_id: int, clave: str) -> PreferenciaInstitucion | None: ...

    @abstractmethod
    def get_all(self, institucion_id: int) -> list[PreferenciaInstitucion]: ...

    @abstractmethod
    def set(self, pref: PreferenciaInstitucion) -> PreferenciaInstitucion: ...

    @abstractmethod
    def seed_defaults(
        self, institucion_id: int, defaults: list[PreferenciaInstitucion]
    ) -> None: ...


__all__ = ["IPreferenciasRepository"]
