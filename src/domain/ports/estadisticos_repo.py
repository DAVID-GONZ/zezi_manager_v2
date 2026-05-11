"""
Port: IEstadisticosRepository
================================
Contrato de acceso a datos para estadísticas, consolidados y métricas.

Este es el único repositorio que es estrictamente de solo lectura:
no tiene métodos INSERT, UPDATE ni DELETE. Todas sus operaciones
son queries de agregación (GROUP BY, COUNT, AVG, SUM) sobre las
tablas que otros repositorios mantienen.

Tres grupos de métodos:

  Métricas de dashboard
    Valores rápidos para el panel principal del docente y el director.
    Deben ser eficientes: se llaman en cada recarga de página.

  Estadísticas de notas
    Promedios, distribuciones de desempeño, comparativos entre periodos.
    Usadas en los informes y en la vista de seguimiento.

  Consolidados para exportación
    Tablas completas de notas y asistencia por grupo. Son las más
    pesadas y se llaman solo cuando el usuario exporta a Excel/PDF.
    Retornan list[dict] porque el exportador necesita flexibilidad
    en los campos y no justifica un DTO específico.

Por qué un repositorio separado:
  Las queries estadísticas hacen JOIN entre asistencias, notas,
  estudiantes y periodos. Si vivieran en IEvaluacionRepository o
  IAsistenciaRepository, esos contratos se volverían demasiado anchos.
  Separar en IEstadisticosRepository permite que el SqliteEstadisticosRepository
  optimice estas queries independientemente (vistas, índices compuestos,
  caching) sin afectar los repositorios transaccionales.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models.configuracion import NivelDesempeno
from ..models.dtos import DashboardMetricsDTO


class IEstadisticosRepository(ABC):

    # =========================================================================
    # Métricas de dashboard
    # =========================================================================

    @abstractmethod
    def calcular_metricas_dashboard(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
    ) -> DashboardMetricsDTO:
        """
        Calcula todas las métricas del panel principal en una sola operación.

        Incluye: total_estudiantes, promedio_general, porcentaje_asistencia,
        estudiantes_en_riesgo, actividades_publicadas, alertas_pendientes.

        El repositorio ejecuta las queries de agregación necesarias;
        el servicio no aplica ningún cálculo adicional sobre el resultado.
        """
        ...

    @abstractmethod
    def promedio_general_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
    ) -> float:
        """
        Promedio de notas definitivas de todos los estudiantes del grupo
        en todas las asignaturas del periodo. Retorna 0.0 si no hay datos.
        """
        ...

    @abstractmethod
    def porcentaje_asistencia_global(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> float:
        """
        Porcentaje de asistencia promedio del grupo en todas sus asignaturas.
        Solo FI y R penalizan (mismo criterio que ResumenAsistenciaDTO).
        Retorna 0.0 si no hay registros.
        """
        ...

    @abstractmethod
    def contar_alertas_pendientes(
        self,
        grupo_id: int,
    ) -> int:
        """Número de alertas no resueltas de los estudiantes del grupo."""
        ...

    # =========================================================================
    # Estadísticas de notas
    # =========================================================================

    @abstractmethod
    def promedio_por_asignacion(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float:
        """
        Promedio de la nota definitiva de todos los estudiantes en una
        asignación+periodo. Retorna 0.0 si no hay cierres registrados.
        """
        ...

    @abstractmethod
    def distribucion_desempenos(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
        niveles: list[NivelDesempeno],
    ) -> dict[str, int]:
        """
        Cuenta cuántos estudiantes cayeron en cada nivel de desempeño.

        Returns:
            dict {nombre_nivel: cantidad_estudiantes}
            Ej: {"Bajo": 3, "Básico": 8, "Alto": 12, "Superior": 5}
            Los niveles sin estudiantes se incluyen con valor 0.
        """
        ...

    @abstractmethod
    def comparativo_periodos(
        self,
        grupo_id: int,
        asignacion_id: int,
        anio_id: int,
    ) -> list[dict[str, Any]]:
        """
        Promedio del grupo por periodo, para mostrar la evolución.

        Returns:
            list de dicts con:
              {"periodo_nombre": str, "periodo_numero": int,
               "promedio": float, "periodo_id": int}
            Ordenado por periodo_numero ascendente.
        """
        ...

    @abstractmethod
    def promedios_por_area(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """
        Promedio del grupo por área de conocimiento en el periodo.

        Returns:
            list de dicts con:
              {"area_nombre": str, "promedio": float,
               "total_asignaturas": int}
            Ordenado por promedio descendente.
        """
        ...

    @abstractmethod
    def estudiantes_en_riesgo_academico(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
        min_asignaturas: int = 1,
    ) -> list[int]:
        """
        IDs de estudiantes que tienen al menos `min_asignaturas` asignaturas
        con promedio actual menor a nota_minima.
        Usado por AlertaService para generar alertas de riesgo académico.
        """
        ...

    @abstractmethod
    def ranking_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """
        Estudiantes del grupo ordenados por promedio descendente.

        Returns:
            list de dicts con:
              {"posicion": int, "estudiante_id": int,
               "nombre_completo": str, "promedio": float}
        """
        ...

    # =========================================================================
    # Estadísticas de asistencia
    # =========================================================================

    @abstractmethod
    def tendencia_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """
        Porcentaje de asistencia del grupo por semana o quincena.
        Permite ver si la asistencia está mejorando o empeorando.

        Returns:
            list de dicts con {"semana": int, "porcentaje": float}
            Ordenado cronológicamente.
        """
        ...

    @abstractmethod
    def distribucion_estados_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> dict[str, int]:
        """
        Conteo total de registros por estado de asistencia en el periodo.

        Returns:
            {"P": int, "FJ": int, "FI": int, "R": int, "E": int}
        """
        ...

    # =========================================================================
    # Consolidados para exportación
    # =========================================================================

    @abstractmethod
    def consolidado_notas_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """
        Tabla completa de notas definitivas por asignatura para todos los
        estudiantes del grupo. Es la fuente del informe consolidado de notas.

        Returns:
            list de dicts donde cada fila es un estudiante con sus notas:
            [
              {
                "estudiante_id": int,
                "nombre_completo": str,
                "documento": str,
                "matematicas": 75.5,      # nombre_asignatura: nota_definitiva
                "lengua_castellana": 82.0,
                ...
                "promedio_periodo": float,
              },
              ...
            ]
            Las claves de asignaturas son los nombres reales de cada una.
        """
        ...

    @abstractmethod
    def consolidado_asistencia_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """
        Tabla completa de asistencia por asignatura para todos los
        estudiantes del grupo.

        Returns:
            list de dicts donde cada fila es un estudiante:
            [
              {
                "estudiante_id": int,
                "nombre_completo": str,
                "nombre_asignatura": str,
                "presentes": int,
                "faltas_injustificadas": int,
                "faltas_justificadas": int,
                "retrasos": int,
                "excusas": int,
                "porcentaje": float,
              },
              ...
            ]
        """
        ...

    @abstractmethod
    def consolidado_anual_grupo(
        self,
        grupo_id: int,
        anio_id: int,
    ) -> list[dict[str, Any]]:
        """
        Consolidado anual: nota definitiva por asignatura + estado de
        promoción para todos los estudiantes del grupo.
        Usado para generar el acta final de calificaciones del año.

        Returns:
            list de dicts con notas por periodo, definitiva anual,
            habilitación si aplica, y estado de promoción.
        """
        ...