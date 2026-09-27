"""Implementación SQLAlchemy Core de IHabilitacionRepository — ZECI Manager v2.0."""
from __future__ import annotations

from datetime import date

from sqlalchemy import insert, select, update

from src.domain.models.habilitacion import (
    EstadoHabilitacion,
    EstadoPlanMejoramiento,
    FiltroHabilitacionesDTO,
    Habilitacion,
    PlanMejoramiento,
    TipoHabilitacion,
)
from src.domain.models.tenant import TenantScope
from src.domain.ports.habilitacion_repo import IHabilitacionRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    estudiantes,
    habilitaciones,
    planes_mejoramiento,
)


class SqlaHabilitacionRepository(RepositorioBase, IHabilitacionRepository):
    def __init__(self, conn=None):
        super().__init__(conn, habilitaciones)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_habilitacion(self, row) -> Habilitacion:
        d = dict(row)
        d["tipo"] = TipoHabilitacion(d["tipo"])
        d["estado"] = EstadoHabilitacion(d["estado"])
        return Habilitacion(**d)

    def _row_to_plan(self, row) -> PlanMejoramiento:
        d = dict(row)
        d["estado"] = EstadoPlanMejoramiento(d["estado"])
        return PlanMejoramiento(**d)

    # ------------------------------------------------------------------
    # Habilitaciones — lectura
    # ------------------------------------------------------------------

    def get_habilitacion(self, habilitacion_id: int) -> Habilitacion | None:
        stmt = select(habilitaciones).where(habilitaciones.c.id == habilitacion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_habilitacion(row) if row else None

    def listar_habilitaciones(
        self,
        filtro: FiltroHabilitacionesDTO,
    ) -> list[Habilitacion]:
        stmt = select(habilitaciones)
        if isinstance(filtro.institucion_id, int):
            subq = select(estudiantes.c.id).where(
                estudiantes.c.institucion_id == filtro.institucion_id
            )
            stmt = stmt.where(habilitaciones.c.estudiante_id.in_(subq))
        if filtro.estudiante_id is not None:
            stmt = stmt.where(habilitaciones.c.estudiante_id == filtro.estudiante_id)
        if filtro.asignacion_id is not None:
            stmt = stmt.where(habilitaciones.c.asignacion_id == filtro.asignacion_id)
        if filtro.periodo_id is not None:
            stmt = stmt.where(habilitaciones.c.periodo_id == filtro.periodo_id)
        if filtro.tipo is not None:
            stmt = stmt.where(habilitaciones.c.tipo == filtro.tipo.value)
        if filtro.estado is not None:
            stmt = stmt.where(habilitaciones.c.estado == filtro.estado.value)
        stmt = stmt.order_by(
            habilitaciones.c.fecha.asc().nulls_last(),
            habilitaciones.c.id.desc(),
        )
        offset = (filtro.pagina - 1) * filtro.por_pagina
        stmt = stmt.limit(filtro.por_pagina).offset(offset)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_habilitacion(r) for r in rows]

    def listar_por_estudiante(
        self,
        estudiante_id: int,
        periodo_id: int | None = None,
        tipo: TipoHabilitacion | None = None,
    ) -> list[Habilitacion]:
        stmt = select(habilitaciones).where(
            habilitaciones.c.estudiante_id == estudiante_id
        )
        if periodo_id is not None:
            stmt = stmt.where(habilitaciones.c.periodo_id == periodo_id)
        if tipo is not None:
            stmt = stmt.where(habilitaciones.c.tipo == tipo.value)
        stmt = stmt.order_by(
            habilitaciones.c.fecha.asc().nulls_last(),
            habilitaciones.c.id,
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_habilitacion(r) for r in rows]

    def existe_habilitacion(
        self,
        estudiante_id: int,
        asignacion_id: int,
        tipo: TipoHabilitacion,
        periodo_id: int | None = None,
    ) -> bool:
        stmt = select(habilitaciones.c.id).where(
            habilitaciones.c.estudiante_id == estudiante_id,
            habilitaciones.c.asignacion_id == asignacion_id,
            habilitaciones.c.tipo == tipo.value,
        )
        if periodo_id is not None:
            stmt = stmt.where(habilitaciones.c.periodo_id == periodo_id)
        else:
            stmt = stmt.where(habilitaciones.c.periodo_id.is_(None))
        with self._get_conn() as conn:
            row = conn.execute(stmt).first()
            return row is not None

    # ------------------------------------------------------------------
    # Habilitaciones — escritura
    # ------------------------------------------------------------------

    def guardar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion:
        stmt = insert(habilitaciones).values(
            estudiante_id=habilitacion.estudiante_id,
            asignacion_id=habilitacion.asignacion_id,
            periodo_id=habilitacion.periodo_id,
            tipo=habilitacion.tipo.value,
            nota_antes=float(habilitacion.nota_antes) if habilitacion.nota_antes is not None else None,
            nota_habilitacion=float(habilitacion.nota_habilitacion) if habilitacion.nota_habilitacion is not None else None,
            fecha=habilitacion.fecha,
            estado=habilitacion.estado.value,
            observacion=habilitacion.observacion,
            usuario_registro_id=habilitacion.usuario_registro_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return habilitacion.model_copy(update={"id": pk})

    def actualizar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion:
        stmt = (
            update(habilitaciones)
            .where(habilitaciones.c.id == habilitacion.id)
            .values(
                nota_antes=float(habilitacion.nota_antes) if habilitacion.nota_antes is not None else None,
                nota_habilitacion=float(habilitacion.nota_habilitacion) if habilitacion.nota_habilitacion is not None else None,
                fecha=habilitacion.fecha,
                estado=habilitacion.estado.value,
                observacion=habilitacion.observacion,
                usuario_registro_id=habilitacion.usuario_registro_id,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return habilitacion

    def actualizar_estado_habilitacion(
        self,
        habilitacion_id: int,
        estado: EstadoHabilitacion,
    ) -> bool:
        stmt = (
            update(habilitaciones)
            .where(habilitaciones.c.id == habilitacion_id)
            .values(estado=estado.value)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Planes de mejoramiento — lectura
    # ------------------------------------------------------------------

    def get_plan(self, plan_id: int) -> PlanMejoramiento | None:
        stmt = select(planes_mejoramiento).where(planes_mejoramiento.c.id == plan_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_plan(row) if row else None

    def listar_planes_por_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int | None = None,
        estado: EstadoPlanMejoramiento | None = None,
    ) -> list[PlanMejoramiento]:
        stmt = select(planes_mejoramiento).where(
            planes_mejoramiento.c.estudiante_id == estudiante_id
        )
        if asignacion_id is not None:
            stmt = stmt.where(planes_mejoramiento.c.asignacion_id == asignacion_id)
        if estado is not None:
            stmt = stmt.where(planes_mejoramiento.c.estado == estado.value)
        stmt = stmt.order_by(planes_mejoramiento.c.fecha_inicio.desc())
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_plan(r) for r in rows]

    def listar_planes_por_seguimiento(
        self,
        fecha_limite: date,
        institucion_id: TenantScope,
        solo_activos: bool = True,
    ) -> list[PlanMejoramiento]:
        stmt = select(planes_mejoramiento).where(
            planes_mejoramiento.c.fecha_seguimiento.isnot(None),
            planes_mejoramiento.c.fecha_seguimiento <= fecha_limite,
        )
        if isinstance(institucion_id, int):
            subq = select(estudiantes.c.id).where(
                estudiantes.c.institucion_id == institucion_id
            )
            stmt = stmt.where(planes_mejoramiento.c.estudiante_id.in_(subq))
        if solo_activos:
            stmt = stmt.where(planes_mejoramiento.c.estado == "activo")
        stmt = stmt.order_by(
            planes_mejoramiento.c.fecha_seguimiento,
            planes_mejoramiento.c.id,
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_plan(r) for r in rows]

    # ------------------------------------------------------------------
    # Planes de mejoramiento — escritura
    # ------------------------------------------------------------------

    def guardar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento:
        stmt = insert(planes_mejoramiento).values(
            estudiante_id=plan.estudiante_id,
            asignacion_id=plan.asignacion_id,
            periodo_id=plan.periodo_id,
            descripcion_dificultad=plan.descripcion_dificultad,
            actividades_propuestas=plan.actividades_propuestas,
            fecha_inicio=plan.fecha_inicio,
            fecha_seguimiento=plan.fecha_seguimiento,
            fecha_cierre=plan.fecha_cierre,
            estado=plan.estado.value,
            observacion_cierre=plan.observacion_cierre,
            usuario_id=plan.usuario_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return plan.model_copy(update={"id": pk})

    def actualizar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento:
        stmt = (
            update(planes_mejoramiento)
            .where(planes_mejoramiento.c.id == plan.id)
            .values(
                descripcion_dificultad=plan.descripcion_dificultad,
                actividades_propuestas=plan.actividades_propuestas,
                fecha_seguimiento=plan.fecha_seguimiento,
                fecha_cierre=plan.fecha_cierre,
                estado=plan.estado.value,
                observacion_cierre=plan.observacion_cierre,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return plan


__all__ = ["SqlaHabilitacionRepository"]
