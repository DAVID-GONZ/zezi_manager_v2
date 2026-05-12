"""
SqliteEstadisticosRepository — implementación SQLite de IEstadisticosRepository.

Este repositorio es estrictamente de solo lectura: solo SELECT y agregaciones.
No hace INSERT, UPDATE ni DELETE.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any

from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.domain.models.configuracion import NivelDesempeno
from src.domain.models.dtos import DashboardMetricsDTO


class SqliteEstadisticosRepository(IEstadisticosRepository):

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
            row_est = conn.execute(
                """
                SELECT COUNT(*) FROM estudiantes
                WHERE grupo_id = ? AND estado_matricula = 'activo'
                """,
                (grupo_id,),
            ).fetchone()
            total_estudiantes = int(row_est[0])

            # Promedio general (avg de cierres_periodo del grupo/periodo)
            row_prom = conn.execute(
                """
                SELECT COALESCE(AVG(cp.nota_definitiva), 0)
                FROM cierres_periodo cp
                JOIN asignaciones a ON a.id = cp.asignacion_id
                WHERE a.grupo_id = ? AND cp.periodo_id = ?
                """,
                (grupo_id, periodo_id),
            ).fetchone()
            promedio_general = round(float(row_prom[0]), 2)
            promedio_general = max(0.0, min(100.0, promedio_general))

            # Porcentaje de asistencia global
            row_asist = conn.execute(
                """
                SELECT
                    COUNT(*)                                        AS total,
                    SUM(CASE WHEN estado IN ('FI','R') THEN 1 ELSE 0 END) AS ausencias
                FROM control_diario
                WHERE grupo_id = ? AND periodo_id = ?
                """,
                (grupo_id, periodo_id),
            ).fetchone()
            if row_asist and row_asist["total"] > 0:
                pct = round((1 - row_asist["ausencias"] / row_asist["total"]) * 100, 2)
                pct_asistencia = max(0.0, min(100.0, pct))
            else:
                pct_asistencia = 0.0

            # Estudiantes en riesgo (con promedio < nota_minima en al menos 1 asignatura)
            row_riesgo = conn.execute(
                """
                SELECT COUNT(DISTINCT cp.estudiante_id)
                FROM cierres_periodo cp
                JOIN asignaciones a ON a.id = cp.asignacion_id
                WHERE a.grupo_id = ? AND cp.periodo_id = ?
                  AND cp.nota_definitiva < ?
                """,
                (grupo_id, periodo_id, nota_minima),
            ).fetchone()
            estudiantes_en_riesgo = int(row_riesgo[0])

            # Actividades publicadas (estado publicada o cerrada)
            row_acts = conn.execute(
                """
                SELECT COUNT(DISTINCT act.id)
                FROM actividades act
                JOIN categorias c ON c.id = act.categoria_id
                JOIN asignaciones a ON a.id = c.asignacion_id
                WHERE a.grupo_id = ? AND c.periodo_id = ?
                  AND act.estado IN ('publicada', 'cerrada')
                """,
                (grupo_id, periodo_id),
            ).fetchone()
            actividades_publicadas = int(row_acts[0])

            # Alertas pendientes
            row_alertas = conn.execute(
                """
                SELECT COUNT(*) FROM alertas al
                JOIN estudiantes e ON e.id = al.estudiante_id
                WHERE e.grupo_id = ? AND al.resuelta = 0
                """,
                (grupo_id,),
            ).fetchone()
            alertas_pendientes = int(row_alertas[0])

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
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(AVG(cp.nota_definitiva), 0)
                FROM cierres_periodo cp
                JOIN asignaciones a ON a.id = cp.asignacion_id
                WHERE a.grupo_id = ? AND cp.periodo_id = ?
                """,
                (grupo_id, periodo_id),
            ).fetchone()
            return round(float(row[0]), 2)

    def porcentaje_asistencia_global(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> float:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                                        AS total,
                    SUM(CASE WHEN estado IN ('FI','R') THEN 1 ELSE 0 END) AS ausencias
                FROM control_diario
                WHERE grupo_id = ? AND periodo_id = ?
                """,
                (grupo_id, periodo_id),
            ).fetchone()
            if not row or row["total"] == 0:
                return 0.0
            return round((1 - row["ausencias"] / row["total"]) * 100, 2)

    def contar_alertas_pendientes(self, grupo_id: int) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM alertas al
                JOIN estudiantes e ON e.id = al.estudiante_id
                WHERE e.grupo_id = ? AND al.resuelta = 0
                """,
                (grupo_id,),
            ).fetchone()
            return int(row[0])

    # ------------------------------------------------------------------
    # Estadísticas de notas
    # ------------------------------------------------------------------

    def promedio_por_asignacion(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(AVG(nota_definitiva), 0)
                FROM cierres_periodo
                WHERE asignacion_id = ? AND periodo_id = ?
                """,
                (asignacion_id, periodo_id),
            ).fetchone()
            return round(float(row[0]), 2)

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
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT nota_definitiva
                FROM cierres_periodo cp
                JOIN asignaciones a ON a.id = cp.asignacion_id
                WHERE cp.asignacion_id = ? AND cp.periodo_id = ?
                  AND a.grupo_id = ?
                """,
                (asignacion_id, periodo_id, grupo_id),
            ).fetchall()
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
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.id        AS periodo_id,
                    p.nombre    AS periodo_nombre,
                    p.numero    AS periodo_numero,
                    COALESCE(AVG(cp.nota_definitiva), 0) AS promedio
                FROM periodos p
                LEFT JOIN cierres_periodo cp
                    ON cp.periodo_id = p.id AND cp.asignacion_id = ?
                LEFT JOIN asignaciones a
                    ON a.id = cp.asignacion_id AND a.grupo_id = ?
                WHERE p.anio_id = ?
                GROUP BY p.id
                ORDER BY p.numero ASC
                """,
                (asignacion_id, grupo_id, anio_id),
            ).fetchall()
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
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    ar.nombre                            AS area_nombre,
                    COUNT(DISTINCT a.asignatura_id)      AS total_asignaturas,
                    COALESCE(AVG(cp.nota_definitiva), 0) AS promedio
                FROM areas_conocimiento ar
                JOIN asignaturas s ON s.area_id = ar.id
                JOIN asignaciones a ON a.asignatura_id = s.id AND a.grupo_id = ?
                LEFT JOIN cierres_periodo cp
                    ON cp.asignacion_id = a.id AND cp.periodo_id = ?
                GROUP BY ar.id
                ORDER BY promedio DESC
                """,
                (grupo_id, periodo_id),
            ).fetchall()
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
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT cp.estudiante_id
                FROM cierres_periodo cp
                JOIN asignaciones a ON a.id = cp.asignacion_id
                WHERE a.grupo_id = ? AND cp.periodo_id = ?
                  AND cp.nota_definitiva < ?
                GROUP BY cp.estudiante_id
                HAVING COUNT(*) >= ?
                ORDER BY cp.estudiante_id
                """,
                (grupo_id, periodo_id, nota_minima, min_asignaturas),
            ).fetchall()
            return [r["estudiante_id"] for r in rows]

    def ranking_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    e.id AS estudiante_id,
                    e.nombre || ' ' || e.apellido AS nombre_completo,
                    COALESCE(AVG(cp.nota_definitiva), 0) AS promedio
                FROM estudiantes e
                LEFT JOIN cierres_periodo cp ON cp.estudiante_id = e.id
                LEFT JOIN asignaciones a ON a.id = cp.asignacion_id
                    AND a.grupo_id = ? AND cp.periodo_id = ?
                WHERE e.grupo_id = ? AND e.estado_matricula = 'activo'
                GROUP BY e.id
                ORDER BY promedio DESC
                """,
                (grupo_id, periodo_id, grupo_id),
            ).fetchall()
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
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    CAST(strftime('%W', fecha) AS INTEGER)          AS semana,
                    COUNT(*)                                        AS total,
                    SUM(CASE WHEN estado IN ('FI','R') THEN 1 ELSE 0 END) AS ausencias
                FROM control_diario
                WHERE grupo_id = ? AND asignacion_id = ? AND periodo_id = ?
                GROUP BY semana
                ORDER BY semana ASC
                """,
                (grupo_id, asignacion_id, periodo_id),
            ).fetchall()
            return [
                {
                    "semana": r["semana"],
                    "porcentaje": round(
                        (1 - r["ausencias"] / r["total"]) * 100, 1
                    ) if r["total"] > 0 else 0.0,
                }
                for r in rows
            ]

    def distribucion_estados_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> dict[str, int]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT estado, COUNT(*) AS total
                FROM control_diario
                WHERE grupo_id = ? AND asignacion_id = ? AND periodo_id = ?
                GROUP BY estado
                """,
                (grupo_id, asignacion_id, periodo_id),
            ).fetchall()
        resultado = {"P": 0, "FJ": 0, "FI": 0, "R": 0, "E": 0}
        for r in rows:
            if r["estado"] in resultado:
                resultado[r["estado"]] = r["total"]
        return resultado

    # ------------------------------------------------------------------
    # Consolidados para exportación
    # ------------------------------------------------------------------

    def consolidado_notas_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            # Estudiantes activos
            estudiantes = conn.execute(
                """
                SELECT id, nombre || ' ' || apellido AS nombre_completo,
                       tipo_documento || ' ' || numero_documento AS documento
                FROM estudiantes
                WHERE grupo_id = ? AND estado_matricula = 'activo'
                ORDER BY apellido, nombre
                """,
                (grupo_id,),
            ).fetchall()

            # Asignaturas del grupo en el periodo
            asignaturas = conn.execute(
                """
                SELECT DISTINCT a.id AS asignacion_id, s.nombre AS asignatura
                FROM asignaciones a
                JOIN asignaturas s ON s.id = a.asignatura_id
                WHERE a.grupo_id = ? AND a.periodo_id = ? AND a.activo = 1
                ORDER BY s.nombre
                """,
                (grupo_id, periodo_id),
            ).fetchall()

            # Cierres de periodo
            cierres = conn.execute(
                """
                SELECT cp.estudiante_id, cp.asignacion_id, cp.nota_definitiva
                FROM cierres_periodo cp
                JOIN asignaciones a ON a.id = cp.asignacion_id
                WHERE a.grupo_id = ? AND cp.periodo_id = ?
                """,
                (grupo_id, periodo_id),
            ).fetchall()

        # Indexar cierres por (estudiante_id, asignacion_id)
        notas_idx: dict[tuple[int, int], float] = {
            (r["estudiante_id"], r["asignacion_id"]): r["nota_definitiva"]
            for r in cierres
        }

        resultado = []
        for est in estudiantes:
            fila: dict[str, Any] = {
                "estudiante_id": est["id"],
                "nombre_completo": est["nombre_completo"],
                "documento": est["documento"],
            }
            notas = []
            for asig in asignaturas:
                nota = notas_idx.get((est["id"], asig["asignacion_id"]), None)
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
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    e.id            AS estudiante_id,
                    e.nombre || ' ' || e.apellido AS nombre_completo,
                    s.nombre        AS nombre_asignatura,
                    COUNT(*)        AS total,
                    SUM(CASE WHEN cd.estado = 'P'  THEN 1 ELSE 0 END) AS presentes,
                    SUM(CASE WHEN cd.estado = 'FI' THEN 1 ELSE 0 END) AS faltas_injustificadas,
                    SUM(CASE WHEN cd.estado = 'FJ' THEN 1 ELSE 0 END) AS faltas_justificadas,
                    SUM(CASE WHEN cd.estado = 'R'  THEN 1 ELSE 0 END) AS retrasos,
                    SUM(CASE WHEN cd.estado = 'E'  THEN 1 ELSE 0 END) AS excusas
                FROM control_diario cd
                JOIN estudiantes e ON e.id = cd.estudiante_id
                JOIN asignaciones a ON a.id = cd.asignacion_id
                JOIN asignaturas s ON s.id = a.asignatura_id
                WHERE cd.grupo_id = ? AND cd.periodo_id = ?
                GROUP BY cd.estudiante_id, cd.asignacion_id
                ORDER BY e.apellido, e.nombre, s.nombre
                """,
                (grupo_id, periodo_id),
            ).fetchall()
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
        with self._get_conn() as conn:
            # Estudiantes
            estudiantes = conn.execute(
                """
                SELECT id, nombre || ' ' || apellido AS nombre_completo,
                       tipo_documento || ' ' || numero_documento AS documento
                FROM estudiantes
                WHERE grupo_id = ? AND estado_matricula = 'activo'
                ORDER BY apellido, nombre
                """,
                (grupo_id,),
            ).fetchall()

            # Asignaturas del grupo en el año
            asignaturas = conn.execute(
                """
                SELECT DISTINCT a.id AS asignacion_id, s.nombre AS asignatura
                FROM asignaciones a
                JOIN asignaturas s ON s.id = a.asignatura_id
                JOIN periodos p ON p.id = a.periodo_id AND p.anio_id = ?
                WHERE a.grupo_id = ? AND a.activo = 1
                ORDER BY s.nombre
                """,
                (anio_id, grupo_id),
            ).fetchall()

            # Cierres anuales
            cierres_anio = conn.execute(
                """
                SELECT ca.estudiante_id, ca.asignacion_id,
                       ca.nota_definitiva_anual, ca.perdio
                FROM cierres_anio ca
                JOIN asignaciones a ON a.id = ca.asignacion_id
                WHERE ca.anio_id = ? AND a.grupo_id = ?
                """,
                (anio_id, grupo_id),
            ).fetchall()

            # Promociones
            promociones = conn.execute(
                """
                SELECT estudiante_id, estado
                FROM promocion_anual
                WHERE anio_id = ?
                """,
                (anio_id,),
            ).fetchall()

        notas_idx: dict[tuple[int, int], dict] = {
            (r["estudiante_id"], r["asignacion_id"]): {
                "nota": r["nota_definitiva_anual"],
                "perdio": bool(r["perdio"]),
            }
            for r in cierres_anio
        }
        promo_idx: dict[int, str] = {r["estudiante_id"]: r["estado"] for r in promociones}

        resultado = []
        for est in estudiantes:
            fila: dict[str, Any] = {
                "estudiante_id": est["id"],
                "nombre_completo": est["nombre_completo"],
                "documento": est["documento"],
                "estado_promocion": promo_idx.get(est["id"], "pendiente"),
            }
            for asig in asignaturas:
                info = notas_idx.get((est["id"], asig["asignacion_id"]))
                fila[asig["asignatura"]] = info["nota"] if info else None
                fila[f"{asig['asignatura']}_perdio"] = info["perdio"] if info else None
            resultado.append(fila)
        return resultado


__all__ = ["SqliteEstadisticosRepository"]
