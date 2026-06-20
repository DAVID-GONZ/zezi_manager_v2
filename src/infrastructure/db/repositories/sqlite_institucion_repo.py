"""
SqliteInstitucionRepository — implementación SQLite de IInstitucionRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.institucion_repo import IInstitucionRepository
from src.domain.models.institucion import Institucion

_COLS = "id, nombre, nit, codigo, activa, fecha_creacion"


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
        d = dict(row)
        d["activa"] = bool(d["activa"])
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
                INSERT INTO instituciones (nombre, nit, codigo, activa, fecha_creacion)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    institucion.nombre,
                    institucion.nit,
                    institucion.codigo,
                    int(institucion.activa),
                    institucion.fecha_creacion.isoformat(),
                ),
            )
            if self._conn is None:
                conn.commit()
            return institucion.model_copy(update={"id": cursor.lastrowid})


__all__ = ["SqliteInstitucionRepository"]
