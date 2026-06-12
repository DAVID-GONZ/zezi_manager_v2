"""
SqliteInfraestructuraRepository
=================================
Implementación SQLite de IInfraestructuraRepository.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager

from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    ConfigGeneracion,
    DiaSemana,
    DisponibilidadDocente,
    EscenarioHorario,
    Franja,
    Grupo,
    Horario,
    HorarioEstadisticasDTO,
    HorarioInfo,
    Jornada,
    Logro,
    PesosGeneracion,
    PlantillaFranja,
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
    # Escenarios de horario
    # =========================================================================

    def _row_to_escenario(self, row) -> EscenarioHorario:
        d = dict(row)
        d["activo"] = bool(d.get("activo", 0))
        return EscenarioHorario(**{k: v for k, v in d.items()
                                   if k in EscenarioHorario.model_fields})

    def get_escenario(self, escenario_id: int) -> EscenarioHorario | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM escenarios_horario WHERE id = ?", (escenario_id,)
            ).fetchone()
            return self._row_to_escenario(row) if row else None

    def listar_escenarios(self, anio_id: int) -> list[EscenarioHorario]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM escenarios_horario WHERE anio_id = ? ORDER BY nombre",
                (anio_id,),
            ).fetchall()
            return [self._row_to_escenario(r) for r in rows]

    def get_escenario_activo(self, anio_id: int) -> EscenarioHorario | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM escenarios_horario WHERE anio_id = ? AND activo = 1",
                (anio_id,),
            ).fetchone()
            return self._row_to_escenario(row) if row else None

    def crear_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO escenarios_horario (anio_id, nombre, descripcion, activo)
                VALUES (?, ?, ?, ?)
                """,
                (esc.anio_id, esc.nombre, esc.descripcion, int(esc.activo)),
            )
            if self._conn is None:
                conn.commit()
            return esc.model_copy(update={"id": cursor.lastrowid})

    def actualizar_escenario(self, esc: EscenarioHorario) -> EscenarioHorario:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE escenarios_horario
                   SET nombre = ?, descripcion = ?, activo = ?
                 WHERE id = ?
                """,
                (esc.nombre, esc.descripcion, int(esc.activo), esc.id),
            )
            if self._conn is None:
                conn.commit()
            return esc

    def activar_escenario(self, escenario_id: int) -> None:
        with self._get_conn() as conn:
            # Obtener el anio_id del escenario
            row = conn.execute(
                "SELECT anio_id FROM escenarios_horario WHERE id = ?", (escenario_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Escenario {escenario_id} no existe.")
            anio_id = row[0]
            # Desactivar todos del año y activar solo el indicado
            conn.execute(
                "UPDATE escenarios_horario SET activo = 0 WHERE anio_id = ?",
                (anio_id,),
            )
            conn.execute(
                "UPDATE escenarios_horario SET activo = 1 WHERE id = ?",
                (escenario_id,),
            )
            if self._conn is None:
                conn.commit()

    def eliminar_escenario(self, escenario_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM escenarios_horario WHERE id = ?", (escenario_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def duplicar_escenario(self, escenario_id: int, nuevo_nombre: str) -> EscenarioHorario:
        with self._get_conn() as conn:
            orig = conn.execute(
                "SELECT * FROM escenarios_horario WHERE id = ?", (escenario_id,)
            ).fetchone()
            if not orig:
                raise ValueError(f"Escenario {escenario_id} no existe.")
            orig_d = dict(orig)
            # Insertar nuevo escenario inactivo
            cursor = conn.execute(
                """
                INSERT INTO escenarios_horario (anio_id, nombre, descripcion, activo)
                VALUES (?, ?, ?, 0)
                """,
                (orig_d["anio_id"], nuevo_nombre, orig_d.get("descripcion")),
            )
            nuevo_id = cursor.lastrowid
            # Copiar bloques de horarios
            conn.execute(
                """
                INSERT INTO horarios
                    (grupo_id, asignatura_id, usuario_id, asignacion_id,
                     periodo_id, escenario_id, dia_semana, hora_inicio, hora_fin, sala)
                SELECT grupo_id, asignatura_id, usuario_id, asignacion_id,
                       periodo_id, ?, dia_semana, hora_inicio, hora_fin, sala
                FROM horarios
                WHERE escenario_id = ?
                """,
                (nuevo_id, escenario_id),
            )
            if self._conn is None:
                conn.commit()
            nuevo = conn.execute(
                "SELECT * FROM escenarios_horario WHERE id = ?", (nuevo_id,)
            ).fetchone()
            return self._row_to_escenario(nuevo)

    # =========================================================================
    # Plantillas de franja y franjas
    # =========================================================================

    def _row_to_plantilla(self, row) -> PlantillaFranja:
        d = dict(row)
        d["activa"] = bool(d.get("activa", 0))
        d["dias_activos"] = d["dias_activos"].split(",") if d.get("dias_activos") else []
        return PlantillaFranja(**{k: v for k, v in d.items()
                                  if k in PlantillaFranja.model_fields})

    def _row_to_franja(self, row) -> Franja:
        d = dict(row)
        return Franja(**{k: v for k, v in d.items()
                         if k in Franja.model_fields})

    def crear_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO plantillas_franja (nombre, jornada, dias_activos, activa)
                VALUES (?, ?, ?, ?)
                """,
                (p.nombre, p.jornada, ",".join(p.dias_activos), int(p.activa)),
            )
            if self._conn is None:
                conn.commit()
            return p.model_copy(update={"id": cursor.lastrowid})

    def get_plantilla_franja(self, plantilla_id: int) -> PlantillaFranja | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM plantillas_franja WHERE id = ?", (plantilla_id,)
            ).fetchone()
            return self._row_to_plantilla(row) if row else None

    def listar_plantillas_franja(self) -> list[PlantillaFranja]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM plantillas_franja ORDER BY nombre"
            ).fetchall()
            return [self._row_to_plantilla(r) for r in rows]

    def get_plantilla_activa(self, jornada: str) -> PlantillaFranja | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM plantillas_franja WHERE jornada = ? AND activa = 1",
                (jornada,),
            ).fetchone()
            return self._row_to_plantilla(row) if row else None

    def actualizar_plantilla_franja(self, p: PlantillaFranja) -> PlantillaFranja:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE plantillas_franja
                   SET nombre = ?, jornada = ?, dias_activos = ?, activa = ?
                 WHERE id = ?
                """,
                (p.nombre, p.jornada, ",".join(p.dias_activos), int(p.activa), p.id),
            )
            if self._conn is None:
                conn.commit()
            return p

    def activar_plantilla_franja(self, plantilla_id: int) -> None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT jornada FROM plantillas_franja WHERE id = ?", (plantilla_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Plantilla {plantilla_id} no existe.")
            jornada = row[0]
            # Desactivar todas las de la misma jornada y activar solo la indicada
            conn.execute(
                "UPDATE plantillas_franja SET activa = 0 WHERE jornada = ?",
                (jornada,),
            )
            conn.execute(
                "UPDATE plantillas_franja SET activa = 1 WHERE id = ?",
                (plantilla_id,),
            )
            if self._conn is None:
                conn.commit()

    def eliminar_plantilla_franja(self, plantilla_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM plantillas_franja WHERE id = ?", (plantilla_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def crear_franja(self, f: Franja) -> Franja:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO franjas
                    (plantilla_id, orden, hora_inicio, hora_fin, tipo, etiqueta)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (f.plantilla_id, f.orden, f.hora_inicio, f.hora_fin, f.tipo, f.etiqueta),
            )
            if self._conn is None:
                conn.commit()
            return f.model_copy(update={"id": cursor.lastrowid})

    def listar_franjas(self, plantilla_id: int) -> list[Franja]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM franjas WHERE plantilla_id = ? ORDER BY orden",
                (plantilla_id,),
            ).fetchall()
            return [self._row_to_franja(r) for r in rows]

    def actualizar_franja(self, f: Franja) -> Franja:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE franjas SET
                    plantilla_id = ?, orden = ?, hora_inicio = ?,
                    hora_fin = ?, tipo = ?, etiqueta = ?
                WHERE id = ?
                """,
                (f.plantilla_id, f.orden, f.hora_inicio, f.hora_fin,
                 f.tipo, f.etiqueta, f.id),
            )
            if self._conn is None:
                conn.commit()
            return f

    def eliminar_franja(self, franja_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM franjas WHERE id = ?", (franja_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def reemplazar_franjas(self, plantilla_id: int, franjas: list[Franja]) -> int:
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM franjas WHERE plantilla_id = ?", (plantilla_id,)
            )
            filas = [
                (plantilla_id, f.orden, f.hora_inicio, f.hora_fin, f.tipo, f.etiqueta)
                for f in franjas
            ]
            if filas:
                conn.executemany(
                    """
                    INSERT INTO franjas
                        (plantilla_id, orden, hora_inicio, hora_fin, tipo, etiqueta)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    filas,
                )
            if self._conn is None:
                conn.commit()
            return len(filas)

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
                "INSERT INTO areas_conocimiento (nombre, codigo, color) VALUES (?,?,?)",
                (area.nombre, area.codigo, area.color),
            )
            if self._conn is None:
                conn.commit()
            return area.model_copy(update={"id": cursor.lastrowid})

    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE areas_conocimiento SET nombre = ?, codigo = ?, color = ? WHERE id = ?",
                (area.nombre, area.codigo, area.color, area.id),
            )
            if self._conn is None:
                conn.commit()
            return area

    def actualizar_color_area(self, area_id: int, color: str | None) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE areas_conocimiento SET color = ? WHERE id = ?",
                (color, area_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

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
               COALESCE(p.nombre, '') AS periodo_nombre
        FROM horarios h
        JOIN grupos      g ON g.id = h.grupo_id
        JOIN asignaturas s ON s.id = h.asignatura_id
        JOIN usuarios    u ON u.id = h.usuario_id
        LEFT JOIN periodos p ON p.id = h.periodo_id
    """

    def _row_to_horario(self, row) -> Horario:
        d = dict(row)
        d["dia_semana"] = DiaSemana(d["dia_semana"])
        return Horario(**{k: v for k, v in d.items()
                          if k in Horario.model_fields})

    def _row_to_horario_info(self, row) -> HorarioInfo:
        d = dict(row)
        d["dia_semana"] = DiaSemana(d["dia_semana"])
        # Remove keys not in HorarioInfo
        valid_keys = set(HorarioInfo.model_fields.keys())
        d = {k: v for k, v in d.items() if k in valid_keys}
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

    def _get_escenario_activo_por_periodo(
        self, conn, periodo_id: int
    ) -> int | None:
        """Resuelve periodo_id → anio_id → escenario activo. Retorna escenario_id o None."""
        row = conn.execute(
            """
            SELECT e.id
            FROM periodos p
            JOIN escenarios_horario e ON e.anio_id = p.anio_id AND e.activo = 1
            WHERE p.id = ?
            """,
            (periodo_id,),
        ).fetchone()
        return row[0] if row else None

    def listar_horario_grupo(
        self, grupo_id: int, periodo_id: int
    ) -> list[HorarioInfo]:
        with self._get_conn() as conn:
            escenario_id = self._get_escenario_activo_por_periodo(conn, periodo_id)
            if escenario_id is None:
                return []
            rows = conn.execute(
                self._HORARIO_INFO_SQL
                + " WHERE h.grupo_id = ? AND h.escenario_id = ?"
                  " ORDER BY h.dia_semana, h.hora_inicio",
                (grupo_id, escenario_id),
            ).fetchall()
            return [self._row_to_horario_info(r) for r in rows]

    def listar_horario_docente(
        self, usuario_id: int, periodo_id: int
    ) -> list[HorarioInfo]:
        with self._get_conn() as conn:
            escenario_id = self._get_escenario_activo_por_periodo(conn, periodo_id)
            if escenario_id is None:
                return []
            rows = conn.execute(
                self._HORARIO_INFO_SQL
                + " WHERE h.usuario_id = ? AND h.escenario_id = ?"
                  " ORDER BY h.dia_semana, h.hora_inicio",
                (usuario_id, escenario_id),
            ).fetchall()
            return [self._row_to_horario_info(r) for r in rows]

    def listar_horario_grupo_escenario(
        self, grupo_id: int, escenario_id: int
    ) -> list[HorarioInfo]:
        with self._get_conn() as conn:
            rows = conn.execute(
                self._HORARIO_INFO_SQL
                + " WHERE h.grupo_id = ? AND h.escenario_id = ?"
                  " ORDER BY h.dia_semana, h.hora_inicio",
                (grupo_id, escenario_id),
            ).fetchall()
            return [self._row_to_horario_info(r) for r in rows]

    def listar_horario_escenario(self, escenario_id: int) -> list[HorarioInfo]:
        with self._get_conn() as conn:
            rows = conn.execute(
                self._HORARIO_INFO_SQL
                + " WHERE h.escenario_id = ?"
                  " ORDER BY h.dia_semana, h.hora_inicio",
                (escenario_id,),
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
                    periodo_id, escenario_id, dia_semana, hora_inicio, hora_fin, sala
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    horario.grupo_id,
                    horario.asignatura_id,
                    horario.usuario_id,
                    horario.asignacion_id,
                    horario.periodo_id,
                    horario.escenario_id,
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
                    asignacion_id = ?, periodo_id = ?, escenario_id = ?,
                    dia_semana = ?, hora_inicio = ?, hora_fin = ?, sala = ?
                WHERE id = ?
                """,
                (
                    horario.grupo_id,
                    horario.asignatura_id,
                    horario.usuario_id,
                    horario.asignacion_id,
                    horario.periodo_id,
                    horario.escenario_id,
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

    def existe_cruce(
        self,
        escenario_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        *,
        usuario_id: int | None = None,
        grupo_id: int | None = None,
        sala: str | None = None,
        excluir_horario_id: int | None = None,
    ) -> bool:
        sql = """SELECT 1 FROM horarios
                 WHERE escenario_id = ?
                   AND dia_semana = ?
                   AND hora_inicio < ?
                   AND hora_fin > ?"""
        params: list = [escenario_id, dia_semana, hora_fin, hora_inicio]
        if usuario_id is not None:
            sql += " AND usuario_id = ?"
            params.append(usuario_id)
        if grupo_id is not None:
            sql += " AND grupo_id = ?"
            params.append(grupo_id)
        if sala is not None:
            sql += " AND sala = ?"
            params.append(sala)
        if excluir_horario_id is not None:
            sql += " AND id != ?"
            params.append(excluir_horario_id)
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
        return row is not None

    def contar_bloques_asignacion(self, escenario_id: int, asignacion_id: int) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM horarios WHERE escenario_id=? AND asignacion_id=?",
                (escenario_id, asignacion_id),
            ).fetchone()
        return row[0]

    def contar_bloques_docente(self, escenario_id: int, usuario_id: int) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM horarios WHERE escenario_id=? AND usuario_id=?",
                (escenario_id, usuario_id),
            ).fetchone()
        return row[0]

    def crear_bloques_masivo(self, horarios: list) -> int:
        if not horarios:
            return 0
        rows = []
        for h in horarios:
            dia = h.dia_semana.value if hasattr(h.dia_semana, "value") else str(h.dia_semana)
            hi = h.hora_inicio.strftime("%H:%M") if hasattr(h.hora_inicio, "strftime") else str(h.hora_inicio)
            hf = h.hora_fin.strftime("%H:%M") if hasattr(h.hora_fin, "strftime") else str(h.hora_fin)
            rows.append((
                h.grupo_id,
                h.asignatura_id,
                h.usuario_id,
                getattr(h, "asignacion_id", None),
                getattr(h, "periodo_id", None),
                h.escenario_id,
                dia, hi, hf,
                getattr(h, "sala", "Aula") or "Aula",
            ))
        with self._get_conn() as conn:
            conn.executemany(
                """INSERT INTO horarios
                   (grupo_id, asignatura_id, usuario_id, asignacion_id,
                    periodo_id, escenario_id, dia_semana, hora_inicio, hora_fin, sala)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            if self._conn is None:
                conn.commit()
        return len(rows)

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

    # =========================================================================
    # Disponibilidad docente (paso_15b)
    # =========================================================================

    def _row_to_disponibilidad(self, row) -> DisponibilidadDocente:
        d = dict(row)
        d["disponible"] = bool(d.get("disponible", 1))
        return DisponibilidadDocente(**{k: v for k, v in d.items()
                                        if k in DisponibilidadDocente.model_fields})

    def upsert_disponibilidad(self, d: DisponibilidadDocente) -> DisponibilidadDocente:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO disponibilidad_docente
                    (usuario_id, dia_semana, franja_orden, disponible)
                VALUES (?, ?, ?, ?)
                """,
                (d.usuario_id, d.dia_semana, d.franja_orden, int(d.disponible)),
            )
            if self._conn is None:
                conn.commit()
            row = conn.execute(
                "SELECT * FROM disponibilidad_docente WHERE id = ?",
                (cursor.lastrowid,)
            ).fetchone()
            if row:
                return self._row_to_disponibilidad(row)
            # fallback: read by unique key
            row = conn.execute(
                """
                SELECT * FROM disponibilidad_docente
                WHERE usuario_id=? AND dia_semana=? AND franja_orden=?
                """,
                (d.usuario_id, d.dia_semana, d.franja_orden),
            ).fetchone()
            return self._row_to_disponibilidad(row) if row else d

    def listar_disponibilidad_docente(self, usuario_id: int) -> list[DisponibilidadDocente]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM disponibilidad_docente WHERE usuario_id = ? ORDER BY dia_semana, franja_orden",
                (usuario_id,),
            ).fetchall()
            return [self._row_to_disponibilidad(r) for r in rows]

    def es_disponible(self, usuario_id: int, dia: str, franja_orden: int) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT disponible FROM disponibilidad_docente
                WHERE usuario_id = ? AND dia_semana = ? AND franja_orden = ?
                """,
                (usuario_id, dia, franja_orden),
            ).fetchone()
            if row is None:
                return True   # R2: no hay fila → disponible por defecto
            return bool(row[0])

    def limpiar_disponibilidad_docente(self, usuario_id: int) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM disponibilidad_docente WHERE usuario_id = ?",
                (usuario_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount

    def cargar_disponibilidad_lote(self, usuario_id: int, slots: list[dict]) -> int:
        with self._get_conn() as conn:
            count = 0
            for slot in slots:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO disponibilidad_docente
                        (usuario_id, dia_semana, franja_orden, disponible)
                    VALUES (?, ?, ?, 0)
                    """,
                    (usuario_id, slot["dia_semana"], slot["franja_orden"]),
                )
                count += 1
            if self._conn is None:
                conn.commit()
            return count

    # =========================================================================
    # Config generación (paso_15b)
    # =========================================================================

    def _row_to_config(self, row) -> ConfigGeneracion:
        d = dict(row)
        grupos = json.loads(d.pop("grupos_json", "[]") or "[]")
        pesos_dict = json.loads(d.pop("pesos_json", "{}") or "{}")
        pesos = PesosGeneracion(**pesos_dict) if pesos_dict else PesosGeneracion()
        return ConfigGeneracion(
            id=d["id"],
            nombre=d["nombre"],
            periodo_id=d["periodo_id"],
            anio_id=d["anio_id"],
            plantilla_id=d["plantilla_id"],
            estado=d["estado"],
            grupos=grupos,
            pesos=pesos,
            escenario_destino_id=d.get("escenario_destino_id"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
        )

    def crear_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion:
        with self._get_conn() as conn:
            grupos_json = json.dumps(c.grupos)
            pesos_json = json.dumps(c.pesos.model_dump())
            cursor = conn.execute(
                """
                INSERT INTO config_generacion
                    (nombre, periodo_id, anio_id, plantilla_id, estado,
                     grupos_json, pesos_json, escenario_destino_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c.nombre, c.periodo_id, c.anio_id, c.plantilla_id,
                    c.estado, grupos_json, pesos_json, c.escenario_destino_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            row = conn.execute(
                "SELECT * FROM config_generacion WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_config(row)

    def get_config_generacion(self, config_id: int) -> ConfigGeneracion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM config_generacion WHERE id = ?", (config_id,)
            ).fetchone()
            return self._row_to_config(row) if row else None

    def listar_configs_generacion(
        self, periodo_id: int | None = None
    ) -> list[ConfigGeneracion]:
        with self._get_conn() as conn:
            if periodo_id is not None:
                rows = conn.execute(
                    "SELECT * FROM config_generacion WHERE periodo_id = ? ORDER BY nombre",
                    (periodo_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM config_generacion ORDER BY nombre"
                ).fetchall()
            return [self._row_to_config(r) for r in rows]

    def actualizar_config_generacion(self, c: ConfigGeneracion) -> ConfigGeneracion:
        with self._get_conn() as conn:
            grupos_json = json.dumps(c.grupos)
            pesos_json = json.dumps(c.pesos.model_dump())
            conn.execute(
                """
                UPDATE config_generacion SET
                    nombre = ?, periodo_id = ?, anio_id = ?, plantilla_id = ?,
                    estado = ?, grupos_json = ?, pesos_json = ?,
                    escenario_destino_id = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    c.nombre, c.periodo_id, c.anio_id, c.plantilla_id,
                    c.estado, grupos_json, pesos_json, c.escenario_destino_id,
                    c.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            row = conn.execute(
                "SELECT * FROM config_generacion WHERE id = ?", (c.id,)
            ).fetchone()
            return self._row_to_config(row)

    def eliminar_config_generacion(self, config_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM config_generacion WHERE id = ?", (config_id,)
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def cambiar_estado_config(
        self, config_id: int, nuevo_estado: str
    ) -> ConfigGeneracion:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM config_generacion WHERE id = ?", (config_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Config {config_id} no existe.")
            config = self._row_to_config(row)
            if not config.puede_transicionar_a(nuevo_estado):
                raise ValueError(
                    f"Transición inválida: '{config.estado}' → '{nuevo_estado}'."
                )
            conn.execute(
                """
                UPDATE config_generacion
                   SET estado = ?, updated_at = datetime('now')
                 WHERE id = ?
                """,
                (nuevo_estado, config_id),
            )
            if self._conn is None:
                conn.commit()
            row = conn.execute(
                "SELECT * FROM config_generacion WHERE id = ?", (config_id,)
            ).fetchone()
            return self._row_to_config(row)

    def duplicar_config_generacion(self, config_id: int) -> ConfigGeneracion:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM config_generacion WHERE id = ?", (config_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Config {config_id} no existe.")
            orig = self._row_to_config(row)
            nuevo_nombre = f"{orig.nombre} (copia)"
            grupos_json = json.dumps(orig.grupos)
            pesos_json = json.dumps(orig.pesos.model_dump())
            cursor = conn.execute(
                """
                INSERT INTO config_generacion
                    (nombre, periodo_id, anio_id, plantilla_id, estado,
                     grupos_json, pesos_json, escenario_destino_id)
                VALUES (?, ?, ?, ?, 'borrador', ?, ?, NULL)
                """,
                (
                    nuevo_nombre, orig.periodo_id, orig.anio_id, orig.plantilla_id,
                    grupos_json, pesos_json,
                ),
            )
            if self._conn is None:
                conn.commit()
            nuevo_row = conn.execute(
                "SELECT * FROM config_generacion WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_config(nuevo_row)


__all__ = ["SqliteInfraestructuraRepository"]
