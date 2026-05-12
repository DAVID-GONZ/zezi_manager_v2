"""
SqliteAcudienteRepository — implementación SQLite de IAcudienteRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.acudiente_repo import IAcudienteRepository
from src.domain.models.acudiente import (
    Acudiente,
    EstudianteAcudiente,
    Parentesco,
    TipoDocumentoAcudiente,
)


class SqliteAcudienteRepository(IAcudienteRepository):

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
    # Helper
    # ------------------------------------------------------------------

    def _row_to_acudiente(self, row: sqlite3.Row) -> Acudiente:
        d = dict(row)
        d["tipo_documento"] = TipoDocumentoAcudiente(d["tipo_documento"])
        d["parentesco"] = Parentesco(d["parentesco"])
        d["activo"] = bool(d["activo"])
        return Acudiente(**d)

    # ------------------------------------------------------------------
    # Lectura — acudiente
    # ------------------------------------------------------------------

    def get_by_id(self, acudiente_id: int) -> Acudiente | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM acudientes WHERE id = ?", (acudiente_id,)
            ).fetchone()
            return self._row_to_acudiente(row) if row else None

    def get_by_documento(self, numero_documento: str) -> Acudiente | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM acudientes WHERE numero_documento = ?",
                (numero_documento.upper(),),
            ).fetchone()
            return self._row_to_acudiente(row) if row else None

    def existe_documento(self, numero_documento: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM acudientes WHERE numero_documento = ?",
                (numero_documento.upper(),),
            ).fetchone()
            return row is not None

    def listar_por_estudiante(
        self,
        estudiante_id: int,
        solo_activos: bool = True,
    ) -> list[Acudiente]:
        sql = """
            SELECT a.*
            FROM acudientes a
            JOIN estudiante_acudiente ea ON ea.acudiente_id = a.id
            WHERE ea.estudiante_id = ?
        """
        params: list = [estudiante_id]
        if solo_activos:
            sql += " AND a.activo = 1"
        sql += " ORDER BY ea.es_principal DESC, a.nombre_completo"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_acudiente(r) for r in rows]

    def get_principal(self, estudiante_id: int) -> Acudiente | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT a.*
                FROM acudientes a
                JOIN estudiante_acudiente ea ON ea.acudiente_id = a.id
                WHERE ea.estudiante_id = ? AND ea.es_principal = 1
                LIMIT 1
                """,
                (estudiante_id,),
            ).fetchone()
            return self._row_to_acudiente(row) if row else None

    def listar_estudiantes_de_acudiente(self, acudiente_id: int) -> list[int]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT estudiante_id FROM estudiante_acudiente WHERE acudiente_id = ?",
                (acudiente_id,),
            ).fetchall()
            return [r["estudiante_id"] for r in rows]

    # ------------------------------------------------------------------
    # Escritura — acudiente
    # ------------------------------------------------------------------

    def guardar(self, acudiente: Acudiente) -> Acudiente:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO acudientes
                    (tipo_documento, numero_documento, nombre_completo,
                     parentesco, celular, email, direccion, activo, usuario_id)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    acudiente.tipo_documento.value,
                    acudiente.numero_documento,
                    acudiente.nombre_completo,
                    acudiente.parentesco.value,
                    acudiente.celular,
                    acudiente.email,
                    acudiente.direccion,
                    int(acudiente.activo),
                    acudiente.usuario_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return acudiente.model_copy(update={"id": cursor.lastrowid})

    def actualizar(self, acudiente: Acudiente) -> Acudiente:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE acudientes SET
                    nombre_completo = ?, parentesco = ?,
                    celular = ?, email = ?, direccion = ?
                WHERE id = ?
                """,
                (
                    acudiente.nombre_completo,
                    acudiente.parentesco.value,
                    acudiente.celular,
                    acudiente.email,
                    acudiente.direccion,
                    acudiente.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return acudiente

    def desactivar(self, acudiente_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE acudientes SET activo = 0 WHERE id = ?",
                (acudiente_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Gestión de vínculos
    # ------------------------------------------------------------------

    def vincular(self, vinculo: EstudianteAcudiente) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO estudiante_acudiente (estudiante_id, acudiente_id, es_principal)
                VALUES (?, ?, ?)
                ON CONFLICT(estudiante_id, acudiente_id)
                DO UPDATE SET es_principal = excluded.es_principal
                """,
                (vinculo.estudiante_id, vinculo.acudiente_id, int(vinculo.es_principal)),
            )
            if self._conn is None:
                conn.commit()

    def desvincular(self, estudiante_id: int, acudiente_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                DELETE FROM estudiante_acudiente
                WHERE estudiante_id = ? AND acudiente_id = ?
                """,
                (estudiante_id, acudiente_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def establecer_principal(self, estudiante_id: int, acudiente_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE estudiante_acudiente
                SET es_principal = 0
                WHERE estudiante_id = ?
                """,
                (estudiante_id,),
            )
            conn.execute(
                """
                UPDATE estudiante_acudiente
                SET es_principal = 1
                WHERE estudiante_id = ? AND acudiente_id = ?
                """,
                (estudiante_id, acudiente_id),
            )
            if self._conn is None:
                conn.commit()

    def get_vinculo(
        self, estudiante_id: int, acudiente_id: int
    ) -> EstudianteAcudiente | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM estudiante_acudiente
                WHERE estudiante_id = ? AND acudiente_id = ?
                """,
                (estudiante_id, acudiente_id),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["es_principal"] = bool(d["es_principal"])
            return EstudianteAcudiente(**d)


__all__ = ["SqliteAcudienteRepository"]
