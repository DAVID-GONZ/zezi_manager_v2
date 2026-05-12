"""Tests unitarios para CierreService."""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from src.domain.models.cierre import (
    CierreAnio, CierrePeriodo, DecidirPromocionDTO,
    EstadoPromocion, PromocionAnual,
)
from src.domain.models.evaluacion import Actividad, Categoria, Nota
from src.domain.models.configuracion import NivelDesempeno
from src.domain.models.dtos import ContextoAcademicoDTO, DashboardMetricsDTO
from src.domain.models.estudiante import Estudiante
from src.domain.models.periodo import Periodo

from src.domain.ports.cierre_repo import ICierreRepository
from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.ports.estudiante_repo import IEstudianteRepository

from src.domain.models.piar import PIAR
from src.domain.models.estudiante import FiltroEstudiantesDTO, EstudianteResumenDTO

from src.services.cierre_service import CierreService


# ===========================================================================
# Fakes
# ===========================================================================

class FakeCierreRepo(ICierreRepository):
    def __init__(self):
        self._cierres_per: dict[tuple, CierrePeriodo] = {}
        self._cierres_anio: dict[tuple, CierreAnio] = {}
        self._promociones: dict[tuple, PromocionAnual] = {}
        self._next_id = 1

    def guardar_cierre_periodo(self, c: CierrePeriodo) -> CierrePeriodo:
        c = c.model_copy(update={"id": self._next_id})
        self._next_id += 1
        key = (c.estudiante_id, c.asignacion_id, c.periodo_id)
        self._cierres_per[key] = c
        return c

    def get_cierre_periodo(self, est_id: int, asig_id: int, per_id: int) -> CierrePeriodo | None:
        return self._cierres_per.get((est_id, asig_id, per_id))

    def listar_cierres_periodo_por_estudiante(self, est_id: int, periodo_id=None) -> list[CierrePeriodo]:
        return [c for k, c in self._cierres_per.items() if k[0] == est_id]

    def guardar_cierre_anio(self, c: CierreAnio) -> CierreAnio:
        c = c.model_copy(update={"id": self._next_id})
        self._next_id += 1
        key = (c.estudiante_id, c.asignacion_id, c.anio_id)
        self._cierres_anio[key] = c
        return c

    def get_cierre_anio(self, est_id: int, asig_id: int, anio_id: int) -> CierreAnio | None:
        return self._cierres_anio.get((est_id, asig_id, anio_id))

    def listar_cierres_anio_por_estudiante(self, est_id: int, anio_id: int) -> list[CierreAnio]:
        return [c for k, c in self._cierres_anio.items() if k[0] == est_id]

    def guardar_promocion(self, p: PromocionAnual) -> PromocionAnual:
        p = p.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._promociones[(p.estudiante_id, p.anio_id)] = p
        return p

    def get_promocion(self, est_id: int, anio_id: int) -> PromocionAnual | None:
        return self._promociones.get((est_id, anio_id))

    def actualizar_promocion(self, p: PromocionAnual) -> PromocionAnual:
        self._promociones[(p.estudiante_id, p.anio_id)] = p
        return p

    def listar_promociones(self, anio_id: int, grupo_id=None) -> list[PromocionAnual]:
        return list(self._promociones.values())


class FakeEvalRepo(IEvaluacionRepository):
    def __init__(self, notas: list[Nota] = None):
        self._notas = notas or []

    def listar_categorias(self, asig_id, per_id) -> list[Categoria]:
        return []

    def listar_actividades(self, asig_id, per_id) -> list[Actividad]:
        return []

    def listar_notas_por_estudiante(self, est_id, asig_id, per_id) -> list[Nota]:
        return [n for n in self._notas if n.estudiante_id == est_id]

    # All other required abstract methods as no-ops
    def guardar_categoria(self, c): return c
    def actualizar_categoria(self, c): return c
    def eliminar_categoria(self, cid): pass
    def get_categoria(self, cid): return None
    def suma_pesos_otras(self, a, p, excluir_id=None): return 0.0
    def guardar_actividad(self, a): return a
    def actualizar_actividad(self, a): return a
    def actualizar_estado_actividad(self, aid, estado): pass
    def eliminar_actividad(self, aid): pass
    def get_actividad(self, aid): return None
    def listar_actividades_por_categoria(self, cid): return []
    def listar_actividades_publicadas(self, asig, per): return []
    def guardar_nota(self, n): return n
    def guardar_notas_masivas(self, notas): return len(notas)
    def get_nota(self, eid, aid): return None
    def eliminar_nota(self, eid, aid): return False
    def listar_notas_por_actividad(self, aid): return []
    def listar_resultados_grupo(self, asig, per): return []
    def guardar_puntos_extra(self, p): return p
    def get_puntos_extra(self, eid, per): return None
    def listar_puntos_extra(self, asig, per): return []


