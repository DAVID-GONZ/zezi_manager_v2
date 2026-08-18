"""
SqliteConvivenciaRepository — implementación SQLite de IConvivenciaRepository.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.models.convivencia import (
    CategoriaObservacion,
    FiltroConvivenciaDTO,
    NotaComportamiento,
    ObservacionPeriodo,
    PlantillaObservacion,
    RegistroComportamiento,
    TipoRegistro,
)
from src.domain.ports.convivencia_repo import IConvivenciaRepository

_TIPOS_NEGATIVOS = ("dificultad", "citacion_acudiente")


class SqliteConvivenciaRepository(IConvivenciaRepository):
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

    def _row_to_observacion(self, row: sqlite3.Row) -> ObservacionPeriodo:
        d = dict(row)
        d["es_publica"] = bool(d["es_publica"])
        return ObservacionPeriodo(**d)

    def _row_to_registro(self, row: sqlite3.Row) -> RegistroComportamiento:
        d = dict(row)
        d["tipo"] = TipoRegistro(d["tipo"])
        d["requiere_firma"] = bool(d["requiere_firma"])
        d["acudiente_notificado"] = bool(d["acudiente_notificado"])
        return RegistroComportamiento(**d)

    def _row_to_nota(self, row: sqlite3.Row) -> NotaComportamiento:
        return NotaComportamiento(**dict(row))

    # ------------------------------------------------------------------
    # Observaciones de Periodo
    # ------------------------------------------------------------------

    def get_observacion(self, observacion_id: int) -> ObservacionPeriodo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM observaciones_periodo WHERE id = ?",
                (observacion_id,),
            ).fetchone()
            return self._row_to_observacion(row) if row else None

    def get_observacion_por_asignacion(
        self, estudiante_id: int, asignacion_id: int, periodo_id: int
    ) -> ObservacionPeriodo | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM observaciones_periodo
                WHERE estudiante_id = ? AND asignacion_id = ? AND periodo_id = ?
                LIMIT 1
                """,
                (estudiante_id, asignacion_id, periodo_id),
            ).fetchone()
            return self._row_to_observacion(row) if row else None

    def listar_observaciones_por_estudiante(
        self, estudiante_id: int, periodo_id: int | None = None, solo_publicas: bool = False
    ) -> list[ObservacionPeriodo]:
        sql = "SELECT * FROM observaciones_periodo WHERE estudiante_id = ?"
        params: list = [estudiante_id]
        if periodo_id is not None:
            sql += " AND periodo_id = ?"
            params.append(periodo_id)
        if solo_publicas:
            sql += " AND es_publica = 1"
        sql += " ORDER BY periodo_id, asignacion_id"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_observacion(r) for r in rows]

    def listar_observaciones_por_grupo(
        self, grupo_id: int, periodo_id: int | None = None, solo_publicas: bool = False
    ) -> list[ObservacionPeriodo]:
        sql = (
            "SELECT op.* FROM observaciones_periodo op "
            "JOIN asignaciones a ON a.id = op.asignacion_id "
            "WHERE a.grupo_id = ?"
        )
        params: list = [grupo_id]
        if periodo_id is not None:
            sql += " AND op.periodo_id = ?"
            params.append(periodo_id)
        if solo_publicas:
            sql += " AND op.es_publica = 1"
        sql += " ORDER BY op.estudiante_id, op.periodo_id, op.asignacion_id"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_observacion(r) for r in rows]

    def guardar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO observaciones_periodo
                    (estudiante_id, asignacion_id, periodo_id, texto,
                     es_publica, fecha_registro, usuario_id, categoria_id, origen,
                     registro_comportamiento_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    observacion.estudiante_id,
                    observacion.asignacion_id,
                    observacion.periodo_id,
                    observacion.texto,
                    int(observacion.es_publica),
                    observacion.fecha_registro.isoformat(),
                    observacion.usuario_id,
                    observacion.categoria_id,
                    observacion.origen,
                    observacion.registro_comportamiento_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return observacion.model_copy(update={"id": cursor.lastrowid})

    def actualizar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE observaciones_periodo
                SET texto = ?, es_publica = ?, categoria_id = ?, origen = ?,
                    registro_comportamiento_id = ?
                WHERE id = ?
                """,
                (
                    observacion.texto,
                    int(observacion.es_publica),
                    observacion.categoria_id,
                    observacion.origen,
                    observacion.registro_comportamiento_id,
                    observacion.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return observacion

    def eliminar_observacion(self, observacion_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM observaciones_periodo WHERE id = ?",
                (observacion_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Registros de Comportamiento
    # ------------------------------------------------------------------

    def get_registro(self, registro_id: int) -> RegistroComportamiento | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM registro_comportamiento WHERE id = ?",
                (registro_id,),
            ).fetchone()
            return self._row_to_registro(row) if row else None

    def _build_filtro_sql(
        self,
        filtro: FiltroConvivenciaDTO,
        institucion_id: int | None = None,
        *,
        select: str = "rc.*",
    ) -> tuple[str, list]:
        # Multi-tenant (paso_32): cuando el listado cruza grupos (sin grupo ni
        # estudiante en el filtro) se acota por institución vía join a `grupos`.
        # El join solo se añade cuando hace falta para no penalizar las consultas
        # ya scopeadas por estudiante/grupo.
        params: list = []
        join = ""
        if institucion_id is not None:
            join = " JOIN grupos g ON g.id = rc.grupo_id"
        sql = f"SELECT {select} FROM registro_comportamiento rc{join} WHERE 1=1"
        if institucion_id is not None:
            sql += " AND g.institucion_id = ?"
            params.append(institucion_id)
        if filtro.estudiante_id is not None:
            sql += " AND rc.estudiante_id = ?"
            params.append(filtro.estudiante_id)
        if filtro.grupo_id is not None:
            sql += " AND rc.grupo_id = ?"
            params.append(filtro.grupo_id)
        if filtro.periodo_id is not None:
            sql += " AND rc.periodo_id = ?"
            params.append(filtro.periodo_id)
        if filtro.tipo is not None:
            sql += " AND rc.tipo = ?"
            params.append(filtro.tipo.value)
        if filtro.solo_negativos:
            placeholders = ",".join("?" for _ in _TIPOS_NEGATIVOS)
            sql += f" AND rc.tipo IN ({placeholders})"
            params.extend(_TIPOS_NEGATIVOS)
        return sql, params

    def listar_registros(
        self,
        filtro: FiltroConvivenciaDTO,
        institucion_id: int | None = None,
    ) -> list[RegistroComportamiento]:
        sql, params = self._build_filtro_sql(filtro, institucion_id)
        sql += " ORDER BY rc.fecha DESC, rc.id DESC"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_registro(r) for r in rows]

    def contar_registros(
        self,
        filtro: FiltroConvivenciaDTO,
        institucion_id: int | None = None,
    ) -> int:
        sql, params = self._build_filtro_sql(filtro, institucion_id, select="COUNT(*)")
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return int(row[0])

    def guardar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO registro_comportamiento
                    (estudiante_id, grupo_id, periodo_id, fecha, tipo,
                     descripcion, seguimiento, requiere_firma,
                     acudiente_notificado, usuario_registro_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    registro.estudiante_id,
                    registro.grupo_id,
                    registro.periodo_id,
                    registro.fecha.isoformat(),
                    registro.tipo.value,
                    registro.descripcion,
                    registro.seguimiento,
                    int(registro.requiere_firma),
                    int(registro.acudiente_notificado),
                    registro.usuario_registro_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return registro.model_copy(update={"id": cursor.lastrowid})

    def actualizar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE registro_comportamiento SET
                    seguimiento          = ?,
                    requiere_firma       = ?,
                    acudiente_notificado = ?
                WHERE id = ?
                """,
                (
                    registro.seguimiento,
                    int(registro.requiere_firma),
                    int(registro.acudiente_notificado),
                    registro.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return registro

    def eliminar_registro(self, registro_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM registro_comportamiento WHERE id = ?",
                (registro_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Notas de Comportamiento
    # ------------------------------------------------------------------

    def get_nota(self, estudiante_id: int, periodo_id: int) -> NotaComportamiento | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM nota_comportamiento_periodo
                WHERE estudiante_id = ? AND periodo_id = ?
                """,
                (estudiante_id, periodo_id),
            ).fetchone()
            return self._row_to_nota(row) if row else None

    def listar_notas_por_estudiante(self, estudiante_id: int) -> list[NotaComportamiento]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM nota_comportamiento_periodo
                WHERE estudiante_id = ?
                ORDER BY periodo_id DESC
                """,
                (estudiante_id,),
            ).fetchall()
            return [self._row_to_nota(r) for r in rows]

    def listar_notas_por_grupo(self, grupo_id: int, periodo_id: int) -> list[NotaComportamiento]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM nota_comportamiento_periodo
                WHERE grupo_id = ? AND periodo_id = ?
                ORDER BY estudiante_id
                """,
                (grupo_id, periodo_id),
            ).fetchall()
            return [self._row_to_nota(r) for r in rows]

    def guardar_nota(self, nota: NotaComportamiento) -> NotaComportamiento:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO nota_comportamiento_periodo
                    (estudiante_id, grupo_id, periodo_id, valor,
                     desempeno_id, observacion, usuario_id)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(estudiante_id, grupo_id, periodo_id)
                DO UPDATE SET
                    valor        = excluded.valor,
                    desempeno_id = excluded.desempeno_id,
                    observacion  = excluded.observacion,
                    usuario_id   = excluded.usuario_id
                """,
                (
                    nota.estudiante_id,
                    nota.grupo_id,
                    nota.periodo_id,
                    nota.valor,
                    nota.desempeno_id,
                    nota.observacion,
                    nota.usuario_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return nota.model_copy(update={"id": cursor.lastrowid})

    # ------------------------------------------------------------------
    # Categorías de Observación (convivencia_09)
    # ------------------------------------------------------------------

    def _row_to_categoria(self, row: sqlite3.Row) -> CategoriaObservacion:
        d = dict(row)
        d["es_comportamental"] = bool(d["es_comportamental"])
        d["activa"] = bool(d["activa"])
        return CategoriaObservacion(**d)

    def listar_categorias(
        self, solo_activas: bool = True, institucion_id: int | None = None
    ) -> list[CategoriaObservacion]:
        sql = "SELECT * FROM categorias_observacion WHERE 1=1"
        params: list = []
        if solo_activas:
            sql += " AND activa = 1"
        if institucion_id is not None:
            sql += " AND institucion_id = ?"
            params.append(institucion_id)
        sql += " ORDER BY nombre"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_categoria(r) for r in rows]

    def get_categoria(self, categoria_id: int) -> CategoriaObservacion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM categorias_observacion WHERE id = ?",
                (categoria_id,),
            ).fetchone()
            return self._row_to_categoria(row) if row else None

    def guardar_categoria(self, categoria: CategoriaObservacion) -> CategoriaObservacion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO categorias_observacion
                    (nombre, es_comportamental, activa, institucion_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    categoria.nombre,
                    int(categoria.es_comportamental),
                    int(categoria.activa),
                    categoria.institucion_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return categoria.model_copy(update={"id": cursor.lastrowid})

    def actualizar_categoria(self, categoria: CategoriaObservacion) -> CategoriaObservacion:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE categorias_observacion
                SET nombre = ?, es_comportamental = ?, activa = ?
                WHERE id = ?
                """,
                (
                    categoria.nombre,
                    int(categoria.es_comportamental),
                    int(categoria.activa),
                    categoria.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return categoria

    # ------------------------------------------------------------------
    # Catálogo de plantillas de observación (convivencia_12)
    # ------------------------------------------------------------------

    def _row_to_plantilla(self, row: sqlite3.Row) -> PlantillaObservacion:
        d = dict(row)
        d["activa"] = bool(d["activa"])
        return PlantillaObservacion(**d)

    def listar_plantillas(
        self,
        categoria_id: int | None = None,
        solo_activas: bool = True,
        institucion_id: int | None = None,
    ) -> list[PlantillaObservacion]:
        sql = "SELECT * FROM plantillas_observacion WHERE 1=1"
        params: list = []
        if solo_activas:
            sql += " AND activa = 1"
        if categoria_id is not None:
            sql += " AND categoria_id = ?"
            params.append(categoria_id)
        if institucion_id is not None:
            sql += " AND institucion_id = ?"
            params.append(institucion_id)
        sql += " ORDER BY uso_count DESC"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_plantilla(r) for r in rows]

    def get_plantilla(self, plantilla_id: int) -> PlantillaObservacion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM plantillas_observacion WHERE id = ?",
                (plantilla_id,),
            ).fetchone()
            return self._row_to_plantilla(row) if row else None

    def guardar_plantilla(self, plantilla: PlantillaObservacion) -> PlantillaObservacion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO plantillas_observacion
                    (texto, categoria_id, uso_count, activa, institucion_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    plantilla.texto,
                    plantilla.categoria_id,
                    plantilla.uso_count,
                    int(plantilla.activa),
                    plantilla.institucion_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return plantilla.model_copy(update={"id": cursor.lastrowid})

    def actualizar_plantilla(self, plantilla: PlantillaObservacion) -> PlantillaObservacion:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE plantillas_observacion
                SET texto = ?, categoria_id = ?, activa = ?
                WHERE id = ?
                """,
                (
                    plantilla.texto,
                    plantilla.categoria_id,
                    int(plantilla.activa),
                    plantilla.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return plantilla

    def incrementar_uso_plantilla(self, plantilla_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE plantillas_observacion SET uso_count = uso_count + 1 WHERE id = ?",
                (plantilla_id,),
            )
            if self._conn is None:
                conn.commit()


__all__ = ["SqliteConvivenciaRepository"]
