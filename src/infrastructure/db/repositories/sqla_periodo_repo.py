"""Implementación SQLAlchemy Core de IPeriodoRepository — AVEDRA v2.0."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.sql.expression import nullslast

from src.domain.models.clock import ahora as _ahora
from src.domain.models.clock import hoy as _hoy
from src.domain.models.periodo import HitoPeriodo, Periodo, TipoHito
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import hitos_periodo, periodos


class SqlaPeriodoRepository(RepositorioBase, IPeriodoRepository):
    def __init__(self, conn=None):
        super().__init__(conn, periodos)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _row_to_periodo(self, row) -> Periodo:
        d = dict(row)
        d["activo"] = bool(d["activo"])
        d["cerrado"] = bool(d["cerrado"])
        return Periodo(**d)

    def _row_to_hito(self, row) -> HitoPeriodo:
        d = dict(row)
        d["tipo"] = TipoHito(d["tipo"])
        return HitoPeriodo(**d)

    # ------------------------------------------------------------------
    # Lectura — periodos
    # ------------------------------------------------------------------

    def get_by_id(self, periodo_id: int) -> Periodo | None:
        stmt = self._select().where(periodos.c.id == periodo_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_periodo(row) if row else None

    def get_por_numero(self, anio_id: int, numero: int) -> Periodo | None:
        stmt = self._select().where(
            periodos.c.anio_id == anio_id,
            periodos.c.numero == numero,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_periodo(row) if row else None

    def get_activo(self, anio_id: int) -> Periodo | None:
        stmt = (
            self._select()
            .where(
                periodos.c.anio_id == anio_id,
                periodos.c.activo == True,  # noqa: E712
                periodos.c.cerrado == False,  # noqa: E712
            )
            .order_by(periodos.c.numero)
            .limit(1)
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_periodo(row) if row else None

    def listar_por_anio(self, anio_id: int, incluir_cerrados: bool = True) -> list[Periodo]:
        stmt = self._select().where(periodos.c.anio_id == anio_id)
        if not incluir_cerrados:
            stmt = stmt.where(periodos.c.cerrado == False)  # noqa: E712
        stmt = stmt.order_by(periodos.c.numero)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_periodo(r) for r in rows]

    def suma_pesos_otros(self, anio_id: int, excluir_periodo_id: int | None = None) -> float:
        stmt = select(func.coalesce(func.sum(periodos.c.peso_porcentual), 0)).where(
            periodos.c.anio_id == anio_id
        )
        if excluir_periodo_id is not None:
            stmt = stmt.where(periodos.c.id != excluir_periodo_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt).scalar()
            return float(result)

    # ------------------------------------------------------------------
    # Escritura — periodos
    # ------------------------------------------------------------------

    def guardar(self, periodo: Periodo) -> Periodo:
        stmt = insert(periodos).values(
            anio_id=periodo.anio_id,
            numero=periodo.numero,
            nombre=periodo.nombre,
            fecha_inicio=periodo.fecha_inicio,
            fecha_fin=periodo.fecha_fin,
            peso_porcentual=periodo.peso_porcentual,
            activo=int(periodo.activo),
            cerrado=int(periodo.cerrado),
            fecha_cierre_real=periodo.fecha_cierre_real,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return periodo.model_copy(update={"id": pk})

    def actualizar(self, periodo: Periodo) -> Periodo:
        stmt = (
            update(periodos)
            .where(periodos.c.id == periodo.id)
            .values(
                nombre=periodo.nombre,
                fecha_inicio=periodo.fecha_inicio,
                fecha_fin=periodo.fecha_fin,
                peso_porcentual=periodo.peso_porcentual,
                activo=int(periodo.activo),
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return periodo

    def cerrar(self, periodo_id: int) -> bool:
        # _ahora() returns a datetime; SQLAlchemy DateTime column accepts it natively.
        stmt = (
            update(periodos)
            .where(periodos.c.id == periodo_id)
            .values(cerrado=True, activo=False, fecha_cierre_real=_ahora())
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def activar(self, periodo_id: int) -> bool:
        stmt = (
            update(periodos)
            .where(periodos.c.id == periodo_id)
            .values(activo=True)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def desactivar(self, periodo_id: int) -> bool:
        stmt = (
            update(periodos)
            .where(periodos.c.id == periodo_id)
            .values(activo=False)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Lectura — hitos
    # ------------------------------------------------------------------

    def get_hito(self, hito_id: int) -> HitoPeriodo | None:
        stmt = select(hitos_periodo).where(hitos_periodo.c.id == hito_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_hito(row) if row else None

    def listar_hitos(self, periodo_id: int, tipo: TipoHito | None = None) -> list[HitoPeriodo]:
        stmt = select(hitos_periodo).where(hitos_periodo.c.periodo_id == periodo_id)
        if tipo is not None:
            stmt = stmt.where(hitos_periodo.c.tipo == tipo.value)
        # NULLS LAST: hitos sin fecha_limite van al final
        stmt = stmt.order_by(nullslast(hitos_periodo.c.fecha_limite), hitos_periodo.c.id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_hito(r) for r in rows]

    def listar_hitos_proximos(self, anio_id: int, dias: int = 7) -> list[HitoPeriodo]:
        today = _hoy()
        end_date = today + timedelta(days=dias)
        stmt = (
            select(hitos_periodo)
            .join(periodos, periodos.c.id == hitos_periodo.c.periodo_id)
            .where(
                periodos.c.anio_id == anio_id,
                hitos_periodo.c.fecha_limite.between(today, end_date),
            )
            .order_by(hitos_periodo.c.fecha_limite, hitos_periodo.c.id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_hito(r) for r in rows]

    # ------------------------------------------------------------------
    # Escritura — hitos
    # ------------------------------------------------------------------

    def guardar_hito(self, hito: HitoPeriodo) -> HitoPeriodo:
        stmt = insert(hitos_periodo).values(
            periodo_id=hito.periodo_id,
            tipo=hito.tipo.value,
            descripcion=hito.descripcion,
            fecha_limite=hito.fecha_limite,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return hito.model_copy(update={"id": pk})

    def actualizar_hito(self, hito: HitoPeriodo) -> HitoPeriodo:
        stmt = (
            update(hitos_periodo)
            .where(hitos_periodo.c.id == hito.id)
            .values(
                tipo=hito.tipo.value,
                descripcion=hito.descripcion,
                fecha_limite=hito.fecha_limite,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return hito

    def eliminar_hito(self, hito_id: int) -> bool:
        stmt = delete(hitos_periodo).where(hitos_periodo.c.id == hito_id)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0


__all__ = ["SqlaPeriodoRepository"]
