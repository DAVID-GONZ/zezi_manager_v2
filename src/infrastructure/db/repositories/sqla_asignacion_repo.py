"""Implementación SQLAlchemy Core de IAsignacionRepository — ZECI Manager v2.0."""
from __future__ import annotations

from sqlalchemy import insert, select, update

from src.domain.models.asignacion import (
    Asignacion,
    AsignacionInfo,
    FiltroAsignacionesDTO,
)
from src.domain.models.tenant import TenantScope
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import asignaciones, asignaturas, grupos, periodos, usuarios


class SqlaAsignacionRepository(RepositorioBase, IAsignacionRepository):
    def __init__(self, conn=None):
        super().__init__(conn, asignaciones)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _row_to_asignacion(self, row) -> Asignacion:
        d = dict(row)
        d["activo"] = bool(d["activo"])
        return Asignacion(**d)

    def _row_to_info(self, row) -> AsignacionInfo:
        d = dict(row)
        d["activo"] = bool(d["activo"])
        return AsignacionInfo(**d)

    def _build_info_stmt(self):
        """SELECT enriquecido con JOINs para el read model AsignacionInfo."""
        return (
            select(
                asignaciones.c.id.label("asignacion_id"),
                asignaciones.c.grupo_id,
                grupos.c.codigo.label("grupo_codigo"),
                asignaciones.c.asignatura_id,
                asignaturas.c.nombre.label("asignatura_nombre"),
                asignaciones.c.usuario_id,
                usuarios.c.nombre_completo.label("docente_nombre"),
                asignaciones.c.periodo_id,
                periodos.c.nombre.label("periodo_nombre"),
                periodos.c.numero.label("periodo_numero"),
                asignaciones.c.activo,
            )
            .join(grupos, grupos.c.id == asignaciones.c.grupo_id)
            .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
            .join(usuarios, usuarios.c.id == asignaciones.c.usuario_id)
            .join(periodos, periodos.c.id == asignaciones.c.periodo_id)
        )

    # ------------------------------------------------------------------
    # Lectura — entidad de persistencia
    # ------------------------------------------------------------------

    def get_by_id(self, asignacion_id: int) -> Asignacion | None:
        stmt = self._select().where(asignaciones.c.id == asignacion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_asignacion(row) if row else None

    def listar(self, filtro: FiltroAsignacionesDTO) -> list[Asignacion]:
        stmt = self._select()
        if filtro.solo_activas:
            stmt = stmt.where(asignaciones.c.activo == True)  # noqa: E712
        if filtro.usuario_id is not None:
            stmt = stmt.where(asignaciones.c.usuario_id == filtro.usuario_id)
        if filtro.grupo_id is not None:
            stmt = stmt.where(asignaciones.c.grupo_id == filtro.grupo_id)
        if filtro.asignatura_id is not None:
            stmt = stmt.where(asignaciones.c.asignatura_id == filtro.asignatura_id)
        if filtro.periodo_id is not None:
            stmt = stmt.where(asignaciones.c.periodo_id == filtro.periodo_id)
        if filtro.institucion_id is not None:
            # Scope multi-tenant: filtrar por institución del grupo vía subquery.
            # asignaciones no tiene institucion_id; se hereda transitivamente del grupo.
            sub = select(grupos.c.id).where(grupos.c.institucion_id == filtro.institucion_id)
            stmt = stmt.where(asignaciones.c.grupo_id.in_(sub))
        stmt = stmt.order_by(asignaciones.c.id)
        offset = (filtro.pagina - 1) * filtro.por_pagina
        stmt = stmt.limit(filtro.por_pagina).offset(offset)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_asignacion(r) for r in rows]

    def existe(
        self,
        grupo_id: int,
        asignatura_id: int,
        usuario_id: int,
        periodo_id: int,
    ) -> bool:
        stmt = select(asignaciones.c.id).where(
            asignaciones.c.grupo_id == grupo_id,
            asignaciones.c.asignatura_id == asignatura_id,
            asignaciones.c.usuario_id == usuario_id,
            asignaciones.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row is not None

    # ------------------------------------------------------------------
    # Lectura — read model con JOINs
    # ------------------------------------------------------------------

    def get_info(self, asignacion_id: int) -> AsignacionInfo | None:
        stmt = self._build_info_stmt().where(asignaciones.c.id == asignacion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_info(row) if row else None

    def listar_info(self, filtro: FiltroAsignacionesDTO) -> list[AsignacionInfo]:
        stmt = self._build_info_stmt()
        if filtro.solo_activas:
            stmt = stmt.where(asignaciones.c.activo == True)  # noqa: E712
        if filtro.usuario_id is not None:
            stmt = stmt.where(asignaciones.c.usuario_id == filtro.usuario_id)
        if filtro.grupo_id is not None:
            stmt = stmt.where(asignaciones.c.grupo_id == filtro.grupo_id)
        if filtro.asignatura_id is not None:
            stmt = stmt.where(asignaciones.c.asignatura_id == filtro.asignatura_id)
        if filtro.periodo_id is not None:
            stmt = stmt.where(asignaciones.c.periodo_id == filtro.periodo_id)
        if filtro.institucion_id is not None:
            # El JOIN a grupos ya está; filtra por la institución del grupo.
            stmt = stmt.where(grupos.c.institucion_id == filtro.institucion_id)
        stmt = stmt.order_by(grupos.c.codigo, asignaturas.c.nombre)
        offset = (filtro.pagina - 1) * filtro.por_pagina
        stmt = stmt.limit(filtro.por_pagina).offset(offset)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_info(r) for r in rows]

    def listar_por_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        institucion_id: TenantScope,
        solo_activas: bool = True,
    ) -> list[AsignacionInfo]:
        stmt = self._build_info_stmt().where(
            asignaciones.c.grupo_id == grupo_id,
            asignaciones.c.periodo_id == periodo_id,
        )
        if solo_activas:
            stmt = stmt.where(asignaciones.c.activo == True)  # noqa: E712
        # TenantScope: int → defensa en profundidad; "*" → cross-tenant (admin).
        if isinstance(institucion_id, int):
            stmt = stmt.where(grupos.c.institucion_id == institucion_id)
        stmt = stmt.order_by(asignaturas.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_info(r) for r in rows]

    def listar_por_docente(
        self,
        usuario_id: int,
        institucion_id: TenantScope,
        periodo_id: int | None = None,
        solo_activas: bool = True,
    ) -> list[AsignacionInfo]:
        stmt = self._build_info_stmt().where(asignaciones.c.usuario_id == usuario_id)
        if periodo_id is not None:
            stmt = stmt.where(asignaciones.c.periodo_id == periodo_id)
        if solo_activas:
            stmt = stmt.where(asignaciones.c.activo == True)  # noqa: E712
        # TenantScope: int → restringe a institución del grupo; "*" → admin.
        if isinstance(institucion_id, int):
            stmt = stmt.where(grupos.c.institucion_id == institucion_id)
        stmt = stmt.order_by(grupos.c.codigo, asignaturas.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_info(r) for r in rows]

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def guardar(self, asignacion: Asignacion) -> Asignacion:
        stmt = insert(asignaciones).values(
            grupo_id=asignacion.grupo_id,
            asignatura_id=asignacion.asignatura_id,
            usuario_id=asignacion.usuario_id,
            periodo_id=asignacion.periodo_id,
            activo=int(asignacion.activo),
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return asignacion.model_copy(update={"id": pk})

    def desactivar(self, asignacion_id: int) -> bool:
        stmt = (
            update(asignaciones)
            .where(asignaciones.c.id == asignacion_id)
            .values(activo=False)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def reactivar(self, asignacion_id: int) -> bool:
        stmt = (
            update(asignaciones)
            .where(asignaciones.c.id == asignacion_id)
            .values(activo=True)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def reasignar_docente(self, asignacion_id: int, nuevo_usuario_id: int) -> bool:
        stmt = (
            update(asignaciones)
            .where(asignaciones.c.id == asignacion_id)
            .values(usuario_id=nuevo_usuario_id)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0


__all__ = ["SqlaAsignacionRepository"]
