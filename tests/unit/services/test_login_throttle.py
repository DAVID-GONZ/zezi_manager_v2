"""Tests unitarios para login_throttle (A1 — throttle/lockout en memoria)."""
from __future__ import annotations

import pytest

from src.services import login_throttle as throttle


@pytest.fixture(autouse=True)
def _reset():
    throttle.reset_throttle()
    yield
    throttle.reset_throttle()


class TestEstadoInicial:
    def test_usuario_desconocido_no_bloqueado(self):
        bloqueado, restante = throttle.estado_bloqueo("nadie")
        assert bloqueado is False
        assert restante == 0


class TestBloqueoPorFallos:
    def test_no_bloquea_antes_del_limite(self):
        for _ in range(throttle.MAX_INTENTOS - 1):
            throttle.registrar_fallo("prof1")
        bloqueado, _ = throttle.estado_bloqueo("prof1")
        assert bloqueado is False

    def test_bloquea_al_alcanzar_el_limite(self):
        for _ in range(throttle.MAX_INTENTOS):
            throttle.registrar_fallo("prof1")
        bloqueado, restante = throttle.estado_bloqueo("prof1")
        assert bloqueado is True
        assert 0 < restante <= throttle.BLOQUEO_SEGUNDOS

    def test_exito_limpia_el_contador(self):
        for _ in range(throttle.MAX_INTENTOS - 1):
            throttle.registrar_fallo("prof1")
        throttle.registrar_exito("prof1")
        # Tras limpiar, un solo fallo más NO debe bloquear.
        throttle.registrar_fallo("prof1")
        bloqueado, _ = throttle.estado_bloqueo("prof1")
        assert bloqueado is False

    def test_exito_libera_bloqueo_existente(self):
        for _ in range(throttle.MAX_INTENTOS):
            throttle.registrar_fallo("prof1")
        assert throttle.estado_bloqueo("prof1")[0] is True
        throttle.registrar_exito("prof1")
        assert throttle.estado_bloqueo("prof1")[0] is False


class TestNormalizacion:
    def test_casing_comparte_contador(self):
        # Mezclar mayúsculas/minúsculas no debe evadir el bloqueo.
        for usuario in ("Admin", "ADMIN", "admin", "AdMiN", "  admin  "):
            throttle.registrar_fallo(usuario)
        assert throttle.estado_bloqueo("admin")[0] is True

    def test_usuario_vacio_se_ignora(self):
        throttle.registrar_fallo("")
        throttle.registrar_fallo("   ")
        assert throttle.estado_bloqueo("")[0] is False


class TestExpiracion:
    def test_ventana_expirada_reinicia(self, monkeypatch):
        # Bloquea y luego avanza el reloj más allá de la ventana.
        base = 1000.0
        monkeypatch.setattr(throttle.time, "monotonic", lambda: base)
        for _ in range(throttle.MAX_INTENTOS):
            throttle.registrar_fallo("prof1")
        assert throttle.estado_bloqueo("prof1")[0] is True

        monkeypatch.setattr(
            throttle.time, "monotonic",
            lambda: base + throttle.BLOQUEO_SEGUNDOS + 1,
        )
        bloqueado, restante = throttle.estado_bloqueo("prof1")
        assert bloqueado is False
        assert restante == 0
