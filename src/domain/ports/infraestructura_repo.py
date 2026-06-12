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
    ConfigGeneracion,
    DisponibilidadDocente,
    EscenarioHorario,
    Franja,
    Grupo,
    Horario,
    HorarioEstadisticasDTO,
    HorarioInfo,
    Logro,
    PlantillaFranja,
)


class IInfraestructuraRepository(ABC):

    # =========================================================================
    # Escenarios de horario
    # =========================================================================

    @abstractmethod
    def get_escenario(self, escenario_id: int) -> EscenarioHorario | None:
        """Retorna el escenario con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]:
        """Retorna todos los escenarios del año, ordenados por nombre."""
        ...

    @abstractmethod
    def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None:
        """Retorna el escenario activo del año, o None si no hay ninguno."""
        ...

    @abstractmethod
    def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        """Inserta un escenario nuevo. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        """Actualiza nombre, descripcion y/o activo de un escenario existente."""
        ...

    @abstractmethod
    def activar_escenario(self, escenario_id: int) -> None:
        """
        Desactiva todos los escenarios del año y activa el indicado.
        Operación atómica en una transacción.
        """
        ...

    @abstractmethod
    def eliminar_escenario(self, escenario_id: int) -> bool:
        """Elimina un escenario. Retorna True si la fila fue afectada."""
        ...

    @abstractmethod
    def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario:
        """
        Crea un nuevo escenario inactivo con el mismo nombre dado
        y copia todos los bloques horarios del escenario origen.
        """
        ...

    @abstractmethod
    def listar_horario_grupo_escenario(
        self, grupo_id: int, escenario_id: int
    ) -> list[HorarioInfo]:
        """Retorna los bloques horarios de un grupo en un escenario específico."""
        ...

    @abstractmethod
    def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]:
        """Retorna todos los bloques horarios de un escenario."""
        ...

    # =========================================================================
    # Plantillas de franja y franjas (rejilla horaria)
    # =========================================================================

    @abstractmethod
    def crear_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja:
        """Inserta una plantilla de franja nueva. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def get_plantilla_franja(self, plantilla_id: int) -> PlantillaFranja | None:
        """Retorna la plantilla con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_plantillas_franja(self) -> list[PlantillaFranja]:
        """Retorna todas las plantillas de franja, ordenadas por nombre."""
        ...

    @abstractmethod
    def get_plantilla_activa(self, jornada: str) -> PlantillaFranja | None:
        """Retorna la plantilla activa de la jornada indicada, o None."""
        ...

    @abstractmethod
    def actualizar_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja:
        """Actualiza nombre, jornada, dias_activos y/o activa de una plantilla."""
        ...

    @abstractmethod
    def activar_plantilla_franja(self, plantilla_id: int) -> None:
        """
        Desactiva las demás plantillas de la misma jornada y activa la indicada.
        Operación atómica en una transacción.
        """
        ...

    @abstractmethod
    def eliminar_plantilla_franja(self, plantilla_id: int) -> bool:
        """Elimina una plantilla (cascada sobre sus franjas). True si afectó filas."""
        ...

    @abstractmethod
    def crear_franja(self, f: Franja) -> Franja:
        """Inserta una franja nueva. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def listar_franjas(self, plantilla_id: int) -> list[Franja]:
        """Retorna las franjas de una plantilla, ordenadas por orden."""
        ...

    @abstractmethod
    def actualizar_franja(self, f: Franja) -> Franja:
        """Actualiza los campos de una franja existente."""
        ...

    @abstractmethod
    def eliminar_franja(self, franja_id: int) -> bool:
        """Elimina una franja. Retorna True si la fila fue afectada."""
        ...

    @abstractmethod
    def reemplazar_franjas(self, plantilla_id: int, franjas: list[Franja]) -> int:
        """
        Reemplaza atómicamente todo el set de franjas de una plantilla
        (DELETE + INSERT en una transacción). Retorna el número insertadas.
        """
        ...

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

    @abstractmethod
    def actualizar_color_area(self, area_id: int, color: str | None) -> bool:
        """
        Actualiza solo el color (hex) de un área. None borra el color.
        Retorna True si la fila fue afectada.
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
    def existe_cruce(
        self,
        escenario_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        *,
        usuario_id: int | None = None,
        grupo_id: int | None = None,
        sala: str | None = None,
        excluir_horario_id: int | None = None,
    ) -> bool:
        """
        True si existe algún bloque en el escenario indicado que se solapa
        con el rango hora_inicio–hora_fin en ese dia_semana.
        Permite filtrar por docente, grupo o sala (o cualquier combinación).
        """
        ...

    @abstractmethod
    def contar_bloques_asignacion(self, escenario_id: int, asignacion_id: int) -> int:
        """Retorna el número de bloques horarios de una asignación en un escenario."""
        ...

    @abstractmethod
    def contar_bloques_docente(self, escenario_id: int, usuario_id: int) -> int:
        """Retorna el número de bloques horarios de un docente en un escenario."""
        ...

    @abstractmethod
    def crear_bloques_masivo(self, horarios: list) -> int:
        """Inserta múltiples bloques horarios en una sola operación. Retorna el número creados."""
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

    # =========================================================================
    # Disponibilidad docente (paso_15b)
    # =========================================================================

    @abstractmethod
    def upsert_disponibilidad(self, d: DisponibilidadDocente) -> DisponibilidadDocente:
        """Inserta o reemplaza la disponibilidad de un docente en una franja."""
        ...

    @abstractmethod
    def listar_disponibilidad_docente(self, usuario_id: int) -> list[DisponibilidadDocente]:
        """Retorna todas las restricciones de disponibilidad de un docente."""
        ...

    @abstractmethod
    def es_disponible(self, usuario_id: int, dia: str, franja_orden: int) -> bool:
        """
        Retorna True si el docente está disponible en esa franja.
        Si no existe fila → True (por defecto disponible).
        """
        ...

    @abstractmethod
    def limpiar_disponibilidad_docente(self, usuario_id: int) -> int:
        """Borra todas las restricciones de un docente. Retorna filas borradas."""
        ...

    @abstractmethod
    def cargar_disponibilidad_lote(self, usuario_id: int, slots: list[dict]) -> int:
        """
        Carga en bloque la no-disponibilidad de un docente.
        Cada dict tiene 'dia_semana' y 'franja_orden'. Marca disponible=0.
        Retorna cantidad de filas insertadas/reemplazadas.
        """
        ...

    # =========================================================================
    # Config generación (paso_15b)
    # =========================================================================

    @abstractmethod
    def crear_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion:
        """Inserta una config de generación nueva. Retorna con id asignado."""
        ...

    @abstractmethod
    def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None:
        """Retorna la config con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_configs_generacion(
        self, periodo_id: int | None = None
    ) -> list[ConfigGeneracion]:
        """Retorna configs, opcionalmente filtradas por periodo."""
        ...

    @abstractmethod
    def actualizar_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion:
        """Actualiza los campos de una config existente."""
        ...

    @abstractmethod
    def eliminar_config_generacion(self, config_id: int) -> bool:
        """Elimina una config. Retorna True si la fila fue afectada."""
        ...

    @abstractmethod
    def cambiar_estado_config(
        self, config_id: int, nuevo_estado: str
    ) -> ConfigGeneracion:
        """
        Cambia el estado de una config validando la transición.
        Lanza ValueError si la transición no está permitida.
        """
        ...

    @abstractmethod
    def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion:
        """
        Crea una copia de la config con nombre '<nombre> (copia)',
        estado 'borrador' y escenario_destino_id NULL.
        """
        ...


__all__ = ["IInfraestructuraRepository"]
