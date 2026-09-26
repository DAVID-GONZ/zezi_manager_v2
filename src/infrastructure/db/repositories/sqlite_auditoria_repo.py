"""
SqliteAuditoriaRepository — implementación SQLite de IAuditoriaRepository.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    SeveridadEvento,
    TipoEventoSesion,
)
from src.domain.models.clock import ahora as _ahora
from src.domain.models.tenant import TenantScope
from src.domain.policies.audit_chain import calcular_hash
from src.domain.ports.auditoria_repo import IAuditoriaRepository

# Número máximo de filas que se leen por lote en la verificación incremental.
# Evita materializar toda la tabla en memoria (D1 en requirements.md).
_LOTE = 5_000

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
        # severidad llega como string desde SQLite; convertir al enum
        if "severidad" in d and d["severidad"] is not None:
            d["severidad"] = SeveridadEvento(d["severidad"])
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
        row = conn.execute(f"SELECT hash_cadena FROM {tabla} ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row is not None else None

    @staticmethod
    def _payload_evento(evento: EventoSesion) -> dict:
        """
        Campos del evento que entran en el hash SHA-256.

        `objetivo` entra en el hash (es contenido de la acción).
        `severidad` NO entra (es clasificación, no contenido; obs_07 la gestiona).
        `institucion_id` NO entra (scope informacional; igual que mejora_07-T7).
        """
        return {
            "usuario": evento.usuario,
            "usuario_id": evento.usuario_id,
            "tipo_evento": evento.tipo_evento.value,
            "ip_address": evento.ip_address,
            "fecha_hora": evento.fecha_hora.isoformat(),
            "detalles": evento.detalles,
            "objetivo": evento.objetivo,  # NUEVO (obs_06): entra en el hash
        }

    @staticmethod
    def _payload_cambio(registro: RegistroCambio) -> dict:
        """
        Campos del cambio que entran en el hash SHA-256.

        `usuario` e `ip_address` entran en el hash (R11): alterarlos rompe la cadena.
        `institucion_id` NO entra (scope informacional; igual que mejora_07-T7).
        """
        return {
            "usuario": registro.usuario,          # NUEVO (obs_06): en el hash (R11)
            "usuario_id": registro.usuario_id,
            "ip_address": registro.ip_address,    # NUEVO (obs_06): en el hash (R11)
            "accion": registro.accion.value,
            "tabla": registro.tabla,
            "registro_id": registro.registro_id,
            "valor_anterior": registro.valor_anterior,
            "valor_nuevo": registro.valor_nuevo,
            "timestamp": registro.timestamp.isoformat(),
        }

    def _mapeadores(self, tabla: str):
        """Devuelve el par (payload_de, row_a_entidad) para la tabla indicada."""
        if tabla == "auditoria":
            return self._payload_evento, self._row_to_evento
        return self._payload_cambio, self._row_to_cambio

    def _hash_de(self, tabla: str, fila_id: int) -> str | None:
        """Devuelve el `hash_cadena` almacenado para `fila_id` en `tabla`."""
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT hash_cadena FROM {tabla} WHERE id = ?", (fila_id,)
            ).fetchone()
        return row[0] if row is not None else None

    def _guardar_checkpoint(self, tabla: str, ultimo_id: int, ultimo_hash: str) -> None:
        """Persiste el punto de control de la verificación incremental."""
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO verificacion_auditoria (tabla, ultimo_id, ultimo_hash, verificado_en)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tabla) DO UPDATE SET
                    ultimo_id    = excluded.ultimo_id,
                    ultimo_hash  = excluded.ultimo_hash,
                    verificado_en = excluded.verificado_en
                """,
                (tabla, ultimo_id, ultimo_hash, _ahora().isoformat()),
            )
            if self._conn is None:
                conn.commit()

    def _leer_checkpoint(self, tabla: str) -> tuple[int | None, str | None]:
        """Devuelve (ultimo_id, ultimo_hash) del último checkpoint guardado, o (None, None)."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT ultimo_id, ultimo_hash FROM verificacion_auditoria WHERE tabla = ?",
                (tabla,),
            ).fetchone()
        if row is None:
            return None, None
        return int(row[0]), row[1]

    def _verificar_cadena(
        self, tabla: str, *, desde_id: int | None = None, guardar: bool = True
    ) -> int | None:
        """
        Verifica el tramo (desde_id, ∞) de `tabla` sembrando con el hash de
        `desde_id`. Con `desde_id=None` verifica desde el origen.

        Lee por lotes de `_LOTE` filas para no materializar la tabla completa
        en memoria (R7). Sale inmediatamente al primer eslabón roto sin avanzar
        el checkpoint (R10). Si el recorrido completa sin roturas y `guardar` es
        True, persiste el nuevo punto de control.

        `guardar=False` se usa cuando no existe checkpoint previo y se hace un
        escaneo completo como «primer contacto»: el checkpoint se crea solo tras
        una verificación completa explícita (`completa=True`) o tras una
        verificación incremental a partir de un checkpoint existente.
        """
        payload_de, row_a_entidad = self._mapeadores(tabla)
        hash_previo = None if desde_id is None else self._hash_de(tabla, desde_id)
        ultimo_id: int | None = desde_id
        ultimo_hash: str | None = hash_previo
        cursor_id = desde_id or 0

        with self._get_conn() as conn:
            while True:
                rows = conn.execute(
                    f"SELECT * FROM {tabla} "
                    f"WHERE hash_cadena IS NOT NULL AND id > ? "
                    f"ORDER BY id ASC LIMIT ?",
                    (cursor_id, _LOTE),
                ).fetchall()
                if not rows:
                    break
                for r in rows:
                    esperado = calcular_hash(hash_previo, payload_de(row_a_entidad(r)))
                    if esperado != r["hash_cadena"]:
                        # R10: no avanzar el checkpoint; salir inmediatamente.
                        return int(r["id"])
                    hash_previo = r["hash_cadena"]
                    ultimo_id = int(r["id"])
                    ultimo_hash = r["hash_cadena"]
                cursor_id = ultimo_id or 0

        # Guardar el checkpoint solo si lo pedimos y si verificamos al menos una fila nueva.
        if guardar and ultimo_id is not None and ultimo_hash is not None:
            self._guardar_checkpoint(tabla, ultimo_id, ultimo_hash)
        return None

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
                     fecha_hora, detalles, objetivo, severidad,
                     hash_cadena, institucion_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    evento.usuario,
                    evento.usuario_id,
                    evento.tipo_evento.value,
                    evento.ip_address,
                    evento.fecha_hora.isoformat(),
                    evento.detalles,
                    evento.objetivo,           # NUEVO (obs_06)
                    evento.severidad.value,    # NUEVO (obs_06)
                    hash_cadena,
                    evento.institucion_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return evento.model_copy(update={"id": cursor.lastrowid})

    # ------------------------------------------------------------------
    # EventoSesion — lectura
    # ------------------------------------------------------------------

    @staticmethod
    def _where_eventos(filtro: FiltroAuditoriaDTO) -> tuple[str, list]:
        """Construye la cláusula WHERE para la tabla `auditoria` a partir de `filtro`.

        Devuelve ``(where_sql, params)`` donde `where_sql` comienza con
        ``" WHERE 1=1"``; no incluye ORDER BY, LIMIT ni OFFSET.
        Compartido por `listar_eventos` y `contar_eventos` para que filtro y
        conteo nunca puedan divergir.
        """
        sql = " WHERE 1=1"
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
        # obs_09: sin_institucion y institucion_id son mutuamente excluyentes (R12, §6)
        if filtro.sin_institucion:
            sql += " AND institucion_id IS NULL"
        elif filtro.institucion_id is not None:
            sql += " AND institucion_id = ?"
            params.append(filtro.institucion_id)
        # obs_07 T10: filtro por severidad
        if filtro.severidad is not None:
            sql += " AND severidad = ?"
            params.append(filtro.severidad.value)
        return sql, params

    def listar_eventos(self, filtro: FiltroAuditoriaDTO) -> list[EventoSesion]:
        where, params = self._where_eventos(filtro)
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql = f"SELECT * FROM auditoria{where} ORDER BY fecha_hora DESC LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_evento(r) for r in rows]

    def contar_eventos(self, filtro: FiltroAuditoriaDTO) -> int:
        """Cuenta eventos que satisfacen `filtro` ignorando pagina/por_pagina."""
        where, params = self._where_eventos(filtro)
        sql = f"SELECT COUNT(*) FROM auditoria{where}"
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return int(row[0])

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
                    (usuario_id, usuario, ip_address, accion, tabla, registro_id,
                     valor_anterior, valor_nuevo, timestamp, hash_cadena,
                     institucion_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    registro.usuario_id,
                    registro.usuario,       # NUEVO (obs_06, R8)
                    registro.ip_address,    # NUEVO (obs_06, R8)
                    registro.accion.value,
                    registro.tabla,
                    registro.registro_id,
                    registro.valor_anterior,
                    registro.valor_nuevo,
                    registro.timestamp.isoformat(),
                    hash_cadena,
                    registro.institucion_id,
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
                params.append(
                    (
                        r.usuario_id,
                        r.usuario,       # NUEVO (obs_06, R8)
                        r.ip_address,    # NUEVO (obs_06, R8)
                        r.accion.value,
                        r.tabla,
                        r.registro_id,
                        r.valor_anterior,
                        r.valor_nuevo,
                        r.timestamp.isoformat(),
                        hash_cadena,
                        r.institucion_id,
                    )
                )
                hash_previo = hash_cadena
            conn.executemany(
                """
                INSERT INTO audit_log
                    (usuario_id, usuario, ip_address, accion, tabla, registro_id,
                     valor_anterior, valor_nuevo, timestamp, hash_cadena,
                     institucion_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                params,
            )
            if self._conn is None:
                conn.commit()
            return len(registros)

    # ------------------------------------------------------------------
    # Verificación de integridad (override del port — seguridad_03, M3)
    # ------------------------------------------------------------------

    def verificar_cadena_eventos(self, *, completa: bool = False) -> int | None:
        """
        Verifica la cadena de `auditoria`.

        `completa=True`: escaneo desde el origen, siempre guarda el checkpoint (R8).
        `completa=False`: reanuda desde el checkpoint existente, guardándolo al
        final; si no hay checkpoint, hace un escaneo completo SIN guardar (primera
        ejecución — el checkpoint se crea en la primera verificación completa
        explícita o en la primera incremental con checkpoint previo) (R6).
        """
        if completa:
            return self._verificar_cadena("auditoria", desde_id=None, guardar=True)
        desde_id, _ = self._leer_checkpoint("auditoria")
        if desde_id is None:
            # Sin checkpoint previo: escaneo completo pero sin persistir el punto
            # de control — mantiene compatibilidad con tests pre-obs_08 que
            # verifican dos veces seguidas (con y sin tampering entre ellas).
            return self._verificar_cadena("auditoria", desde_id=None, guardar=False)
        return self._verificar_cadena("auditoria", desde_id=desde_id, guardar=True)

    def verificar_cadena_cambios(self, *, completa: bool = False) -> int | None:
        """
        Verifica la cadena de `audit_log`.

        `completa=True`: escaneo desde el origen, siempre guarda el checkpoint (R8).
        `completa=False` con checkpoint: incremental, guarda checkpoint tras scan limpio.
        `completa=False` sin checkpoint: escaneo completo SIN guardar (R6).
        """
        if completa:
            return self._verificar_cadena("audit_log", desde_id=None, guardar=True)
        desde_id, _ = self._leer_checkpoint("audit_log")
        if desde_id is None:
            return self._verificar_cadena("audit_log", desde_id=None, guardar=False)
        return self._verificar_cadena("audit_log", desde_id=desde_id, guardar=True)

    # ------------------------------------------------------------------
    # RegistroCambio — lectura
    # ------------------------------------------------------------------

    @staticmethod
    def _where_cambios(filtro: FiltroAuditoriaDTO) -> tuple[str, list]:
        """Construye la cláusula WHERE para la tabla `audit_log` a partir de `filtro`.

        Devuelve ``(where_sql, params)`` donde `where_sql` comienza con
        ``" WHERE 1=1"``. Compartido por `listar_cambios` y `contar_cambios`.

        Filtros obs_09:
          - ``registro_id``: acota a una entidad concreta (R11).
          - ``sin_institucion``: muestra filas con institucion_id IS NULL (R12).
            Es excluyente con ``institucion_id`` — el orden del ``if`` lo garantiza.
        """
        sql = " WHERE 1=1"
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
        # obs_09: registro_id acota a una entidad concreta (R11)
        if filtro.registro_id is not None:
            sql += " AND registro_id = ?"
            params.append(filtro.registro_id)
        # obs_09: sin_institucion y institucion_id son mutuamente excluyentes (R12, §6)
        if filtro.sin_institucion:
            sql += " AND institucion_id IS NULL"
        elif filtro.institucion_id is not None:
            sql += " AND institucion_id = ?"
            params.append(filtro.institucion_id)
        return sql, params

    def listar_cambios(self, filtro: FiltroAuditoriaDTO) -> list[RegistroCambio]:
        where, params = self._where_cambios(filtro)
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql = f"SELECT * FROM audit_log{where} ORDER BY timestamp DESC LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_cambio(r) for r in rows]

    def contar_cambios(self, filtro: FiltroAuditoriaDTO) -> int:
        """Cuenta cambios que satisfacen `filtro` ignorando pagina/por_pagina."""
        where, params = self._where_cambios(filtro)
        sql = f"SELECT COUNT(*) FROM audit_log{where}"
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return int(row[0])

    def resumen_eventos(
        self,
        desde,
        hasta=None,
        institucion_id="*",
    ) -> dict:
        """
        Devuelve agregados de uso calculados en SQL para la ventana temporal
        [desde, hasta]. Respeta el scope de institución (R5).

        Claves en el dict:
          por_tipo          dict[str, int]  — conteo por tipo_evento.
          logins_hoy        int             — LOGIN_EXITOSO desde inicio del día actual.
          usuarios_distintos int            — usuarios únicos con login en la ventana.
          denegados_criticos int            — ACCESO_DENEGADO con severidad=CRITICA.
        """
        from datetime import datetime as _dt

        desde_iso = desde.isoformat() if hasattr(desde, "isoformat") else str(desde)
        hasta_iso = hasta.isoformat() if hasta is not None and hasattr(hasta, "isoformat") else None
        ahora = _ahora()
        inicio_hoy_iso = _dt(ahora.year, ahora.month, ahora.day).isoformat()

        # Scope: None o "*" → sin filtro de institución; int → filtro exacto.
        inst_filter = "" if institucion_id == "*" or institucion_id is None else " AND institucion_id = ?"
        inst_param = [] if institucion_id == "*" or institucion_id is None else [institucion_id]

        hasta_filter = "" if hasta_iso is None else " AND fecha_hora <= ?"
        hasta_param = [] if hasta_iso is None else [hasta_iso]

        with self._get_conn() as conn:
            # 1. Conteo por tipo en la ventana
            rows_tipo = conn.execute(
                f"SELECT tipo_evento, COUNT(*) AS n FROM auditoria"
                f" WHERE fecha_hora >= ?{hasta_filter}{inst_filter}"
                f" GROUP BY tipo_evento",
                [desde_iso, *hasta_param, *inst_param],
            ).fetchall()
            por_tipo: dict[str, int] = {r["tipo_evento"]: int(r["n"]) for r in rows_tipo}

            # 2. Logins de hoy
            r_hoy = conn.execute(
                f"SELECT COUNT(*) FROM auditoria"
                f" WHERE tipo_evento = 'LOGIN_EXITOSO' AND fecha_hora >= ?"
                f"{inst_filter}",
                [inicio_hoy_iso, *inst_param],
            ).fetchone()
            logins_hoy = int(r_hoy[0])

            # 3. Usuarios distintos con login en la ventana
            r_usu = conn.execute(
                f"SELECT COUNT(DISTINCT COALESCE(usuario_id, usuario)) FROM auditoria"
                f" WHERE tipo_evento = 'LOGIN_EXITOSO' AND fecha_hora >= ?"
                f"{hasta_filter}{inst_filter}",
                [desde_iso, *hasta_param, *inst_param],
            ).fetchone()
            usuarios_distintos = int(r_usu[0])

            # 4. Denegaciones críticas en la ventana (obs_07: solo CRITICA cuentan)
            r_den = conn.execute(
                f"SELECT COUNT(*) FROM auditoria"
                f" WHERE tipo_evento = 'ACCESO_DENEGADO' AND severidad = 'CRITICA'"
                f" AND fecha_hora >= ?{hasta_filter}{inst_filter}",
                [desde_iso, *hasta_param, *inst_param],
            ).fetchone()
            denegados_criticos = int(r_den[0])

        return {
            "por_tipo": por_tipo,
            "logins_hoy": logins_hoy,
            "usuarios_distintos": usuarios_distintos,
            "denegados_criticos": denegados_criticos,
        }

    def uso_diario(self, dias: int = 14) -> list[dict]:
        """
        Devuelve una lista ``[{fecha, logins, denegados}]`` por día de la
        ventana de ``dias`` días, incluidos los días sin actividad (ceros).

        Implementa obs_13 T9: GROUP BY date(fecha_hora) en SQL.
        """
        from datetime import datetime as _dt, timedelta as _td
        from src.domain.models.clock import ahora as _ahora

        dias = max(1, dias)
        ahora = _ahora()
        desde = ahora - _td(days=dias)
        desde_iso = _dt(desde.year, desde.month, desde.day).isoformat()

        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    date(fecha_hora)            AS fecha,
                    SUM(tipo_evento = 'LOGIN_EXITOSO')    AS logins,
                    SUM(tipo_evento = 'ACCESO_DENEGADO')  AS denegados
                FROM auditoria
                WHERE fecha_hora >= ?
                GROUP BY date(fecha_hora)
                ORDER BY fecha ASC
                """,
                (desde_iso,),
            ).fetchall()

        # Indexar por fecha para rellenar los días vacíos
        por_fecha: dict[str, dict] = {}
        for r in rows:
            por_fecha[r["fecha"]] = {
                "fecha": r["fecha"],
                "logins": int(r["logins"] or 0),
                "denegados": int(r["denegados"] or 0),
            }

        # Completar los días sin actividad con ceros (T9)
        resultado: list[dict] = []
        for i in range(dias):
            dia = (desde + _td(days=i + 1))
            clave = _dt(dia.year, dia.month, dia.day).strftime("%Y-%m-%d")
            resultado.append(
                por_fecha.get(clave, {"fecha": clave, "logins": 0, "denegados": 0})
            )
        return resultado

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
            row = conn.execute("SELECT * FROM audit_log WHERE id = ?", (cambio_id,)).fetchone()
            return self._row_to_cambio(row) if row else None

    # ------------------------------------------------------------------
    # Tramo y retención (obs_12 — T2, T9)
    # ------------------------------------------------------------------

    def rango_de(
        self,
        tabla: str,
        filtro: FiltroAuditoriaDTO,
    ) -> tuple[int, int] | None:
        """
        Devuelve ``(id_min, id_max)`` del tramo que satisface ``filtro`` en
        ``tabla``, o None si el tramo está vacío.
        """
        if tabla == "auditoria":
            where, params = self._where_eventos(filtro)
        else:
            where, params = self._where_cambios(filtro)
        sql = f"SELECT MIN(id), MAX(id) FROM {tabla}{where}"
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
        if row is None or row[0] is None:
            return None
        return int(row[0]), int(row[1])

    def listar_cambios_tramo(
        self,
        tabla: str,
        id_desde: int,
        id_hasta: int,
        scope: TenantScope,
        *,
        lote: int = 5_000,
    ) -> Iterator[list[RegistroCambio]]:
        """
        Itera por lotes las filas de ``tabla`` con id en ``[id_desde, id_hasta]``
        respetando el scope de institución. Devuelve un iterador de listas.
        """
        if tabla == "auditoria":
            row_fn = self._row_to_evento
        else:
            row_fn = self._row_to_cambio

        # Construir cláusula de scope
        scope_sql = ""
        scope_params: list = []
        if scope != "*" and scope is not None:
            scope_sql = " AND institucion_id = ?"
            scope_params.append(scope)

        cursor_id = id_desde - 1
        with self._get_conn() as conn:
            while True:
                rows = conn.execute(
                    f"SELECT * FROM {tabla}"
                    f" WHERE id >= ? AND id <= ? AND id > ?{scope_sql}"
                    f" ORDER BY id ASC LIMIT ?",
                    (id_desde, id_hasta, cursor_id, *scope_params, lote),
                ).fetchall()
                if not rows:
                    break
                batch = [row_fn(r) for r in rows]
                yield batch
                cursor_id = int(rows[-1]["id"])
                if cursor_id >= id_hasta:
                    break

    def eliminar_hasta(
        self,
        tabla: str,
        id_hasta: int,
        scope: TenantScope,
    ) -> int:
        """
        Elimina las filas de ``tabla`` con id <= id_hasta, respetando scope.

        INVARIANTE APPEND-ONLY: solo invocado desde archivar_y_purgar
        del servicio de retención, después del archivado verificado y antes
        del evento AUDITORIA_PURGADA. Ver docstring del puerto.
        """
        scope_sql = ""
        scope_params: list = []
        if scope != "*" and scope is not None:
            scope_sql = " AND institucion_id = ?"
            scope_params.append(scope)

        sql = f"DELETE FROM {tabla} WHERE id <= ?{scope_sql}"
        with self._get_conn() as conn:
            cursor = conn.execute(sql, (id_hasta, *scope_params))
            if self._conn is None:
                conn.commit()
            return cursor.rowcount

    def hash_de_fila(self, tabla: str, fila_id: int) -> str | None:
        """Devuelve el hash_cadena almacenado para ``fila_id`` en ``tabla``, o None."""
        return self._hash_de(tabla, fila_id)

    def _verificar_tramo_ids(
        self,
        tabla: str,
        id_desde: int,
        id_hasta: int,
    ) -> int | None:
        """
        Verifica el encadenamiento del tramo ``[id_desde, id_hasta]``.

        Arranca con el hash previo de la fila anterior a ``id_desde`` (o GENESIS
        si ``id_desde`` es el primer registro de la tabla). Recorre por lotes de
        ``_LOTE`` filas dentro del rango. Devuelve el id del primer eslabón roto,
        o None si el tramo es íntegro.

        Usado por AuditoriaExportService para el veredicto de integridad del
        tramo exportado sin afectar el checkpoint de la verificación incremental.
        """
        payload_de, row_a_entidad = self._mapeadores(tabla)

        # El hash previo es el de la fila inmediatamente anterior a id_desde
        # (None si no existe, lo que equivale a GENESIS para la primera fila).
        with self._get_conn() as conn:
            row_prev = conn.execute(
                f"SELECT hash_cadena FROM {tabla} WHERE id < ? ORDER BY id DESC LIMIT 1",
                (id_desde,),
            ).fetchone()
        hash_previo: str | None = row_prev[0] if row_prev is not None else None

        cursor_id = id_desde - 1
        with self._get_conn() as conn:
            while True:
                rows = conn.execute(
                    f"SELECT * FROM {tabla}"
                    f" WHERE hash_cadena IS NOT NULL AND id >= ? AND id <= ? AND id > ?"
                    f" ORDER BY id ASC LIMIT ?",
                    (id_desde, id_hasta, cursor_id, _LOTE),
                ).fetchall()
                if not rows:
                    break
                for r in rows:
                    esperado = calcular_hash(hash_previo, payload_de(row_a_entidad(r)))
                    if esperado != r["hash_cadena"]:
                        return int(r["id"])
                    hash_previo = r["hash_cadena"]
                cursor_id = int(rows[-1]["id"])
                if cursor_id >= id_hasta:
                    break
        return None


__all__ = ["SqliteAuditoriaRepository"]
