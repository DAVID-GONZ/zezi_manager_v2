"""
Port: IConfiguracionRepository
================================
Contrato de acceso a datos para toda la configuración del año lectivo.

Cubre cuatro tablas de configuración íntimamente relacionadas:
  configuracion_anio      → ConfiguracionAnio
  niveles_desempeno       → NivelDesempeno  (SIE, Decreto 1290)
  criterios_promocion     → CriterioPromocion
  configuracion_periodos  → número de periodos y si los pesos son iguales

ConfiguracionAlerta NO está aquí — pertenece a IAlertaRepository
porque su ciclo de vida está ligado a la generación de alertas.

Invariantes que el servicio garantiza (no el repositorio):
  - Solo un ConfiguracionAnio puede tener activo=True.
    `activar` debe desactivar todos los demás en la misma transacción.
  - Los rangos de NivelDesempeno no deben solaparse para un mismo anio_id.
    `clasificar_nota` retorna el primero que aplique; si se solapan,
    el resultado es indeterminado.
  - Debe haber exactamente un CriterioPromocion por año.
    Si no existe, el servicio usa valores por defecto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.configuracion import (
    ConfiguracionAnio,
    CriterioPromocion,
    NivelDesempeno,
)


class IConfiguracionRepository(ABC):

    # =========================================================================
    # ConfiguracionAnio
    # =========================================================================

    @abstractmethod
    def get_activa(self) -> ConfiguracionAnio | None:
        """
        Retorna la configuración del año lectivo activo.
        Retorna None si no hay ningún año marcado como activo.
        Es el método más llamado del sistema: casi todas las operaciones
        necesitan saber el año en curso.
        """
        ...

    @abstractmethod
    def get_by_id(self, anio_id: int) -> ConfiguracionAnio | None:
        """Retorna la configuración con ese id, o None si no existe."""
        ...

    @abstractmethod
    def get_by_anio(self, anio: int) -> ConfiguracionAnio | None:
        """
        Busca la configuración por número de año (ej: 2025).
        Útil al crear un año nuevo para verificar que no exista ya.
        """
        ...

    @abstractmethod
    def listar(self) -> list[ConfiguracionAnio]:
        """
        Retorna todas las configuraciones anuales, ordenadas por año
        descendente (más reciente primero).
        """
        ...

    @abstractmethod
    def guardar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        """
        Inserta una configuración nueva.
        Retorna la entidad con id asignado.
        El servicio verifica que el año no exista antes de llamar.
        """
        ...

    @abstractmethod
    def actualizar(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        """
        Actualiza todos los campos de una configuración existente.
        Requiere que config.id no sea None.
        """
        ...

    @abstractmethod
    def activar(self, anio_id: int) -> bool:
        """
        Marca el año indicado como activo y desactiva todos los demás.
        Operación atómica: los dos UPDATEs van en la misma transacción.
        Retorna True si la fila fue afectada.
        """
        ...

    # =========================================================================
    # NivelDesempeno — SIE
    # =========================================================================

    @abstractmethod
    def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]:
        """
        Retorna los niveles de desempeño de un año, ordenados por `orden`.
        Lista vacía si el año no tiene niveles configurados.
        """
        ...

    @abstractmethod
    def get_nivel(self, nivel_id: int) -> NivelDesempeno | None:
        """Retorna el nivel con ese id, o None si no existe."""
        ...

    @abstractmethod
    def guardar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        """
        Inserta un nivel de desempeño nuevo.
        El servicio verifica que el nombre sea único para el año y que
        los rangos no se solapen antes de llamar.
        """
        ...

    @abstractmethod
    def actualizar_nivel(self, nivel: NivelDesempeno) -> NivelDesempeno:
        """Actualiza un nivel de desempeño existente."""
        ...

    @abstractmethod
    def eliminar_nivel(self, nivel_id: int) -> bool:
        """
        Elimina un nivel de desempeño.
        Retorna True si existía y fue eliminado.
        El servicio verifica que no haya cierres que referencien este
        nivel (desempeno_id en cierres_periodo y cierres_anio) antes de llamar.
        """
        ...

    @abstractmethod
    def reemplazar_niveles(
        self,
        anio_id: int,
        niveles: list[NivelDesempeno],
    ) -> list[NivelDesempeno]:
        """
        Reemplaza todos los niveles de un año por la lista provista.
        Operación atómica: primero elimina todos los existentes,
        luego inserta los nuevos.
        Usado cuando el director reconfigura el SIE completo.
        Retorna los niveles con ids asignados.
        """
        ...

    @abstractmethod
    def clasificar_nota(
        self,
        nota: float,
        anio_id: int,
    ) -> NivelDesempeno | None:
        """
        Retorna el nivel de desempeño que corresponde a una nota.
        Retorna None si la nota no cae en ningún rango definido
        (configuración incompleta) o si no hay niveles para el año.

        El repositorio ejecuta:
          SELECT * FROM niveles_desempeno
          WHERE anio_id = ? AND rango_min <= ? AND rango_max >= ?
          ORDER BY orden LIMIT 1
        """
        ...

    # =========================================================================
    # CriterioPromocion
    # =========================================================================

    @abstractmethod
    def get_criterios(self, anio_id: int) -> CriterioPromocion | None:
        """
        Retorna los criterios de promoción del año.
        Retorna None si el año no tiene criterios configurados.
        El servicio usa valores por defecto en ese caso.
        """
        ...

    @abstractmethod
    def guardar_criterios(
        self,
        criterios: CriterioPromocion,
    ) -> CriterioPromocion:
        """
        Inserta o actualiza los criterios de promoción para el año
        (ON CONFLICT REPLACE — hay uno por año).
        Retorna la entidad con id asignado.
        """
        ...

    # =========================================================================
    # ConfiguracionPeriodos
    # =========================================================================

    @abstractmethod
    def get_numero_periodos(self, anio_id: int) -> int:
        """
        Retorna el número de periodos configurados para el año.
        Default 4 si no hay configuración explícita.
        """
        ...

    @abstractmethod
    def guardar_numero_periodos(
        self,
        anio_id: int,
        numero_periodos: int,
        pesos_iguales: bool = True,
    ) -> None:
        """
        Persiste la configuración de número de periodos para el año.
        Solo el director puede llamar a esta operación, y solo
        antes de crear los periodos.
        """
        ...