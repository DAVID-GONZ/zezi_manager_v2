"""Implementación SQLAlchemy Core de IPlanMejoramientoRepository — ZECI Manager v2.0."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, insert, join, select, update

from src.domain.models.plan_mejoramiento import (
    ActividadPlan,
    CortePlan,
    EstadoNotaCorte,
    NotaActividadPlan,
    NotaCortePlan,
)
from src.domain.ports.plan_mejoramiento_repo import IPlanMejoramientoRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    actividades_plan,
    cortes_plan,
    notas_actividad_plan,
    notas_corte_plan,
)


class SqlaPlanMejoramientoRepository(RepositorioBase, IPlanMejoramientoRepository):
    def __init__(self, conn=None):
        super().__init__(conn, cortes_plan)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_corte(self, row) -> CortePlan:
        d = dict(row)
        if isinstance(d.get("fecha_ejecucion"), str):
            d["fecha_ejecucion"] = date.fromisoformat(d["fecha_ejecucion"])
        return CortePlan(**d)

    def _row_to_nota_corte(self, row) -> NotaCortePlan:
        d = dict(row)
        d["estado"] = EstadoNotaCorte(d["estado"])
        return NotaCortePlan(**d)

    def _row_to_actividad(self, row) -> ActividadPlan:
        d = dict(row)
        if isinstance(d.get("fecha"), str):
            d["fecha"] = date.fromisoformat(d["fecha"]) if d["fecha"] else None
        return ActividadPlan(**d)

    def _row_to_nota_actividad(self, row) -> NotaActividadPlan:
        return NotaActividadPlan(**dict(row))

    # ------------------------------------------------------------------
    # Corte
    # ------------------------------------------------------------------

    def guardar_corte(self, corte: CortePlan) -> CortePlan:
        stmt = insert(cortes_plan).values(
            asignacion_id=corte.asignacion_id,
            periodo_id=corte.periodo_id,
            fecha_ejecucion=corte.fecha_ejecucion,
            peso_registrado=float(corte.peso_registrado),
            nota_umbral=float(corte.nota_umbral),
            nota_minima_aprobacion=float(corte.nota_minima_aprobacion),
            usuario_id=corte.usuario_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return corte.model_copy(update={"id": pk})

    def get_corte(self, asignacion_id: int, periodo_id: int) -> CortePlan | None:
        stmt = select(cortes_plan).where(
            cortes_plan.c.asignacion_id == asignacion_id,
            cortes_plan.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_corte(row) if row else None

    def get_corte_by_id(self, corte_id: int) -> CortePlan | None:
        stmt = select(cortes_plan).where(cortes_plan.c.id == corte_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_corte(row) if row else None

    # ------------------------------------------------------------------
    # Notas de corte
    # ------------------------------------------------------------------

    def guardar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan:
        stmt = insert(notas_corte_plan).values(
            corte_id=nota.corte_id,
            estudiante_id=nota.estudiante_id,
            asignacion_id=nota.asignacion_id,
            periodo_id=nota.periodo_id,
            nota_al_corte=float(nota.nota_al_corte),
            nota_definitiva_plan=float(nota.nota_definitiva_plan) if nota.nota_definitiva_plan is not None else None,
            estado=nota.estado.value,
            usuario_cierre_id=nota.usuario_cierre_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return nota.model_copy(update={"id": pk})

    def get_nota_corte(self, corte_id: int, estudiante_id: int) -> NotaCortePlan | None:
        stmt = select(notas_corte_plan).where(
            notas_corte_plan.c.corte_id == corte_id,
            notas_corte_plan.c.estudiante_id == estudiante_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_nota_corte(row) if row else None

    def listar_notas_corte(self, corte_id: int) -> list[NotaCortePlan]:
        stmt = (
            select(notas_corte_plan)
            .where(notas_corte_plan.c.corte_id == corte_id)
            .order_by(notas_corte_plan.c.estudiante_id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota_corte(r) for r in rows]

    def actualizar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan:
        stmt = (
            update(notas_corte_plan)
            .where(
                notas_corte_plan.c.corte_id == nota.corte_id,
                notas_corte_plan.c.estudiante_id == nota.estudiante_id,
            )
            .values(
                nota_definitiva_plan=float(nota.nota_definitiva_plan) if nota.nota_definitiva_plan is not None else None,
                estado=nota.estado.value,
                usuario_cierre_id=nota.usuario_cierre_id,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return nota

    # ------------------------------------------------------------------
    # Actividades del plan
    # ------------------------------------------------------------------

    def guardar_actividad(self, actividad: ActividadPlan) -> ActividadPlan:
        stmt = insert(actividades_plan).values(
            corte_id=actividad.corte_id,
            asignacion_id=actividad.asignacion_id,
            periodo_id=actividad.periodo_id,
            nombre=actividad.nombre,
            descripcion=actividad.descripcion,
            peso=float(actividad.peso),
            fecha=actividad.fecha,
            usuario_id=actividad.usuario_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return actividad.model_copy(update={"id": pk})

    def get_actividad(self, actividad_id: int) -> ActividadPlan | None:
        stmt = select(actividades_plan).where(actividades_plan.c.id == actividad_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_actividad(row) if row else None

    def listar_actividades(self, corte_id: int) -> list[ActividadPlan]:
        stmt = (
            select(actividades_plan)
            .where(actividades_plan.c.corte_id == corte_id)
            .order_by(actividades_plan.c.id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_actividad(r) for r in rows]

    def suma_pesos_actividades(self, corte_id: int, excluir_id: int | None = None) -> float:
        stmt = select(
            func.coalesce(func.sum(actividades_plan.c.peso), 0)
        ).where(actividades_plan.c.corte_id == corte_id)
        if excluir_id is not None:
            stmt = stmt.where(actividades_plan.c.id != excluir_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt).scalar()
            return float(result) if result is not None else 0.0

    # ------------------------------------------------------------------
    # Notas de actividades
    # ------------------------------------------------------------------

    def guardar_nota_actividad(self, nota: NotaActividadPlan) -> NotaActividadPlan:
        stmt = insert(notas_actividad_plan).values(
            actividad_plan_id=nota.actividad_plan_id,
            estudiante_id=nota.estudiante_id,
            asignacion_id=nota.asignacion_id,
            periodo_id=nota.periodo_id,
            valor=nota.valor,
            usuario_id=nota.usuario_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return nota.model_copy(update={"id": pk})

    def get_nota_actividad(
        self, actividad_plan_id: int, estudiante_id: int
    ) -> NotaActividadPlan | None:
        stmt = select(notas_actividad_plan).where(
            notas_actividad_plan.c.actividad_plan_id == actividad_plan_id,
            notas_actividad_plan.c.estudiante_id == estudiante_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_nota_actividad(row) if row else None

    def listar_notas_actividad(self, actividad_plan_id: int) -> list[NotaActividadPlan]:
        stmt = (
            select(notas_actividad_plan)
            .where(notas_actividad_plan.c.actividad_plan_id == actividad_plan_id)
            .order_by(notas_actividad_plan.c.estudiante_id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota_actividad(r) for r in rows]

    def listar_notas_por_corte_estudiante(
        self, corte_id: int, estudiante_id: int
    ) -> list[NotaActividadPlan]:
        # JOIN notas_actividad_plan con actividades_plan para filtrar por corte_id
        j = join(
            notas_actividad_plan,
            actividades_plan,
            notas_actividad_plan.c.actividad_plan_id == actividades_plan.c.id,
        )
        stmt = (
            select(notas_actividad_plan)
            .select_from(j)
            .where(
                actividades_plan.c.corte_id == corte_id,
                notas_actividad_plan.c.estudiante_id == estudiante_id,
            )
            .order_by(notas_actividad_plan.c.actividad_plan_id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota_actividad(r) for r in rows]


__all__ = ["SqlaPlanMejoramientoRepository"]
