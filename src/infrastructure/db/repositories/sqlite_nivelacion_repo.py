"""
SqliteNivelacionRepository — implementación SQLite de INivelacionRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.nivelacion_repo import INivelacionRepository
from src.domain.models.nivelacion import (
    ActividadNivelacion,
    CierreNivelacion,
    NotaNivelacion,
)


class SqliteNivelacionRepository(INivelacionRepository):

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
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_actividad(self, row: sqlite3.Row) -> ActividadNivelacion:
        return ActividadNivelacion(**dict(row))

    def _row_to_nota(self, row: sqlite3.Row) -> NotaNivelacion:
        return NotaNivelacion(**dict(row))

    def _row_to_cierre(self, row: sqlite3.Row) -> CierreNivelacion:
        return CierreNivelacion(**dict(row))

    # ------------------------------------------------------------------
    # ActividadNivelacion
    # ------------------------------------------------------------------

    def guardar_actividad(self, actividad: ActividadNivelacion) -> ActividadNivelacion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO actividades_nivelacion
                    (asignacion_id, periodo_id, nombre, descripcion, peso, fecha, usuario_id)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    actividad.asignacion_id,
                    actividad.periodo_id,
                    actividad.nombre,
                    actividad.descripcion,
                    actividad.peso,
                    actividad.fecha.isoformat() if actividad.fecha else None,
                    actividad.usuario_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return actividad.model_copy(update={"id": cursor.lastrowid})

    def listar_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ActividadNivelacion]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM actividades_nivelacion
                WHERE asignacion_id = ? AND periodo_id = ?
                ORDER BY id
                """,
                (asignacion_id, periodo_id),
            ).fetchall()
            return [self._row_to_actividad(r) for r in rows]

    def get_actividad(self, actividad_id: int) -> ActividadNivelacion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM actividades_nivelacion WHERE id = ?",
                (actividad_id,),
            ).fetchone()
            return self._row_to_actividad(row) if row else None

    def suma_pesos_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
        excluir_id: int | None = None,
    ) -> float:
        sql = """
            SELECT COALESCE(SUM(peso), 0)
            FROM actividades_nivelacion
            WHERE asignacion_id = ? AND periodo_id = ?
        """
        params: list = [asignacion_id, periodo_id]
        if excluir_id is not None:
            sql += " AND id != ?"
            params.append(excluir_id)
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return float(row[0]) if row else 0.0

    # ------------------------------------------------------------------
    # NotaNivelacion
    # ------------------------------------------------------------------

    def guardar_nota(self, nota: NotaNivelacion) -> NotaNivelacion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notas_nivelacion
                    (actividad_nivelacion_id, estudiante_id, asignacion_id,
                     periodo_id, valor, usuario_id)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    nota.actividad_nivelacion_id,
                    nota.estudiante_id,
                    nota.asignacion_id,
                    nota.periodo_id,
                    nota.valor,
                    nota.usuario_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return nota.model_copy(update={"id": cursor.lastrowid})

    def actualizar_nota(self, nota: NotaNivelacion) -> NotaNivelacion:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE notas_nivelacion
                SET valor = ?, usuario_id = ?
                WHERE actividad_nivelacion_id = ? AND estudiante_id = ?
                """,
                (nota.valor, nota.usuario_id,
                 nota.actividad_nivelacion_id, nota.estudiante_id),
            )
            if self._conn is None:
                conn.commit()
            return nota

    def listar_notas_por_actividad(
        self,
        actividad_nivelacion_id: int,
    ) -> list[NotaNivelacion]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM notas_nivelacion
                WHERE actividad_nivelacion_id = ?
                ORDER BY estudiante_id
                """,
                (actividad_nivelacion_id,),
            ).fetchall()
            return [self._row_to_nota(r) for r in rows]

    def listar_notas_por_asignacion(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[NotaNivelacion]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM notas_nivelacion
                WHERE asignacion_id = ? AND periodo_id = ?
                ORDER BY estudiante_id, actividad_nivelacion_id
                """,
                (asignacion_id, periodo_id),
            ).fetchall()
            return [self._row_to_nota(r) for r in rows]

    def get_nota(
        self,
        actividad_nivelacion_id: int,
        estudiante_id: int,
    ) -> NotaNivelacion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM notas_nivelacion
                WHERE actividad_nivelacion_id = ? AND estudiante_id = ?
                """,
                (actividad_nivelacion_id, estudiante_id),
            ).fetchone()
            return self._row_to_nota(row) if row else None

    # ------------------------------------------------------------------
    # CierreNivelacion
    # ------------------------------------------------------------------

    def guardar_cierre(self, cierre: CierreNivelacion) -> CierreNivelacion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cierres_nivelacion
                    (asignacion_id, periodo_id, fecha_cierre, usuario_cierre_id)
                VALUES (?,?,?,?)
                """,
                (
                    cierre.asignacion_id,
                    cierre.periodo_id,
                    cierre.fecha_cierre.isoformat(),
                    cierre.usuario_cierre_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return cierre.model_copy(update={"id": cursor.lastrowid})

    def get_cierre(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> CierreNivelacion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM cierres_nivelacion
                WHERE asignacion_id = ? AND periodo_id = ?
                """,
                (asignacion_id, periodo_id),
            ).fetchone()
            return self._row_to_cierre(row) if row else None


__all__ = ["SqliteNivelacionRepository"]
