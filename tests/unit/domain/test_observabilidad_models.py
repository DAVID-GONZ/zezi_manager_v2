"""
tests/unit/domain/test_observabilidad_models.py
================================================
Tests de los DTOs del dominio de observabilidad (obs_13 — T14).

Cubre:
  - Construcción válida de cada DTO.
  - Rechazo de campos extra (extra="forbid").
  - Campos opcionales en EntradaLogDTO.
  - model_dump() en lugar de .dict() (regla project).
"""
from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.models.observabilidad import (
    AlertaIPDTO,
    EntradaLogDTO,
    PuntoUsoDTO,
    SaludDTO,
)


# ── SaludDTO ───────────────────────────────────────────────────────────────────

class TestSaludDTO:
    def test_construccion_valida_sin_backup(self):
        s = SaludDTO(integra=True, version="2.0.0", uptime_segundos=300.5, tamanio_db_bytes=4096)
        assert s.integra is True
        assert s.version == "2.0.0"
        assert s.uptime_segundos == 300.5
        assert s.tamanio_db_bytes == 4096
        assert s.ultimo_backup is None

    def test_construccion_valida_con_backup(self):
        ts = datetime(2026, 9, 26, 12, 0, 0)
        s = SaludDTO(integra=False, version="1.9.0", uptime_segundos=0.0, tamanio_db_bytes=0, ultimo_backup=ts)
        assert s.ultimo_backup == ts

    def test_rechaza_campos_extra(self):
        with pytest.raises(Exception):
            SaludDTO(integra=True, version="2.0", uptime_segundos=1.0, tamanio_db_bytes=0, campo_extra="x")

    def test_model_dump_no_dict(self):
        s = SaludDTO(integra=True, version="2.0", uptime_segundos=10.0, tamanio_db_bytes=1024)
        d = s.model_dump()
        assert "integra" in d
        assert d["uptime_segundos"] == 10.0


# ── EntradaLogDTO ──────────────────────────────────────────────────────────────

class TestEntradaLogDTO:
    def test_construccion_todos_opcionales(self):
        """EntradaLogDTO se puede construir sin ningún campo."""
        e = EntradaLogDTO()
        assert e.timestamp is None
        assert e.usuario is None
        assert e.ip is None

    def test_construccion_con_campos(self):
        e = EntradaLogDTO(
            timestamp="2026-09-26T10:00:00",
            usuario="admin@school.edu",
            ip="192.168.1.1",
            tipo_evento="LOGIN_EXITOSO",
        )
        assert e.tipo_evento == "LOGIN_EXITOSO"

    def test_rechaza_campos_extra(self):
        with pytest.raises(Exception):
            EntradaLogDTO(campo_no_declarado="x")

    def test_model_dump_solo_campos_declarados(self):
        e = EntradaLogDTO(usuario="u", tipo_evento="LOGOUT")
        d = e.model_dump()
        assert d["usuario"] == "u"
        assert d["tipo_evento"] == "LOGOUT"
        assert "campo_no_declarado" not in d


# ── AlertaIPDTO ────────────────────────────────────────────────────────────────

class TestAlertaIPDTO:
    def test_construccion_valida(self):
        a = AlertaIPDTO(ip="10.0.0.1", fallos=5, segundos_restantes=120.0)
        assert a.ip == "10.0.0.1"
        assert a.fallos == 5
        assert a.segundos_restantes == 120.0

    def test_rechaza_campos_extra(self):
        with pytest.raises(Exception):
            AlertaIPDTO(ip="x", fallos=1, segundos_restantes=1.0, extra="y")

    def test_model_dump(self):
        a = AlertaIPDTO(ip="1.2.3.4", fallos=3, segundos_restantes=60.0)
        d = a.model_dump()
        assert d["ip"] == "1.2.3.4"
        assert d["fallos"] == 3


# ── PuntoUsoDTO ────────────────────────────────────────────────────────────────

class TestPuntoUsoDTO:
    def test_construccion_con_defaults(self):
        p = PuntoUsoDTO(fecha="2026-09-26")
        assert p.logins == 0
        assert p.denegados == 0

    def test_construccion_con_valores(self):
        p = PuntoUsoDTO(fecha="2026-09-25", logins=10, denegados=2)
        assert p.logins == 10
        assert p.denegados == 2

    def test_rechaza_campos_extra(self):
        with pytest.raises(Exception):
            PuntoUsoDTO(fecha="2026-09-24", logins=0, denegados=0, x="y")

    def test_model_dump(self):
        p = PuntoUsoDTO(fecha="2026-09-23", logins=7, denegados=1)
        d = p.model_dump()
        assert d["fecha"] == "2026-09-23"
        assert d["logins"] == 7
