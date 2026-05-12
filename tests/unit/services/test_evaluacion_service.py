"""Tests unitarios para EvaluacionService."""
from __future__ import annotations

import pytest

from src.domain.models.evaluacion import (
    Actividad, Categoria, EstadoActividad, Nota,
    NuevaCategoriaDTO, ActualizarCategoriaDTO,
    NuevaActividadDTO, PuntosExtra,
    RegistrarNotaDTO, RegistrarNotasMasivasDTO, ResultadoEstudianteDTO,
)
from src.domain.models.dtos import ContextoAcademicoDTO
from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.services.evaluacion_service import EvaluacionService


# ===========================================================================
# Fake
# ===========================================================================

class FakeEvalRepo(IEvaluacionRepository):
    def __init__(self):
        self._cats: dict[int, Categoria] = {}
        self._acts: dict[int, Actividad] = {}
        self._notas: list[Nota] = []
        self._puntos: list[PuntosExtra] = []
        self._next_cat = 1
        self._next_act = 1

    # Categorías
    def guardar_categoria(self, c: Categoria) -> Categoria:
        c = c.model_copy(update={"id": self._next_cat})
        self._next_cat += 1
        self._cats[c.id] = c
        return c

    def actualizar_categoria(self, c: Categoria) -> Categoria:
        self._cats[c.id] = c
        return c

    def eliminar_categoria(self, cat_id: int) -> None:
        self._cats.pop(cat_id, None)

    def get_categoria(self, cat_id: int) -> Categoria | None:
        return self._cats.get(cat_id)

    def listar_categorias(self, asig_id: int, per_id: int) -> list[Categoria]:
        return [c for c in self._cats.values()
                if c.asignacion_id == asig_id and c.periodo_id == per_id]

    def suma_pesos_otras(self, asig_id: int, per_id: int, excluir_id: int | None = None) -> float:
        return sum(
            c.peso for c in self._cats.values()
            if c.asignacion_id == asig_id and c.periodo_id == per_id and c.id != excluir_id
        )

    # Actividades
    def guardar_actividad(self, a: Actividad) -> Actividad:
        a = a.model_copy(update={"id": self._next_act})
        self._next_act += 1
        self._acts[a.id] = a
        return a

    def actualizar_actividad(self, a: Actividad) -> Actividad:
        self._acts[a.id] = a
        return a

    def actualizar_estado_actividad(self, act_id: int, estado: EstadoActividad) -> None:
        a = self._acts[act_id]
        self._acts[act_id] = a.model_copy(update={"estado": estado})

    def eliminar_actividad(self, act_id: int) -> None:
        self._acts.pop(act_id, None)

    def get_actividad(self, act_id: int) -> Actividad | None:
        return self._acts.get(act_id)

    def listar_actividades(self, asig_id: int, per_id: int) -> list[Actividad]:
        return [a for a in self._acts.values()
                if a.asignacion_id == asig_id and a.periodo_id == per_id]

    def listar_actividades_por_categoria(self, cat_id: int) -> list[Actividad]:
        return [a for a in self._acts.values() if a.categoria_id == cat_id]

    def listar_actividades_publicadas(self, asig_id: int, per_id: int) -> list[Actividad]:
        return [a for a in self._acts.values() if a.estado == EstadoActividad.PUBLICADA]

    # Notas
    def guardar_nota(self, n: Nota) -> Nota:
        self._notas.append(n)
        return n

    def guardar_notas_masivas(self, notas: list[Nota]) -> int:
        self._notas.extend(notas)
        return len(notas)

    def get_nota(self, est_id: int, act_id: int) -> Nota | None:
        return None

    def eliminar_nota(self, est_id: int, act_id: int) -> bool:
        return False

    def listar_notas_por_actividad(self, act_id: int) -> list[Nota]:
        return [n for n in self._notas if n.actividad_id == act_id]

    def listar_notas_por_estudiante(self, est_id: int, asig_id: int, per_id: int) -> list[Nota]:
        return [n for n in self._notas if n.estudiante_id == est_id]

    def listar_resultados_grupo(self, asig_id: int, per_id: int) -> list[ResultadoEstudianteDTO]:
        return []

    # Puntos extra
    def guardar_puntos_extra(self, p: PuntosExtra) -> PuntosExtra:
        self._puntos.append(p)
        return p

    def get_puntos_extra(self, est_id: int, per_id: int) -> PuntosExtra | None:
        return None

    def listar_puntos_extra(self, asig_id: int, per_id: int) -> list[PuntosExtra]:
        return []


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> tuple[EvaluacionService, FakeEvalRepo]:
    repo = FakeEvalRepo()
    return EvaluacionService(repo), repo


