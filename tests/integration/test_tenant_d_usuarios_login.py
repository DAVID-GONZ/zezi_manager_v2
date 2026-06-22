"""
Tests de integración — multi-tenant frente D (paso_37: username global + login
simple, revierte el guard ambiguo de paso_33).

Cubre:
  - crear_usuario valida unicidad GLOBAL del username: el mismo username en DOS
    instituciones FALLA (no se puede repetir en ninguna institución).
  - autenticar_usuario (BcryptAuthService) es simple:
      * username existente → login directo, sin pedir institución; la
        institucion_id del usuario viaja en la entidad retornada.
      * username inexistente o password incorrecto → credenciales_invalidas
        (mensaje genérico, sin divulgación).
  - Sigue habiendo 2 instituciones con aislamiento (institucion_id por usuario y
    por tablas académicas), pero ya NO hay login ambiguo ni selector.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.domain.models.usuario import NuevoUsuarioDTO, Rol
from src.infrastructure.auth.bcrypt_auth_service import BcryptAuthService
from src.infrastructure.db.repositories.sqlite_usuario_repo import (
    SqliteUsuarioRepository,
)
from src.services.contexto_tenant import usar_institucion
from src.services.usuario_service import UsuarioService


def _crear_institucion(conn: sqlite3.Connection, nombre: str) -> int:
    cur = conn.execute(
        "INSERT INTO instituciones (nombre, activa) VALUES (?, 1)", (nombre,)
    )
    return int(cur.lastrowid)


def _svc(conn: sqlite3.Connection) -> tuple[UsuarioService, BcryptAuthService]:
    repo = SqliteUsuarioRepository(conn=conn)
    auth = BcryptAuthService(repo=repo)
    return UsuarioService(repo=repo, auth_service=auth), auth


# =============================================================================
# T2 — Unicidad GLOBAL de creación
# =============================================================================

class TestCreacionGlobal:

    def test_mismo_username_en_dos_instituciones_falla(self, db_conn):
        """Unicidad global: un username no puede repetirse en otra institución."""
        svc, _ = _svc(db_conn)
        otra = _crear_institucion(db_conn, "Colegio B")

        with usar_institucion(1):
            u1 = svc.crear_usuario(
                NuevoUsuarioDTO(usuario="director2", nombre_completo="Dir Uno",
                                rol=Rol.DIRECTOR)
            )
        assert u1.institucion_id == 1

        with usar_institucion(otra):
            with pytest.raises(ValueError, match="Ya existe"):
                svc.crear_usuario(
                    NuevoUsuarioDTO(usuario="director2", nombre_completo="Dir Dos",
                                    rol=Rol.DIRECTOR)
                )

    def test_duplicado_en_misma_institucion_falla(self, db_conn):
        svc, _ = _svc(db_conn)
        with usar_institucion(1):
            svc.crear_usuario(
                NuevoUsuarioDTO(usuario="profe.x", nombre_completo="Profe X")
            )
            with pytest.raises(ValueError, match="Ya existe"):
                svc.crear_usuario(
                    NuevoUsuarioDTO(usuario="profe.x", nombre_completo="Otro X")
                )

    def test_usernames_distintos_en_dos_instituciones_conviven(self, db_conn):
        """El multi-tenant se mantiene: distintos usernames, distinto tenant."""
        svc, _ = _svc(db_conn)
        otra = _crear_institucion(db_conn, "Colegio C")
        with usar_institucion(1):
            u1 = svc.crear_usuario(
                NuevoUsuarioDTO(usuario="profe.uno", nombre_completo="Profe Uno")
            )
        with usar_institucion(otra):
            u2 = svc.crear_usuario(
                NuevoUsuarioDTO(usuario="profe.dos", nombre_completo="Profe Dos")
            )
        assert u1.institucion_id == 1
        assert u2.institucion_id == otra


# =============================================================================
# T3 — Login simple (sin institución)
# =============================================================================

class TestLoginSimple:

    def test_login_entra_sin_institucion(self, db_conn):
        svc, auth = _svc(db_conn)
        with usar_institucion(1):
            svc.crear_usuario(
                NuevoUsuarioDTO(usuario="unico.user", nombre_completo="Único",
                                password="clave123")
            )
        user = auth.autenticar_usuario("unico.user", "clave123")
        assert user.usuario == "unico.user"
        # La institución viaja en la entidad: un username = una institución.
        assert user.institucion_id == 1

    def test_login_usuario_inexistente_falla(self, db_conn):
        _, auth = _svc(db_conn)
        with pytest.raises(ValueError, match="credenciales_invalidas"):
            auth.autenticar_usuario("no.existe", "loquesea")

    def test_password_incorrecto_falla(self, db_conn):
        svc, auth = _svc(db_conn)
        with usar_institucion(1):
            svc.crear_usuario(
                NuevoUsuarioDTO(usuario="passcheck", nombre_completo="Pass",
                                password="correcta")
            )
        with pytest.raises(ValueError, match="credenciales_invalidas"):
            auth.autenticar_usuario("passcheck", "incorrecta")
