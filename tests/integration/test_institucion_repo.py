"""
Tests de integración — multi-tenant (paso_24).

Cubre:
  - SqliteInstitucionRepository (listar, get, guardar, existe, por_defecto).
  - Seed: institución #1 sembrada desde configuracion.nombre_institucion.
  - usuarios.institucion_id: backfill de existentes + nuevos asignados.
  - Migración idempotente sobre una BD preexistente SIN la columna.
"""
from __future__ import annotations

import sqlite3

from src.infrastructure.db.repositories import (
    SqliteInstitucionRepository,
    SqliteUsuarioRepository,
)
from src.infrastructure.db.schema import SCHEMA, INDICES, _column_exists
from src.infrastructure.db.seed import _seed_institucion
from src.domain.models.institucion import NuevaInstitucionDTO
from src.domain.models.usuario import FiltroUsuariosDTO, NuevoUsuarioDTO


# =============================================================================
# SqliteInstitucionRepository
# =============================================================================

class TestSqliteInstitucionRepository:

    def test_seed_crea_institucion_por_defecto(self, db_conn):
        repo = SqliteInstitucionRepository(conn=db_conn)
        instituciones = repo.listar()
        assert len(instituciones) == 1
        assert instituciones[0].id == 1
        # El nombre proviene de configuracion.nombre_institucion (seed_test).
        assert instituciones[0].nombre == "Institución Educativa ZECI"

    def test_get_por_defecto(self, db_conn):
        repo = SqliteInstitucionRepository(conn=db_conn)
        por_defecto = repo.get_por_defecto()
        assert por_defecto is not None
        assert por_defecto.id == 1

    def test_get_by_id(self, db_conn):
        repo = SqliteInstitucionRepository(conn=db_conn)
        assert repo.get_by_id(1) is not None
        assert repo.get_by_id(999) is None

    def test_guardar_y_existe_nombre(self, db_conn):
        repo = SqliteInstitucionRepository(conn=db_conn)
        nueva = NuevaInstitucionDTO(nombre="Colegio Nuevo", nit="900").to_institucion()
        guardada = repo.guardar(nueva)
        assert guardada.id is not None and guardada.id > 1
        assert repo.existe_nombre("Colegio Nuevo") is True
        assert repo.existe_nombre("colegio nuevo") is True  # case-insensitive
        assert repo.existe_nombre("No Existe") is False

    def test_listar_solo_activas(self, db_conn):
        repo = SqliteInstitucionRepository(conn=db_conn)
        db_conn.execute(
            "INSERT INTO instituciones (nombre, activa) VALUES ('Inactiva', 0)"
        )
        assert len(repo.listar(solo_activas=False)) == 2
        assert len(repo.listar(solo_activas=True)) == 1


# =============================================================================
# usuarios.institucion_id — backfill + nuevos usuarios
# =============================================================================

class TestUsuarioInstitucion:

    def test_usuarios_sembrados_tienen_institucion(self, db_conn):
        repo = SqliteUsuarioRepository(conn=db_conn)
        usuarios = repo.listar_resumenes(FiltroUsuariosDTO(solo_activos=False))
        assert usuarios, "El seed debe crear usuarios"
        for u in usuarios:
            assert u.institucion_id == 1

    def test_usuario_nuevo_persiste_institucion(self, db_conn):
        repo = SqliteUsuarioRepository(conn=db_conn)
        dto = NuevoUsuarioDTO(
            usuario="tenant_user",
            nombre_completo="Tenant User",
            institucion_id=1,
        )
        saved = repo.guardar(dto.to_usuario())
        leido = repo.get_by_id(saved.id)
        assert leido is not None
        assert leido.institucion_id == 1

    def test_filtro_por_institucion(self, db_conn):
        repo = SqliteUsuarioRepository(conn=db_conn)
        # Inserta un usuario en otra institución.
        db_conn.execute("INSERT INTO instituciones (nombre, activa) VALUES ('Otra', 1)")
        otra_id = db_conn.execute(
            "SELECT id FROM instituciones WHERE nombre='Otra'"
        ).fetchone()[0]
        dto = NuevoUsuarioDTO(
            usuario="otro_tenant", nombre_completo="Otro Tenant",
            institucion_id=otra_id,
        )
        repo.guardar(dto.to_usuario())

        en_1 = repo.listar_resumenes(
            FiltroUsuariosDTO(solo_activos=False, institucion_id=1)
        )
        en_otra = repo.listar_resumenes(
            FiltroUsuariosDTO(solo_activos=False, institucion_id=otra_id)
        )
        assert all(u.institucion_id == 1 for u in en_1)
        assert len(en_otra) == 1
        assert en_otra[0].usuario == "otro_tenant"


