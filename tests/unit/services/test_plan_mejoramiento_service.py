"""Tests unitarios de PlanMejoramientoService."""
from __future__ import annotations

import pytest

from src.services.plan_mejoramiento_service import PlanMejoramientoService
from src.domain.models.plan_mejoramiento import (
    ActividadPlan,
    CalificarNotaPlanDTO,
    CerrarPlanEstudianteDTO,
    CortePlan,
    EjecutarCorteDTO,
    EstadoNotaCorte,
    NotaActividadPlan,
    NotaCortePlan,
    NuevaActividadPlanDTO,
)
from src.domain.ports.plan_mejoramiento_repo import IPlanMejoramientoRepository
from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.domain.models.evaluacion import Actividad, Categoria, Nota, EstadoActividad
from src.domain.models.estudiante import Estudiante


# ---------------------------------------------------------------------------
# Helpers de construcción
# ---------------------------------------------------------------------------

def _est(id_: int) -> Estudiante:
    return Estudiante(
        id=id_,
        numero_documento=f"1000000{id_:03d}",
        nombre="Estudiante",
        apellido=f"Apellido{id_}",
    )


def _cat(id_: int, peso: float, asig_id: int = 1, per_id: int = 1) -> Categoria:
    return Categoria(id=id_, nombre=f"Cat{id_}", peso=peso,
                     asignacion_id=asig_id, periodo_id=per_id)


def _act_eval(id_: int, cat_id: int) -> Actividad:
    return Actividad(id=id_, nombre=f"Act{id_}", categoria_id=cat_id)


def _nota_eval(est_id: int, act_id: int, valor: float) -> Nota:
    return Nota(estudiante_id=est_id, actividad_id=act_id, valor=valor)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakePlanRepo(IPlanMejoramientoRepository):
    def __init__(self):
        self._cortes: dict[tuple, CortePlan] = {}
        self._cortes_by_id: dict[int, CortePlan] = {}
        self._notas_corte: dict[tuple, NotaCortePlan] = {}
        self._actividades: dict[int, ActividadPlan] = {}
        self._notas_actividad: dict[tuple, NotaActividadPlan] = {}
        self._next_id = 1

    def guardar_corte(self, c: CortePlan) -> CortePlan:
        c = c.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._cortes[(c.asignacion_id, c.periodo_id)] = c
        self._cortes_by_id[c.id] = c
        return c

    def get_corte(self, asig_id: int, per_id: int) -> CortePlan | None:
        return self._cortes.get((asig_id, per_id))

    def get_corte_by_id(self, cid: int) -> CortePlan | None:
        return self._cortes_by_id.get(cid)

    def guardar_nota_corte(self, n: NotaCortePlan) -> NotaCortePlan:
        n = n.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._notas_corte[(n.corte_id, n.estudiante_id)] = n
        return n

    def get_nota_corte(self, corte_id: int, est_id: int) -> NotaCortePlan | None:
        return self._notas_corte.get((corte_id, est_id))

    def listar_notas_corte(self, corte_id: int) -> list[NotaCortePlan]:
        return [n for n in self._notas_corte.values() if n.corte_id == corte_id]

    def actualizar_nota_corte(self, n: NotaCortePlan) -> NotaCortePlan:
        self._notas_corte[(n.corte_id, n.estudiante_id)] = n
        return n

    def guardar_actividad(self, a: ActividadPlan) -> ActividadPlan:
        a = a.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._actividades[a.id] = a
        return a

    def get_actividad(self, aid: int) -> ActividadPlan | None:
        return self._actividades.get(aid)

    def listar_actividades(self, corte_id: int) -> list[ActividadPlan]:
        return [a for a in self._actividades.values() if a.corte_id == corte_id]

    def suma_pesos_actividades(self, corte_id: int, excluir_id: int | None = None) -> float:
        return sum(
            a.peso for a in self._actividades.values()
            if a.corte_id == corte_id and a.id != excluir_id
        )

    def guardar_nota_actividad(self, n: NotaActividadPlan) -> NotaActividadPlan:
        if n.id is None:
            n = n.model_copy(update={"id": self._next_id})
            self._next_id += 1
        self._notas_actividad[(n.actividad_plan_id, n.estudiante_id)] = n
        return n

    def get_nota_actividad(self, act_id: int, est_id: int) -> NotaActividadPlan | None:
        return self._notas_actividad.get((act_id, est_id))

    def listar_notas_actividad(self, act_id: int) -> list[NotaActividadPlan]:
        return [n for n in self._notas_actividad.values() if n.actividad_plan_id == act_id]

    def listar_notas_por_corte_estudiante(self, corte_id: int, est_id: int) -> list[NotaActividadPlan]:
        act_ids = {a.id for a in self._actividades.values() if a.corte_id == corte_id}
        return [
            n for n in self._notas_actividad.values()
            if n.actividad_plan_id in act_ids and n.estudiante_id == est_id
        ]


