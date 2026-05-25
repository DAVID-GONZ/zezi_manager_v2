"""
SqliteSIEERepository — implementación SQLite de ISIEERepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.siee_repo import ISIEERepository
from src.domain.models.evaluacion import Categoria, ConfiguracionSIEE, ModoSIEE


class SqliteSIEERepository(ISIEERepository):

    def __init__(self, conn: sqlite3.Connection | None = None):
        self._conn = conn
        if conn is not None:
            conn.row_factory = sqlite3.Row

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

    def _row_to_siee(self, row: sqlite3.Row) -> ConfiguracionSIEE:
        d = dict(row)
        d["modo"] = ModoSIEE(d["modo"])
        return ConfiguracionSIEE(**d)

    def _row_to_categoria(self, row: sqlite3.Row) -> Categoria:
        d = dict(row)
        # SQLite almacena booleanos como 0/1
        d["es_institucional"]      = bool(d.get("es_institucional", 0))
        d["permite_subcategorias"] = bool(d.get("permite_subcategorias", 0))
        return Categoria(**d)

    # ------------------------------------------------------------------
    # Configuración SIEE
    # ------------------------------------------------------------------

    def get_configuracion(self, anio_id: int) -> ConfiguracionSIEE | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM configuracion_siee WHERE anio_id = ?",
                (anio_id,),
            ).fetchone()
            return self._row_to_siee(row) if row else None

    def guardar_configuracion(self, cfg: ConfiguracionSIEE) -> ConfiguracionSIEE:
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM configuracion_siee WHERE anio_id = ?",
                (cfg.anio_id,),
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE configuracion_siee
                       SET modo = ?, porcentaje_autonomia_docente = ?
                     WHERE anio_id = ?
                    """,
                    (cfg.modo.value, cfg.porcentaje_autonomia_docente, cfg.anio_id),
                )
                siee_id = existing[0]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO configuracion_siee
                        (anio_id, modo, porcentaje_autonomia_docente)
                    VALUES (?, ?, ?)
                    """,
                    (cfg.anio_id, cfg.modo.value, cfg.porcentaje_autonomia_docente),
                )
                siee_id = cursor.lastrowid

            if self._conn is None:
                conn.commit()

            return cfg.model_copy(update={"id": siee_id})

    # ------------------------------------------------------------------
    # Categorías institucionales
    # ------------------------------------------------------------------

    def listar_categorias_institucionales(self, anio_id: int) -> list[Categoria]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM categorias
                WHERE es_institucional = 1 AND anio_id = ?
                ORDER BY nombre
                """,
                (anio_id,),
            ).fetchall()
            return [self._row_to_categoria(r) for r in rows]

    def get_categoria_institucional(self, cat_id: int) -> Categoria | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM categorias WHERE id = ? AND es_institucional = 1",
                (cat_id,),
            ).fetchone()
            return self._row_to_categoria(row) if row else None

    def guardar_categoria_institucional(self, cat: Categoria) -> Categoria:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO categorias
                    (nombre, peso, anio_id, es_institucional, permite_subcategorias)
                VALUES (?, ?, ?, 1, ?)
                """,
                (
                    cat.nombre,
                    cat.peso,
                    cat.anio_id,
                    int(cat.permite_subcategorias),
                ),
            )
            if self._conn is None:
                conn.commit()
            return cat.model_copy(update={"id": cursor.lastrowid})

    def actualizar_categoria_institucional(self, cat: Categoria) -> Categoria:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE categorias
                   SET nombre = ?, peso = ?, permite_subcategorias = ?
                 WHERE id = ? AND es_institucional = 1
                """,
                (cat.nombre, cat.peso, int(cat.permite_subcategorias), cat.id),
            )
            if self._conn is None:
                conn.commit()
            return cat

    def eliminar_categoria_institucional(self, cat_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM categorias WHERE id = ? AND es_institucional = 1",
                (cat_id,),
            )
            if self._conn is None:
                conn.commit()

    def suma_pesos_institucionales(self, anio_id: int) -> float:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(peso), 0.0)
                FROM categorias
                WHERE es_institucional = 1 AND anio_id = ?
                """,
                (anio_id,),
            ).fetchone()
            return float(row[0])


__all__ = ["SqliteSIEERepository"]
