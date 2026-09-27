"""
SqlaAuditoriaRepository — implementación SQLAlchemy Core de IAuditoriaRepository.

Decisiones de migración:
- Cadena SHA-256: _ultimo_hash / registrar_evento / registrar_cambio mantienen
  la misma lógica; solo reemplaza la API de cursor por SQLAlchemy Core.
- _verificar_cadena y _verificar_tramo_ids: se conserva la iteración Python
  por lotes (_LOTE filas) — es más portable y se mantiene igual que en SQLite.
- _where_eventos / _where_cambios: refactorizados de (sql_str, params) a
  listas de Column expressions para uso con .where(*filters).
- resumen_eventos / uso_diario: SUM(tipo=X) → func.sum(case(...)) portable.
- contar_fallos_recientes: func.datetime() SQLite para aritmética de fechas.
- _guardar_checkpoint: usa _upsert() sobre verificacion_auditoria.
- verificacion_auditoria tiene TEXT PK "tabla" — el upsert usa conflict_cols=["tabla"].
- Tenant scope en auditoria/audit_log: institucion_id opcional (no obligatorio
  en todos los registros). Los filtros de scope se aplican solo cuando
  scope != "*" y scope is not None.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime as _dt

from sqlalchemy import Table, case, func, select

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
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import audit_log, auditoria, verificacion_auditoria

_LOTE = 5_000

_COLUMNAS_NO_DOMINIO = frozenset({"hash_cadena"})


class SqlaAuditoriaRepository(RepositorioBase, IAuditoriaRepository):
    def __init__(self, conn=None):
        super().__init__(conn, None)

    # ------------------------------------------------------------------
    # Helper: tabla dinámica por nombre
    # ------------------------------------------------------------------

    @staticmethod
    def _tabla_de(nombre: str) -> Table:
        if nombre == "auditoria":
            return auditoria
        return audit_log

    # ------------------------------------------------------------------
    # Row mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_evento(row) -> EventoSesion:
        d = {k: v for k, v in dict(row).items() if k not in _COLUMNAS_NO_DOMINIO}
        d["tipo_evento"] = TipoEventoSesion(d["tipo_evento"])
        if "severidad" in d and d["severidad"] is not None:
            d["severidad"] = SeveridadEvento(d["severidad"])
        return EventoSesion(**d)

    @staticmethod
    def _row_to_cambio(row) -> RegistroCambio:
        d = {k: v for k, v in dict(row).items() if k not in _COLUMNAS_NO_DOMINIO}
        d["accion"] = AccionCambio(d["accion"])
        return RegistroCambio(**d)

    # ------------------------------------------------------------------
    # Encadenamiento por hash — helpers internos
    # ------------------------------------------------------------------

    def _ultimo_hash(self, conn, tabla: str) -> str | None:
        """Último hash_cadena de `tabla` (None si vacía)."""
        t = self._tabla_de(tabla)
        row = conn.execute(
            select(t.c.hash_cadena).order_by(t.c.id.desc()).limit(1)
        ).fetchone()
        return row[0] if row is not None else None

    @staticmethod
    def _payload_evento(evento: EventoSesion) -> dict:
        return {
            "usuario": evento.usuario,
            "usuario_id": evento.usuario_id,
            "tipo_evento": evento.tipo_evento.value,
            "ip_address": evento.ip_address,
            "fecha_hora": evento.fecha_hora.isoformat(),
            "detalles": evento.detalles,
            "objetivo": evento.objetivo,
        }

    @staticmethod
    def _payload_cambio(registro: RegistroCambio) -> dict:
        return {
            "usuario": registro.usuario,
            "usuario_id": registro.usuario_id,
            "ip_address": registro.ip_address,
            "accion": registro.accion.value,
            "tabla": registro.tabla,
            "registro_id": registro.registro_id,
            "valor_anterior": registro.valor_anterior,
            "valor_nuevo": registro.valor_nuevo,
            "timestamp": registro.timestamp.isoformat(),
        }

    def _mapeadores(self, tabla: str):
        if tabla == "auditoria":
            return self._payload_evento, self._row_to_evento
        return self._payload_cambio, self._row_to_cambio

    def _hash_de(self, tabla: str, fila_id: int) -> str | None:
        t = self._tabla_de(tabla)
        with self._get_conn() as conn:
            row = conn.execute(
                select(t.c.hash_cadena).where(t.c.id == fila_id)
            ).fetchone()
        return row[0] if row is not None else None

    def _guardar_checkpoint(self, tabla: str, ultimo_id: int, ultimo_hash: str) -> None:
        stmt = self._upsert(
            verificacion_auditoria,
            {
                "tabla": tabla,
                "ultimo_id": ultimo_id,
                "ultimo_hash": ultimo_hash,
                "verificado_en": _ahora(),
            },
            ["tabla"],
            ["ultimo_id", "ultimo_hash", "verificado_en"],
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()

    def _leer_checkpoint(self, tabla: str) -> tuple[int | None, str | None]:
        stmt = select(
            verificacion_auditoria.c.ultimo_id,
            verificacion_auditoria.c.ultimo_hash,
        ).where(verificacion_auditoria.c.tabla == tabla)
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
        if row is None:
            return None, None
        return int(row[0]), row[1]

    def _verificar_cadena(
        self, tabla: str, *, desde_id: int | None = None, guardar: bool = True
    ) -> int | None:
        t = self._tabla_de(tabla)
        payload_de, row_a_entidad = self._mapeadores(tabla)
        hash_previo = None if desde_id is None else self._hash_de(tabla, desde_id)
        ultimo_id: int | None = desde_id
        ultimo_hash: str | None = hash_previo
        cursor_id = desde_id or 0

        with self._get_conn() as conn:
            while True:
                stmt = (
                    select(t)
                    .where(
                        t.c.hash_cadena.isnot(None),
                        t.c.id > cursor_id,
                    )
                    .order_by(t.c.id.asc())
                    .limit(_LOTE)
                )
                rows = conn.execute(stmt).mappings().all()
                if not rows:
                    break
                for r in rows:
                    esperado = calcular_hash(hash_previo, payload_de(row_a_entidad(r)))
                    if esperado != r["hash_cadena"]:
                        return int(r["id"])
                    hash_previo = r["hash_cadena"]
                    ultimo_id = int(r["id"])
                    ultimo_hash = r["hash_cadena"]
                cursor_id = ultimo_id or 0

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
            stmt = auditoria.insert().values(
                usuario=evento.usuario,
                usuario_id=evento.usuario_id,
                tipo_evento=evento.tipo_evento.value,
                ip_address=evento.ip_address,
                fecha_hora=evento.fecha_hora,
                detalles=evento.detalles,
                objetivo=evento.objetivo,
                severidad=evento.severidad.value,
                hash_cadena=hash_cadena,
                institucion_id=evento.institucion_id,
            )
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
            return evento.model_copy(update={"id": pk})

    # ------------------------------------------------------------------
    # EventoSesion — lectura
    # ------------------------------------------------------------------

    @staticmethod
    def _where_eventos(filtro: FiltroAuditoriaDTO) -> list:
        """Construye lista de filtros SQLAlchemy para la tabla `auditoria`."""
        f: list = []
        if filtro.usuario_id is not None:
            f.append(auditoria.c.usuario_id == filtro.usuario_id)
        if filtro.tipo_evento is not None:
            f.append(auditoria.c.tipo_evento == filtro.tipo_evento.value)
        if filtro.desde is not None:
            f.append(auditoria.c.fecha_hora >= filtro.desde.isoformat())
        if filtro.hasta is not None:
            f.append(auditoria.c.fecha_hora <= filtro.hasta.isoformat())
        if filtro.sin_institucion:
            f.append(auditoria.c.institucion_id.is_(None))
        elif filtro.institucion_id is not None:
            f.append(auditoria.c.institucion_id == filtro.institucion_id)
        if filtro.severidad is not None:
            f.append(auditoria.c.severidad == filtro.severidad.value)
        return f

    def listar_eventos(self, filtro: FiltroAuditoriaDTO) -> list[EventoSesion]:
        filters = self._where_eventos(filtro)
        offset = (filtro.pagina - 1) * filtro.por_pagina
        stmt = (
            select(auditoria)
            .where(*filters)
            .order_by(auditoria.c.fecha_hora.desc())
            .limit(filtro.por_pagina)
            .offset(offset)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_evento(r) for r in rows]

    def contar_eventos(self, filtro: FiltroAuditoriaDTO) -> int:
        filters = self._where_eventos(filtro)
        stmt = select(func.count()).select_from(auditoria).where(*filters)
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    def get_ultimo_login(self, usuario_id: int) -> EventoSesion | None:
        stmt = (
            select(auditoria)
            .where(
                auditoria.c.usuario_id == usuario_id,
                auditoria.c.tipo_evento == "LOGIN_EXITOSO",
            )
            .order_by(auditoria.c.fecha_hora.desc())
            .limit(1)
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_evento(row) if row else None

    def contar_fallos_recientes(
        self,
        usuario: str,
        ventana_minutos: int = 30,
    ) -> int:
        ventana_expr = func.datetime("now", "localtime", f"-{ventana_minutos} minutes")
        stmt = (
            select(func.count())
            .select_from(auditoria)
            .where(
                func.lower(auditoria.c.usuario) == func.lower(usuario),
                auditoria.c.tipo_evento == "LOGIN_FALLIDO",
                auditoria.c.fecha_hora >= ventana_expr,
            )
        )
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    # ------------------------------------------------------------------
    # RegistroCambio — escritura
    # ------------------------------------------------------------------

    def registrar_cambio(self, registro: RegistroCambio) -> RegistroCambio:
        with self._get_conn() as conn:
            payload = self._payload_cambio(registro)
            hash_cadena = calcular_hash(self._ultimo_hash(conn, "audit_log"), payload)
            stmt = audit_log.insert().values(
                usuario_id=registro.usuario_id,
                usuario=registro.usuario,
                ip_address=registro.ip_address,
                accion=registro.accion.value,
                tabla=registro.tabla,
                registro_id=registro.registro_id,
                valor_anterior=registro.valor_anterior,
                valor_nuevo=registro.valor_nuevo,
                timestamp=registro.timestamp,
                hash_cadena=hash_cadena,
                institucion_id=registro.institucion_id,
            )
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
            return registro.model_copy(update={"id": pk})

    def registrar_cambios_masivos(self, registros: list[RegistroCambio]) -> int:
        if not registros:
            return 0
        with self._get_conn() as conn:
            # Hashes secuenciales: cada registro encadena con el anterior del lote.
            hash_previo = self._ultimo_hash(conn, "audit_log")
            params: list[dict] = []
            for r in registros:
                hash_cadena = calcular_hash(hash_previo, self._payload_cambio(r))
                params.append({
                    "usuario_id": r.usuario_id,
                    "usuario": r.usuario,
                    "ip_address": r.ip_address,
                    "accion": r.accion.value,
                    "tabla": r.tabla,
                    "registro_id": r.registro_id,
                    "valor_anterior": r.valor_anterior,
                    "valor_nuevo": r.valor_nuevo,
                    "timestamp": r.timestamp,
                    "hash_cadena": hash_cadena,
                    "institucion_id": r.institucion_id,
                })
                hash_previo = hash_cadena
            conn.execute(audit_log.insert(), params)
            if self._conn is None:
                conn.commit()
            return len(registros)

    # ------------------------------------------------------------------
    # Verificación de integridad
    # ------------------------------------------------------------------

    def verificar_cadena_eventos(self, *, completa: bool = False) -> int | None:
        if completa:
            return self._verificar_cadena("auditoria", desde_id=None, guardar=True)
        desde_id, _ = self._leer_checkpoint("auditoria")
        if desde_id is None:
            return self._verificar_cadena("auditoria", desde_id=None, guardar=False)
        return self._verificar_cadena("auditoria", desde_id=desde_id, guardar=True)

    def verificar_cadena_cambios(self, *, completa: bool = False) -> int | None:
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
    def _where_cambios(filtro: FiltroAuditoriaDTO) -> list:
        """Construye lista de filtros SQLAlchemy para la tabla `audit_log`."""
        f: list = []
        if filtro.usuario_id is not None:
            f.append(audit_log.c.usuario_id == filtro.usuario_id)
        if filtro.tabla is not None:
            f.append(audit_log.c.tabla == filtro.tabla)
        if filtro.accion is not None:
            f.append(audit_log.c.accion == filtro.accion.value)
        if filtro.desde is not None:
            f.append(audit_log.c.timestamp >= filtro.desde.isoformat())
        if filtro.hasta is not None:
            f.append(audit_log.c.timestamp <= filtro.hasta.isoformat())
        if filtro.registro_id is not None:
            f.append(audit_log.c.registro_id == filtro.registro_id)
        if filtro.sin_institucion:
            f.append(audit_log.c.institucion_id.is_(None))
        elif filtro.institucion_id is not None:
            f.append(audit_log.c.institucion_id == filtro.institucion_id)
        return f

    def listar_cambios(self, filtro: FiltroAuditoriaDTO) -> list[RegistroCambio]:
        filters = self._where_cambios(filtro)
        offset = (filtro.pagina - 1) * filtro.por_pagina
        stmt = (
            select(audit_log)
            .where(*filters)
            .order_by(audit_log.c.timestamp.desc())
            .limit(filtro.por_pagina)
            .offset(offset)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_cambio(r) for r in rows]

    def contar_cambios(self, filtro: FiltroAuditoriaDTO) -> int:
        filters = self._where_cambios(filtro)
        stmt = select(func.count()).select_from(audit_log).where(*filters)
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    def resumen_eventos(
        self,
        desde,
        hasta=None,
        institucion_id="*",
    ) -> dict:
        desde_iso = desde.isoformat() if hasattr(desde, "isoformat") else str(desde)
        hasta_iso = hasta.isoformat() if hasta is not None and hasattr(hasta, "isoformat") else None
        ahora_now = _ahora()
        inicio_hoy_iso = _dt(ahora_now.year, ahora_now.month, ahora_now.day).isoformat()

        # Filtros comunes de scope e institución
        base_filters: list = [auditoria.c.fecha_hora >= desde_iso]
        if hasta_iso is not None:
            base_filters.append(auditoria.c.fecha_hora <= hasta_iso)
        if institucion_id not in ("*", None):
            base_filters.append(auditoria.c.institucion_id == institucion_id)

        inst_today: list = [auditoria.c.fecha_hora >= inicio_hoy_iso]
        if institucion_id not in ("*", None):
            inst_today.append(auditoria.c.institucion_id == institucion_id)

        with self._get_conn() as conn:
            # 1. Conteo por tipo en la ventana
            rows_tipo = conn.execute(
                select(auditoria.c.tipo_evento, func.count().label("n"))
                .where(*base_filters)
                .group_by(auditoria.c.tipo_evento)
            ).fetchall()
            por_tipo: dict[str, int] = {r[0]: int(r[1]) for r in rows_tipo}

            # 2. Logins de hoy
            logins_hoy = int(conn.execute(
                select(func.count())
                .select_from(auditoria)
                .where(
                    auditoria.c.tipo_evento == "LOGIN_EXITOSO",
                    *inst_today,
                )
            ).scalar() or 0)

            # 3. Usuarios distintos con login en la ventana
            usuarios_distintos = int(conn.execute(
                select(func.count(func.coalesce(auditoria.c.usuario_id, auditoria.c.usuario).distinct()))
                .select_from(auditoria)
                .where(
                    auditoria.c.tipo_evento == "LOGIN_EXITOSO",
                    *base_filters,
                )
            ).scalar() or 0)

            # 4. Denegaciones críticas en la ventana
            denegados_criticos = int(conn.execute(
                select(func.count())
                .select_from(auditoria)
                .where(
                    auditoria.c.tipo_evento == "ACCESO_DENEGADO",
                    auditoria.c.severidad == "CRITICA",
                    *base_filters,
                )
            ).scalar() or 0)

        return {
            "por_tipo": por_tipo,
            "logins_hoy": logins_hoy,
            "usuarios_distintos": usuarios_distintos,
            "denegados_criticos": denegados_criticos,
        }

    def uso_diario(self, dias: int = 14) -> list[dict]:
        from datetime import timedelta as _td

        dias = max(1, dias)
        ahora_now = _ahora()
        desde = ahora_now - _td(days=dias)
        desde_iso = _dt(desde.year, desde.month, desde.day).isoformat()

        fecha_col = func.date(auditoria.c.fecha_hora).label("fecha")
        stmt = (
            select(
                fecha_col,
                func.sum(
                    case((auditoria.c.tipo_evento == "LOGIN_EXITOSO", 1), else_=0)
                ).label("logins"),
                func.sum(
                    case((auditoria.c.tipo_evento == "ACCESO_DENEGADO", 1), else_=0)
                ).label("denegados"),
            )
            .where(auditoria.c.fecha_hora >= desde_iso)
            .group_by(fecha_col)
            .order_by(fecha_col)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()

        por_fecha: dict[str, dict] = {}
        for r in rows:
            por_fecha[r["fecha"]] = {
                "fecha": r["fecha"],
                "logins": int(r["logins"] or 0),
                "denegados": int(r["denegados"] or 0),
            }

        resultado: list[dict] = []
        for i in range(dias):
            dia = desde + _td(days=i + 1)
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
        stmt = (
            select(audit_log)
            .where(
                audit_log.c.tabla == tabla,
                audit_log.c.registro_id == registro_id,
            )
            .order_by(audit_log.c.timestamp.asc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_cambio(r) for r in rows]

    def get_cambio(self, cambio_id: int) -> RegistroCambio | None:
        stmt = select(audit_log).where(audit_log.c.id == cambio_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_cambio(row) if row else None

    # ------------------------------------------------------------------
    # Tramo y retención
    # ------------------------------------------------------------------

    def rango_de(
        self,
        tabla: str,
        filtro: FiltroAuditoriaDTO,
    ) -> tuple[int, int] | None:
        t = self._tabla_de(tabla)
        if tabla == "auditoria":
            filters = self._where_eventos(filtro)
        else:
            filters = self._where_cambios(filtro)
        stmt = select(func.min(t.c.id), func.max(t.c.id)).where(*filters)
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
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
        t = self._tabla_de(tabla)
        row_fn = self._row_to_evento if tabla == "auditoria" else self._row_to_cambio

        scope_filters: list = []
        if scope != "*" and scope is not None:
            scope_filters.append(t.c.institucion_id == scope)

        cursor_id = id_desde - 1
        with self._get_conn() as conn:
            while True:
                stmt = (
                    select(t)
                    .where(
                        t.c.id >= id_desde,
                        t.c.id <= id_hasta,
                        t.c.id > cursor_id,
                        *scope_filters,
                    )
                    .order_by(t.c.id.asc())
                    .limit(lote)
                )
                rows = conn.execute(stmt).mappings().all()
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
        t = self._tabla_de(tabla)
        stmt = t.delete().where(t.c.id <= id_hasta)
        if scope != "*" and scope is not None:
            stmt = stmt.where(t.c.institucion_id == scope)
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount

    def hash_de_fila(self, tabla: str, fila_id: int) -> str | None:
        return self._hash_de(tabla, fila_id)

    def _verificar_tramo_ids(
        self,
        tabla: str,
        id_desde: int,
        id_hasta: int,
    ) -> int | None:
        t = self._tabla_de(tabla)
        payload_de, row_a_entidad = self._mapeadores(tabla)

        # Hash previo: el de la fila inmediatamente anterior a id_desde
        with self._get_conn() as conn:
            row_prev = conn.execute(
                select(t.c.hash_cadena)
                .where(t.c.id < id_desde)
                .order_by(t.c.id.desc())
                .limit(1)
            ).fetchone()
        hash_previo: str | None = row_prev[0] if row_prev is not None else None

        cursor_id = id_desde - 1
        with self._get_conn() as conn:
            while True:
                stmt = (
                    select(t)
                    .where(
                        t.c.hash_cadena.isnot(None),
                        t.c.id >= id_desde,
                        t.c.id <= id_hasta,
                        t.c.id > cursor_id,
                    )
                    .order_by(t.c.id.asc())
                    .limit(_LOTE)
                )
                rows = conn.execute(stmt).mappings().all()
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


__all__ = ["SqlaAuditoriaRepository"]
