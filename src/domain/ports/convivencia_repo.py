"""
Port: IConvivenciaRepository
============================
Contrato de acceso a datos para el módulo de convivencia.

Cubre:
  ObservacionPeriodo     — Texto narrativo (público o privado) en el periodo.
  RegistroComportamiento — Eventos puntuales (fortalezas, dificultades, descargos, etc.).
  NotaComportamiento     — Calificación cuantitativa de convivencia por periodo.

Patrones de uso principales:

  Registrar un evento disciplinario:
    registro = repo.guardar_registro(nuevo_registro)
    
  Actualizar un registro (ej. notificar acudiente o agregar seguimiento):
    repo.actualizar_registro(registro_modificado)

  Guardar o actualizar nota de comportamiento (Upsert):
    repo.guardar_nota(nueva_nota)

  Listar historial de un estudiante:
    registros = repo.listar_registros(FiltroConvivenciaDTO(estudiante_id=est_id))
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.convivencia import (
    FiltroConvivenciaDTO,
    NotaComportamiento,
    ObservacionPeriodo,
    RegistroComportamiento,
)


class IConvivenciaRepository(ABC):

    # =========================================================================
    # Observaciones de Periodo
    # =========================================================================

    @abstractmethod
    def get_observacion(self, observacion_id: int) -> ObservacionPeriodo | None:
        """Retorna una observación por su ID, o None si no existe."""
        ...

    @abstractmethod
    def get_observacion_por_asignacion(
        self, estudiante_id: int, asignacion_id: int, periodo_id: int
    ) -> ObservacionPeriodo | None:
        """
        Retorna la observación de una asignatura específica en un periodo.
        Solo debería haber una observación por asignatura/periodo/estudiante.
        """
        ...

    @abstractmethod
    def listar_observaciones_por_estudiante(
        self, estudiante_id: int, periodo_id: int | None = None, solo_publicas: bool = False
    ) -> list[ObservacionPeriodo]:
        """
        Retorna las observaciones de un estudiante.
        Si se especifica periodo_id, filtra por ese periodo.
        Si solo_publicas es True, omite las observaciones privadas.
        """
        ...

    @abstractmethod
    def guardar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo:
        """
        Guarda una nueva observación.
        Retorna la entidad con su id asignado.
        """
        ...

    @abstractmethod
    def actualizar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo:
        """
        Actualiza una observación existente (texto o visibilidad).
        Requiere que observacion.id no sea None.
        """
        ...

    @abstractmethod
    def eliminar_observacion(self, observacion_id: int) -> bool:
        """
        Elimina (o desactiva lógicamente) una observación.
        Retorna True si fue eliminada.
        """
        ...

    # =========================================================================
    # Registros de Comportamiento
    # =========================================================================

    @abstractmethod
    def get_registro(self, registro_id: int) -> RegistroComportamiento | None:
        """Retorna un registro de comportamiento por su ID, o None si no existe."""
        ...

    @abstractmethod
    def listar_registros(self, filtro: FiltroConvivenciaDTO) -> list[RegistroComportamiento]:
        """
        Retorna una lista paginada de registros que cumplen con los criterios
        del filtro (estudiante, grupo, periodo, tipo, etc.).
        """
        ...

    @abstractmethod
    def contar_registros(self, filtro: FiltroConvivenciaDTO) -> int:
        """
        Retorna la cantidad total de registros que cumplen con el filtro,
        útil para paginación o métricas.
        """
        ...

    @abstractmethod
    def guardar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento:
        """
        Guarda un nuevo registro de comportamiento.
        Retorna la entidad con su id asignado.
        """
        ...

    @abstractmethod
    def actualizar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento:
        """
        Actualiza un registro existente (ej. se agregó seguimiento o se 
        notificó al acudiente). Requiere que registro.id no sea None.
        """
        ...

    @abstractmethod
    def eliminar_registro(self, registro_id: int) -> bool:
        """
        Elimina un registro de comportamiento (físico o lógico).
        Generalmente usado si un docente comete un error al crearlo.
        Retorna True si la fila fue afectada.
        """
        ...

    # =========================================================================
    # Notas de Comportamiento
    # =========================================================================

    @abstractmethod
    def get_nota(self, estudiante_id: int, periodo_id: int) -> NotaComportamiento | None:
        """
        Retorna la nota de comportamiento de un estudiante en un periodo, 
        o None si no ha sido evaluado.
        """
        ...

    @abstractmethod
    def listar_notas_por_estudiante(self, estudiante_id: int) -> list[NotaComportamiento]:
        """
        Retorna todas las notas de comportamiento de un estudiante en los
        diferentes periodos del año activo.
        """
        ...

    @abstractmethod
    def listar_notas_por_grupo(
        self, grupo_id: int, periodo_id: int
    ) -> list[NotaComportamiento]:
        """
        Retorna las notas de comportamiento de todos los estudiantes de un grupo 
        en un periodo específico.
        """
        ...

    @abstractmethod
    def guardar_nota(self, nota: NotaComportamiento) -> NotaComportamiento:
        """
        Guarda o actualiza la nota de comportamiento (Upsert).
        Si ya existe una nota para ese estudiante y periodo, la reemplaza.
        Retorna la entidad guardada con su id.
        """
        ...
