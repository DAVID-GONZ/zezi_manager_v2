"""
Port: ISIEERepository
======================
Contrato de acceso a datos para la configuración SIEE
(Sistema Institucional de Evaluación).

Cubre:
  ConfiguracionSIEE   — modo y porcentaje de autonomía docente por año
  Categoria           — categorías institucionales (es_institucional=True)

Principios de este contrato:
  - Retorna entidades Pydantic, nunca dicts.
  - Sin imports de SQLite, pandas ni NiceGUI.
  - Cada método tiene una sola responsabilidad.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.evaluacion import Categoria, ConfiguracionSIEE


class ISIEERepository(ABC):

    # =========================================================================
    # Configuración SIEE
    # =========================================================================

    @abstractmethod
    def get_configuracion(self, anio_id: int) -> ConfiguracionSIEE | None:
        """
        Retorna la configuración SIEE del año, o None si no ha sido configurada.
        En ausencia de configuración el servicio asume modo LIBRE.
        """
        ...

    @abstractmethod
    def guardar_configuracion(self, cfg: ConfiguracionSIEE) -> ConfiguracionSIEE:
        """
        Inserta o reemplaza la configuración SIEE del año.
        Retorna la entidad con id asignado.
        """
        ...

    # =========================================================================
    # Categorías institucionales
    # =========================================================================

    @abstractmethod
    def listar_categorias_institucionales(self, anio_id: int) -> list[Categoria]:
        """
        Retorna las categorías institucionales del año, ordenadas por nombre.
        Estas categorías tienen es_institucional=True y anio_id asignado.
        """
        ...

    @abstractmethod
    def get_categoria_institucional(self, cat_id: int) -> Categoria | None:
        """Retorna la categoría institucional con ese id, o None."""
        ...

    @abstractmethod
    def guardar_categoria_institucional(self, cat: Categoria) -> Categoria:
        """
        Inserta una categoría institucional nueva.
        Retorna la entidad con id asignado.
        """
        ...

    @abstractmethod
    def actualizar_categoria_institucional(self, cat: Categoria) -> Categoria:
        """
        Actualiza nombre, peso y permite_subcategorias de una categoría institucional.
        Requiere que cat.id no sea None.
        """
        ...

    @abstractmethod
    def eliminar_categoria_institucional(self, cat_id: int) -> None:
        """
        Elimina una categoría institucional.
        El servicio debe verificar que no tenga sub-categorías activas antes.
        """
        ...

    @abstractmethod
    def suma_pesos_institucionales(self, anio_id: int) -> float:
        """
        Suma de pesos de todas las categorías institucionales del año.
        Usado para validar que la suma no supere 1.0 antes de crear una nueva.
        """
        ...


__all__ = ["ISIEERepository"]
