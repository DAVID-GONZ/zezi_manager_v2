"""Tests de la lógica pura del widget de parrilla.

`parrilla_widget` es un render helper SIN estado (no necesita presenter), pero sus
helpers de indexación por eje son view-logic pura y merecen tests reales.
"""
from __future__ import annotations

from src.interface.pages.academico.parrilla_widget import (
    _clave_eje,
    _grupos_presentes,
    _opciones_eje,
)


def _celda(grupo_id, grupo_codigo, usuario_id, docente_nombre, sala):
    return {
        "grupo_id": grupo_id,
        "grupo_codigo": grupo_codigo,
        "usuario_id": usuario_id,
        "docente_nombre": docente_nombre,
        "sala": sala,
    }


def _datos():
    return {
        "celdas": [
            _celda(2, "7B", 20, "Beatriz", "Aula 2"),
            _celda(1, "6A", 10, "Ana", "Aula 1"),
            _celda(1, "6A", 10, "Ana", "Aula 1"),  # duplicada
        ]
    }


class TestClaveEje:
    def test_por_perspectiva(self):
        c = _celda(1, "6A", 10, "Ana", "Aula 1")
        assert _clave_eje(c, "Grupo") == 1
        assert _clave_eje(c, "Docente") == 10
        assert _clave_eje(c, "Sala") == "Aula 1"


class TestOpcionesEje:
    def test_grupo_dedup_y_ordenado_por_codigo(self):
        opts = _opciones_eje(_datos(), "Grupo")
        assert opts == {1: "6A", 2: "7B"}
        assert list(opts) == [1, 2]  # ordenado por código

    def test_docente(self):
        assert _opciones_eje(_datos(), "Docente") == {10: "Ana", 20: "Beatriz"}

    def test_sala(self):
        assert _opciones_eje(_datos(), "Sala") == {"Aula 1": "Aula 1", "Aula 2": "Aula 2"}


class TestGruposPresentes:
    def test_dedup_y_orden(self):
        assert _grupos_presentes(_datos()) == {1: "6A", 2: "7B"}
