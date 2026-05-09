"""
Port: IAsistenciaRepository
=============================
Contrato de acceso a datos para el módulo de asistencia.

Cubre:
  ControlDiario      — registro individual por estudiante, clase y fecha
  ResumenAsistenciaDTO — agregado de presencias/faltas por estudiante y periodo

Dos patrones de uso principales:

  Registro diario (docente toma asistencia):
    controles = dto.to_controles()
    repo.registrar_masivo(controles)

  Seguimiento (coordinador/director consulta):
    resumen = repo.resumen_por_estudiante(est_id, periodo_id)
    if resumen.porcentaje_asistencia < umbral:
        # generar alerta

La distinción entre FALTA_JUSTIFICADA y FALTA_INJUSTIFICADA importa
en el cálculo de porcentaje_asistencia (solo FI y R penalizan).
El repositorio almacena el estado tal como viene; el cálculo vive en
ResumenAsistenciaDTO.porcentaje_asistencia.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..models.asistencia import (
    ControlDiario,
    EstadoAsistencia,
    ResumenAsistenciaDTO,
)


class IAsistenciaRepository(ABC):

    # =========================================================================
    # Escritura
    # =========================================================================

    @abstractmethod
    def registrar(self, control: ControlDiario) -> ControlDiario:
        """
        Inserta o actualiza el registro de asistencia de un estudiante
        en una clase y fecha (ON CONFLICT REPLACE en la BD).
        Retorna la entidad con id asignado.
        """
        ...

    @abstractmethod
    def registrar_masivo(self, controles: list[ControlDiario]) -> int:
        """
        Inserta o actualiza múltiples registros en una sola operación.
        Operación atómica: todos se persisten o ninguno.
        Retorna el número de registros procesados.
        """
        ...

    # =========================================================================
    # Lectura — registro individual
    # =========================================================================

    @abstractmethod
    def get_por_fecha_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int,
        fecha: date,
    ) -> ControlDiario | None:
        """
        Retorna el registro de asistencia de un estudiante en una
        clase específica y fecha, o None si no existe.
        """
        ...

    @abstractmethod
    def listar_por_grupo_y_fecha(
        self,
        grupo_id: int,
        asignacion_id: int,
        fecha: date,
    ) -> list[ControlDiario]:
        """
        Retorna todos los registros de asistencia de un grupo en una
        fecha y asignación. Usado para mostrar el estado de una clase.
        """
        ...

    @abstractmethod
    def listar_por_estudiante_y_periodo(
        self,
        estudiante_id: int,
        periodo_id: int,
    ) -> list[ControlDiario]:
        """
        Retorna todos los registros de asistencia de un estudiante
        durante un periodo. Usado por el historial de asistencia.
        """
        ...

    @abstractmethod
    def listar_por_asignacion_y_rango(
        self,
        asignacion_id: int,
        fecha_desde: date,
        fecha_hasta: date,
    ) -> list[ControlDiario]:
        """
        Retorna los registros de una asignación en un rango de fechas.
        Usado para generar informes de asistencia.
        """
        ...

    # =========================================================================
    # Lectura — resúmenes y estadísticas
    # =========================================================================

    @abstractmethod
    def resumen_por_estudiante(
        self,
        estudiante_id: int,
        periodo_id: int,
        asignacion_id: int | None = None,
    ) -> ResumenAsistenciaDTO:
        """
        Calcula el resumen de asistencia de un estudiante en un periodo,
        opcionalmente filtrado por asignación.

        El repositorio ejecuta la query GROUP BY; el modelo
        ResumenAsistenciaDTO calcula porcentaje_asistencia.

        Returns:
            ResumenAsistenciaDTO con conteos por estado.
            Si no hay registros, retorna el DTO con todos los conteos en 0.
        """
        ...

    @abstractmethod
    def resumen_por_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ResumenAsistenciaDTO]:
        """
        Calcula el resumen de asistencia de todos los estudiantes de un grupo
        en una asignación y periodo. Uno por estudiante.
        Usado en el informe consolidado de asistencia.
        """
        ...

    @abstractmethod
    def contar_faltas_injustificadas(
        self,
        estudiante_id: int,
        periodo_id: int,
    ) -> int:
        """
        Cuenta las faltas injustificadas de un estudiante en el periodo.
        Usado por AlertaService para generar alertas por inasistencia.
        """
        ...

    @abstractmethod
    def fechas_con_registro(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[date]:
        """
        Retorna las fechas que ya tienen registro de asistencia para
        una asignación+periodo. Permite saber qué días faltan por registrar.
        Ordenado cronológicamente.
        """
        ...

    @abstractmethod
    def porcentaje_asistencia_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float:
        """
        Porcentaje de asistencia promedio del grupo (0.0 a 100.0).
        Usado en el dashboard del docente como métrica rápida.
        """
        ...

    @abstractmethod
    def estudiantes_en_riesgo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
        umbral_pct: float = 80.0,
    ) -> list[int]:
        """
        Retorna los IDs de los estudiantes cuyo porcentaje de asistencia
        está por debajo de umbral_pct. Usado por AlertaService.
        """
        ...