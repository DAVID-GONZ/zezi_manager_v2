"""
Port: IInfraestructuraRepository
==================================
Contrato de acceso a datos para las entidades estructurales del sistema.

Cubre las cinco entidades que conforman la infraestructura académica:
  AreaConocimiento — áreas del currículo (Ley 115, Art. 23)
  Asignatura       — materias dictadas en la institución
  Grupo            — cursos con grado, jornada y capacidad
  Horario          — bloques horarios por grupo/asignatura/docente/periodo
  Logro            — enunciados de aprendizaje esperado (aparecen en boletines)

Y los read models:
  HorarioInfo            — horario enriquecido con nombres (para grids de UI)
  HorarioEstadisticasDTO — métricas del horario maestro

Principios:
  - Las entidades de infraestructura son relativamente estables durante el año.
  - Horario es la excepción: puede ajustarse durante el año lectivo.
  - Logro está ligado a una asignación y periodo — cambia con cada periodo.
  - No hay soft-delete en infraestructura: las eliminaciones son reales,
    con restricciones de FK en la BD que protegen los datos dependientes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    Grupo,
    Horario,
    HorarioEstadisticasDTO,
    HorarioInfo,
    Logro,
)


class IInfraestructuraRepository(ABC):

    # =========================================================================
    # Áreas de conocimiento
    # =========================================================================

    @abstractmethod
    def get_area(self, area_id: int) -> AreaConocimiento | None:
        """Retorna el área con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_areas(self) -> list[AreaConocimiento]:
        """Retorna todas las áreas de conocimiento, ordenadas por nombre."""
        ...

    @abstractmethod
    def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        """
        Inserta un área nueva. Retorna la entidad con id asignado.
        El servicio debe verificar que el nombre no exista antes.
        """
        ...

    @abstractmethod
    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        """Actualiza nombre y/o código de un área existente."""
        ...

    @abstractmethod
    def eliminar_area(self, area_id: int) -> bool:
        """
        Elimina un área. Retorna True si la fila fue afectada.
        La BD rechaza la operación si hay asignaturas vinculadas (FK).
        """
        ...

    # =========================================================================
    # Asignaturas
    # =========================================================================

    @abstractmethod
    def get_asignatura(self, asignatura_id: int) -> Asignatura | None:
        """Retorna la asignatura con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_asignaturas(
        self,
        area_id: int | None = None,
    ) -> list[Asignatura]:
        """
        Retorna asignaturas, opcionalmente filtradas por área.
        Ordenadas por nombre.
        """
        ...

    @abstractmethod
    def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        """Inserta una asignatura nueva. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        """Actualiza los campos de una asignatura existente."""
        ...

    @abstractmethod
    def eliminar_asignatura(self, asignatura_id: int) -> bool:
        """
        Elimina una asignatura. Retorna True si la fila fue afectada.
        La BD rechaza si hay asignaciones o horarios vinculados (FK).
        """
        ...

    # =========================================================================
    # Grupos
    # =========================================================================

    @abstractmethod
    def get_grupo(self, grupo_id: int) -> Grupo | None:
        """Retorna el grupo con ese id, o None si no existe."""
        ...

    @abstractmethod
    def get_grupo_por_codigo(self, codigo: str) -> Grupo | None:
        """
        Busca un grupo por su código (ej. '601', '1101').
        Útil para importaciones masivas y formularios con código manual.
        """
        ...

    @abstractmethod
    def listar_grupos(self, grado: int | None = None) -> list[Grupo]:
        """
        Retorna grupos, opcionalmente filtrados por grado.
        Ordenados por código.
        """
        ...

    @abstractmethod
    def guardar_grupo(self, grupo: Grupo) -> Grupo:
        """Inserta un grupo nuevo. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        """Actualiza los campos de un grupo existente."""
        ...

    @abstractmethod
    def eliminar_grupo(self, grupo_id: int) -> bool:
        """
        Elimina un grupo. Retorna True si la fila fue afectada.
        La BD rechaza si hay estudiantes o asignaciones vinculadas (FK).
        """
        ...

    # =========================================================================
    # Horarios
    # =========================================================================

    @abstractmethod
    def get_horario(self, horario_id: int) -> Horario | None:
        """Retorna el bloque horario con ese id, o None si no existe."""
        ...

    @abstractmethod
    def get_info_horario(self, horario_id: int) -> HorarioInfo | None:
        """
        Retorna el bloque horario enriquecido con nombres (JOIN).
        Usado en el detalle de un bloque en la UI.
        """
        ...

    @abstractmethod
    def listar_horario_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[HorarioInfo]:
        """
        Retorna todos los bloques horarios de un grupo en un periodo.
        Ordenados por dia_semana y hora_inicio.
        Alimenta el grid de horario del grupo y la página de horario.
        """
        ...

    @abstractmethod
    def listar_horario_docente(
        self,
        usuario_id: int,
        periodo_id: int,
    ) -> list[HorarioInfo]:
        """
        Retorna todos los bloques horarios de un docente en un periodo.
        Ordenados por dia_semana y hora_inicio.
        Alimenta la vista de carga horaria del docente.
        """
        ...

    @abstractmethod
    def existe_conflicto_horario(
        self,
        usuario_id: int,
        periodo_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        excluir_horario_id: int | None = None,
    ) -> bool:
        """
        True si el docente ya tiene un bloque que se solapa con el
        rango hora_inicio–hora_fin en ese dia_semana y periodo.
        Permite que el servicio valide conflictos antes de insertar.
        """
        ...

    @abstractmethod
    def get_estadisticas(self, periodo_id: int) -> HorarioEstadisticasDTO:
        """
        Retorna métricas del horario maestro para el panel de estadísticas:
        total de bloques, grupos cubiertos, materias cargadas, docentes activos.
        """
        ...

    @abstractmethod
    def guardar_horario(self, horario: Horario) -> Horario:
        """Inserta un bloque horario nuevo. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_horario(self, horario: Horario) -> Horario:
        """Actualiza los campos de un bloque horario existente."""
        ...

    @abstractmethod
    def eliminar_horario(self, horario_id: int) -> bool:
        """Elimina un bloque horario. Retorna True si la fila fue afectada."""
        ...

    @abstractmethod
    def eliminar_horarios_por_asignacion(self, asignacion_id: int) -> int:
        """
        Elimina todos los bloques horarios de una asignación.
        Retorna el número de bloques eliminados.
        Usado cuando se desactiva una asignación.
        """
        ...

    # =========================================================================
    # Logros
    # =========================================================================

    @abstractmethod
    def get_logro(self, logro_id: int) -> Logro | None:
        """Retorna el logro con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_logros(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Logro]:
        """
        Retorna los logros de una asignación en un periodo,
        ordenados por campo `orden`, luego por id.
        Los logros son los que aparecen en el boletín.
        """
        ...

    @abstractmethod
    def guardar_logro(self, logro: Logro) -> Logro:
        """Inserta un logro nuevo. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_logro(self, logro: Logro) -> Logro:
        """Actualiza descripción y/o orden de un logro existente."""
        ...

    @abstractmethod
    def eliminar_logro(self, logro_id: int) -> bool:
        """Elimina un logro. Retorna True si la fila fue afectada."""
        ...


__all__ = ["IInfraestructuraRepository"]
