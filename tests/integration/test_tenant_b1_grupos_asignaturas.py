"""
Tests de integración — multi-tenant frente B1 (paso_29).

Cubre:
  - Scope de InfraestructuraService.listar_grupos / listar_asignaturas:
    director (contextvar fijado) ve solo lo suyo; admin (None) ve todo.
  - guardar_grupo / guardar_asignatura asignan la institución del scope.
  - Unicidad compuesta: mismo codigo de grupo / mismo nombre de asignatura en
    DOS instituciones NO colisiona.
  - Migración idempotente sobre una BD preexistente (schema viejo, sin
    institucion_id, UNIQUE global): rebuild preserva ids, FKs hijos
    (estudiantes/asignaciones/control_diario) intactos (`foreign_key_check`
    limpio), backfill #1, idempotente.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.domain.models.infraestructura import Asignatura, Grupo, Jornada
from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
    SqliteInfraestructuraRepository,
)
from src.services.contexto_tenant import usar_institucion
from src.services.infraestructura_service import InfraestructuraService


# =============================================================================
# Scope desde el contextvar — listados auto-scopeados
# =============================================================================

class TestScopeGruposAsignaturas:

    def _crear_institucion(self, conn, nombre: str) -> int:
        cur = conn.execute(
            "INSERT INTO instituciones (nombre, activa) VALUES (?, 1)", (nombre,)
        )
        return int(cur.lastrowid)

    def test_listar_grupos_director_ve_solo_su_institucion(self, db_conn):
        """Con scope=institución, listar_grupos filtra; admin (None) ve todo."""
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = self._crear_institucion(db_conn, "Colegio B")

        # Crear grupos en ambas instituciones (scope vía contextvar).
        with usar_institucion(1):
            svc.guardar_grupo(Grupo(codigo="A100", grado=6, jornada=Jornada.UNICA))
        with usar_institucion(otra_id):
            svc.guardar_grupo(Grupo(codigo="B100", grado=6, jornada=Jornada.UNICA))

        # Director de la institución 1 ve solo los suyos.
        with usar_institucion(1):
            codigos_1 = {g.codigo for g in svc.listar_grupos()}
        assert "A100" in codigos_1
        assert "B100" not in codigos_1

        # Director de la otra institución ve solo el suyo.
        with usar_institucion(otra_id):
            codigos_b = {g.codigo for g in svc.listar_grupos()}
        assert codigos_b == {"B100"}

        # Admin (sin scope) ve TODO.
        codigos_admin = {g.codigo for g in svc.listar_grupos()}
        assert {"A100", "B100"}.issubset(codigos_admin)

    def test_listar_asignaturas_director_ve_solo_su_institucion(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = self._crear_institucion(db_conn, "Colegio C")

        with usar_institucion(1):
            svc.guardar_asignatura(Asignatura(nombre="Robótica", codigo="ROB1"))
        with usar_institucion(otra_id):
            svc.guardar_asignatura(Asignatura(nombre="Astronomía", codigo="AST1"))

        with usar_institucion(1):
            nombres_1 = {a.nombre for a in svc.listar_asignaturas()}
        assert "Robótica" in nombres_1
        assert "Astronomía" not in nombres_1

        with usar_institucion(otra_id):
            nombres_c = {a.nombre for a in svc.listar_asignaturas()}
        assert "Astronomía" in nombres_c
        assert "Robótica" not in nombres_c

        # Admin ve todas.
        nombres_admin = {a.nombre for a in svc.listar_asignaturas()}
        assert {"Robótica", "Astronomía"}.issubset(nombres_admin)

    def test_guardar_asigna_institucion_del_scope(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = self._crear_institucion(db_conn, "Colegio D")

        with usar_institucion(otra_id):
            g = svc.guardar_grupo(Grupo(codigo="D200", grado=7))
            a = svc.guardar_asignatura(Asignatura(nombre="Filosofía"))
        assert g.institucion_id == otra_id
        assert a.institucion_id == otra_id

    def test_mismo_codigo_grupo_dos_instituciones_no_colisiona(self, db_conn):
        """UNIQUE(institucion_id, codigo): mismo codigo en dos tenants es válido."""
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = self._crear_institucion(db_conn, "Colegio E")

        with usar_institucion(1):
            g1 = svc.guardar_grupo(Grupo(codigo="601", grado=6))
        with usar_institucion(otra_id):
            g2 = svc.guardar_grupo(Grupo(codigo="601", grado=6))
        assert g1.id != g2.id
        assert g1.institucion_id == 1 and g2.institucion_id == otra_id

    def test_mismo_codigo_grupo_misma_institucion_falla(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        with usar_institucion(1):
            svc.guardar_grupo(Grupo(codigo="UNICO1", grado=6))
            with pytest.raises(sqlite3.IntegrityError):
                svc.guardar_grupo(Grupo(codigo="UNICO1", grado=7))

    def test_mismo_nombre_asignatura_dos_instituciones_no_colisiona(self, db_conn):
        repo = SqliteInfraestructuraRepository(conn=db_conn)
        svc = InfraestructuraService(repo)
        otra_id = self._crear_institucion(db_conn, "Colegio F")

        with usar_institucion(1):
            a1 = svc.guardar_asignatura(Asignatura(nombre="Matemáticas", codigo="MAT9"))
        with usar_institucion(otra_id):
            a2 = svc.guardar_asignatura(Asignatura(nombre="Matemáticas", codigo="MAT9"))
        assert a1.id != a2.id
        assert a1.institucion_id == 1 and a2.institucion_id == otra_id


# =============================================================================
# Migración idempotente sobre BD preexistente (schema viejo)
# =============================================================================

# Schema antiguo (pre-paso_29): grupos.codigo UNIQUE global, asignaturas.nombre
# y codigo UNIQUE globales, sin institucion_id. Más las tablas hijas mínimas
# para validar que los FKs sobreviven al rebuild.
_SCHEMA_VIEJO = [
    """
    CREATE TABLE instituciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        activa BOOLEAN NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE areas_conocimiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        codigo TEXT UNIQUE
    )
    """,
    """
    CREATE TABLE asignaturas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT    NOT NULL UNIQUE,
        codigo          TEXT    UNIQUE,
        area_id         INTEGER,
        horas_semanales INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(area_id) REFERENCES areas_conocimiento(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE grupos (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo           TEXT    NOT NULL UNIQUE,
        nombre           TEXT,
        grado            INTEGER,
        jornada          TEXT    NOT NULL DEFAULT 'UNICA',
        capacidad_maxima INTEGER NOT NULL DEFAULT 40
    )
    """,
    """
    CREATE TABLE estudiantes (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre   TEXT    NOT NULL,
        grupo_id INTEGER,
        FOREIGN KEY(grupo_id) REFERENCES grupos(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE asignaciones (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        grupo_id      INTEGER NOT NULL,
        asignatura_id INTEGER NOT NULL,
        FOREIGN KEY(grupo_id)      REFERENCES grupos(id)      ON DELETE CASCADE,
        FOREIGN KEY(asignatura_id) REFERENCES asignaturas(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE control_diario (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        grupo_id INTEGER NOT NULL,
        FOREIGN KEY(grupo_id) REFERENCES grupos(id) ON DELETE CASCADE
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
    # Áreas + asignaturas (ids específicos para verificar preservación).
    conn.execute("INSERT INTO areas_conocimiento (nombre, codigo) VALUES ('Mat', 'M')")
    conn.execute(
        "INSERT INTO asignaturas (id, nombre, codigo, area_id) VALUES (7, 'Álgebra', 'ALG', 1)"
    )
    conn.execute(
        "INSERT INTO asignaturas (id, nombre, codigo, area_id) VALUES (9, 'Lengua', 'LEN', 1)"
    )
    # Grupos con ids no contiguos.
    conn.execute("INSERT INTO grupos (id, codigo, grado) VALUES (3, '601', 6)")
    conn.execute("INSERT INTO grupos (id, codigo, grado) VALUES (8, '1101', 11)")
    # Hijos que referencian grupos(id) y asignaturas(id).
    conn.execute("INSERT INTO estudiantes (id, nombre, grupo_id) VALUES (1, 'Ana', 3)")
    conn.execute("INSERT INTO estudiantes (id, nombre, grupo_id) VALUES (2, 'Luis', 8)")
    conn.execute(
        "INSERT INTO asignaciones (id, grupo_id, asignatura_id) VALUES (1, 3, 7)"
    )
    conn.execute(
        "INSERT INTO asignaciones (id, grupo_id, asignatura_id) VALUES (2, 8, 9)"
    )
    conn.execute("INSERT INTO control_diario (id, grupo_id) VALUES (1, 3)")
    conn.commit()
    return conn

