"""
SqliteInfraestructuraRepository
=================================
Implementación SQLite de IInfraestructuraRepository.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    DiaSemana,
    Grupo,
    Horario,
    HorarioEstadisticasDTO,
    HorarioInfo,
    Jornada,
    Logro,
)


class SqliteInfraestructuraRepository(IInfraestructuraRepository):

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

    # =========================================================================
    # Áreas de conocimiento
    # =========================================================================

    def get_area(self, area_id: int) -> AreaConocimiento | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM areas_conocimiento WHERE id = ?", (area_id,)
            ).fetchone()
            return AreaConocimiento(**dict(row)) if row else None

    def listar_areas(self) -> list[AreaConocimiento]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM areas_conocimiento ORDER BY nombre"
            ).fetchall()
            return [AreaConocimiento(**dict(r)) for r in rows]

    def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO areas_conocimiento (nombre, codigo) VALUES (?,?)",
                (area.nombre, area.codigo),
            )
            if self._conn is None:
                conn.commit()
            return area.model_copy(update={"id": cursor.lastrowid})

    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE areas_conocimiento SET nombre = ?, codigo = ? WHERE id = ?",
                (area.nombre, area.codigo, area.id),
            )
            if self._conn is None:
                conn.commit()
            return area

    def eliminar_area(self, area_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM areas_conocimiento WHERE id = ?", (area_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # Asignaturas
    # =========================================================================

    def get_asignatura(self, asignatura_id: int) -> Asignatura | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM asignaturas WHERE id = ?", (asignatura_id,)
            ).fetchone()
            return Asignatura(**dict(row)) if row else None

    def listar_asignaturas(self, area_id: int | None = None) -> list[Asignatura]:
        with self._get_conn() as conn:
            if area_id is not None:
                rows = conn.execute(
                    "SELECT * FROM asignaturas WHERE area_id = ? ORDER BY nombre",
                    (area_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM asignaturas ORDER BY nombre"
                ).fetchall()
            return [Asignatura(**dict(r)) for r in rows]

    def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO asignaturas (nombre, codigo, area_id, horas_semanales)
                VALUES (?,?,?,?)
                """,
                (
                    asignatura.nombre,
                    asignatura.codigo,
                    asignatura.area_id,
                    asignatura.horas_semanales,
                ),
            )
            if self._conn is None:
                conn.commit()
            return asignatura.model_copy(update={"id": cursor.lastrowid})

    def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE asignaturas SET
                    nombre = ?, codigo = ?, area_id = ?, horas_semanales = ?
                WHERE id = ?
                """,
                (
                    asignatura.nombre,
                    asignatura.codigo,
                    asignatura.area_id,
                    asignatura.horas_semanales,
                    asignatura.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return asignatura

    def eliminar_asignatura(self, asignatura_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM asignaturas WHERE id = ?", (asignatura_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # Grupos
    # =========================================================================

    def get_grupo(self, grupo_id: int) -> Grupo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM grupos WHERE id = ?", (grupo_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["jornada"] = Jornada(d["jornada"]) if d.get("jornada") else Jornada.UNICA
            return Grupo(**d)

    def get_grupo_por_codigo(self, codigo: str) -> Grupo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM grupos WHERE codigo = ?", (codigo,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["jornada"] = Jornada(d["jornada"]) if d.get("jornada") else Jornada.UNICA
            return Grupo(**d)

    def listar_grupos(self, grado: int | None = None) -> list[Grupo]:
        with self._get_conn() as conn:
            if grado is not None:
                rows = conn.execute(
                    "SELECT * FROM grupos WHERE grado = ? ORDER BY codigo",
                    (grado,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM grupos ORDER BY codigo"
                ).fetchall()
            resultado = []
            for r in rows:
                d = dict(r)
                d["jornada"] = Jornada(d["jornada"]) if d.get("jornada") else Jornada.UNICA
                resultado.append(Grupo(**d))
            return resultado

    def guardar_grupo(self, grupo: Grupo) -> Grupo:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO grupos (codigo, nombre, grado, jornada, capacidad_maxima)
                VALUES (?,?,?,?,?)
                """,
                (
                    grupo.codigo,
                    grupo.nombre,
                    grupo.grado,
                    grupo.jornada.value if grupo.jornada else None,
                    grupo.capacidad_maxima,
                ),
            )
            if self._conn is None:
                conn.commit()
            return grupo.model_copy(update={"id": cursor.lastrowid})

    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE grupos SET
                    codigo = ?, nombre = ?, grado = ?,
                    jornada = ?, capacidad_maxima = ?
                WHERE id = ?
                """,
                (
                    grupo.codigo,
                    grupo.nombre,
                    grupo.grado,
                    grupo.jornada.value if grupo.jornada else None,
                    grupo.capacidad_maxima,
                    grupo.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return grupo

    def eliminar_grupo(self, grupo_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM grupos WHERE id = ?", (grupo_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # Horarios
    # =========================================================================

    _HORARIO_INFO_SQL = """
        SELECT h.*,
               g.codigo  AS grupo_codigo,
               s.nombre  AS asignatura_nombre,
               u.nombre_completo AS docente_nombre,
               p.nombre  AS periodo_nombre
        FROM horarios h
        JOIN grupos      g ON g.id = h.grupo_id
        JOIN asignaturas s ON s.id = h.asignatura_id
        JOIN usuarios    u ON u.id = h.usuario_id
        JOIN periodos    p ON p.id = h.periodo_id
    """

    def _row_to_horario(self, row) -> Horario:
        d = dict(row)
        d["dia_semana"] = DiaSemana(d["dia_semana"])
        return Horario(**{k: v for k, v in d.items()
                          if k in Horario.model_fields})

    def _row_to_horario_info(self, row) -> HorarioInfo:
        d = dict(row)
        d["dia_semana"] = DiaSemana(d["dia_semana"])
        return HorarioInfo(**d)

    def get_horario(self, horario_id: int) -> Horario | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM horarios WHERE id = ?", (horario_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_horario(row)

    def get_info_horario(self, horario_id: int) -> HorarioInfo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                self._HORARIO_INFO_SQL + " WHERE h.id = ?", (horario_id,)
            ).fetchone()
            return self._row_to_horario_info(row) if row else None

    def listar_horario_grupo(
        self, grupo_id: int, periodo_id: int
    ) -> list[HorarioInfo]:
        with self._get_conn() as conn:
            rows = conn.execute(
                self._HORARIO_INFO_SQL
                + " WHERE h.grupo_id = ? AND h.periodo_id = ?"
                  " ORDER BY h.dia_semana, h.hora_inicio",
                (grupo_id, periodo_id),
            ).fetchall()
            return [self._row_to_horario_info(r) for r in rows]

    def listar_horario_docente(
        self, usuario_id: int, periodo_id: int
    ) -> list[HorarioInfo]:
        with self._get_conn() as conn:
            rows = conn.execute(
                self._HORARIO_INFO_SQL
                + " WHERE h.usuario_id = ? AND h.periodo_id = ?"
                  " ORDER BY h.dia_semana, h.hora_inicio",
                (usuario_id, periodo_id),
            ).fetchall()
            return [self._row_to_horario_info(r) for r in rows]

    def existe_conflicto_horario(
        self,
        usuario_id: int,
        periodo_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        excluir_horario_id: int | None = None,
    ) -> bool:
        with self._get_conn() as conn:
            sql = """
                SELECT 1 FROM horarios
                WHERE usuario_id = ?
                  AND periodo_id = ?
                  AND dia_semana = ?
                  AND hora_inicio < ?
                  AND hora_fin   > ?
            """
            params: list = [usuario_id, periodo_id, dia_semana, hora_fin, hora_inicio]
            if excluir_horario_id is not None:
                sql += " AND id != ?"
                params.append(excluir_horario_id)
            row = conn.execute(sql, params).fetchone()
            return row is not None

    def get_estadisticas(self, periodo_id: int) -> HorarioEstadisticasDTO:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                        AS total_bloques,
                    COUNT(DISTINCT grupo_id)        AS grupos_cubiertos,
                    COUNT(DISTINCT asignatura_id)   AS materias_cargadas,
                    COUNT(DISTINCT usuario_id)      AS docentes_con_horario
                FROM horarios
                WHERE periodo_id = ?
                """,
                (periodo_id,),
            ).fetchone()
            if not row:
                return HorarioEstadisticasDTO()
            return HorarioEstadisticasDTO(**dict(row))

    def guardar_horario(self, horario: Horario) -> Horario:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO horarios (
                    grupo_id, asignatura_id, usuario_id, asignacion_id,
                    periodo_id, dia_semana, hora_inicio, hora_fin, sala
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    horario.grupo_id,
                    horario.asignatura_id,
                    horario.usuario_id,
                    horario.asignacion_id,
                    horario.periodo_id,
                    horario.dia_semana.value,
                    horario.hora_inicio.strftime("%H:%M"),
                    horario.hora_fin.strftime("%H:%M"),
                    horario.sala,
                ),
            )
            if self._conn is None:
                conn.commit()
            return horario.model_copy(update={"id": cursor.lastrowid})

    def actualizar_horario(self, horario: Horario) -> Horario:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE horarios SET
                    grupo_id = ?, asignatura_id = ?, usuario_id = ?,
                    asignacion_id = ?, periodo_id = ?, dia_semana = ?,
                    hora_inicio = ?, hora_fin = ?, sala = ?
                WHERE id = ?
                """,
                (
                    horario.grupo_id,
                    horario.asignatura_id,
                    horario.usuario_id,
                    horario.asignacion_id,
                    horario.periodo_id,
                    horario.dia_semana.value,
                    horario.hora_inicio.strftime("%H:%M"),
                    horario.hora_fin.strftime("%H:%M"),
                    horario.sala,
                    horario.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return horario

    def eliminar_horario(self, horario_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM horarios WHERE id = ?", (horario_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def eliminar_horarios_por_asignacion(self, asignacion_id: int) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM horarios WHERE asignacion_id = ?", (asignacion_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount

    # =========================================================================
    # Logros
    # =========================================================================

    def get_logro(self, logro_id: int) -> Logro | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM logros WHERE id = ?", (logro_id,)
            ).fetchone()
            return Logro(**dict(row)) if row else None

    def listar_logros(self, asignacion_id: int, periodo_id: int) -> list[Logro]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM logros
                WHERE asignacion_id = ? AND periodo_id = ?
                ORDER BY orden, id
                """,
                (asignacion_id, periodo_id),
            ).fetchall()
            return [Logro(**dict(r)) for r in rows]

    def guardar_logro(self, logro: Logro) -> Logro:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO logros (asignacion_id, periodo_id, descripcion, orden)
                VALUES (?,?,?,?)
                """,
                (logro.asignacion_id, logro.periodo_id, logro.descripcion, logro.orden),
            )
            if self._conn is None:
                conn.commit()
            return logro.model_copy(update={"id": cursor.lastrowid})

    def actualizar_logro(self, logro: Logro) -> Logro:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE logros SET descripcion = ?, orden = ? WHERE id = ?",
                (logro.descripcion, logro.orden, logro.id),
            )
            if self._conn is None:
                conn.commit()
            return logro

    def eliminar_logro(self, logro_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM logros WHERE id = ?", (logro_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0


__all__ = ["SqliteInfraestructuraRepository"]
