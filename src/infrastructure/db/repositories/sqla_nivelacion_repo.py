"""Implementación SQLAlchemy Core de INivelacionRepository — AVEDRA v2.0."""
from __future__ import annotations

from sqlalchemy import func, insert, select, update

from src.domain.models.nivelacion import (
    ActividadNivelacion,
    CierreNivelacion,
    NotaNivelacion,
)
from src.domain.ports.nivelacion_repo import INivelacionRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    actividades_nivelacion,
    cierres_nivelacion,
    notas_nivelacion,
)


class SqlaNivelacionRepository(RepositorioBase, INivelacionRepository):
    def __init__(self, conn=None):
        super().__init__(conn, actividades_nivelacion)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_actividad(self, row) -> ActividadNivelacion:
        return ActividadNivelacion(**dict(row))

    def _row_to_nota(self, row) -> NotaNivelacion:
        return NotaNivelacion(**dict(row))

    def _row_to_cierre(self, row) -> CierreNivelacion:
        return CierreNivelacion(**dict(row))

    # ------------------------------------------------------------------
    # ActividadNivelacion
    # ------------------------------------------------------------------

    def guardar_actividad(self, actividad: ActividadNivelacion) -> ActividadNivelacion:
        stmt = insert(actividades_nivelacion).values(
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

    def listar_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ActividadNivelacion]:
        stmt = (
            select(actividades_nivelacion)
            .where(
                actividades_nivelacion.c.asignacion_id == asignacion_id,
                actividades_nivelacion.c.periodo_id == periodo_id,
            )
            .order_by(actividades_nivelacion.c.id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_actividad(r) for r in rows]

    def get_actividad(self, actividad_id: int) -> ActividadNivelacion | None:
        stmt = select(actividades_nivelacion).where(
            actividades_nivelacion.c.id == actividad_id
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_actividad(row) if row else None

    def suma_pesos_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
        excluir_id: int | None = None,
    ) -> float:
        stmt = select(
            func.coalesce(func.sum(actividades_nivelacion.c.peso), 0)
        ).where(
            actividades_nivelacion.c.asignacion_id == asignacion_id,
            actividades_nivelacion.c.periodo_id == periodo_id,
        )
        if excluir_id is not None:
            stmt = stmt.where(actividades_nivelacion.c.id != excluir_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt).scalar()
            return float(result) if result is not None else 0.0

    # ------------------------------------------------------------------
    # NotaNivelacion
    # ------------------------------------------------------------------

    def guardar_nota(self, nota: NotaNivelacion) -> NotaNivelacion:
        stmt = insert(notas_nivelacion).values(
            actividad_nivelacion_id=nota.actividad_nivelacion_id,
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

    def actualizar_nota(self, nota: NotaNivelacion) -> NotaNivelacion:
        stmt = (
            update(notas_nivelacion)
            .where(
                notas_nivelacion.c.actividad_nivelacion_id == nota.actividad_nivelacion_id,
                notas_nivelacion.c.estudiante_id == nota.estudiante_id,
            )
            .values(valor=nota.valor, usuario_id=nota.usuario_id)
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return nota

    def listar_notas_por_actividad(
        self,
        actividad_nivelacion_id: int,
    ) -> list[NotaNivelacion]:
        stmt = (
            select(notas_nivelacion)
            .where(notas_nivelacion.c.actividad_nivelacion_id == actividad_nivelacion_id)
            .order_by(notas_nivelacion.c.estudiante_id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota(r) for r in rows]

    def listar_notas_por_asignacion(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[NotaNivelacion]:
        stmt = (
            select(notas_nivelacion)
            .where(
                notas_nivelacion.c.asignacion_id == asignacion_id,
                notas_nivelacion.c.periodo_id == periodo_id,
            )
            .order_by(
                notas_nivelacion.c.estudiante_id,
                notas_nivelacion.c.actividad_nivelacion_id,
            )
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_nota(r) for r in rows]

    def get_nota(
        self,
        actividad_nivelacion_id: int,
        estudiante_id: int,
    ) -> NotaNivelacion | None:
        stmt = select(notas_nivelacion).where(
            notas_nivelacion.c.actividad_nivelacion_id == actividad_nivelacion_id,
            notas_nivelacion.c.estudiante_id == estudiante_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_nota(row) if row else None

    # ------------------------------------------------------------------
    # CierreNivelacion
    # ------------------------------------------------------------------

    def guardar_cierre(self, cierre: CierreNivelacion) -> CierreNivelacion:
        stmt = insert(cierres_nivelacion).values(
            asignacion_id=cierre.asignacion_id,
            periodo_id=cierre.periodo_id,
            fecha_cierre=cierre.fecha_cierre,
            usuario_cierre_id=cierre.usuario_cierre_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return cierre.model_copy(update={"id": pk})

    def get_cierre(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> CierreNivelacion | None:
        stmt = select(cierres_nivelacion).where(
            cierres_nivelacion.c.asignacion_id == asignacion_id,
            cierres_nivelacion.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_cierre(row) if row else None


__all__ = ["SqlaNivelacionRepository"]
