"""
Tests de integración — multi-tenant frente B4 (paso_32).

Cubre:
  - Scope de catálogos InfraestructuraService.listar_salas / listar_plantillas:
    director (contextvar fijado) ve solo lo suyo; admin (None) ve todo.
  - crear_sala / crear_plantilla_simple asignan la institución del scope.
  - Unicidad compuesta: mismo nombre de sala / plantilla en DOS instituciones
    NO colisiona; duplicarlo en la MISMA institución sí falla.
  - plantilla activa por jornada es por institución (índice único compuesto):
    dos instituciones pueden tener cada una su 'UNICA' activa a la vez.
  - Agregado de convivencia que CRUZA grupos (listar_registros sin grupo ni
    estudiante en el filtro) se scopea por institución vía join a `grupos`.
  - Migración idempotente sobre una BD preexistente (schema viejo, sin
    institucion_id, UNIQUE global de nombre): rebuild de salas y
    plantillas_franja preserva ids, FKs hijos (grupos.sala_id /
    franjas.plantilla_id) intactos (`foreign_key_check` limpio), backfill #1,
    idempotente, y la unicidad compuesta queda habilitada.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.domain.models.convivencia import FiltroConvivenciaDTO
from src.domain.models.infraestructura import Sala
from src.infrastructure.db.repositories.sqlite_convivencia_repo import (
    SqliteConvivenciaRepository,
)
from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
    SqliteInfraestructuraRepository,
)
from src.services.contexto_tenant import usar_institucion
from src.services.convivencia_service import ConvivenciaService
from src.services.infraestructura_service import InfraestructuraService


def _crear_institucion(conn: sqlite3.Connection, nombre: str) -> int:
    cur = conn.execute(
        "INSERT INTO instituciones (nombre, activa) VALUES (?, 1)", (nombre,)
    )
    return int(cur.lastrowid)


def _crear_grupo(conn: sqlite3.Connection, codigo: str, institucion_id: int) -> int:
    cur = conn.execute(
        "INSERT INTO grupos (codigo, grado, jornada, institucion_id) "
        "VALUES (?, 6, 'UNICA', ?)",
        (codigo, institucion_id),
    )
    return int(cur.lastrowid)


def _crear_estudiante(conn: sqlite3.Connection, grupo_id: int, institucion_id: int) -> int:
    cur = conn.execute(
        "INSERT INTO estudiantes (nombre, apellido, numero_documento, grupo_id, "
        "institucion_id) VALUES ('E', 'X', ?, ?, ?)",
        (f"DOC{grupo_id}", grupo_id, institucion_id),
    )
    return int(cur.lastrowid)


def _crear_registro_comportamiento(
    conn: sqlite3.Connection, estudiante_id: int, grupo_id: int, periodo_id: int
) -> None:
    conn.execute(
        "INSERT INTO registro_comportamiento "
        "(estudiante_id, grupo_id, periodo_id, fecha, tipo, descripcion) "
        "VALUES (?, ?, ?, '2025-03-01', 'dificultad', 'evento')",
        (estudiante_id, grupo_id, periodo_id),
    )


# =============================================================================
# T1/T2 — Scope de catálogos salas / plantillas
# =============================================================================

class TestScopeSalasPlantillas:

    def test_listar_salas_director_ve_solo_su_institucion(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = _crear_institucion(db_conn, "Colegio B")

        with usar_institucion(1):
            svc.crear_sala(Sala(nombre="Lab Física", tipo="laboratorio"))
        with usar_institucion(otra_id):
            svc.crear_sala(Sala(nombre="Lab Química", tipo="laboratorio"))

        with usar_institucion(1):
            nombres_1 = {s.nombre for s in svc.listar_salas()}
        assert "Lab Física" in nombres_1
        assert "Lab Química" not in nombres_1

        with usar_institucion(otra_id):
            nombres_b = {s.nombre for s in svc.listar_salas()}
        assert "Lab Química" in nombres_b
        assert "Lab Física" not in nombres_b

        # Admin (sin scope) ve TODAS.
        nombres_admin = {s.nombre for s in svc.listar_salas()}
        assert {"Lab Física", "Lab Química"}.issubset(nombres_admin)

    def test_listar_plantillas_director_ve_solo_su_institucion(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = _crear_institucion(db_conn, "Colegio C")

        with usar_institucion(1):
            svc.crear_plantilla_simple("Mañana A", jornada="AM")
        with usar_institucion(otra_id):
            svc.crear_plantilla_simple("Mañana B", jornada="AM")

        with usar_institucion(1):
            nombres_1 = {p.nombre for p in svc.listar_plantillas()}
        assert "Mañana A" in nombres_1
        assert "Mañana B" not in nombres_1

        with usar_institucion(otra_id):
            nombres_c = {p.nombre for p in svc.listar_plantillas()}
        assert "Mañana B" in nombres_c
        assert "Mañana A" not in nombres_c

        nombres_admin = {p.nombre for p in svc.listar_plantillas()}
        assert {"Mañana A", "Mañana B"}.issubset(nombres_admin)

    def test_crear_asigna_institucion_del_scope(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = _crear_institucion(db_conn, "Colegio D")

        with usar_institucion(otra_id):
            sala = svc.crear_sala(Sala(nombre="Aula 101"))
            plantilla = svc.crear_plantilla_simple("Tarde D", jornada="PM")
        assert sala.institucion_id == otra_id
        assert plantilla.institucion_id == otra_id

    def test_mismo_nombre_sala_dos_instituciones_no_colisiona(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = _crear_institucion(db_conn, "Colegio E")

        with usar_institucion(1):
            s1 = svc.crear_sala(Sala(nombre="Aula 201"))
        with usar_institucion(otra_id):
            s2 = svc.crear_sala(Sala(nombre="Aula 201"))
        assert s1.id != s2.id
        assert s1.institucion_id == 1 and s2.institucion_id == otra_id

    def test_mismo_nombre_sala_misma_institucion_falla(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        with usar_institucion(1):
            svc.crear_sala(Sala(nombre="Aula Única"))
            with pytest.raises(sqlite3.IntegrityError):
                svc.crear_sala(Sala(nombre="Aula Única"))

    def test_mismo_nombre_plantilla_dos_instituciones_no_colisiona(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = _crear_institucion(db_conn, "Colegio F")

        with usar_institucion(1):
            p1 = svc.crear_plantilla_simple("Jornada X", jornada="UNICA")
        with usar_institucion(otra_id):
            p2 = svc.crear_plantilla_simple("Jornada X", jornada="UNICA")
        assert p1.id != p2.id
        assert p1.institucion_id == 1 and p2.institucion_id == otra_id

    def test_plantilla_activa_es_por_institucion(self, db_conn):
        """El índice único de plantilla activa es por (institucion, jornada):
        dos instituciones pueden tener cada una su 'UNICA' activa a la vez."""
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = _crear_institucion(db_conn, "Colegio G")

        with usar_institucion(1):
            p1 = svc.crear_plantilla_simple("Activa 1", jornada="UNICA")
            svc.activar_plantilla(p1.id)
        with usar_institucion(otra_id):
            p2 = svc.crear_plantilla_simple("Activa 2", jornada="UNICA")
            svc.activar_plantilla(p2.id)  # no debe violar el índice único

        with usar_institucion(1):
            act1 = svc.plantilla_activa("UNICA")
        with usar_institucion(otra_id):
            act2 = svc.plantilla_activa("UNICA")
        assert act1 is not None and act1.nombre == "Activa 1"
        assert act2 is not None and act2.nombre == "Activa 2"


# =============================================================================
# T4 — Agregado de convivencia que cruza grupos
# =============================================================================

class TestScopeConvivenciaAgregado:

    def test_listar_registros_cruza_grupos_se_scopea(self, db_conn, seed_result):
        """listar_registros sin grupo/estudiante cruza grupos: el director ve
        solo los de su institución; admin (None) ve todos."""
        repo = SqliteConvivenciaRepository(conn=db_conn)
        svc = ConvivenciaService(repo)
        periodo_id = seed_result.periodo_ids[0]

        otra_id = _crear_institucion(db_conn, "Colegio H")
        # Institución #1: grupo + estudiante + registro
        g1 = _crear_grupo(db_conn, "INST1-G", 1)
        e1 = _crear_estudiante(db_conn, g1, 1)
        _crear_registro_comportamiento(db_conn, e1, g1, periodo_id)
        # Institución H: grupo + estudiante + registro
        g2 = _crear_grupo(db_conn, "INSTH-G", otra_id)
        e2 = _crear_estudiante(db_conn, g2, otra_id)
        _crear_registro_comportamiento(db_conn, e2, g2, periodo_id)

        filtro = FiltroConvivenciaDTO()  # cruza grupos (sin grupo ni estudiante)

        with usar_institucion(1):
            grupos_1 = {r.grupo_id for r in svc.listar_registros(filtro)}
        assert g1 in grupos_1
        assert g2 not in grupos_1

        with usar_institucion(otra_id):
            grupos_h = {r.grupo_id for r in svc.listar_registros(filtro)}
        assert g2 in grupos_h
        assert g1 not in grupos_h

        # Admin (sin scope) ve los de ambas instituciones.
        grupos_admin = {r.grupo_id for r in svc.listar_registros(filtro)}
        assert {g1, g2}.issubset(grupos_admin)

    def test_contar_registros_respeta_scope(self, db_conn, seed_result):
        repo = SqliteConvivenciaRepository(conn=db_conn)
        periodo_id = seed_result.periodo_ids[0]
        otra_id = _crear_institucion(db_conn, "Colegio I")

        g1 = _crear_grupo(db_conn, "I1-G", 1)
        e1 = _crear_estudiante(db_conn, g1, 1)
        _crear_registro_comportamiento(db_conn, e1, g1, periodo_id)
        g2 = _crear_grupo(db_conn, "II-G", otra_id)
        e2 = _crear_estudiante(db_conn, g2, otra_id)
        _crear_registro_comportamiento(db_conn, e2, g2, periodo_id)
        _crear_registro_comportamiento(db_conn, e2, g2, periodo_id)

        filtro = FiltroConvivenciaDTO()
        assert repo.contar_registros(filtro, institucion_id=1) == 1
        assert repo.contar_registros(filtro, institucion_id=otra_id) == 2


# =============================================================================
# T1/T2 — Migración idempotente sobre BD preexistente (schema viejo)
# =============================================================================

# Schema antiguo (pre-paso_32): salas.nombre y plantillas_franja.nombre UNIQUE
# globales, sin institucion_id. Más las tablas hijas mínimas para validar que
# los FKs sobreviven al rebuild.
_SCHEMA_VIEJO = [
    """
    CREATE TABLE instituciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        activa BOOLEAN NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE salas (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre    TEXT    NOT NULL UNIQUE,
        tipo      TEXT    NOT NULL DEFAULT 'aula',
        capacidad INTEGER NOT NULL DEFAULT 30
    )
    """,
    """
    CREATE TABLE grupos (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo  TEXT    NOT NULL,
        sala_id INTEGER,
        FOREIGN KEY(sala_id) REFERENCES salas(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE plantillas_franja (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre       TEXT    NOT NULL UNIQUE,
        jornada      TEXT    NOT NULL DEFAULT 'UNICA',
        dias_activos TEXT    NOT NULL DEFAULT 'Lunes',
        activa       INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE franjas (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        plantilla_id INTEGER NOT NULL,
        orden        INTEGER NOT NULL,
        FOREIGN KEY(plantilla_id) REFERENCES plantillas_franja(id) ON DELETE CASCADE
    )
    """,
]


def _bd_vieja_con_datos() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    for sql in _SCHEMA_VIEJO:
        conn.execute(sql)
    conn.execute("INSERT INTO instituciones (nombre) VALUES ('Institución #1')")
    # Salas con ids no contiguos (verificar preservación).
    conn.execute("INSERT INTO salas (id, nombre, tipo) VALUES (4, 'Aula A', 'aula')")
    conn.execute("INSERT INTO salas (id, nombre, tipo) VALUES (9, 'Lab', 'laboratorio')")
    # Grupos que referencian salas(id) por sala_id.
    conn.execute("INSERT INTO grupos (id, codigo, sala_id) VALUES (1, '601', 4)")
    conn.execute("INSERT INTO grupos (id, codigo, sala_id) VALUES (2, '602', 9)")
    # Plantillas con ids no contiguos + franjas hijas.
    conn.execute(
        "INSERT INTO plantillas_franja (id, nombre, jornada) VALUES (5, 'PA', 'UNICA')"
    )
    conn.execute(
        "INSERT INTO plantillas_franja (id, nombre, jornada) VALUES (11, 'PB', 'AM')"
    )
    conn.execute("INSERT INTO franjas (id, plantilla_id, orden) VALUES (1, 5, 1)")
    conn.execute("INSERT INTO franjas (id, plantilla_id, orden) VALUES (2, 11, 1)")
    conn.commit()
    return conn

