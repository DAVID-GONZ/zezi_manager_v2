"""
SqliteAsistenciaRepository — implementación SQLite de IAsistenciaRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date

from src.domain.ports.asistencia_repo import IAsistenciaRepository
from src.domain.models.asistencia import (
    ControlDiario,
    EstadoAsistencia,
    ResumenAsistenciaDTO,
)


class SqliteAsistenciaRepository(IAsistenciaRepository):

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

    def _row_to_control(self, row: sqlite3.Row) -> ControlDiario:
        d = dict(row)
        d["estado"] = EstadoAsistencia(d["estado"])
        d["uniforme"] = bool(d["uniforme"])
        d["materiales"] = bool(d["materiales"])
        return ControlDiario(**d)

    def _fmt_hora(self, t) -> str | None:
        if t is None:
            return None
        return t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def registrar(self, control: ControlDiario) -> ControlDiario:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO control_diario
                    (estudiante_id, grupo_id, asignacion_id, periodo_id,
                     fecha, estado, hora_entrada, hora_salida,
                     uniforme, materiales, observacion,
                     usuario_registro_id, fecha_actualizacion)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(estudiante_id, grupo_id, asignacion_id, fecha)
                DO UPDATE SET
                    estado              = excluded.estado,
                    hora_entrada        = excluded.hora_entrada,
                    hora_salida         = excluded.hora_salida,
                    uniforme            = excluded.uniforme,
                    materiales          = excluded.materiales,
                    observacion         = excluded.observacion,
                    usuario_registro_id = excluded.usuario_registro_id,
                    fecha_actualizacion = excluded.fecha_actualizacion
                """,
                (
                    control.estudiante_id,
                    control.grupo_id,
                    control.asignacion_id,
                    control.periodo_id,
                    control.fecha.isoformat(),
                    control.estado.value,
                    self._fmt_hora(control.hora_entrada),
                    self._fmt_hora(control.hora_salida),
                    int(control.uniforme),
                    int(control.materiales),
                    control.observacion,
                    control.usuario_registro_id,
                    control.fecha_actualizacion.isoformat(),
                ),
            )
            if self._conn is None:
                conn.commit()
            return control.model_copy(update={"id": cursor.lastrowid})

    def registrar_masivo(self, controles: list[ControlDiario]) -> int:
        if not controles:
            return 0
        with self._get_conn() as conn:
            conn.executemany(
                """
                INSERT INTO control_diario
                    (estudiante_id, grupo_id, asignacion_id, periodo_id,
                     fecha, estado, hora_entrada, hora_salida,
                     uniforme, materiales, observacion,
                     usuario_registro_id, fecha_actualizacion)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(estudiante_id, grupo_id, asignacion_id, fecha)
                DO UPDATE SET
                    estado              = excluded.estado,
                    hora_entrada        = excluded.hora_entrada,
                    hora_salida         = excluded.hora_salida,
                    uniforme            = excluded.uniforme,
                    materiales          = excluded.materiales,
                    observacion         = excluded.observacion,
                    usuario_registro_id = excluded.usuario_registro_id,
                    fecha_actualizacion = excluded.fecha_actualizacion
                """,
                [
                    (
                        c.estudiante_id,
                        c.grupo_id,
                        c.asignacion_id,
                        c.periodo_id,
                        c.fecha.isoformat(),
                        c.estado.value,
                        self._fmt_hora(c.hora_entrada),
                        self._fmt_hora(c.hora_salida),
                        int(c.uniforme),
                        int(c.materiales),
                        c.observacion,
                        c.usuario_registro_id,
                        c.fecha_actualizacion.isoformat(),
                    )
                    for c in controles
                ],
            )
            if self._conn is None:
                conn.commit()
            return len(controles)

    # ------------------------------------------------------------------
    # Lectura — registro individual
    # ------------------------------------------------------------------

    def get_por_fecha_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int,
        fecha: date,
    ) -> ControlDiario | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM control_diario
                WHERE estudiante_id = ? AND asignacion_id = ? AND fecha = ?
                """,
                (estudiante_id, asignacion_id, fecha.isoformat()),
            ).fetchone()
            return self._row_to_control(row) if row else None

    def listar_por_grupo_y_fecha(
        self,
        grupo_id: int,
        asignacion_id: int,
        fecha: date,
    ) -> list[ControlDiario]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM control_diario
                WHERE grupo_id = ? AND asignacion_id = ? AND fecha = ?
                ORDER BY estudiante_id
                """,
                (grupo_id, asignacion_id, fecha.isoformat()),
            ).fetchall()
            return [self._row_to_control(r) for r in rows]

    def listar_por_estudiante_y_periodo(
        self,
        estudiante_id: int,
        periodo_id: int,
    ) -> list[ControlDiario]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM control_diario
                WHERE estudiante_id = ? AND periodo_id = ?
                ORDER BY fecha, asignacion_id
                """,
                (estudiante_id, periodo_id),
            ).fetchall()
            return [self._row_to_control(r) for r in rows]

    def listar_por_asignacion_y_rango(
        self,
        asignacion_id: int,
        fecha_desde: date,
        fecha_hasta: date,
    ) -> list[ControlDiario]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM control_diario
                WHERE asignacion_id = ?
                  AND fecha BETWEEN ? AND ?
                ORDER BY fecha, estudiante_id
                """,
                (asignacion_id, fecha_desde.isoformat(), fecha_hasta.isoformat()),
            ).fetchall()
            return [self._row_to_control(r) for r in rows]

    # ------------------------------------------------------------------
    # Lectura — resúmenes y estadísticas
    # ------------------------------------------------------------------

    def resumen_por_estudiante(
        self,
        estudiante_id: int,
        periodo_id: int,
        asignacion_id: int | None = None,
    ) -> ResumenAsistenciaDTO:
        sql = """
            SELECT
                estudiante_id,
                COUNT(*)                                     AS total_clases,
                SUM(CASE WHEN estado = 'P'  THEN 1 ELSE 0 END) AS presentes,
                SUM(CASE WHEN estado = 'FJ' THEN 1 ELSE 0 END) AS faltas_justificadas,
                SUM(CASE WHEN estado = 'FI' THEN 1 ELSE 0 END) AS faltas_injustificadas,
                SUM(CASE WHEN estado = 'R'  THEN 1 ELSE 0 END) AS retrasos,
                SUM(CASE WHEN estado = 'E'  THEN 1 ELSE 0 END) AS excusas
            FROM control_diario
            WHERE estudiante_id = ? AND periodo_id = ?
        """
        params: list = [estudiante_id, periodo_id]
        if asignacion_id is not None:
            sql += " AND asignacion_id = ?"
            params.append(asignacion_id)
        sql += " GROUP BY estudiante_id"
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            if not row:
                return ResumenAsistenciaDTO(estudiante_id=estudiante_id)
            return ResumenAsistenciaDTO(**dict(row))

    def resumen_por_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ResumenAsistenciaDTO]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    estudiante_id,
                    COUNT(*)                                        AS total_clases,
                    SUM(CASE WHEN estado = 'P'  THEN 1 ELSE 0 END) AS presentes,
                    SUM(CASE WHEN estado = 'FJ' THEN 1 ELSE 0 END) AS faltas_justificadas,
                    SUM(CASE WHEN estado = 'FI' THEN 1 ELSE 0 END) AS faltas_injustificadas,
                    SUM(CASE WHEN estado = 'R'  THEN 1 ELSE 0 END) AS retrasos,
                    SUM(CASE WHEN estado = 'E'  THEN 1 ELSE 0 END) AS excusas
                FROM control_diario
                WHERE grupo_id = ? AND asignacion_id = ? AND periodo_id = ?
                GROUP BY estudiante_id
                ORDER BY estudiante_id
                """,
                (grupo_id, asignacion_id, periodo_id),
            ).fetchall()
            return [ResumenAsistenciaDTO(**dict(r)) for r in rows]

    def contar_faltas_injustificadas(
        self,
        estudiante_id: int,
        periodo_id: int,
    ) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM control_diario
                WHERE estudiante_id = ? AND periodo_id = ? AND estado = 'FI'
                """,
                (estudiante_id, periodo_id),
            ).fetchone()
            return int(row[0])

    def fechas_con_registro(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[date]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT fecha FROM control_diario
                WHERE asignacion_id = ? AND periodo_id = ?
                ORDER BY fecha
                """,
                (asignacion_id, periodo_id),
            ).fetchall()
            return [date.fromisoformat(r["fecha"]) for r in rows]

    def porcentaje_asistencia_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                                        AS total,
                    SUM(CASE WHEN estado = 'FI' THEN 1
                             WHEN estado = 'R'  THEN 1
                             ELSE 0 END)                           AS ausencias
                FROM control_diario
                WHERE grupo_id = ? AND asignacion_id = ? AND periodo_id = ?
                """,
                (grupo_id, asignacion_id, periodo_id),
            ).fetchone()
            if not row or row["total"] == 0:
                return 0.0
            total = row["total"]
            ausencias = row["ausencias"] or 0
            return round((1 - ausencias / total) * 100, 1)

    def estudiantes_en_riesgo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
        umbral_pct: float = 80.0,
    ) -> list[int]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    estudiante_id,
                    COUNT(*)                                        AS total,
                    SUM(CASE WHEN estado = 'FI' THEN 1
                             WHEN estado = 'R'  THEN 1
                             ELSE 0 END)                           AS ausencias
                FROM control_diario
                WHERE grupo_id = ? AND asignacion_id = ? AND periodo_id = ?
                GROUP BY estudiante_id
                HAVING total > 0
                   AND ROUND((1.0 - CAST(ausencias AS REAL) / total) * 100, 1) < ?
                ORDER BY estudiante_id
                """,
                (grupo_id, asignacion_id, periodo_id, umbral_pct),
            ).fetchall()
            return [r["estudiante_id"] for r in rows]


__all__ = ["SqliteAsistenciaRepository"]
