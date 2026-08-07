"""
SqliteInstitucionRepository — implementación SQLite de IInstitucionRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.models.institucion import Institucion
from src.domain.ports.institucion_repo import IInstitucionRepository

_COLS = (
    "id, nombre, nit, codigo, activa, fecha_creacion, "
    "nombre_oficial, codigo_dane, rector, direccion, municipio, telefono, "
    "logo_path, logo_url, resolucion_aprobacion, lema, email_institucional, "
    "jornada_principal, tipo_institucion, calendario, "
    "configuracion_inicial_completa"
)


class SqliteInstitucionRepository(IInstitucionRepository):

    def __init__(self, conn: sqlite3.Connection | None = None):
        self._conn = conn

    @contextmanager
    def _get_conn(self):
        if self._conn is not None:
            yield self._conn
        else:
            from src.infrastructure.db.connection import get_connection
            with get_connection() as conn:
                yield conn

    def _row_to_institucion(self, row: sqlite3.Row) -> Institucion:
        from src.domain.models.institucion import JornadaPrincipal, TipoInstitucion, Calendario
        d = dict(row)
        d["activa"] = bool(d["activa"])
        d["configuracion_inicial_completa"] = bool(d.get("configuracion_inicial_completa", 0))
        for field, enum_cls in [
            ("jornada_principal", JornadaPrincipal),
            ("tipo_institucion",  TipoInstitucion),
            ("calendario",        Calendario),
        ]:
            if d.get(field):
                try:
                    d[field] = enum_cls(d[field])
                except ValueError:
                    d[field] = None
        return Institucion(**d)

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_by_id(self, institucion_id: int) -> Institucion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT {_COLS} FROM instituciones WHERE id = ?",
                (institucion_id,),
            ).fetchone()
            return self._row_to_institucion(row) if row else None

    def listar(self, solo_activas: bool = False) -> list[Institucion]:
        sql = f"SELECT {_COLS} FROM instituciones"
        if solo_activas:
            sql += " WHERE activa = 1"
        sql += " ORDER BY id"
        with self._get_conn() as conn:
            rows = conn.execute(sql).fetchall()
            return [self._row_to_institucion(r) for r in rows]

    def existe_nombre(self, nombre: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM instituciones WHERE LOWER(nombre) = LOWER(?)",
                (nombre.strip(),),
            ).fetchone()
            return row is not None

    def get_por_defecto(self) -> Institucion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT {_COLS} FROM instituciones ORDER BY id LIMIT 1"
            ).fetchone()
            return self._row_to_institucion(row) if row else None

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def guardar(self, institucion: Institucion) -> Institucion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO instituciones
                    (nombre, nit, codigo, activa, fecha_creacion,
                     configuracion_inicial_completa)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    institucion.nombre,
                    institucion.nit,
                    institucion.codigo,
                    int(institucion.activa),
                    institucion.fecha_creacion.isoformat(),
                    int(institucion.configuracion_inicial_completa),
                ),
            )
            if self._conn is None:
                conn.commit()
            return institucion.model_copy(update={"id": cursor.lastrowid})

    def actualizar(self, institucion: Institucion) -> Institucion:
        if not institucion.id:
            raise ValueError("La institución debe tener id para actualizar.")
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE instituciones SET
                    nombre=?, nit=?, codigo=?, activa=?,
                    nombre_oficial=?, codigo_dane=?, rector=?,
                    direccion=?, municipio=?, telefono=?,
                    logo_path=?, logo_url=?, resolucion_aprobacion=?,
                    lema=?, email_institucional=?,
                    jornada_principal=?, tipo_institucion=?, calendario=?,
                    configuracion_inicial_completa=?
                WHERE id=?
                """,
                (
                    institucion.nombre, institucion.nit, institucion.codigo,
                    int(institucion.activa),
                    institucion.nombre_oficial, institucion.codigo_dane,
                    institucion.rector, institucion.direccion, institucion.municipio,
                    institucion.telefono, institucion.logo_path, institucion.logo_url,
                    institucion.resolucion_aprobacion, institucion.lema,
                    institucion.email_institucional,
                    institucion.jornada_principal.value if institucion.jornada_principal else None,
                    institucion.tipo_institucion.value if institucion.tipo_institucion else None,
                    institucion.calendario.value if institucion.calendario else None,
                    int(institucion.configuracion_inicial_completa),
                    institucion.id,
                ),
            )
            if self._conn is None:
                conn.commit()
        return institucion

    def sembrar_defaults_tenant(self, institucion_id: int) -> None:
        """
        Siembra catálogos estándar + preferencias por defecto para un tenant
        nuevo (mejora_09a). Reutiliza los seeders idempotentes de
        `src.infrastructure.db.seed` (infra→infra, permitido) con la conexión
        propia del repo.
        """
        from src.infrastructure.db.seed import (
            _seed_catalogos_institucion,
            _seed_preferencias_institucion,
        )
        with self._get_conn() as conn:
            _seed_catalogos_institucion(conn, institucion_id)
            _seed_preferencias_institucion(conn, institucion_id)
            if self._conn is None:
                conn.commit()


__all__ = ["SqliteInstitucionRepository"]
