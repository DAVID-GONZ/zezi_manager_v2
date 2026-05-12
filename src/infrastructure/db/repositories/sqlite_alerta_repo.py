"""
SqliteAlertaRepository — implementación SQLite de IAlertaRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from src.domain.ports.alerta_repo import IAlertaRepository
from src.domain.models.alerta import (
    Alerta,
    ConfiguracionAlerta,
    FiltroAlertasDTO,
    NivelAlerta,
    TipoAlerta,
)


class SqliteAlertaRepository(IAlertaRepository):

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

    def _row_to_config(self, row: sqlite3.Row) -> ConfiguracionAlerta:
        d = dict(row)
        d["tipo_alerta"] = TipoAlerta(d["tipo_alerta"])
        d["activa"] = bool(d["activa"])
        d["notificar_docente"] = bool(d["notificar_docente"])
        d["notificar_director"] = bool(d["notificar_director"])
        d["notificar_acudiente"] = bool(d["notificar_acudiente"])
        return ConfiguracionAlerta(**d)

    def _row_to_alerta(self, row: sqlite3.Row) -> Alerta:
        d = dict(row)
        d["tipo_alerta"] = TipoAlerta(d["tipo_alerta"])
        d["nivel"] = NivelAlerta(d["nivel"])
        d["resuelta"] = bool(d["resuelta"])
        return Alerta(**d)

    # ------------------------------------------------------------------
    # Configuración de alertas
    # ------------------------------------------------------------------

    def get_configuracion(
        self,
        anio_id: int,
        tipo_alerta: TipoAlerta,
    ) -> ConfiguracionAlerta | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM configuracion_alertas
                WHERE anio_id = ? AND tipo_alerta = ?
                """,
                (anio_id, tipo_alerta.value),
            ).fetchone()
            return self._row_to_config(row) if row else None

    def listar_configuraciones(
        self,
        anio_id: int,
        solo_activas: bool = True,
    ) -> list[ConfiguracionAlerta]:
        sql = "SELECT * FROM configuracion_alertas WHERE anio_id = ?"
        params: list = [anio_id]
        if solo_activas:
            sql += " AND activa = 1"
        sql += " ORDER BY tipo_alerta"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_config(r) for r in rows]

    def guardar_configuracion(
        self,
        config: ConfiguracionAlerta,
    ) -> ConfiguracionAlerta:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO configuracion_alertas
                    (anio_id, tipo_alerta, umbral, activa,
                     notificar_docente, notificar_director, notificar_acudiente)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(anio_id, tipo_alerta)
                DO UPDATE SET
                    umbral               = excluded.umbral,
                    activa               = excluded.activa,
                    notificar_docente    = excluded.notificar_docente,
                    notificar_director   = excluded.notificar_director,
                    notificar_acudiente  = excluded.notificar_acudiente
                """,
                (
                    config.anio_id,
                    config.tipo_alerta.value,
                    config.umbral,
                    int(config.activa),
                    int(config.notificar_docente),
                    int(config.notificar_director),
                    int(config.notificar_acudiente),
                ),
            )
            if self._conn is None:
                conn.commit()
            return config.model_copy(update={"id": cursor.lastrowid})

    def desactivar_configuracion(
        self,
        anio_id: int,
        tipo_alerta: TipoAlerta,
    ) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                UPDATE configuracion_alertas SET activa = 0
                WHERE anio_id = ? AND tipo_alerta = ?
                """,
                (anio_id, tipo_alerta.value),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Lectura — alertas
    # ------------------------------------------------------------------

    def get_alerta(self, alerta_id: int) -> Alerta | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM alertas WHERE id = ?", (alerta_id,)
            ).fetchone()
            return self._row_to_alerta(row) if row else None

    def listar_alertas(self, filtro: FiltroAlertasDTO) -> list[Alerta]:
        sql = "SELECT * FROM alertas WHERE 1=1"
        params: list = []
        if filtro.solo_pendientes:
            sql += " AND resuelta = 0"
        if filtro.estudiante_id is not None:
            sql += " AND estudiante_id = ?"
            params.append(filtro.estudiante_id)
        if filtro.tipo_alerta is not None:
            sql += " AND tipo_alerta = ?"
            params.append(filtro.tipo_alerta.value)
        if filtro.nivel is not None:
            sql += " AND nivel = ?"
            params.append(filtro.nivel.value)
        sql += " ORDER BY CASE nivel WHEN 'critica' THEN 0 WHEN 'advertencia' THEN 1 ELSE 2 END, fecha_generacion DESC"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_alerta(r) for r in rows]

    def contar_pendientes(
        self,
        estudiante_id: int | None = None,
        nivel: NivelAlerta | None = None,
    ) -> int:
        sql = "SELECT COUNT(*) FROM alertas WHERE resuelta = 0"
        params: list = []
        if estudiante_id is not None:
            sql += " AND estudiante_id = ?"
            params.append(estudiante_id)
        if nivel is not None:
            sql += " AND nivel = ?"
            params.append(nivel.value)
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return int(row[0])

    def existe_pendiente(
        self,
        estudiante_id: int,
        tipo_alerta: TipoAlerta,
    ) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM alertas
                WHERE estudiante_id = ? AND tipo_alerta = ? AND resuelta = 0
                """,
                (estudiante_id, tipo_alerta.value),
            ).fetchone()
            return row is not None

    # ------------------------------------------------------------------
    # Escritura — alertas
    # ------------------------------------------------------------------

    def guardar_alerta(self, alerta: Alerta) -> Alerta:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO alertas
                    (estudiante_id, tipo_alerta, nivel, descripcion,
                     fecha_generacion, resuelta,
                     fecha_resolucion, usuario_resolucion_id, observacion_resolucion)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    alerta.estudiante_id,
                    alerta.tipo_alerta.value,
                    alerta.nivel.value,
                    alerta.descripcion,
                    alerta.fecha_generacion.isoformat(),
                    int(alerta.resuelta),
                    alerta.fecha_resolucion.isoformat() if alerta.fecha_resolucion else None,
                    alerta.usuario_resolucion_id,
                    alerta.observacion_resolucion,
                ),
            )
            if self._conn is None:
                conn.commit()
            return alerta.model_copy(update={"id": cursor.lastrowid})

    def guardar_alertas_masivas(self, alertas: list[Alerta]) -> int:
        if not alertas:
            return 0
        with self._get_conn() as conn:
            conn.executemany(
                """
                INSERT INTO alertas
                    (estudiante_id, tipo_alerta, nivel, descripcion,
                     fecha_generacion, resuelta,
                     fecha_resolucion, usuario_resolucion_id, observacion_resolucion)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        a.estudiante_id,
                        a.tipo_alerta.value,
                        a.nivel.value,
                        a.descripcion,
                        a.fecha_generacion.isoformat(),
                        int(a.resuelta),
                        a.fecha_resolucion.isoformat() if a.fecha_resolucion else None,
                        a.usuario_resolucion_id,
                        a.observacion_resolucion,
                    )
                    for a in alertas
                ],
            )
            if self._conn is None:
                conn.commit()
            return len(alertas)

    def resolver_alerta(
        self,
        alerta_id: int,
        usuario_id: int,
        observacion: str | None = None,
        fecha: datetime | None = None,
    ) -> bool:
        ts = (fecha or datetime.now()).isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                UPDATE alertas SET
                    resuelta               = 1,
                    fecha_resolucion       = ?,
                    usuario_resolucion_id  = ?,
                    observacion_resolucion = ?
                WHERE id = ? AND resuelta = 0
                """,
                (ts, usuario_id, observacion, alerta_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def resolver_alertas_de_estudiante(
        self,
        estudiante_id: int,
        tipo_alerta: TipoAlerta,
        usuario_id: int,
        observacion: str | None = None,
    ) -> int:
        ts = datetime.now().isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                UPDATE alertas SET
                    resuelta               = 1,
                    fecha_resolucion       = ?,
                    usuario_resolucion_id  = ?,
                    observacion_resolucion = ?
                WHERE estudiante_id = ? AND tipo_alerta = ? AND resuelta = 0
                """,
                (ts, usuario_id, observacion, estudiante_id, tipo_alerta.value),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount


__all__ = ["SqliteAlertaRepository"]
