"""
test_marcar_config_inicial.py — Tests para InstitucionService.marcar_configuracion_inicial_completa.

Cubre: marcado exitoso, idempotencia y lanzamiento si no existe la institución.
"""
from __future__ import annotations

import pytest

from src.domain.models.institucion import Institucion, NuevaInstitucionDTO
from src.domain.ports.institucion_repo import IInstitucionRepository
from src.services.institucion_service import InstitucionService

# ---------------------------------------------------------------------------
# FakeRepo (mínimo para los tests de este módulo)
# ---------------------------------------------------------------------------

class _FakeInstitucionRepo(IInstitucionRepository):
    def __init__(self):
        self._data: dict[int, Institucion] = {}
        self._next_id = 1

    def get_by_id(self, id: int) -> Institucion | None:
        return self._data.get(id)

    def listar(self, solo_activas: bool = False) -> list[Institucion]:
        return list(self._data.values())

    def existe_nombre(self, nombre: str) -> bool:
        return any(i.nombre == nombre for i in self._data.values())

    def guardar(self, inst: Institucion) -> Institucion:
        inst = inst.model_copy(update={"id": self._next_id})
        self._data[self._next_id] = inst
        self._next_id += 1
        return inst

    def get_por_defecto(self) -> Institucion | None:
        return next(iter(self._data.values()), None)

    def actualizar(self, inst: Institucion) -> Institucion:
        if inst.id not in self._data:
            raise ValueError(f"No existe institución con id {inst.id}.")
        self._data[inst.id] = inst
        return inst

    def sembrar_defaults_tenant(self, institucion_id: int) -> None:
        pass


def _setup():
    repo = _FakeInstitucionRepo()
    svc = InstitucionService(repo)
    return svc, repo


# ---------------------------------------------------------------------------
# Tests de marcar_configuracion_inicial_completa
# ---------------------------------------------------------------------------

def test_marcar_config_completa_pone_flag_en_true():
    """
    Dada una institución recién creada (flag False por defecto),
    marcar_configuracion_inicial_completa debe retornar la institución
    con el flag en True.
    """
    svc, _ = _setup()
    inst = svc.crear(NuevaInstitucionDTO(nombre="IE Nueva"))
    assert inst.configuracion_inicial_completa is False

    inst_marcada = svc.marcar_configuracion_inicial_completa(inst.id)
    assert inst_marcada.configuracion_inicial_completa is True


def test_marcar_config_completa_idempotente():
    """
    Llamar marcar_configuracion_inicial_completa dos veces no lanza
    y deja el flag en True.
    """
    svc, _ = _setup()
    inst = svc.crear(NuevaInstitucionDTO(nombre="IE Idempotente"))

    svc.marcar_configuracion_inicial_completa(inst.id)
    inst_segunda = svc.marcar_configuracion_inicial_completa(inst.id)
    assert inst_segunda.configuracion_inicial_completa is True


def test_marcar_config_completa_institucion_no_existe_lanza():
    """
    Si la institución no existe, marcar_configuracion_inicial_completa
    debe lanzar ValueError.
    """
    svc, _ = _setup()
    with pytest.raises(ValueError, match="no existe"):
        svc.marcar_configuracion_inicial_completa(999)


def test_marcar_config_completa_no_altera_otros_campos():
    """
    El método no debe modificar campos como nombre, rector, etc.
    Solo cambia configuracion_inicial_completa.
    """
    svc, _ = _setup()
    inst = svc.crear(NuevaInstitucionDTO(nombre="IE Datos"))
    from src.services.institucion_service import ActualizarInstitucionDTO
    svc.actualizar(inst.id, ActualizarInstitucionDTO(rector="Dr. Alvarado"))

    inst_marcada = svc.marcar_configuracion_inicial_completa(inst.id)
    assert inst_marcada.rector == "Dr. Alvarado"
    assert inst_marcada.nombre == "IE Datos"
    assert inst_marcada.configuracion_inicial_completa is True
