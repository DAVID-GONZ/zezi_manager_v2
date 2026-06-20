"""
AsignacionService
==================
Orquesta los casos de uso del módulo de Asignaciones académicas.
"""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from dataclasses import dataclass

from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.ports.usuario_repo import IUsuarioRepository
from src.domain.models.asignacion import (
    Asignacion,
    AsignacionInfo,
    FiltroAsignacionesDTO,
    NuevaAsignacionDTO,
)
from src.domain.models.auditoria import AccionCambio, RegistroCambio


# =============================================================================
# DTOs de resultado (consumidos por las vistas — se re-exportan desde aquí)
# =============================================================================

@dataclass(frozen=True)
class CupoDocenteDTO:
    """Cupo de un docente para una (asignatura, grupo) con sus horas."""
    usuario_id: int
    carga_actual: int
    cap_efectivo: int | None      # None = sin tope configurado
    tiene_cupo: bool
    es_actual: bool               # ya está asignado a esa materia/grupo


@dataclass(frozen=True)
class CompletitudGrupoDTO:
    """Cobertura del plan de estudios de un grupo en un periodo."""
    horas_asignadas: int
    horas_totales: int

    @property
    def completo(self) -> bool:
        return bool(self.horas_totales) and self.horas_asignadas >= self.horas_totales

    @property
    def faltantes(self) -> int:
        return max(0, self.horas_totales - self.horas_asignadas)


