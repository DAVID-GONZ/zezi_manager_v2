"""Tests unitarios para PeriodoService."""
from __future__ import annotations

import pytest

from src.domain.models.periodo import (
    HitoPeriodo, NuevoPeriodoDTO, NuevoHitoPeriodoDTO, Periodo, TipoHito,
)
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.services.periodo_service import PeriodoService


# ===========================================================================
# Fake
# ===========================================================================

class FakePeriodoRepo(IPeriodoRepository):
    def __init__(self):
        self._periodos: dict[int, Periodo] = {}
        self._hitos: dict[int, HitoPeriodo] = {}
        self._next_id = 1
        self._next_hito_id = 1

    def guardar(self, p: Periodo) -> Periodo:
        p = p.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._periodos[p.id] = p
        return p

    def actualizar(self, p: Periodo) -> Periodo:
        self._periodos[p.id] = p
        return p

    def cerrar(self, periodo_id: int) -> Periodo | None:
        return self._periodos.get(periodo_id)

    def activar(self, periodo_id: int) -> None:
        pass

    def desactivar(self, periodo_id: int) -> None:
        pass

    def get_by_id(self, pid: int) -> Periodo | None:
        return self._periodos.get(pid)

    def get_activo(self, anio_id: int) -> Periodo | None:
        for p in self._periodos.values():
            if p.anio_id == anio_id and p.esta_abierto:
                return p
        return None

    def get_por_numero(self, anio_id: int, numero: int) -> Periodo | None:
        for p in self._periodos.values():
            if p.anio_id == anio_id and p.numero == numero:
                return p
        return None

    def listar_por_anio(self, anio_id: int) -> list[Periodo]:
        return [p for p in self._periodos.values() if p.anio_id == anio_id]

    def suma_pesos_otros(self, anio_id: int, excluir_id: int | None = None) -> float:
        return sum(
            p.peso_porcentual for p in self._periodos.values()
            if p.anio_id == anio_id and p.id != excluir_id
        )

    def guardar_hito(self, h: HitoPeriodo) -> HitoPeriodo:
        h = h.model_copy(update={"id": self._next_hito_id})
        self._next_hito_id += 1
        self._hitos[h.id] = h
        return h

    def get_hito(self, hito_id: int) -> HitoPeriodo | None:
        return self._hitos.get(hito_id)

    def actualizar_hito(self, h: HitoPeriodo) -> HitoPeriodo:
        self._hitos[h.id] = h
        return h

    def eliminar_hito(self, hito_id: int) -> bool:
        return self._hitos.pop(hito_id, None) is not None

    def listar_hitos(self, periodo_id: int) -> list[HitoPeriodo]:
        return [h for h in self._hitos.values() if h.periodo_id == periodo_id]

    def listar_hitos_proximos(self, dias: int = 7) -> list[HitoPeriodo]:
        return []


# ===========================================================================
# Helpers
# ===========================================================================

def _make_svc() -> tuple[PeriodoService, FakePeriodoRepo]:
    repo = FakePeriodoRepo()
    return PeriodoService(repo), repo


def _dto(numero: int = 1, peso: float = 25.0) -> NuevoPeriodoDTO:
    return NuevoPeriodoDTO(
        anio_id=1,
        numero=numero,
        nombre=f"Periodo {numero}",
        peso_porcentual=peso,
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestCrearPeriodo:
    def test_crea_periodo_nuevo(self):
        svc, _ = _make_svc()
        p = svc.crear_periodo(_dto(1))
        assert p.id is not None
        assert p.numero == 1

    def test_lanza_si_numero_duplicado_en_anio(self):
        svc, _ = _make_svc()
        svc.crear_periodo(_dto(1))
        with pytest.raises(ValueError, match="1"):
            svc.crear_periodo(_dto(1))

    def test_lanza_si_suma_pesos_supera_100(self):
        svc, _ = _make_svc()
        svc.crear_periodo(_dto(1, 60.0))
        svc.crear_periodo(_dto(2, 30.0))
        with pytest.raises(ValueError, match="100"):
            svc.crear_periodo(_dto(3, 15.0))  # 60+30+15 = 105 > 100


class TestCerrarPeriodo:
    def test_cierra_periodo_abierto(self):
        svc, _ = _make_svc()
        p = svc.crear_periodo(_dto())
        cerrado = svc.cerrar_periodo(p.id)
        assert not cerrado.esta_abierto

    def test_lanza_si_no_existe(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="999"):
            svc.cerrar_periodo(999)


class TestAgregarHito:
    def test_agrega_hito_a_periodo_abierto(self):
        from datetime import date, timedelta
        svc, _ = _make_svc()
        p = svc.crear_periodo(_dto())
        dto_hito = NuevoHitoPeriodoDTO(
            periodo_id=p.id,
            tipo=TipoHito.ENTREGA_NOTAS,
            fecha_limite=date.today() + timedelta(days=10),
            descripcion="Entrega de notas",
        )
        hito = svc.agregar_hito(dto_hito)
        assert hito.id is not None

    def test_lanza_si_periodo_cerrado(self):
        from datetime import date, timedelta
        svc, _ = _make_svc()
        p = svc.crear_periodo(_dto())
        svc.cerrar_periodo(p.id)
        dto_hito = NuevoHitoPeriodoDTO(
            periodo_id=p.id,
            tipo=TipoHito.ENTREGA_NOTAS,
            fecha_limite=date.today() + timedelta(days=10),
            descripcion="Entrega de notas",
        )
        with pytest.raises(ValueError, match="cerrado"):
            svc.agregar_hito(dto_hito)


class TestGetActivo:
    def test_lanza_si_no_hay_activo(self):
        svc, _ = _make_svc()
        with pytest.raises(ValueError, match="activo"):
            svc.get_activo(anio_id=1)
