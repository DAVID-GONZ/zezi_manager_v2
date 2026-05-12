"""
SqliteEstudianteRepository — implementación SQLite de IEstudianteRepository.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.domain.models.estudiante import (
    EstadoMatricula,
    Estudiante,
    EstudianteResumenDTO,
    FiltroEstudiantesDTO,
    Genero,
    TipoDocumento,
)
from src.domain.models.piar import PIAR


class SqliteEstudianteRepository(IEstudianteRepository):

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

    def _row_to_estudiante(self, row: sqlite3.Row) -> Estudiante:
        d = dict(row)
        d["tipo_documento"] = TipoDocumento(d["tipo_documento"])
        if d.get("genero"):
            d["genero"] = Genero(d["genero"])
        d["estado_matricula"] = EstadoMatricula(d["estado_matricula"])
        d["posee_piar"] = bool(d["posee_piar"])
        return Estudiante(**d)

    def _row_to_resumen(self, row: sqlite3.Row) -> EstudianteResumenDTO:
        d = dict(row)
        tipo_doc = TipoDocumento(d["tipo_documento"])
        num_doc = d["numero_documento"]
        return EstudianteResumenDTO(
            id=d["id"],
            id_publico=d.get("id_publico"),
            documento_display=f"{tipo_doc.value} {num_doc}",
            nombre_completo=f"{d['nombre']} {d['apellido']}",
            genero=Genero(d["genero"]) if d.get("genero") else None,
            grupo_id=d.get("grupo_id"),
            estado_matricula=EstadoMatricula(d["estado_matricula"]),
            posee_piar=bool(d["posee_piar"]),
        )

    # ------------------------------------------------------------------
    # Lectura — estudiantes
    # ------------------------------------------------------------------

    def get_by_id(self, estudiante_id: int) -> Estudiante | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM estudiantes WHERE id = ?", (estudiante_id,)
            ).fetchone()
            return self._row_to_estudiante(row) if row else None

    def get_by_documento(self, numero_documento: str) -> Estudiante | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM estudiantes WHERE numero_documento = ?",
                (numero_documento.upper(),),
            ).fetchone()
            return self._row_to_estudiante(row) if row else None

    def existe_documento(self, numero_documento: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM estudiantes WHERE numero_documento = ?",
                (numero_documento.upper(),),
            ).fetchone()
            return row is not None

    def get_resumen(self, estudiante_id: int) -> EstudianteResumenDTO | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM estudiantes WHERE id = ?", (estudiante_id,)
            ).fetchone()
            return self._row_to_resumen(row) if row else None

    def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]:
        sql = "SELECT * FROM estudiantes WHERE 1=1"
        params: list = []
        if filtro.grupo_id is not None:
            sql += " AND grupo_id = ?"
            params.append(filtro.grupo_id)
        if filtro.estado_matricula is not None:
            sql += " AND estado_matricula = ?"
            params.append(filtro.estado_matricula.value)
        if filtro.posee_piar is not None:
            sql += " AND posee_piar = ?"
            params.append(int(filtro.posee_piar))
        if filtro.busqueda:
            like = f"%{filtro.busqueda.lower()}%"
            sql += (
                " AND (LOWER(nombre) LIKE ? OR LOWER(apellido) LIKE ?"
                " OR LOWER(numero_documento) LIKE ?)"
            )
            params.extend([like, like, like])
        sql += " ORDER BY apellido, nombre"
        offset = (filtro.pagina - 1) * filtro.por_pagina
        sql += f" LIMIT {filtro.por_pagina} OFFSET {offset}"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_estudiante(r) for r in rows]

    def listar_resumenes(self, filtro: FiltroEstudiantesDTO) -> list[EstudianteResumenDTO]:
        sql = "SELECT * FROM estudiantes WHERE 1=1"
        params: list = []
        if filtro.grupo_id is not None:
            sql += " AND grupo_id = ?"
            params.append(filtro.grupo_id)
        if filtro.estado_matricula is not None:
            sql += " AND estado_matricula = ?"
            params.append(filtro.estado_matricula.value)
        if filtro.posee_piar is not None:
            sql += " AND posee_piar = ?"
            params.append(int(filtro.posee_piar))
        if filtro.busqueda:
            like = f"%{filtro.busqueda.lower()}%"
            sql += (
                " AND (LOWER(nombre) LIKE ? OR LOWER(apellido) LIKE ?"
                " OR LOWER(numero_documento) LIKE ?)"
            )
            params.extend([like, like, like])
        sql += " ORDER BY apellido, nombre"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_resumen(r) for r in rows]

    def listar_por_grupo(self, grupo_id: int, solo_activos: bool = True) -> list[Estudiante]:
        sql = "SELECT * FROM estudiantes WHERE grupo_id = ?"
        params: list = [grupo_id]
        if solo_activos:
            sql += " AND estado_matricula = 'activo'"
        sql += " ORDER BY apellido, nombre"
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_estudiante(r) for r in rows]

    def contar_por_grupo(self, grupo_id: int, solo_activos: bool = True) -> int:
        sql = "SELECT COUNT(*) FROM estudiantes WHERE grupo_id = ?"
        params: list = [grupo_id]
        if solo_activos:
            sql += " AND estado_matricula = 'activo'"
        with self._get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return int(row[0])

    # ------------------------------------------------------------------
    # Escritura — estudiantes
    # ------------------------------------------------------------------

    def guardar(self, estudiante: Estudiante) -> Estudiante:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO estudiantes
                    (id_publico, tipo_documento, numero_documento,
                     nombre, apellido, genero, grupo_id, posee_piar,
                     fecha_nacimiento, direccion, fecha_ingreso, estado_matricula)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    estudiante.id_publico,
                    estudiante.tipo_documento.value,
                    estudiante.numero_documento,
                    estudiante.nombre,
                    estudiante.apellido,
                    estudiante.genero.value if estudiante.genero else None,
                    estudiante.grupo_id,
                    int(estudiante.posee_piar),
                    estudiante.fecha_nacimiento.isoformat()
                    if estudiante.fecha_nacimiento else None,
                    estudiante.direccion,
                    estudiante.fecha_ingreso.isoformat(),
                    estudiante.estado_matricula.value,
                ),
            )
            if self._conn is None:
                conn.commit()
            return estudiante.model_copy(update={"id": cursor.lastrowid})

    def actualizar(self, estudiante: Estudiante) -> Estudiante:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE estudiantes SET
                    nombre = ?, apellido = ?, genero = ?,
                    grupo_id = ?, posee_piar = ?, fecha_nacimiento = ?,
                    direccion = ?, estado_matricula = ?
                WHERE id = ?
                """,
                (
                    estudiante.nombre,
                    estudiante.apellido,
                    estudiante.genero.value if estudiante.genero else None,
                    estudiante.grupo_id,
                    int(estudiante.posee_piar),
                    estudiante.fecha_nacimiento.isoformat()
                    if estudiante.fecha_nacimiento else None,
                    estudiante.direccion,
                    estudiante.estado_matricula.value,
                    estudiante.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return estudiante

    def actualizar_estado_matricula(self, estudiante_id: int, estado: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE estudiantes SET estado_matricula = ? WHERE id = ?",
                (estado, estudiante_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    def asignar_grupo(self, estudiante_id: int, grupo_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE estudiantes SET grupo_id = ? WHERE id = ?",
                (grupo_id, estudiante_id),
            )
            if self._conn is None:
                conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # PIAR
    # ------------------------------------------------------------------

    def get_piar(self, estudiante_id: int, anio_id: int) -> PIAR | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM piar WHERE estudiante_id = ? AND anio_id = ?",
                (estudiante_id, anio_id),
            ).fetchone()
            return PIAR(**dict(row)) if row else None

    def listar_piars(self, estudiante_id: int) -> list[PIAR]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM piar WHERE estudiante_id = ? ORDER BY anio_id DESC",
                (estudiante_id,),
            ).fetchall()
            return [PIAR(**dict(r)) for r in rows]

    def existe_piar(self, estudiante_id: int, anio_id: int) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM piar WHERE estudiante_id = ? AND anio_id = ?",
                (estudiante_id, anio_id),
            ).fetchone()
            return row is not None

    def guardar_piar(self, piar: PIAR) -> PIAR:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO piar
                    (estudiante_id, anio_id, descripcion_necesidad,
                     ajustes_evaluativos, ajustes_pedagogicos, profesionales_apoyo,
                     fecha_elaboracion, fecha_revision, usuario_elaboracion_id)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    piar.estudiante_id,
                    piar.anio_id,
                    piar.descripcion_necesidad,
                    piar.ajustes_evaluativos,
                    piar.ajustes_pedagogicos,
                    piar.profesionales_apoyo,
                    piar.fecha_elaboracion.isoformat(),
                    piar.fecha_revision.isoformat() if piar.fecha_revision else None,
                    piar.usuario_elaboracion_id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return piar.model_copy(update={"id": cursor.lastrowid})

    def actualizar_piar(self, piar: PIAR) -> PIAR:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE piar SET
                    descripcion_necesidad = ?, ajustes_evaluativos = ?,
                    ajustes_pedagogicos = ?, profesionales_apoyo = ?,
                    fecha_revision = ?
                WHERE id = ?
                """,
                (
                    piar.descripcion_necesidad,
                    piar.ajustes_evaluativos,
                    piar.ajustes_pedagogicos,
                    piar.profesionales_apoyo,
                    piar.fecha_revision.isoformat() if piar.fecha_revision else None,
                    piar.id,
                ),
            )
            if self._conn is None:
                conn.commit()
            return piar


__all__ = ["SqliteEstudianteRepository"]
