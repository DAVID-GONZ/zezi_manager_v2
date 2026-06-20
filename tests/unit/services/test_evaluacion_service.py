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

    def suma_pesos_otras(self, asig_id: int, per_id: int, excluir_cat_id: int | None = None) -> float:
        return sum(
            c.peso for c in self._cats.values()
            if c.asignacion_id == asig_id and c.periodo_id == per_id and c.id != excluir_cat_id
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
        with pytest.raises(ValueError, match="disponible|100%"):
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

    def test_reabrir_actividad_cerrada(self):
        svc, _ = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        svc.publicar_actividad(act.id)
        svc.cerrar_actividad(act.id)
        reabierta = svc.reabrir_actividad(act.id)
        assert reabierta.estado == EstadoActividad.PUBLICADA

    def test_lanza_al_reabrir_no_cerrada(self):
        svc, _ = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        svc.publicar_actividad(act.id)
        with pytest.raises(ValueError, match="cerrada"):
            svc.reabrir_actividad(act.id)


class TestActualizarCategoria:
    def test_actualiza_nombre_y_peso(self):
        svc, _ = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(0.30), _ctx())
        dto = ActualizarCategoriaDTO(nombre="Trabajos", peso=0.25)
        actualizada = svc.actualizar_categoria(cat.id, dto)
        assert actualizada.nombre == "Trabajos"
        assert actualizada.peso == pytest.approx(0.25)

    def test_lanza_si_nuevo_peso_supera_100(self):
        svc, _ = _make_svc()
        c1 = svc.agregar_categoria(_cat_dto(0.60), _ctx())
        dto2 = NuevaCategoriaDTO(asignacion_id=3, periodo_id=5, nombre="B", peso=0.30)
        c2 = svc.agregar_categoria(dto2, _ctx())
        # Intentar subir c2 a 0.50 haría 0.60 + 0.50 = 1.10
        with pytest.raises(ValueError, match="disponible|100%"):
            svc.actualizar_categoria(c2.id, ActualizarCategoriaDTO(peso=0.50))

    def test_peso_dto_rechaza_escala_incorrecta(self):
        with pytest.raises(ValueError):
            ActualizarCategoriaDTO(peso=50.0)  # 50.0 > 1.0 → debe fallar


class TestRegistrarNotasMasivas:
    def test_to_notas_genera_entidades(self):
        dto = RegistrarNotasMasivasDTO(
            actividad_id=1,
            notas=[
                RegistrarNotaDTO(estudiante_id=1, actividad_id=1, valor=80.0),
                RegistrarNotaDTO(estudiante_id=2, actividad_id=1, valor=90.0),
            ],
        )
        notas = dto.to_notas(usuario_registro_id=99)
        assert len(notas) == 2
        assert all(n.actividad_id == 1 for n in notas)
        assert all(n.usuario_registro_id == 99 for n in notas)

    def test_registrar_masivo_en_actividad_publicada(self):
        svc, repo = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        svc.publicar_actividad(act.id)
        dto = RegistrarNotasMasivasDTO(
            actividad_id=act.id,
            notas=[
                RegistrarNotaDTO(estudiante_id=1, actividad_id=act.id, valor=75.0),
                RegistrarNotaDTO(estudiante_id=2, actividad_id=act.id, valor=85.0),
            ],
        )
        n = svc.registrar_notas_masivas(dto, _ctx())
        assert n == 2

    def test_masivo_lanza_si_actividad_no_publicada(self):
        svc, _ = _make_svc()
        cat = svc.agregar_categoria(_cat_dto(), _ctx())
        act = svc.agregar_actividad(_act_dto(cat.id))
        dto = RegistrarNotasMasivasDTO(
            actividad_id=act.id,
            notas=[RegistrarNotaDTO(estudiante_id=1, actividad_id=act.id, valor=70.0)],
        )
        with pytest.raises(ValueError, match="no acepta notas"):
            svc.registrar_notas_masivas(dto, _ctx())


class TestCalculadorNotas:
    """Verifica que el cálculo de definitiva sea correcto."""

    def _make_cat(self, cat_id: int, peso: float) -> Categoria:
        return Categoria(
            id=cat_id, nombre=f"Cat{cat_id}", peso=peso,
            asignacion_id=3, periodo_id=5,
        )

    def _make_act(self, act_id: int, cat_id: int) -> "Actividad":
        return Actividad(
            id=act_id, nombre=f"Act{act_id}", categoria_id=cat_id,
            asignacion_id=3, periodo_id=5, valor_maximo=100.0,
            estado=EstadoActividad.PUBLICADA,
        )

    def test_definitiva_con_dict(self):
        from src.domain.models.evaluacion import CalculadorNotas
        cats = [self._make_cat(1, 0.60), self._make_cat(2, 0.40)]
        acts = [self._make_act(1, 1), self._make_act(2, 2)]
        # Cat1: act1=80 → promedio 80, Cat2: act2=100 → promedio 100
        # Definitiva = 80*0.60 + 100*0.40 = 48 + 40 = 88
        nota_map = {1: 80.0, 2: 100.0}
        assert CalculadorNotas.calcular_definitiva(nota_map, acts, cats) == pytest.approx(88.0)

    def test_definitiva_con_lista_nota(self):
        from src.domain.models.evaluacion import CalculadorNotas
        cats = [self._make_cat(1, 1.0)]
        acts = [self._make_act(1, 1), self._make_act(2, 1)]
        # Ambas actividades: act1=60, act2=80 → promedio 70
        notas = [
            Nota(estudiante_id=1, actividad_id=1, valor=60.0),
            Nota(estudiante_id=1, actividad_id=2, valor=80.0),
        ]
        assert CalculadorNotas.calcular_definitiva(notas, acts, cats) == pytest.approx(70.0)

    def test_sin_notas_cuenta_como_cero(self):
        from src.domain.models.evaluacion import CalculadorNotas
        cats = [self._make_cat(1, 1.0)]
        acts = [self._make_act(1, 1)]
        assert CalculadorNotas.calcular_definitiva({}, acts, cats) == pytest.approx(0.0)

    def test_sin_categorias_retorna_cero(self):
        from src.domain.models.evaluacion import CalculadorNotas
        assert CalculadorNotas.calcular_definitiva({}, [], []) == pytest.approx(0.0)


# ===========================================================================
# Group 6c — agregador planilla_completa (una sola llamada)
# ===========================================================================

class _AggRepo(FakeEvalRepo):
    """Fake con resultados de grupo y puntos extra para planilla_completa."""
    def __init__(self, resultados, puntos):
        super().__init__()
        self._res = resultados
        self._pe = puntos

    def listar_resultados_grupo(self, grupo_id, asig_id, per_id):
        return self._res

    def listar_puntos_extra(self, asig_id, per_id):
        return self._pe


def test_planilla_completa_agrega_todo():
    res = [ResultadoEstudianteDTO(estudiante_id=1, nombre_completo="Ana", notas={})]
    pe = [PuntosExtra(estudiante_id=1, asignacion_id=3, periodo_id=5, positivos=2)]
    svc = EvaluacionService(_AggRepo(res, pe))
    out = svc.planilla_completa(grupo_id=10, asignacion_id=3, periodo_id=5)
    assert out.planilla == res
    assert out.categorias == []
    assert out.actividades == []
    assert 1 in out.puntos_extra
