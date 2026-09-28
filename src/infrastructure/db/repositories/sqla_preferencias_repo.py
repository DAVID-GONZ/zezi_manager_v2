"""Implementación SQLAlchemy Core de IPreferenciasRepository — AVEDRA v2.0."""
from __future__ import annotations

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.domain.models.preferencia_institucion import (
    CategoriaPreferencia,
    PreferenciaInstitucion,
    TipoValor,
)
from src.domain.ports.preferencias_repo import IPreferenciasRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import preferencias_institucion


class SqlaPreferenciasRepository(RepositorioBase, IPreferenciasRepository):
    def __init__(self, conn=None):
        super().__init__(conn, preferencias_institucion)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_pref(self, row) -> PreferenciaInstitucion:
        d = dict(row._mapping)
        d["categoria"] = CategoriaPreferencia(d["categoria"])
        d["tipo_valor"] = TipoValor(d["tipo_valor"])
        return PreferenciaInstitucion(**d)

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get(self, institucion_id: int, clave: str) -> PreferenciaInstitucion | None:
        with self._get_conn() as conn:
            stmt = self._select().where(
                preferencias_institucion.c.institucion_id == institucion_id,
                preferencias_institucion.c.clave == clave,
            )
            row = conn.execute(stmt).fetchone()
            return self._row_to_pref(row) if row else None

    def get_all(self, institucion_id: int) -> list[PreferenciaInstitucion]:
        with self._get_conn() as conn:
            stmt = self._select().where(
                preferencias_institucion.c.institucion_id == institucion_id
            )
            rows = conn.execute(stmt).fetchall()
            return [self._row_to_pref(r) for r in rows]

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def set(self, pref: PreferenciaInstitucion) -> PreferenciaInstitucion:
        stmt = self._upsert(
            preferencias_institucion,
            values={
                "institucion_id": pref.institucion_id,
                "categoria": pref.categoria.value,
                "clave": pref.clave,
                "valor": pref.valor,
                "tipo_valor": pref.tipo_valor.value,
            },
            conflict_cols=["institucion_id", "clave"],
            update_cols=["valor", "tipo_valor", "categoria"],
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return pref.model_copy(update={"id": pk})

    def seed_defaults(
        self, institucion_id: int, defaults: list[PreferenciaInstitucion]
    ) -> None:
        with self._get_conn() as conn:
            for p in defaults:
                stmt = (
                    sqlite_insert(preferencias_institucion)
                    .values(
                        institucion_id=institucion_id,
                        categoria=p.categoria.value,
                        clave=p.clave,
                        valor=p.valor,
                        tipo_valor=p.tipo_valor.value,
                    )
                    .on_conflict_do_nothing()
                )
                conn.execute(stmt)
            if self._conn is None:
                conn.commit()


__all__ = ["SqlaPreferenciasRepository"]
