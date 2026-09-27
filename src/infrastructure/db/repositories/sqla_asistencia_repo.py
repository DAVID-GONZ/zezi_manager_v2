"""Implementación SQLAlchemy Core de IAsistenciaRepository — ZECI Manager v2.0."""
from __future__ import annotations

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.domain.models.asistencia import (
    ControlDiario,
    EstadoAsistencia,
    ResumenAsistenciaDTO,
)
from src.domain.ports.asistencia_repo import IAsistenciaRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import asignaciones, control_diario


class SqlaAsistenciaRepository(RepositorioBase, IAsistenciaRepository):
    def __init__(self, conn=None):
        super().__init__(conn, control_diario)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_control(self, row) -> ControlDiario:
        d = dict(row)
        d["estado"] = EstadoAsistencia(d["estado"])
        d["uniforme"] = bool(d["uniforme"])
        d["materiales"] = bool(d["materiales"])
        return ControlDiario(**d)

    @staticmethod
    def _fmt_hora(t) -> str | None:
        if t is None:
            return None
        return t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)

    def _control_to_dict(self, c: ControlDiario) -> dict:
        return {
            "estudiante_id": c.estudiante_id,
            "grupo_id": c.grupo_id,
            "asignacion_id": c.asignacion_id,
            "periodo_id": c.periodo_id,
            "fecha": c.fecha,
            "estado": c.estado.value,
            "hora_entrada": self._fmt_hora(c.hora_entrada),
            "hora_salida": self._fmt_hora(c.hora_salida),
            "uniforme": int(c.uniforme),
            "materiales": int(c.materiales),
            "observacion": c.observacion,
            "usuario_registro_id": c.usuario_registro_id,
            "fecha_actualizacion": c.fecha_actualizacion,
        }

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def registrar(self, control: ControlDiario) -> ControlDiario:
        _UPSERT_COLS = [
            "estado", "hora_entrada", "hora_salida",
            "uniforme", "materiales", "observacion",
            "usuario_registro_id", "fecha_actualizacion",
        ]
        stmt = self._upsert(
            control_diario,
            values=self._control_to_dict(control),
            conflict_cols=["estudiante_id", "grupo_id", "asignacion_id", "fecha"],
            update_cols=_UPSERT_COLS,
        )
        with self._get_conn() as conn:
            result = conn.execute(stmt)
            if self._conn is None:
                conn.commit()
            return control.model_copy(update={"id": result.inserted_primary_key[0]})

    def registrar_masivo(self, controles: list[ControlDiario]) -> int:
        if not controles:
            return 0
        rows = [self._control_to_dict(c) for c in controles]
        base_stmt = sqlite_insert(control_diario)
        stmt = base_stmt.on_conflict_do_update(
            index_elements=["estudiante_id", "grupo_id", "asignacion_id", "fecha"],
            set_={
                "estado": base_stmt.excluded.estado,
                "hora_entrada": base_stmt.excluded.hora_entrada,
                "hora_salida": base_stmt.excluded.hora_salida,
                "uniforme": base_stmt.excluded.uniforme,
                "materiales": base_stmt.excluded.materiales,
                "observacion": base_stmt.excluded.observacion,
                "usuario_registro_id": base_stmt.excluded.usuario_registro_id,
                "fecha_actualizacion": base_stmt.excluded.fecha_actualizacion,
            },
        )
        with self._get_conn() as conn:
            conn.execute(stmt, rows)
            if self._conn is None:
                conn.commit()
        return len(controles)

    # ------------------------------------------------------------------
    # Lectura — registro individual
    # ------------------------------------------------------------------

    def get_por_fecha_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int,
        fecha: date,
    ) -> ControlDiario | None:
        stmt = self._select().where(
            control_diario.c.estudiante_id == estudiante_id,
            control_diario.c.asignacion_id == asignacion_id,
            control_diario.c.fecha == fecha,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            return self._row_to_control(row) if row else None

    def listar_por_grupo_y_fecha(
        self,
        grupo_id: int,
        asignacion_id: int,
        fecha: date,
    ) -> list[ControlDiario]:
        stmt = self._select().where(
            control_diario.c.grupo_id == grupo_id,
            control_diario.c.asignacion_id == asignacion_id,
            control_diario.c.fecha == fecha,
        ).order_by(control_diario.c.estudiante_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_control(r) for r in rows]

    def listar_por_estudiante_y_periodo(
        self,
        estudiante_id: int,
        periodo_id: int,
    ) -> list[ControlDiario]:
        stmt = self._select().where(
            control_diario.c.estudiante_id == estudiante_id,
            control_diario.c.periodo_id == periodo_id,
        ).order_by(control_diario.c.fecha, control_diario.c.asignacion_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_control(r) for r in rows]

    def listar_por_asignacion_y_rango(
        self,
        asignacion_id: int,
        fecha_desde: date,
        fecha_hasta: date,
    ) -> list[ControlDiario]:
        stmt = self._select().where(
            control_diario.c.asignacion_id == asignacion_id,
            control_diario.c.fecha >= fecha_desde,
            control_diario.c.fecha <= fecha_hasta,
        ).order_by(control_diario.c.fecha, control_diario.c.estudiante_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_control(r) for r in rows]

    # ------------------------------------------------------------------
    # Lectura — resúmenes y estadísticas
    # ------------------------------------------------------------------

    def resumen_por_estudiante(
        self,
        estudiante_id: int,
        periodo_id: int,
        asignacion_id: int | None = None,
    ) -> ResumenAsistenciaDTO:
        stmt = select(
            control_diario.c.estudiante_id,
            func.count().label("total_clases"),
            func.sum(case((control_diario.c.estado == "P", 1), else_=0)).label("presentes"),
            func.sum(case((control_diario.c.estado == "FJ", 1), else_=0)).label("faltas_justificadas"),
            func.sum(case((control_diario.c.estado == "FI", 1), else_=0)).label("faltas_injustificadas"),
            func.sum(case((control_diario.c.estado == "R", 1), else_=0)).label("retrasos"),
            func.sum(case((control_diario.c.estado == "E", 1), else_=0)).label("excusas"),
        ).where(
            control_diario.c.estudiante_id == estudiante_id,
            control_diario.c.periodo_id == periodo_id,
        )
        if asignacion_id is not None:
            stmt = stmt.where(control_diario.c.asignacion_id == asignacion_id)
        stmt = stmt.group_by(control_diario.c.estudiante_id)
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            if not row:
                return ResumenAsistenciaDTO(estudiante_id=estudiante_id)
            return ResumenAsistenciaDTO(**dict(row))

    def resumen_por_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ResumenAsistenciaDTO]:
        stmt = select(
            control_diario.c.estudiante_id,
            func.count().label("total_clases"),
            func.sum(case((control_diario.c.estado == "P", 1), else_=0)).label("presentes"),
            func.sum(case((control_diario.c.estado == "FJ", 1), else_=0)).label("faltas_justificadas"),
            func.sum(case((control_diario.c.estado == "FI", 1), else_=0)).label("faltas_injustificadas"),
            func.sum(case((control_diario.c.estado == "R", 1), else_=0)).label("retrasos"),
            func.sum(case((control_diario.c.estado == "E", 1), else_=0)).label("excusas"),
        ).where(
            control_diario.c.grupo_id == grupo_id,
            control_diario.c.asignacion_id == asignacion_id,
            control_diario.c.periodo_id == periodo_id,
        ).group_by(control_diario.c.estudiante_id).order_by(control_diario.c.estudiante_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [ResumenAsistenciaDTO(**dict(r)) for r in rows]

    def contar_faltas_injustificadas(
        self,
        estudiante_id: int,
        periodo_id: int,
    ) -> int:
        stmt = select(func.count()).where(
            control_diario.c.estudiante_id == estudiante_id,
            control_diario.c.periodo_id == periodo_id,
            control_diario.c.estado == "FI",
        )
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    def fechas_con_registro(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[date]:
        stmt = (
            select(control_diario.c.fecha)
            .distinct()
            .where(
                control_diario.c.asignacion_id == asignacion_id,
                control_diario.c.periodo_id == periodo_id,
            )
            .order_by(control_diario.c.fecha)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
            result = []
            for r in rows:
                val = r[0]
                if isinstance(val, date):
                    result.append(val)
                else:
                    result.append(date.fromisoformat(str(val)))
            return result

    def porcentaje_asistencia_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float:
        stmt = select(
            func.count().label("total"),
            func.sum(case(
                (control_diario.c.estado == "FI", 1),
                (control_diario.c.estado == "R", 1),
                else_=0,
            )).label("ausencias"),
        ).where(
            control_diario.c.grupo_id == grupo_id,
            control_diario.c.asignacion_id == asignacion_id,
            control_diario.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            if not row or not row["total"]:
                return 0.0
            total = row["total"]
            ausencias = row["ausencias"] or 0
            return round((1 - ausencias / total) * 100, 1)

    def estudiantes_en_riesgo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
        umbral_pct: float = 80.0,
    ) -> list[int]:
        # Obtiene los agregados y filtra en Python para evitar HAVING con
        # expresiones computadas que SQLAlchemy Core no puede referenciar por alias.
        stmt = select(
            control_diario.c.estudiante_id,
            func.count().label("total"),
            func.sum(case(
                (control_diario.c.estado == "FI", 1),
                (control_diario.c.estado == "R", 1),
                else_=0,
            )).label("ausencias"),
        ).where(
            control_diario.c.grupo_id == grupo_id,
            control_diario.c.asignacion_id == asignacion_id,
            control_diario.c.periodo_id == periodo_id,
        ).group_by(control_diario.c.estudiante_id).order_by(control_diario.c.estudiante_id)
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            r["estudiante_id"]
            for r in rows
            if r["total"] and r["total"] > 0
            and round((1.0 - (r["ausencias"] or 0) / r["total"]) * 100, 1) < umbral_pct
        ]

    def contar_clases_dictadas_docente(self, usuario_id: int, anio: int, mes: int) -> int:
        anio_str = f"{anio:04d}"
        mes_str = f"{mes:02d}"
        inner = (
            select(control_diario.c.asignacion_id, control_diario.c.fecha)
            .join(asignaciones, asignaciones.c.id == control_diario.c.asignacion_id)
            .where(
                asignaciones.c.usuario_id == usuario_id,
                func.strftime("%Y", control_diario.c.fecha) == anio_str,
                func.strftime("%m", control_diario.c.fecha) == mes_str,
            )
            .group_by(control_diario.c.asignacion_id, control_diario.c.fecha)
            .subquery()
        )
        stmt = select(func.count()).select_from(inner)
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    def clases_dictadas_por_asignacion(
        self, usuario_id: int, anio: int, mes: int
    ) -> dict[int, int]:
        anio_str = f"{anio:04d}"
        mes_str = f"{mes:02d}"
        stmt = (
            select(
                control_diario.c.asignacion_id,
                func.count(control_diario.c.fecha.distinct()).label("n"),
            )
            .join(asignaciones, asignaciones.c.id == control_diario.c.asignacion_id)
            .where(
                asignaciones.c.usuario_id == usuario_id,
                func.strftime("%Y", control_diario.c.fecha) == anio_str,
                func.strftime("%m", control_diario.c.fecha) == mes_str,
            )
            .group_by(control_diario.c.asignacion_id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
            return {row[0]: row[1] for row in rows}


__all__ = ["SqlaAsistenciaRepository"]
