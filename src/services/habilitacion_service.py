"""
HabilitacionService
====================
Orquesta los casos de uso de habilitaciones y planes de mejoramiento.
"""
from __future__ import annotations

from datetime import date

from src.domain.ports.habilitacion_repo import IHabilitacionRepository
from src.domain.ports.cierre_repo import ICierreRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.models.habilitacion import (
    EstadoHabilitacion,
    EstadoPlanMejoramiento,
    FiltroHabilitacionesDTO,
    Habilitacion,
    NuevaHabilitacionDTO,
    NuevoPlanMejoramientoDTO,
    CerrarPlanMejoramientoDTO,
    PlanMejoramiento,
    TipoHabilitacion,
    RegistrarNotaHabilitacionDTO,
)
from src.domain.models.auditoria import AccionCambio, RegistroCambio
from src.domain.ports.auditoria_repo import IAuditoriaRepository


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
        self._repo        = repo
        self._cierre_repo = cierre_repo
        self._config_repo = config_repo
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

    def _get_habilitacion_o_lanzar(self, hab_id: int) -> Habilitacion:
        hab = self._repo.get_habilitacion(hab_id)
        if hab is None:
            raise ValueError(f"Habilitación con id {hab_id} no existe.")
        return hab

    def _get_plan_o_lanzar(self, plan_id: int) -> PlanMejoramiento:
        plan = self._repo.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan de mejoramiento con id {plan_id} no existe.")
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
            raise ValueError(
                f"Ya existe una habilitación de tipo '{dto.tipo.value}' para "
                f"el estudiante {dto.estudiante_id} en la asignación {dto.asignacion_id}."
            )

        habilitacion = dto.to_habilitacion()
        habilitacion = self._repo.guardar_habilitacion(habilitacion)
        self._auditar(
            AccionCambio.CREATE, "habilitaciones", habilitacion.id,
            None, habilitacion.model_dump(mode="json"), usuario_id,
        )
        return habilitacion

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

        if dto.nota >= nota_minima:
            hab_final = hab_realizada.aprobar()
        else:
            hab_final = hab_realizada.reprobar()

        self._repo.actualizar_habilitacion(hab_final)
        self._auditar(
            AccionCambio.UPDATE, "habilitaciones", hab_id,
            datos_ant, hab_final.model_dump(mode="json"), dto.usuario_id,
        )
        return hab_final

    def listar_habilitaciones(
        self,
        filtro: FiltroHabilitacionesDTO,
    ) -> list[Habilitacion]:
        """Retorna habilitaciones según los filtros indicados."""
        return self._repo.listar_habilitaciones(filtro)

    def get_by_id(self, hab_id: int) -> Habilitacion:
        """Retorna una habilitación por id. Lanza si no existe."""
        return self._get_habilitacion_o_lanzar(hab_id)

    # ------------------------------------------------------------------
    # Planes de mejoramiento
    # ------------------------------------------------------------------

    def crear_plan(
        self,
        dto: NuevoPlanMejoramientoDTO,
        usuario_id: int | None = None,
    ) -> PlanMejoramiento:
        """Crea un plan de mejoramiento para un estudiante."""
        plan = dto.to_plan(usuario_id=usuario_id)
        plan = self._repo.guardar_plan(plan)
        self._auditar(
            AccionCambio.CREATE, "planes_mejoramiento", plan.id,
            None, plan.model_dump(mode="json"), usuario_id,
        )
        return plan

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
        self._auditar(
            AccionCambio.UPDATE, "planes_mejoramiento", plan_id,
            datos_ant, plan_cerrado.model_dump(mode="json"), usuario_id,
        )
        return plan_cerrado

    def listar_planes_por_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int | None = None,
        estado: EstadoPlanMejoramiento | None = None,
    ) -> list[PlanMejoramiento]:
        """Retorna los planes de mejoramiento de un estudiante."""
        return self._repo.listar_planes_por_estudiante(
            estudiante_id, asignacion_id, estado
        )


__all__ = ["HabilitacionService"]
