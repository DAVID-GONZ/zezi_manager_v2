"""
Port: IAcudienteRepository
============================
Contrato de acceso a datos para el módulo de acudientes.

Cubre:
  Acudiente          — entidad del acudiente (datos personales y contacto)
  EstudianteAcudiente — vínculo pivot entre estudiante y acudiente

Patrones de uso principales:

  Registrar un acudiente nuevo y vincularlo:
    acudiente = repo.guardar(nuevo_acudiente)
    repo.vincular(EstudianteAcudiente(
        estudiante_id=est_id,
        acudiente_id=acudiente.id,
        es_principal=True,
    ))

  Consultar el acudiente principal para el boletín:
    principal = repo.get_principal(estudiante_id)

  Un acudiente con varios hijos:
    acudiente = repo.get_by_documento("12345678")
    # luego vincular a cada estudiante

Invariante del servicio (no del repositorio):
  Solo puede haber un acudiente con es_principal=True por estudiante.
  `establecer_principal` lo garantiza desvinculando el anterior primero.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.acudiente import Acudiente, EstudianteAcudiente


class IAcudienteRepository(ABC):

    # =========================================================================
    # Lectura — acudiente
    # =========================================================================

    @abstractmethod
    def get_by_id(self, acudiente_id: int) -> Acudiente | None:
        """Retorna el acudiente con ese id, o None si no existe."""
        ...

    @abstractmethod
    def get_by_documento(self, numero_documento: str) -> Acudiente | None:
        """
        Busca un acudiente por número de documento.
        Útil para evitar duplicados cuando se registra un nuevo acudiente.
        Retorna None si no existe.
        """
        ...

    @abstractmethod
    def existe_documento(self, numero_documento: str) -> bool:
        """
        True si ya existe un acudiente con ese número de documento.
        """
        ...

    @abstractmethod
    def listar_por_estudiante(
        self,
        estudiante_id: int,
        solo_activos: bool = True,
    ) -> list[Acudiente]:
        """
        Retorna todos los acudientes vinculados a un estudiante,
        opcionalmente filtrando solo los activos.
        Ordenados: el principal primero.
        """
        ...

    @abstractmethod
    def get_principal(self, estudiante_id: int) -> Acudiente | None:
        """
        Retorna el acudiente marcado como principal para un estudiante.
        Retorna None si el estudiante no tiene acudiente principal.
        Usado para imprimir el nombre en boletines y citaciones.
        """
        ...

    @abstractmethod
    def listar_estudiantes_de_acudiente(
        self,
        acudiente_id: int,
    ) -> list[int]:
        """
        Retorna los IDs de los estudiantes vinculados a un acudiente.
        Un acudiente puede tener varios hijos en la institución.
        """
        ...

    # =========================================================================
    # Escritura — acudiente
    # =========================================================================

    @abstractmethod
    def guardar(self, acudiente: Acudiente) -> Acudiente:
        """
        Inserta un acudiente nuevo.
        Retorna la entidad con id asignado.
        El servicio debe verificar que el documento no exista antes.
        """
        ...

    @abstractmethod
    def actualizar(self, acudiente: Acudiente) -> Acudiente:
        """
        Actualiza los datos de un acudiente existente.
        No cambia numero_documento (es el identificador principal).
        Requiere que acudiente.id no sea None.
        """
        ...

    @abstractmethod
    def desactivar(self, acudiente_id: int) -> bool:
        """
        Marca el acudiente como inactivo (activo=False, soft delete).
        Retorna True si la fila fue afectada.
        Los vínculos con estudiantes permanecen para el historial.
        """
        ...

    # =========================================================================
    # Gestión de vínculos
    # =========================================================================

    @abstractmethod
    def vincular(self, vinculo: EstudianteAcudiente) -> None:
        """
        Crea el vínculo entre un estudiante y un acudiente.
        Si el vínculo ya existe (mismo estudiante_id + acudiente_id),
        actualiza es_principal.
        """
        ...

    @abstractmethod
    def desvincular(
        self,
        estudiante_id: int,
        acudiente_id: int,
    ) -> bool:
        """
        Elimina el vínculo entre un estudiante y un acudiente.
        Retorna True si el vínculo existía y fue eliminado.
        No elimina el acudiente — puede tener otros estudiantes vinculados.
        """
        ...

    @abstractmethod
    def establecer_principal(
        self,
        estudiante_id: int,
        acudiente_id: int,
    ) -> None:
        """
        Marca un acudiente como principal para un estudiante.
        Quita el flag es_principal del acudiente que lo tenía antes
        (si existía) y lo asigna al nuevo.
        Operación atómica: los dos UPDATEs van en la misma transacción.
        """
        ...

    @abstractmethod
    def get_vinculo(
        self,
        estudiante_id: int,
        acudiente_id: int,
    ) -> EstudianteAcudiente | None:
        """
        Retorna el vínculo entre un estudiante y un acudiente,
        o None si no existe.
        """
        ...