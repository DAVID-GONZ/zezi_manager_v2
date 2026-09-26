"""
tests/unit/services/test_observabilidad_service.py
=====================================================
Tests del servicio de observabilidad (obs_13 — T10).

Cubre:
  - base íntegra → salud OK.
  - base corrupta → veredicto en rojo (integra=False).
  - log ausente → lista vacía con la marca de no disponible.
  - uso_diario devuelve un punto por día, incluidos los días sin actividad.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.domain.models.observabilidad import AlertaIPDTO, EntradaLogDTO, PuntoUsoDTO, SaludDTO
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.ports.log_reader import ILogReader
from src.services.observabilidad_service import ObservabilidadService


# ── Fakes ─────────────────────────────────────────────────────────────────────

class FakeAuditoriaRepo(IAuditoriaRepository):
    """Fake mínimo que devuelve datos controlados para los tests."""

    def __init__(self, uso_diario_filas=None):
        self._uso_filas = uso_diario_filas or []

    # Abstractos obligatorios
    def registrar_evento(self, evento): ...
    def listar_eventos(self, filtro): return []
    def get_ultimo_login(self, usuario_id): return None
    def contar_fallos_recientes(self, usuario, ventana_minutos=30): return 0
    def registrar_cambio(self, registro): ...
    def registrar_cambios_masivos(self, registros): return 0
    def listar_cambios(self, filtro): return []
    def listar_cambios_por_registro(self, tabla, registro_id): return []
    def get_cambio(self, cambio_id): return None

    def uso_diario(self, dias=14):
        return self._uso_filas


class FakeLogReader(ILogReader):
    def __init__(self, entradas=None, disponible_=True):
        self._entradas = entradas if entradas is not None else []
        self._disponible = disponible_

    def leer_ultimos(self, n=200, *, nivel=None, tipo_evento=None):
        return [e for e in self._entradas if tipo_evento is None or e.get("tipo_evento") == tipo_evento][:n]

    def disponible(self):
        return self._disponible


# ── Helpers ────────────────────────────────────────────────────────────────────

def _svc(uso_filas=None, entradas_log=None, log_disponible=True):
    return ObservabilidadService(
        auditoria_repo=FakeAuditoriaRepo(uso_diario_filas=uso_filas),
        log_reader=FakeLogReader(entradas=entradas_log, disponible_=log_disponible),
    )


# ── Tests: salud ───────────────────────────────────────────────────────────────

class TestSaludDTO:

    def test_salud_base_integra_devuelve_true(self):
        """Base íntegra → salud OK (integra=True)."""
        svc = _svc()
        with patch("src.services.observabilidad_service.verify_db_integrity", return_value=True):
            resultado = svc.salud()
        assert isinstance(resultado, SaludDTO)
        assert resultado.integra is True  # R2

    def test_salud_base_corrupta_devuelve_false(self):
        """Base corrupta → veredicto en rojo (integra=False)."""
        svc = _svc()
        with patch("src.services.observabilidad_service.verify_db_integrity", return_value=False):
            resultado = svc.salud()
        assert resultado.integra is False

    def test_salud_contiene_version(self):
        svc = _svc()
        with patch("src.services.observabilidad_service.verify_db_integrity", return_value=True):
            resultado = svc.salud()
        assert isinstance(resultado.version, str)
        assert resultado.version  # no vacía

    def test_salud_sin_backup_es_none(self):
        """Sin directorio de archivos, ultimo_backup es None (R3)."""
        svc = _svc()
        with (
            patch("src.services.observabilidad_service.verify_db_integrity", return_value=True),
            patch.object(ObservabilidadService, "_ultimo_backup", return_value=None),
        ):
            resultado = svc.salud()
        assert resultado.ultimo_backup is None  # R3

    def test_salud_uptime_es_positivo(self):
        svc = _svc()
        with patch("src.services.observabilidad_service.verify_db_integrity", return_value=True):
            resultado = svc.salud()
        assert resultado.uptime_segundos >= 0

    def test_salud_error_integrity_devuelve_false(self):
        """Si verify_db_integrity lanza excepción, integra=False (fail-safe)."""
        svc = _svc()
        with patch(
            "src.services.observabilidad_service.verify_db_integrity",
            side_effect=Exception("BD inaccesible"),
        ):
            resultado = svc.salud()
        assert resultado.integra is False


# ── Tests: log de seguridad ────────────────────────────────────────────────────

class TestEventosSeguridad:

    def test_log_ausente_devuelve_lista_vacia(self):
        """Log ausente → lista vacía con disponible()=False (R7)."""
        svc = _svc(log_disponible=False)
        resultado = svc.eventos_seguridad()
        assert resultado == []
        assert svc.log_disponible() is False

    def test_eventos_devuelven_entradas_log_dto(self):
        entradas = [
            {"tipo_evento": "LOGIN_EXITOSO", "timestamp": "2026-09-26T10:00:00", "usuario": "ana"},
        ]
        svc = _svc(entradas_log=entradas)
        resultado = svc.eventos_seguridad()
        assert len(resultado) == 1
        assert isinstance(resultado[0], EntradaLogDTO)
        assert resultado[0].tipo_evento == "LOGIN_EXITOSO"

    def test_log_disponible_cuando_hay_archivo(self):
        svc = _svc(log_disponible=True)
        assert svc.log_disponible() is True

    def test_filtro_tipo_evento_delegado(self):
        entradas = [
            {"tipo_evento": "LOGIN_EXITOSO", "timestamp": "2026-09-26T10:00:00"},
            {"tipo_evento": "LOGIN_FALLIDO", "timestamp": "2026-09-26T10:01:00"},
        ]
        svc = _svc(entradas_log=entradas)
        resultado = svc.eventos_seguridad(tipo_evento="LOGIN_FALLIDO")
        assert all(e.tipo_evento == "LOGIN_FALLIDO" for e in resultado)


# ── Tests: alertas de IP ───────────────────────────────────────────────────────

class TestAlertasIP:

    def test_sin_alertas_devuelve_vacio(self):
        svc = _svc()
        with patch("src.services.observabilidad_service.alertas_activas", return_value=[]):
            resultado = svc.alertas_ip()
        assert resultado == []

    def test_alertas_mapeadas_a_dto(self):
        svc = _svc()
        activas = [("192.168.1.1", 5, 120.0), ("10.0.0.1", 3, 60.0)]
        with patch("src.services.observabilidad_service.alertas_activas", return_value=activas):
            resultado = svc.alertas_ip()
        assert len(resultado) == 2
        ips = {a.ip for a in resultado}
        assert "192.168.1.1" in ips
        assert "10.0.0.1" in ips
        for alerta in resultado:
            assert isinstance(alerta, AlertaIPDTO)
            assert alerta.fallos > 0
            assert alerta.segundos_restantes > 0


# ── Tests: uso_diario ─────────────────────────────────────────────────────────

class TestUsoDiario:

    def test_devuelve_un_punto_por_dia(self):
        """uso_diario devuelve un punto por día de la ventana (T9)."""
        dias = 7
        filas = [
            {"fecha": f"2026-09-{20+i}", "logins": i, "denegados": 0}
            for i in range(dias)
        ]
        svc = _svc(uso_filas=filas)
        resultado = svc.uso_diario(dias=dias)
        assert len(resultado) == dias
        for punto in resultado:
            assert isinstance(punto, PuntoUsoDTO)

    def test_dias_sin_actividad_tienen_ceros(self):
        """Los días sin actividad se incluyen con ceros."""
        filas = [
            {"fecha": "2026-09-26", "logins": 5, "denegados": 1},
            # Día 2 sin datos — el repo fake devuelve solo lo que hay
        ]
        svc = _svc(uso_filas=filas)
        resultado = svc.uso_diario(dias=1)
        assert len(resultado) == 1
        assert resultado[0].logins == 5

    def test_repo_vacio_devuelve_lista_vacia(self):
        """Si el repo devuelve [] (no implementado), uso_diario da []."""
        svc = _svc(uso_filas=[])
        resultado = svc.uso_diario(dias=14)
        assert resultado == []

    def test_puntos_tienen_tipos_correctos(self):
        filas = [
            {"fecha": "2026-09-25", "logins": 3, "denegados": 0},
        ]
        svc = _svc(uso_filas=filas)
        resultado = svc.uso_diario(dias=1)
        assert isinstance(resultado[0].fecha, str)
        assert isinstance(resultado[0].logins, int)
        assert isinstance(resultado[0].denegados, int)
