"""Implementación SQLAlchemy Core de IUsuarioRepository — AVEDRA v2.0."""
from __future__ import annotations

from sqlalchemy import and_, distinct, func, insert, select, update

from src.domain.models.tenant import TenantScope
from src.domain.models.usuario import (
    AsignacionDocenteInfoDTO,
    DocenteInfoDTO,
    FiltroUsuariosDTO,
    Rol,
    Usuario,
    UsuarioResumenDTO,
)
from src.domain.ports.usuario_repo import IUsuarioRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    asignaciones,
    asignaturas,
    grupos,
    horarios,
    periodos,
    usuarios,
)

# Columnas de usuario expuestas al dominio — excluye password_hash
_USUARIO_COLS = [
    usuarios.c.id,
    usuarios.c.usuario,
    usuarios.c.nombre_completo,
    usuarios.c.email,
    usuarios.c.telefono,
    usuarios.c.rol,
    usuarios.c.activo,
    usuarios.c.debe_cambiar_password,
    usuarios.c.fecha_creacion,
    usuarios.c.ultima_sesion,
    usuarios.c.carga_horaria_max,
    usuarios.c.horas_extra,
    usuarios.c.institucion_id,
]


class SqlaUsuarioRepository(RepositorioBase, IUsuarioRepository):
    def __init__(self, conn=None):
        super().__init__(conn, usuarios)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _row_to_usuario(self, row) -> Usuario:
        d = dict(row)
        d["rol"] = Rol(d["rol"])
        d["activo"] = bool(d["activo"])
        if "debe_cambiar_password" in d:
            d["debe_cambiar_password"] = bool(d["debe_cambiar_password"])
        return Usuario(**d)

    def _select_usuario(self):
        """SELECT de columnas de dominio (sin password_hash)."""
        return select(*_USUARIO_COLS)

    def _build_docente_info_stmt(self, periodo_id: int | None):
        """Construye el SELECT agregado base para DocenteInfoDTO."""
        asig_join_cond = and_(
            asignaciones.c.usuario_id == usuarios.c.id,
            asignaciones.c.activo == True,  # noqa: E712
        )
        if periodo_id is not None:
            asig_join_cond = and_(
                asig_join_cond, asignaciones.c.periodo_id == periodo_id
            )

        hor_join_cond = horarios.c.usuario_id == usuarios.c.id
        if periodo_id is not None:
            hor_join_cond = and_(
                hor_join_cond, horarios.c.periodo_id == periodo_id
            )

        return (
            select(
                usuarios.c.id,
                usuarios.c.usuario,
                usuarios.c.nombre_completo,
                usuarios.c.email,
                usuarios.c.telefono,
                usuarios.c.activo,
                usuarios.c.fecha_creacion,
                usuarios.c.ultima_sesion,
                func.count(distinct(asignaciones.c.id)).label("total_asignaciones"),
                func.count(distinct(asignaciones.c.grupo_id)).label("grupos_asignados"),
                func.count(distinct(asignaciones.c.asignatura_id)).label(
                    "asignaturas_asignadas"
                ),
                func.coalesce(
                    func.sum(distinct(asignaturas.c.horas_semanales)), 0
                ).label("horas_totales"),
                func.count(distinct(horarios.c.id)).label("bloques_horarios"),
            )
            .select_from(usuarios)
            .outerjoin(asignaciones, asig_join_cond)
            .outerjoin(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
            .outerjoin(horarios, hor_join_cond)
            .where(usuarios.c.rol == "profesor")
            .group_by(usuarios.c.id)
        )

    # ------------------------------------------------------------------
    # Lectura — usuarios
    # ------------------------------------------------------------------

    def get_by_id(self, usuario_id: int) -> Usuario | None:
        stmt = self._select_usuario().where(usuarios.c.id == usuario_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_usuario(row) if row else None

    def get_varios(self, ids: set[int]) -> list[Usuario]:
        if not ids:
            return []
        stmt = self._select_usuario().where(usuarios.c.id.in_(list(ids)))
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_usuario(r) for r in rows]

    def get_by_username(self, username: str) -> Usuario | None:
        stmt = self._select_usuario().where(
            func.lower(usuarios.c.usuario) == username.lower()
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_usuario(row) if row else None

    def get_by_email(self, email: str) -> Usuario | None:
        stmt = self._select_usuario().where(
            func.lower(usuarios.c.email) == email.lower()
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_usuario(row) if row else None

    def existe_usuario(self, username: str) -> bool:
        stmt = select(usuarios.c.id).where(
            func.lower(usuarios.c.usuario) == username.lower()
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row is not None

    def listar_filtrado(self, filtro: FiltroUsuariosDTO) -> list[Usuario]:
        stmt = self._select_usuario()
        if filtro.solo_activos:
            stmt = stmt.where(usuarios.c.activo == True)  # noqa: E712
        if filtro.rol is not None:
            stmt = stmt.where(usuarios.c.rol == filtro.rol.value)
        if filtro.busqueda:
            like = f"%{filtro.busqueda.lower()}%"
            stmt = stmt.where(
                func.lower(usuarios.c.nombre_completo).like(like)
                | func.lower(usuarios.c.usuario).like(like)
            )
        if filtro.institucion_id is not None:
            stmt = stmt.where(usuarios.c.institucion_id == filtro.institucion_id)
        stmt = stmt.order_by(usuarios.c.nombre_completo)
        offset = (filtro.pagina - 1) * filtro.por_pagina
        stmt = stmt.limit(filtro.por_pagina).offset(offset)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_usuario(r) for r in rows]

    def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]:
        stmt = select(
            usuarios.c.id,
            usuarios.c.usuario,
            usuarios.c.nombre_completo,
            usuarios.c.rol,
            usuarios.c.activo,
            usuarios.c.institucion_id,
        )
        if filtro.solo_activos:
            stmt = stmt.where(usuarios.c.activo == True)  # noqa: E712
        if filtro.rol is not None:
            stmt = stmt.where(usuarios.c.rol == filtro.rol.value)
        if filtro.busqueda:
            like = f"%{filtro.busqueda.lower()}%"
            stmt = stmt.where(
                func.lower(usuarios.c.nombre_completo).like(like)
                | func.lower(usuarios.c.usuario).like(like)
            )
        if filtro.institucion_id is not None:
            stmt = stmt.where(usuarios.c.institucion_id == filtro.institucion_id)
        stmt = stmt.order_by(usuarios.c.nombre_completo)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            result = []
            for r in rows:
                d = dict(r)
                d["rol"] = Rol(d["rol"])
                d["activo"] = bool(d["activo"])
                result.append(UsuarioResumenDTO(**d))
            return result

    # ------------------------------------------------------------------
    # Lectura — read models docentes
    # ------------------------------------------------------------------

    def listar_docentes_info(
        self,
        institucion_id: TenantScope,
        periodo_id: int | None = None,
        solo_activos: bool = True,
    ) -> list[DocenteInfoDTO]:
        stmt = self._build_docente_info_stmt(periodo_id)
        if solo_activos:
            stmt = stmt.where(usuarios.c.activo == True)  # noqa: E712
        if isinstance(institucion_id, int):
            stmt = stmt.where(usuarios.c.institucion_id == institucion_id)
        stmt = stmt.order_by(usuarios.c.nombre_completo)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            result = []
            for r in rows:
                d = dict(r)
                d["activo"] = bool(d["activo"])
                result.append(DocenteInfoDTO(**d))
            return result

    def get_docente_info(
        self,
        usuario_id: int,
        institucion_id: TenantScope,
        periodo_id: int | None = None,
    ) -> DocenteInfoDTO | None:
        stmt = self._build_docente_info_stmt(periodo_id).where(
            usuarios.c.id == usuario_id
        )
        if isinstance(institucion_id, int):
            stmt = stmt.where(usuarios.c.institucion_id == institucion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            if not row:
                return None
            d = dict(row)
            d["activo"] = bool(d["activo"])
            return DocenteInfoDTO(**d)

    def listar_asignaciones_docente(
        self,
        usuario_id: int,
        institucion_id: TenantScope,
        periodo_id: int | None = None,
    ) -> list[AsignacionDocenteInfoDTO]:
        stmt = (
            select(
                asignaciones.c.id,
                asignaciones.c.grupo_id,
                grupos.c.codigo.label("grupo_codigo"),
                grupos.c.nombre.label("grupo_nombre"),
                asignaciones.c.asignatura_id,
                asignaturas.c.nombre.label("asignatura_nombre"),
                asignaturas.c.codigo.label("asignatura_codigo"),
                asignaturas.c.horas_semanales.label("horas_teoricas"),
                func.count(horarios.c.id).label("horas_programadas"),
                asignaciones.c.periodo_id,
                periodos.c.nombre.label("periodo_nombre"),
                asignaciones.c.activo,
            )
            .select_from(asignaciones)
            .join(grupos, grupos.c.id == asignaciones.c.grupo_id)
            .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
            .join(periodos, periodos.c.id == asignaciones.c.periodo_id)
            .outerjoin(horarios, horarios.c.asignacion_id == asignaciones.c.id)
            .where(asignaciones.c.usuario_id == usuario_id)
        )
        if isinstance(institucion_id, int):
            stmt = stmt.where(grupos.c.institucion_id == institucion_id)
        if periodo_id is not None:
            stmt = stmt.where(asignaciones.c.periodo_id == periodo_id)
        stmt = (
            stmt
            .group_by(asignaciones.c.id)
            .order_by(grupos.c.codigo, asignaturas.c.nombre)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            result = []
            for r in rows:
                d = dict(r)
                d["activo"] = bool(d["activo"])
                result.append(AsignacionDocenteInfoDTO(**d))
            return result

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def guardar(self, usuario: Usuario) -> Usuario:
        stmt = insert(usuarios).values(
            usuario=usuario.usuario,
            password_hash="",  # placeholder — IAuthenticationService lo actualiza
            nombre_completo=usuario.nombre_completo,
            email=usuario.email,
            telefono=usuario.telefono,
            rol=usuario.rol.value,
            activo=int(usuario.activo),
            debe_cambiar_password=int(usuario.debe_cambiar_password),
            fecha_creacion=usuario.fecha_creacion,
            institucion_id=usuario.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return usuario.model_copy(update={"id": pk})

    def actualizar(self, usuario: Usuario) -> Usuario:
        stmt = (
            update(usuarios)
            .where(usuarios.c.id == usuario.id)
            .values(
                nombre_completo=usuario.nombre_completo,
                email=usuario.email,
                telefono=usuario.telefono,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return usuario

    def actualizar_carga(
        self, usuario_id: int, carga_horaria_max: int | None, horas_extra: int
    ) -> bool:
        stmt = (
            update(usuarios)
            .where(usuarios.c.id == usuario_id)
            .values(carga_horaria_max=carga_horaria_max, horas_extra=horas_extra)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def cambiar_rol(self, usuario_id: int, nuevo_rol: Rol) -> bool:
        stmt = (
            update(usuarios)
            .where(usuarios.c.id == usuario_id)
            .values(rol=nuevo_rol.value)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def desactivar(self, usuario_id: int) -> bool:
        stmt = (
            update(usuarios)
            .where(usuarios.c.id == usuario_id)
            .values(activo=False)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def reactivar(self, usuario_id: int) -> bool:
        stmt = (
            update(usuarios)
            .where(usuarios.c.id == usuario_id)
            .values(activo=True)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def marcar_debe_cambiar_password(self, usuario_id: int, valor: bool) -> bool:
        stmt = (
            update(usuarios)
            .where(usuarios.c.id == usuario_id)
            .values(debe_cambiar_password=int(valor))
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Credenciales — uso exclusivo de IAuthenticationService
    # ------------------------------------------------------------------

    def get_password_hash(self, usuario_id: int) -> str | None:
        stmt = select(usuarios.c.password_hash).where(usuarios.c.id == usuario_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row[0] if row else None

    def actualizar_password_hash(self, usuario_id: int, nuevo_hash: str) -> bool:
        stmt = (
            update(usuarios)
            .where(usuarios.c.id == usuario_id)
            .values(password_hash=nuevo_hash)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0


__all__ = ["SqlaUsuarioRepository"]
