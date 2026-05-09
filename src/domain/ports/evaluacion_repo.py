"""
Port: IEvaluacionRepository
=============================
Contrato de acceso a datos para el módulo de evaluación.

Cubre las cuatro entidades que componen el modelo evaluativo:
  Categoria    — agrupaciones con peso porcentual
  Actividad    — talleres, exámenes, proyectos, quizzes
  Nota         — calificación de un estudiante en una actividad
  PuntosExtra  — ajustes adicionales por comportamiento/participación

Y el read model de resultados:
  ResultadoEstudianteDTO — notas + definitiva + promedio ajustado

Principios de este contrato:
  - Retorna entidades Pydantic, nunca dicts ni DataFrames.
  - Los parámetros usan tipos primitivos o entidades del dominio.
  - No hay imports de SQLite, pandas, ni NiceGUI.
  - Cada método tiene una única responsabilidad.
  - `suma_pesos_otras` anticipa la validación del trigger de BD,
    permitiendo que el servicio la verifique y emita un error
    útil antes de intentar el INSERT.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..models.evaluacion import (
    Actividad,
    Categoria,
    EstadoActividad,
    Nota,
    PuntosExtra,
    ResultadoEstudianteDTO,
    TipoPuntosExtra,
)


class IEvaluacionRepository(ABC):

    # =========================================================================
    # Categorías
    # =========================================================================

    @abstractmethod
    def listar_categorias(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Categoria]:
        """
        Retorna todas las categorías de una asignación en un periodo,
        ordenadas por nombre.
        """
        ...

    @abstractmethod
    def get_categoria(self, cat_id: int) -> Categoria | None:
        """Retorna la categoría con ese id, o None si no existe."""
        ...

    @abstractmethod
    def guardar_categoria(self, categoria: Categoria) -> Categoria:
        """
        Inserta una categoría nueva. Retorna la entidad con id asignado.
        El trigger de BD valida que la suma de pesos no supere 1.0.
        El servicio debe verificar con `suma_pesos_otras` antes de llamar.
        """
        ...

    @abstractmethod
    def actualizar_categoria(self, categoria: Categoria) -> Categoria:
        """
        Actualiza nombre y/o peso de una categoría existente.
        Requiere que categoria.id no sea None.
        """
        ...

    @abstractmethod
    def eliminar_categoria(self, cat_id: int) -> None:
        """
        Elimina una categoría y todas sus actividades y notas en cascada
        (ON DELETE CASCADE en la BD). Operación irreversible.
        """
        ...

    @abstractmethod
    def suma_pesos_otras(
        self,
        asignacion_id: int,
        periodo_id: int,
        excluir_cat_id: int | None = None,
    ) -> float:
        """
        Suma de pesos de las categorías existentes para una asignación+periodo,
        excluyendo opcionalmente la categoría indicada.

        Uso típico antes de crear/actualizar:
          suma = repo.suma_pesos_otras(asig_id, per_id, excluir_cat_id=cat.id)
          if suma + nueva_peso > 1.001:
              raise ValueError("Los pesos superan el 100%")

        Returns:
            Suma de pesos (0.0 si no hay categorías).
        """
        ...

    # =========================================================================
    # Actividades
    # =========================================================================

    @abstractmethod
    def listar_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Actividad]:
        """
        Retorna todas las actividades de una asignación+periodo,
        ordenadas por fecha (nulas al final) y luego por nombre.
        """
        ...

    @abstractmethod
    def listar_actividades_por_categoria(
        self,
        cat_id: int,
    ) -> list[Actividad]:
        """Retorna las actividades de una categoría específica."""
        ...

    @abstractmethod
    def listar_actividades_publicadas(
        self,
        asignacion_id: int,
        periodo_id: int,
        hasta_fecha: date | None = None,
    ) -> list[Actividad]:
        """
        Retorna actividades en estado PUBLICADA o CERRADA.
        Si hasta_fecha está definida, solo incluye actividades
        con fecha <= hasta_fecha (para promedio ajustado).
        """
        ...

    @abstractmethod
    def get_actividad(self, act_id: int) -> Actividad | None:
        """Retorna la actividad con ese id, o None si no existe."""
        ...

    @abstractmethod
    def guardar_actividad(self, actividad: Actividad) -> Actividad:
        """Inserta una actividad nueva. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_actividad(self, actividad: Actividad) -> Actividad:
        """Actualiza los campos de una actividad existente."""
        ...

    @abstractmethod
    def actualizar_estado_actividad(
        self,
        act_id: int,
        estado: EstadoActividad,
    ) -> bool:
        """
        Actualiza solo el estado de una actividad.
        Más eficiente que actualizar_actividad cuando solo cambia el estado.
        Retorna True si la fila fue afectada.
        """
        ...

    @abstractmethod
    def eliminar_actividad(self, act_id: int) -> None:
        """
        Elimina una actividad y todas sus notas en cascada.
        El servicio debe verificar que la actividad no esté cerrada antes.
        """
        ...

    # =========================================================================
    # Notas
    # =========================================================================

    @abstractmethod
    def listar_notas_por_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Nota]:
        """
        Retorna todas las notas de un estudiante en una asignación+periodo.
        Es el conjunto que CalculadorNotas necesita para calcular definitiva.
        """
        ...

    @abstractmethod
    def listar_notas_por_actividad(
        self,
        actividad_id: int,
    ) -> list[Nota]:
        """
        Retorna las notas de todos los estudiantes en una actividad.
        Usado para poblar el ag-grid de la planilla de notas.
        """
        ...

    @abstractmethod
    def get_nota(
        self,
        estudiante_id: int,
        actividad_id: int,
    ) -> Nota | None:
        """Retorna la nota de un estudiante en una actividad, o None."""
        ...

    @abstractmethod
    def guardar_nota(self, nota: Nota) -> Nota:
        """
        Inserta o actualiza la nota de un estudiante en una actividad
        (ON CONFLICT REPLACE en la BD).
        Retorna la entidad con id asignado.
        """
        ...

    @abstractmethod
    def guardar_notas_masivas(self, notas: list[Nota]) -> int:
        """
        Inserta o actualiza múltiples notas en una sola operación.
        Retorna el número de notas procesadas.
        Más eficiente que llamar guardar_nota en bucle.
        """
        ...

    @abstractmethod
    def eliminar_nota(
        self,
        estudiante_id: int,
        actividad_id: int,
    ) -> bool:
        """
        Elimina la nota de un estudiante en una actividad.
        Retorna True si existía y fue eliminada.
        """
        ...

    # =========================================================================
    # Puntos extra
    # =========================================================================

    @abstractmethod
    def get_puntos_extra(
        self,
        estudiante_id: int,
        asignacion_id: int,
        periodo_id: int,
        tipo: TipoPuntosExtra | None = None,
    ) -> PuntosExtra | None:
        """
        Retorna los puntos extra de un estudiante. Si tipo es None,
        retorna el primer registro (generalmente hay uno por tipo).
        """
        ...

    @abstractmethod
    def listar_puntos_extra(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[PuntosExtra]:
        """Retorna todos los puntos extra de una asignación+periodo."""
        ...

    @abstractmethod
    def guardar_puntos_extra(self, pe: PuntosExtra) -> PuntosExtra:
        """
        Inserta o actualiza los puntos extra (ON CONFLICT REPLACE).
        Retorna la entidad con id asignado.
        """
        ...

    # =========================================================================
    # Read models — resultados consolidados
    # =========================================================================

    @abstractmethod
    def listar_resultados_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ResultadoEstudianteDTO]:
        """
        Retorna el resultado de todos los estudiantes del grupo en una
        asignación+periodo: notas por actividad, definitiva y promedio ajustado.

        Es la query principal de la planilla de notas. El repositorio
        ejecuta el JOIN con estudiantes y notas; el servicio aplica
        CalculadorNotas para definitiva y promedio_ajustado.
        """
        ...