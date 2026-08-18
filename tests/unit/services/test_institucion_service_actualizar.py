"""
Tests de servicio para InstitucionService.actualizar y snapshot_institucional (mejora_06).
"""
import pytest

from src.domain.models.institucion import (
    ActualizarInstitucionDTO,
    Institucion,
    NuevaInstitucionDTO,
)
from src.domain.ports.institucion_repo import IInstitucionRepository
from src.services.institucion_service import InstitucionService

# ---------------------------------------------------------------------------
# FakeRepo
# ---------------------------------------------------------------------------

class FakeInstitucionRepo(IInstitucionRepository):
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


def _crear_svc():
    repo = FakeInstitucionRepo()
    svc = InstitucionService(repo)
    return svc, repo


# ---------------------------------------------------------------------------
# actualizar()
# ---------------------------------------------------------------------------

def test_actualizar_cambia_rector():
    svc, _ = _crear_svc()
    inst = svc.crear(NuevaInstitucionDTO(nombre="IE Test"))
    dto = ActualizarInstitucionDTO(rector="Dr. Pérez", codigo_dane="123456789012")
    inst2 = svc.actualizar(inst.id, dto)
    assert inst2.rector == "Dr. Pérez"
    assert inst2.codigo_dane == "123456789012"
    assert inst2.nombre == "IE Test"  # no tocado


def test_actualizar_institucion_no_existe_lanza():
    svc, _ = _crear_svc()
    dto = ActualizarInstitucionDTO(rector="X")
    with pytest.raises(ValueError, match="no existe"):
        svc.actualizar(999, dto)


# ---------------------------------------------------------------------------
# snapshot_institucional()
# ---------------------------------------------------------------------------

def test_snapshot_institucional_vacio_si_no_hay_datos():
    svc, _ = _crear_svc()
    inst = svc.crear(NuevaInstitucionDTO(nombre="IE Sin Datos"))
    snap = svc.snapshot_institucional(inst.id)
    # nombre_institucion se mapea desde nombre si no hay nombre_oficial
    assert "nombre_institucion" in snap
    assert snap["nombre_institucion"] == "IE Sin Datos"
    # campos opcionales no están
    assert "rector" not in snap
    assert "dane_code" not in snap


def test_snapshot_incluye_solo_no_nulos():
    svc, _ = _crear_svc()
    inst = svc.crear(NuevaInstitucionDTO(nombre="IE Test"))
    svc.actualizar(inst.id, ActualizarInstitucionDTO(
        rector="Dr. García",
        codigo_dane="123456789012",
    ))
    snap = svc.snapshot_institucional(inst.id)
    assert snap["rector"] == "Dr. García"
    assert snap["dane_code"] == "123456789012"
    assert "logo_path" not in snap
    assert "resolucion_aprobacion" not in snap


def test_snapshot_mapea_telefono_correctamente():
    """telefono de Institucion → telefono_institucion en el snapshot."""
    svc, _ = _crear_svc()
    inst = svc.crear(NuevaInstitucionDTO(nombre="IE Tel"))
    svc.actualizar(inst.id, ActualizarInstitucionDTO(telefono="3001234567"))
    snap = svc.snapshot_institucional(inst.id)
    assert "telefono_institucion" in snap
    assert snap["telefono_institucion"] == "3001234567"
    assert "telefono" not in snap  # la clave en el snapshot es telefono_institucion


def test_snapshot_institucional_none_id_retorna_vacio():
    svc, _ = _crear_svc()
    snap = svc.snapshot_institucional(None)
    assert snap == {}