class FakeEvalRepo(IEvaluacionRepository):
    """Fake configurable para IEvaluacionRepository."""

    def __init__(
        self,
        categorias: list[Categoria] | None = None,
        actividades: list[Actividad] | None = None,
        notas_por_actividad: dict[int, list[Nota]] | None = None,
        notas_por_estudiante: dict[tuple, list[Nota]] | None = None,
    ):
        self._categorias = categorias or []
        self._actividades = actividades or []
        self._notas_por_actividad = notas_por_actividad or {}
        self._notas_por_estudiante = notas_por_estudiante or {}

    def listar_categorias(self, asignacion_id: int, periodo_id: int) -> list[Categoria]:
        return self._categorias

    def listar_actividades(self, asignacion_id: int, periodo_id: int) -> list[Actividad]:
        return self._actividades

    def listar_notas_por_actividad(self, actividad_id: int) -> list[Nota]:
        return self._notas_por_actividad.get(actividad_id, [])

    def listar_notas_por_estudiante(self, estudiante_id: int, asignacion_id: int, periodo_id: int) -> list[Nota]:
        return self._notas_por_estudiante.get((estudiante_id, asignacion_id, periodo_id), [])

    # -- Stubs para métodos abstractos restantes --

    def get_categoria(self, cat_id):
        return None

    def guardar_categoria(self, categoria):
        return categoria

    def actualizar_categoria(self, categoria):
        return categoria

    def eliminar_categoria(self, cat_id):
        pass

    def suma_pesos_otras(self, asignacion_id, periodo_id, excluir_cat_id=None):
        return 0.0

    def listar_actividades_por_categoria(self, cat_id):
        return []

    def listar_actividades_publicadas(self, asignacion_id, periodo_id, hasta_fecha=None):
        return []

    def get_actividad(self, act_id):
        return None

    def guardar_actividad(self, actividad):
        return actividad

    def actualizar_actividad(self, actividad):
        return actividad

    def actualizar_estado_actividad(self, act_id, estado):
        return True

    def eliminar_actividad(self, act_id):
        pass

    def get_nota(self, estudiante_id, actividad_id):
        return None

    def guardar_nota(self, nota):
        return nota

    def guardar_notas_masivas(self, notas):
        return len(notas)

    def eliminar_nota(self, estudiante_id, actividad_id):
        return False

    def get_puntos_extra(self, estudiante_id, asignacion_id, periodo_id, tipo=None):
        return None

    def listar_puntos_extra(self, asignacion_id, periodo_id):
        return []

    def guardar_puntos_extra(self, pe):
        return pe

    def listar_resultados_grupo(self, grupo_id, asignacion_id, periodo_id):
        return []


class FakeEstRepo(IEstudianteRepository):
    def __init__(self, estudiantes: list[Estudiante]):
        self._ests = {e.id: e for e in estudiantes}

    def listar_por_grupo(self, grupo_id: int, solo_activos: bool = True) -> list[Estudiante]:
        return list(self._ests.values())

    # Stubs para métodos abstractos restantes

    def get_by_id(self, estudiante_id):
        return self._ests.get(estudiante_id)

    def get_by_documento(self, numero_documento):
        return None

    def existe_documento(self, numero_documento):
        return False

    def get_resumen(self, estudiante_id):
        return None

    def listar_filtrado(self, filtro):
        return []

    def listar_resumenes(self, filtro):
        return []

    def contar_por_grupo(self, grupo_id, solo_activos=True):
        return len(self._ests)

    def guardar(self, estudiante):
        return estudiante

    def actualizar(self, estudiante):
        return estudiante

    def actualizar_estado_matricula(self, estudiante_id, estado):
        return True

    def asignar_grupo(self, estudiante_id, grupo_id):
        return True

    def get_piar(self, estudiante_id, anio_id):
        return None

    def listar_piars(self, estudiante_id):
        return []

    def existe_piar(self, estudiante_id, anio_id):
        return False

    def guardar_piar(self, piar):
        return piar

    def actualizar_piar(self, piar):
        return piar


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def _make_svc(
    plan_repo: FakePlanRepo | None = None,
    eval_repo: FakeEvalRepo | None = None,
    est_repo: FakeEstRepo | None = None,
    estudiantes: list[Estudiante] | None = None,
) -> PlanMejoramientoService:
    return PlanMejoramientoService(
        plan_repo=plan_repo or FakePlanRepo(),
        eval_repo=eval_repo or FakeEvalRepo(),
        est_repo=est_repo or FakeEstRepo(estudiantes or []),
    )


