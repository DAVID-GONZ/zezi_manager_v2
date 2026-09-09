"""
HabilitacionService
====================
Orquesta los casos de uso de habilitaciones y planes de mejoramiento.
"""

from __future__ import annotations

from src.domain.exceptions import (
    ConflictoError,
    NoEncontradoError,
)
from src.domain.models.auditoria import AccionCambio
from src.domain.models.habilitacion import (
    CerrarPlanMejoramientoDTO,
    EstadoHabilitacion,
    EstadoPlanMejoramiento,
    FiltroHabilitacionesDTO,
    Habilitacion,
    NuevaHabilitacionDTO,
    NuevoPlanMejoramientoDTO,
    PlanMejoramiento,
    RegistrarNotaHabilitacionDTO,
)
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.ports.cierre_repo import ICierreRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.ports.habilitacion_repo import IHabilitacionRepository
from src.services.auditoria_helpers import auditar_cambio
from src.services.contexto_tenant import institucion_actual
from src.services.solo_lectura import requiere_escritura


class HabilitacionService:
    """
    Orquesta los casos de uso del módulo de Habilitaciones.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IHabilitacionRepository,
        cierre_repo: ICierreRepository | None = None,
        config_repo: IConfiguracionRepository | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        """Inyecta el repo de habilitación y los repos opcionales de cierre,
        configuración y auditoría."""
        self._repo = repo
        self._cierre_repo = cierre_repo
        self._config_repo = config_repo
        self._auditoria = auditoria

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_habilitacion_o_lanzar(self, hab_id: int) -> Habilitacion:
        hab = self._repo.get_habilitacion(hab_id)
        if hab is None:
            raise NoEncontradoError(f"Habilitación con id {hab_id} no existe.")
        return hab

    def _get_plan_o_lanzar(self, plan_id: int) -> PlanMejoramiento:
        plan = self._repo.get_plan(plan_id)
        if plan is None:
            raise NoEncontradoError(f"Plan de mejoramiento con id {plan_id} no existe.")
        return plan

    # ------------------------------------------------------------------
    # Habilitaciones
    # ------------------------------------------------------------------

    def programar_habilitacion(
        self,
        dto: NuevaHabilitacionDTO,
        usuario_id: int | None = None,
    ) -> Habilitacion:
        """
        Programa una habilitación para un estudiante.

        Verifica:
        - Que no exista ya una habilitación para esa combinación.
        - (Opcional) Que el estudiante efectivamente perdió la materia.
        """
        if self._repo.existe_habilitacion(
            dto.estudiante_id,
            dto.asignacion_id,
            dto.tipo,
            dto.periodo_id,
        ):
            raise ConflictoError(
                f"Ya existe una habilitación de tipo '{dto.tipo.value}' para "
                f"el estudiante {dto.estudiante_id} en la asignación {dto.asignacion_id}."
            )

        habilitacion = dto.to_habilitacion()
        habilitacion = self._repo.guardar_habilitacion(habilitacion)
        auditar_cambio(
            self._auditoria,
            accion=AccionCambio.CREATE,
            tabla="habilitaciones",
            registro_id=habilitacion.id,
            nuevo=habilitacion.model_dump(mode="json"),
        )
        return habilitacion

    @requiere_escritura
    def registrar_nota_habilitacion(
        self,
        hab_id: int,
        dto: RegistrarNotaHabilitacionDTO,
        anio_id: int | None = None,
    ) -> Habilitacion:
        """
        Registra la nota obtenida en la habilitación y determina si aprueba.

        Transición: PENDIENTE → REALIZADA → APROBADA | REPROBADA
        """
        hab = self._get_habilitacion_o_lanzar(hab_id)
        datos_ant = hab.model_dump(mode="json")

        # Registrar nota: PENDIENTE → REALIZADA
        hab_realizada = hab.registrar_nota(
            nota=dto.nota,
            fecha=dto.fecha,
            usuario_id=dto.usuario_id,
            observacion=dto.observacion,
        )
        self._repo.actualizar_habilitacion(hab_realizada)

        # Determinar automáticamente si aprueba
        nota_minima = 60.0
        if self._config_repo is not None and anio_id is not None:
            criterios = self._config_repo.get_criterios(anio_id)
            if criterios is not None:
                nota_minima = criterios.nota_minima_habilitacion

        hab_final = hab_realizada.aprobar() if dto.nota >= nota_minima else hab_realizada.reprobar()

        self._repo.actualizar_habilitacion(hab_final)
        auditar_cambio(
            self._auditoria,
            accion=AccionCambio.UPDATE,
            tabla="habilitaciones",
            registro_id=hab_id,
            anterior=datos_ant,
            nuevo=hab_final.model_dump(mode="json"),
        )
        return hab_final

    def listar_habilitaciones(
        self,
        filtro: FiltroHabilitacionesDTO,
    ) -> list[Habilitacion]:
        """Retorna habilitaciones según los filtros indicados."""
        return self._repo.listar_habilitaciones(filtro)

    def contar_habilitaciones_pendientes(
        self,
        periodo_id: int | None = None,
    ) -> int:
        """Cuenta las habilitaciones en estado PENDIENTE (SOLO LECTURA).

        Si se indica `periodo_id`, restringe el conteo a ese periodo;
        de lo contrario cuenta todas las pendientes. Usado por el dashboard
        institucional del directivo.
        """
        scope = institucion_actual() or "*"
        filtro = FiltroHabilitacionesDTO(
            institucion_id=scope,
            periodo_id=periodo_id,
            estado=EstadoHabilitacion.PENDIENTE,
            por_pagina=200,
        )
        return len(self._repo.listar_habilitaciones(filtro))

    def get_by_id(self, hab_id: int) -> Habilitacion:
        """Retorna una habilitación por id. Lanza si no existe."""
        return self._get_habilitacion_o_lanzar(hab_id)

    # ------------------------------------------------------------------
    # Planes de mejoramiento
    # ------------------------------------------------------------------

    @requiere_escritura
    def crear_plan(
        self,
        dto: NuevoPlanMejoramientoDTO,
        usuario_id: int | None = None,
    ) -> PlanMejoramiento:
        """Crea un plan de mejoramiento para un estudiante."""
        plan = dto.to_plan(usuario_id=usuario_id)
        plan = self._repo.guardar_plan(plan)
        auditar_cambio(
            self._auditoria,
            accion=AccionCambio.CREATE,
            tabla="planes_mejoramiento",
            registro_id=plan.id,
            nuevo=plan.model_dump(mode="json"),
        )
        return plan

    @requiere_escritura
    def cerrar_plan(
        self,
        plan_id: int,
        dto: CerrarPlanMejoramientoDTO,
        usuario_id: int | None = None,
    ) -> PlanMejoramiento:
        """
        Cierra un plan de mejoramiento con el estado y observación indicados.

        ACTIVO → CUMPLIDO | INCUMPLIDO.
        """
        plan = self._get_plan_o_lanzar(plan_id)
        datos_ant = plan.model_dump(mode="json")
        plan_cerrado = plan.cerrar(dto.estado, dto.observacion)
        self._repo.actualizar_plan(plan_cerrado)
        auditar_cambio(
            self._auditoria,
            accion=AccionCambio.UPDATE,
            tabla="planes_mejoramiento",
            registro_id=plan_id,
            anterior=datos_ant,
            nuevo=plan_cerrado.model_dump(mode="json"),
        )
        return plan_cerrado

    def listar_planes_por_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int | None = None,
        estado: EstadoPlanMejoramiento | None = None,
    ) -> list[PlanMejoramiento]:
        """Retorna los planes de mejoramiento de un estudiante."""
        return self._repo.listar_planes_por_estudiante(estudiante_id, asignacion_id, estado)


__all__ = ["HabilitacionService"]