class FakePeriodoRepo(IPeriodoRepository):
    def __init__(self, periodos: list[Periodo]):
        self._periodos = {p.id: p for p in periodos}

    def get_by_id(self, pid): return self._periodos.get(pid)
    def listar_por_anio(self, anio_id): return list(self._periodos.values())
    def suma_pesos_otros(self, anio_id, excluir_id=None): return 0.0
    def get_activo(self, anio_id): return None
    def get_por_numero(self, anio_id, num): return None
    def guardar(self, p): return p
    def actualizar(self, p): return p
    def cerrar(self, pid): return None
    def activar(self, pid): pass
    def desactivar(self, pid): pass
    def guardar_hito(self, h): return h
    def get_hito(self, hid): return None
    def actualizar_hito(self, h): return h
    def eliminar_hito(self, hid): return False
    def listar_hitos(self, pid): return []
    def listar_hitos_proximos(self, dias=7): return []


class FakeConfigRepo(IConfiguracionRepository):
    def get_activa(self): return None
    def get_by_id(self, anio_id): return None
    def get_by_anio(self, anio): return None
    def listar(self): return []
    def guardar(self, c): return c
    def actualizar(self, c): return c
    def activar(self, anio_id): pass
    def listar_niveles(self, anio_id): return []
    def get_nivel(self, nid): return None
    def guardar_nivel(self, n): return n
    def actualizar_nivel(self, n): return n
    def eliminar_nivel(self, nid): return False
    def reemplazar_niveles(self, anio_id, niveles): return niveles
    def clasificar_nota(self, nota, anio_id): return None
    def get_criterios(self, anio_id): return None
    def guardar_criterios(self, c): return c
    def get_numero_periodos(self, anio_id): return 4
    def guardar_numero_periodos(self, anio_id, numero, pesos_iguales=True): pass


class FakeEstudianteRepo(IEstudianteRepository):
    def __init__(self, estudiantes: list[Estudiante] = None):
        self._ests = {e.id: e for e in (estudiantes or [])}

    def listar_por_grupo(self, grupo_id, solo_activos=True): return list(self._ests.values())
    def get_by_id(self, eid): return self._ests.get(eid)
    def guardar(self, e): return e
    def actualizar(self, e): return e
    def actualizar_estado_matricula(self, eid, estado): pass
    def get_by_documento(self, doc): return None
    def existe_documento(self, doc): return False
    def asignar_grupo(self, eid, grupo_id): pass
    def listar_filtrado(self, filtro): return []
    def listar_resumenes(self, filtro): return []
    def contar_por_grupo(self, grupo_id): return 0
    def get_resumen(self, eid): return None
    def existe_piar(self, eid, anio_id): return False
    def guardar_piar(self, p): return p
    def get_piar(self, eid, anio_id): return None
    def actualizar_piar(self, p): return p
    def listar_piars(self, eid): return []


# ===========================================================================
# Helpers
# ===========================================================================

def _make_periodo(pid: int, anio_id: int, numero: int, cerrado: bool = False) -> Periodo:
    from datetime import datetime
    p = Periodo(
        id=pid, anio_id=anio_id, numero=numero,
        nombre=f"Periodo {numero}",
        peso_porcentual=25.0,
    )
    if cerrado:
        p = p.cerrar(datetime.now())
        p = p.model_copy(update={"id": pid})
    return p


