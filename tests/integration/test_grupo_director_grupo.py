"""
Tests de integración — director de grupo (convivencia_01).

Cubre el backend puro de `grupos.director_grupo_id` (FK a usuarios,
ON DELETE SET NULL):
  - guardar_grupo persiste director_grupo_id y get_grupo lo relee.
  - actualizar_grupo escribe director_grupo_id (asignar y quitar).
  - listar_grupos hidrata director_grupo_id.
  - ON DELETE SET NULL: al borrar el usuario director, el grupo queda con
    director_grupo_id = NULL (sin romper la FK).
"""
from __future__ import annotations

from src.domain.models.infraestructura import Grupo, Jornada
from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
    SqliteInfraestructuraRepository,
)
from src.services.contexto_tenant import usar_institucion


def _crear_usuario(conn, usuario: str) -> int:
    """Inserta un usuario mínimo (profesor) y retorna su id."""
    cur = conn.execute(
        """
        INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol,
                              institucion_id)
        VALUES (?, 'x', ?, 'profesor', 1)
        """,
        (usuario, f"Docente {usuario}"),
    )
    conn.commit()
    return int(cur.lastrowid)


def test_guardar_y_releer_conserva_director_grupo_id(db_conn):
    """guardar_grupo persiste director_grupo_id; get_grupo lo relee."""
    repo = SqliteInfraestructuraRepository(conn=db_conn)
    uid = _crear_usuario(db_conn, "prof_dir_1")

    with usar_institucion(1):
        g = repo.guardar_grupo(
            Grupo(codigo="DIR100", grado=6, jornada=Jornada.UNICA,
                  institucion_id=1, director_grupo_id=uid)
        )
    releido = repo.get_grupo(g.id)
    assert releido is not None
    assert releido.director_grupo_id == uid


def test_grupo_sin_director_es_none(db_conn):
    """Un grupo sin director asignado se relee con director_grupo_id = None."""
    repo = SqliteInfraestructuraRepository(conn=db_conn)
    with usar_institucion(1):
        g = repo.guardar_grupo(
            Grupo(codigo="DIR101", grado=7, institucion_id=1)
        )
    releido = repo.get_grupo(g.id)
    assert releido is not None
    assert releido.director_grupo_id is None


def test_actualizar_grupo_asigna_y_quita_director(db_conn):
    """actualizar_grupo escribe director_grupo_id (asignar y luego quitar)."""
    repo = SqliteInfraestructuraRepository(conn=db_conn)
    uid = _crear_usuario(db_conn, "prof_dir_2")
    with usar_institucion(1):
        g = repo.guardar_grupo(Grupo(codigo="DIR102", grado=8, institucion_id=1))

    # Asignar director.
    g = repo.get_grupo(g.id)
    repo.actualizar_grupo(g.model_copy(update={"director_grupo_id": uid}))
    assert repo.get_grupo(g.id).director_grupo_id == uid

    # Quitar director.
    repo.actualizar_grupo(g.model_copy(update={"director_grupo_id": None}))
    assert repo.get_grupo(g.id).director_grupo_id is None


def test_listar_grupos_hidrata_director(db_conn):
    """listar_grupos rehidrata director_grupo_id de cada fila."""
    repo = SqliteInfraestructuraRepository(conn=db_conn)
    uid = _crear_usuario(db_conn, "prof_dir_3")
    with usar_institucion(1):
        repo.guardar_grupo(
            Grupo(codigo="DIR103", grado=9, institucion_id=1, director_grupo_id=uid)
        )
        grupos = {g.codigo: g for g in repo.listar_grupos(institucion_id=1)}
    assert grupos["DIR103"].director_grupo_id == uid


def test_on_delete_set_null_al_borrar_usuario(db_conn):
    """Al borrar el usuario director, el grupo queda con director_grupo_id NULL."""
    repo = SqliteInfraestructuraRepository(conn=db_conn)
    uid = _crear_usuario(db_conn, "prof_dir_4")
    with usar_institucion(1):
        g = repo.guardar_grupo(
            Grupo(codigo="DIR104", grado=10, institucion_id=1, director_grupo_id=uid)
        )
    assert repo.get_grupo(g.id).director_grupo_id == uid

    db_conn.execute("DELETE FROM usuarios WHERE id = ?", (uid,))
    db_conn.commit()

    releido = repo.get_grupo(g.id)
    assert releido is not None  # el grupo sigue existiendo
    assert releido.director_grupo_id is None  # FK puesta a NULL
