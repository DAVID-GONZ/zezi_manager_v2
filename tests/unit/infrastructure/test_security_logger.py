"""
Tests de SecurityLogger e _JsonSecurityFormatter (obs_03).

Cubre:
  - Campos permitidos aparecen en el JSON serializado.
  - R7: un campo no permitido (ej. "password") no aparece en el JSON,
    ni como clave ni como valor, incluso si se inyecta vía atributo del record.
  - Niveles de log correctos (INFO/WARNING) por tipo de evento.
  - Campos específicos por método (tipo_evento, usuario, ip, etc.).
"""
from __future__ import annotations

import json
import logging

import pytest

import src.infrastructure.logging.security_logger as _sl_module
from src.infrastructure.logging.security_logger import (
    SecurityLogger,
    _JsonSecurityFormatter,
    _CAMPOS_PERMITIDOS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def formatter() -> _JsonSecurityFormatter:
    return _JsonSecurityFormatter()


def _make_record(
    level: int,
    msg: str,
    **extra_attrs,
) -> logging.LogRecord:
    """Crea un LogRecord con atributos extra inyectados directamente."""
    record = logging.LogRecord(
        name="zeci.security",
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in extra_attrs.items():
        setattr(record, k, v)
    return record


# ---------------------------------------------------------------------------
# Tests del formatter
# ---------------------------------------------------------------------------

class TestJsonSecurityFormatter:
    def test_campos_permitidos_aparecen(self, formatter):
        record = _make_record(
            logging.WARNING,
            "login_fallido",
            usuario="jperez",
            ip="192.168.1.1",
            motivo="credenciales invalidas",
            tipo_evento="LOGIN_FALLIDO",
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert data["usuario"] == "jperez"
        assert data["ip"] == "192.168.1.1"
        assert data["motivo"] == "credenciales invalidas"
        assert data["tipo_evento"] == "LOGIN_FALLIDO"
        assert "timestamp" in data

    def test_r7_password_no_aparece_en_json(self, formatter):
        """
        R7: si se inyecta un campo 'password' en el record (simulando
        un intento de filtrar datos sensibles), el formatter lo descarta
        porque no está en _CAMPOS_PERMITIDOS.
        """
        password_secreto = "SuperPasswordSensitivo1234567890"
        record = _make_record(
            logging.WARNING,
            "login_fallido",
            usuario="jperez",
            ip="10.0.0.1",
            motivo="credenciales invalidas",
            tipo_evento="LOGIN_FALLIDO",
            # Inyección maliciosa vía atributo extra
            password=password_secreto,
        )
        output = formatter.format(record)

        # El password NO debe aparecer ni como valor ni como clave
        assert password_secreto not in output
        assert "password" not in output.lower()

        # La salida sigue siendo JSON válido
        data = json.loads(output)
        assert data["usuario"] == "jperez"

    def test_campo_fuera_de_whitelist_descartado(self, formatter):
        """Cualquier campo fuera de _CAMPOS_PERMITIDOS no aparece en el JSON."""
        record = _make_record(
            logging.INFO,
            "login_exitoso",
            usuario="admin",
            ip="127.0.0.1",
            tipo_evento="LOGIN_EXITOSO",
            objetivo="usuario_objetivo",        # permitido desde obs_06 (R12)
            # Campos que NO están en la whitelist
            token="eyJhbGciOiJIUzI1NiJ9",
            datos_internos={"secreto": "valor"},
            datos_extras="no deberia aparecer",
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert "token" not in data
        assert "datos_internos" not in data
        assert "datos_extras" not in data
        # Los permitidos sí aparecen
        assert data["usuario"] == "admin"
        assert data["tipo_evento"] == "LOGIN_EXITOSO"
        assert data["objetivo"] == "usuario_objetivo"

    def test_timestamp_iso8601_presente(self, formatter):
        record = _make_record(logging.INFO, "logout", usuario="u", ip="1.1.1.1")
        output = formatter.format(record)
        data = json.loads(output)
        ts = data["timestamp"]
        # Formato ISO-8601: YYYY-MM-DDTHH:MM:SS
        assert len(ts) == 19
        assert ts[10] == "T"

    def test_campo_none_omitido(self, formatter):
        """Campos con valor None no se incluyen en el JSON."""
        record = _make_record(
            logging.INFO,
            "logout",
            usuario="u",
            ip="1.1.1.1",
            tipo_evento="LOGOUT",
            # motivo no se establece → getattr devuelve None
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "motivo" not in data

    def test_whitelist_es_frozenset_completo(self):
        """Verificar que _CAMPOS_PERMITIDOS contiene los campos esperados."""
        esperados = {
            "usuario", "ip", "timestamp", "rol", "institucion_id",
            "tipo_evento", "motivo", "recurso",
            "objetivo",   # añadido en obs_06 para ver_como / gestion_usuario
        }
        assert esperados == _CAMPOS_PERMITIDOS


# ---------------------------------------------------------------------------
# Tests de SecurityLogger (nivel y campos)
# ---------------------------------------------------------------------------

class TestSecurityLoggerNiveles:
    """Verifica que cada método emite al nivel correcto."""

    def setup_method(self):
        """Instalar un handler de captura en el logger zeci.security."""
        self.records: list[logging.LogRecord] = []
        self.handler = _CapturingHandler(self.records)
        # Referenciar directamente el logger del módulo para evitar ambigüedad
        _sl_module._logger.addHandler(self.handler)
        # tests/conftest.py deshabilita todos los logs con logging.disable(CRITICAL).
        # Aquí rehabilitamos temporalmente para poder capturar los registros de seguridad.
        logging.disable(logging.NOTSET)

    def teardown_method(self):
        _sl_module._logger.removeHandler(self.handler)
        # Restaurar el silenciado global de tests.
        logging.disable(logging.CRITICAL)

    def test_login_exitoso_info(self):
        sl = SecurityLogger()
        sl.login_exitoso("u", "1.2.3.4", "PROFESOR", 7)
        assert any(r.levelno == logging.INFO for r in self.records)

    def test_login_fallido_warning(self):
        sl = SecurityLogger()
        sl.login_fallido("u", "1.2.3.4", "credenciales invalidas")
        assert any(r.levelno == logging.WARNING for r in self.records)

    def test_logout_info(self):
        sl = SecurityLogger()
        sl.logout("u", "1.2.3.4")
        assert any(r.levelno == logging.INFO for r in self.records)

    def test_acceso_denegado_warning(self):
        sl = SecurityLogger()
        sl.acceso_denegado("u", "1.2.3.4", "/admin")
        assert any(r.levelno == logging.WARNING for r in self.records)

    def test_ver_como_info(self):
        sl = SecurityLogger()
        sl.ver_como("admin", "profesor1", "VER_COMO_INICIO")
        assert any(r.levelno == logging.INFO for r in self.records)

    def test_gestion_usuario_info(self):
        sl = SecurityLogger()
        sl.gestion_usuario("admin", "nuevo_user", "CREAR_USUARIO")
        assert any(r.levelno == logging.INFO for r in self.records)

    def test_login_exitoso_campos(self):
        sl = SecurityLogger()
        sl.login_exitoso("jperez", "10.0.0.1", "DIRECTOR", 3)
        rec = self.records[-1]
        assert getattr(rec, "usuario") == "jperez"
        assert getattr(rec, "ip") == "10.0.0.1"
        assert getattr(rec, "rol") == "DIRECTOR"
        assert getattr(rec, "institucion_id") == 3
        assert getattr(rec, "tipo_evento") == "LOGIN_EXITOSO"

    def test_login_fallido_campos(self):
        sl = SecurityLogger()
        sl.login_fallido("x", "2.2.2.2", "cuenta bloqueada")
        rec = self.records[-1]
        assert getattr(rec, "usuario") == "x"
        assert getattr(rec, "tipo_evento") == "LOGIN_FALLIDO"
        assert getattr(rec, "motivo") == "cuenta bloqueada"


class _CapturingHandler(logging.Handler):
    """Handler de captura para tests: almacena los records en una lista."""

    def __init__(self, records: list):
        super().__init__()
        self._records = records

    def emit(self, record: logging.LogRecord) -> None:
        self._records.append(record)
