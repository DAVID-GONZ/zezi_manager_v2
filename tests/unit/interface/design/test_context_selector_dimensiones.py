"""
test_context_selector_dimensiones.py — paso_40.

Verifica que las dimensiones del chip de contexto se declaran POR PÁGINA
(no por rol), cubriendo:

  1. Lógica pura `dimensiones_visibles` / `seleccion_completa`:
     - Periodo siempre visible (base).
     - Asignatura ⇒ Grupo (implicación).
     - El botón "Aplicar" se habilita con SOLO las dimensiones visibles.
  2. Se eliminó la heurística por rol `mostrar_asignatura=(rol=="profesor")`
     en `layout.py`; el flag llega por parámetro (default True).
  3. Las páginas que muestran el chip declaran sus flags de dimensión por
     PÁGINA: el mismo valor para directivo y profesor (no depende del rol).
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from src.interface.design.components.context_selector import (
    dimensiones_visibles,
    seleccion_completa,
)


# ── 1. Lógica pura de dimensiones ──────────────────────────────────────────────

def test_periodo_siempre_visible():
    per, _, _ = dimensiones_visibles(mostrar_grupo=False, mostrar_asignatura=False)
    assert per is True


def test_asignatura_implica_grupo():
    # Una página que pide asignatura siempre obtiene el paso grupo, aunque
    # mostrar_grupo venga False.
    _, grupo, asig = dimensiones_visibles(mostrar_grupo=False, mostrar_asignatura=True)
    assert grupo is True
    assert asig is True


def test_solo_periodo():
    _, grupo, asig = dimensiones_visibles(mostrar_grupo=False, mostrar_asignatura=False)
    assert grupo is False
    assert asig is False


def test_periodo_y_grupo():
    _, grupo, asig = dimensiones_visibles(mostrar_grupo=True, mostrar_asignatura=False)
    assert grupo is True
    assert asig is False


def test_aplicar_solo_periodo_visible():
    # Página institucional: basta con periodo.
    assert seleccion_completa(
        periodo_id=1, grupo_id=None, asignacion_id=None,
        mostrar_grupo=False, mostrar_asignatura=False,
    ) is True
    assert seleccion_completa(
        periodo_id=None, grupo_id=None, asignacion_id=None,
        mostrar_grupo=False, mostrar_asignatura=False,
    ) is False


def test_aplicar_periodo_grupo_no_exige_asignatura():
    # Página P+G: se habilita sin asignación.
    assert seleccion_completa(
        periodo_id=1, grupo_id=2, asignacion_id=None,
        mostrar_grupo=True, mostrar_asignatura=False,
    ) is True
    # Falta grupo → deshabilitado.
    assert seleccion_completa(
        periodo_id=1, grupo_id=None, asignacion_id=None,
        mostrar_grupo=True, mostrar_asignatura=False,
    ) is False


def test_aplicar_full_exige_asignatura():
    # Página P+G+A: requiere las tres.
    assert seleccion_completa(
        periodo_id=1, grupo_id=2, asignacion_id=3,
        mostrar_grupo=True, mostrar_asignatura=True,
    ) is True
    assert seleccion_completa(
        periodo_id=1, grupo_id=2, asignacion_id=None,
        mostrar_grupo=True, mostrar_asignatura=True,
    ) is False


# ── 2. Heurística por rol eliminada en layout.py ───────────────────────────────

def test_layout_sin_heuristica_por_rol():
    from src.interface.design import layout

    fuente = inspect.getsource(layout)
    assert 'mostrar_asignatura=(usuario_rol == "profesor")' not in fuente
    assert "usuario_rol == \"profesor\"" not in fuente


def test_app_layout_acepta_flags_de_dimension():
    from src.interface.design.layout import app_layout

    params = inspect.signature(app_layout).parameters
    assert "mostrar_grupo" in params
    assert "mostrar_asignatura" in params
    assert params["mostrar_grupo"].default is True
    assert params["mostrar_asignatura"].default is True


# ── 3. Flags declarados por página (no por rol) ────────────────────────────────

_PAGES_DIR = Path(__file__).resolve().parents[4] / "src" / "interface" / "pages"


def _flags_de_app_layout(ruta: Path) -> dict | None:
    """
    Extrae los kwargs mostrar_* de la llamada a app_layout(...) de una página
    mediante AST. Retorna None si la página no llama a app_layout.
    """
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        fn = nodo.func
        if isinstance(fn, ast.Name) and fn.id == "app_layout":
            flags: dict = {}
            for kw in nodo.keywords:
                if kw.arg in ("mostrar_contexto", "mostrar_grupo", "mostrar_asignatura"):
                    if isinstance(kw.value, ast.Constant):
                        flags[kw.arg] = kw.value.value
            return flags
    return None


def test_paginas_con_chip_declaran_dimensiones_validas():
    """
    Toda página que muestra el chip (sin mostrar_contexto=False) debe declarar
    flags coherentes: si pide asignatura, grupo no puede ser explícitamente
    False (la implicación se respeta en el origen declarativo).
    """
    revisadas = 0
    for ruta in _PAGES_DIR.rglob("*.py"):
        flags = _flags_de_app_layout(ruta)
        if flags is None:
            continue
        if flags.get("mostrar_contexto") is False:
            continue  # chip oculto: no aplica
        revisadas += 1
        # Coherencia: asignatura=True nunca con grupo=False explícito.
        if flags.get("mostrar_asignatura") is True:
            assert flags.get("mostrar_grupo") is not False, (
                f"{ruta.name}: declara asignatura sin grupo"
            )
    assert revisadas > 0, "No se encontró ninguna página con chip"


def test_flags_no_dependen_del_rol():
    """
    Los flags de dimensión están fijados como literales en app_layout(...),
    no en ramas condicionales por rol. Garantiza que un directivo y un profesor
    en la misma página ven los mismos pasos del selector.
    """
    sospechosas: list[str] = []
    for ruta in _PAGES_DIR.rglob("*.py"):
        texto = ruta.read_text(encoding="utf-8")
        # mostrar_asignatura/mostrar_grupo nunca deben derivarse del rol.
        for linea in texto.splitlines():
            if "mostrar_asignatura" in linea or "mostrar_grupo" in linea:
                if "usuario_rol" in linea or "es_profesor" in linea or "rol ==" in linea:
                    sospechosas.append(f"{ruta.name}: {linea.strip()}")
    assert not sospechosas, f"Flags derivados del rol: {sospechosas}"
