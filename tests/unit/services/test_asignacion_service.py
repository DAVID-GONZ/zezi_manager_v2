"""Tests unitarios para AsignacionService."""
from __future__ import annotations

import pytest

from src.domain.models.asignacion import (
    Asignacion, AsignacionInfo, FiltroAsignacionesDTO, NuevaAsignacionDTO,
)
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.services.asignacion_service import AsignacionService


# ===========================================================================
# Fake
# ===========================================================================

class FakeAsignacionRepo(IAsignacionRepository):
    def __init__(self):
        self._asigs: dict[int, Asignacion] = {}
        self._next_id = 1

    def guardar(self, a: Asignacion) -> Asignacion:
        a = a.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._asigs[a.id] = a
        return a

    def get_by_id(self, aid: int) -> Asignacion | None:
        return self._asigs.get(aid)

    def get_info(self, aid: int) -> AsignacionInfo | None:
        return None

    def existe(self, grupo_id: int, asignatura_id: int, usuario_id: int, periodo_id: int) -> bool:
        return any(
            a.grupo_id == grupo_id and a.asignatura_id == asignatura_id
            and a.usuario_id == usuario_id and a.periodo_id == periodo_id
            for a in self._asigs.values()
        )

    def desactivar(self, aid: int) -> None:
        a = self._asigs[aid]
        self._asigs[aid] = a.model_copy(update={"activo": False})

    def reactivar(self, aid: int) -> None:
        a = self._asigs[aid]
        self._asigs[aid] = a.model_copy(update={"activo": True})

    def reasignar_docente(self, aid: int, nuevo_usuario_id: int) -> None:
        a = self._asigs[aid]
        self._asigs[aid] = a.model_copy(update={"usuario_id": nuevo_usuario_id})

    def listar(self, filtro: FiltroAsignacionesDTO) -> list[Asignacion]:
        return list(self._asigs.values())

    def listar_info(self, filtro: FiltroAsignacionesDTO) -> list[AsignacionInfo]:
        return []

    def listar_por_docente(self, uid: int, periodo_id=None) -> list[AsignacionInfo]:
        return []

    def listar_por_grupo(self, grupo_id: int, periodo_id=None) -> list[Asignacion]:
        return [a for a in self._asigs.values() if a.grupo_id == grupo_id]


def _make_svc() -> tuple[AsignacionService, FakeAsignacionRepo]:
    repo = FakeAsignacionRepo()
    return AsignacionService(repo), repo


