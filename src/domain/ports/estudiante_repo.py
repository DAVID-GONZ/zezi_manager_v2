"""
Port: IEstudianteRepository
=============================
Contrato de acceso a datos para el módulo de estudiantes y PIARs.

Cubre:
  Estudiante — entidad principal (datos personales, matrícula, grupo)
  PIAR       — Plan Individual de Apoyos y Ajustes Razonables (Decreto 1421)

El PIAR está en este repositorio porque es un sub-documento del estudiante:
cada PIAR pertenece a un estudiante y a un año lectivo, y su ciclo de vida
está acoplado al del estudiante.

Patrones de uso principales:

  Matricular un estudiante nuevo:
    if not repo.existe_documento(dto.numero_documento):
        estudiante = repo.guardar(dto.to_estudiante())

  Buscar un estudiante para la planilla:
    resumen = repo.get_resumen(estudiante_id)

  Registrar un PIAR:
    if not repo.existe_piar(estudiante_id, anio_id):
        repo.guardar_piar(piar)

  Listar estudiantes con PIAR activo en un grupo:
    estudiantes = repo.listar_filtrado(FiltroEstudiantesDTO(
        grupo_id=grupo_id, posee_piar=True
    ))
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.estudiante import (
    Estudiante,
    EstudianteResumenDTO,
    FiltroEstudiantesDTO,
)
from ..models.piar import PIAR


class IEstudianteRepository(ABC):

    # =========================================================================
    # Lectura — estudiantes
    # =========================================================================

    @abstractmethod
    def get_by_id(self, estudiante_id: int) -> Estudiante | None:
        """Retorna el estudiante con ese id, o None si no existe."""
        ...

    @abstractmethod
    def get_by_documento(self, numero_documento: str) -> Estudiante | None:
        """
        Busca un estudiante por número de documento.
        Útil para evitar duplicados en el proceso de matrícula.
        Retorna None si no existe.
        """
        ...

    @abstractmethod
    def existe_documento(self, numero_documento: str) -> bool:
        """
        True si ya existe un estudiante con ese número de documento.
        Más eficiente que get_by_documento cuando solo se necesita
        saber si existe (evita construir el objeto completo).
        """
        ...

    @abstractmethod
    def get_resumen(self, estudiante_id: int) -> EstudianteResumenDTO | None:
        """
        Retorna la vista reducida del estudiante para selects y referencias.
        None si el estudiante no existe.
        """
        ...

    @abstractmethod
    def listar_filtrado(
        self,
        filtro: FiltroEstudiantesDTO,
    ) -> list[Estudiante]:
        """
        Retorna estudiantes según los filtros indicados.
        Ordenados por apellido, luego nombre.
        Soporta paginación mediante filtro.pagina y filtro.por_pagina.
        """
        ...

    @abstractmethod
    def listar_resumenes(
        self,
        filtro: FiltroEstudiantesDTO,
    ) -> list[EstudianteResumenDTO]:
        """
        Versión optimizada de listar_filtrado que retorna solo los campos
        necesarios para selects y lookups. Evita transferir datos no usados.
        """
        ...

    @abstractmethod
    def listar_por_grupo(
        self,
        grupo_id: int,
        solo_activos: bool = True,
    ) -> list[Estudiante]:
        """
        Retorna todos los estudiantes de un grupo, ordenados por apellido.
        Usado para generar planillas de notas y asistencia.
        """
        ...

    @abstractmethod
    def contar_por_grupo(self, grupo_id: int, solo_activos: bool = True) -> int:
        """
        Cuenta los estudiantes de un grupo.
        Usado por Grupo.esta_lleno() y Grupo.cupos_disponibles().
        """
        ...

    # =========================================================================
    # Escritura — estudiantes
    # =========================================================================

    @abstractmethod
    def guardar(self, estudiante: Estudiante) -> Estudiante:
        """
        Inserta un estudiante nuevo.
        Retorna la entidad con id y id_publico asignados.
        El servicio debe verificar unicidad de documento con `existe_documento`.
        """
        ...

    @abstractmethod
    def actualizar(self, estudiante: Estudiante) -> Estudiante:
        """
        Actualiza los datos de un estudiante existente.
        Requiere que estudiante.id no sea None.
        El numero_documento no se actualiza — es el identificador principal.
        """
        ...

    @abstractmethod
    def actualizar_estado_matricula(
        self,
        estudiante_id: int,
        estado: str,
    ) -> bool:
        """
        Actualiza solo el estado de matrícula de un estudiante.
        Más eficiente que actualizar() cuando solo cambia el estado.
        Retorna True si la fila fue afectada.
        """
        ...

    @abstractmethod
    def asignar_grupo(self, estudiante_id: int, grupo_id: int) -> bool:
        """
        Asigna o cambia el grupo de un estudiante.
        Retorna True si la fila fue afectada.
        """
        ...

    # =========================================================================
    # PIAR
    # =========================================================================

    @abstractmethod
    def get_piar(self, estudiante_id: int, anio_id: int) -> PIAR | None:
        """
        Retorna el PIAR del estudiante para el año indicado.
        Cada estudiante tiene máximo un PIAR por año (UNIQUE en BD).
        None si no tiene PIAR ese año.
        """
        ...

    @abstractmethod
    def listar_piars(self, estudiante_id: int) -> list[PIAR]:
        """
        Retorna todos los PIARs de un estudiante, ordenados por año descendente.
        Permite ver el historial de necesidades y ajustes a lo largo de los años.
        """
        ...

    @abstractmethod
    def existe_piar(self, estudiante_id: int, anio_id: int) -> bool:
        """
        True si ya existe un PIAR para ese estudiante y año.
        El servicio verifica esto antes de intentar insertar para
        emitir un error útil antes de llegar al UNIQUE constraint de la BD.
        """
        ...

    @abstractmethod
    def guardar_piar(self, piar: PIAR) -> PIAR:
        """
        Inserta un PIAR nuevo.
        Retorna la entidad con id asignado.
        El servicio debe verificar con `existe_piar` antes de llamar.
        """
        ...

    @abstractmethod
    def actualizar_piar(self, piar: PIAR) -> PIAR:
        """
        Actualiza un PIAR existente.
        Requiere que piar.id no sea None.
        """
        ...


__all__ = ["IEstudianteRepository"]
