"""Tests del RegistroAsistenciaPresenter."""
from __future__ import annotations

from types import SimpleNamespace

from src.interface.presenters.academico.registro_asistencia_presenter import (
    RegistroAsistenciaPresenter,
)


def test_marcar_pone_pendiente():
    p = RegistroAsistenciaPresenter()
    p.marcar(5, "P")
    assert p.estado["registros"][5] == "P"
    assert p.estado["pendiente"] is True


def test_marcar_todos():
    p = RegistroAsistenciaPresenter()
    p.estado["estudiantes"] = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    p.marcar_todos("FI")
    assert p.estado["registros"] == {1: "FI", 2: "FI"}
    assert p.estado["pendiente"] is True


def test_aplicar_seleccion_copia_aliases():
    p = RegistroAsistenciaPresenter()
    p.aplicar_seleccion({"sel_grupo_id": 3, "sel_asignacion_id": 7, "sel_periodo_id": 1})
    assert p.estado["grupo_id"] == 3
    assert p.estado["asignacion_id"] == 7
    assert p.estado["periodo_id"] == 1
