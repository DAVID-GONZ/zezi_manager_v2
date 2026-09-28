"""Implementación SQLAlchemy Core de IEstudianteRepository — AVEDRA v2.0."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, insert, select, update

from src.domain.models.estudiante import (
    EstadoMatricula,
    Estudiante,
    EstudianteResumenDTO,
    FiltroEstudiantesDTO,
    Genero,
    MovimientoEstudiante,
    MovimientoEstudianteInfoDTO,
    TipoDocumento,
    TipoMovimiento,
)
from src.domain.models.piar import PIAR
from src.domain.models.tenant import TenantScope
from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    estudiantes,
    grupos,
    historial_estudiantes,
)
from src.infrastructure.db.schema import (
    piar as piar_tabla,
)


class SqlaEstudianteRepository(RepositorioBase, IEstudianteRepository):
    def __init__(self, conn=None):
        super().__init__(conn, estudiantes)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _row_to_estudiante(self, row) -> Estudiante:
        d = dict(row)
        d["tipo_documento"] = TipoDocumento(d["tipo_documento"])
        if d.get("genero"):
            d["genero"] = Genero(d["genero"])
        d["estado_matricula"] = EstadoMatricula(d["estado_matricula"])
        d["posee_piar"] = bool(d["posee_piar"])
        return Estudiante(**d)

    def _row_to_resumen(self, row) -> EstudianteResumenDTO:
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

    @staticmethod
    def _parse_fecha(valor) -> datetime | None:
        if valor is None:
            return None
        if isinstance(valor, datetime):
            return valor
        try:
            return datetime.fromisoformat(str(valor))
        except (ValueError, TypeError):
            return None

    def _row_to_movimiento_info(self, row) -> MovimientoEstudianteInfoDTO:
        d = dict(row)
        return MovimientoEstudianteInfoDTO(
            id=d["id"],
            estudiante_id=d["estudiante_id"],
            grupo_origen_codigo=d.get("grupo_origen_codigo"),
            grupo_destino_codigo=d.get("grupo_destino_codigo"),
            fecha_movimiento=self._parse_fecha(d.get("fecha_movimiento")),
            tipo_movimiento=TipoMovimiento(d["tipo_movimiento"]),
            motivo=d.get("motivo"),
            usuario_registro_id=d.get("usuario_registro_id"),
        )

    def _build_filtro_stmt(self, filtro: FiltroEstudiantesDTO, select_stmt):
        """Aplica los filtros comunes a un SELECT de estudiantes."""
        stmt = select_stmt
        if filtro.institucion_id is not None:
            stmt = stmt.where(estudiantes.c.institucion_id == filtro.institucion_id)
        if filtro.grupo_id is not None:
            stmt = stmt.where(estudiantes.c.grupo_id == filtro.grupo_id)
        if filtro.grupos_ids is not None:
            if not filtro.grupos_ids:
                return None  # vacío → 0 resultados
            stmt = stmt.where(estudiantes.c.grupo_id.in_(filtro.grupos_ids))
        if filtro.estado_matricula is not None:
            stmt = stmt.where(
                estudiantes.c.estado_matricula == filtro.estado_matricula.value
            )
        if filtro.posee_piar is not None:
            stmt = stmt.where(estudiantes.c.posee_piar == int(filtro.posee_piar))
        if filtro.busqueda:
            like = f"%{filtro.busqueda.lower()}%"
            stmt = stmt.where(
                func.lower(estudiantes.c.nombre).like(like)
                | func.lower(estudiantes.c.apellido).like(like)
                | func.lower(estudiantes.c.numero_documento).like(like)
            )
        return stmt.order_by(estudiantes.c.apellido, estudiantes.c.nombre)

    # ------------------------------------------------------------------
    # Lectura — estudiantes
    # ------------------------------------------------------------------

    def get_by_id(self, estudiante_id: int) -> Estudiante | None:
        stmt = self._select().where(estudiantes.c.id == estudiante_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_estudiante(row) if row else None

    def get_by_documento(
        self, numero_documento: str, institucion_id: TenantScope
    ) -> Estudiante | None:
        stmt = self._select().where(
            estudiantes.c.numero_documento == numero_documento.upper()
        )
        if isinstance(institucion_id, int):
            stmt = stmt.where(estudiantes.c.institucion_id == institucion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_estudiante(row) if row else None

    def existe_documento(
        self, numero_documento: str, institucion_id: TenantScope
    ) -> bool:
        stmt = select(estudiantes.c.id).where(
            estudiantes.c.numero_documento == numero_documento.upper()
        )
        if isinstance(institucion_id, int):
            stmt = stmt.where(estudiantes.c.institucion_id == institucion_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row is not None

    def get_resumen(self, estudiante_id: int) -> EstudianteResumenDTO | None:
        stmt = self._select().where(estudiantes.c.id == estudiante_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_resumen(row) if row else None

    def listar_filtrado(self, filtro: FiltroEstudiantesDTO) -> list[Estudiante]:
        stmt = self._build_filtro_stmt(filtro, self._select())
        if stmt is None:
            return []
        offset = (filtro.pagina - 1) * filtro.por_pagina
        stmt = stmt.limit(filtro.por_pagina).offset(offset)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_estudiante(r) for r in rows]

    def listar_resumenes(
        self, filtro: FiltroEstudiantesDTO
    ) -> list[EstudianteResumenDTO]:
        stmt = self._build_filtro_stmt(filtro, self._select())
        if stmt is None:
            return []
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_resumen(r) for r in rows]

    def listar_por_grupo(
        self,
        grupo_id: int,
        institucion_id: TenantScope,
        solo_activos: bool = True,
    ) -> list[Estudiante]:
        stmt = self._select().where(estudiantes.c.grupo_id == grupo_id)
        if isinstance(institucion_id, int):
            stmt = stmt.where(estudiantes.c.institucion_id == institucion_id)
        if solo_activos:
            stmt = stmt.where(estudiantes.c.estado_matricula == "activo")
        stmt = stmt.order_by(estudiantes.c.apellido, estudiantes.c.nombre)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_estudiante(r) for r in rows]

    def contar_por_grupo(
        self,
        grupo_id: int,
        institucion_id: TenantScope,
        solo_activos: bool = True,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(estudiantes)
            .where(estudiantes.c.grupo_id == grupo_id)
        )
        if isinstance(institucion_id, int):
            stmt = stmt.where(estudiantes.c.institucion_id == institucion_id)
        if solo_activos:
            stmt = stmt.where(estudiantes.c.estado_matricula == "activo")
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return int(row[0])

    # ------------------------------------------------------------------
    # Escritura — estudiantes
    # ------------------------------------------------------------------

    def guardar(self, estudiante: Estudiante) -> Estudiante:
        stmt = insert(estudiantes).values(
            id_publico=estudiante.id_publico,
            tipo_documento=estudiante.tipo_documento.value,
            numero_documento=estudiante.numero_documento,
            nombre=estudiante.nombre,
            apellido=estudiante.apellido,
            genero=estudiante.genero.value if estudiante.genero else None,
            grupo_id=estudiante.grupo_id,
            posee_piar=int(estudiante.posee_piar),
            fecha_nacimiento=estudiante.fecha_nacimiento,
            direccion=estudiante.direccion,
            fecha_ingreso=estudiante.fecha_ingreso,
            estado_matricula=estudiante.estado_matricula.value,
            institucion_id=estudiante.institucion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return estudiante.model_copy(update={"id": pk})

    def actualizar(self, estudiante: Estudiante) -> Estudiante:
        # No se actualiza institucion_id ni numero_documento (identificador único)
        stmt = (
            update(estudiantes)
            .where(estudiantes.c.id == estudiante.id)
            .values(
                nombre=estudiante.nombre,
                apellido=estudiante.apellido,
                genero=estudiante.genero.value if estudiante.genero else None,
                grupo_id=estudiante.grupo_id,
                posee_piar=int(estudiante.posee_piar),
                fecha_nacimiento=estudiante.fecha_nacimiento,
                direccion=estudiante.direccion,
                estado_matricula=estudiante.estado_matricula.value,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return estudiante

    def actualizar_estado_matricula(self, estudiante_id: int, estado: str) -> bool:
        stmt = (
            update(estudiantes)
            .where(estudiantes.c.id == estudiante_id)
            .values(estado_matricula=estado)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    def asignar_grupo(self, estudiante_id: int, grupo_id: int) -> bool:
        stmt = (
            update(estudiantes)
            .where(estudiantes.c.id == estudiante_id)
            .values(grupo_id=grupo_id)
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Historial de movimientos (paso_43)
    # ------------------------------------------------------------------

    def registrar_movimiento(
        self,
        estudiante_id: int,
        grupo_origen_id: int | None,
        grupo_destino_id: int | None,
        tipo: TipoMovimiento,
        motivo: str | None = None,
        usuario_registro_id: int | None = None,
    ) -> MovimientoEstudiante:
        stmt = insert(historial_estudiantes).values(
            estudiante_id=estudiante_id,
            grupo_origen_id=grupo_origen_id,
            grupo_destino_id=grupo_destino_id,
            tipo_movimiento=tipo.value,
            motivo=motivo,
            usuario_registro_id=usuario_registro_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
            # Recuperar fecha_movimiento generada por server_default
            row = conn.execute(
                select(historial_estudiantes.c.fecha_movimiento).where(
                    historial_estudiantes.c.id == pk
                )
            ).fetchone()
            fecha = self._parse_fecha(row[0]) if row else None

        return MovimientoEstudiante(
            id=pk,
            estudiante_id=estudiante_id,
            grupo_origen_id=grupo_origen_id,
            grupo_destino_id=grupo_destino_id,
            fecha_movimiento=fecha,
            tipo_movimiento=tipo,
            motivo=motivo,
            usuario_registro_id=usuario_registro_id,
        )

    def listar_historial(
        self, estudiante_id: int
    ) -> list[MovimientoEstudianteInfoDTO]:
        go = grupos.alias("go")
        gd = grupos.alias("gd")
        stmt = (
            select(
                historial_estudiantes.c.id,
                historial_estudiantes.c.estudiante_id,
                go.c.codigo.label("grupo_origen_codigo"),
                gd.c.codigo.label("grupo_destino_codigo"),
                historial_estudiantes.c.fecha_movimiento,
                historial_estudiantes.c.tipo_movimiento,
                historial_estudiantes.c.motivo,
                historial_estudiantes.c.usuario_registro_id,
            )
            .select_from(historial_estudiantes)
            .outerjoin(go, go.c.id == historial_estudiantes.c.grupo_origen_id)
            .outerjoin(gd, gd.c.id == historial_estudiantes.c.grupo_destino_id)
            .where(historial_estudiantes.c.estudiante_id == estudiante_id)
            .order_by(
                historial_estudiantes.c.fecha_movimiento.desc(),
                historial_estudiantes.c.id.desc(),
            )
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_movimiento_info(r) for r in rows]

    # ------------------------------------------------------------------
    # PIAR
    # ------------------------------------------------------------------

    def get_piar(self, estudiante_id: int, anio_id: int) -> PIAR | None:
        stmt = select(piar_tabla).where(
            piar_tabla.c.estudiante_id == estudiante_id,
            piar_tabla.c.anio_id == anio_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return PIAR(**dict(row)) if row else None

    def listar_piars(self, estudiante_id: int) -> list[PIAR]:
        stmt = (
            select(piar_tabla)
            .where(piar_tabla.c.estudiante_id == estudiante_id)
            .order_by(piar_tabla.c.anio_id.desc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [PIAR(**dict(r)) for r in rows]

    def existe_piar(self, estudiante_id: int, anio_id: int) -> bool:
        stmt = select(piar_tabla.c.id).where(
            piar_tabla.c.estudiante_id == estudiante_id,
            piar_tabla.c.anio_id == anio_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).fetchone()
            return row is not None

    def guardar_piar(self, piar: PIAR) -> PIAR:
        stmt = insert(piar_tabla).values(
            estudiante_id=piar.estudiante_id,
            anio_id=piar.anio_id,
            descripcion_necesidad=piar.descripcion_necesidad,
            ajustes_evaluativos=piar.ajustes_evaluativos,
            ajustes_pedagogicos=piar.ajustes_pedagogicos,
            profesionales_apoyo=piar.profesionales_apoyo,
            fecha_elaboracion=piar.fecha_elaboracion,
            fecha_revision=piar.fecha_revision,
            usuario_elaboracion_id=piar.usuario_elaboracion_id,
        )
        with self._get_conn() as conn:
            pk = self._execute_insert(conn, stmt)
            if self._conn is None:
                conn.commit()
        return piar.model_copy(update={"id": pk})

    def actualizar_piar(self, piar: PIAR) -> PIAR:
        stmt = (
            update(piar_tabla)
            .where(piar_tabla.c.id == piar.id)
            .values(
                descripcion_necesidad=piar.descripcion_necesidad,
                ajustes_evaluativos=piar.ajustes_evaluativos,
                ajustes_pedagogicos=piar.ajustes_pedagogicos,
                profesionales_apoyo=piar.profesionales_apoyo,
                fecha_revision=piar.fecha_revision,
            )
        )
        with self._get_conn() as conn:
            conn.execute(stmt)
            if self._conn is None:
                conn.commit()
        return piar


__all__ = ["SqlaEstudianteRepository"]
