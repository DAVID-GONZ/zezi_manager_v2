"""
Tests unitarios para src/services/contexto_actor.py (obs_01 — T1).
"""

from __future__ import annotations

from src.services.contexto_actor import (
    activar_actor,
    actor_actual,
    limpiar_actor,
    usar_actor,
)


def test_actor_actual_retorna_none_por_defecto():
    """Sin ninguna llamada previa, actor_actual() debe ser None."""
    limpiar_actor()  # garantizar estado limpio
    assert actor_actual() is None


def test_activar_actor_setea_el_valor():
    """Tras activar_actor(5), actor_actual() debe retornar 5."""
    activar_actor(5)
    assert actor_actual() == 5
    limpiar_actor()  # cleanup


def test_limpiar_actor_vuelve_a_none():
    """limpiar_actor() debe resetear el valor a None."""
    activar_actor(99)
    assert actor_actual() == 99
    limpiar_actor()
    assert actor_actual() is None


def test_usar_actor_setea_y_restaura():
    """usar_actor(3) debe fijar el actor dentro del bloque y restaurar al salir."""
    limpiar_actor()
    assert actor_actual() is None

    with usar_actor(3):
        assert actor_actual() == 3

    # Al salir del CM el valor debe restaurarse al previo (None)
    assert actor_actual() is None


def test_usar_actor_restaura_valor_previo():
    """usar_actor anidado restaura al valor externo, no a None."""
    activar_actor(10)
    with usar_actor(20):
        assert actor_actual() == 20
    assert actor_actual() == 10
    limpiar_actor()


def test_usar_actor_con_none():
    """usar_actor(None) fija el actor a None y lo restaura al salir."""
    activar_actor(7)
    with usar_actor(None):
        assert actor_actual() is None
    assert actor_actual() == 7
    limpiar_actor()