def _dto_corte(asig=1, per=1, nota_min=60.0) -> EjecutarCorteDTO:
    return EjecutarCorteDTO(asignacion_id=asig, periodo_id=per, nota_minima_aprobacion=nota_min)


def _setup_corte_con_estudiantes(
    nota_est1: float = 30.0,
    nota_est2: float = 75.0,
    nota_min: float = 60.0,
) -> tuple[FakePlanRepo, FakeEvalRepo, FakeEstRepo, PlanMejoramientoService]:
    """Configura un escenario base con 2 estudiantes, 1 categoría, 1 actividad."""
    cat = _cat(1, 1.0)
    act = _act_eval(10, cat_id=1)
    est1 = _est(1)
    est2 = _est(2)

    notas_por_act = {
        10: [_nota_eval(1, 10, nota_est1), _nota_eval(2, 10, nota_est2)]
    }
    notas_por_est = {
        (1, 1, 1): [_nota_eval(1, 10, nota_est1)],
        (2, 1, 1): [_nota_eval(2, 10, nota_est2)],
    }

    plan_repo = FakePlanRepo()
    eval_repo = FakeEvalRepo(
        categorias=[cat],
        actividades=[act],
        notas_por_actividad=notas_por_act,
        notas_por_estudiante=notas_por_est,
    )
    est_repo = FakeEstRepo([est1, est2])
    svc = PlanMejoramientoService(plan_repo, eval_repo, est_repo)
    return plan_repo, eval_repo, est_repo, svc


# ---------------------------------------------------------------------------
# Tests: TestEjecutarCorte
# ---------------------------------------------------------------------------

class TestEjecutarCorte:
    def test_lanza_si_ya_existe_corte(self):
        plan_repo, eval_repo, est_repo, svc = _setup_corte_con_estudiantes()
        dto = _dto_corte()
        svc.ejecutar_corte(dto, grupo_id=1)
        with pytest.raises(ValueError, match="Ya existe un corte"):
            svc.ejecutar_corte(dto, grupo_id=1)

    def test_lanza_si_no_hay_categorias(self):
        plan_repo = FakePlanRepo()
        eval_repo = FakeEvalRepo(categorias=[], actividades=[])
        est_repo = FakeEstRepo([_est(1)])
        svc = PlanMejoramientoService(plan_repo, eval_repo, est_repo)
        with pytest.raises(ValueError, match="categor"):
            svc.ejecutar_corte(_dto_corte(), grupo_id=1)

    def test_lanza_si_no_hay_notas_registradas(self):
        """Categorías configuradas pero sin ninguna nota → ValueError."""
        cat = _cat(1, 1.0)
        act = _act_eval(10, cat_id=1)
        plan_repo = FakePlanRepo()
        eval_repo = FakeEvalRepo(
            categorias=[cat],
            actividades=[act],
            notas_por_actividad={10: []},  # sin notas
        )
        est_repo = FakeEstRepo([_est(1)])
        svc = PlanMejoramientoService(plan_repo, eval_repo, est_repo)
        with pytest.raises(ValueError, match="notas"):
            svc.ejecutar_corte(_dto_corte(), grupo_id=1)

    def test_crea_corte_y_notas_para_todos(self):
        plan_repo, _, _, svc = _setup_corte_con_estudiantes()
        corte, notas = svc.ejecutar_corte(_dto_corte(), grupo_id=1)
        assert corte.id is not None
        assert len(notas) == 2

    def test_clasifica_en_plan_correctamente(self):
        """Est1 nota baja (30) → EN_PLAN; Est2 nota alta (75) → SIN_PLAN."""
        plan_repo, _, _, svc = _setup_corte_con_estudiantes(
            nota_est1=30.0, nota_est2=75.0, nota_min=60.0
        )
        corte, notas = svc.ejecutar_corte(_dto_corte(nota_min=60.0), grupo_id=1)
        # umbral = 1.0 * 60.0 = 60.0
        estados = {n.estudiante_id: n.estado for n in notas}
        assert estados[1] == EstadoNotaCorte.EN_PLAN
        assert estados[2] == EstadoNotaCorte.SIN_PLAN


