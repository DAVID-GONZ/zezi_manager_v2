"""
SqlitePeriodoRepository — implementación SQLite de IPeriodoRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.models.periodo import HitoPeriodo, Periodo, TipoHito


class SqlitePeriodoRepository(IPeriodoRepository):

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
    # Helpers privados
    # ------------------------------------------------------------------

    def _row_to_periodo(self, row: sqlite3.Row) -> Periodo:
        d = dict(row)
        d["activo"] = bool(d["activo"])
        d["cerrado"] = bool(d["cerrado"])
        return Periodo(**d)

    def _row_to_hito(self, row: sqlite3.Row) -> HitoPeriodo:
        d = dict(row)
        d["tipo"] = TipoHito(d["tipo"])
        return HitoPeriodo(**d)

    # ------------------------------------------------------------------
    # Lectura — periodos
    # ------------------------------------------------------------------

    def get_by_id(self, periodo_id: int) -> Periodo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM periodos WHERE id = ?", (periodo_id,)
            ).fetchone()
            return self._row_to_periodo(row) if row else None

    def get_por_numero(self, anio_id: int, numero: int) -> Periodo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM periodos WHERE anio_id = ? AND numero = ?",
                (anio_id, numero),
            ).fetchone()
            return self._row_to_periodo(row) if row else None

    def get_activo(self, anio_id: int) -> Periodo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM periodos
                WHERE anio_id = ? AND activo = 1 AND cerrado = 0
                ORDER BY numero
                LIMIT 1
                """,
                (anio_id,),
            ).fetchone()
            return self._row_to_periodo(row) if row else None

    def listar_por_anio(
        self, anio_id: int, incluir_cerrados: bool = True
    ) -> list[Periodo]:
        with self._get_conn() as conn:
            sql = "SELECT * FROM periodos WHERE anio_id = ?"
            params: list = [anio_id]
            if not incluir_cerrados:
                sql += " AND cerrado = 0"
            sql += " ORDER BY numero"
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_periodo(r) for r in rows]

    def suma_pesos_otros(
        self, anio_id: int, excluir_periodo_id: int | None = None
    ) -> float:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(peso_porcentual), 0)
                FROM periodos
                WHERE anio_id = ? AND id != COALESCE(?, 0)
                """,
                (anio_id, excluir_periodo_id),
            ).fetchone()
            return float(row[0])

    # ------------------------------------------------------------------
    # Escritura — periodos
    # ------------------------------------------------------------------

    def guardar(self, periodo: Periodo) -> Periodo:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO periodos
                    (anio_id, numero, nombre, fecha_inicio, fecha_fin,
                     peso_porcentual, activo, cerrado, fecha_cierre_real)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    periodo.anio_id,
                    periodo.numero,
                    periodo.nombre,
                    periodo.fecha_inicio.isoformat() if periodo.fecha_inicio else None,
                    periodo.fecha_fin.isoformat() if periodo.fecha_fin else None,
                    periodo.peso_porcentual,
                    int(periodo.activo),
                    int(periodo.cerrado),
                    periodo.fecha_cierre_real.isoformat() if periodo.fecha_cierre_real else None,
                ),
            )
            if self._conn is None:
                conn.commit()
            return periodo.model_copy(update={"id": cursor.lastrowid})

    def actualizar(self, periodo: Periodo) -> Periodo:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE periodos SET
                    nombre = ?, fecha_inicio = ?, fecha_fin = ?,
                    peso_porcentual = ?, activo = ?
                WHERE id = ?
                """,
                (
                    periodo.nombre,
                    periodo.fecha_inicio.isoformat() if periodo.fecha_inicio else None,
                    periodo.fecha_fin.isoformat() if periodo.fecha_fin else None,
                    periodo.peso_porcentual,
                    int(periodo.activo),
                    periodo.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return periodo

    def cerrar(self, periodo_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                UPDATE periodos
                SET cerrado = 1, activo = 0, fecha_cierre_real = datetime('now')
                WHERE id = ?
                """,
                (periodo_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def activar(self, periodo_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE periodos SET activo = 1 WHERE id = ?",
                (periodo_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def desactivar(self, periodo_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE periodos SET activo = 0 WHERE id = ?",
                (periodo_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Lectura — hitos
    # ------------------------------------------------------------------

    def get_hito(self, hito_id: int) -> HitoPeriodo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM hitos_periodo WHERE id = ?", (hito_id,)
            ).fetchone()
            return self._row_to_hito(row) if row else None

    def listar_hitos(
        self, periodo_id: int, tipo: TipoHito | None = None
    ) -> list[HitoPeriodo]:
        with self._get_conn() as conn:
            sql = "SELECT * FROM hitos_periodo WHERE periodo_id = ?"
            params: list = [periodo_id]
            if tipo is not None:
                sql += " AND tipo = ?"
                params.append(tipo.value)
            sql += " ORDER BY fecha_limite NULLS LAST, id"
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_hito(r) for r in rows]

    def listar_hitos_proximos(self, anio_id: int, dias: int = 7) -> list[HitoPeriodo]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT h.*
                FROM hitos_periodo h
                JOIN periodos p ON p.id = h.periodo_id
                WHERE p.anio_id = ?
                  AND h.fecha_limite BETWEEN DATE('now') AND DATE('now', ?)
                ORDER BY h.fecha_limite, h.id
                """,
                (anio_id, f"+{dias} days"),
            ).fetchall()
            return [self._row_to_hito(r) for r in rows]

    # ------------------------------------------------------------------
    # Escritura — hitos
    # ------------------------------------------------------------------

    def guardar_hito(self, hito: HitoPeriodo) -> HitoPeriodo:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO hitos_periodo (periodo_id, tipo, descripcion, fecha_limite)
                VALUES (?, ?, ?, ?)
                """,
                (
                    hito.periodo_id,
                    hito.tipo.value,
                    hito.descripcion,
                    hito.fecha_limite.isoformat() if hito.fecha_limite else None,
                ),
            )
            if self._conn is None:
                conn.commit()
            return hito.model_copy(update={"id": cursor.lastrowid})

    def actualizar_hito(self, hito: HitoPeriodo) -> HitoPeriodo:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE hitos_periodo
                SET tipo = ?, descripcion = ?, fecha_limite = ?
                WHERE id = ?
                """,
                (
                    hito.tipo.value,
                    hito.descripcion,
                    hito.fecha_limite.isoformat() if hito.fecha_limite else None,
                    hito.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return hito

    def eliminar_hito(self, hito_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM hitos_periodo WHERE id = ?", (hito_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

__all__ = ["SqlitePeriodoRepository"]   