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
            # Datos del estudiante, grupo y periodo
            est = conn.execute(
                """
                SELECT e.nombre || ' ' || e.apellido AS nombre,
                       e.tipo_documento || ' ' || e.numero_documento AS documento,
                       g.nombre AS grupo_nombre, g.codigo AS grupo_codigo,
                       p.nombre AS periodo_nombre
                FROM estudiantes e
                JOIN grupos g ON g.id = e.grupo_id
                JOIN periodos p ON p.id = ?
                WHERE e.id = ?
                """,
                (periodo_id, estudiante_id),
            ).fetchone()

            # Asignaturas con área + nota + asistencia para ese estudiante/periodo
            rows = conn.execute(
                """
                SELECT
                    ar.id   AS area_id,
                    ar.nombre AS area_nombre,
                    s.nombre  AS asignatura_nombre,
                    a.id      AS asignacion_id,
                    cp.nota_definitiva AS nota,
                    COALESCE(SUM(CASE WHEN cd.estado='P'  THEN 1 ELSE 0 END), 0) AS presentes,
                    COALESCE(SUM(CASE WHEN cd.estado='FI' THEN 1 ELSE 0 END), 0) AS faltas_injustificadas,
                    COALESCE(SUM(CASE WHEN cd.estado='FJ' THEN 1 ELSE 0 END), 0) AS faltas_justificadas,
                    COALESCE(SUM(CASE WHEN cd.estado='R'  THEN 1 ELSE 0 END), 0) AS retrasos,
                    COALESCE(SUM(CASE WHEN cd.estado='E'  THEN 1 ELSE 0 END), 0) AS excusas
                FROM asignaciones a
                JOIN asignaturas s  ON s.id  = a.asignatura_id
                JOIN areas_conocimiento ar ON ar.id = s.area_id
                LEFT JOIN cierres_periodo cp
                    ON cp.asignacion_id = a.id
                    AND cp.periodo_id   = ?
                    AND cp.estudiante_id = ?
                LEFT JOIN control_diario cd
                    ON cd.asignacion_id  = a.id
                    AND cd.periodo_id    = ?
                    AND cd.estudiante_id = ?
                WHERE a.grupo_id   = ?
                  AND a.periodo_id = ?
                  AND a.activo     = 1
                GROUP BY ar.id, a.id
                ORDER BY ar.nombre, s.nombre
                """,
                (
                    periodo_id, estudiante_id,
                    periodo_id, estudiante_id,
                    grupo_id, periodo_id,
                ),
            ).fetchall()

        # Agrupar por área
        areas: dict[int, dict] = {}
        for r in rows:
            aid = r["area_id"]
            if aid not in areas:
                areas[aid] = {"area_nombre": r["area_nombre"], "asignaturas": []}
            areas[aid]["asignaturas"].append({
                "nombre":               r["asignatura_nombre"],
                "nota":                 r["nota"],
                "presentes":            r["presentes"],
                "faltas_injustificadas": r["faltas_injustificadas"],
                "faltas_justificadas":  r["faltas_justificadas"],
                "retrasos":             r["retrasos"],
                "excusas":              r["excusas"],
            })

        return {
            "estudiante": {
                "nombre":   est["nombre"]  if est else f"Estudiante {estudiante_id}",
                "documento": est["documento"] if est else "",
                "grupo":    (est["grupo_nombre"] or est["grupo_codigo"]) if est else "",
                "periodo":  est["periodo_nombre"] if est else str(periodo_id),
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
            # Datos básicos del periodo destino (anio_id, numero, total periodos del año)
            meta_per = conn.execute(
                "SELECT anio_id, numero FROM periodos WHERE id = ?",
                (hasta_periodo_id,),
            ).fetchone()
            if not meta_per:
                return {"estudiante": {}, "periodos": [], "areas": [],
                        "es_ultimo_periodo": False}
            anio_id    = meta_per["anio_id"]
            numero_max = meta_per["numero"]

            total_per_anio = conn.execute(
                "SELECT COUNT(*) FROM periodos WHERE anio_id = ?",
                (anio_id,),
            ).fetchone()[0]
            es_ultimo = (numero_max >= total_per_anio)

            # Datos del estudiante y grupo
            est = conn.execute(
                """
                SELECT e.nombre || ' ' || e.apellido AS nombre,
                       e.tipo_documento || ' ' || e.numero_documento AS documento,
                       g.nombre AS grupo_nombre, g.codigo AS grupo_codigo
                FROM estudiantes e
                JOIN grupos g ON g.id = e.grupo_id
                WHERE e.id = ?
                """,
                (estudiante_id,),
            ).fetchone()

            # Periodos del año hasta el actual
            periodos = conn.execute(
                """
                SELECT id, nombre, numero FROM periodos
                WHERE anio_id = ? AND numero <= ?
                ORDER BY numero ASC
                """,
                (anio_id, numero_max),
            ).fetchall()

            # Nombre del periodo actual para la ficha
            per_actual = next((p for p in periodos if p["id"] == hasta_periodo_id), periodos[-1])

            # Asignaturas únicas por área en el año
            asigs = conn.execute(
                """
                SELECT DISTINCT
                    ar.id AS area_id, ar.nombre AS area_nombre,
                    s.id  AS asig_id, s.nombre  AS asig_nombre
                FROM asignaciones a
                JOIN asignaturas s ON s.id = a.asignatura_id
                JOIN areas_conocimiento ar ON ar.id = s.area_id
                JOIN periodos p ON p.id = a.periodo_id AND p.anio_id = ? AND p.numero <= ?
                WHERE a.grupo_id = ? AND a.activo = 1
                ORDER BY ar.nombre, s.nombre
                """,
                (anio_id, numero_max, grupo_id),
            ).fetchall()

            # Notas por periodo (asignatura_id → periodo_id → nota)
            periodo_ids_sql = ",".join("?" * len(periodos))
            notas_rows = conn.execute(
                f"""
                SELECT s.id AS asig_id, cp.periodo_id, cp.nota_definitiva
                FROM cierres_periodo cp
                JOIN asignaciones a ON a.id = cp.asignacion_id AND a.grupo_id = ?
                JOIN asignaturas s  ON s.id = a.asignatura_id
                WHERE cp.estudiante_id = ?
                  AND cp.periodo_id IN ({periodo_ids_sql})
                """,
                (grupo_id, estudiante_id, *[p["id"] for p in periodos]),
            ).fetchall()

            # Asistencia acumulada por asignatura (todos los periodos incluidos)
            asist_rows = conn.execute(
                f"""
                SELECT s.id AS asig_id,
                    COALESCE(SUM(CASE WHEN cd.estado='P'  THEN 1 ELSE 0 END), 0) AS presentes,
                    COALESCE(SUM(CASE WHEN cd.estado='FI' THEN 1 ELSE 0 END), 0) AS faltas_injustificadas,
                    COALESCE(SUM(CASE WHEN cd.estado='FJ' THEN 1 ELSE 0 END), 0) AS faltas_justificadas,
                    COALESCE(SUM(CASE WHEN cd.estado='R'  THEN 1 ELSE 0 END), 0) AS retrasos,
                    COALESCE(SUM(CASE WHEN cd.estado='E'  THEN 1 ELSE 0 END), 0) AS excusas
                FROM control_diario cd
                JOIN asignaciones a ON a.id = cd.asignacion_id AND a.grupo_id = ?
                JOIN asignaturas s  ON s.id = a.asignatura_id
                WHERE cd.estudiante_id = ?
                  AND cd.periodo_id IN ({periodo_ids_sql})
                GROUP BY s.id
                """,
                (grupo_id, estudiante_id, *[p["id"] for p in periodos]),
            ).fetchall()

        notas_idx: dict[tuple[int, int], float | None] = {
            (r["asig_id"], r["periodo_id"]): r["nota_definitiva"]
            for r in notas_rows
        }
        asist_idx: dict[int, dict] = {r["asig_id"]: dict(r) for r in asist_rows}
        periodos_list = [
            {"id": p["id"], "nombre": p["nombre"], "numero": p["numero"]}
            for p in periodos
        ]
        periodo_ids = [p["id"] for p in periodos_list]

        areas: dict[int, dict] = {}
        for r in asigs:
            aid = r["area_id"]
            if aid not in areas:
                areas[aid] = {"area_nombre": r["area_nombre"], "asignaturas": []}
            sid = r["asig_id"]
            notas_p = {pid: notas_idx.get((sid, pid)) for pid in periodo_ids}
            notas_validas = [v for v in notas_p.values() if v is not None]
            definitiva = round(sum(notas_validas) / len(notas_validas), 1) if notas_validas else None
            asist = asist_idx.get(sid, {})
            areas[aid]["asignaturas"].append({
                "nombre":                r["asig_nombre"],
                "notas_periodo":         notas_p,
                "definitiva":            definitiva,
                "presentes":             asist.get("presentes", 0),
                "faltas_injustificadas": asist.get("faltas_injustificadas", 0),
                "faltas_justificadas":   asist.get("faltas_justificadas", 0),
                "retrasos":              asist.get("retrasos", 0),
                "excusas":               asist.get("excusas", 0),
            })

        return {
            "estudiante": {
                "nombre":    est["nombre"] if est else f"Estudiante {estudiante_id}",
                "documento": est["documento"] if est else "",
                "grupo":     (est["grupo_nombre"] or est["grupo_codigo"]) if est else "",
                "periodo":   per_actual["nombre"] if per_actual else str(hasta_periodo_id),
                "anio":      anio_id,
            },
            "periodos":           periodos_list,
            "areas":              list(areas.values()),
            "es_ultimo_periodo":  es_ultimo,
        }

    def boletin_datos_anual(
        self,
        estudiante_id: int,
        grupo_id: int,
        anio_id: int,
    ) -> dict[str, Any]:
        with self._get_conn() as conn:
            # Datos del estudiante y grupo
            est = conn.execute(
                """
                SELECT e.nombre || ' ' || e.apellido AS nombre,
                       e.tipo_documento || ' ' || e.numero_documento AS documento,
                       g.nombre AS grupo_nombre, g.codigo AS grupo_codigo
                FROM estudiantes e
                JOIN grupos g ON g.id = e.grupo_id
                WHERE e.id = ?
                """,
                (estudiante_id,),
            ).fetchone()

            # Periodos del año
            periodos = conn.execute(
                """
                SELECT id, nombre, numero FROM periodos
                WHERE anio_id = ? ORDER BY numero ASC
                """,
                (anio_id,),
            ).fetchall()

            # Asignaturas únicas por área en el año
            asigs = conn.execute(
                """
                SELECT DISTINCT
                    ar.id AS area_id, ar.nombre AS area_nombre,
                    s.id  AS asig_id, s.nombre  AS asig_nombre
                FROM asignaciones a
                JOIN asignaturas s ON s.id = a.asignatura_id
                JOIN areas_conocimiento ar ON ar.id = s.area_id
                JOIN periodos p ON p.id = a.periodo_id AND p.anio_id = ?
                WHERE a.grupo_id = ? AND a.activo = 1
                ORDER BY ar.nombre, s.nombre
                """,
                (anio_id, grupo_id),
            ).fetchall()

            # Notas por periodo (asignatura_id → periodo_id → nota)
            notas_rows = conn.execute(
                """
                SELECT s.id AS asig_id, cp.periodo_id, cp.nota_definitiva
                FROM cierres_periodo cp
                JOIN asignaciones a ON a.id = cp.asignacion_id AND a.grupo_id = ?
                JOIN asignaturas s  ON s.id = a.asignatura_id
                JOIN periodos p     ON p.id = cp.periodo_id AND p.anio_id = ?
                WHERE cp.estudiante_id = ?
                """,
                (grupo_id, anio_id, estudiante_id),
            ).fetchall()

            # Asistencia anual por asignatura
            asist_rows = conn.execute(
                """
                SELECT s.id AS asig_id,
                    COALESCE(SUM(CASE WHEN cd.estado='P'  THEN 1 ELSE 0 END), 0) AS presentes,
                    COALESCE(SUM(CASE WHEN cd.estado='FI' THEN 1 ELSE 0 END), 0) AS faltas_injustificadas,
                    COALESCE(SUM(CASE WHEN cd.estado='FJ' THEN 1 ELSE 0 END), 0) AS faltas_justificadas,
                    COALESCE(SUM(CASE WHEN cd.estado='R'  THEN 1 ELSE 0 END), 0) AS retrasos,
                    COALESCE(SUM(CASE WHEN cd.estado='E'  THEN 1 ELSE 0 END), 0) AS excusas
                FROM control_diario cd
                JOIN asignaciones a ON a.id = cd.asignacion_id AND a.grupo_id = ?
                JOIN asignaturas s  ON s.id = a.asignatura_id
                JOIN periodos p     ON p.id = cd.periodo_id AND p.anio_id = ?
                WHERE cd.estudiante_id = ?
                GROUP BY s.id
                """,
                (grupo_id, anio_id, estudiante_id),
            ).fetchall()

            # Estado de promoción
            promo = conn.execute(
                "SELECT estado FROM promocion_anual WHERE anio_id = ? AND estudiante_id = ?",
                (anio_id, estudiante_id),
            ).fetchone()

        # Indexar
        notas_idx: dict[tuple[int, int], float | None] = {
            (r["asig_id"], r["periodo_id"]): r["nota_definitiva"]
            for r in notas_rows
        }
        asist_idx: dict[int, dict] = {
            r["asig_id"]: dict(r) for r in asist_rows
        }
        periodos_list = [
            {"id": p["id"], "nombre": p["nombre"], "numero": p["numero"]}
            for p in periodos
        ]
        periodo_ids = [p["id"] for p in periodos_list]

        # Agrupar por área
        areas: dict[int, dict] = {}
        for r in asigs:
            aid = r["area_id"]
            if aid not in areas:
                areas[aid] = {"area_nombre": r["area_nombre"], "asignaturas": []}
            sid = r["asig_id"]
            notas_p = {pid: notas_idx.get((sid, pid)) for pid in periodo_ids}
            notas_validas = [v for v in notas_p.values() if v is not None]
            definitiva = round(sum(notas_validas) / len(notas_validas), 1) if notas_validas else None
            asist = asist_idx.get(sid, {})
            areas[aid]["asignaturas"].append({
                "nombre":                r["asig_nombre"],
                "notas_periodo":         notas_p,
                "definitiva":            definitiva,
                "presentes":             asist.get("presentes", 0),
                "faltas_injustificadas": asist.get("faltas_injustificadas", 0),
                "faltas_justificadas":   asist.get("faltas_justificadas", 0),
                "retrasos":              asist.get("retrasos", 0),
                "excusas":               asist.get("excusas", 0),
            })

        return {
            "estudiante": {
                "nombre":           est["nombre"] if est else f"Estudiante {estudiante_id}",
                "documento":        est["documento"] if est else "",
                "grupo":            (est["grupo_nombre"] or est["grupo_codigo"]) if est else "",
                "anio":             anio_id,
                "estado_promocion": promo["estado"] if promo else "pendiente",
            },
            "periodos": periodos_list,
            "areas":    list(areas.values()),
        }


__all__ = ["SqliteEstadisticosRepository"]
