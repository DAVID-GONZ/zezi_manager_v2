"""
Implementación SQLAlchemy Core de IEstadisticosRepository — ZECI Manager v2.0.

Este repositorio es estrictamente de solo lectura: solo SELECT y agregaciones.
No hace INSERT, UPDATE ni DELETE.

Decisiones de migración:
- Todos los métodos usan Core expressions (func, case, outerjoin, and_(), etc.).
- boletin_datos_periodo usa .outerjoin() con and_() para sus LEFT JOINs con
  múltiples condiciones en el ON clause (periodo_id y estudiante_id), lo que
  preserva la semántica OUTER sin necesidad de text().
- En boletin_datos_acumulado / boletin_datos_anual, los IN dinámicos se
  resuelven con .in_([lista]) de Core.
- En consolidado_notas_grupo, las tres sub-queries se migran a Core; la
  composición en Python se conserva tal cual.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, and_, case, func, select
from sqlalchemy.dialects.sqlite import (
    insert as sqlite_insert,  # noqa: F401 (unused, kept for symmetry)
)

from src.domain.models.configuracion import NivelDesempeno
from src.domain.models.dtos import DashboardMetricsDTO
from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.infrastructure.db.repositories.base import RepositorioBase
from src.infrastructure.db.schema import (
    actividades,
    alertas,
    areas_conocimiento,
    asignaciones,
    asignaturas,
    categorias,
    cierres_anio,
    cierres_periodo,
    control_diario,
    estudiantes,
    grupos,
    periodos,
    promocion_anual,
)


class SqlaEstadisticosRepository(RepositorioBase, IEstadisticosRepository):
    def __init__(self, conn=None):
        super().__init__(conn, None)  # no tabla principal única

    # ------------------------------------------------------------------
    # Métricas de dashboard
    # ------------------------------------------------------------------

    def calcular_metricas_dashboard(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
    ) -> DashboardMetricsDTO:
        with self._get_conn() as conn:
            # Total estudiantes activos
            total_estudiantes = int(conn.execute(
                select(func.count()).select_from(estudiantes).where(
                    estudiantes.c.grupo_id == grupo_id,
                    estudiantes.c.estado_matricula == "activo",
                )
            ).scalar() or 0)

            # Promedio general
            promedio_general = round(float(conn.execute(
                select(func.coalesce(func.avg(cierres_periodo.c.nota_definitiva), 0.0))
                .join(asignaciones, asignaciones.c.id == cierres_periodo.c.asignacion_id)
                .where(
                    asignaciones.c.grupo_id == grupo_id,
                    cierres_periodo.c.periodo_id == periodo_id,
                )
            ).scalar() or 0), 2)
            promedio_general = max(0.0, min(100.0, promedio_general))

            # Porcentaje de asistencia global
            row_asist = conn.execute(
                select(
                    func.count().label("total"),
                    func.sum(case(
                        (control_diario.c.estado.in_(["FI", "R"]), 1),
                        else_=0,
                    )).label("ausencias"),
                ).where(
                    control_diario.c.grupo_id == grupo_id,
                    control_diario.c.periodo_id == periodo_id,
                )
            ).mappings().first()
            if row_asist and row_asist["total"] and row_asist["total"] > 0:
                pct = round((1 - (row_asist["ausencias"] or 0) / row_asist["total"]) * 100, 2)
                pct_asistencia = max(0.0, min(100.0, pct))
            else:
                pct_asistencia = 0.0

            # Estudiantes en riesgo
            estudiantes_en_riesgo = int(conn.execute(
                select(func.count(cierres_periodo.c.estudiante_id.distinct()))
                .join(asignaciones, asignaciones.c.id == cierres_periodo.c.asignacion_id)
                .where(
                    asignaciones.c.grupo_id == grupo_id,
                    cierres_periodo.c.periodo_id == periodo_id,
                    cierres_periodo.c.nota_definitiva < nota_minima,
                )
            ).scalar() or 0)

            # Actividades publicadas
            actividades_publicadas = int(conn.execute(
                select(func.count(actividades.c.id.distinct()))
                .join(categorias, categorias.c.id == actividades.c.categoria_id)
                .join(asignaciones, asignaciones.c.id == categorias.c.asignacion_id)
                .where(
                    asignaciones.c.grupo_id == grupo_id,
                    categorias.c.periodo_id == periodo_id,
                    actividades.c.estado.in_(["publicada", "cerrada"]),
                )
            ).scalar() or 0)

            # Alertas pendientes
            alertas_pendientes = int(conn.execute(
                select(func.count())
                .select_from(alertas)
                .join(estudiantes, estudiantes.c.id == alertas.c.estudiante_id)
                .where(
                    estudiantes.c.grupo_id == grupo_id,
                    alertas.c.resuelta == False,  # noqa: E712
                )
            ).scalar() or 0)

        return DashboardMetricsDTO(
            grupo_id=grupo_id,
            total_estudiantes=total_estudiantes,
            promedio_general=promedio_general,
            porcentaje_asistencia=pct_asistencia,
            estudiantes_en_riesgo=estudiantes_en_riesgo,
            actividades_publicadas=actividades_publicadas,
            alertas_pendientes=alertas_pendientes,
        )

    def promedio_general_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
    ) -> float:
        stmt = (
            select(func.coalesce(func.avg(cierres_periodo.c.nota_definitiva), 0.0))
            .join(asignaciones, asignaciones.c.id == cierres_periodo.c.asignacion_id)
            .where(
                asignaciones.c.grupo_id == grupo_id,
                cierres_periodo.c.periodo_id == periodo_id,
            )
        )
        with self._get_conn() as conn:
            return round(float(conn.execute(stmt).scalar() or 0), 2)

    def porcentaje_asistencia_global(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> float:
        stmt = select(
            func.count().label("total"),
            func.sum(case(
                (control_diario.c.estado.in_(["FI", "R"]), 1),
                else_=0,
            )).label("ausencias"),
        ).where(
            control_diario.c.grupo_id == grupo_id,
            control_diario.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            row = conn.execute(stmt).mappings().first()
            if not row or not row["total"]:
                return 0.0
            return round((1 - (row["ausencias"] or 0) / row["total"]) * 100, 2)

    def contar_alertas_pendientes(self, grupo_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(alertas)
            .join(estudiantes, estudiantes.c.id == alertas.c.estudiante_id)
            .where(
                estudiantes.c.grupo_id == grupo_id,
                alertas.c.resuelta == False,  # noqa: E712
            )
        )
        with self._get_conn() as conn:
            return int(conn.execute(stmt).scalar() or 0)

    # ------------------------------------------------------------------
    # Estadísticas de notas
    # ------------------------------------------------------------------

    def promedio_por_asignacion(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float:
        stmt = select(
            func.coalesce(func.avg(cierres_periodo.c.nota_definitiva), 0.0)
        ).where(
            cierres_periodo.c.asignacion_id == asignacion_id,
            cierres_periodo.c.periodo_id == periodo_id,
        )
        with self._get_conn() as conn:
            return round(float(conn.execute(stmt).scalar() or 0), 2)

    def distribucion_desempenos(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
        niveles: list[NivelDesempeno],
    ) -> dict[str, int]:
        resultado = {n.nombre: 0 for n in niveles}
        if not niveles:
            return resultado
        stmt = (
            select(cierres_periodo.c.nota_definitiva)
            .join(asignaciones, asignaciones.c.id == cierres_periodo.c.asignacion_id)
            .where(
                cierres_periodo.c.asignacion_id == asignacion_id,
                cierres_periodo.c.periodo_id == periodo_id,
                asignaciones.c.grupo_id == grupo_id,
            )
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
        for row in rows:
            nota = row[0]
            for nivel in niveles:
                if nivel.nota_minima <= nota <= nivel.nota_maxima:
                    resultado[nivel.nombre] += 1
                    break
        return resultado

    def comparativo_periodos(
        self,
        grupo_id: int,
        asignacion_id: int,
        anio_id: int,
    ) -> list[dict[str, Any]]:
        cp_alias = cierres_periodo
        stmt = (
            select(
                periodos.c.id.label("periodo_id"),
                periodos.c.nombre.label("periodo_nombre"),
                periodos.c.numero.label("periodo_numero"),
                func.coalesce(func.avg(cp_alias.c.nota_definitiva), 0.0).label("promedio"),
            )
            .outerjoin(
                cp_alias,
                and_(
                    cp_alias.c.periodo_id == periodos.c.id,
                    cp_alias.c.asignacion_id == asignacion_id,
                ),
            )
            .outerjoin(
                asignaciones,
                and_(
                    asignaciones.c.id == cp_alias.c.asignacion_id,
                    asignaciones.c.grupo_id == grupo_id,
                ),
            )
            .where(periodos.c.anio_id == anio_id)
            .group_by(periodos.c.id)
            .order_by(periodos.c.numero.asc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            {
                "periodo_id": r["periodo_id"],
                "periodo_nombre": r["periodo_nombre"],
                "periodo_numero": r["periodo_numero"],
                "promedio": round(float(r["promedio"]), 2),
            }
            for r in rows
        ]

    def promedios_por_area(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                areas_conocimiento.c.nombre.label("area_nombre"),
                func.count(asignaciones.c.asignatura_id.distinct()).label("total_asignaturas"),
                func.coalesce(func.avg(cierres_periodo.c.nota_definitiva), 0.0).label("promedio"),
            )
            .join(asignaturas, asignaturas.c.area_id == areas_conocimiento.c.id)
            .join(asignaciones, and_(
                asignaciones.c.asignatura_id == asignaturas.c.id,
                asignaciones.c.grupo_id == grupo_id,
            ))
            .outerjoin(cierres_periodo, and_(
                cierres_periodo.c.asignacion_id == asignaciones.c.id,
                cierres_periodo.c.periodo_id == periodo_id,
            ))
            .group_by(areas_conocimiento.c.id)
            .order_by(func.coalesce(func.avg(cierres_periodo.c.nota_definitiva), 0.0).desc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            {
                "area_nombre": r["area_nombre"],
                "total_asignaturas": r["total_asignaturas"],
                "promedio": round(float(r["promedio"]), 2),
            }
            for r in rows
        ]

    def estudiantes_en_riesgo_academico(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
        min_asignaturas: int = 1,
    ) -> list[int]:
        stmt = (
            select(cierres_periodo.c.estudiante_id)
            .join(asignaciones, asignaciones.c.id == cierres_periodo.c.asignacion_id)
            .where(
                asignaciones.c.grupo_id == grupo_id,
                cierres_periodo.c.periodo_id == periodo_id,
                cierres_periodo.c.nota_definitiva < nota_minima,
            )
            .group_by(cierres_periodo.c.estudiante_id)
            .having(func.count() >= min_asignaturas)
            .order_by(cierres_periodo.c.estudiante_id)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
        return [r[0] for r in rows]

    def ranking_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        nombre_col = (estudiantes.c.nombre + " " + estudiantes.c.apellido).label("nombre_completo")
        stmt = (
            select(
                estudiantes.c.id.label("estudiante_id"),
                nombre_col,
                func.coalesce(func.avg(cierres_periodo.c.nota_definitiva), 0.0).label("promedio"),
            )
            .outerjoin(cierres_periodo, cierres_periodo.c.estudiante_id == estudiantes.c.id)
            .outerjoin(asignaciones, and_(
                asignaciones.c.id == cierres_periodo.c.asignacion_id,
                asignaciones.c.grupo_id == grupo_id,
                cierres_periodo.c.periodo_id == periodo_id,
            ))
            .where(
                estudiantes.c.grupo_id == grupo_id,
                estudiantes.c.estado_matricula == "activo",
            )
            .group_by(estudiantes.c.id)
            .order_by(func.coalesce(func.avg(cierres_periodo.c.nota_definitiva), 0.0).desc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            {
                "posicion": idx + 1,
                "estudiante_id": r["estudiante_id"],
                "nombre_completo": r["nombre_completo"],
                "promedio": round(float(r["promedio"]), 2),
            }
            for idx, r in enumerate(rows)
        ]

    # ------------------------------------------------------------------
    # Estadísticas de asistencia
    # ------------------------------------------------------------------

    def tendencia_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        semana_col = func.cast(func.strftime("%W", control_diario.c.fecha), Integer).label("semana")
        stmt = (
            select(
                semana_col,
                func.count().label("total"),
                func.sum(case(
                    (control_diario.c.estado.in_(["FI", "R"]), 1),
                    else_=0,
                )).label("ausencias"),
            )
            .where(
                control_diario.c.grupo_id == grupo_id,
                control_diario.c.asignacion_id == asignacion_id,
                control_diario.c.periodo_id == periodo_id,
            )
            .group_by(semana_col)
            .order_by(semana_col.asc())
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            {
                "semana": r["semana"],
                "porcentaje": round((1 - (r["ausencias"] or 0) / r["total"]) * 100, 1)
                if r["total"] and r["total"] > 0
                else 0.0,
            }
            for r in rows
        ]

    def distribucion_estados_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> dict[str, int]:
        stmt = (
            select(control_diario.c.estado, func.count().label("total"))
            .where(
                control_diario.c.grupo_id == grupo_id,
                control_diario.c.asignacion_id == asignacion_id,
                control_diario.c.periodo_id == periodo_id,
            )
            .group_by(control_diario.c.estado)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).fetchall()
        resultado = {"P": 0, "FJ": 0, "FI": 0, "R": 0, "E": 0}
        for r in rows:
            if r[0] in resultado:
                resultado[r[0]] = r[1]
        return resultado

    # ------------------------------------------------------------------
    # Consolidados para exportación
    # ------------------------------------------------------------------

    def consolidado_notas_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        nombre_col = (estudiantes.c.nombre + " " + estudiantes.c.apellido).label("nombre_completo")
        doc_col = (estudiantes.c.tipo_documento + " " + estudiantes.c.numero_documento).label("documento")

        with self._get_conn() as conn:
            # Estudiantes activos
            est_rows = conn.execute(
                select(estudiantes.c.id, nombre_col, doc_col)
                .where(
                    estudiantes.c.grupo_id == grupo_id,
                    estudiantes.c.estado_matricula == "activo",
                )
                .order_by(estudiantes.c.apellido, estudiantes.c.nombre)
            ).mappings().all()

            # Asignaturas del grupo en el periodo
            asig_rows = conn.execute(
                select(asignaciones.c.id.label("asignacion_id"), asignaturas.c.nombre.label("asignatura"))
                .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
                .where(
                    asignaciones.c.grupo_id == grupo_id,
                    asignaciones.c.periodo_id == periodo_id,
                    asignaciones.c.activo == True,  # noqa: E712
                )
                .distinct()
                .order_by(asignaturas.c.nombre)
            ).mappings().all()

            # Cierres de periodo
            cierre_rows = conn.execute(
                select(
                    cierres_periodo.c.estudiante_id,
                    cierres_periodo.c.asignacion_id,
                    cierres_periodo.c.nota_definitiva,
                )
                .join(asignaciones, asignaciones.c.id == cierres_periodo.c.asignacion_id)
                .where(
                    asignaciones.c.grupo_id == grupo_id,
                    cierres_periodo.c.periodo_id == periodo_id,
                )
            ).mappings().all()

        # Indexar cierres
        notas_idx: dict[tuple[int, int], float] = {
            (r["estudiante_id"], r["asignacion_id"]): r["nota_definitiva"]
            for r in cierre_rows
        }

        resultado = []
        for est in est_rows:
            fila: dict[str, Any] = {
                "estudiante_id": est["id"],
                "nombre_completo": est["nombre_completo"],
                "documento": est["documento"],
            }
            notas = []
            for asig in asig_rows:
                nota = notas_idx.get((est["id"], asig["asignacion_id"]))
                fila[asig["asignatura"]] = nota
                if nota is not None:
                    notas.append(nota)
            fila["promedio_periodo"] = round(sum(notas) / len(notas), 2) if notas else 0.0
            resultado.append(fila)
        return resultado

    def consolidado_asistencia_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        nombre_col = (estudiantes.c.nombre + " " + estudiantes.c.apellido).label("nombre_completo")
        stmt = (
            select(
                estudiantes.c.id.label("estudiante_id"),
                nombre_col,
                asignaturas.c.nombre.label("nombre_asignatura"),
                func.count().label("total"),
                func.sum(case((control_diario.c.estado == "P", 1), else_=0)).label("presentes"),
                func.sum(case((control_diario.c.estado == "FI", 1), else_=0)).label("faltas_injustificadas"),
                func.sum(case((control_diario.c.estado == "FJ", 1), else_=0)).label("faltas_justificadas"),
                func.sum(case((control_diario.c.estado == "R", 1), else_=0)).label("retrasos"),
                func.sum(case((control_diario.c.estado == "E", 1), else_=0)).label("excusas"),
            )
            .join(estudiantes, estudiantes.c.id == control_diario.c.estudiante_id)
            .join(asignaciones, asignaciones.c.id == control_diario.c.asignacion_id)
            .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
            .where(
                control_diario.c.grupo_id == grupo_id,
                control_diario.c.periodo_id == periodo_id,
            )
            .group_by(control_diario.c.estudiante_id, control_diario.c.asignacion_id)
            .order_by(estudiantes.c.apellido, estudiantes.c.nombre, asignaturas.c.nombre)
        )
        with self._get_conn() as conn:
            rows = conn.execute(stmt).mappings().all()
        resultado = []
        for r in rows:
            total = r["total"] or 0
            ausencias = (r["faltas_injustificadas"] or 0) + (r["retrasos"] or 0)
            pct = round((1 - ausencias / total) * 100, 1) if total > 0 else 0.0
            resultado.append({
                "estudiante_id": r["estudiante_id"],
                "nombre_completo": r["nombre_completo"],
                "nombre_asignatura": r["nombre_asignatura"],
                "presentes": r["presentes"] or 0,
                "faltas_injustificadas": r["faltas_injustificadas"] or 0,
                "faltas_justificadas": r["faltas_justificadas"] or 0,
                "retrasos": r["retrasos"] or 0,
                "excusas": r["excusas"] or 0,
                "porcentaje": pct,
            })
        return resultado

    def consolidado_anual_grupo(
        self,
        grupo_id: int,
        anio_id: int,
    ) -> list[dict[str, Any]]:
        nombre_col = (estudiantes.c.nombre + " " + estudiantes.c.apellido).label("nombre_completo")
        doc_col = (estudiantes.c.tipo_documento + " " + estudiantes.c.numero_documento).label("documento")

        with self._get_conn() as conn:
            # Estudiantes
            est_rows = conn.execute(
                select(estudiantes.c.id, nombre_col, doc_col)
                .where(
                    estudiantes.c.grupo_id == grupo_id,
                    estudiantes.c.estado_matricula == "activo",
                )
                .order_by(estudiantes.c.apellido, estudiantes.c.nombre)
            ).mappings().all()

            # Asignaturas del grupo en el año
            asig_rows = conn.execute(
                select(asignaciones.c.id.label("asignacion_id"), asignaturas.c.nombre.label("asignatura"))
                .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
                .join(periodos, and_(periodos.c.id == asignaciones.c.periodo_id, periodos.c.anio_id == anio_id))
                .where(
                    asignaciones.c.grupo_id == grupo_id,
                    asignaciones.c.activo == True,  # noqa: E712
                )
                .distinct()
                .order_by(asignaturas.c.nombre)
            ).mappings().all()

            # Cierres anuales
            cierre_rows = conn.execute(
                select(
                    cierres_anio.c.estudiante_id,
                    cierres_anio.c.asignacion_id,
                    cierres_anio.c.nota_definitiva_anual,
                    cierres_anio.c.perdio,
                )
                .join(asignaciones, asignaciones.c.id == cierres_anio.c.asignacion_id)
                .where(
                    cierres_anio.c.anio_id == anio_id,
                    asignaciones.c.grupo_id == grupo_id,
                )
            ).mappings().all()

            # Promociones
            promo_rows = conn.execute(
                select(promocion_anual.c.estudiante_id, promocion_anual.c.estado)
                .where(promocion_anual.c.anio_id == anio_id)
            ).mappings().all()

        notas_idx: dict[tuple[int, int], dict] = {
            (r["estudiante_id"], r["asignacion_id"]): {
                "nota": r["nota_definitiva_anual"],
                "perdio": bool(r["perdio"]),
            }
            for r in cierre_rows
        }
        promo_idx: dict[int, str] = {r["estudiante_id"]: r["estado"] for r in promo_rows}

        resultado = []
        for est in est_rows:
            fila: dict[str, Any] = {
                "estudiante_id": est["id"],
                "nombre_completo": est["nombre_completo"],
                "documento": est["documento"],
                "estado_promocion": promo_idx.get(est["id"], "pendiente"),
            }
            for asig in asig_rows:
                info = notas_idx.get((est["id"], asig["asignacion_id"]))
                fila[asig["asignatura"]] = info["nota"] if info else None
                fila[f"{asig['asignatura']}_perdio"] = info["perdio"] if info else None
            resultado.append(fila)
        return resultado

    # ------------------------------------------------------------------
    # Datos para boletines formales
    # ------------------------------------------------------------------

    def boletin_datos_periodo(
        self,
        estudiante_id: int,
        grupo_id: int,
        periodo_id: int,
    ) -> dict[str, Any]:
        with self._get_conn() as conn:
            est = conn.execute(
                select(
                    (estudiantes.c.nombre + " " + estudiantes.c.apellido).label("nombre"),
                    (estudiantes.c.tipo_documento + " " + estudiantes.c.numero_documento).label("documento"),
                    grupos.c.nombre.label("grupo_nombre"),
                    grupos.c.codigo.label("grupo_codigo"),
                    periodos.c.nombre.label("periodo_nombre"),
                )
                .join(grupos, grupos.c.id == estudiantes.c.grupo_id)
                .join(periodos, periodos.c.id == periodo_id)
                .where(estudiantes.c.id == estudiante_id)
            ).mappings().first()

            # Los LEFT JOINs llevan periodo_id y estudiante_id en el ON clause
            # (no en WHERE) para preservar la semántica OUTER: una asignación sin
            # cierre o sin registros de asistencia debe aparecer igual.
            # SQLAlchemy Core soporta esto con .outerjoin() + and_().
            stmt = (
                select(
                    areas_conocimiento.c.id.label("area_id"),
                    areas_conocimiento.c.nombre.label("area_nombre"),
                    asignaturas.c.nombre.label("asignatura_nombre"),
                    asignaciones.c.id.label("asignacion_id"),
                    cierres_periodo.c.nota_definitiva.label("nota"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "P", 1), else_=0)), 0).label("presentes"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "FI", 1), else_=0)), 0).label("faltas_injustificadas"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "FJ", 1), else_=0)), 0).label("faltas_justificadas"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "R", 1), else_=0)), 0).label("retrasos"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "E", 1), else_=0)), 0).label("excusas"),
                )
                .select_from(asignaciones)
                .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
                .join(areas_conocimiento, areas_conocimiento.c.id == asignaturas.c.area_id)
                .outerjoin(
                    cierres_periodo,
                    and_(
                        cierres_periodo.c.asignacion_id == asignaciones.c.id,
                        cierres_periodo.c.periodo_id == periodo_id,
                        cierres_periodo.c.estudiante_id == estudiante_id,
                    ),
                )
                .outerjoin(
                    control_diario,
                    and_(
                        control_diario.c.asignacion_id == asignaciones.c.id,
                        control_diario.c.periodo_id == periodo_id,
                        control_diario.c.estudiante_id == estudiante_id,
                    ),
                )
                .where(
                    asignaciones.c.grupo_id == grupo_id,
                    asignaciones.c.periodo_id == periodo_id,
                    asignaciones.c.activo == True,  # noqa: E712
                )
                .group_by(areas_conocimiento.c.id, asignaciones.c.id)
                .order_by(areas_conocimiento.c.nombre, asignaturas.c.nombre)
            )
            rows = conn.execute(stmt).mappings().all()

        # Agrupar por área
        areas: dict[int, dict] = {}
        for r in rows:
            aid = r["area_id"]
            if aid not in areas:
                areas[aid] = {"area_nombre": r["area_nombre"], "asignaturas": []}
            areas[aid]["asignaturas"].append({
                "nombre": r["asignatura_nombre"],
                "nota": r["nota"],
                "presentes": r["presentes"],
                "faltas_injustificadas": r["faltas_injustificadas"],
                "faltas_justificadas": r["faltas_justificadas"],
                "retrasos": r["retrasos"],
                "excusas": r["excusas"],
            })

        return {
            "estudiante": {
                "nombre": est["nombre"] if est else f"Estudiante {estudiante_id}",
                "documento": est["documento"] if est else "",
                "grupo": (est["grupo_nombre"] or est["grupo_codigo"]) if est else "",
                "periodo": est["periodo_nombre"] if est else str(periodo_id),
            },
            "areas": list(areas.values()),
        }

    def boletin_datos_acumulado(
        self,
        estudiante_id: int,
        grupo_id: int,
        hasta_periodo_id: int,
    ) -> dict[str, Any]:
        with self._get_conn() as conn:
            meta_per = conn.execute(
                select(periodos.c.anio_id, periodos.c.numero)
                .where(periodos.c.id == hasta_periodo_id)
            ).mappings().first()
            if not meta_per:
                return {"estudiante": {}, "periodos": [], "areas": [], "es_ultimo_periodo": False}
            anio_id = meta_per["anio_id"]
            numero_max = meta_per["numero"]

            total_per_anio = conn.execute(
                select(func.count()).where(
                    periodos.c.anio_id == anio_id
                )
            ).scalar() or 0
            es_ultimo = numero_max >= total_per_anio

            # Datos del estudiante y grupo
            est = conn.execute(
                select(
                    (estudiantes.c.nombre + " " + estudiantes.c.apellido).label("nombre"),
                    (estudiantes.c.tipo_documento + " " + estudiantes.c.numero_documento).label("documento"),
                    grupos.c.nombre.label("grupo_nombre"),
                    grupos.c.codigo.label("grupo_codigo"),
                )
                .join(grupos, grupos.c.id == estudiantes.c.grupo_id)
                .where(estudiantes.c.id == estudiante_id)
            ).mappings().first()

            # Periodos del año hasta el actual
            per_rows = conn.execute(
                select(periodos.c.id, periodos.c.nombre, periodos.c.numero)
                .where(periodos.c.anio_id == anio_id, periodos.c.numero <= numero_max)
                .order_by(periodos.c.numero.asc())
            ).mappings().all()

            per_actual = next(
                (p for p in per_rows if p["id"] == hasta_periodo_id),
                per_rows[-1] if per_rows else None,
            )
            periodo_ids = [p["id"] for p in per_rows]

            if not periodo_ids:
                return {"estudiante": {}, "periodos": [], "areas": [], "es_ultimo_periodo": es_ultimo}

            # Asignaturas únicas por área en el año
            asig_rows = conn.execute(
                select(
                    areas_conocimiento.c.id.label("area_id"),
                    areas_conocimiento.c.nombre.label("area_nombre"),
                    asignaturas.c.id.label("asig_id"),
                    asignaturas.c.nombre.label("asig_nombre"),
                )
                .join(asignaturas, asignaturas.c.area_id == areas_conocimiento.c.id)
                .join(asignaciones, asignaciones.c.asignatura_id == asignaturas.c.id)
                .join(periodos, and_(periodos.c.id == asignaciones.c.periodo_id, periodos.c.anio_id == anio_id, periodos.c.numero <= numero_max))
                .where(asignaciones.c.grupo_id == grupo_id, asignaciones.c.activo == True)  # noqa: E712
                .distinct()
                .order_by(areas_conocimiento.c.nombre, asignaturas.c.nombre)
            ).mappings().all()

            # Notas por periodo
            notas_rows = conn.execute(
                select(
                    asignaturas.c.id.label("asig_id"),
                    cierres_periodo.c.periodo_id,
                    cierres_periodo.c.nota_definitiva,
                )
                .join(asignaciones, and_(
                    asignaciones.c.id == cierres_periodo.c.asignacion_id,
                    asignaciones.c.grupo_id == grupo_id,
                ))
                .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
                .where(
                    cierres_periodo.c.estudiante_id == estudiante_id,
                    cierres_periodo.c.periodo_id.in_(periodo_ids),
                )
            ).mappings().all()

            # Asistencia acumulada
            asist_rows = conn.execute(
                select(
                    asignaturas.c.id.label("asig_id"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "P", 1), else_=0)), 0).label("presentes"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "FI", 1), else_=0)), 0).label("faltas_injustificadas"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "FJ", 1), else_=0)), 0).label("faltas_justificadas"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "R", 1), else_=0)), 0).label("retrasos"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "E", 1), else_=0)), 0).label("excusas"),
                )
                .join(asignaciones, and_(
                    asignaciones.c.id == control_diario.c.asignacion_id,
                    asignaciones.c.grupo_id == grupo_id,
                ))
                .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
                .where(
                    control_diario.c.estudiante_id == estudiante_id,
                    control_diario.c.periodo_id.in_(periodo_ids),
                )
                .group_by(asignaturas.c.id)
            ).mappings().all()

        notas_idx: dict[tuple[int, int], float | None] = {
            (r["asig_id"], r["periodo_id"]): r["nota_definitiva"] for r in notas_rows
        }
        asist_idx: dict[int, dict] = {r["asig_id"]: dict(r) for r in asist_rows}
        periodos_list = [{"id": p["id"], "nombre": p["nombre"], "numero": p["numero"]} for p in per_rows]

        areas: dict[int, dict] = {}
        for r in asig_rows:
            aid = r["area_id"]
            if aid not in areas:
                areas[aid] = {"area_nombre": r["area_nombre"], "asignaturas": []}
            sid = r["asig_id"]
            notas_p = {pid: notas_idx.get((sid, pid)) for pid in periodo_ids}
            notas_validas = [v for v in notas_p.values() if v is not None]
            definitiva = round(sum(notas_validas) / len(notas_validas), 1) if notas_validas else None
            asist = asist_idx.get(sid, {})
            areas[aid]["asignaturas"].append({
                "nombre": r["asig_nombre"],
                "notas_periodo": notas_p,
                "definitiva": definitiva,
                "presentes": asist.get("presentes", 0),
                "faltas_injustificadas": asist.get("faltas_injustificadas", 0),
                "faltas_justificadas": asist.get("faltas_justificadas", 0),
                "retrasos": asist.get("retrasos", 0),
                "excusas": asist.get("excusas", 0),
            })

        return {
            "estudiante": {
                "nombre": est["nombre"] if est else f"Estudiante {estudiante_id}",
                "documento": est["documento"] if est else "",
                "grupo": (est["grupo_nombre"] or est["grupo_codigo"]) if est else "",
                "periodo": per_actual["nombre"] if per_actual else str(hasta_periodo_id),
                "anio": anio_id,
            },
            "periodos": periodos_list,
            "areas": list(areas.values()),
            "es_ultimo_periodo": bool(es_ultimo),
        }

    def boletin_datos_anual(
        self,
        estudiante_id: int,
        grupo_id: int,
        anio_id: int,
    ) -> dict[str, Any]:
        with self._get_conn() as conn:
            est = conn.execute(
                select(
                    (estudiantes.c.nombre + " " + estudiantes.c.apellido).label("nombre"),
                    (estudiantes.c.tipo_documento + " " + estudiantes.c.numero_documento).label("documento"),
                    grupos.c.nombre.label("grupo_nombre"),
                    grupos.c.codigo.label("grupo_codigo"),
                )
                .join(grupos, grupos.c.id == estudiantes.c.grupo_id)
                .where(estudiantes.c.id == estudiante_id)
            ).mappings().first()

            per_rows = conn.execute(
                select(periodos.c.id, periodos.c.nombre, periodos.c.numero)
                .where(periodos.c.anio_id == anio_id)
                .order_by(periodos.c.numero.asc())
            ).mappings().all()

            asig_rows = conn.execute(
                select(
                    areas_conocimiento.c.id.label("area_id"),
                    areas_conocimiento.c.nombre.label("area_nombre"),
                    asignaturas.c.id.label("asig_id"),
                    asignaturas.c.nombre.label("asig_nombre"),
                )
                .join(asignaturas, asignaturas.c.area_id == areas_conocimiento.c.id)
                .join(asignaciones, asignaciones.c.asignatura_id == asignaturas.c.id)
                .join(periodos, and_(periodos.c.id == asignaciones.c.periodo_id, periodos.c.anio_id == anio_id))
                .where(asignaciones.c.grupo_id == grupo_id, asignaciones.c.activo == True)  # noqa: E712
                .distinct()
                .order_by(areas_conocimiento.c.nombre, asignaturas.c.nombre)
            ).mappings().all()

            periodo_ids = [p["id"] for p in per_rows]

            notas_rows = conn.execute(
                select(
                    asignaturas.c.id.label("asig_id"),
                    cierres_periodo.c.periodo_id,
                    cierres_periodo.c.nota_definitiva,
                )
                .join(asignaciones, and_(
                    asignaciones.c.id == cierres_periodo.c.asignacion_id,
                    asignaciones.c.grupo_id == grupo_id,
                ))
                .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
                .join(periodos, and_(periodos.c.id == cierres_periodo.c.periodo_id, periodos.c.anio_id == anio_id))
                .where(cierres_periodo.c.estudiante_id == estudiante_id)
            ).mappings().all()

            asist_rows = conn.execute(
                select(
                    asignaturas.c.id.label("asig_id"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "P", 1), else_=0)), 0).label("presentes"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "FI", 1), else_=0)), 0).label("faltas_injustificadas"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "FJ", 1), else_=0)), 0).label("faltas_justificadas"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "R", 1), else_=0)), 0).label("retrasos"),
                    func.coalesce(func.sum(case((control_diario.c.estado == "E", 1), else_=0)), 0).label("excusas"),
                )
                .join(asignaciones, and_(
                    asignaciones.c.id == control_diario.c.asignacion_id,
                    asignaciones.c.grupo_id == grupo_id,
                ))
                .join(asignaturas, asignaturas.c.id == asignaciones.c.asignatura_id)
                .join(periodos, and_(periodos.c.id == control_diario.c.periodo_id, periodos.c.anio_id == anio_id))
                .where(control_diario.c.estudiante_id == estudiante_id)
                .group_by(asignaturas.c.id)
            ).mappings().all()

            promo = conn.execute(
                select(promocion_anual.c.estado)
                .where(
                    promocion_anual.c.anio_id == anio_id,
                    promocion_anual.c.estudiante_id == estudiante_id,
                )
            ).mappings().first()

        notas_idx: dict[tuple[int, int], float | None] = {
            (r["asig_id"], r["periodo_id"]): r["nota_definitiva"] for r in notas_rows
        }
        asist_idx: dict[int, dict] = {r["asig_id"]: dict(r) for r in asist_rows}
        periodos_list = [{"id": p["id"], "nombre": p["nombre"], "numero": p["numero"]} for p in per_rows]

        areas: dict[int, dict] = {}
        for r in asig_rows:
            aid = r["area_id"]
            if aid not in areas:
                areas[aid] = {"area_nombre": r["area_nombre"], "asignaturas": []}
            sid = r["asig_id"]
            notas_p = {pid: notas_idx.get((sid, pid)) for pid in periodo_ids}
            notas_validas = [v for v in notas_p.values() if v is not None]
            definitiva = round(sum(notas_validas) / len(notas_validas), 1) if notas_validas else None
            asist = asist_idx.get(sid, {})
            areas[aid]["asignaturas"].append({
                "nombre": r["asig_nombre"],
                "notas_periodo": notas_p,
                "definitiva": definitiva,
                "presentes": asist.get("presentes", 0),
                "faltas_injustificadas": asist.get("faltas_injustificadas", 0),
                "faltas_justificadas": asist.get("faltas_justificadas", 0),
                "retrasos": asist.get("retrasos", 0),
                "excusas": asist.get("excusas", 0),
            })

        return {
            "estudiante": {
                "nombre": est["nombre"] if est else f"Estudiante {estudiante_id}",
                "documento": est["documento"] if est else "",
                "grupo": (est["grupo_nombre"] or est["grupo_codigo"]) if est else "",
                "anio": anio_id,
                "estado_promocion": promo["estado"] if promo else "pendiente",
            },
            "periodos": periodos_list,
            "areas": list(areas.values()),
        }


__all__ = ["SqlaEstadisticosRepository"]
