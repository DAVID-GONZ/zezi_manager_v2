"""
tests/unit/infrastructure/test_jsonl_log_reader.py
=====================================================
Tests del lector JSONL de seguridad (obs_13 — T4).

Cubre:
  - Archivo ausente → leer_ultimos() devuelve [] y disponible() es False.  (R7)
  - Línea a medio escribir → se descarta sin excepción.                    (R6)
  - Archivo mayor que el tope → devuelve las últimas n entradas.           (R6)
  - Campo fuera de la whitelist → no aparece en la salida.                 (R8)
  - Filtro por tipo_evento funciona correctamente.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.infrastructure.logging.jsonl_log_reader import JsonlLogReader, _TOPE_BYTES


# ── Helpers ────────────────────────────────────────────────────────────────────

def _linea_json(**kwargs) -> str:
    return json.dumps(kwargs)


def _escribir_log(path: Path, lineas: list[str]) -> None:
    path.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestJsonlLogReaderArchivoAusente:
    """R7: archivo ausente → comportamiento vacío, no excepción."""

    def setup_method(self):
        self.reader = JsonlLogReader()

    def test_disponible_sin_archivo_es_false(self, tmp_path):
        ruta_no_existe = tmp_path / "no_existe.log"
        with patch.object(JsonlLogReader, "_ruta", return_value=ruta_no_existe):
            assert self.reader.disponible() is False  # R7

    def test_leer_ultimos_sin_archivo_devuelve_lista_vacia(self, tmp_path):
        ruta_no_existe = tmp_path / "no_existe.log"
        with patch.object(JsonlLogReader, "_ruta", return_value=ruta_no_existe):
            resultado = self.reader.leer_ultimos()
        assert resultado == []  # R7

    def test_disponible_con_ruta_none(self):
        with patch.object(JsonlLogReader, "_ruta", return_value=None):
            assert self.reader.disponible() is False

    def test_leer_ultimos_con_ruta_none(self):
        with patch.object(JsonlLogReader, "_ruta", return_value=None):
            resultado = self.reader.leer_ultimos()
        assert resultado == []


class TestJsonlLogReaderLineasIlegibles:
    """R6: líneas a medio escribir (ilegibles) se descartan sin excepción."""

    def setup_method(self):
        self.reader = JsonlLogReader()

    def test_linea_truncada_se_descarta(self, tmp_path):
        log = tmp_path / "security.log"
        # Una línea válida y una truncada (sin cierre de JSON)
        lineas = [
            _linea_json(tipo_evento="LOGIN_EXITOSO", timestamp="2026-09-26T10:00:00"),
            '{"tipo_evento": "LOGIN_FALLIDO", "timestamp": "2026',  # truncada
        ]
        _escribir_log(log, lineas)
        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            resultado = self.reader.leer_ultimos()
        # Solo la línea válida debe aparecer
        assert len(resultado) == 1
        assert resultado[0]["tipo_evento"] == "LOGIN_EXITOSO"

    def test_linea_vacia_se_ignora(self, tmp_path):
        log = tmp_path / "security.log"
        lineas = [
            "",
            _linea_json(tipo_evento="LOGOUT", timestamp="2026-09-26T11:00:00"),
            "   ",
        ]
        _escribir_log(log, lineas)
        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            resultado = self.reader.leer_ultimos()
        assert len(resultado) == 1
        assert resultado[0]["tipo_evento"] == "LOGOUT"

    def test_todas_lineas_ilegibles_devuelve_vacio(self, tmp_path):
        log = tmp_path / "security.log"
        log.write_text("no es json\ntampoco esto\n", encoding="utf-8")
        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            resultado = self.reader.leer_ultimos()
        assert resultado == []


class TestJsonlLogReaderTope:
    """R6: archivo mayor que el tope → solo se carga la cola."""

    def setup_method(self):
        self.reader = JsonlLogReader()

    def test_archivo_mayor_que_tope_devuelve_ultimas_n(self, tmp_path):
        log = tmp_path / "security.log"
        # Construir un archivo mayor que _TOPE_BYTES
        # Líneas "relleno" al inicio, luego las últimas 5 líneas válidas
        linea_relleno = _linea_json(
            tipo_evento="LOGIN_EXITOSO",
            timestamp="2026-01-01T00:00:00",
            usuario="relleno",
        )
        # Tamaño de una línea de relleno + salto de línea
        tam_linea = len(linea_relleno.encode("utf-8")) + 1
        n_relleno = (_TOPE_BYTES // tam_linea) + 50  # bastantes más del tope

        lineas_cola = [
            _linea_json(tipo_evento="ACCESO_DENEGADO", timestamp=f"2026-09-26T10:0{i}:00")
            for i in range(5)
        ]

        with log.open("w", encoding="utf-8") as f:
            for _ in range(n_relleno):
                f.write(linea_relleno + "\n")
            for linea in lineas_cola:
                f.write(linea + "\n")

        assert log.stat().st_size > _TOPE_BYTES, "El archivo debe ser mayor que el tope"

        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            resultado = self.reader.leer_ultimos(n=5)

        assert len(resultado) == 5
        # Las entradas son las de la cola (más recientes primero)
        for entrada in resultado:
            assert entrada["tipo_evento"] == "ACCESO_DENEGADO"

    def test_n_limita_la_cantidad_devuelta(self, tmp_path):
        log = tmp_path / "security.log"
        lineas = [
            _linea_json(tipo_evento="LOGIN_EXITOSO", timestamp=f"2026-09-26T10:{i:02d}:00")
            for i in range(20)
        ]
        _escribir_log(log, lineas)
        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            resultado = self.reader.leer_ultimos(n=5)
        assert len(resultado) == 5


class TestJsonlLogReaderWhitelist:
    """R8: campos fuera de la whitelist no aparecen en la salida."""

    def setup_method(self):
        self.reader = JsonlLogReader()

    def test_campo_fuera_de_whitelist_no_aparece(self, tmp_path):
        log = tmp_path / "security.log"
        # Añadir campos que NO están en _CAMPOS_PERMITIDOS
        linea = _linea_json(
            tipo_evento="LOGIN_EXITOSO",
            timestamp="2026-09-26T10:00:00",
            usuario="pepe",
            CAMPO_SECRETO="valor_secreto",       # no en whitelist
            password="deberia_filtrarse",         # no en whitelist
            campo_raro="algo",                    # no en whitelist
        )
        _escribir_log(log, [linea])
        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            resultado = self.reader.leer_ultimos()
        assert len(resultado) == 1
        entrada = resultado[0]
        assert "CAMPO_SECRETO" not in entrada
        assert "password" not in entrada
        assert "campo_raro" not in entrada
        assert entrada.get("tipo_evento") == "LOGIN_EXITOSO"
        assert entrada.get("usuario") == "pepe"

    def test_solo_campos_de_whitelist_presentes(self, tmp_path):
        """Todos los campos presentes deben pertenecer a la whitelist."""
        from src.infrastructure.logging.security_logger import _CAMPOS_PERMITIDOS

        log = tmp_path / "security.log"
        linea = _linea_json(
            tipo_evento="LOGIN_FALLIDO",
            timestamp="2026-09-26T10:05:00",
            usuario="juan",
            ip="192.168.1.10",
            motivo="password incorrecta",
            campo_extra_inventado="no debe pasar",
        )
        _escribir_log(log, [linea])
        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            resultado = self.reader.leer_ultimos()
        assert len(resultado) == 1
        for campo in resultado[0]:
            assert campo in _CAMPOS_PERMITIDOS


class TestJsonlLogReaderFiltros:
    """Filtros de leer_ultimos funcionan correctamente."""

    def setup_method(self):
        self.reader = JsonlLogReader()

    def test_filtro_tipo_evento(self, tmp_path):
        log = tmp_path / "security.log"
        lineas = [
            _linea_json(tipo_evento="LOGIN_EXITOSO", timestamp="2026-09-26T10:00:00"),
            _linea_json(tipo_evento="LOGIN_FALLIDO", timestamp="2026-09-26T10:01:00"),
            _linea_json(tipo_evento="LOGIN_EXITOSO", timestamp="2026-09-26T10:02:00"),
        ]
        _escribir_log(log, lineas)
        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            resultado = self.reader.leer_ultimos(tipo_evento="LOGIN_FALLIDO")
        assert len(resultado) == 1
        assert resultado[0]["tipo_evento"] == "LOGIN_FALLIDO"

    def test_disponible_con_archivo_existente(self, tmp_path):
        log = tmp_path / "security.log"
        log.write_text("{}\n", encoding="utf-8")
        with patch.object(JsonlLogReader, "_ruta", return_value=log):
            assert self.reader.disponible() is True