class AsignacionService:
    """
    Orquesta los casos de uso del módulo de Asignaciones.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IAsignacionRepository,
        periodo_repo:  IPeriodoRepository           | None = None,
        auditoria:     IAuditoriaRepository         | None = None,
        usuario_repo:  IUsuarioRepository           | None = None,
        infra_repo:    IInfraestructuraRepository   | None = None,
        plan_svc=None,
    ) -> None:
        self._repo         = repo
        self._periodo_repo = periodo_repo
        self._auditoria    = auditoria
        self._usuario_repo = usuario_repo
        self._infra_repo   = infra_repo
        self._plan_svc     = plan_svc

    # ------------------------------------------------------------------
    # Horas y carga docente (vía plan de estudios, con fallback global)
    # ------------------------------------------------------------------

    def horas_de_asignacion(self, grupo_id: int, asignatura_id: int) -> int:
        """Horas semanales que aporta una (grupo, asignatura) según el plan del
        grado del grupo; fallback al horas_semanales global de la asignatura."""
        if self._plan_svc is not None and self._infra_repo is not None:
            grupo = self._infra_repo.get_grupo(grupo_id)
            if grupo is not None and grupo.grado is not None:
                return self._plan_svc.horas_de(grupo.grado, asignatura_id)
        if self._infra_repo is not None:
            asig = self._infra_repo.get_asignatura(asignatura_id)
            return (asig.horas_semanales or 0) if asig else 0
        return 0

    def carga_docente(self, usuario_id: int, periodo_id: int) -> int:
        """Suma de horas semanales asignadas (activas) a un docente en un periodo."""
        activas = self._repo.listar(
            FiltroAsignacionesDTO(
                usuario_id=usuario_id, periodo_id=periodo_id, solo_activas=True
            )
        )
        return sum(
            self.horas_de_asignacion(a.grupo_id, a.asignatura_id) for a in activas
        )

    @requiere_escritura
    def desactivar_por_grado_asignatura(
        self, grado: int, asignatura_id: int, usuario_id: int | None = None
    ) -> int:
        """Desactiva las asignaciones activas de una asignatura en todos los
        grupos de un grado (al quitarla del plan de estudios). Retorna cuántas.
        """
        if self._infra_repo is None:
            return 0
        grupos = self._infra_repo.listar_grupos(grado=grado)
        n = 0
        for g in grupos:
            activas = self._repo.listar(
                FiltroAsignacionesDTO(
                    grupo_id=g.id, asignatura_id=asignatura_id, solo_activas=True
                )
            )
            for a in activas:
                self.desactivar(a.id, usuario_id=usuario_id)
                n += 1
        return n

    # ------------------------------------------------------------------
    # Swap atómico docente↔materia (encapsula la orquestación de la vista)
    # ------------------------------------------------------------------

    @requiere_escritura
    def asignar_docente_a_materia(
        self,
        grupo_id: int,
        asignatura_id: int,
        periodo_id: int,
        nuevo_usuario_id: int | None,
        usuario_id: int | None = None,
    ) -> Asignacion | None:
        """Asigna (o quita) el docente de una materia en un grupo+periodo de forma
        atómica desde la perspectiva del llamador:

          - nuevo_usuario_id is None → desactiva el docente actual (si lo hay).
          - nuevo_usuario_id == actual → no-op (retorna la asignación activa).
          - distinto → desactiva el actual, y reactiva el combo inactivo existente
            (mismo docente+materia+grupo+periodo) o crea uno nuevo.

        Retorna la asignación activa resultante, o None si solo se desactivó.
        """
        activas = self._repo.listar(
            FiltroAsignacionesDTO(
                grupo_id=grupo_id, asignatura_id=asignatura_id,
                periodo_id=periodo_id, solo_activas=True,
            )
        )
        activa = activas[0] if activas else None

        if nuevo_usuario_id is None:
            if activa is not None:
                self.desactivar(activa.id, usuario_id=usuario_id)
            return None

        if activa is not None and activa.usuario_id == nuevo_usuario_id:
            return activa

        if activa is not None:
            self.desactivar(activa.id, usuario_id=usuario_id)

        # ¿existe un combo inactivo para reactivar?
        todas = self._repo.listar(
            FiltroAsignacionesDTO(
                grupo_id=grupo_id, asignatura_id=asignatura_id,
                periodo_id=periodo_id, solo_activas=False,
            )
        )
        destino = next(
            (a for a in todas
             if a.usuario_id == nuevo_usuario_id and not a.activo),
            None,
        )
        if destino is not None:
            return self.reactivar(destino.id, usuario_id=usuario_id)

        return self.crear_asignacion(
            NuevaAsignacionDTO(
                usuario_id=nuevo_usuario_id, grupo_id=grupo_id,
                asignatura_id=asignatura_id, periodo_id=periodo_id,
            ),
            usuario_id=usuario_id,
        )

    # ------------------------------------------------------------------
    # Cupo de docentes (cálculo hoy en la vista _fila_materia)
    # ------------------------------------------------------------------

    def docentes_con_cupo(
        self,
        asignatura_id: int,
        grupo_id: int,
        horas: int,
        periodo_id: int,
        docente_ids: list[int],
        usuario_actual_id: int | None = None,
    ) -> dict[int, CupoDocenteDTO]:
        """Por cada docente en `docente_ids`, calcula (carga_actual, cap_efectivo,
        tiene_cupo) para asumir `horas` adicionales en esta materia/grupo.

        El docente actualmente asignado (`usuario_actual_id`) no suma las horas
        nuevas (ya las tiene) y siempre se considera con cupo.
        """
        out: dict[int, CupoDocenteDTO] = {}
        for did in docente_ids:
            es_actual = (did == usuario_actual_id)
            carga = self.carga_docente(did, periodo_id)
            cap = None
            if self._usuario_repo is not None:
                u = self._usuario_repo.get_by_id(did)
                cap = u.carga_maxima_efectiva if u else None
            if cap is None:
                tiene_cupo = True
            else:
                proyectado = carga + (0 if es_actual else (horas or 0))
                tiene_cupo = proyectado <= cap
            out[did] = CupoDocenteDTO(
                usuario_id=did, carga_actual=carga, cap_efectivo=cap,
                tiene_cupo=tiene_cupo or es_actual, es_actual=es_actual,
            )
        return out

    # ------------------------------------------------------------------
    # Cobertura del plan de estudios (cálculo hoy en la vista)
    # ------------------------------------------------------------------

    def completitud_grupo(
        self, grupo_id: int, grado: int | None, periodo_id: int
    ) -> CompletitudGrupoDTO:
        """(horas del plan ya asignadas, total del plan) para un grupo+periodo."""
        if grado is None or self._plan_svc is None:
            return CompletitudGrupoDTO(0, 0)
        plan = {
            p.asignatura_id: p.horas_semanales
            for p in self._plan_svc.por_grado(grado)
        }
        total = sum(plan.values())
        asigns = self._repo.listar(
            FiltroAsignacionesDTO(
                grupo_id=grupo_id, periodo_id=periodo_id, solo_activas=True
            )
        )
        asignadas = sum(plan.get(a.asignatura_id, 0) for a in asigns)
        return CompletitudGrupoDTO(asignadas, total)

    def materias_sin_docente(
        self, grupo_id: int, grado: int | None, periodo_id: int
    ) -> list[int]:
        """IDs de asignaturas del plan del grado sin docente activo en el grupo."""
        if grado is None or self._plan_svc is None:
            return []
        asigns = self._repo.listar(
            FiltroAsignacionesDTO(
                grupo_id=grupo_id, periodo_id=periodo_id, solo_activas=True
            )
        )
        ya = {a.asignatura_id for a in asigns}
        return [
            p.asignatura_id
            for p in self._plan_svc.por_grado(grado)
            if p.asignatura_id not in ya
        ]

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

    def _validar_carga_docente(self, dto: NuevaAsignacionDTO) -> None:
        """Comprueba que agregar esta asignación no supere carga_horaria_max (R4)."""
        if self._usuario_repo is None or self._infra_repo is None:
            return
        usuario = self._usuario_repo.get_by_id(dto.usuario_id)
        if usuario is None or usuario.carga_maxima_efectiva is None:
            return
        cap = usuario.carga_maxima_efectiva
        nuevas_horas = self.horas_de_asignacion(dto.grupo_id, dto.asignatura_id)
        carga_actual = self.carga_docente(dto.usuario_id, dto.periodo_id)
        total = carga_actual + nuevas_horas
        if total > cap:
            nombre = usuario.nombre_completo or usuario.usuario
            extra_txt = (
                f" ({usuario.carga_horaria_max}h base + {usuario.horas_extra}h extra)"
                if usuario.horas_extra else ""
            )
            raise ValueError(
                f"Esta asignación elevaría la carga de {nombre} a {total}h/semana, "
                f"superando su tope de {cap}h{extra_txt}. "
                "Sube las horas extra o reasigna a otro docente."
            )

    def _get_asignacion_o_lanzar(self, asignacion_id: int) -> Asignacion:
        asig = self._repo.get_by_id(asignacion_id)
        if asig is None:
            raise ValueError(f"Asignación con id {asignacion_id} no existe.")
        return asig

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    @requiere_escritura
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

        self._validar_carga_docente(dto)

        asignacion = dto.to_asignacion()
        asignacion = self._repo.guardar(asignacion)
        self._auditar(
            AccionCambio.CREATE, "asignaciones", asignacion.id,
            None, asignacion.model_dump(mode="json"), usuario_id,
        )
        return asignacion

    @requiere_escritura
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

    @requiere_escritura
    def reactivar(
        self,
        asignacion_id: int,
        usuario_id: int | None = None,
    ) -> Asignacion:
        """Reactiva una asignación previamente desactivada (idempotente)."""
        asig = self._get_asignacion_o_lanzar(asignacion_id)
        if asig.activo:
            return asig
        datos_ant = asig.model_dump(mode="json")
        self._repo.reactivar(asignacion_id)
        asig_react = asig.model_copy(update={"activo": True})
        self._auditar(
            AccionCambio.UPDATE, "asignaciones", asignacion_id,
            datos_ant, asig_react.model_dump(mode="json"), usuario_id,
        )
        return asig_react

    @requiere_escritura
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

    def listar_por_grupo(
        self,
        grupo_id: int,
        solo_activas: bool = True,
    ) -> list[AsignacionInfo]:
        """Retorna las asignaciones de un grupo con info completa."""
        filtro = FiltroAsignacionesDTO(grupo_id=grupo_id, solo_activas=solo_activas)
        return self._repo.listar_info(filtro)


__all__ = [
    "AsignacionService",
    "FiltroAsignacionesDTO",
    "CupoDocenteDTO",
    "CompletitudGrupoDTO",
]
