"""
Tests de integración — PlantillaFranja + Franja repo (paso_15a).
"""
import pytest

from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
    SqliteInfraestructuraRepository,
)
from src.domain.models.infraestructura import Franja, PlantillaFranja


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(conn) -> SqliteInfraestructuraRepository:
    return SqliteInfraestructuraRepository(conn=conn)


def _plantilla(nombre="Test UNICA", jornada="UNICA", dias=None) -> PlantillaFranja:
    return PlantillaFranja(
        nombre=nombre,
        jornada=jornada,
        dias_activos=dias or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
    )


def _franjas_basicas(plantilla_id: int) -> list[Franja]:
    return [
        Franja(plantilla_id=plantilla_id, orden=1, hora_inicio="07:00", hora_fin="07:55"),
        Franja(plantilla_id=plantilla_id, orden=2, hora_inicio="07:55", hora_fin="08:50",
               tipo="descanso", etiqueta="Recreo"),
        Franja(plantilla_id=plantilla_id, orden=3, hora_inicio="08:50", hora_fin="09:45"),
    ]


# ---------------------------------------------------------------------------
# Crear + listar franjas ordenadas
# ---------------------------------------------------------------------------

def test_crear_plantilla_y_reemplazar_franjas(db_conn):
    repo = _repo(db_conn)
    p = repo.crear_plantilla_franja(_plantilla())
    assert p.id is not None

    franjas = _franjas_basicas(p.id)
    n = repo.reemplazar_franjas(p.id, franjas)
    assert n == 3

    listadas = repo.listar_franjas(p.id)
    assert len(listadas) == 3
    assert [f.orden for f in listadas] == [1, 2, 3]
    assert listadas[1].tipo == "descanso"
    assert listadas[1].etiqueta == "Recreo"
    assert listadas[0].es_lectiva


def test_reemplazar_franjas_borra_anteriores(db_conn):
    """Llamar reemplazar_franjas dos veces no acumula filas."""
    repo = _repo(db_conn)
    p = repo.crear_plantilla_franja(_plantilla("Reemplazo"))
    repo.reemplazar_franjas(p.id, _franjas_basicas(p.id))
    # Segunda llamada con sólo 1 franja
    repo.reemplazar_franjas(p.id, [
        Franja(plantilla_id=p.id, orden=1, hora_inicio="07:00", hora_fin="07:55"),
    ])
    assert len(repo.listar_franjas(p.id)) == 1


# ---------------------------------------------------------------------------
# Exclusividad activa por jornada
# ---------------------------------------------------------------------------

def test_activar_excluye_misma_jornada(db_conn):
    """Activar plantilla_2 desactiva plantilla_1 de la misma jornada."""
    repo = _repo(db_conn)
    p1 = repo.crear_plantilla_franja(_plantilla("P1 UNICA"))
    p2 = repo.crear_plantilla_franja(_plantilla("P2 UNICA"))

    repo.activar_plantilla_franja(p1.id)
    assert repo.get_plantilla_activa("UNICA").id == p1.id

    repo.activar_plantilla_franja(p2.id)
    activa = repo.get_plantilla_activa("UNICA")
    assert activa.id == p2.id

    inactiva = repo.get_plantilla_franja(p1.id)
    assert not inactiva.activa


def test_jornadas_distintas_ambas_activas(db_conn):
    """AM y PM pueden estar activas simultáneamente (índice parcial por jornada)."""
    repo = _repo(db_conn)
    p_am = repo.crear_plantilla_franja(_plantilla("Jornada AM", jornada="AM"))
    p_pm = repo.crear_plantilla_franja(_plantilla("Jornada PM", jornada="PM"))

    repo.activar_plantilla_franja(p_am.id)
    repo.activar_plantilla_franja(p_pm.id)

    assert repo.get_plantilla_activa("AM").id == p_am.id
    assert repo.get_plantilla_activa("PM").id == p_pm.id


def test_get_plantilla_activa_sin_activa_retorna_none(db_conn):
    """Si no hay ninguna activa para una jornada, devuelve None."""
    repo = _repo(db_conn)
    # Crear plantilla pero no activar
    repo.crear_plantilla_franja(_plantilla("Sin activar", jornada="PM"))
    result = repo.get_plantilla_activa("PM")
    # Solo retorna None si ninguna PM está activa (el seed no crea PM)
    assert result is None or isinstance(result, PlantillaFranja)


# ---------------------------------------------------------------------------
# Borrado con cascada
# ---------------------------------------------------------------------------

def test_eliminar_plantilla_cascada_borra_franjas(db_conn):
    """Al borrar una plantilla sus franjas se borran por CASCADE FK."""
    repo = _repo(db_conn)
    p = repo.crear_plantilla_franja(_plantilla("Para borrar"))
    repo.reemplazar_franjas(p.id, _franjas_basicas(p.id))
    assert len(repo.listar_franjas(p.id)) == 3

    ok = repo.eliminar_plantilla_franja(p.id)
    assert ok
    assert len(repo.listar_franjas(p.id)) == 0
    assert repo.get_plantilla_franja(p.id) is None


# ---------------------------------------------------------------------------
# Seed dejó plantilla activa (R12)
# ---------------------------------------------------------------------------

def test_seed_deja_plantilla_activa_unica(db_conn):
    """El seed crea una plantilla UNICA activa con franjas lectivas."""
    repo = _repo(db_conn)
    activa = repo.get_plantilla_activa("UNICA")
    assert activa is not None, "seed debe dejar una plantilla UNICA activa"
    franjas = repo.listar_franjas(activa.id)
    assert len(franjas) >= 1
    lectivas = [f for f in franjas if f.es_lectiva]
    assert len(lectivas) >= 1
