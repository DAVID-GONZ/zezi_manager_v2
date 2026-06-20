"""
EstadisticosService
====================
Orquesta los casos de uso del módulo de Estadísticas y Métricas.

Este servicio es principalmente de solo lectura: delega al repositorio
de estadísticos que ejecuta las queries de agregación.

datos_tablero():
    Método anti-corrupción para la capa de interfaz.
    Recibe IDs de contexto, usa modelos de dominio internamente y devuelve
    un dict plano de primitivos — la UI no necesita importar ningún modelo.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.models.configuracion import NivelDesempeno
from src.domain.models.dtos import DashboardMetricsDTO

logger = logging.getLogger("ESTADISTICOS_SERVICE")


@dataclass(frozen=True)
class MetricasInstitucionalesDTO:
    """Métricas institucionales agregadas sobre todos los grupos con datos."""
    grupos: list[dict] = field(default_factory=list)   # filas por grupo
    kpi_grupos: int = 0
    kpi_promedio: float = 0.0
    kpi_asistencia: float = 0.0
    kpi_riesgo: int = 0


@dataclass(frozen=True)
class PendientesDocenteDTO:
    """Resumen de pendientes accionables de un docente (solo lectura)."""
    actividades_sin_calificar:    int = 0   # actividades publicadas sin nota alguna
    asignaciones_sin_asistencia:  int = 0   # asignaciones sin asistencia registrada hoy
    alertas_estudiantes:          int = 0   # alertas pendientes de sus estudiantes
    total_asignaciones:           int = 0   # asignaciones activas del docente en el periodo

    @property
    def hay_pendientes(self) -> bool:
        return (
            self.actividades_sin_calificar > 0
            or self.asignaciones_sin_asistencia > 0
            or self.alertas_estudiantes > 0
        )


class EstadisticosService:
    """
    Orquesta los casos de uso del módulo de Estadísticas.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IEstadisticosRepository,
        config_repo: IConfiguracionRepository | None = None,
        evaluacion_repo=None,
        asistencia_repo=None,
        estudiante_repo=None,
        infra_repo=None,
        asignacion_repo=None,
        alerta_repo=None,
    ) -> None:
        self._repo           = repo
        self._config_repo    = config_repo
        self._eval_repo      = evaluacion_repo
        self._asist_repo     = asistencia_repo
        self._est_repo       = estudiante_repo
        self._infra_repo     = infra_repo
        self._asignacion_repo = asignacion_repo
        self._alerta_repo    = alerta_repo

    # ------------------------------------------------------------------
    # Métricas de dashboard
    # ------------------------------------------------------------------

    def metricas_dashboard(
        self,
        grupo_id: int,
        periodo_id: int,
        anio_id: int | None = None,
    ) -> DashboardMetricsDTO:
        """
        Calcula las métricas del panel principal para un grupo y periodo.

        Obtiene la nota mínima de aprobación de la configuración del año
        si está disponible; usa 60.0 por defecto.
        """
        nota_minima = 60.0
        if self._config_repo is not None and anio_id is not None:
            config = self._config_repo.get_by_id(anio_id)
            if config is not None:
                nota_minima = config.nota_minima_aprobacion

        return self._repo.calcular_metricas_dashboard(
            grupo_id, periodo_id, nota_minima
        )

    def metricas_institucionales(
        self,
        periodo_id: int,
        anio_id: int | None = None,
    ) -> MetricasInstitucionalesDTO:
        """Agrega las métricas de TODOS los grupos con datos en un periodo,
        en una sola llamada (reemplaza el bucle N+1 de la vista).

        Devuelve las filas por grupo más los KPIs institucionales
        (promedio y asistencia medios entre grupos, total en riesgo)."""
        if not periodo_id or self._infra_repo is None:
            return MetricasInstitucionalesDTO()

        nota_minima = 60.0
        if self._config_repo is not None and anio_id is not None:
            config = self._config_repo.get_by_id(anio_id)
            if config is not None:
                nota_minima = config.nota_minima_aprobacion

        filas: list[dict] = []
        for g in self._infra_repo.listar_grupos():
            if not g.id:
                continue
            try:
                m = self._repo.calcular_metricas_dashboard(
                    g.id, periodo_id, nota_minima
                )
            except Exception:
                continue
            if m.total_estudiantes == 0:
                continue
            filas.append({
                "grupo_id":   g.id,
                "codigo":     g.codigo or str(g.id),
                "total":      m.total_estudiantes,
                "promedio":   m.promedio_general,
                "asistencia": m.porcentaje_asistencia,
                "en_riesgo":  m.estudiantes_en_riesgo,
            })

        filas.sort(key=lambda x: x["codigo"])
        n = len(filas)
        return MetricasInstitucionalesDTO(
            grupos=filas,
            kpi_grupos=n,
            kpi_promedio=round(sum(f["promedio"] for f in filas) / n, 1) if n else 0.0,
            kpi_asistencia=round(sum(f["asistencia"] for f in filas) / n, 1) if n else 0.0,
            kpi_riesgo=sum(f["en_riesgo"] for f in filas),
        )

    def pendientes_docente(
        self,
        usuario_id: int,
        periodo_id: int,
        anio_id: int | None = None,
    ) -> PendientesDocenteDTO:
        """Resumen de pendientes accionables de un docente (SOLO LECTURA).

        Agrega, sobre las asignaciones activas del docente en el periodo:
          - actividades publicadas que aún no tienen ninguna nota registrada,
          - asignaciones sin asistencia registrada en la fecha de hoy,
          - alertas pendientes de los estudiantes de sus grupos.

        Usado por el dashboard del profesor. No muta nada.
        """
        if (
            not usuario_id
            or not periodo_id
            or self._asignacion_repo is None
        ):
            return PendientesDocenteDTO()

        from datetime import date as _date

        try:
            asignaciones = self._asignacion_repo.listar_por_docente(
                usuario_id, periodo_id, solo_activas=True
            )
        except Exception:
            return PendientesDocenteDTO()

        hoy = _date.today()
        sin_calificar = 0
        sin_asistencia = 0
        grupos_ids: set[int] = set()

        for asig in asignaciones:
            asig_id = getattr(asig, "asignacion_id", None)
            grupo_id = getattr(asig, "grupo_id", None)
            if grupo_id:
                grupos_ids.add(grupo_id)
            if asig_id is None:
                continue

            # Actividades publicadas sin nota alguna
            if self._eval_repo is not None:
                try:
                    actividades = self._eval_repo.listar_actividades(asig_id, periodo_id)
                    for act in actividades:
                        if not getattr(act, "esta_publicada", False) or act.id is None:
                            continue
                        notas = self._eval_repo.listar_notas_por_actividad(act.id)
                        if not notas:
                            sin_calificar += 1
                except Exception:
                    pass

            # Asistencia de hoy sin registrar para la asignación
            if self._asist_repo is not None and grupo_id:
                try:
                    registros_hoy = self._asist_repo.listar_por_grupo_y_fecha(
                        grupo_id, asig_id, hoy
                    )
                    if not registros_hoy:
                        sin_asistencia += 1
                except Exception:
                    pass

        # Alertas pendientes de los estudiantes de sus grupos
        alertas = 0
        if self._alerta_repo is not None and self._est_repo is not None:
            vistos: set[int] = set()
            for grupo_id in grupos_ids:
                try:
                    estudiantes = self._est_repo.listar_por_grupo(grupo_id, solo_activos=True)
                except Exception:
                    continue
                for est in estudiantes:
                    if est.id is None or est.id in vistos:
                        continue
                    vistos.add(est.id)
                    try:
                        alertas += self._alerta_repo.contar_pendientes(est.id)
                    except Exception:
                        pass

        return PendientesDocenteDTO(
            actividades_sin_calificar=sin_calificar,
            asignaciones_sin_asistencia=sin_asistencia,
            alertas_estudiantes=alertas,
            total_asignaciones=len(asignaciones),
        )

    def promedio_general_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
    ) -> float:
        """Promedio de notas definitivas de todos los estudiantes del grupo."""
        return self._repo.promedio_general_grupo(
            grupo_id, periodo_id, nota_minima
        )

    def porcentaje_asistencia_global(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> float:
        """Porcentaje de asistencia promedio del grupo en todas sus asignaturas."""
        return self._repo.porcentaje_asistencia_global(grupo_id, periodo_id)

    def contar_alertas_pendientes(self, grupo_id: int) -> int:
        """Número de alertas no resueltas de los estudiantes del grupo."""
        return self._repo.contar_alertas_pendientes(grupo_id)

    # ------------------------------------------------------------------
    # Estadísticas de notas
    # ------------------------------------------------------------------

    def promedio_por_asignacion(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float:
        """Promedio de la nota definitiva de todos los estudiantes en una asignación."""
        return self._repo.promedio_por_asignacion(
            grupo_id, asignacion_id, periodo_id
        )

    def distribucion_desempenos(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
        anio_id: int | None = None,
    ) -> dict[str, int]:
        """
        Cuenta cuántos estudiantes cayeron en cada nivel de desempeño.

        Obtiene los niveles de desempeño de la configuración del año;
        si no hay configuración, retorna un dict vacío.
        """
        niveles: list[NivelDesempeno] = []
        if self._config_repo is not None and anio_id is not None:
            niveles = self._config_repo.listar_niveles(anio_id)

        return self._repo.distribucion_desempenos(
            grupo_id, asignacion_id, periodo_id, niveles
        )

    def comparativo_periodos(
        self,
        grupo_id: int,
        asignacion_id: int,
        anio_id: int,
    ) -> list[dict[str, Any]]:
        """
        Promedio del grupo por periodo, para ver la evolución temporal.

        Returns:
            list de dicts con {"periodo_nombre", "periodo_numero",
            "promedio", "periodo_id"} ordenado por periodo_numero.
        """
        return self._repo.comparativo_periodos(
            grupo_id, asignacion_id, anio_id
        )

    def promedios_por_area(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Promedio del grupo por área de conocimiento en el periodo."""
        return self._repo.promedios_por_area(grupo_id, periodo_id)

    def estudiantes_en_riesgo_academico(
        self,
        grupo_id: int,
        periodo_id: int,
        nota_minima: float = 60.0,
        min_asignaturas: int = 1,
    ) -> list[int]:
        """IDs de estudiantes con al menos N asignaturas bajo nota mínima."""
        return self._repo.estudiantes_en_riesgo_academico(
            grupo_id, periodo_id, nota_minima, min_asignaturas
        )

    def ranking_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Estudiantes del grupo ordenados por promedio descendente."""
        return self._repo.ranking_grupo(grupo_id, periodo_id)

    # ------------------------------------------------------------------
    # Estadísticas de asistencia
    # ------------------------------------------------------------------

    def tendencia_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Porcentaje de asistencia del grupo por semana/quincena."""
        return self._repo.tendencia_asistencia(
            grupo_id, asignacion_id, periodo_id
        )

    def distribucion_estados_asistencia(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> dict[str, int]:
        """Conteo total de registros por estado de asistencia en el periodo."""
        return self._repo.distribucion_estados_asistencia(
            grupo_id, asignacion_id, periodo_id
        )

    # ------------------------------------------------------------------
    # Consolidados para exportación
    # ------------------------------------------------------------------

    def consolidado_notas_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Tabla completa de notas definitivas por asignatura para el grupo."""
        return self._repo.consolidado_notas_grupo(grupo_id, periodo_id)

    def consolidado_asistencia_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[dict[str, Any]]:
        """Tabla completa de asistencia por asignatura para el grupo."""
        return self._repo.consolidado_asistencia_grupo(grupo_id, periodo_id)

    def consolidado_anual_grupo(
        self,
        grupo_id: int,
        anio_id: int,
    ) -> list[dict[str, Any]]:
        """Consolidado anual: notas + estado de promoción por estudiante."""
        return self._repo.consolidado_anual_grupo(grupo_id, anio_id)


    # ------------------------------------------------------------------
    # Anti-corrupción para la capa de interfaz — solo devuelve primitivos
    # ------------------------------------------------------------------

    def datos_tablero(
        self,
        asignacion_id: int,
        periodo_id: int,
        grupo_id: int,
        anio_id: int | None = None,
    ) -> dict:
        """
        Calcula todos los datos del tablero estadístico para una asignación.

        Usa modelos de dominio internamente (CalculadorNotas, NivelDesempeno)
        y devuelve únicamente primitivos Python (str, int, float, list, dict).

        La capa de interfaz llama este método y recibe el dict sin necesidad
        de importar ningún símbolo de src.domain.*.

        Returns:
            dict con claves documentadas, o {"error": str, "vacio": True}
            si algún repositorio requerido no está disponible o falla.
        """
        if self._eval_repo is None or self._est_repo is None:
            return {"error": "Repositorios requeridos no configurados.", "vacio": True}

        try:
            from src.domain.models.evaluacion import CalculadorNotas

            # ── 1. Configuración de niveles y nota mínima ─────────────
            nota_minima = 60.0
            niveles: list[NivelDesempeno] = []
            try:
                if self._config_repo and anio_id:
                    cfg = self._config_repo.get_by_id(anio_id)
                    if cfg:
                        nota_minima = cfg.nota_minima_aprobacion
                        niveles = self._config_repo.listar_niveles(anio_id)
            except Exception:
                pass

            # ── 2. Estructura evaluativa ──────────────────────────────
            categorias  = self._eval_repo.listar_categorias(asignacion_id, periodo_id)
            actividades = self._eval_repo.listar_actividades(asignacion_id, periodo_id)

            # ── 3. Estudiantes del grupo ──────────────────────────────
            estudiantes = self._est_repo.listar_por_grupo(grupo_id)
            est_ids     = [e.id for e in estudiantes if e.id]

            if not est_ids:
                return {"error": "Sin estudiantes en el grupo.", "vacio": True}

            # ── 4. Notas por estudiante y mapa global ─────────────────
            notas_por_est: dict[int, list] = {}
            nota_map: dict[tuple, float]   = {}

            for est_id in est_ids:
                notas = self._eval_repo.listar_notas_por_estudiante(
                    est_id, asignacion_id, periodo_id
                )
                notas_por_est[est_id] = notas
                for n in notas:
                    nota_map[(est_id, n.actividad_id)] = n.valor

            # ── 5. Promedio ponderado ajustado por estudiante ─────────
            promedios_est: dict[int, float] = {
                est_id: round(
                    CalculadorNotas.calcular_promedio_ajustado(
                        notas=notas_por_est[est_id],
                        actividades=actividades,
                        categorias=categorias,
                    ),
                    2,
                )
                for est_id in est_ids
            }

            # ── 6. Promedio general del grupo ─────────────────────────
            validos = [p for p in promedios_est.values() if p > 0]
            promedio_grupo = round(sum(validos) / len(validos), 2) if validos else 0.0

            # ── 7. Distribución por nivel de desempeño ────────────────
            dist_niveles: dict[str, int]
            if niveles:
                dist_niveles = {n.nombre: 0 for n in niveles}
                dist_niveles["Sin clasificar"] = 0
                for est_id, prom in promedios_est.items():
                    if prom == 0:
                        continue
                    clasificado = False
                    for nivel in sorted(niveles, key=lambda n: n.rango_min):
                        if nivel.clasifica(prom):
                            dist_niveles[nivel.nombre] = dist_niveles.get(nivel.nombre, 0) + 1
                            clasificado = True
                            break
                    if not clasificado:
                        dist_niveles["Sin clasificar"] += 1
            else:
                dist_niveles = {"Bajo": 0, "Básico": 0, "Alto": 0, "Superior": 0}
                for prom in promedios_est.values():
                    if   prom < 60: dist_niveles["Bajo"]     += 1
                    elif prom < 70: dist_niveles["Básico"]   += 1
                    elif prom < 85: dist_niveles["Alto"]      += 1
                    else:           dist_niveles["Superior"]  += 1

            en_riesgo = [eid for eid, p in promedios_est.items() if 0 < p < nota_minima]

            # ── 8. Análisis por categoría ─────────────────────────────
            analisis_categorias = []
            for cat in sorted(categorias, key=lambda c: c.peso, reverse=True):
                acts_cat    = [a for a in actividades if a.categoria_id == cat.id]
                act_ids_cat = {a.id for a in acts_cat if a.id}
                notas_cat   = [v for (_, aid), v in nota_map.items() if aid in act_ids_cat]
                prom_cat    = round(sum(notas_cat) / len(notas_cat), 2) if notas_cat else None
                aprobados   = sum(
                    1 for eid in est_ids
                    if any(nota_map.get((eid, aid), 0) >= nota_minima for aid in act_ids_cat)
                )
                analisis_categorias.append({
                    "nombre":       cat.nombre,
                    "peso_pct":     round(cat.peso * 100, 1),
                    "promedio":     prom_cat,
                    "aprobados":    aprobados,
                    "total_est":    len(est_ids),
                    "n_actividades": len(acts_cat),
                })

            # ── 9. Análisis por actividad ─────────────────────────────
            cat_nombre_map = {c.id: c.nombre for c in categorias}
            analisis_actividades = []
            for act in actividades:
                notas_act  = [nota_map[(eid, act.id)] for eid in est_ids if (eid, act.id) in nota_map]
                prom_act   = round(sum(notas_act) / len(notas_act), 2) if notas_act else None
                analisis_actividades.append({
                    "nombre":      act.nombre[:22],
                    "nombre_full": act.nombre,
                    "categoria":   cat_nombre_map.get(act.categoria_id, "—"),
                    "promedio":    prom_act,
                    "entregadas":  len(notas_act),
                    "total":       len(est_ids),
                    "pct_entrega": round(len(notas_act) / len(est_ids) * 100, 1) if est_ids else 0,
                    "fecha":       str(act.fecha) if act.fecha else "—",
                })

            # ── 10. Heatmap (nota por estudiante × actividad) ─────────
            est_nombres = {e.id: f"{e.apellido}, {e.nombre}" for e in estudiantes if e.id}
            act_ids_ord = [a.id for a in actividades if a.id]
            est_ids_ord = sorted(est_ids, key=lambda eid: promedios_est.get(eid, 0))

            heatmap_data = [
                [col, row, round(nota_map[(est_ids_ord[row], act_ids_ord[col])], 1)]
                for col, act_id in enumerate(act_ids_ord)
                for row, est_id in enumerate(est_ids_ord)
                if (est_ids_ord[row], act_ids_ord[col]) in nota_map
            ]

            # ── 11. Asistencia por estudiante ─────────────────────────
            asist_por_est: dict[int, float] = {}
            pct_asistencia_grupo            = 0.0
            if self._asist_repo is not None:
                try:
                    resumenes = self._asist_repo.resumen_por_grupo(
                        grupo_id=grupo_id,
                        asignacion_id=asignacion_id,
                        periodo_id=periodo_id,
                    )
                    asist_por_est = {r.estudiante_id: r.porcentaje_asistencia for r in resumenes}
                    if resumenes:
                        pct_asistencia_grupo = round(
                            sum(r.porcentaje_asistencia for r in resumenes) / len(resumenes), 1
                        )
                except Exception:
                    pass

            # ── 12. Tendencia de asistencia por semana ────────────────
            tendencia_asistencia: list[dict] = []
            try:
                raw = self._repo.tendencia_asistencia(grupo_id, asignacion_id, periodo_id)
                tendencia_asistencia = [
                    {"semana": f"Sem {r['semana']}", "pct": r["porcentaje"]}
                    for r in raw
                ]
            except Exception:
                pass

            # ── 13. Tabla de estudiantes ordenada por promedio ────────
            def _nivel_nombre(prom: float) -> str:
                if prom <= 0:
                    return "Sin datos"
                if niveles:
                    for nivel in sorted(niveles, key=lambda n: n.rango_min):
                        if nivel.clasifica(prom):
                            return nivel.nombre
                else:
                    if prom >= 85:  return "Superior"
                    if prom >= 70:  return "Alto"
                    if prom >= 60:  return "Básico"
                return "Bajo"

            tabla_estudiantes = sorted(
                [
                    {
                        "nombre":         f"{e.apellido}, {e.nombre}",
                        "promedio":       promedios_est.get(e.id, 0),
                        "nivel":          _nivel_nombre(promedios_est.get(e.id, 0)),
                        "asistencia_pct": asist_por_est.get(e.id, 0),
                        "en_riesgo":      0 < promedios_est.get(e.id, 0) < nota_minima,
                    }
                    for e in estudiantes if e.id
                ],
                key=lambda x: x["promedio"],
            )

            return {
                "error":                None,
                "vacio":                False,
                "promedio_grupo":       promedio_grupo,
                "pct_asistencia":       pct_asistencia_grupo,
                "total_estudiantes":    len(est_ids),
                "en_riesgo_count":      len(en_riesgo),
                "actividades_count":    len(actividades),
                "nota_minima":          nota_minima,
                "dist_niveles":         dist_niveles,
                "analisis_categorias":  analisis_categorias,
                "analisis_actividades": analisis_actividades,
                "heatmap_data":         heatmap_data,
                "heatmap_actos":        [a.nombre[:18] for a in actividades if a.id],
                "heatmap_ests":         [est_nombres.get(e, "?") for e in est_ids_ord],
                "tendencia_asistencia": tendencia_asistencia,
                "tabla_estudiantes":    tabla_estudiantes,
            }

        except Exception as exc:
            logger.error("datos_tablero(%s, %s, %s): %s", asignacion_id, periodo_id, grupo_id, exc)
            return {"error": str(exc), "vacio": True}


__all__ = ["EstadisticosService", "MetricasInstitucionalesDTO", "PendientesDocenteDTO"]
