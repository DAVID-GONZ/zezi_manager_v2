"""
SqliteCierreRepository — implementación SQLite de ICierreRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.cierre_repo import ICierreRepository
from src.domain.models.cierre import (
    CierreAnio,
    CierrePeriodo,
    EstadoPromocion,
    PromocionAnual,
)


class SqliteCierreRepository(ICierreRepository):

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

    def _row_to_cierre_periodo(self, row: sqlite3.Row) -> CierrePeriodo:
        return CierrePeriodo(**dict(row))

    def _row_to_cierre_anio(self, row: sqlite3.Row) -> CierreAnio:
        d = dict(row)
        d["perdio"] = bool(d["perdio"])
        return CierreAnio(**d)

    def _row_to_promocion(self, row: sqlite3.Row) -> PromocionAnual:
        d = dict(row)
        d["estado"] = EstadoPromocion(d["estado"])
        return PromocionAnual(**d)

    # ------------------------------------------------------------------
    # Cierre Periodo
    # ------------------------------------------------------------------

    def get_cierre_periodo(
        self, estudiante_id: int, asignacion_id: int, periodo_id: int
    ) -> CierrePeriodo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM cierres_periodo
                WHERE estudiante_id = ? AND asignacion_id = ? AND periodo_id = ?
                """,
                (estudiante_id, asignacion_id, periodo_id),
            ).fetchone()
            return self._row_to_cierre_periodo(row) if row else None

    def listar_cierres_periodo_por_estudiante(
        self, estudiante_id: int, periodo_id: int | None = None
    ) -> list[CierrePeriodo]:
        sql = "SELECT * FROM cierres_periodo WHERE estudiante_id = ?"
        params: list = [estudiante_id]
        if periodo_id is not None:
            sql += " AND periodo_id = ?"
            params.append(periodo_id)
        sql += " ORDER BY periodo_id, asignacion_id"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_cierre_periodo(r) for r in rows]

    def guardar_cierre_periodo(self, cierre: CierrePeriodo) -> CierrePeriodo:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cierres_periodo
                    (estudiante_id, asignacion_id, periodo_id,
                     nota_definitiva, desempeno_id, logro_id,
                     fecha_cierre, usuario_cierre_id)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(estudiante_id, asignacion_id, periodo_id)
                DO UPDATE SET
                    nota_definitiva   = excluded.nota_definitiva,
                    desempeno_id      = excluded.desempeno_id,
                    logro_id          = excluded.logro_id,
                    fecha_cierre      = excluded.fecha_cierre,
                    usuario_cierre_id = excluded.usuario_cierre_id
                """,
                (
                    cierre.estudiante_id,
                    cierre.asignacion_id,
                    cierre.periodo_id,
                    cierre.nota_definitiva,
                    cierre.desempeno_id,
                    cierre.logro_id,
                    cierre.fecha_cierre.isoformat(),
                    cierre.usuario_cierre_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return cierre.model_copy(update={"id": cursor.lastrowid})

    # ------------------------------------------------------------------
    # Cierre Año
    # ------------------------------------------------------------------

    def get_cierre_anio(
        self, estudiante_id: int, asignacion_id: int, anio_id: int
    ) -> CierreAnio | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM cierres_anio
                WHERE estudiante_id = ? AND asignacion_id = ? AND anio_id = ?
                """,
                (estudiante_id, asignacion_id, anio_id),
            ).fetchone()
            return self._row_to_cierre_anio(row) if row else None

    def listar_cierres_anio_por_estudiante(
        self, estudiante_id: int, anio_id: int
    ) -> list[CierreAnio]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM cierres_anio
                WHERE estudiante_id = ? AND anio_id = ?
                ORDER BY asignacion_id
                """,
                (estudiante_id, anio_id),
            ).fetchall()
            return [self._row_to_cierre_anio(r) for r in rows]

    def guardar_cierre_anio(self, cierre: CierreAnio) -> CierreAnio:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cierres_anio
                    (estudiante_id, asignacion_id, anio_id,
                     nota_promedio_periodos, nota_habilitacion,
                     nota_definitiva_anual, perdio, desempeno_id,
                     fecha_cierre, usuario_cierre_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(estudiante_id, asignacion_id, anio_id)
                DO UPDATE SET
                    nota_promedio_periodos = excluded.nota_promedio_periodos,
                    nota_habilitacion      = excluded.nota_habilitacion,
                    nota_definitiva_anual  = excluded.nota_definitiva_anual,
                    perdio                 = excluded.perdio,
                    desempeno_id           = excluded.desempeno_id,
                    fecha_cierre           = excluded.fecha_cierre,
                    usuario_cierre_id      = excluded.usuario_cierre_id
                """,
                (
                    cierre.estudiante_id,
                    cierre.asignacion_id,
                    cierre.anio_id,
                    cierre.nota_promedio_periodos,
                    cierre.nota_habilitacion,
                    cierre.nota_definitiva_anual,
                    int(cierre.perdio),
                    cierre.desempeno_id,
                    cierre.fecha_cierre.isoformat(),
                    cierre.usuario_cierre_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return cierre.model_copy(update={"id": cursor.lastrowid})

    # ------------------------------------------------------------------
    # Promoción Anual
    # ------------------------------------------------------------------

    def get_promocion(
        self, estudiante_id: int, anio_id: int
    ) -> PromocionAnual | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM promocion_anual
                WHERE estudiante_id = ? AND anio_id = ?
                """,
                (estudiante_id, anio_id),
            ).fetchone()
            return self._row_to_promocion(row) if row else None

    def listar_promociones(
        self, anio_id: int, estado: EstadoPromocion | None = None
    ) -> list[PromocionAnual]:
        sql = "SELECT * FROM promocion_anual WHERE anio_id = ?"
        params: list = [anio_id]
        if estado is not None:
            sql += " AND estado = ?"
            params.append(estado.value)
        sql += " ORDER BY estudiante_id"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_promocion(r) for r in rows]

    def guardar_promocion(self, promocion: PromocionAnual) -> PromocionAnual:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO promocion_anual
                    (estudiante_id, anio_id, estado,
                     asignaturas_perdidas, observacion,
                     fecha_decision, usuario_decision_id)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    promocion.estudiante_id,
                    promocion.anio_id,
                    promocion.estado.value,
                    promocion.asignaturas_perdidas,
                    promocion.observacion,
                    promocion.fecha_decision.isoformat() if promocion.fecha_decision else None,
                    promocion.usuario_decision_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return promocion.model_copy(update={"id": cursor.lastrowid})

    def actualizar_promocion(self, promocion: PromocionAnual) -> PromocionAnual:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE promocion_anual SET
                    estado               = ?,
                    asignaturas_perdidas = ?,
                    observacion          = ?,
                    fecha_decision       = ?,
                    usuario_decision_id  = ?
                WHERE id = ?
                """,
                (
                    promocion.estado.value,
                    promocion.asignaturas_perdidas,
                    promocion.observacion,
                    promocion.fecha_decision.isoformat() if promocion.fecha_decision else None,
                    promocion.usuario_decision_id,
                    promocion.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return promocion


__all__ = ["SqliteCierreRepository"]
