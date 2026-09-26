"""Tests del HistorialPresenter (obs_10, T5/T6)."""
from __future__ import annotations

from src.interface.presenters.admin.historial_presenter import HistorialPresenter


class TestHistorialPresenter:
    # ── abrir ────────────────────────────────────────────────────────────────

    def test_abrir_fija_tabla_y_registro_id(self):
        p = HistorialPresenter()
        p.abrir("estudiantes", 42)
        assert p.estado["tabla"] == "estudiantes"
        assert p.estado["registro_id"] == 42

    def test_abrir_marca_cargando_true(self):
        p = HistorialPresenter()
        p.abrir("usuarios", 1)
        assert p.estado["cargando"] is True

    def test_abrir_marca_abierto_true(self):
        p = HistorialPresenter()
        p.abrir("usuarios", 1)
        assert p.estado["abierto"] is True

    def test_abrir_limpia_items_anteriores(self):
        p = HistorialPresenter()
        p.estado["items"] = ["residuo"]
        p.abrir("estudiantes", 7)
        assert p.estado["items"] == []

    def test_abrir_limpia_error_anterior(self):
        p = HistorialPresenter()
        p.estado["error"] = "error previo"
        p.abrir("estudiantes", 7)
        assert p.estado["error"] is None

    # ── set_items ────────────────────────────────────────────────────────────

    def test_set_items_almacena_lista(self):
        p = HistorialPresenter()
        p.abrir("estudiantes", 1)
        p.set_items(["item1", "item2"])
        assert p.estado["items"] == ["item1", "item2"]

    def test_set_items_apaga_cargando(self):
        p = HistorialPresenter()
        p.abrir("estudiantes", 1)
        assert p.estado["cargando"] is True
        p.set_items([])
        assert p.estado["cargando"] is False

    def test_set_items_copia_la_lista(self):
        p = HistorialPresenter()
        p.abrir("estudiantes", 1)
        lista_original = ["x"]
        p.set_items(lista_original)
        lista_original.append("y")
        assert len(p.estado["items"]) == 1

    # ── set_error ────────────────────────────────────────────────────────────

    def test_set_error_almacena_mensaje(self):
        p = HistorialPresenter()
        p.abrir("usuarios", 5)
        p.set_error("No se pudo cargar")
        assert p.estado["error"] == "No se pudo cargar"

    def test_set_error_apaga_cargando(self):
        p = HistorialPresenter()
        p.abrir("usuarios", 5)
        p.set_error("Error de conexión")
        assert p.estado["cargando"] is False

    def test_set_error_none_borra_mensaje(self):
        p = HistorialPresenter()
        p.abrir("usuarios", 5)
        p.set_error("Error previo")
        p.set_error(None)
        assert p.estado["error"] is None

    # ── cerrar ────────────────────────────────────────────────────────────────

    def test_cerrar_limpia_estado_completamente(self):
        p = HistorialPresenter()
        p.abrir("usuarios", 5)
        p.set_items(["item"])
        p.cerrar()
        assert p.estado["abierto"] is False
        assert p.estado["cargando"] is False
        assert p.estado["tabla"] is None
        assert p.estado["registro_id"] is None
        assert p.estado["items"] == []
        assert p.estado["error"] is None

    # ── estado inicial ────────────────────────────────────────────────────────

    def test_estado_inicial_cerrado(self):
        p = HistorialPresenter()
        assert p.estado["abierto"] is False
        assert p.estado["cargando"] is False
        assert p.estado["tabla"] is None
        assert p.estado["registro_id"] is None
        assert p.estado["items"] == []
        assert p.estado["error"] is None
