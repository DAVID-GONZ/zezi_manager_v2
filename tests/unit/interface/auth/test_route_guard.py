"""
test_route_guard.py — Tests de autorización central de rutas (paso_35).

Verifica el guard deny-by-default a tres niveles:

1. Unidad de la decisión pura `decidir_acceso` (PUBLICO / sin sesión /
   AUTENTICADO / rol permitido / rol denegado).
2. Contrato de `registrar_pagina`: imposible registrar sin declarar `roles`.
3. Tabla exhaustiva (ruta, rol) → permitido/denegado sobre TODAS las rutas
   registradas. Caza explícitamente:
     - B: /horarios (+variantes) = {director, coordinador, profesor}; admin
          y "autenticado sin rol" → denegado (→ /inicio).
     - C: /evaluacion/configuracion = solo profesor.

El fixture autouse `registro_rutas` (tests/unit/interface/conftest.py) puebla
el registro central antes de estos tests.
"""
from __future__ import annotations

import pytest

from src.domain.models.usuario import Rol
from src.interface.auth import (
    AUTENTICADO,
    PUBLICO,
    registrar_pagina,
    roles_de_ruta,
    rutas_registradas,
)
from src.interface.auth.route_guard import (
    ACCESO_DENEGADO,
    ACCESO_LOGIN,
    ACCESO_OK,
    decidir_acceso,
)

ROLES_SISTEMA = ["admin", "director", "coordinador", "profesor"]


# ── 1. Decisión pura ──────────────────────────────────────────────────────────

def test_publico_siempre_ok_incluso_sin_sesion():
    assert decidir_acceso(PUBLICO, autenticado=False, rol=None) == ACCESO_OK
    assert decidir_acceso(PUBLICO, autenticado=True, rol="admin") == ACCESO_OK


def test_sin_sesion_redirige_a_login():
    assert decidir_acceso(AUTENTICADO, autenticado=False, rol=None) == ACCESO_LOGIN
    roles = frozenset({Rol.DIRECTOR})
    assert decidir_acceso(roles, autenticado=False, rol=None) == ACCESO_LOGIN


def test_autenticado_acepta_cualquier_rol_con_sesion():
    for rol in ROLES_SISTEMA:
        assert decidir_acceso(AUTENTICADO, autenticado=True, rol=rol) == ACCESO_OK


def test_rol_permitido_ok_y_no_permitido_denegado():
    roles = frozenset({Rol.DIRECTOR, Rol.COORDINADOR})
    assert decidir_acceso(roles, autenticado=True, rol="director") == ACCESO_OK
    assert decidir_acceso(roles, autenticado=True, rol="coordinador") == ACCESO_OK
    assert decidir_acceso(roles, autenticado=True, rol="profesor") == ACCESO_DENEGADO
    assert decidir_acceso(roles, autenticado=True, rol="admin") == ACCESO_DENEGADO


def test_autenticado_sin_rol_en_ruta_restringida_denegado():
    """Sesión válida pero rol vacío/desconocido → denegado (→ /inicio)."""
    roles = frozenset({Rol.PROFESOR})
    assert decidir_acceso(roles, autenticado=True, rol=None) == ACCESO_DENEGADO
    assert decidir_acceso(roles, autenticado=True, rol="") == ACCESO_DENEGADO


# ── 2. Contrato deny-by-default de registrar_pagina ───────────────────────────

def test_registrar_sin_roles_es_imposible():
    """`roles` es keyword-only obligatorio: no se puede omitir."""
    def fake():
        pass

    with pytest.raises(TypeError):
        registrar_pagina("/x-sin-roles", fake)  # type: ignore[call-arg]


def test_registrar_con_roles_vacios_rechazado():
    def fake():
        pass

    with pytest.raises(ValueError):
        registrar_pagina("/x-roles-vacios", fake, roles=set())


def test_registrar_con_string_rechazado():
    def fake():
        pass

    with pytest.raises(TypeError):
        registrar_pagina("/x-string", fake, roles="director")  # type: ignore[arg-type]