def _ctx() -> ContextoAcademicoDTO:
    return ContextoAcademicoDTO(
        usuario_id=1, anio_id=1, periodo_id=5, grupo_id=10, asignacion_id=3
    )


def _cat_dto(peso: float = 0.40) -> NuevaCategoriaDTO:
    return NuevaCategoriaDTO(
        asignacion_id=3, periodo_id=5, nombre="Evaluaciones", peso=peso
    )


def _act_dto(cat_id: int = 1) -> NuevaActividadDTO:
    return NuevaActividadDTO(
        asignacion_id=3, periodo_id=5, categoria_id=cat_id,
        nombre="Quiz 1", valor_maximo=100.0,
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestAgregarCategoria:
    def test_agrega_categoria_con_peso_valido(self):
        svc, _ = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(0.40), _ctx())
        assert cat.id is not None
        assert cat.peso == pytest.approx(0.40)

    def test_lanza_si_peso_supera_100(self):
        svc, _ = _make_svc()
        svc.agregar_categoria(_cat_dto(0.70), _ctx())
        with pytest.raises(ValueError, match="100%"):
            svc.agregar_categoria(_cat_dto(0.50), _ctx())

    def test_dos_categorias_distintas(self):
        svc, _ = _make_svc()
        c1 = svc.agregar_categoria(_cat_dto(0.40), _ctx())
        dto2 = NuevaCategoriaDTO(asignacion_id=3, periodo_id=5, nombre="Trabajos", peso=0.35)
        c2 = svc.agregar_categoria(dto2, _ctx())
        assert c1.id != c2.id


class TestEliminarActividad:
    def test_elimina_actividad_en_borrador(self):
        svc, repo = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        assert act.estado == EstadoActividad.BORRADOR
        svc.eliminar_actividad(act.id)  # no lanza

    def test_lanza_si_actividad_cerrada(self):
        svc, repo = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        svc.publicar_actividad(act.id)
        svc.cerrar_actividad(act.id)
        with pytest.raises(ValueError, match="cerrada"):
            svc.eliminar_actividad(act.id)


class TestRegistrarNota:
    def test_lanza_si_actividad_no_acepta_notas(self):
        svc, _ = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        # La actividad está en BORRADOR, no acepta notas
        dto_nota = RegistrarNotaDTO(
            estudiante_id=5, actividad_id=act.id, valor=85.0
        )
        with pytest.raises(ValueError, match="no acepta notas"):
            svc.registrar_nota(dto_nota, _ctx())

    def test_registra_nota_en_actividad_publicada(self):
        svc, repo = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        svc.publicar_actividad(act.id)
        dto_nota = RegistrarNotaDTO(
            estudiante_id=5, actividad_id=act.id, valor=85.0
        )
        nota = svc.registrar_nota(dto_nota, _ctx())
        assert nota.valor == pytest.approx(85.0)


class TestPublicarCerrarActividad:
    def test_flujo_borrador_publicada_cerrada(self):
        svc, _ = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        assert act.estado == EstadoActividad.BORRADOR
        publicada = svc.publicar_actividad(act.id)
        assert publicada.estado == EstadoActividad.PUBLICADA
        cerrada = svc.cerrar_actividad(act.id)
        assert cerrada.estado == EstadoActividad.CERRADA
