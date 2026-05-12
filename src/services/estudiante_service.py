"""
EstudianteService
==================
Orquesta los casos de uso del módulo de Estudiantes y PIARs.
"""
from __future__ import annotations

from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.domain.ports.acudiente_repo import IAcudienteRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.models.estudiante import (
    Estudiante,
    EstadoMatricula,
    NuevoEstudianteDTO,
    ActualizarEstudianteDTO,
    FiltroEstudiantesDTO,
    EstudianteResumenDTO,
)
from src.domain.models.piar import PIAR, NuevoPIARDTO
from src.domain.models.auditoria import AccionCambio, RegistroCambio


class EstudianteService:
    """
    Orquesta los casos de uso del módulo de Estudiantes.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IEstudianteRepository,
        acudiente_repo: IAcudienteRepository | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        self._repo           = repo
        self._acudiente_repo = acudiente_repo
        self._auditoria      = auditoria

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _auditar(
        self,
        accion: AccionCambio,
        tabla: str,
        registro_id: int | None,
        datos_ant: dict | None,
        datos_nue: dict | None,
        usuario_id: int | None,
    ) -> None:
        if self._auditoria is None:
            return
        if accion == AccionCambio.CREATE:
            cambio = RegistroCambio.para_creacion(
                tabla, datos_nue or {}, registro_id, usuario_id
            )
        elif accion == AccionCambio.UPDATE:
            cambio = RegistroCambio.para_actualizacion(
                tabla, datos_ant or {}, datos_nue or {}, registro_id, usuario_id
            )
        else:
            cambio = RegistroCambio.para_eliminacion(
                tabla, datos_ant or {}, registro_id, usuario_id
            )
        self._auditoria.registrar_cambio(cambio)

    def _get_estudiante_o_lanzar(self, estudiante_id: int) -> Estudiante:
        est = self._repo.get_by_id(estudiante_id)
        if est is None:
            raise ValueError(f"Estudiante con id {estudiante_id} no existe.")
        return est

    # ------------------------------------------------------------------
    # Casos de uso — estudiantes
    # ------------------------------------------------------------------

    def matricular(
        self,
        dto: NuevoEstudianteDTO,
        usuario_id: int | None = None,
    ) -> Estudiante:
        """
        Matricula un estudiante nuevo.

        Verifica que el documento no esté duplicado, construye la
        entidad desde el DTO y la persiste.
        """
        if self._repo.existe_documento(dto.numero_documento):
            raise ValueError(
                f"Ya existe un estudiante con el documento '{dto.numero_documento}'."
            )
        estudiante = dto.to_estudiante()
        estudiante = self._repo.guardar(estudiante)
        self._auditar(
            AccionCambio.CREATE, "estudiantes", estudiante.id,
            None, estudiante.model_dump(mode="json"), usuario_id,
        )
        return estudiante

    def actualizar(
        self,
        estudiante_id: int,
        dto: ActualizarEstudianteDTO,
        usuario_id: int | None = None,
    ) -> Estudiante:
        """Actualiza los datos de un estudiante existente."""
        estudiante = self._get_estudiante_o_lanzar(estudiante_id)
        datos_ant = estudiante.model_dump(mode="json")
        estudiante_actualizado = dto.aplicar_a(estudiante)
        self._repo.actualizar(estudiante_actualizado)
        self._auditar(
            AccionCambio.UPDATE, "estudiantes", estudiante_id,
            datos_ant, estudiante_actualizado.model_dump(mode="json"), usuario_id,
        )
        return estudiante_actualizado

    def retirar(
        self,
        estudiante_id: int,
        motivo: str | None = None,
        usuario_id: int | None = None,
    ) -> Estudiante:
        """
        Retira un estudiante del establecimiento.

        Lanza ValueError si el estudiante ya está retirado.
        """
        estudiante = self._get_estudiante_o_lanzar(estudiante_id)
        if estudiante.estado_matricula == EstadoMatricula.RETIRADO:
            raise ValueError("El estudiante ya está en estado RETIRADO.")
        datos_ant = estudiante.model_dump(mode="json")
        estudiante_retirado = estudiante.model_copy(
            update={"estado_matricula": EstadoMatricula.RETIRADO}
        )
        self._repo.actualizar_estado_matricula(
            estudiante_id, EstadoMatricula.RETIRADO.value
        )
        self._auditar(
            AccionCambio.UPDATE, "estudiantes", estudiante_id,
            datos_ant, estudiante_retirado.model_dump(mode="json"), usuario_id,
        )
        return estudiante_retirado

    def asignar_grupo(
        self,
        estudiante_id: int,
        grupo_id: int,
    ) -> Estudiante:
        """
        Asigna o cambia el grupo de un estudiante.

        El trigger de BD registra automáticamente el historial de cambios de grupo.
        """
        estudiante = self._get_estudiante_o_lanzar(estudiante_id)
        self._repo.asignar_grupo(estudiante_id, grupo_id)
        return estudiante.model_copy(update={"grupo_id": grupo_id})

    def listar_por_grupo(
        self,
        grupo_id: int,
        solo_activos: bool = True,
    ) -> list[Estudiante]:
        """Retorna todos los estudiantes de un grupo."""
        return self._repo.listar_por_grupo(grupo_id, solo_activos=solo_activos)

    def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]:
        """Retorna estudiantes según los filtros indicados."""
        return self._repo.listar_filtrado(filtro)

    def listar_resumenes(
        self,
        filtro: FiltroEstudiantesDTO,
    ) -> list[EstudianteResumenDTO]:
        """Retorna la vista resumida de estudiantes para selects."""
        return self._repo.listar_resumenes(filtro)

    def get_by_id(self, estudiante_id: int) -> Estudiante:
        """Retorna un estudiante por id. Lanza si no existe."""
        return self._get_estudiante_o_lanzar(estudiante_id)

    # ------------------------------------------------------------------
    # Casos de uso — PIAR
    # ------------------------------------------------------------------

    def registrar_piar(
        self,
        dto: NuevoPIARDTO,
        usuario_id: int | None = None,
    ) -> PIAR:
        """
        Registra un PIAR para un estudiante en un año lectivo.

        Lanza ValueError si ya existe un PIAR para ese estudiante y año.
        """
        if self._repo.existe_piar(dto.estudiante_id, dto.anio_id):
            raise ValueError(
                f"Ya existe un PIAR para el estudiante {dto.estudiante_id} "
                f"en el año {dto.anio_id}. Actualice el existente."
            )
        piar = dto.to_piar()
        piar = self._repo.guardar_piar(piar)
        # Marcar al estudiante como poseedor de PIAR
        estudiante = self._get_estudiante_o_lanzar(dto.estudiante_id)
        if not estudiante.posee_piar:
            self._repo.actualizar(
                estudiante.model_copy(update={"posee_piar": True})
            )
        self._auditar(
            AccionCambio.CREATE, "piars", piar.id,
            None, piar.model_dump(mode="json"), usuario_id,
        )
        return piar

    def get_piar(self, estudiante_id: int, anio_id: int) -> PIAR | None:
        """Retorna el PIAR del estudiante para el año indicado."""
        return self._repo.get_piar(estudiante_id, anio_id)


__all__ = ["EstudianteService"]
