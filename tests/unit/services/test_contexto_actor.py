"""
Tests unitarios para src/services/contexto_actor.py
(obs_01 — T1 / obs_06 — T1, T2).
"""

from __future__ import annotations

from src.services.contexto_actor import (
    ActorContexto,
    activar_actor,
    actor_actual,
    actor_ip,
    actor_username,
    limpiar_actor,
    usar_actor,
)

# ---------------------------------------------------------------------------
# Tests de obs_01 (retrocompatibles)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tests de obs_06 — tres campos (T1, T2)
# ---------------------------------------------------------------------------

def test_activar_actor_un_argumento_retrocompatible():
    """activar_actor(id) con un solo argumento sigue siendo válido."""
    limpiar_actor()
    activar_actor(42)
    assert actor_actual() == 42
    assert actor_username() is None
    assert actor_ip() is None
    limpiar_actor()


def test_activar_actor_tres_campos():
    """activar_actor(id, username, ip) puebla los tres datos."""
    activar_actor(5, "jperez", "192.168.1.10")
    assert actor_actual() == 5
    assert actor_username() == "jperez"
    assert actor_ip() == "192.168.1.10"
    limpiar_actor()


def test_actor_username_y_actor_ip_devuelven_none_sin_activacion():
    """Sin activar_actor con username/ip, ambos getters devuelven None."""
    limpiar_actor()
    assert actor_username() is None
    assert actor_ip() is None


def test_limpiar_actor_borra_username_e_ip():
    """limpiar_actor() resetea los tres campos a None."""
    activar_actor(7, "admin", "10.0.0.1")
    assert actor_username() == "admin"
    limpiar_actor()
    assert actor_actual() is None
    assert actor_username() is None
    assert actor_ip() is None


def test_usar_actor_con_tres_campos_restaura():
    """usar_actor restaura los tres campos al salir del bloque."""
    activar_actor(1, "user1", "1.1.1.1")
    with usar_actor(2, "user2", "2.2.2.2"):
        assert actor_actual() == 2
        assert actor_username() == "user2"
        assert actor_ip() == "2.2.2.2"
    assert actor_actual() == 1
    assert actor_username() == "user1"
    assert actor_ip() == "1.1.1.1"
    limpiar_actor()


def test_actor_contexto_es_frozen():
    """ActorContexto es inmutable (frozen dataclass)."""
    ctx = ActorContexto(1, "u", "127.0.0.1")
    try:
        ctx.usuario_id = 99  # type: ignore[misc]
        raise AssertionError("Debería haber lanzado FrozenInstanceError")
    except Exception as exc:
        assert "frozen" in str(type(exc).__name__).lower() or "can't" in str(exc).lower()


def test_aislamiento_entre_contextos():
    """Dos contextos independientes no interfieren entre sí."""
    import contextvars

    limpiar_actor()

    resultados = {}

    def capturar(nombre: str, uid: int, uname: str) -> None:
        activar_actor(uid, uname)
        resultados[nombre] = (actor_actual(), actor_username())

    ctx1 = contextvars.copy_context()
    ctx2 = contextvars.copy_context()

    ctx1.run(capturar, "ctx1", 10, "alice")
    ctx2.run(capturar, "ctx2", 20, "bob")

    assert resultados["ctx1"] == (10, "alice")
    assert resultados["ctx2"] == (20, "bob")
    # El contexto principal no fue modificado
    assert actor_actual() is None