# =============================================================================
# Migración idempotente sobre BD preexistente SIN la columna
# =============================================================================

class TestMigracionPreexistente:

    def _bd_preexistente(self) -> sqlite3.Connection:
        """BD con usuarios SIN institucion_id y sin tabla instituciones."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            """CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL, nombre_completo TEXT NOT NULL,
                email TEXT, telefono TEXT, rol TEXT NOT NULL,
                activo BOOLEAN NOT NULL DEFAULT 1,
                fecha_creacion DATE NOT NULL DEFAULT CURRENT_DATE,
                ultima_sesion DATETIME)"""
        )
        conn.execute(
            """CREATE TABLE configuracion_anio (
                id INTEGER PRIMARY KEY AUTOINCREMENT, anio INTEGER UNIQUE NOT NULL,
                nombre_institucion TEXT NOT NULL DEFAULT 'X', activo BOOLEAN DEFAULT 1)"""
        )
        conn.execute(
            "INSERT INTO configuracion_anio (anio, nombre_institucion, activo) "
            "VALUES (2025, 'Colegio Preexistente', 1)"
        )
        conn.execute(
            "INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol) "
            "VALUES ('viejo', 'h', 'Usuario Viejo', 'admin')"
        )
        conn.commit()
        return conn

    def _arrancar(self, conn: sqlite3.Connection) -> None:
        """Aplica schema (CREATE IF NOT EXISTS) + micro-migración + seed institución."""
        for s in SCHEMA:
            conn.execute(s)
        if not _column_exists(conn, "usuarios", "institucion_id"):
            conn.execute(
                "ALTER TABLE usuarios ADD COLUMN institucion_id "
                "INTEGER REFERENCES instituciones(id)"
            )
        for s in INDICES:
            try:
                conn.execute(s)
            except sqlite3.OperationalError:
                pass
        _seed_institucion(conn)
        conn.commit()

    def test_migra_sin_perder_datos(self):
        conn = self._bd_preexistente()
        assert not _column_exists(conn, "usuarios", "institucion_id")

        self._arrancar(conn)

        # La columna existe y el usuario preexistente se conserva + backfill.
        assert _column_exists(conn, "usuarios", "institucion_id")
        rows = conn.execute(
            "SELECT usuario, nombre_completo, institucion_id FROM usuarios"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["usuario"] == "viejo"
        assert rows[0]["nombre_completo"] == "Usuario Viejo"
        assert rows[0]["institucion_id"] == 1

        # La institución por defecto toma su nombre de la config preexistente.
        inst = conn.execute("SELECT id, nombre FROM instituciones").fetchall()
        assert len(inst) == 1
        assert inst[0]["nombre"] == "Colegio Preexistente"
        conn.close()

    def test_arranque_es_idempotente(self):
        conn = self._bd_preexistente()
        self._arrancar(conn)
        # Segunda pasada: no duplica institución ni rompe el backfill.
        self._arrancar(conn)
        assert conn.execute("SELECT COUNT(*) FROM instituciones").fetchone()[0] == 1
        assert conn.execute(
            "SELECT institucion_id FROM usuarios WHERE usuario='viejo'"
        ).fetchone()[0] == 1
        conn.close()
