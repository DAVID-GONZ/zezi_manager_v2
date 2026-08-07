"""Implementación SQLite de IPreferenciasRepository."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.models.preferencia_institucion import (
    CategoriaPreferencia,
    PreferenciaInstitucion,
    TipoValor,
)
from src.domain.ports.preferencias_repo import IPreferenciasRepository


class SqlitePreferenciasRepository(IPreferenciasRepository):

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

    def _row_to_pref(self, row: sqlite3.Row) -> PreferenciaInstitucion:
        d = dict(row)
        d["categoria"] = CategoriaPreferencia(d["categoria"])
        d["tipo_valor"] = TipoValor(d["tipo_valor"])
        return PreferenciaInstitucion(**d)

    def get(self, institucion_id: int, clave: str) -> PreferenciaInstitucion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM preferencias_institucion WHERE institucion_id=? AND clave=?",
                (institucion_id, clave),
            ).fetchone()
            return self._row_to_pref(row) if row else None

    def get_all(self, institucion_id: int) -> list[PreferenciaInstitucion]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM preferencias_institucion WHERE institucion_id=?",
                (institucion_id,),
            ).fetchall()
            return [self._row_to_pref(r) for r in rows]

    def set(self, pref: PreferenciaInstitucion) -> PreferenciaInstitucion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO preferencias_institucion
                    (institucion_id, categoria, clave, valor, tipo_valor)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pref.institucion_id,
                    pref.categoria.value,
                    pref.clave,
                    pref.valor,
                    pref.tipo_valor.value,
                ),
            )
            if self._conn is None:
                conn.commit()
            return pref.model_copy(update={"id": cursor.lastrowid})

    def seed_defaults(
        self, institucion_id: int, defaults: list[PreferenciaInstitucion]
    ) -> None:
        with self._get_conn() as conn:
            for p in defaults:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO preferencias_institucion
                        (institucion_id, categoria, clave, valor, tipo_valor)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        institucion_id,
                        p.categoria.value,
                        p.clave,
                        p.valor,
                        p.tipo_valor.value,
                    ),
                )
            if self._conn is None:
                conn.commit()


__all__ = ["SqlitePreferenciasRepository"]