def _make_estudiante(eid: int) -> Estudiante:
    return Estudiante(
        id=eid, numero_documento=f"DOC{eid}",
        nombre="Test", apellido="User",
    )


def _ctx(anio_id: int = 1) -> ContextoAcademicoDTO:
    return ContextoAcademicoDTO(
        usuario_id=1, anio_id=anio_id, periodo_id=10, grupo_id=5
    )


def _make_svc(periodos: list[Periodo], estudiantes: list[Estudiante]) -> tuple[CierreService, FakeCierreRepo]:
    cierre_repo = FakeCierreRepo()
    eval_repo = FakeEvalRepo()
    periodo_repo = FakePeriodoRepo(periodos)
    config_repo = FakeConfigRepo()
    est_repo = FakeEstudianteRepo(estudiantes)
    svc = CierreService(
        cierre_repo=cierre_repo,
        evaluacion_repo=eval_repo,
        periodo_repo=periodo_repo,
        config_repo=config_repo,
        estudiante_repo=est_repo,
    )
    return svc, cierre_repo


# ===========================================================================
# Tests
# ===========================================================================

class TestCerrarPeriodo:
    def test_lanza_si_periodo_ya_cerrado(self):
        periodo = _make_periodo(10, 1, 1, cerrado=True)
        svc, _ = _make_svc([periodo], [_make_estudiante(1)])
        with pytest.raises(ValueError, match="cerrado"):
            svc.cerrar_periodo(3, 10, _ctx())

    def test_genera_cierre_por_estudiante(self):
        periodo = _make_periodo(10, 1, 1, cerrado=False)
        est = _make_estudiante(1)
        svc, cierre_repo = _make_svc([periodo], [est])
        cierres = svc.cerrar_periodo(asignacion_id=3, periodo_id=10, ctx=_ctx())
        assert len(cierres) == 1
        assert cierres[0].estudiante_id == 1

    def test_lanza_si_periodo_no_existe(self):
        svc, _ = _make_svc([], [])
        with pytest.raises(ValueError, match="no existe"):
            svc.cerrar_periodo(3, 999, _ctx())


class TestCerrarAnio:
    def test_lanza_si_hay_periodos_abiertos(self):
        p_abierto = _make_periodo(10, 1, 1, cerrado=False)
        svc, _ = _make_svc([p_abierto], [_make_estudiante(1)])
        with pytest.raises(ValueError, match="abiertos"):
            svc.cerrar_anio(grupo_id=5, anio_id=1, ctx=_ctx())

    def test_cierra_anio_con_todos_periodos_cerrados(self):
        p1 = _make_periodo(10, 1, 1, cerrado=True)
        p2 = _make_periodo(11, 1, 2, cerrado=True)
        est = _make_estudiante(1)
        svc, cierre_repo = _make_svc([p1, p2], [est])
        cierres = svc.cerrar_anio(grupo_id=5, anio_id=1, ctx=_ctx())
        assert isinstance(cierres, list)


class TestDecidirPromocion:
    def test_lanza_si_no_hay_promocion_previa(self):
        svc, _ = _make_svc([], [])
        dto = DecidirPromocionDTO(estado=EstadoPromocion.PROMOVIDO)
        with pytest.raises(ValueError, match="cierre de año"):
            svc.decidir_promocion(est_id=1, anio_id=1, dto=dto)

    def test_decide_promocion_correctamente(self):
        p1 = _make_periodo(10, 1, 1, cerrado=True)
        est = _make_estudiante(1)
        svc, cierre_repo = _make_svc([p1], [est])
        # Crear la promoción directamente
        prom = cierre_repo.guardar_promocion(PromocionAnual(estudiante_id=1, anio_id=1))
        dto = DecidirPromocionDTO(estado=EstadoPromocion.PROMOVIDO, observacion="Sin novedades")
        resultado = svc.decidir_promocion(est_id=1, anio_id=1, dto=dto)
        assert resultado.estado == EstadoPromocion.PROMOVIDO
