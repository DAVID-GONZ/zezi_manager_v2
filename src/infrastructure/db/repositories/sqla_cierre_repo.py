"""Implementación SQLAlchemy Core de ICierreRepository — ZECI Manager v2.0."""
from __future__ import annotations

from sqlalchemy import delete, insert, select, update

from src.domain.models.cierre import (
    CierreAnio,
    CierrePeriodo,
    EstadoPromocion,
    PromocionAnual,
)
from src.domain.ports.cierre_repo import ICierreRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    cierres_anio,
    cierres_periodo,
    promocion_anual,
)


class SqlaCierreRepository(RepositorioBase, ICierreRepository):
    def __init__(self, conn=None):
        super().__init__(conn, cierres_periodo)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_cierre_periodo(self, row) -> CierrePeriodo:
        return CierrePeriodo(**dict(row))

    def _row_to_cierre_anio(self, row) -> CierreAnio:
        d = dict(row)
        d["perdio"] = bool(d["perdio"])
        return CierreAnio(**d)

    def _row_to_promocion(self, row) -> PromocionAnual:
        d = dict(row)
        d["estado"] = EstadoPromocion(d["estado"])
        return PromocionAnual(**d)

    # ------------------------------------------------------------------
    # Cierre Periodo
    # ------------------------------------------------------------------

    def get_cierre_periodo(
        self, estudiante_id: int, asignacion_id: int, periodo_id: int
    ) -> CierrePeriodo | None:
        stmt = select(cierres_periodo).where(
            cierres_periodo.c.estudiante_id == estudiante_id,
            cierres_periodo.c.asignacion_id == asignacion_id,
            cierres_periodo.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_cierre_periodo(row) if row else None

    def listar_cierres_periodo_por_estudiante(
        self, estudiante_id: int, periodo_id: int | None = None
    ) -> list[CierrePeriodo]:
        stmt = select(cierres_periodo).where(
            cierres_periodo.c.estudiante_id == estudiante_id
        )
        if periodo_id is not None:
            stmt = stmt.where(cierres_periodo.c.periodo_id == periodo_id)
        stmt = stmt.order_by(
            cierres_periodo.c.periodo_id,
            cierres_periodo.c.asignacion_id,
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_cierre_periodo(r) for r in rows]

    def guardar_cierre_periodo(self, cierre: CierrePeriodo) -> CierrePeriodo:
        # INSERT OR REPLACE (upsert) por clave única (estudiante_id, asignacion_id, periodo_id)
        stmt = self._upsert(
            cierres_periodo,
            values={
                "estudiante_id": cierre.estudiante_id,
                "asignacion_id": cierre.asignacion_id,
                "periodo_id": cierre.periodo_id,
                "nota_definitiva": float(cierre.nota_definitiva),
                "desempeno_id": cierre.desempeno_id,
                "logro_id": cierre.logro_id,
                "fecha_cierre": cierre.fecha_cierre,
                "usuario_cierre_id": cierre.usuario_cierre_id,
            },
            conflict_cols=["estudiante_id", "asignacion_id", "periodo_id"],
            update_cols=[
                "nota_definitiva",
                "desempeno_id",
                "logro_id",
                "fecha_cierre",
                "usuario_cierre_id",
            ],
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return cierre.model_copy(update={"id": pk})

    def listar_cierres_periodo_por_asignaciones(
        self,
        asignacion_ids: list[int],
        periodo_id: int,
        nota_maxima: float | None = None,
    ) -> list[CierrePeriodo]:
        if not asignacion_ids:
            return []
        stmt = select(cierres_periodo).where(
            cierres_periodo.c.asignacion_id.in_(asignacion_ids),
            cierres_periodo.c.periodo_id == periodo_id,
        )
        if nota_maxima is not None:
            stmt = stmt.where(cierres_periodo.c.nota_definitiva <= nota_maxima)
        stmt = stmt.order_by(
            cierres_periodo.c.asignacion_id,
            cierres_periodo.c.nota_definitiva.asc(),
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_cierre_periodo(r) for r in rows]

    def borrar_cierres_periodo(self, asignacion_id: int, periodo_id: int) -> int:
        stmt = delete(cierres_periodo).where(
            cierres_periodo.c.asignacion_id == asignacion_id,
            cierres_periodo.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount

    # ------------------------------------------------------------------
    # Cierre Año
    # ------------------------------------------------------------------

    def get_cierre_anio(
        self, estudiante_id: int, asignacion_id: int, anio_id: int
    ) -> CierreAnio | None:
        stmt = select(cierres_anio).where(
            cierres_anio.c.estudiante_id == estudiante_id,
            cierres_anio.c.asignacion_id == asignacion_id,
            cierres_anio.c.anio_id == anio_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_cierre_anio(row) if row else None

    def listar_cierres_anio_por_estudiante(
        self, estudiante_id: int, anio_id: int
    ) -> list[CierreAnio]:
        stmt = (
            select(cierres_anio)
            .where(
                cierres_anio.c.estudiante_id == estudiante_id,
                cierres_anio.c.anio_id == anio_id,
            )
            .order_by(cierres_anio.c.asignacion_id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_cierre_anio(r) for r in rows]

    def guardar_cierre_anio(self, cierre: CierreAnio) -> CierreAnio:
        # INSERT OR REPLACE (upsert) por clave única (estudiante_id, asignacion_id, anio_id)
        stmt = self._upsert(
            cierres_anio,
            values={
                "estudiante_id": cierre.estudiante_id,
                "asignacion_id": cierre.asignacion_id,
                "anio_id": cierre.anio_id,
                "nota_promedio_periodos": float(cierre.nota_promedio_periodos),
                "nota_habilitacion": float(cierre.nota_habilitacion) if cierre.nota_habilitacion is not None else None,
                "nota_definitiva_anual": float(cierre.nota_definitiva_anual),
                "perdio": int(cierre.perdio),
                "desempeno_id": cierre.desempeno_id,
                "fecha_cierre": cierre.fecha_cierre,
                "usuario_cierre_id": cierre.usuario_cierre_id,
            },
            conflict_cols=["estudiante_id", "asignacion_id", "anio_id"],
            update_cols=[
                "nota_promedio_periodos",
                "nota_habilitacion",
                "nota_definitiva_anual",
                "perdio",
                "desempeno_id",
                "fecha_cierre",
                "usuario_cierre_id",
            ],
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return cierre.model_copy(update={"id": pk})

    # ------------------------------------------------------------------
    # Promoción Anual
    # ------------------------------------------------------------------

    def get_promocion(self, estudiante_id: int, anio_id: int) -> PromocionAnual | None:
        stmt = select(promocion_anual).where(
            promocion_anual.c.estudiante_id == estudiante_id,
            promocion_anual.c.anio_id == anio_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_promocion(row) if row else None

    def listar_promociones(
        self, anio_id: int, estado: EstadoPromocion | None = None
    ) -> list[PromocionAnual]:
        stmt = select(promocion_anual).where(promocion_anual.c.anio_id == anio_id)
        if estado is not None:
            stmt = stmt.where(promocion_anual.c.estado == estado.value)
        stmt = stmt.order_by(promocion_anual.c.estudiante_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_promocion(r) for r in rows]

    def guardar_promocion(self, promocion: PromocionAnual) -> PromocionAnual:
        stmt = insert(promocion_anual).values(
            estudiante_id=promocion.estudiante_id,
            anio_id=promocion.anio_id,
            estado=promocion.estado.value,
            asignaturas_perdidas=promocion.asignaturas_perdidas,
            observacion=promocion.observacion,
            fecha_decision=promocion.fecha_decision,
            usuario_decision_id=promocion.usuario_decision_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return promocion.model_copy(update={"id": pk})

    def actualizar_promocion(self, promocion: PromocionAnual) -> PromocionAnual:
        stmt = (
            update(promocion_anual)
            .where(promocion_anual.c.id == promocion.id)
            .values(
                estado=promocion.estado.value,
                asignaturas_perdidas=promocion.asignaturas_perdidas,
                observacion=promocion.observacion,
                fecha_decision=promocion.fecha_decision,
                usuario_decision_id=promocion.usuario_decision_id,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return promocion


__all__ = ["SqlaCierreRepository"]
