"""
EstadisticosService
====================
Orquesta los casos de uso del módulo de Estadísticas y Métricas.

Este servicio es principalmente de solo lectura: delega al repositorio
de estadísticos que ejecuta las queries de agregación.
"""
from __future__ import annotations

from typing import Any

from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.models.configuracion import NivelDesempeno
from src.domain.models.dtos import DashboardMetricsDTO


class EstadisticosService:
    """
    Orquesta los casos de uso del módulo de Estadísticas.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IEstadisticosRepository,
        config_repo: IConfiguracionRepository | None = None,
    ) -> None:
        self._repo        = repo
        self._config_repo = config_repo

    # ------------------------------------------------------------------
    # Métricas de dashboard
    # ------------------------------------------------------------------

    def metricas_dashboard(
        self,
        grupo_id: int,
        periodo_id: int,
        anio_id: int | None = None,
    ) -> DashboardMetricsDTO:
        """
        Calcula las métricas del panel principal para un grupo y periodo.

        Obtiene la nota mínima de aprobación de la configuración del año
        si está disponible; usa 60.0 por defecto.
        """
        nota_minima = 60.0
        if self._config_repo is not None and anio_id is not None:
            config = self._config_repo.get_by_id(anio_id)
            if config is not None:
                nota_minima = config.nota_minima_aprobacion

        return self._repo.calcular_metricas_dashboard(
            grupo_id, periodo_id, nota_minima
        )

    def promedio_general_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
    ) -> float:
        """Promedio de notas definitivas de todos los estudiantes del grupo."""
        return self._repo.promedio_general_grupo(
            grupo_id, periodo_id, nota_minima
        )

    def porcentaje_asistencia_global(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> float:
        """Porcentaje de asistencia promedio del grupo en todas sus asignaturas."""
        return self._repo.porcentaje_asistencia_global(grupo_id, periodo_id)

    def contar_alertas_pendientes(self, grupo_id: int) -> int:
        """Número de alertas no resueltas de los estudiantes del grupo."""
        return self._repo.contar_alertas_pendientes(grupo_id)

    # ------------------------------------------------------------------
    # Estadísticas de notas
    # ------------------------------------------------------------------

    def promedio_por_asignacion(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float:
        """Promedio de la nota definitiva de todos los estudiantes en una asignación."""
        return self._repo.promedio_por_asignacion(
            grupo_id, asignacion_id, periodo_id
        )

    def distribucion_desempenos(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
        anio_id: int | None = None,
    ) -> dict[str, int]:
        """
        Cuenta cuántos estudiantes cayeron en cada nivel de desempeño.

        Obtiene los niveles de desempeño de la configuración del año;
        si no hay configuración, retorna un dict vacío.
        """
        niveles: list[NivelDesempeno] = []
        if self._config_repo is not None and anio_id is not None:
            niveles = self._config_repo.listar_niveles(anio_id)

        return self._repo.distribucion_desempenos(
            grupo_id, asignacion_id, periodo_id, niveles
        )

    def comparativo_periodos(
        self,
        grupo_id: int,
        asignacion_id: int,
        anio_id: int,
    ) -> list[dict[str, Any]]:
        """
        Promedio del grupo por periodo, para ver la evolución temporal.

        Returns:
            list de dicts con {"periodo_nombre", "periodo_numero",
            "promedio", "periodo_id"} ordenado por periodo_numero.
        """
        return self._repo.comparativo_periodos(
            grupo_id, asignacion_id, anio_id
        )

    def promedios_por_area(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Promedio del grupo por área de conocimiento en el periodo."""
        return self._repo.promedios_por_area(grupo_id, periodo_id)

    def estudiantes_en_riesgo_academico(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
        min_asignaturas: int = 1,
    ) -> list[int]:
        """IDs de estudiantes con al menos N asignaturas bajo nota mínima."""
        return self._repo.estudiantes_en_riesgo_academico(
            grupo_id, periodo_id, nota_minima, min_asignaturas
        )

    def ranking_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Estudiantes del grupo ordenados por promedio descendente."""
        return self._repo.ranking_grupo(grupo_id, periodo_id)

    # ------------------------------------------------------------------
    # Estadísticas de asistencia
    # ------------------------------------------------------------------

    def tendencia_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Porcentaje de asistencia del grupo por semana/quincena."""
        return self._repo.tendencia_asistencia(
            grupo_id, asignacion_id, periodo_id
        )

    def distribucion_estados_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> dict[str, int]:
        """Conteo total de registros por estado de asistencia en el periodo."""
        return self._repo.distribucion_estados_asistencia(
            grupo_id, asignacion_id, periodo_id
        )

    # ------------------------------------------------------------------
    # Consolidados para exportación
    # ------------------------------------------------------------------

    def consolidado_notas_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Tabla completa de notas definitivas por asignatura para el grupo."""
        return self._repo.consolidado_notas_grupo(grupo_id, periodo_id)

    def consolidado_asistencia_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Tabla completa de asistencia por asignatura para el grupo."""
        return self._repo.consolidado_asistencia_grupo(grupo_id, periodo_id)

    def consolidado_anual_grupo(
        self,
        grupo_id: int,
        anio_id: int,
    ) -> list[dict[str, Any]]:
        """Consolidado anual: notas + estado de promoción por estudiante."""
        return self._repo.consolidado_anual_grupo(grupo_id, anio_id)


__all__ = ["EstadisticosService"]
