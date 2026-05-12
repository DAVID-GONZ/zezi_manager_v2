"""Tests unitarios para HabilitacionService."""
from __future__ import annotations

from datetime import date

import pytest

from src.domain.models.habilitacion import (
    EstadoHabilitacion, EstadoPlanMejoramiento,
    FiltroHabilitacionesDTO, Habilitacion,
    NuevaHabilitacionDTO, NuevoPlanMejoramientoDTO,
    CerrarPlanMejoramientoDTO, PlanMejoramiento,
    TipoHabilitacion, RegistrarNotaHabilitacionDTO,
)
from src.domain.ports.habilitacion_repo import IHabilitacionRepository
from src.services.habilitacion_service import HabilitacionService


# ===========================================================================
# Fake
# ===========================================================================

class FakeHabRepo(IHabilitacionRepository):
    def __init__(self):
        self._habs: dict[int, Habilitacion] = {}
        self._planes: dict[int, PlanMejoramiento] = {}
        self._next_hab = 1
        self._next_plan = 1

    def guardar_habilitacion(self, h: Habilitacion) -> Habilitacion:
        h = h.model_copy(update={"id": self._next_hab})
        self._next_hab += 1
        self._habs[h.id] = h
        return h

    def actualizar_habilitacion(self, h: Habilitacion) -> Habilitacion:
        self._habs[h.id] = h
        return h

    def actualizar_estado_habilitacion(self, hab_id: int, estado: EstadoHabilitacion) -> None:
        h = self._habs[hab_id]
        self._habs[hab_id] = h.model_copy(update={"estado": estado})

    def get_habilitacion(self, hab_id: int) -> Habilitacion | None:
        return self._habs.get(hab_id)

    def listar_habilitaciones(self, filtro: FiltroHabilitacionesDTO) -> list[Habilitacion]:
        return list(self._habs.values())

    def listar_por_estudiante(self, est_id: int) -> list[Habilitacion]:
        return [h for h in self._habs.values() if h.estudiante_id == est_id]

    def existe_habilitacion(self, est_id: int, asig_id: int, tipo: TipoHabilitacion, per_id: int | None) -> bool:
        return any(
            h.estudiante_id == est_id and h.asignacion_id == asig_id
            and h.tipo == tipo and h.periodo_id == per_id
            for h in self._habs.values()
        )

    def guardar_plan(self, p: PlanMejoramiento) -> PlanMejoramiento:
        p = p.model_copy(update={"id": self._next_plan})
        self._next_plan += 1
        self._planes[p.id] = p
        return p

    def actualizar_plan(self, p: PlanMejoramiento) -> PlanMejoramiento:
        self._planes[p.id] = p
        return p

    def get_plan(self, plan_id: int) -> PlanMejoramiento | None:
        return self._planes.get(plan_id)

    def listar_planes_por_estudiante(self, est_id: int, asig_id=None, estado=None) -> list[PlanMejoramiento]:
        return [p for p in self._planes.values() if p.estudiante_id == est_id]

    def listar_planes_por_seguimiento(self, grupo_id: int) -> list[PlanMejoramiento]:
        return []


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> tuple[HabilitacionService, FakeHabRepo]:
    repo = FakeHabRepo()
    return HabilitacionService(repo), repo


def _dto_hab() -> NuevaHabilitacionDTO:
    return NuevaHabilitacionDTO(
        estudiante_id=1, asignacion_id=3,
        tipo=TipoHabilitacion.PERIODO,
        periodo_id=5,
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestProgramarHabilitacion:
    def test_programa_habilitacion_nueva(self):
        svc, _ = _make_svc()
        h = svc.programar_habilitacion(_dto_hab())
        assert h.id is not None
        assert h.estado == EstadoHabilitacion.PENDIENTE

    def test_lanza_si_duplicada(self):
        svc, _ = _make_svc()
        svc.programar_habilitacion(_dto_hab())
        with pytest.raises(ValueError, match="Ya existe"):
            svc.programar_habilitacion(_dto_hab())

    def test_distintos_tipos_no_duplican(self):
        svc, _ = _make_svc()
        dto1 = NuevaHabilitacionDTO(
            estudiante_id=1, asignacion_id=3,
            tipo=TipoHabilitacion.PERIODO,
            periodo_id=5,
        )
        dto2 = NuevaHabilitacionDTO(
            estudiante_id=1, asignacion_id=3,
            tipo=TipoHabilitacion.ANUAL,
            periodo_id=None,
        )
        h1 = svc.programar_habilitacion(dto1)
        h2 = svc.programar_habilitacion(dto2)
        assert h1.id != h2.id


class TestRegistrarNotaHabilitacion:
    def test_nota_aprobatoria_cambia_a_aprobada(self):
        svc, _ = _make_svc()
        h = svc.programar_habilitacion(_dto_hab())
        dto_nota = RegistrarNotaHabilitacionDTO(
            nota=70.0, fecha=date.today(), usuario_id=1
        )
        resultado = svc.registrar_nota_habilitacion(h.id, dto_nota)
        assert resultado.estado == EstadoHabilitacion.APROBADA

    def test_nota_reprobatoria_cambia_a_reprobada(self):
        svc, _ = _make_svc()
        h = svc.programar_habilitacion(_dto_hab())
        dto_nota = RegistrarNotaHabilitacionDTO(
            nota=40.0, fecha=date.today(), usuario_id=1
        )
        resultado = svc.registrar_nota_habilitacion(h.id, dto_nota)
        assert resultado.estado == EstadoHabilitacion.REPROBADA

    def test_lanza_si_habilitacion_no_existe(self):
        svc, _ = _make_svc()
        dto_nota = RegistrarNotaHabilitacionDTO(
            nota=70.0, fecha=date.today(), usuario_id=1
        )
        with pytest.raises(ValueError, match="999"):
            svc.registrar_nota_habilitacion(999, dto_nota)


class TestPlanMejoramiento:
    def test_crea_plan(self):
        svc, _ = _make_svc()
        dto = NuevoPlanMejoramientoDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            descripcion_dificultad="Bajo rendimiento en matemáticas",
            actividades_propuestas="Talleres adicionales y ejercicios de práctica",
        )
        plan = svc.crear_plan(dto)
        assert plan.id is not None
        assert plan.estado == EstadoPlanMejoramiento.ACTIVO

    def test_cierra_plan(self):
        svc, _ = _make_svc()
        dto = NuevoPlanMejoramientoDTO(
            estudiante_id=1, asignacion_id=3, periodo_id=5,
            descripcion_dificultad="Bajo rendimiento",
            actividades_propuestas="Talleres de refuerzo",
        )
        plan = svc.crear_plan(dto)
        dto_cierre = CerrarPlanMejoramientoDTO(
            estado=EstadoPlanMejoramiento.CUMPLIDO,
            observacion="Cumplido satisfactoriamente",
        )
        cerrado = svc.cerrar_plan(plan.id, dto_cierre)
        assert cerrado.estado == EstadoPlanMejoramiento.CUMPLIDO