def test_registrar_con_no_rol_rechazado():
    def fake():
        pass

    with pytest.raises(TypeError):
        registrar_pagina("/x-no-rol", fake, roles={"director"})  # type: ignore[arg-type]


# ── 3. Tabla exhaustiva (ruta, rol) sobre TODAS las rutas registradas ─────────

def _veredicto_para(ruta: str, rol: str | None, *, autenticado: bool) -> str:
    roles = roles_de_ruta(ruta)
    assert roles is not None, f"{ruta} no registrada"
    return decidir_acceso(roles, autenticado=autenticado, rol=rol)


def test_todas_las_rutas_publicas_ok_sin_sesion():
    """Rutas públicas: render directo aun sin sesión."""
    for ruta, roles in rutas_registradas().items():
        if roles is PUBLICO:
            assert _veredicto_para(ruta, None, autenticado=False) == ACCESO_OK


def test_toda_ruta_no_publica_exige_sesion():
    """Sin sesión, cualquier ruta no pública → /login."""
    for ruta, roles in rutas_registradas().items():
        if roles is PUBLICO:
            continue
        assert _veredicto_para(ruta, None, autenticado=False) == ACCESO_LOGIN


def test_tabla_ruta_rol_permitido_o_denegado():
    """
    Para cada ruta registrada y cada rol del sistema, el veredicto coincide con
    la matriz declarada. Recorre el registro COMPLETO (no una lista a mano).
    """
    for ruta, roles in rutas_registradas().items():
        for rol in ROLES_SISTEMA:
            veredicto = _veredicto_para(ruta, rol, autenticado=True)
            if roles is PUBLICO or roles is AUTENTICADO:
                esperado = ACCESO_OK
            elif rol in {r.value for r in roles}:
                esperado = ACCESO_OK
            else:
                esperado = ACCESO_DENEGADO
            assert veredicto == esperado, (
                f"(ruta={ruta}, rol={rol}) → {veredicto}, esperado {esperado}"
            )


# ── B: /horarios y variantes protegidas por la ruta ──────────────────────────

@pytest.mark.parametrize(
    "ruta",
    ["/horarios", "/academico/horarios", "/academico/generar-horario"],
)
def test_horarios_protegido_por_ruta(ruta):
    """B: horarios = {director, coordinador, profesor}; admin y sin-rol denegados."""
    assert _veredicto_para(ruta, "director", autenticado=True) == ACCESO_OK
    assert _veredicto_para(ruta, "coordinador", autenticado=True) == ACCESO_OK
    assert _veredicto_para(ruta, "profesor", autenticado=True) == ACCESO_OK
    assert _veredicto_para(ruta, "admin", autenticado=True) == ACCESO_DENEGADO
    assert _veredicto_para(ruta, None, autenticado=True) == ACCESO_DENEGADO
    assert _veredicto_para(ruta, None, autenticado=False) == ACCESO_LOGIN


# ── C: /evaluacion/configuracion = solo profesor ─────────────────────────────

def test_configuracion_evaluacion_solo_profesor():
    """C: solo profesor accede; los roles institucionales son denegados
    (→ /inicio, sin redirección-sorpresa a /admin/configuracion)."""
    ruta = "/evaluacion/configuracion"
    assert _veredicto_para(ruta, "profesor", autenticado=True) == ACCESO_OK
    assert _veredicto_para(ruta, "director", autenticado=True) == ACCESO_DENEGADO
    assert _veredicto_para(ruta, "coordinador", autenticado=True) == ACCESO_DENEGADO
    assert _veredicto_para(ruta, "admin", autenticado=True) == ACCESO_DENEGADO


def test_admin_solo_inicio_y_rutas_admin():
    """admin (rol de plataforma): /inicio OK, rutas de aula denegadas,
    /admin/auditoria OK."""
    assert _veredicto_para("/inicio", "admin", autenticado=True) == ACCESO_OK
    assert _veredicto_para("/admin/auditoria", "admin", autenticado=True) == ACCESO_OK
    assert _veredicto_para("/estudiantes", "admin", autenticado=True) == ACCESO_DENEGADO
    assert _veredicto_para("/evaluacion/planilla", "admin", autenticado=True) == ACCESO_DENEGADO
