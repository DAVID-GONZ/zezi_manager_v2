"""
AsignacionService
==================
Orquesta los casos de uso del módulo de Asignaciones académicas.
"""
from __future__ import annotations

from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.models.asignacion import (
    Asignacion,
    AsignacionInfo,
    FiltroAsignacionesDTO,
    NuevaAsignacionDTO,
)
from src.domain.models.auditoria import AccionCambio, RegistroCambio


class AsignacionService:
    """
    Orquesta los casos de uso del módulo de Asignaciones.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IAsignacionRepository,
        periodo_repo: IPeriodoRepository | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        self._repo        = repo
        self._periodo_repo = periodo_repo
        self._auditoria   = auditoria

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

    def _get_asignacion_o_lanzar(self, asignacion_id: int) -> Asignacion:
        asig = self._repo.get_by_id(asignacion_id)
        if asig is None:
            raise ValueError(f"Asignación con id {asignacion_id} no existe.")
        return asig

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    def crear_asignacion(
        self,
        dto: NuevaAsignacionDTO,
        usuario_id: int | None = None,
    ) -> Asignacion:
        """
        Crea una asignación docente-grupo-asignatura-periodo.

        Verifica:
        - Que el periodo exista y esté activo (no cerrado).
        - Que no exista ya la misma combinación.
        """
        if self._periodo_repo is not None:
            periodo = self._periodo_repo.get_by_id(dto.periodo_id)
            if periodo is None:
                raise ValueError(
                    f"Periodo con id {dto.periodo_id} no existe."
                )
            if not periodo.esta_abierto:
                raise ValueError(
                    f"El periodo '{periodo.nombre}' está cerrado. "
                    "No se pueden crear asignaciones en periodos cerrados."
                )

        if self._repo.existe(
            dto.grupo_id, dto.asignatura_id, dto.usuario_id, dto.periodo_id
        ):
            raise ValueError(
                "Ya existe una asignación con esa combinación de grupo, "
                "asignatura, docente y periodo."
            )

        asignacion = dto.to_asignacion()
        asignacion = self._repo.guardar(asignacion)
        self._auditar(
            AccionCambio.CREATE, "asignaciones", asignacion.id,
            None, asignacion.model_dump(mode="json"), usuario_id,
        )
        return asignacion

    def desactivar(
        self,
        asignacion_id: int,
        usuario_id: int | None = None,
    ) -> Asignacion:
        """Desactiva una asignación (soft delete)."""
        asig = self._get_asignacion_o_lanzar(asignacion_id)
        if not asig.activo:
            raise ValueError(
                f"La asignación {asignacion_id} ya está desactivada."
            )
        datos_ant = asig.model_dump(mode="json")
        self._repo.desactivar(asignacion_id)
        asig_desactivada = asig.model_copy(update={"activo": False})
        self._auditar(
            AccionCambio.UPDATE, "asignaciones", asignacion_id,
            datos_ant, asig_desactivada.model_dump(mode="json"), usuario_id,
        )
        return asig_desactivada

    def reasignar_docente(
        self,
        asignacion_id: int,
        nuevo_usuario_id: int,
        usuario_id: int | None = None,
    ) -> Asignacion:
        """
        Reasigna una asignación a un docente diferente.

        Verifica que la nueva combinación no exista ya.
        """
        asig = self._get_asignacion_o_lanzar(asignacion_id)
        if asig.usuario_id == nuevo_usuario_id:
            raise ValueError(
                "El nuevo docente es el mismo que el actual."
            )
        if self._repo.existe(
            asig.grupo_id, asig.asignatura_id, nuevo_usuario_id, asig.periodo_id
        ):
            raise ValueError(
                "Ya existe una asignación con ese docente para el mismo "
                "grupo, asignatura y periodo."
            )
        datos_ant = asig.model_dump(mode="json")
        self._repo.reasignar_docente(asignacion_id, nuevo_usuario_id)
        asig_reasignada = asig.model_copy(update={"usuario_id": nuevo_usuario_id})
        self._auditar(
            AccionCambio.UPDATE, "asignaciones", asignacion_id,
            datos_ant, asig_reasignada.model_dump(mode="json"), usuario_id,
        )
        return asig_reasignada

    def listar_con_info(
        self,
        filtro: FiltroAsignacionesDTO,
    ) -> list[AsignacionInfo]:
        """Retorna asignaciones con nombres resueltos por JOIN."""
        return self._repo.listar_info(filtro)

    def listar_por_docente(
        self,
        usuario_id: int,
        periodo_id: int | None = None,
    ) -> list[AsignacionInfo]:
        """Retorna las asignaciones de un docente con info completa."""
        return self._repo.listar_por_docente(usuario_id, periodo_id)

    def get_by_id(self, asignacion_id: int) -> Asignacion:
        """Retorna una asignación por id. Lanza si no existe."""
        return self._get_asignacion_o_lanzar(asignacion_id)


__all__ = ["AsignacionService"]
