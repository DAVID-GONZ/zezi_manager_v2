"""Matriz de completitud ruta × rol (uitest_07) — golden/lock del control de acceso.

A diferencia de `test_route_guard.py::test_tabla_ruta_rol_permitido_o_denegado` —que
DERIVA el veredicto esperado del mismo registro que prueba— aquí la expectativa está
**declarada a mano** e independiente del guard. Eso da dos garantías que la versión
derivada no puede dar:

  1. **Completitud**: si se registra (o elimina) una ruta y no se actualiza esta
     tabla, el test FALLA → obliga a declarar conscientemente el acceso de cada ruta.
  2. **Anti-drift**: si alguien cambia los roles de una ruta ya existente (p. ej. una
     ruta de aula gana `admin` por error), el test FALLA aunque el guard sea coherente
     consigo mismo.

Cuando cambie el acceso de una ruta A PROPÓSITO, actualiza `ACCESO_ESPERADO` en el
mismo commit — ese es justamente el punto de control.
"""
from __future__ import annotations

import pytest

from src.interface.auth import (
    AUTENTICADO,
    PUBLICO,
    roles_de_ruta,
    rutas_registradas,
)
from src.interface.auth.route_guard import (
    ACCESO_DENEGADO,
    ACCESO_LOGIN,
    ACCESO_OK,
    decidir_acceso,
)

# Conjuntos de roles reutilizados (por legibilidad).
_AULA = frozenset({"coordinador", "director", "profesor"})
_DIR_COORD = frozenset({"coordinador", "director"})
_DIR = frozenset({"director"})
_ADMIN = frozenset({"admin"})

# Expectativa declarada: ruta → acceso esperado.
#   "PUBLICO"       → sin sesión
#   "AUTENTICADO"   → cualquier rol con sesión
#   frozenset(...)  → solo esos roles
ACCESO_ESPERADO: dict[str, object] = {
    # ── Públicas ──
    "/": "PUBLICO",
    "/login": "PUBLICO",
    "/logout": "PUBLICO",
    # ── Autenticadas (cualquier rol) ──
    "/inicio": "AUTENTICADO",
    "/buscar": "AUTENTICADO",
    "/cambiar-password": "AUTENTICADO",
    "/mi-cuenta/cambiar-password": "AUTENTICADO",
    "/espera-configuracion": "AUTENTICADO",
    # ── Solo admin de plataforma ──
    "/admin/auditoria": _ADMIN,
    "/admin/instituciones": _ADMIN,
    "/diagnostico": _ADMIN,
    # ── admin + director ──
    "/admin/usuarios": frozenset({"admin", "director"}),
    # ── Solo director ──
    "/admin/asignaturas": _DIR,
    "/admin/configuracion": _DIR,
    "/admin/salas": _DIR,
    "/configuracion-inicial": _DIR,
    "/institucion/configuracion": _DIR,
    # ── Director + coordinador ──
    "/admin/disponibilidad-docente": _DIR_COORD,
    "/admin/grupos": _DIR_COORD,
    "/admin/plan-estudios": _DIR_COORD,
    "/convivencia/configuracion-alertas": _DIR_COORD,
    "/evaluacion/cierre": _DIR_COORD,
    "/evaluacion/cierre-anio": _DIR_COORD,
    "/evaluacion/cierre-periodo": _DIR_COORD,
    "/informes/consolidado-asistencia": _DIR_COORD,
    "/informes/consolidado-notas": _DIR_COORD,
    # ── Solo profesor ──
    "/evaluacion/configuracion": frozenset({"profesor"}),
    # ── Aula (director + coordinador + profesor) ──
    "/academico/generar-horario": _AULA,
    "/academico/horarios": _AULA,
    "/academico/tablero": _AULA,
    "/admin/asignaciones": _AULA,
    "/asistencia": _AULA,
    "/convivencia/alertas": _AULA,
    "/convivencia/categorias": _AULA,
    "/convivencia/comportamiento": _AULA,
    "/convivencia/configuracion": _AULA,
    "/convivencia/notas": _AULA,
    "/convivencia/observaciones": _AULA,
    "/convivencia/plantillas": _AULA,
    "/convivencia/reporte-periodo": _AULA,
    "/convivencia/seguimiento": _AULA,
    "/estudiantes": _AULA,
    "/evaluacion/habilitaciones": _AULA,
    "/evaluacion/planes": _AULA,
    "/evaluacion/planilla": _AULA,
    "/horarios": _AULA,
    "/informes": _AULA,
    "/informes/boletin-anual": _AULA,
    "/informes/boletin-periodo": _AULA,
    "/informes/estadisticos": _AULA,
}

# Principales del sistema: (rol, autenticado).
_PRINCIPALES = [
    ("admin", True),
    ("director", True),
    ("coordinador", True),
    ("profesor", True),
    (None, True),   # sesión válida sin rol reconocido
    (None, False),  # sin sesión
]


def _norm_actual(roles) -> object:
    """Normaliza el valor del registro a la misma forma que ACCESO_ESPERADO."""
    if roles is PUBLICO:
        return "PUBLICO"
    if roles is AUTENTICADO:
        return "AUTENTICADO"
    return frozenset(r.value for r in roles)


def _verdicto_esperado(esperado: object, rol: str | None, autenticado: bool) -> str:
    if not autenticado:
        return ACCESO_OK if esperado == "PUBLICO" else ACCESO_LOGIN
    if esperado in ("PUBLICO", "AUTENTICADO"):
        return ACCESO_OK
    return ACCESO_OK if rol in esperado else ACCESO_DENEGADO


def test_completitud_toda_ruta_registrada_esta_declarada():
    registradas = set(rutas_registradas())
    declaradas = set(ACCESO_ESPERADO)
    sin_declarar = registradas - declaradas
    declaradas_de_mas = declaradas - registradas
    assert not sin_declarar and not declaradas_de_mas, (
        "La matriz de acceso está desincronizada con el registro de rutas.\n"
        f"  Rutas registradas SIN declarar (añádelas a ACCESO_ESPERADO): {sorted(sin_declarar)}\n"
        f"  Rutas declaradas que ya NO existen (elimínalas): {sorted(declaradas_de_mas)}"
    )


@pytest.mark.parametrize("ruta", sorted(ACCESO_ESPERADO))
def test_permisos_sin_drift(ruta):
    """Los roles reales del guard coinciden con los declarados (atrapa cambios de acceso)."""
    actual = roles_de_ruta(ruta)
    assert actual is not None, f"{ruta} declarada pero no registrada"
    assert _norm_actual(actual) == ACCESO_ESPERADO[ruta], (
        f"Acceso de {ruta} cambió respecto a lo declarado. "
        f"Actual={_norm_actual(actual)!r}, declarado={ACCESO_ESPERADO[ruta]!r}. "
        "Si el cambio es intencional, actualiza ACCESO_ESPERADO."
    )


@pytest.mark.parametrize("rol,autenticado", _PRINCIPALES)
def test_matriz_verdicto_por_principal(rol, autenticado):
    """Para CADA ruta y cada principal, el veredicto del guard coincide con lo declarado."""
    for ruta, esperado in ACCESO_ESPERADO.items():
        roles = roles_de_ruta(ruta)
        assert roles is not None, f"{ruta} no registrada"
        veredicto = decidir_acceso(roles, autenticado=autenticado, rol=rol)
        esperado_v = _verdicto_esperado(esperado, rol, autenticado)
        assert veredicto == esperado_v, (
            f"(ruta={ruta}, rol={rol}, auth={autenticado}) → {veredicto}, "
            f"esperado {esperado_v}"
        )
