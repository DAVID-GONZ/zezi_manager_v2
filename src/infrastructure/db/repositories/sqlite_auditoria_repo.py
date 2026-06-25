"""
SqliteAuditoriaRepository — implementación SQLite de IAuditoriaRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.policies.audit_chain import calcular_hash, primer_eslabon_roto
from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    TipoEventoSesion,
)

# Columnas que existen en las tablas de auditoría pero NO son campos del modelo
# de dominio. El mapper las descarta antes de construir la entidad Pydantic
# (que prohíbe campos extra). `hash_cadena` es metadato de integridad, no dato
# de negocio.
_COLUMNAS_NO_DOMINIO = frozenset({"hash_cadena"})


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
        d = {k: v for k, v in dict(row).items() if k not in _COLUMNAS_NO_DOMINIO}
        d["tipo_evento"] = TipoEventoSesion(d["tipo_evento"])
        return EventoSesion(**d)

    def _row_to_cambio(self, row: sqlite3.Row) -> RegistroCambio:
        d = {k: v for k, v in dict(row).items() if k not in _COLUMNAS_NO_DOMINIO}
        d["accion"] = AccionCambio(d["accion"])
        return RegistroCambio(**d)

    # ------------------------------------------------------------------
    # Encadenamiento por hash (seguridad_03, M3)
    # ------------------------------------------------------------------

    def _ultimo_hash(self, conn: sqlite3.Connection, tabla: str) -> str | None:
        """Último `hash_cadena` almacenado en `tabla` (None si está vacía)."""
        row = conn.execute(
            f"SELECT hash_cadena FROM {tabla} ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row is not None else None

    @staticmethod
    def _payload_evento(evento: EventoSesion) -> dict:
        """Campos persistidos de un evento (sin id), en el orden de inserción."""
        return {
            "usuario": evento.usuario,
            "usuario_id": evento.usuario_id,
            "tipo_evento": evento.tipo_evento.value,
            "ip_address": evento.ip_address,
            "fecha_hora": evento.fecha_hora.isoformat(),
            "detalles": evento.detalles,
        }

    @staticmethod
    def _payload_cambio(registro: RegistroCambio) -> dict:
        """Campos persistidos de un cambio (sin id), en el orden de inserción."""
        return {
            "usuario_id": registro.usuario_id,
            "accion": registro.accion.value,
            "tabla": registro.tabla,
            "registro_id": registro.registro_id,
            "valor_anterior": registro.valor_anterior,
            "valor_nuevo": registro.valor_nuevo,
            "timestamp": registro.timestamp.isoformat(),
        }

    def _verificar_cadena(self, tabla: str) -> int | None:
        """
        Reconstruye la cadena de `tabla` (solo filas con hash_cadena no nulo,
        orden id ASC) y devuelve el `id` real del primer registro roto, o None.
        """
        if tabla == "auditoria":
            payload_de = self._payload_evento
            row_a_entidad = self._row_to_evento
        else:
            payload_de = self._payload_cambio
            row_a_entidad = self._row_to_cambio

        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM {tabla} "
                "WHERE hash_cadena IS NOT NULL ORDER BY id ASC"
            ).fetchall()

        secuencia: list[tuple[dict, str]] = [
            (payload_de(row_a_entidad(r)), r["hash_cadena"]) for r in rows
        ]
        indice = primer_eslabon_roto(secuencia)
        if indice is None:
            return None
        return int(rows[indice]["id"])

    # ------------------------------------------------------------------
    # EventoSesion — escritura
    # ------------------------------------------------------------------

    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        with self._get_conn() as conn:
            payload = self._payload_evento(evento)
            hash_cadena = calcular_hash(self._ultimo_hash(conn, "auditoria"), payload)
            cursor = conn.execute(
                """
                INSERT INTO auditoria
                    (usuario, usuario_id, tipo_evento, ip_address,
                     fecha_hora, detalles, hash_cadena)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    evento.usuario,
                    evento.usuario_id,
                    evento.tipo_evento.value,
                    evento.ip_address,
                    evento.fecha_hora.isoformat(),
                    evento.detalles,
                    hash_cadena,
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
                  AND fecha_hora >= datetime('now', 'localtime', ?)
                """,
                (usuario, f"-{ventana_minutos} minutes"),
            ).fetchone()
            return int(row[0])

    # ------------------------------------------------------------------
    # RegistroCambio — escritura
    # ------------------------------------------------------------------

    def registrar_cambio(self, registro: RegistroCambio) -> RegistroCambio:
        with self._get_conn() as conn:
            payload = self._payload_cambio(registro)
            hash_cadena = calcular_hash(self._ultimo_hash(conn, "audit_log"), payload)
            cursor = conn.execute(
                """
                INSERT INTO audit_log
                    (usuario_id, accion, tabla, registro_id,
                     valor_anterior, valor_nuevo, timestamp, hash_cadena)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    registro.usuario_id,
                    registro.accion.value,
                    registro.tabla,
                    registro.registro_id,
                    registro.valor_anterior,
                    registro.valor_nuevo,
                    registro.timestamp.isoformat(),
                    hash_cadena,
                ),
            )
            if self._conn is None:
                conn.commit()
            return registro.model_copy(update={"id": cursor.lastrowid})

    def registrar_cambios_masivos(self, registros: list[RegistroCambio]) -> int:
        if not registros:
            return 0
        with self._get_conn() as conn:
            # Precomputar los hashes SECUENCIALMENTE: cada registro encadena con
            # el anterior del lote, partiendo del último hash ya en la tabla. No
            # un hash constante por lote.
            hash_previo = self._ultimo_hash(conn, "audit_log")
            params: list[tuple] = []
            for r in registros:
                hash_cadena = calcular_hash(hash_previo, self._payload_cambio(r))
                params.append((
                    r.usuario_id,
                    r.accion.value,
                    r.tabla,
                    r.registro_id,
                    r.valor_anterior,
                    r.valor_nuevo,
                    r.timestamp.isoformat(),
                    hash_cadena,
                ))
                hash_previo = hash_cadena
            conn.executemany(
                """
                INSERT INTO audit_log
                    (usuario_id, accion, tabla, registro_id,
                     valor_anterior, valor_nuevo, timestamp, hash_cadena)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                params,
            )
            if self._conn is None:
                conn.commit()
            return len(registros)

    # ------------------------------------------------------------------
    # Verificación de integridad (override del port — seguridad_03, M3)
    # ------------------------------------------------------------------

    def verificar_cadena_eventos(self) -> int | None:
        return self._verificar_cadena("auditoria")

    def verificar_cadena_cambios(self) -> int | None:
        return self._verificar_cadena("audit_log")

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