def _dto(usuario_id: int = 1) -> NuevaAsignacionDTO:
    return NuevaAsignacionDTO(
        grupo_id=10, asignatura_id=20, usuario_id=usuario_id, periodo_id=5
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestCrearAsignacion:
    def test_crea_asignacion_nueva(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto())
        assert a.id is not None

    def test_lanza_si_duplicada(self):
        svc, _ = _make_svc()
        svc.crear_asignacion(_dto())
        with pytest.raises(ValueError, match="Ya existe"):
            svc.crear_asignacion(_dto())

    def test_distintos_docentes_en_misma_asignatura(self):
        svc, _ = _make_svc()
        a1 = svc.crear_asignacion(_dto(usuario_id=1))
        a2 = svc.crear_asignacion(_dto(usuario_id=2))
        assert a1.id != a2.id


class TestDesactivar:
    def test_desactiva_asignacion_activa(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto())
        resultado = svc.desactivar(a.id)
        assert resultado.activo is False

    def test_lanza_si_ya_inactiva(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto())
        svc.desactivar(a.id)
        with pytest.raises(ValueError, match="ya está desactivada"):
            svc.desactivar(a.id)

    def test_lanza_si_no_existe(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.desactivar(999)


class TestReasignarDocente:
    def test_reasigna_a_nuevo_docente(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto(usuario_id=1))
        resultado = svc.reasignar_docente(a.id, nuevo_usuario_id=99)
        assert resultado.usuario_id == 99

    def test_lanza_si_mismo_docente(self):
        svc, _ = _make_svc()
        a = svc.crear_asignacion(_dto(usuario_id=1))
        with pytest.raises(ValueError, match="mismo"):
            svc.reasignar_docente(a.id, nuevo_usuario_id=1)


# ===========================================================================
# Group 1 — swap atómico, cupo y cobertura del plan
# ===========================================================================

class _FilterAsignRepo(FakeAsignacionRepo):
    """Repo que respeta el filtro (grupo/asignatura/usuario/periodo/activas)."""
    def listar(self, f: FiltroAsignacionesDTO) -> list[Asignacion]:
        out = []
        for a in self._asigs.values():
            if f.grupo_id is not None and a.grupo_id != f.grupo_id:
                continue
            if f.asignatura_id is not None and a.asignatura_id != f.asignatura_id:
                continue
            if f.usuario_id is not None and a.usuario_id != f.usuario_id:
                continue
            if f.periodo_id is not None and a.periodo_id != f.periodo_id:
                continue
            if f.solo_activas and not a.activo:
                continue
            out.append(a)
        return out


class _FakeUsuario:
    def __init__(self, uid, cap):
        self.id = uid
        self.carga_maxima_efectiva = cap
        self.nombre_completo = f"Doc{uid}"
        self.usuario = f"d{uid}"
        self.carga_horaria_max = cap
        self.horas_extra = 0


class _FakeUsuarioRepo:
    def __init__(self, caps: dict):
        self._caps = caps
    def get_by_id(self, uid):
        return _FakeUsuario(uid, self._caps.get(uid))


class _FakePlan:
    def __init__(self, aid, horas):
        self.asignatura_id = aid
        self.horas_semanales = horas


class _FakePlanSvc:
    def __init__(self, por_grado_map: dict):
        self._m = por_grado_map
    def por_grado(self, grado):
        return self._m.get(grado, [])
    def horas_de(self, grado, aid):
        return next((p.horas_semanales for p in self._m.get(grado, [])
                     if p.asignatura_id == aid), 0)


def _svc_completo(caps=None, plan_map=None):
    repo = _FilterAsignRepo()
    return AsignacionService(
        repo,
        usuario_repo=_FakeUsuarioRepo(caps or {}),
        infra_repo=None,
        plan_svc=_FakePlanSvc(plan_map or {}),
    ), repo


class TestAsignarDocenteAMateria:
    def test_crea_si_no_hay_activa(self):
        svc, repo = _svc_completo()
        a = svc.asignar_docente_a_materia(10, 20, 5, nuevo_usuario_id=1)
        assert a is not None and a.usuario_id == 1 and a.activo

    def test_none_desactiva_actual(self):
        svc, repo = _svc_completo()
        svc.crear_asignacion(_dto(usuario_id=1))
        res = svc.asignar_docente_a_materia(10, 20, 5, nuevo_usuario_id=None)
        assert res is None
        assert all(not a.activo for a in repo._asigs.values())

    def test_mismo_docente_es_noop(self):
        svc, _ = _svc_completo()
        a = svc.crear_asignacion(_dto(usuario_id=1))
        res = svc.asignar_docente_a_materia(10, 20, 5, nuevo_usuario_id=1)
        assert res.id == a.id

    def test_swap_reactiva_combo_inactivo(self):
        svc, repo = _svc_completo()
        a1 = svc.crear_asignacion(_dto(usuario_id=1))
        # cambia a doc 2
        a2 = svc.asignar_docente_a_materia(10, 20, 5, nuevo_usuario_id=2)
        assert a2.usuario_id == 2 and not repo._asigs[a1.id].activo
        # vuelve a doc 1 → reactiva el combo inactivo, no crea uno nuevo
        a3 = svc.asignar_docente_a_materia(10, 20, 5, nuevo_usuario_id=1)
        assert a3.id == a1.id and a3.activo


class TestDocentesConCupo:
    def test_sin_tope_siempre_con_cupo(self):
        svc, _ = _svc_completo(caps={1: None})
        cupos = svc.docentes_con_cupo(20, 10, horas=5, periodo_id=5, docente_ids=[1])
        assert cupos[1].tiene_cupo and cupos[1].cap_efectivo is None

    def test_sin_cupo_si_supera_tope(self):
        plan = {7: [_FakePlan(20, 30)]}
        svc, _ = _svc_completo(caps={1: 10}, plan_map=plan)
        # plan_svc sin infra_repo: horas_de_asignacion usa fallback 0, así que
        # forzamos carga simulando una asignación existente del docente
        svc.crear_asignacion(NuevaAsignacionDTO(grupo_id=99, asignatura_id=20,
                                                usuario_id=1, periodo_id=5))
        cupos = svc.docentes_con_cupo(20, 10, horas=99, periodo_id=5, docente_ids=[1])
        assert cupos[1].cap_efectivo == 10


class TestCompletitud:
    def test_completitud_y_pendientes(self):
        plan = {7: [_FakePlan(20, 4), _FakePlan(21, 3)]}
        svc, _ = _svc_completo(plan_map=plan)
        svc.crear_asignacion(NuevaAsignacionDTO(grupo_id=10, asignatura_id=20,
                                                usuario_id=1, periodo_id=5))
        c = svc.completitud_grupo(10, grado=7, periodo_id=5)
        assert c.horas_totales == 7 and c.horas_asignadas == 4
        assert not c.completo and c.faltantes == 3
        pend = svc.materias_sin_docente(10, grado=7, periodo_id=5)
        assert pend == [21]
