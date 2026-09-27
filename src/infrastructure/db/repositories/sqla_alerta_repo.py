"""Implementación SQLAlchemy Core de IAlertaRepository — ZECI Manager v2.0."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, insert, select, update

from src.domain.models.alerta import (
    Alerta,
    ConfiguracionAlerta,
    FiltroAlertasDTO,
    NivelAlerta,
    TipoAlerta,
)
from src.domain.models.clock import ahora
from src.domain.models.tenant import TenantScope
from src.domain.ports.alerta_repo import IAlertaRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import alertas, configuracion_alertas, estudiantes


class SqlaAlertaRepository(RepositorioBase, IAlertaRepository):
    def __init__(self, conn=None):
        super().__init__(conn, alertas)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_config(self, row) -> ConfiguracionAlerta:
        d = dict(row)
        d["tipo_alerta"] = TipoAlerta(d["tipo_alerta"])
        d["activa"] = bool(d["activa"])
        d["notificar_docente"] = bool(d["notificar_docente"])
        d["notificar_director"] = bool(d["notificar_director"])
        d["notificar_acudiente"] = bool(d["notificar_acudiente"])
        return ConfiguracionAlerta(**d)

    def _row_to_alerta(self, row) -> Alerta:
        d = dict(row)
        d["tipo_alerta"] = TipoAlerta(d["tipo_alerta"])
        d["nivel"] = NivelAlerta(d["nivel"])
        d["resuelta"] = bool(d["resuelta"])
        d.setdefault("usuario_destino_id", None)
        return Alerta(**d)

    # ------------------------------------------------------------------
    # Configuración de alertas
    # ------------------------------------------------------------------

    def get_configuracion(
        self,
        anio_id: int,
        tipo_alerta: TipoAlerta,
    ) -> ConfiguracionAlerta | None:
        stmt = select(configuracion_alertas).where(
            configuracion_alertas.c.anio_id == anio_id,
            configuracion_alertas.c.tipo_alerta == tipo_alerta.value,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_config(row) if row else None

    def listar_configuraciones(
        self,
        anio_id: int,
        solo_activas: bool = True,
    ) -> list[ConfiguracionAlerta]:
        stmt = select(configuracion_alertas).where(
            configuracion_alertas.c.anio_id == anio_id,
        )
        if solo_activas:
            stmt = stmt.where(configuracion_alertas.c.activa == True)  # noqa: E712
        stmt = stmt.order_by(configuracion_alertas.c.tipo_alerta)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_config(r) for r in rows]

    def guardar_configuracion(
        self,
        config: ConfiguracionAlerta,
    ) -> ConfiguracionAlerta:
        stmt = self._upsert(
            configuracion_alertas,
            values={
                "anio_id": config.anio_id,
                "tipo_alerta": config.tipo_alerta.value,
                "umbral": config.umbral,
                "activa": int(config.activa),
                "notificar_docente": int(config.notificar_docente),
                "notificar_director": int(config.notificar_director),
                "notificar_acudiente": int(config.notificar_acudiente),
            },
            conflict_cols=["anio_id", "tipo_alerta"],
            update_cols=["umbral", "activa", "notificar_docente", "notificar_director", "notificar_acudiente"],
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return config.model_copy(update={"id": result.inserted_primary_key[0]})

    def desactivar_configuracion(
        self,
        anio_id: int,
        tipo_alerta: TipoAlerta,
    ) -> bool:
        stmt = (
            update(configuracion_alertas)
            .where(
                configuracion_alertas.c.anio_id == anio_id,
                configuracion_alertas.c.tipo_alerta == tipo_alerta.value,
            )
            .values(activa=False)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Lectura — alertas
    # ------------------------------------------------------------------

    def get_alerta(self, alerta_id: int) -> Alerta | None:
        stmt = select(alertas).where(alertas.c.id == alerta_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_alerta(row) if row else None

    def listar_alertas(self, filtro: FiltroAlertasDTO) -> list[Alerta]:
        stmt = select(alertas)
        if filtro.solo_pendientes:
            stmt = stmt.where(alertas.c.resuelta == False)  # noqa: E712
        if filtro.institucion_id != "*":
            sub = select(estudiantes.c.id).where(
                estudiantes.c.institucion_id == filtro.institucion_id
            )
            stmt = stmt.where(alertas.c.estudiante_id.in_(sub))
        if filtro.estudiante_id is not None:
            stmt = stmt.where(alertas.c.estudiante_id == filtro.estudiante_id)
        if filtro.tipo_alerta is not None:
            stmt = stmt.where(alertas.c.tipo_alerta == filtro.tipo_alerta.value)
        if filtro.nivel is not None:
            stmt = stmt.where(alertas.c.nivel == filtro.nivel.value)
        if filtro.usuario_destino_id is not None:
            stmt = stmt.where(alertas.c.usuario_destino_id == filtro.usuario_destino_id)
        # ORDER BY nivel (critica primero) luego fecha_generacion DESC
        nivel_order = case(
            (alertas.c.nivel == "critica", 0),
            (alertas.c.nivel == "advertencia", 1),
            else_=2,
        )
        stmt = stmt.order_by(nivel_order, alertas.c.fecha_generacion.desc())
        offset = (filtro.pagina - 1) * filtro.por_pagina
        stmt = stmt.limit(filtro.por_pagina).offset(offset)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_alerta(r) for r in rows]

    def contar_pendientes(
        self,
        institucion_id: TenantScope,
        estudiante_id: int | None = None,
        nivel: NivelAlerta | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(alertas).where(
            alertas.c.resuelta == False  # noqa: E712
        )
        if institucion_id != "*":
            sub = select(estudiantes.c.id).where(
                estudiantes.c.institucion_id == institucion_id
            )
            stmt = stmt.where(alertas.c.estudiante_id.in_(sub))
        if estudiante_id is not None:
            stmt = stmt.where(alertas.c.estudiante_id == estudiante_id)
        if nivel is not None:
            stmt = stmt.where(alertas.c.nivel == nivel.value)
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    def existe_pendiente(
        self,
        estudiante_id: int,
        tipo_alerta: TipoAlerta,
    ) -> bool:
        stmt = select(alertas.c.id).where(
            alertas.c.estudiante_id == estudiante_id,
            alertas.c.tipo_alerta == tipo_alerta.value,
            alertas.c.resuelta == False,  # noqa: E712
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row is not None

    # ------------------------------------------------------------------
    # Escritura — alertas
    # ------------------------------------------------------------------

    def guardar_alerta(self, alerta: Alerta) -> Alerta:
        stmt = insert(alertas).values(
            estudiante_id=alerta.estudiante_id,
            tipo_alerta=alerta.tipo_alerta.value,
            nivel=alerta.nivel.value,
            descripcion=alerta.descripcion,
            fecha_generacion=alerta.fecha_generacion,
            resuelta=int(alerta.resuelta),
            fecha_resolucion=alerta.fecha_resolucion,
            usuario_resolucion_id=alerta.usuario_resolucion_id,
            observacion_resolucion=alerta.observacion_resolucion,
            usuario_destino_id=alerta.usuario_destino_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return alerta.model_copy(update={"id": pk})

    def guardar_alertas_masivas(self, alertas_list: list[Alerta]) -> int:
        if not alertas_list:
            return 0
        rows = [
            {
                "estudiante_id": a.estudiante_id,
                "tipo_alerta": a.tipo_alerta.value,
                "nivel": a.nivel.value,
                "descripcion": a.descripcion,
                "fecha_generacion": a.fecha_generacion,
                "resuelta": int(a.resuelta),
                "fecha_resolucion": a.fecha_resolucion,
                "usuario_resolucion_id": a.usuario_resolucion_id,
                "observacion_resolucion": a.observacion_resolucion,
            }
            for a in alertas_list
        ]
        stmt = insert(alertas)
        with self._get_conn() as conn:
            conn.execute(stmt, rows)
            if self._conn is None:
                conn.commit()
        return len(alertas_list)

    def resolver_alerta(
        self,
        alerta_id: int,
        usuario_id: int,
        observacion: str | None = None,
        fecha: datetime | None = None,
    ) -> bool:
        ts = fecha or ahora()
        stmt = (
            update(alertas)
            .where(alertas.c.id == alerta_id, alertas.c.resuelta == False)  # noqa: E712
            .values(
                resuelta=True,
                fecha_resolucion=ts,
                usuario_resolucion_id=usuario_id,
                observacion_resolucion=observacion,
            )
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def listar_alertas_por_destinatario(
        self,
        usuario_destino_id: int,
        tipo: str | None = None,
        solo_pendientes: bool = True,
    ) -> list[Alerta]:
        stmt = select(alertas).where(alertas.c.usuario_destino_id == usuario_destino_id)
        if tipo is not None:
            stmt = stmt.where(alertas.c.tipo_alerta == tipo)
        if solo_pendientes:
            stmt = stmt.where(alertas.c.resuelta == False)  # noqa: E712
        stmt = stmt.order_by(alertas.c.fecha_generacion.desc())
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_alerta(r) for r in rows]

    def resolver_alertas_de_estudiante(
        self,
        estudiante_id: int,
        tipo_alerta: TipoAlerta,
        usuario_id: int,
        observacion: str | None = None,
    ) -> int:
        ts = ahora()
        stmt = (
            update(alertas)
            .where(
                alertas.c.estudiante_id == estudiante_id,
                alertas.c.tipo_alerta == tipo_alerta.value,
                alertas.c.resuelta == False,  # noqa: E712
            )
            .values(
                resuelta=True,
                fecha_resolucion=ts,
                usuario_resolucion_id=usuario_id,
                observacion_resolucion=observacion,
            )
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount


__all__ = ["SqlaAlertaRepository"]
