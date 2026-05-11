"""
Port: IAlertaRepository
========================
Contrato de acceso a datos para el módulo de alertas.

Cubre:
  ConfiguracionAlerta — umbrales por tipo de alerta y año lectivo
  Alerta              — alerta generada para un estudiante específico

Patrones de uso principales:

  Generar una alerta automática:
    if not repo.existe_pendiente(estudiante_id, TipoAlerta.FALTAS_INJUSTIFICADAS):
        repo.guardar_alerta(alerta)

  Resolver alertas de un estudiante:
    alertas = repo.listar_alertas(FiltroAlertasDTO(
        estudiante_id=est_id, solo_pendientes=True
    ))
    for a in alertas:
        repo.resolver_alerta(a.id, usuario_id=uid, observacion="Citado y atendido")

  Configurar umbrales al inicio del año:
    repo.guardar_configuracion(ConfiguracionAlerta(
        anio_id=anio_id,
        tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
        umbral=3,
    ))
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models.alerta import (
    Alerta,
    ConfiguracionAlerta,
    FiltroAlertasDTO,
    NivelAlerta,
    TipoAlerta,
)


class IAlertaRepository(ABC):

    # =========================================================================
    # Configuración de alertas
    # =========================================================================

    @abstractmethod
    def get_configuracion(
        self,
        anio_id: int,
        tipo_alerta: TipoAlerta,
    ) -> ConfiguracionAlerta | None:
        """
        Retorna la configuración de un tipo de alerta para un año lectivo.
        None si no existe configuración (se usarán valores por defecto del servicio).
        """
        ...

    @abstractmethod
    def listar_configuraciones(
        self,
        anio_id: int,
        solo_activas: bool = True,
    ) -> list[ConfiguracionAlerta]:
        """
        Retorna todas las configuraciones de alerta de un año lectivo,
        opcionalmente solo las activas. Ordenadas por tipo_alerta.
        """
        ...

    @abstractmethod
    def guardar_configuracion(
        self,
        config: ConfiguracionAlerta,
    ) -> ConfiguracionAlerta:
        """
        Inserta o actualiza la configuración de un tipo de alerta
        (ON CONFLICT REPLACE basado en anio_id + tipo_alerta).
        Retorna la entidad con id asignado.
        """
        ...

    @abstractmethod
    def desactivar_configuracion(
        self,
        anio_id: int,
        tipo_alerta: TipoAlerta,
    ) -> bool:
        """
        Marca la configuración como inactiva (activa=False).
        Retorna True si la fila fue afectada.
        Las alertas ya generadas no se eliminan.
        """
        ...

    # =========================================================================
    # Lectura — alertas
    # =========================================================================

    @abstractmethod
    def get_alerta(self, alerta_id: int) -> Alerta | None:
        """Retorna la alerta con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_alertas(self, filtro: FiltroAlertasDTO) -> list[Alerta]:
        """
        Retorna alertas según los filtros indicados.
        Ordenadas: críticas primero, luego por fecha_generacion descendente.
        """
        ...

    @abstractmethod
    def contar_pendientes(
        self,
        estudiante_id: int | None = None,
        nivel: NivelAlerta | None = None,
    ) -> int:
        """
        Cuenta las alertas pendientes. Si estudiante_id es None,
        cuenta todas las alertas pendientes del sistema.
        Usado para mostrar el badge de notificaciones en el dashboard.
        """
        ...

    @abstractmethod
    def existe_pendiente(
        self,
        estudiante_id: int,
        tipo_alerta: TipoAlerta,
    ) -> bool:
        """
        True si ya existe una alerta pendiente del tipo indicado para ese estudiante.
        Evita duplicar alertas cuando el job de detección se ejecuta varias veces.
        """
        ...

    # =========================================================================
    # Escritura — alertas
    # =========================================================================

    @abstractmethod
    def guardar_alerta(self, alerta: Alerta) -> Alerta:
        """
        Inserta una alerta nueva.
        Retorna la entidad con id asignado.
        El servicio debe verificar con `existe_pendiente` antes de llamar.
        """
        ...

    @abstractmethod
    def guardar_alertas_masivas(self, alertas: list[Alerta]) -> int:
        """
        Inserta múltiples alertas en una sola operación.
        Retorna el número de alertas insertadas.
        Más eficiente que llamar guardar_alerta en bucle para jobs batch.
        """
        ...

    @abstractmethod
    def resolver_alerta(
        self,
        alerta_id: int,
        usuario_id: int,
        observacion: str | None = None,
        fecha: datetime | None = None,
    ) -> bool:
        """
        Marca una alerta como resuelta en la BD.
        Retorna True si la fila fue afectada.
        El servicio debe verificar que la alerta no esté ya resuelta.
        """
        ...

    @abstractmethod
    def resolver_alertas_de_estudiante(
        self,
        estudiante_id: int,
        tipo_alerta: TipoAlerta,
        usuario_id: int,
        observacion: str | None = None,
    ) -> int:
        """
        Resuelve todas las alertas pendientes de un tipo para un estudiante.
        Útil cuando la condición que generó las alertas ya no existe
        (ej. el estudiante recuperó su asistencia).
        Retorna el número de alertas resueltas.
        """
        ...


__all__ = ["IAlertaRepository"]
