"""
SqliteAuditoriaRepository — implementación SQLite de IAuditoriaRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    TipoEventoSesion,
)


class SqliteAuditoriaRepository(IAuditoriaRepository):

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

    def _row_to_evento(self, row: sqlite3.Row) -> EventoSesion:
        d = dict(row)
        d["tipo_evento"] = TipoEventoSesion(d["tipo_evento"])
        return EventoSesion(**d)

    def _row_to_cambio(self, row: sqlite3.Row) -> RegistroCambio:
        d = dict(row)
        d["accion"] = AccionCambio(d["accion"])
        return RegistroCambio(**d)

    # ------------------------------------------------------------------
    # EventoSesion — escritura
    # ------------------------------------------------------------------

    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO auditoria
                    (usuario, usuario_id, tipo_evento, ip_address,
                     fecha_hora, detalles)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    evento.usuario,
                    evento.usuario_id,
                    evento.tipo_evento.value,
                    evento.ip_address,
                    evento.fecha_hora.isoformat(),
                    evento.detalles,
                ),
            )
            if self._conn is None:
                conn.commit()
            return evento.model_copy(update={"id": cursor.lastrowid})

    # ------------------------------------------------------------------
    # EventoSesion — lectura
    # ------------------------------------------------------------------

    def listar_eventos(self, filtro: FiltroAuditoriaDTO) -> list[EventoSesion]:
        sql = "SELECT * FROM auditoria WHERE 1=1"
        params: list = []
        if filtro.usuario_id is not None:
            sql += " AND usuario_id = ?"
            params.append(filtro.usuario_id)
        if filtro.tipo_evento is not None:
            sql += " AND tipo_evento = ?"
            params.append(filtro.tipo_evento.value)
        if filtro.desde is not None:
            sql += " AND fecha_hora >= ?"
            params.append(filtro.desde.isoformat())
        if filtro.hasta is not None:
            sql += " AND fecha_hora <= ?"
            params.append(filtro.hasta.isoformat())
        sql += " ORDER BY fecha_hora DESC"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_evento(r) for r in rows]

    def get_ultimo_login(self, usuario_id: int) -> EventoSesion | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM auditoria
                WHERE usuario_id = ? AND tipo_evento = 'LOGIN_EXITOSO'
                ORDER BY fecha_hora DESC
                LIMIT 1
                """,
                (usuario_id,),
            ).fetchone()
            return self._row_to_evento(row) if row else None

    def contar_fallos_recientes(
        self,
        usuario: str,
        ventana_minutos: int = 30,
    ) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM auditoria
                WHERE LOWER(usuario) = LOWER(?)
                  AND tipo_evento = 'LOGIN_FALLIDO'
                  AND fecha_hora >= datetime('now', ?)
                """,
                (usuario, f"-{ventana_minutos} minutes"),
            ).fetchone()
            return int(row[0])

    # ------------------------------------------------------------------
    # RegistroCambio — escritura
    # ------------------------------------------------------------------

    def registrar_cambio(self, registro: RegistroCambio) -> RegistroCambio:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_log
                    (usuario_id, accion, tabla, registro_id,
                     valor_anterior, valor_nuevo, timestamp)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    registro.usuario_id,
                    registro.accion.value,
                    registro.tabla,
                    registro.registro_id,
                    registro.valor_anterior,
                    registro.valor_nuevo,
                    registro.timestamp.isoformat(),
                ),
            )
            if self._conn is None:
                conn.commit()
            return registro.model_copy(update={"id": cursor.lastrowid})

    def registrar_cambios_masivos(self, registros: list[RegistroCambio]) -> int:
        if not registros:
            return 0
        with self._get_conn() as conn:
            conn.executemany(
                """
                INSERT INTO audit_log
                    (usuario_id, accion, tabla, registro_id,
                     valor_anterior, valor_nuevo, timestamp)
                VALUES (?,?,?,?,?,?,?)
                """,
                [
                    (
                        r.usuario_id,
                        r.accion.value,
                        r.tabla,
                        r.registro_id,
                        r.valor_anterior,
                        r.valor_nuevo,
                        r.timestamp.isoformat(),
                    )
                    for r in registros
                ],
            )
            if self._conn is None:
                conn.commit()
            return len(registros)

    # ------------------------------------------------------------------
    # RegistroCambio — lectura
    # ------------------------------------------------------------------

    def listar_cambios(self, filtro: FiltroAuditoriaDTO) -> list[RegistroCambio]:
        sql = "SELECT * FROM audit_log WHERE 1=1"
        params: list = []
        if filtro.usuario_id is not None:
            sql += " AND usuario_id = ?"
            params.append(filtro.usuario_id)
        if filtro.tabla is not None:
            sql += " AND tabla = ?"
            params.append(filtro.tabla)
        if filtro.accion is not None:
            sql += " AND accion = ?"
            params.append(filtro.accion.value)
        if filtro.desde is not None:
            sql += " AND timestamp >= ?"
            params.append(filtro.desde.isoformat())
        if filtro.hasta is not None:
            sql += " AND timestamp <= ?"
            params.append(filtro.hasta.isoformat())
        sql += " ORDER BY timestamp DESC"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_cambio(r) for r in rows]

    def listar_cambios_por_registro(
        self,
        tabla: str,
        registro_id: int,
    ) -> list[RegistroCambio]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM audit_log
                WHERE tabla = ? AND registro_id = ?
                ORDER BY timestamp ASC
                """,
                (tabla, registro_id),
            ).fetchall()
            return [self._row_to_cambio(r) for r in rows]

    def get_cambio(self, cambio_id: int) -> RegistroCambio | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM audit_log WHERE id = ?", (cambio_id,)
            ).fetchone()
            return self._row_to_cambio(row) if row else None


__all__ = ["SqliteAuditoriaRepository"]
