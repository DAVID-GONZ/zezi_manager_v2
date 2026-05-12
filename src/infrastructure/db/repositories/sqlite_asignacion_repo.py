"""
SqliteAsignacionRepository — implementación SQLite de IAsignacionRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.models.asignacion import (
    Asignacion,
    AsignacionInfo,
    FiltroAsignacionesDTO,
)


class SqliteAsignacionRepository(IAsignacionRepository):

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

    # ------------------------------------------------------------------
    # SQL compartido para read model con JOINs
    # ------------------------------------------------------------------

    _INFO_SQL = """
        SELECT
            a.id            AS asignacion_id,
            a.grupo_id,
            g.codigo        AS grupo_codigo,
            a.asignatura_id,
            s.nombre        AS asignatura_nombre,
            a.usuario_id,
            u.nombre_completo AS docente_nombre,
            a.periodo_id,
            p.nombre        AS periodo_nombre,
            p.numero        AS periodo_numero,
            a.activo
        FROM asignaciones a
        JOIN grupos      g ON g.id = a.grupo_id
        JOIN asignaturas s ON s.id = a.asignatura_id
        JOIN usuarios    u ON u.id = a.usuario_id
        JOIN periodos    p ON p.id = a.periodo_id
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_asignacion(self, row: sqlite3.Row) -> Asignacion:
        d = dict(row)
        d["activo"] = bool(d["activo"])
        return Asignacion(**d)

    def _row_to_info(self, row: sqlite3.Row) -> AsignacionInfo:
        d = dict(row)
        d["activo"] = bool(d["activo"])
        return AsignacionInfo(**d)

    # ------------------------------------------------------------------
    # Lectura — entidad de persistencia
    # ------------------------------------------------------------------

    def get_by_id(self, asignacion_id: int) -> Asignacion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM asignaciones WHERE id = ?", (asignacion_id,)
            ).fetchone()
            return self._row_to_asignacion(row) if row else None

    def listar(self, filtro: FiltroAsignacionesDTO) -> list[Asignacion]:
        sql = "SELECT * FROM asignaciones WHERE 1=1"
        params: list = []
        if filtro.solo_activas:
            sql += " AND activo = 1"
        if filtro.usuario_id is not None:
            sql += " AND usuario_id = ?"
            params.append(filtro.usuario_id)
        if filtro.grupo_id is not None:
            sql += " AND grupo_id = ?"
            params.append(filtro.grupo_id)
        if filtro.asignatura_id is not None:
            sql += " AND asignatura_id = ?"
            params.append(filtro.asignatura_id)
        if filtro.periodo_id is not None:
            sql += " AND periodo_id = ?"
            params.append(filtro.periodo_id)
        sql += " ORDER BY id"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_asignacion(r) for r in rows]

    def existe(
        self,
        grupo_id: int,
        asignatura_id: int,
        usuario_id: int,
        periodo_id: int,
    ) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM asignaciones
                WHERE grupo_id = ? AND asignatura_id = ?
                  AND usuario_id = ? AND periodo_id = ?
                """,
                (grupo_id, asignatura_id, usuario_id, periodo_id),
            ).fetchone()
            return row is not None

    # ------------------------------------------------------------------
    # Lectura — read model con JOINs
    # ------------------------------------------------------------------

    def get_info(self, asignacion_id: int) -> AsignacionInfo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                self._INFO_SQL + " WHERE a.id = ?", (asignacion_id,)
            ).fetchone()
            return self._row_to_info(row) if row else None

    def listar_info(self, filtro: FiltroAsignacionesDTO) -> list[AsignacionInfo]:
        sql = self._INFO_SQL + " WHERE 1=1"
        params: list = []
        if filtro.solo_activas:
            sql += " AND a.activo = 1"
        if filtro.usuario_id is not None:
            sql += " AND a.usuario_id = ?"
            params.append(filtro.usuario_id)
        if filtro.grupo_id is not None:
            sql += " AND a.grupo_id = ?"
            params.append(filtro.grupo_id)
        if filtro.asignatura_id is not None:
            sql += " AND a.asignatura_id = ?"
            params.append(filtro.asignatura_id)
        if filtro.periodo_id is not None:
            sql += " AND a.periodo_id = ?"
            params.append(filtro.periodo_id)
        sql += " ORDER BY g.codigo, s.nombre"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_info(r) for r in rows]

    def listar_por_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        solo_activas: bool = True,
    ) -> list[AsignacionInfo]:
        sql = self._INFO_SQL + " WHERE a.grupo_id = ? AND a.periodo_id = ?"
        params: list = [grupo_id, periodo_id]
        if solo_activas:
            sql += " AND a.activo = 1"
        sql += " ORDER BY s.nombre"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_info(r) for r in rows]

    def listar_por_docente(
        self,
        usuario_id: int,
        periodo_id: int | None = None,
        solo_activas: bool = True,
    ) -> list[AsignacionInfo]:
        sql = self._INFO_SQL + " WHERE a.usuario_id = ?"
        params: list = [usuario_id]
        if periodo_id is not None:
            sql += " AND a.periodo_id = ?"
            params.append(periodo_id)
        if solo_activas:
            sql += " AND a.activo = 1"
        sql += " ORDER BY g.codigo, s.nombre"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_info(r) for r in rows]

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def guardar(self, asignacion: Asignacion) -> Asignacion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO asignaciones
                    (grupo_id, asignatura_id, usuario_id, periodo_id, activo)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    asignacion.grupo_id,
                    asignacion.asignatura_id,
                    asignacion.usuario_id,
                    asignacion.periodo_id,
                    int(asignacion.activo),
                ),
            )
            if self._conn is None:
                conn.commit()
            return asignacion.model_copy(update={"id": cursor.lastrowid})

    def desactivar(self, asignacion_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE asignaciones SET activo = 0 WHERE id = ?",
                (asignacion_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def reactivar(self, asignacion_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE asignaciones SET activo = 1 WHERE id = ?",
                (asignacion_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def reasignar_docente(
        self,
        asignacion_id: int,
        nuevo_usuario_id: int,
    ) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE asignaciones SET usuario_id = ? WHERE id = ?",
                (nuevo_usuario_id, asignacion_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0


__all__ = ["SqliteAsignacionRepository"]
