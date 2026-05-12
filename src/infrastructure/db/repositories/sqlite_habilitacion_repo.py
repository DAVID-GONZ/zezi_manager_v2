"""
SqliteHabilitacionRepository — implementación SQLite de IHabilitacionRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date

from src.domain.ports.habilitacion_repo import IHabilitacionRepository
from src.domain.models.habilitacion import (
    EstadoHabilitacion,
    EstadoPlanMejoramiento,
    FiltroHabilitacionesDTO,
    Habilitacion,
    PlanMejoramiento,
    TipoHabilitacion,
)


class SqliteHabilitacionRepository(IHabilitacionRepository):

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

    def _row_to_habilitacion(self, row: sqlite3.Row) -> Habilitacion:
        d = dict(row)
        d["tipo"] = TipoHabilitacion(d["tipo"])
        d["estado"] = EstadoHabilitacion(d["estado"])
        return Habilitacion(**d)

    def _row_to_plan(self, row: sqlite3.Row) -> PlanMejoramiento:
        d = dict(row)
        d["estado"] = EstadoPlanMejoramiento(d["estado"])
        return PlanMejoramiento(**d)

    # ------------------------------------------------------------------
    # Habilitaciones — lectura
    # ------------------------------------------------------------------

    def get_habilitacion(self, habilitacion_id: int) -> Habilitacion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM habilitaciones WHERE id = ?", (habilitacion_id,)
            ).fetchone()
            return self._row_to_habilitacion(row) if row else None

    def listar_habilitaciones(
        self,
        filtro: FiltroHabilitacionesDTO,
    ) -> list[Habilitacion]:
        sql = "SELECT * FROM habilitaciones WHERE 1=1"
        params: list = []
        if filtro.estudiante_id is not None:
            sql += " AND estudiante_id = ?"
            params.append(filtro.estudiante_id)
        if filtro.asignacion_id is not None:
            sql += " AND asignacion_id = ?"
            params.append(filtro.asignacion_id)
        if filtro.periodo_id is not None:
            sql += " AND periodo_id = ?"
            params.append(filtro.periodo_id)
        if filtro.tipo is not None:
            sql += " AND tipo = ?"
            params.append(filtro.tipo.value)
        if filtro.estado is not None:
            sql += " AND estado = ?"
            params.append(filtro.estado.value)
        sql += " ORDER BY fecha NULLS LAST, id DESC"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_habilitacion(r) for r in rows]

    def listar_por_estudiante(
        self,
        estudiante_id: int,
        periodo_id: int | None = None,
        tipo: TipoHabilitacion | None = None,
    ) -> list[Habilitacion]:
        sql = "SELECT * FROM habilitaciones WHERE estudiante_id = ?"
        params: list = [estudiante_id]
        if periodo_id is not None:
            sql += " AND periodo_id = ?"
            params.append(periodo_id)
        if tipo is not None:
            sql += " AND tipo = ?"
            params.append(tipo.value)
        sql += " ORDER BY fecha NULLS LAST, id"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_habilitacion(r) for r in rows]

    def existe_habilitacion(
        self,
        estudiante_id: int,
        asignacion_id: int,
        tipo: TipoHabilitacion,
        periodo_id: int | None = None,
    ) -> bool:
        sql = """
            SELECT 1 FROM habilitaciones
            WHERE estudiante_id = ? AND asignacion_id = ? AND tipo = ?
        """
        params: list = [estudiante_id, asignacion_id, tipo.value]
        if periodo_id is not None:
            sql += " AND periodo_id = ?"
            params.append(periodo_id)
        else:
            sql += " AND periodo_id IS NULL"
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return row is not None

    # ------------------------------------------------------------------
    # Habilitaciones — escritura
    # ------------------------------------------------------------------

    def guardar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO habilitaciones
                    (estudiante_id, asignacion_id, periodo_id, tipo,
                     nota_antes, nota_habilitacion, fecha, estado,
                     observacion, usuario_registro_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    habilitacion.estudiante_id,
                    habilitacion.asignacion_id,
                    habilitacion.periodo_id,
                    habilitacion.tipo.value,
                    habilitacion.nota_antes,
                    habilitacion.nota_habilitacion,
                    habilitacion.fecha.isoformat() if habilitacion.fecha else None,
                    habilitacion.estado.value,
                    habilitacion.observacion,
                    habilitacion.usuario_registro_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return habilitacion.model_copy(update={"id": cursor.lastrowid})

    def actualizar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE habilitaciones SET
                    nota_antes          = ?,
                    nota_habilitacion   = ?,
                    fecha               = ?,
                    estado              = ?,
                    observacion         = ?,
                    usuario_registro_id = ?
                WHERE id = ?
                """,
                (
                    habilitacion.nota_antes,
                    habilitacion.nota_habilitacion,
                    habilitacion.fecha.isoformat() if habilitacion.fecha else None,
                    habilitacion.estado.value,
                    habilitacion.observacion,
                    habilitacion.usuario_registro_id,
                    habilitacion.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return habilitacion

    def actualizar_estado_habilitacion(
        self,
        habilitacion_id: int,
        estado: EstadoHabilitacion,
    ) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE habilitaciones SET estado = ? WHERE id = ?",
                (estado.value, habilitacion_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Planes de mejoramiento — lectura
    # ------------------------------------------------------------------

    def get_plan(self, plan_id: int) -> PlanMejoramiento | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM planes_mejoramiento WHERE id = ?", (plan_id,)
            ).fetchone()
            return self._row_to_plan(row) if row else None

    def listar_planes_por_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int | None = None,
        estado: EstadoPlanMejoramiento | None = None,
    ) -> list[PlanMejoramiento]:
        sql = "SELECT * FROM planes_mejoramiento WHERE estudiante_id = ?"
        params: list = [estudiante_id]
        if asignacion_id is not None:
            sql += " AND asignacion_id = ?"
            params.append(asignacion_id)
        if estado is not None:
            sql += " AND estado = ?"
            params.append(estado.value)
        sql += " ORDER BY fecha_inicio DESC"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_plan(r) for r in rows]

    def listar_planes_por_seguimiento(
        self,
        fecha_limite: date,
        solo_activos: bool = True,
    ) -> list[PlanMejoramiento]:
        sql = """
            SELECT * FROM planes_mejoramiento
            WHERE fecha_seguimiento IS NOT NULL
              AND fecha_seguimiento <= ?
        """
        params: list = [fecha_limite.isoformat()]
        if solo_activos:
            sql += " AND estado = 'activo'"
        sql += " ORDER BY fecha_seguimiento, id"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_plan(r) for r in rows]

    # ------------------------------------------------------------------
    # Planes de mejoramiento — escritura
    # ------------------------------------------------------------------

    def guardar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO planes_mejoramiento
                    (estudiante_id, asignacion_id, periodo_id,
                     descripcion_dificultad, actividades_propuestas,
                     fecha_inicio, fecha_seguimiento, fecha_cierre,
                     estado, observacion_cierre, usuario_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    plan.estudiante_id,
                    plan.asignacion_id,
                    plan.periodo_id,
                    plan.descripcion_dificultad,
                    plan.actividades_propuestas,
                    plan.fecha_inicio.isoformat(),
                    plan.fecha_seguimiento.isoformat() if plan.fecha_seguimiento else None,
                    plan.fecha_cierre.isoformat() if plan.fecha_cierre else None,
                    plan.estado.value,
                    plan.observacion_cierre,
                    plan.usuario_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return plan.model_copy(update={"id": cursor.lastrowid})

    def actualizar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE planes_mejoramiento SET
                    descripcion_dificultad = ?,
                    actividades_propuestas = ?,
                    fecha_seguimiento      = ?,
                    fecha_cierre           = ?,
                    estado                 = ?,
                    observacion_cierre     = ?
                WHERE id = ?
                """,
                (
                    plan.descripcion_dificultad,
                    plan.actividades_propuestas,
                    plan.fecha_seguimiento.isoformat() if plan.fecha_seguimiento else None,
                    plan.fecha_cierre.isoformat() if plan.fecha_cierre else None,
                    plan.estado.value,
                    plan.observacion_cierre,
                    plan.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return plan


__all__ = ["SqliteHabilitacionRepository"]
