"""Implementación SQLite del repositorio de Plan de Mejoramiento."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Generator

from src.domain.models.plan_mejoramiento import (
    ActividadPlan,
    CortePlan,
    EstadoNotaCorte,
    NotaActividadPlan,
    NotaCortePlan,
)
from src.domain.ports.plan_mejoramiento_repo import IPlanMejoramientoRepository


def _db_path() -> Path:
    from src.infrastructure.db.connection import DB_PATH
    return DB_PATH


@contextmanager
def _get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_corte(row: sqlite3.Row) -> CortePlan:
    d = dict(row)
    return CortePlan(
        id=d["id"],
        asignacion_id=d["asignacion_id"],
        periodo_id=d["periodo_id"],
        fecha_ejecucion=date.fromisoformat(d["fecha_ejecucion"]) if d["fecha_ejecucion"] else date.today(),
        peso_registrado=d["peso_registrado"],
        nota_umbral=d["nota_umbral"],
        nota_minima_aprobacion=d["nota_minima_aprobacion"],
        usuario_id=d["usuario_id"],
    )


def _row_to_nota_corte(row: sqlite3.Row) -> NotaCortePlan:
    d = dict(row)
    return NotaCortePlan(
        id=d["id"],
        corte_id=d["corte_id"],
        estudiante_id=d["estudiante_id"],
        asignacion_id=d["asignacion_id"],
        periodo_id=d["periodo_id"],
        nota_al_corte=d["nota_al_corte"],
        nota_definitiva_plan=d["nota_definitiva_plan"],
        estado=EstadoNotaCorte(d["estado"]),
        usuario_cierre_id=d["usuario_cierre_id"],
    )


def _row_to_actividad(row: sqlite3.Row) -> ActividadPlan:
    d = dict(row)
    return ActividadPlan(
        id=d["id"],
        corte_id=d["corte_id"],
        asignacion_id=d["asignacion_id"],
        periodo_id=d["periodo_id"],
        nombre=d["nombre"],
        descripcion=d["descripcion"],
        peso=d["peso"],
        fecha=date.fromisoformat(d["fecha"]) if d["fecha"] else None,
        usuario_id=d["usuario_id"],
    )


def _row_to_nota_actividad(row: sqlite3.Row) -> NotaActividadPlan:
    d = dict(row)
    return NotaActividadPlan(
        id=d["id"],
        actividad_plan_id=d["actividad_plan_id"],
        estudiante_id=d["estudiante_id"],
        asignacion_id=d["asignacion_id"],
        periodo_id=d["periodo_id"],
        valor=d["valor"],
        usuario_id=d["usuario_id"],
    )


class SqlitePlanMejoramientoRepository(IPlanMejoramientoRepository):

    # ------------------------------------------------------------------
    # Corte
    # ------------------------------------------------------------------

    def guardar_corte(self, corte: CortePlan) -> CortePlan:
        with _get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO cortes_plan
                   (asignacion_id, periodo_id, fecha_ejecucion,
                    peso_registrado, nota_umbral, nota_minima_aprobacion, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    corte.asignacion_id, corte.periodo_id,
                    corte.fecha_ejecucion.isoformat(),
                    corte.peso_registrado, corte.nota_umbral,
                    corte.nota_minima_aprobacion, corte.usuario_id,
                ),
            )
            return corte.model_copy(update={"id": cur.lastrowid})

    def get_corte(self, asignacion_id: int, periodo_id: int) -> CortePlan | None:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM cortes_plan WHERE asignacion_id=? AND periodo_id=?",
                (asignacion_id, periodo_id),
            ).fetchone()
            return _row_to_corte(row) if row else None

    def get_corte_by_id(self, corte_id: int) -> CortePlan | None:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM cortes_plan WHERE id=?", (corte_id,)
            ).fetchone()
            return _row_to_corte(row) if row else None

    # ------------------------------------------------------------------
    # Notas de corte
    # ------------------------------------------------------------------

    def guardar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan:
        with _get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO notas_corte_plan
                   (corte_id, estudiante_id, asignacion_id, periodo_id,
                    nota_al_corte, nota_definitiva_plan, estado, usuario_cierre_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    nota.corte_id, nota.estudiante_id,
                    nota.asignacion_id, nota.periodo_id,
                    nota.nota_al_corte, nota.nota_definitiva_plan,
                    nota.estado.value, nota.usuario_cierre_id,
                ),
            )
            return nota.model_copy(update={"id": cur.lastrowid})

    def get_nota_corte(self, corte_id: int, estudiante_id: int) -> NotaCortePlan | None:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM notas_corte_plan WHERE corte_id=? AND estudiante_id=?",
                (corte_id, estudiante_id),
            ).fetchone()
            return _row_to_nota_corte(row) if row else None

    def listar_notas_corte(self, corte_id: int) -> list[NotaCortePlan]:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM notas_corte_plan WHERE corte_id=? ORDER BY estudiante_id",
                (corte_id,),
            ).fetchall()
            return [_row_to_nota_corte(r) for r in rows]

    def actualizar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan:
        with _get_conn() as conn:
            conn.execute(
                """UPDATE notas_corte_plan
                   SET nota_definitiva_plan=?, estado=?, usuario_cierre_id=?
                   WHERE corte_id=? AND estudiante_id=?""",
                (
                    nota.nota_definitiva_plan, nota.estado.value,
                    nota.usuario_cierre_id,
                    nota.corte_id, nota.estudiante_id,
                ),
            )
            return nota

    # ------------------------------------------------------------------
    # Actividades del plan
    # ------------------------------------------------------------------

    def guardar_actividad(self, actividad: ActividadPlan) -> ActividadPlan:
        with _get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO actividades_plan
                   (corte_id, asignacion_id, periodo_id, nombre, descripcion,
                    peso, fecha, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    actividad.corte_id, actividad.asignacion_id, actividad.periodo_id,
                    actividad.nombre, actividad.descripcion, actividad.peso,
                    actividad.fecha.isoformat() if actividad.fecha else None,
                    actividad.usuario_id,
                ),
            )
            return actividad.model_copy(update={"id": cur.lastrowid})

    def get_actividad(self, actividad_id: int) -> ActividadPlan | None:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM actividades_plan WHERE id=?", (actividad_id,)
            ).fetchone()
            return _row_to_actividad(row) if row else None

    def listar_actividades(self, corte_id: int) -> list[ActividadPlan]:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM actividades_plan WHERE corte_id=? ORDER BY id",
                (corte_id,),
            ).fetchall()
            return [_row_to_actividad(r) for r in rows]

    def suma_pesos_actividades(self, corte_id: int, excluir_id: int | None = None) -> float:
        with _get_conn() as conn:
            if excluir_id is not None:
                row = conn.execute(
                    "SELECT COALESCE(SUM(peso), 0) FROM actividades_plan WHERE corte_id=? AND id!=?",
                    (corte_id, excluir_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COALESCE(SUM(peso), 0) FROM actividades_plan WHERE corte_id=?",
                    (corte_id,),
                ).fetchone()
            return float(row[0]) if row else 0.0

    # ------------------------------------------------------------------
    # Notas de actividades
    # ------------------------------------------------------------------

    def guardar_nota_actividad(self, nota: NotaActividadPlan) -> NotaActividadPlan:
        with _get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO notas_actividad_plan
                   (actividad_plan_id, estudiante_id, asignacion_id,
                    periodo_id, valor, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    nota.actividad_plan_id, nota.estudiante_id,
                    nota.asignacion_id, nota.periodo_id,
                    nota.valor, nota.usuario_id,
                ),
            )
            return nota.model_copy(update={"id": cur.lastrowid})

    def get_nota_actividad(
        self, actividad_plan_id: int, estudiante_id: int
    ) -> NotaActividadPlan | None:
        with _get_conn() as conn:
            row = conn.execute(
                """SELECT * FROM notas_actividad_plan
                   WHERE actividad_plan_id=? AND estudiante_id=?""",
                (actividad_plan_id, estudiante_id),
            ).fetchone()
            return _row_to_nota_actividad(row) if row else None

    def listar_notas_actividad(self, actividad_plan_id: int) -> list[NotaActividadPlan]:
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM notas_actividad_plan
                   WHERE actividad_plan_id=? ORDER BY estudiante_id""",
                (actividad_plan_id,),
            ).fetchall()
            return [_row_to_nota_actividad(r) for r in rows]

    def listar_notas_por_corte_estudiante(
        self, corte_id: int, estudiante_id: int
    ) -> list[NotaActividadPlan]:
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT nap.*
                   FROM notas_actividad_plan nap
                   JOIN actividades_plan ap ON ap.id = nap.actividad_plan_id
                   WHERE ap.corte_id=? AND nap.estudiante_id=?
                   ORDER BY nap.actividad_plan_id""",
                (corte_id, estudiante_id),
            ).fetchall()
            return [_row_to_nota_actividad(r) for r in rows]