# ---------------------------------------------------------------------------
# Tests: TestAgregarActividad
# ---------------------------------------------------------------------------

class TestAgregarActividad:
    def _setup_con_corte(self) -> tuple[FakePlanRepo, PlanMejoramientoService, int]:
        """Devuelve repo, svc, corte_id con un estudiante EN_PLAN."""
        plan_repo, _, _, svc = _setup_corte_con_estudiantes(nota_est1=30.0, nota_est2=30.0)
        corte, _ = svc.ejecutar_corte(_dto_corte(), grupo_id=1)
        return plan_repo, svc, corte.id

    def test_lanza_si_suma_pesos_supera_1(self):
        plan_repo, svc, corte_id = self._setup_con_corte()
        # Agregar primera actividad con peso 0.7
        dto1 = NuevaActividadPlanDTO(
            corte_id=corte_id, asignacion_id=1, periodo_id=1,
            nombre="Act1", peso=0.7,
        )
        svc.agregar_actividad(dto1)
        # Agregar segunda con peso 0.4 → suma 1.1 → ValueError
        dto2 = NuevaActividadPlanDTO(
            corte_id=corte_id, asignacion_id=1, periodo_id=1,
            nombre="Act2", peso=0.4,
        )
        with pytest.raises(ValueError, match="superaría"):
            svc.agregar_actividad(dto2)

    def test_crea_notas_vacias_para_en_plan(self):
        plan_repo, svc, corte_id = self._setup_con_corte()
        dto = NuevaActividadPlanDTO(
            corte_id=corte_id, asignacion_id=1, periodo_id=1,
            nombre="Taller1", peso=0.5,
        )
        actividad = svc.agregar_actividad(dto)
        # Ambos estudiantes están EN_PLAN → deben tener nota vacía
        notas = plan_repo.listar_notas_actividad(actividad.id)
        assert len(notas) == 2
        assert all(n.valor is None for n in notas)


# ---------------------------------------------------------------------------
# Tests: TestCalificarNota
# ---------------------------------------------------------------------------

class TestCalificarNota:
    def _setup_con_actividad(self) -> tuple[FakePlanRepo, PlanMejoramientoService, int, int]:
        """Devuelve repo, svc, actividad_plan_id, corte_id."""
        plan_repo, _, _, svc = _setup_corte_con_estudiantes(nota_est1=30.0, nota_est2=30.0)
        corte, _ = svc.ejecutar_corte(_dto_corte(), grupo_id=1)
        dto = NuevaActividadPlanDTO(
            corte_id=corte.id, asignacion_id=1, periodo_id=1,
            nombre="Expo", peso=1.0,
        )
        actividad = svc.agregar_actividad(dto)
        return plan_repo, svc, actividad.id, corte.id

    def test_lanza_si_nota_no_existe(self):
        plan_repo, svc, act_id, corte_id = self._setup_con_actividad()
        dto = CalificarNotaPlanDTO(valor=80.0)
        with pytest.raises(ValueError, match="no tiene asignada"):
            svc.calificar_nota(act_id, estudiante_id=999, dto=dto)

    def test_lanza_si_plan_ya_cerrado(self):
        plan_repo, svc, act_id, corte_id = self._setup_con_actividad()
        # Calificar al est1 primero
        svc.calificar_nota(act_id, estudiante_id=1, dto=CalificarNotaPlanDTO(valor=80.0))
        # Cerrar el plan del est1 como aprobado
        cerrar_dto = CerrarPlanEstudianteDTO(
            estudiante_id=1, corte_id=corte_id, aprobado=True
        )
        svc.cerrar_plan_estudiante(cerrar_dto)
        # Intentar calificar de nuevo → ValueError
        with pytest.raises(ValueError, match="ya fue cerrado"):
            svc.calificar_nota(act_id, estudiante_id=1, dto=CalificarNotaPlanDTO(valor=90.0))

    def test_califica_correctamente(self):
        plan_repo, svc, act_id, corte_id = self._setup_con_actividad()
        dto = CalificarNotaPlanDTO(valor=75.0)
        nota = svc.calificar_nota(act_id, estudiante_id=1, dto=dto)
        assert nota.valor == 75.0


# ---------------------------------------------------------------------------
# Tests: TestCerrarPlanEstudiante
# ---------------------------------------------------------------------------

