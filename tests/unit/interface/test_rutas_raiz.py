"""
test_rutas_raiz.py — portal_35: verifica el split limpio de rutas raiz.

R1: `/` registrado como PUBLICO (landing).
R2: `/inicio` registrado como AUTENTICADO (portal); sin sesion → redirect /login.
R5: roles_de_ruta y decidir_acceso como fuente de verdad.

Regresiones de enlaces muertos (revision de diseno):
D2: el buscador del topbar no puede navegar a rutas no registradas.
M9: la landing no puede enlazar anclas sin destino en la propia pagina.
"""
from __future__ import annotations

import re
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[3]


def test_raiz_es_publica():
    """R1 — `/` debe estar registrada con PUBLICO."""
    from src.interface.auth import PUBLICO, roles_de_ruta

    roles = roles_de_ruta("/")
    assert roles is not None, "/ no registrada en el guard"
    assert roles is PUBLICO, f"/ debe ser PUBLICO, pero es {roles!r}"


def test_inicio_es_autenticado():
    """R2/R5 — `/inicio` debe estar registrada con AUTENTICADO (no PUBLICO)."""
    from src.interface.auth import AUTENTICADO, PUBLICO, roles_de_ruta

    roles = roles_de_ruta("/inicio")
    assert roles is not None, "/inicio no registrada en el guard"
    assert roles is not PUBLICO, "/inicio no debe ser PUBLICO tras portal_35"
    assert roles is AUTENTICADO, f"/inicio debe ser AUTENTICADO, pero es {roles!r}"


def test_inicio_sin_sesion_redirige_a_login():
    """R2/R5 — decidir_acceso para /inicio sin sesion debe retornar 'login'."""
    from src.interface.auth import decidir_acceso, roles_de_ruta

    roles = roles_de_ruta("/inicio")
    assert roles is not None
    veredicto = decidir_acceso(roles, autenticado=False, rol=None)
    assert veredicto == "login", (
        f"Sin sesion, /inicio debe redirigir a login, pero decidir_acceso retorno {veredicto!r}"
    )


def test_raiz_sin_sesion_permite_render():
    """R1 — `/` sin sesion debe ser accesible (PUBLICO)."""
    from src.interface.auth import decidir_acceso, roles_de_ruta

    roles = roles_de_ruta("/")
    assert roles is not None
    veredicto = decidir_acceso(roles, autenticado=False, rol=None)
    assert veredicto == "ok", (
        f"Sin sesion, / debe renderizar (ok), pero decidir_acceso retorno {veredicto!r}"
    )


# ── D2: el buscador del topbar no apunta a una ruta inexistente ────────────


def _fuente(*partes: str) -> str:
    return (_RAIZ.joinpath(*partes)).read_text(encoding="utf-8")


def test_topbar_no_navega_a_ruta_no_registrada():
    """D2 — ningun destino de navegacion del layout puede estar fuera del guard.

    `/buscar` no existe (no hay `@ui.page` ni `registrar_pagina` que la declare),
    asi que el buscador global no debe navegar alli mientras no se implemente.
    """
    from src.interface.auth import roles_de_ruta

    fuente = _fuente("src", "interface", "design", "layout.py")
    destinos = set(re.findall(r'ui\.navigate\.to\(\s*f?"(/[^"?]*)', fuente))
    huerfanas = sorted(d for d in destinos if roles_de_ruta(d) is None)
    assert not huerfanas, f"layout.py navega a rutas no registradas: {huerfanas}"


def test_buscador_topbar_operativo_navega_a_buscar():
    """D2 — el buscador global del topbar ya está implementado y navega a `/buscar`.

    Historia: este guard verificaba que el input estuviera deshabilitado mientras
    `/buscar` no existiera. El sistema de búsqueda ya se entregó, así que ahora el
    invariante es el inverso: el buscador está cableado a `/buscar`, que debe estar
    registrada en el guard (no puede ser un enlace muerto).
    """
    from src.interface.auth import roles_de_ruta

    fuente = _fuente("src", "interface", "design", "layout.py")
    bloque = fuente.split("def _topbar_search")[1].split("\ndef ")[0]
    assert "/buscar" in bloque, "el buscador del topbar debe navegar a /buscar"
    assert roles_de_ruta("/buscar") is not None, "/buscar navegada pero no registrada en el guard"


def test_buscador_topbar_oculta_chrome_de_quasar():
    """D5 — el input del buscador oculta el chrome de Quasar (props borderless) y usa
    la clase del repo `topbar-search`, en vez del estilo por defecto de Quasar."""
    fuente = _fuente("src", "interface", "design", "layout.py")
    bloque = fuente.split("def _topbar_search")[1].split("\ndef ")[0]
    assert "borderless" in bloque, "falta props borderless (chrome de Quasar visible)"
    assert "topbar-search" in bloque, "falta la clase topbar-search del input del buscador"


# ── D6: los items clicables del portal son alcanzables por teclado ─────────


def test_items_clicables_del_portal_son_focalizables():
    """D6 — todo div clicable de inicio.py pasa por el helper accesible."""
    fuente = _fuente("src", "interface", "pages", "inicio.py")
    assert 'tabindex="0"' in fuente and 'role="button"' in fuente
    assert "keydown.enter" in fuente and "keydown.space" in fuente
    # Ningun div clicable debe cablear el click por su cuenta, saltandose el helper.
    sueltos = re.findall(r'\.classes\([^)]*\)\s*\.on\(\s*"click"', fuente)
    assert not sueltos, f"divs con click sin _activable(): {sueltos}"


# ── M9: la landing no deja anclas muertas ──────────────────────────────────


def test_landing_sin_anclas_muertas():
    """M9 — cada `#ancla` enlazada debe tener su id declarado en la misma pagina."""
    fuente = _fuente("src", "interface", "pages", "landing.py")
    anclas = set(re.findall(r'ui\.link\([^)]*"#([^"]*)"', fuente))
    ids = set(re.findall(r'id="([^"]+)"', fuente))
    muertas = sorted(a for a in anclas if a == "" or a not in ids)
    assert not muertas, f"landing.py enlaza anclas sin destino: {muertas or ['#']}"
