"""
Tests de AuditoriaService.verificar_integridad (seguridad_03, M3).

El servicio solo compone primitivos a partir de los dos métodos de verificación
del repositorio; aquí se usa un fake configurable para cubrir las combinaciones
íntegra / alterada sin tocar SQLite.
"""
from __future__ import annotations

from src.services.auditoria_service import AuditoriaService


class _FakeAuditoriaRepo:
    """Repo mínimo: solo expone los métodos de verificación de cadena."""

    def __init__(self, evento_roto: int | None, cambio_roto: int | None):
        self._evento_roto = evento_roto
        self._cambio_roto = cambio_roto

    def verificar_cadena_eventos(self) -> int | None:
        return self._evento_roto

    def verificar_cadena_cambios(self) -> int | None:
        return self._cambio_roto


def test_ambas_cadenas_integras():
    svc = AuditoriaService(_FakeAuditoriaRepo(evento_roto=None, cambio_roto=None))
    resultado = svc.verificar_integridad()
    assert resultado == {
        "eventos_ok": True,
        "cambios_ok": True,
        "evento_roto_id": None,
        "cambio_roto_id": None,
    }


def test_eventos_alterados():
    svc = AuditoriaService(_FakeAuditoriaRepo(evento_roto=42, cambio_roto=None))
    resultado = svc.verificar_integridad()
    assert resultado["eventos_ok"] is False
    assert resultado["evento_roto_id"] == 42
    assert resultado["cambios_ok"] is True
    assert resultado["cambio_roto_id"] is None


def test_cambios_alterados():
    svc = AuditoriaService(_FakeAuditoriaRepo(evento_roto=None, cambio_roto=7))
    resultado = svc.verificar_integridad()
    assert resultado["cambios_ok"] is False
    assert resultado["cambio_roto_id"] == 7
    assert resultado["eventos_ok"] is True


def test_ambas_alteradas():
    svc = AuditoriaService(_FakeAuditoriaRepo(evento_roto=1, cambio_roto=2))
    resultado = svc.verificar_integridad()
    assert resultado == {
        "eventos_ok": False,
        "cambios_ok": False,
        "evento_roto_id": 1,
        "cambio_roto_id": 2,
    }