class TestCerrarPlanEstudiante:
    def _setup_listo_para_cierre(self) -> tuple[FakePlanRepo, PlanMejoramientoService, int, int]:
        """Retorna repo, svc, corte_id, act_id con est1 EN_PLAN y calificado."""
        plan_repo, _, _, svc = _setup_corte_con_estudiantes(nota_est1=30.0, nota_est2=30.0)
        corte, _ = svc.ejecutar_corte(_dto_corte(), grupo_id=1)
        dto_act = NuevaActividadPlanDTO(
            corte_id=corte.id, asignacion_id=1, periodo_id=1,
            nombre="Recuperacion", peso=1.0,
        )
        actividad = svc.agregar_actividad(dto_act)
        # Calificar a ambos estudiantes
        svc.calificar_nota(actividad.id, 1, CalificarNotaPlanDTO(valor=70.0))
        svc.calificar_nota(actividad.id, 2, CalificarNotaPlanDTO(valor=55.0))
        return plan_repo, svc, corte.id, actividad.id

    def test_lanza_si_no_existe_nota_corte(self):
        plan_repo, svc, corte_id, _ = self._setup_listo_para_cierre()
        dto = CerrarPlanEstudianteDTO(
            estudiante_id=999, corte_id=corte_id, aprobado=True
        )
        with pytest.raises(ValueError, match="No existe nota de corte"):
            svc.cerrar_plan_estudiante(dto)

    def test_lanza_si_ya_cerrado(self):
        plan_repo, svc, corte_id, _ = self._setup_listo_para_cierre()
        dto = CerrarPlanEstudianteDTO(
            estudiante_id=1, corte_id=corte_id, aprobado=True
        )
        svc.cerrar_plan_estudiante(dto)
        with pytest.raises(ValueError, match="ya fue cerrado"):
            svc.cerrar_plan_estudiante(dto)

    def test_lanza_si_sin_plan(self):
        """Un estudiante SIN_PLAN no puede ser cerrado."""
        plan_repo = FakePlanRepo()
        cat = _cat(1, 1.0)
        act = _act_eval(10, cat_id=1)
        # est1=30 → EN_PLAN, est2=80 → SIN_PLAN
        notas_por_act = {10: [_nota_eval(1, 10, 30.0), _nota_eval(2, 10, 80.0)]}
        notas_por_est = {
            (1, 1, 1): [_nota_eval(1, 10, 30.0)],
            (2, 1, 1): [_nota_eval(2, 10, 80.0)],
        }
        eval_repo = FakeEvalRepo(
            categorias=[cat], actividades=[act],
            notas_por_actividad=notas_por_act,
            notas_por_estudiante=notas_por_est,
        )
        est_repo = FakeEstRepo([_est(1), _est(2)])
        svc = PlanMejoramientoService(plan_repo, eval_repo, est_repo)
        corte, _ = svc.ejecutar_corte(_dto_corte(), grupo_id=1)
        # est2 está SIN_PLAN
        dto = CerrarPlanEstudianteDTO(
            estudiante_id=2, corte_id=corte.id, aprobado=True
        )
        with pytest.raises(ValueError, match="no está en plan"):
            svc.cerrar_plan_estudiante(dto)

    def test_aprobado_congela_nota_minima(self):
        """aprobado=True → nota_definitiva = peso_reg * nota_minima."""
        plan_repo, svc, corte_id, _ = self._setup_listo_para_cierre()
        dto = CerrarPlanEstudianteDTO(
            estudiante_id=1, corte_id=corte_id, aprobado=True
        )
        resultado = svc.cerrar_plan_estudiante(dto)
        # peso_registrado = 1.0, nota_minima = 60.0 → 60.0
        assert resultado.estado == EstadoNotaCorte.APROBADO
        assert resultado.nota_definitiva_plan == pytest.approx(60.0)

    def test_reprobado_usa_nota_calculada(self):
        """aprobado=False → nota_definitiva = promedio ponderado de actividades del plan."""
        plan_repo, svc, corte_id, act_id = self._setup_listo_para_cierre()
        # est1 calificado con 70.0 en actividad peso=1.0 → nota_plan = 70.0
        dto = CerrarPlanEstudianteDTO(
            estudiante_id=1, corte_id=corte_id, aprobado=False
        )
        resultado = svc.cerrar_plan_estudiante(dto)
        assert resultado.estado == EstadoNotaCorte.REPROBADO
        assert resultado.nota_definitiva_plan == pytest.approx(70.0)
