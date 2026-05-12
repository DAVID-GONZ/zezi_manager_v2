"""
SqliteEvaluacionRepository — implementación SQLite de IEvaluacionRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date

from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.domain.models.evaluacion import (
    Actividad,
    Categoria,
    EstadoActividad,
    Nota,
    PuntosExtra,
    ResultadoEstudianteDTO,
    TipoPuntosExtra,
)


class SqliteEvaluacionRepository(IEvaluacionRepository):

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
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_categoria(self, row: sqlite3.Row) -> Categoria:
        return Categoria(**dict(row))

    def _row_to_actividad(self, row: sqlite3.Row) -> Actividad:
        d = dict(row)
        d["estado"] = EstadoActividad(d["estado"])
        return Actividad(**d)

    def _row_to_nota(self, row: sqlite3.Row) -> Nota:
        return Nota(**dict(row))

    def _row_to_puntos_extra(self, row: sqlite3.Row) -> PuntosExtra:
        d = dict(row)
        d["tipo"] = TipoPuntosExtra(d["tipo"])
        return PuntosExtra(**d)

    # ------------------------------------------------------------------
    # Categorías
    # ------------------------------------------------------------------

    def listar_categorias(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Categoria]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM categorias
                WHERE asignacion_id = ? AND periodo_id = ?
                ORDER BY nombre
                """,
                (asignacion_id, periodo_id),
            ).fetchall()
            return [self._row_to_categoria(r) for r in rows]

    def get_categoria(self, cat_id: int) -> Categoria | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM categorias WHERE id = ?", (cat_id,)
            ).fetchone()
            return self._row_to_categoria(row) if row else None

    def guardar_categoria(self, categoria: Categoria) -> Categoria:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO categorias (nombre, peso, asignacion_id, periodo_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    categoria.nombre,
                    categoria.peso,
                    categoria.asignacion_id,
                    categoria.periodo_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return categoria.model_copy(update={"id": cursor.lastrowid})

    def actualizar_categoria(self, categoria: Categoria) -> Categoria:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE categorias SET nombre = ?, peso = ? WHERE id = ?",
                (categoria.nombre, categoria.peso, categoria.id),
            )
            if self._conn is None:
                conn.commit()
            return categoria

    def eliminar_categoria(self, cat_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM categorias WHERE id = ?", (cat_id,))
            if self._conn is None:
                conn.commit()

    def suma_pesos_otras(
        self,
        asignacion_id: int,
        periodo_id: int,
        excluir_cat_id: int | None = None,
    ) -> float:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(peso), 0)
                FROM categorias
                WHERE asignacion_id = ? AND periodo_id = ?
                  AND id != COALESCE(?, 0)
                """,
                (asignacion_id, periodo_id, excluir_cat_id),
            ).fetchone()
            return float(row[0])

    # ------------------------------------------------------------------
    # Actividades
    # ------------------------------------------------------------------

    def listar_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Actividad]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT a.*
                FROM actividades a
                JOIN categorias c ON c.id = a.categoria_id
                WHERE c.asignacion_id = ? AND c.periodo_id = ?
                ORDER BY a.fecha NULLS LAST, a.nombre
                """,
                (asignacion_id, periodo_id),
            ).fetchall()
            return [self._row_to_actividad(r) for r in rows]

    def listar_actividades_por_categoria(self, cat_id: int) -> list[Actividad]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM actividades
                WHERE categoria_id = ?
                ORDER BY fecha NULLS LAST, nombre
                """,
                (cat_id,),
            ).fetchall()
            return [self._row_to_actividad(r) for r in rows]

    def listar_actividades_publicadas(
        self,
        asignacion_id: int,
        periodo_id: int,
        hasta_fecha: date | None = None,
    ) -> list[Actividad]:
        sql = """
            SELECT a.*
            FROM actividades a
            JOIN categorias c ON c.id = a.categoria_id
            WHERE c.asignacion_id = ? AND c.periodo_id = ?
              AND a.estado IN ('publicada', 'cerrada')
        """
        params: list = [asignacion_id, periodo_id]
        if hasta_fecha is not None:
            sql += " AND (a.fecha IS NULL OR a.fecha <= ?)"
            params.append(hasta_fecha.isoformat())
        sql += " ORDER BY a.fecha NULLS LAST, a.nombre"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_actividad(r) for r in rows]

    def get_actividad(self, act_id: int) -> Actividad | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM actividades WHERE id = ?", (act_id,)
            ).fetchone()
            return self._row_to_actividad(row) if row else None

    def guardar_actividad(self, actividad: Actividad) -> Actividad:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO actividades
                    (nombre, descripcion, fecha, valor_maximo, estado, categoria_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    actividad.nombre,
                    actividad.descripcion,
                    actividad.fecha.isoformat() if actividad.fecha else None,
                    actividad.valor_maximo,
                    actividad.estado.value,
                    actividad.categoria_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return actividad.model_copy(update={"id": cursor.lastrowid})

    def actualizar_actividad(self, actividad: Actividad) -> Actividad:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE actividades SET
                    nombre = ?, descripcion = ?, fecha = ?,
                    valor_maximo = ?, estado = ?
                WHERE id = ?
                """,
                (
                    actividad.nombre,
                    actividad.descripcion,
                    actividad.fecha.isoformat() if actividad.fecha else None,
                    actividad.valor_maximo,
                    actividad.estado.value,
                    actividad.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return actividad

    def actualizar_estado_actividad(
        self,
        act_id: int,
        estado: EstadoActividad,
    ) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE actividades SET estado = ? WHERE id = ?",
                (estado.value, act_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def eliminar_actividad(self, act_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM actividades WHERE id = ?", (act_id,))
            if self._conn is None:
                conn.commit()

    # ------------------------------------------------------------------
    # Notas
    # ------------------------------------------------------------------

    def listar_notas_por_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[Nota]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT n.*
                FROM notas n
                JOIN actividades a ON a.id = n.actividad_id
                JOIN categorias c  ON c.id = a.categoria_id
                WHERE n.estudiante_id = ?
                  AND c.asignacion_id = ?
                  AND c.periodo_id    = ?
                """,
                (estudiante_id, asignacion_id, periodo_id),
            ).fetchall()
            return [self._row_to_nota(r) for r in rows]

    def listar_notas_por_actividad(self, actividad_id: int) -> list[Nota]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM notas WHERE actividad_id = ?",
                (actividad_id,),
            ).fetchall()
            return [self._row_to_nota(r) for r in rows]

    def get_nota(self, estudiante_id: int, actividad_id: int) -> Nota | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM notas WHERE estudiante_id = ? AND actividad_id = ?",
                (estudiante_id, actividad_id),
            ).fetchone()
            return self._row_to_nota(row) if row else None

    def guardar_nota(self, nota: Nota) -> Nota:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notas
                    (estudiante_id, actividad_id, valor,
                     usuario_registro_id, fecha_registro)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(estudiante_id, actividad_id)
                DO UPDATE SET
                    valor               = excluded.valor,
                    usuario_registro_id = excluded.usuario_registro_id,
                    fecha_registro      = excluded.fecha_registro
                """,
                (
                    nota.estudiante_id,
                    nota.actividad_id,
                    nota.valor,
                    nota.usuario_registro_id,
                    nota.fecha_registro.isoformat(),
                ),
            )
            if self._conn is None:
                conn.commit()
            return nota.model_copy(update={"id": cursor.lastrowid})

    def guardar_notas_masivas(self, notas: list[Nota]) -> int:
        if not notas:
            return 0
        with self._get_conn() as conn:
            conn.executemany(
                """
                INSERT INTO notas
                    (estudiante_id, actividad_id, valor,
                     usuario_registro_id, fecha_registro)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(estudiante_id, actividad_id)
                DO UPDATE SET
                    valor               = excluded.valor,
                    usuario_registro_id = excluded.usuario_registro_id,
                    fecha_registro      = excluded.fecha_registro
                """,
                [
                    (
                        n.estudiante_id,
                        n.actividad_id,
                        n.valor,
                        n.usuario_registro_id,
                        n.fecha_registro.isoformat(),
                    )
                    for n in notas
                ],
            )
            if self._conn is None:
                conn.commit()
            return len(notas)

    def eliminar_nota(self, estudiante_id: int, actividad_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM notas WHERE estudiante_id = ? AND actividad_id = ?",
                (estudiante_id, actividad_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Puntos extra
    # ------------------------------------------------------------------

    def get_puntos_extra(
        self,
        estudiante_id: int,
        asignacion_id: int,
        periodo_id: int,
        tipo: TipoPuntosExtra | None = None,
    ) -> PuntosExtra | None:
        sql = """
            SELECT * FROM puntos_extra
            WHERE estudiante_id = ? AND asignacion_id = ? AND periodo_id = ?
        """
        params: list = [estudiante_id, asignacion_id, periodo_id]
        if tipo is not None:
            sql += " AND tipo = ?"
            params.append(tipo.value)
        sql += " LIMIT 1"
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return self._row_to_puntos_extra(row) if row else None

    def listar_puntos_extra(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[PuntosExtra]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM puntos_extra
                WHERE asignacion_id = ? AND periodo_id = ?
                ORDER BY estudiante_id, tipo
                """,
                (asignacion_id, periodo_id),
            ).fetchall()
            return [self._row_to_puntos_extra(r) for r in rows]

    def guardar_puntos_extra(self, pe: PuntosExtra) -> PuntosExtra:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO puntos_extra
                    (estudiante_id, asignacion_id, periodo_id, tipo,
                     positivos, negativos, observacion, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(estudiante_id, asignacion_id, periodo_id, tipo)
                DO UPDATE SET
                    positivos          = excluded.positivos,
                    negativos          = excluded.negativos,
                    observacion        = excluded.observacion,
                    fecha_actualizacion = excluded.fecha_actualizacion
                """,
                (
                    pe.estudiante_id,
                    pe.asignacion_id,
                    pe.periodo_id,
                    pe.tipo.value,
                    pe.positivos,
                    pe.negativos,
                    pe.observacion,
                    pe.fecha_actualizacion.isoformat(),
                ),
            )
            if self._conn is None:
                conn.commit()
            return pe.model_copy(update={"id": cursor.lastrowid})

    # ------------------------------------------------------------------
    # Read models — resultados consolidados
    # ------------------------------------------------------------------

    def listar_resultados_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ResultadoEstudianteDTO]:
        with self._get_conn() as conn:
            # Obtener todos los estudiantes activos del grupo
            estudiantes = conn.execute(
                """
                SELECT id, nombre || ' ' || apellido AS nombre_completo, posee_piar
                FROM estudiantes
                WHERE grupo_id = ? AND estado_matricula = 'activo'
                ORDER BY apellido, nombre
                """,
                (grupo_id,),
            ).fetchall()

            # Obtener todas las notas de la asignación en el periodo
            notas_rows = conn.execute(
                """
                SELECT n.estudiante_id, n.actividad_id, n.valor
                FROM notas n
                JOIN actividades a ON a.id = n.actividad_id
                JOIN categorias c  ON c.id = a.categoria_id
                WHERE c.asignacion_id = ? AND c.periodo_id = ?
                """,
                (asignacion_id, periodo_id),
            ).fetchall()

        # Indexar notas por estudiante
        notas_por_est: dict[int, dict[int, float]] = {}
        for r in notas_rows:
            notas_por_est.setdefault(r["estudiante_id"], {})[r["actividad_id"]] = r["valor"]

        resultado: list[ResultadoEstudianteDTO] = []
        for est in estudiantes:
            est_id = est["id"]
            resultado.append(
                ResultadoEstudianteDTO(
                    estudiante_id=est_id,
                    nombre_completo=est["nombre_completo"],
                    notas=notas_por_est.get(est_id, {}),
                    posee_piar=bool(est["posee_piar"]),
                )
            )
        return resultado


__all__ = ["SqliteEvaluacionRepository"]
