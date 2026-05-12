"""
SqliteUsuarioRepository — implementación SQLite de IUsuarioRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.usuario_repo import IUsuarioRepository
from src.domain.models.usuario import (
    AsignacionDocenteInfoDTO,
    DocenteInfoDTO,
    FiltroUsuariosDTO,
    Rol,
    Usuario,
    UsuarioResumenDTO,
)

_COLS_USUARIO = (
    "id, usuario, nombre_completo, email, telefono, "
    "rol, activo, fecha_creacion, ultima_sesion"
)


class SqliteUsuarioRepository(IUsuarioRepository):

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

    def _row_to_usuario(self, row: sqlite3.Row) -> Usuario:
        d = dict(row)
        d["rol"] = Rol(d["rol"])
        d["activo"] = bool(d["activo"])
        return Usuario(**d)

    # ------------------------------------------------------------------
    # Lectura — usuarios
    # ------------------------------------------------------------------

    def get_by_id(self, usuario_id: int) -> Usuario | None:
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT {_COLS_USUARIO} FROM usuarios WHERE id = ?",
                (usuario_id,),
            ).fetchone()
            return self._row_to_usuario(row) if row else None

    def get_by_username(self, username: str) -> Usuario | None:
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT {_COLS_USUARIO} FROM usuarios "
                "WHERE LOWER(usuario) = LOWER(?)",
                (username,),
            ).fetchone()
            return self._row_to_usuario(row) if row else None

    def get_by_email(self, email: str) -> Usuario | None:
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT {_COLS_USUARIO} FROM usuarios WHERE LOWER(email) = LOWER(?)",
                (email,),
            ).fetchone()
            return self._row_to_usuario(row) if row else None

    def existe_usuario(self, username: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM usuarios WHERE LOWER(usuario) = LOWER(?)",
                (username,),
            ).fetchone()
            return row is not None

    def listar_filtrado(self, filtro: FiltroUsuariosDTO) -> list[Usuario]:
        sql = f"SELECT {_COLS_USUARIO} FROM usuarios WHERE 1=1"
        params: list = []
        if filtro.solo_activos:
            sql += " AND activo = 1"
        if filtro.rol is not None:
            sql += " AND rol = ?"
            params.append(filtro.rol.value)
        if filtro.busqueda:
            sql += " AND (LOWER(nombre_completo) LIKE ? OR LOWER(usuario) LIKE ?)"
            like = f"%{filtro.busqueda.lower()}%"
            params.extend([like, like])
        sql += " ORDER BY nombre_completo"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_usuario(r) for r in rows]

    def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]:
        sql = "SELECT id, usuario, nombre_completo, rol, activo FROM usuarios WHERE 1=1"
        params: list = []
        if filtro.solo_activos:
            sql += " AND activo = 1"
        if filtro.rol is not None:
            sql += " AND rol = ?"
            params.append(filtro.rol.value)
        if filtro.busqueda:
            sql += " AND (LOWER(nombre_completo) LIKE ? OR LOWER(usuario) LIKE ?)"
            like = f"%{filtro.busqueda.lower()}%"
            params.extend([like, like])
        sql += " ORDER BY nombre_completo"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
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
        periodo_id: int | None = None,
        solo_activos: bool = True,
    ) -> list[DocenteInfoDTO]:
        periodo_filter_a = "AND a.periodo_id = ?" if periodo_id else ""
        periodo_filter_h = "AND h.periodo_id = ?" if periodo_id else ""
        activos_filter = "AND u.activo = 1" if solo_activos else ""
        sql = f"""
            SELECT
                u.id, u.usuario, u.nombre_completo, u.email,
                u.telefono, u.activo, u.fecha_creacion, u.ultima_sesion,
                COUNT(DISTINCT a.id)            AS total_asignaciones,
                COUNT(DISTINCT a.grupo_id)      AS grupos_asignados,
                COUNT(DISTINCT a.asignatura_id) AS asignaturas_asignadas,
                COALESCE(SUM(DISTINCT s.horas_semanales * (a.id IS NOT NULL)), 0)
                                                AS horas_totales,
                COUNT(DISTINCT h.id)            AS bloques_horarios
            FROM usuarios u
            LEFT JOIN asignaciones a
                ON a.usuario_id = u.id AND a.activo = 1 {periodo_filter_a}
            LEFT JOIN asignaturas s ON s.id = a.asignatura_id
            LEFT JOIN horarios h ON h.usuario_id = u.id {periodo_filter_h}
            WHERE u.rol = 'profesor' {activos_filter}
            GROUP BY u.id
            ORDER BY u.nombre_completo
        """
        params: list = []
        if periodo_id:
            params.append(periodo_id)
            params.append(periodo_id)
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["activo"] = bool(d["activo"])
                result.append(DocenteInfoDTO(**d))
            return result

    def get_docente_info(
        self,
        usuario_id: int,
        periodo_id: int | None = None,
    ) -> DocenteInfoDTO | None:
        periodo_filter_a = "AND a.periodo_id = ?" if periodo_id else ""
        periodo_filter_h = "AND h.periodo_id = ?" if periodo_id else ""
        sql = f"""
            SELECT
                u.id, u.usuario, u.nombre_completo, u.email,
                u.telefono, u.activo, u.fecha_creacion, u.ultima_sesion,
                COUNT(DISTINCT a.id)            AS total_asignaciones,
                COUNT(DISTINCT a.grupo_id)      AS grupos_asignados,
                COUNT(DISTINCT a.asignatura_id) AS asignaturas_asignadas,
                COALESCE(SUM(DISTINCT s.horas_semanales * (a.id IS NOT NULL)), 0)
                                                AS horas_totales,
                COUNT(DISTINCT h.id)            AS bloques_horarios
            FROM usuarios u
            LEFT JOIN asignaciones a
                ON a.usuario_id = u.id AND a.activo = 1 {periodo_filter_a}
            LEFT JOIN asignaturas s ON s.id = a.asignatura_id
            LEFT JOIN horarios h ON h.usuario_id = u.id {periodo_filter_h}
            WHERE u.id = ? AND u.rol = 'profesor'
            GROUP BY u.id
        """
        params: list = []
        if periodo_id:
            params.append(periodo_id)
            params.append(periodo_id)
        params.append(usuario_id)
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            if not row:
                return None
            d = dict(row)
            d["activo"] = bool(d["activo"])
            return DocenteInfoDTO(**d)

    def listar_asignaciones_docente(
        self,
        usuario_id: int,
        periodo_id: int | None = None,
    ) -> list[AsignacionDocenteInfoDTO]:
        sql = """
            SELECT
                a.id,
                a.grupo_id,
                g.codigo  AS grupo_codigo,
                g.nombre  AS grupo_nombre,
                a.asignatura_id,
                s.nombre  AS asignatura_nombre,
                s.codigo  AS asignatura_codigo,
                s.horas_semanales AS horas_teoricas,
                COUNT(h.id) AS horas_programadas,
                a.periodo_id,
                p.nombre  AS periodo_nombre,
                a.activo
            FROM asignaciones a
            JOIN grupos      g ON g.id = a.grupo_id
            JOIN asignaturas s ON s.id = a.asignatura_id
            JOIN periodos    p ON p.id = a.periodo_id
            LEFT JOIN horarios h ON h.asignacion_id = a.id
            WHERE a.usuario_id = ?
        """
        params: list = [usuario_id]
        if periodo_id is not None:
            sql += " AND a.periodo_id = ?"
            params.append(periodo_id)
        sql += " GROUP BY a.id ORDER BY g.codigo, s.nombre"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
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
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO usuarios
                    (usuario, password_hash, nombre_completo, email, telefono,
                     rol, activo, fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    usuario.usuario,
                    "",  # placeholder — IAuthenticationService lo actualiza
                    usuario.nombre_completo,
                    usuario.email,
                    usuario.telefono,
                    usuario.rol.value,
                    int(usuario.activo),
                    usuario.fecha_creacion.isoformat(),
                ),
            )
            if self._conn is None:
                conn.commit()
            return usuario.model_copy(update={"id": cursor.lastrowid})

    def actualizar(self, usuario: Usuario) -> Usuario:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE usuarios
                SET nombre_completo = ?, email = ?, telefono = ?
                WHERE id = ?
                """,
                (
                    usuario.nombre_completo,
                    usuario.email,
                    usuario.telefono,
                    usuario.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return usuario

    def cambiar_rol(self, usuario_id: int, nuevo_rol: Rol) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE usuarios SET rol = ? WHERE id = ?",
                (nuevo_rol.value, usuario_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def desactivar(self, usuario_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE usuarios SET activo = 0 WHERE id = ?",
                (usuario_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def reactivar(self, usuario_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE usuarios SET activo = 1 WHERE id = ?",
                (usuario_id,),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0


__all__ = ["SqliteUsuarioRepository"]
