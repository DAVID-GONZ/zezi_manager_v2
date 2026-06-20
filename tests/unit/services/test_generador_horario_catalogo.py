"""
Tests unitarios para los helpers de capa-de-interfaz movidos al servicio:

  - GeneradorHorarioService.catalogo_pesos()      (catálogo de pesos del motor)
  - GeneradorHorarioService.plantilla_generable() (inspección de dominio)
  - InfraestructuraService.construir_restricciones() (payload de restricciones)

Estos métodos extraen lógica de dominio que antes vivía en
src/interface/pages/academico/horarios_hub.py (R4/R2).
"""
from __future__ import annotations

from types import SimpleNamespace

from src.domain.models.infraestructura import Franja, PlantillaFranja
from src.services.generador_horario_service import (
    PESOS_AVANZADOS,
    PESOS_PRINCIPALES,
    GeneradorHorarioService,
)
from src.services.infraestructura_service import InfraestructuraService


PLANTILLA_ID = 7


# ===========================================================================
# Fakes mínimos
# ===========================================================================

class _FakeInfraRepo:
    """Repo de infraestructura mínimo: solo lo que usa plantilla_generable."""

    def __init__(self, plantilla=None, franjas=None):
        self._plantilla = plantilla
        self._franjas = list(franjas or [])

    def get_plantilla_franja(self, plantilla_id):
        if self._plantilla is None:
            return None
        if getattr(self._plantilla, "id", None) == plantilla_id:
            return self._plantilla
        # Permite buscar por id de PlantillaFranja con id None en tests simples.
        return self._plantilla

    def listar_franjas(self, plantilla_id):
        return list(self._franjas)


def _gen_service(plantilla=None, franjas=None) -> GeneradorHorarioService:
    return GeneradorHorarioService(
        infra_repo=_FakeInfraRepo(plantilla, franjas),
        asignacion_repo=None,
        usuario_repo=None,
        horario_service=None,
        infraestructura_service=None,
        plan_svc=None,
    )


def _franja(orden, tipo="lectiva"):
    return Franja(
        id=orden, plantilla_id=PLANTILLA_ID, orden=orden,
        hora_inicio="07:00", hora_fin="07:55", tipo=tipo,
    )


def _plantilla(dias=("Lunes", "Martes")):
    return PlantillaFranja(
        id=PLANTILLA_ID, nombre="Plantilla Test", jornada="UNICA",
        dias_activos=list(dias),
    )


# ===========================================================================
# catalogo_pesos
# ===========================================================================

def test_catalogo_pesos_estructura():
    cat = GeneradorHorarioService.catalogo_pesos()
    assert set(cat.keys()) == {"principales", "avanzados"}
    assert cat["principales"] == list(PESOS_PRINCIPALES)
    assert cat["avanzados"] == list(PESOS_AVANZADOS)


def test_catalogo_pesos_claves_y_labels_exactos():
    cat = GeneradorHorarioService.catalogo_pesos()
    principales = [(k, lbl) for k, lbl, _ in cat["principales"]]
    avanzados = [(k, lbl) for k, lbl, _ in cat["avanzados"]]
    assert principales == [
        ("huecos", "Evitar huecos"),
        ("distribucion", "Repartir en la semana"),
        ("compactacion", "Compactar al docente"),
    ]
    assert avanzados == [
        ("balance_diario", "Equilibrar horas por día"),
        ("franja_preferida", "Respetar franja preferida"),
        ("dia_libre", "Dar un día libre"),
        ("hueco_comun", "Proteger franja de reunión"),
    ]


def test_catalogo_pesos_devuelve_copias():
    cat1 = GeneradorHorarioService.catalogo_pesos()
    cat1["principales"].append(("x", "y", "z"))
    cat2 = GeneradorHorarioService.catalogo_pesos()
    assert len(cat2["principales"]) == len(PESOS_PRINCIPALES)


# ===========================================================================
# plantilla_generable
# ===========================================================================

def test_plantilla_generable_sin_id():
    ok, motivo = _gen_service().plantilla_generable(None)
    assert ok is False
    assert "plantilla asignada" in motivo


def test_plantilla_generable_plantilla_inexistente():
    svc = _gen_service(plantilla=None)
    ok, motivo = svc.plantilla_generable(PLANTILLA_ID)
    assert ok is False
    assert "ya no existe" in motivo


def test_plantilla_generable_sin_dias_activos():
    # dias_activos vacío no es construible vía PlantillaFranja; se usa un stub
    # para ejercitar la rama defensiva del servicio.
    stub = SimpleNamespace(id=PLANTILLA_ID, dias_activos=[])
    svc = _gen_service(plantilla=stub, franjas=[_franja(1)])
    ok, motivo = svc.plantilla_generable(PLANTILLA_ID)
    assert ok is False
    assert "días activos" in motivo


def test_plantilla_generable_sin_franjas_lectivas():
    svc = _gen_service(
        plantilla=_plantilla(),
        franjas=[_franja(1, tipo="descanso")],
    )
    ok, motivo = svc.plantilla_generable(PLANTILLA_ID)
    assert ok is False
    assert "lectivas" in motivo


def test_plantilla_generable_ok():
    svc = _gen_service(
        plantilla=_plantilla(),
        franjas=[_franja(1), _franja(2, tipo="descanso")],
    )
    ok, motivo = svc.plantilla_generable(PLANTILLA_ID)
    assert ok is True
    assert motivo == ""


# ===========================================================================
# construir_restricciones
# ===========================================================================

class _FakeInfraRepoVacio:
    pass


def _infra_service() -> InfraestructuraService:
    return InfraestructuraService(repo=_FakeInfraRepoVacio())


def test_construir_restricciones_default_vacio():
    # Rango default (min=0, max=8) → sin restricción.
    assert _infra_service().construir_restricciones(0, 8, "preferente") == {}


def test_construir_restricciones_min_mayor_cero():
    res = _infra_service().construir_restricciones(2, 8, "preferente")
    assert res == {"min_max_diario": {"modo": "preferente", "min": 2, "max": 8}}


def test_construir_restricciones_max_menor_ocho():
    res = _infra_service().construir_restricciones(0, 6, "estricta")
    assert res == {"min_max_diario": {"modo": "estricta", "min": 0, "max": 6}}


def test_construir_restricciones_coerciona_a_int():
    res = _infra_service().construir_restricciones(1.0, 7.0, "preferente")
    assert res["min_max_diario"]["min"] == 1
    assert res["min_max_diario"]["max"] == 7
    assert isinstance(res["min_max_diario"]["min"], int)
