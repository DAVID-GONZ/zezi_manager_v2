"""
tests/unit/domain/test_modulos.py — Invariantes del registro unico de modulos.

Verifica:
  - modulo_de_ruta devuelve el modulo correcto y None para rutas libres.
  - clave_de_modulo devuelve None para modulos nucleo.
  - toda clave_preferencia declarada esta en CLAVES_CONOCIDAS.
  - ninguna ruta pertenece a dos modulos.
"""
from src.domain.modulos import (
    MODULOS,
    Modulo,
    clave_de_modulo,
    definicion,
    modulo_de_ruta,
    modulos_con_pagina,
    modulos_desactivables,
)


def test_modulo_de_ruta_correcto():
    """modulo_de_ruta devuelve el modulo esperado para rutas conocidas."""
    assert modulo_de_ruta("/asistencia") == Modulo.ASISTENCIA
    assert modulo_de_ruta("/evaluacion/planilla") == Modulo.EVALUACION
    assert modulo_de_ruta("/estudiantes") == Modulo.ACADEMICO
    assert modulo_de_ruta("/convivencia/observaciones") == Modulo.CONVIVENCIA
    assert modulo_de_ruta("/convivencia/reporte-periodo") == Modulo.CONVIVENCIA
    assert modulo_de_ruta("/informes/estadisticos") == Modulo.INFORMES


def test_modulo_de_ruta_none_para_rutas_libres():
    """Rutas no gateadas por ningun modulo devuelven None."""
    assert modulo_de_ruta("/inicio") is None
    assert modulo_de_ruta("/login") is None
    assert modulo_de_ruta("/admin/usuarios") is None
    assert modulo_de_ruta("/no-existe") is None


def test_clave_de_modulo_nucleo():
    """Modulos nucleo devuelven None como clave de preferencia."""
    assert clave_de_modulo("asistencia") is None
    assert clave_de_modulo("evaluacion") is None
    assert clave_de_modulo("academico") is None
    assert clave_de_modulo("informes") is None


def test_clave_de_modulo_desactivable():
    """Modulos desactivables devuelven su clave de preferencia."""
    assert clave_de_modulo("convivencia") == "modulo_convivencia_activo"
    assert clave_de_modulo("alertas") == "modulo_alertas_activo"


def test_clave_de_modulo_inexistente():
    """Un modulo inexistente devuelve None."""
    assert clave_de_modulo("no_existe") is None


def test_claves_preferencia_en_conocidas():
    """Toda clave_preferencia declarada debe estar en CLAVES_CONOCIDAS
    del servicio de preferencias."""
    from src.services.preferencias_institucion_service import CLAVES_CONOCIDAS

    for d in MODULOS.values():
        if d.clave_preferencia is not None:
            assert d.clave_preferencia in CLAVES_CONOCIDAS, (
                f"clave_preferencia {d.clave_preferencia!r} del modulo "
                f"{d.id.value!r} no esta en CLAVES_CONOCIDAS"
            )


def test_ninguna_ruta_en_dos_modulos():
    """Cada ruta pertenece a un unico modulo."""
    ruta_a_modulo: dict[str, str] = {}
    for m, d in MODULOS.items():
        for r in d.rutas:
            if r in ruta_a_modulo:
                raise AssertionError(
                    f"Ruta {r!r} esta en {ruta_a_modulo[r]!r} y en {m.value!r}"
                )
            ruta_a_modulo[r] = m.value


def test_definicion_por_enum_y_string():
    """definicion() acepta tanto Modulo enum como string."""
    d1 = definicion(Modulo.ASISTENCIA)
    d2 = definicion("asistencia")
    assert d1 is not None
    assert d1 is d2


def test_definicion_inexistente():
    """definicion() devuelve None para valores desconocidos."""
    assert definicion("inventado") is None


def test_modulos_desactivables_tienen_clave():
    """Todos los modulos desactivables tienen clave_preferencia no nula."""
    for d in modulos_desactivables():
        assert d.clave_preferencia is not None, (
            f"modulo desactivable {d.id.value!r} sin clave_preferencia"
        )


def test_modulos_con_pagina_tienen_ruta_principal():
    """Todos los modulos con pagina tienen ruta_principal no nula."""
    for d in modulos_con_pagina():
        assert d.ruta_principal is not None, (
            f"modulo con pagina {d.id.value!r} sin ruta_principal"
        )


def test_alertas_sin_pagina():
    """El modulo alertas no tiene pagina propia (R8)."""
    d = definicion(Modulo.ALERTAS)
    assert d is not None
    assert d.ruta_principal is None
    assert d.rutas == frozenset()


def test_alertas_no_genera_tarjeta():
    """El modulo alertas no aparece entre modulos_con_pagina."""
    ids = {d.id for d in modulos_con_pagina()}
    assert Modulo.ALERTAS not in ids
