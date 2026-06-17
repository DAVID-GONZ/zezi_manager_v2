"""
PreparacionHorarioService — validadores de preparación para generar horarios (paso_19).

Expone:
  validar(anio_id, periodo_id, plantilla_id) -> ReportePreparacionDTO
  puede_generar(reporte) -> bool

Cada puerta es una función pura que devuelve un PuertaDTO; nunca lanza excepciones.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.models.asignacion import FiltroAsignacionesDTO
from src.domain.ports.asignacion_repo import IAsignacionRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.ports.usuario_repo import IUsuarioRepository

if TYPE_CHECKING:
    from src.services.plan_estudios_service import PlanEstudiosService


@dataclass(frozen=True)
class PuertaDTO:
    id:         str
    titulo:     str
    severidad:  str          # "dura" | "advertencia"
    ok:         bool
    detalle:    str
    fix_ruta:   str | None = None


ReportePreparacionDTO = list[PuertaDTO]


class PreparacionHorarioService:

    def __init__(
        self,
        infra_repo:       IInfraestructuraRepository,
        asignacion_repo:  IAsignacionRepository,
        config_repo:      IConfiguracionRepository,
        periodo_repo:     IPeriodoRepository,
        usuario_repo:     IUsuarioRepository,
        plan_svc:         "PlanEstudiosService",
    ) -> None:
        self._infra      = infra_repo
        self._asigs      = asignacion_repo
        self._cfg        = config_repo
        self._periodos   = periodo_repo
        self._usuarios   = usuario_repo
        self._plan       = plan_svc

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def validar(
        self,
        anio_id:      int,
        periodo_id:   int,
        plantilla_id: int,
    ) -> ReportePreparacionDTO:
        """Ejecuta las 7 puertas en orden y devuelve el reporte."""
        asignaciones = self._listar_asignaciones(periodo_id)
        grupos       = self._infra.listar_grupos()
        asignaturas  = self._infra.listar_asignaturas()
        salas        = self._infra.listar_salas()
        franjas      = self._infra.listar_franjas(plantilla_id) if plantilla_id else []
        plantilla    = (
            next((p for p in self._infra.listar_plantillas_franja() if p.id == plantilla_id), None)
            if plantilla_id else None
        )

        asig_map = {a.id: a for a in asignaturas}
        grado_de_grupo = {g.id: g.grado for g in grupos}
        return [
            self._p1_anio_periodo(anio_id, periodo_id),
            self._p2_asignaturas_con_horas(asignaturas),
            self._p3_horas_grupo_vs_slots(grupos, plantilla, franjas),
            self._p4_capacidad_docente(asignaciones, asig_map, grado_de_grupo),
            self._p5_cobertura_asignaciones(grupos, asignaciones, asig_map),
            self._p6_plantilla_suficiente(plantilla_id, plantilla, franjas),
            self._p7_salas_suficientes(asignaturas, salas),
        ]

    def _listar_asignaciones(self, periodo_id: int) -> list:
        """Devuelve TODAS las asignaciones del periodo recorriendo las páginas.

        `IAsignacionRepository.listar` está paginado (máx. 500/página); las
        puertas de preparación necesitan el conjunto completo, de lo contrario
        las asignaciones más allá de la primera página parecen inexistentes
        (cobertura del plan y carga docente quedarían mal calculadas).
        """
        todas: list = []
        pagina = 1
        while True:
            lote = self._asigs.listar(
                FiltroAsignacionesDTO(
                    periodo_id=periodo_id, pagina=pagina, por_pagina=500
                )
            )
            todas.extend(lote)
            if len(lote) < 500:
                break
            pagina += 1
        return todas

    def _horas_asignacion(self, asignacion, asig_map: dict, grado_de_grupo: dict) -> int:
        """Horas semanales de una asignación según el plan de estudios del grado
        (con fallback a las horas globales de la asignatura)."""
        grado = grado_de_grupo.get(asignacion.grupo_id)
        asignatura = asig_map.get(asignacion.asignatura_id)
        global_h = (asignatura.horas_semanales or 0) if asignatura else 0
        if grado is None:
            return global_h
        try:
            return self._plan.horas_de(grado, asignacion.asignatura_id) or global_h
        except Exception:
            return global_h

    # Cupos lectivos semanales = franjas lectivas × días activos de la plantilla.
    @staticmethod
    def _cupos_semana(plantilla, franjas) -> tuple[int, int, int]:
        n_lectivas = sum(1 for f in franjas if getattr(f, "es_lectiva", True))
        n_dias = len(getattr(plantilla, "dias_activos", None) or []) if plantilla else 0
        return n_lectivas * n_dias, n_lectivas, n_dias

    @staticmethod
    def puede_generar(reporte: ReportePreparacionDTO) -> bool:
        """True si todas las puertas 'dura' están en ok."""
        return all(p.ok for p in reporte if p.severidad == "dura")

    # ------------------------------------------------------------------
    # Puerta 1 — año y periodo existen y son coherentes
    # ------------------------------------------------------------------

    def _p1_anio_periodo(self, anio_id: int, periodo_id: int) -> PuertaDTO:
        config = self._cfg.get_by_id(anio_id)
        if config is None:
            return PuertaDTO(
                id="anio_periodo",
                titulo="Año lectivo configurado",
                severidad="dura",
                ok=False,
                detalle=f"No existe una configuración para el año con id={anio_id}.",
                fix_ruta="/admin/configuracion",
            )
        periodo = self._periodos.get_by_id(periodo_id)
        if periodo is None:
            return PuertaDTO(
                id="anio_periodo",
                titulo="Año lectivo configurado",
                severidad="dura",
                ok=False,
                detalle=f"No existe el periodo con id={periodo_id}.",
                fix_ruta="/admin/configuracion",
            )
        if periodo.anio_id != anio_id:
            return PuertaDTO(
                id="anio_periodo",
                titulo="Año lectivo configurado",
                severidad="dura",
                ok=False,
                detalle=(
                    f"El periodo {periodo_id} no pertenece al año {config.anio}."
                ),
                fix_ruta="/admin/configuracion",
            )
        return PuertaDTO(
            id="anio_periodo",
            titulo="Año lectivo configurado",
            severidad="dura",
            ok=True,
            detalle=f"Año {config.anio}, periodo {periodo.numero} — OK.",
        )

    # ------------------------------------------------------------------
    # Puerta 2 — todas las asignaturas tienen horas_semanales >= 1
    # ------------------------------------------------------------------

    def _p2_asignaturas_con_horas(self, asignaturas) -> PuertaDTO:
        sin_horas = [a for a in asignaturas if (a.horas_semanales or 0) < 1]
        if sin_horas:
            nombres = ", ".join(a.nombre for a in sin_horas[:5])
            resto   = f" y {len(sin_horas) - 5} más" if len(sin_horas) > 5 else ""
            return PuertaDTO(
                id="asignaturas_con_horas",
                titulo="Asignaturas con horas definidas",
                severidad="dura",
                ok=False,
                detalle=f"{len(sin_horas)} asignatura(s) sin horas: {nombres}{resto}.",
                fix_ruta="/admin/asignaturas",
            )
        return PuertaDTO(
            id="asignaturas_con_horas",
            titulo="Asignaturas con horas definidas",
            severidad="dura",
            ok=True,
            detalle=f"Las {len(asignaturas)} asignaturas tienen horas semanales.",
        )

    # ------------------------------------------------------------------
    # Puerta 3 — horas del plan de estudios ≤ slots de la plantilla
    # ------------------------------------------------------------------

    def _p3_horas_grupo_vs_slots(self, grupos, plantilla, franjas) -> PuertaDTO:
        ruta = "/academico/generar-horario?tab=plantillas"
        cupos, n_lectivas, n_dias = self._cupos_semana(plantilla, franjas)
        if cupos == 0:
            return PuertaDTO(
                id="horas_grupo_vs_slots",
                titulo="Capacidad de la plantilla",
                severidad="dura",
                ok=False,
                detalle="La plantilla no tiene cupos lectivos (faltan franjas lectivas o días activos).",
                fix_ruta=ruta,
            )
        problemas = []
        for g in grupos:
            if g.grado is None:
                continue
            total = self._plan.horas_por_grado(g.grado)
            if total > cupos:
                problemas.append(f"{g.nombre}: {total}h")
        if problemas:
            detalle = (
                f"{len(problemas)} grupo(s) requieren más horas de las que caben en la "
                f"plantilla ({cupos} cupos lectivos/semana = {n_lectivas} franjas × {n_dias} días): "
                + "; ".join(problemas[:3])
            )
            if len(problemas) > 3:
                detalle += f" y {len(problemas) - 3} más"
            detalle += ". Amplía la plantilla (más franjas o días) o reduce el plan de estudios del grado."
            return PuertaDTO(
                id="horas_grupo_vs_slots",
                titulo="Capacidad de la plantilla",
                severidad="dura",
                ok=False,
                detalle=detalle,
                fix_ruta=ruta,
            )
        return PuertaDTO(
            id="horas_grupo_vs_slots",
            titulo="Capacidad de la plantilla",
            severidad="dura",
            ok=True,
            detalle=f"Todos los grupos caben en los {cupos} cupos lectivos semanales.",
        )

    # ------------------------------------------------------------------
    # Puerta 4 — docentes con carga_horaria_max no excedida
    # ------------------------------------------------------------------

    def _p4_capacidad_docente(self, asignaciones, asig_map: dict, grado_de_grupo: dict) -> PuertaDTO:
        carga_por_docente: dict[int, int] = {}
        for a in asignaciones:
            if not a.activo:
                continue
            horas = self._horas_asignacion(a, asig_map, grado_de_grupo)
            carga_por_docente[a.usuario_id] = carga_por_docente.get(a.usuario_id, 0) + horas

        excedidos = []
        for uid, carga in carga_por_docente.items():
            usuario = self._usuarios.get_by_id(uid)
            if usuario and usuario.carga_horaria_max and carga > usuario.carga_horaria_max:
                excedidos.append(
                    f"{usuario.nombre_completo or usuario.usuario}: {carga}h > {usuario.carga_horaria_max}h max"
                )
        if excedidos:
            return PuertaDTO(
                id="capacidad_docente",
                titulo="Capacidad de docentes",
                severidad="advertencia",
                ok=False,
                detalle=f"{len(excedidos)} docente(s) exceden su carga máxima: " + "; ".join(excedidos[:3]) + ("…" if len(excedidos) > 3 else "") + ".",
                fix_ruta="/admin/asignaciones",
            )
        return PuertaDTO(
            id="capacidad_docente",
            titulo="Capacidad de docentes",
            severidad="advertencia",
            ok=True,
            detalle="Ningún docente excede su carga horaria máxima.",
        )

    # ------------------------------------------------------------------
    # Puerta 5 — plan de estudios cubierto por asignaciones
    # ------------------------------------------------------------------

    def _p5_cobertura_asignaciones(self, grupos, asignaciones, asig_map: dict) -> PuertaDTO:
        activas = [a for a in asignaciones if a.activo]
        grupo_map = {g.id: g for g in grupos}

        cubiertos: set[tuple[int, int]] = set()
        for a in activas:
            g = grupo_map.get(a.grupo_id)
            if g and g.grado is not None:
                cubiertos.add((g.grado, a.asignatura_id))

        plan_total = self._plan.listar()
        sin_cubrir = [
            p for p in plan_total
            if (p.grado, p.asignatura_id) not in cubiertos
        ]

        if not plan_total:
            return PuertaDTO(
                id="cobertura_asignaciones",
                titulo="Plan de estudios cubierto",
                severidad="advertencia",
                ok=True,
                detalle="No hay plan de estudios definido; se omite la validación de cobertura.",
            )

        if sin_cubrir:
            ejemplos = []
            for p in sin_cubrir[:3]:
                asig = asig_map.get(p.asignatura_id)
                nombre = asig.nombre if asig else f"asignatura {p.asignatura_id}"
                ejemplos.append(f"grado {p.grado} — {nombre}")
            return PuertaDTO(
                id="cobertura_asignaciones",
                titulo="Plan de estudios cubierto",
                severidad="advertencia",
                ok=False,
                detalle=f"{len(sin_cubrir)} combinación(es) del plan sin asignación: " + "; ".join(ejemplos) + ("…" if len(sin_cubrir) > 3 else "") + ".",
                fix_ruta="/admin/asignaciones",
            )

        return PuertaDTO(
            id="cobertura_asignaciones",
            titulo="Plan de estudios cubierto",
            severidad="advertencia",
            ok=True,
            detalle=f"Las {len(plan_total)} combinaciones del plan tienen asignación.",
        )

    # ------------------------------------------------------------------
    # Puerta 6 — plantilla existe y tiene franjas suficientes
    # ------------------------------------------------------------------

    def _p6_plantilla_suficiente(self, plantilla_id: int, plantilla, franjas) -> PuertaDTO:
        ruta = "/academico/generar-horario?tab=plantillas"

        def _falla(detalle: str) -> PuertaDTO:
            return PuertaDTO(
                id="plantilla_suficiente",
                titulo="Plantilla de franjas lista",
                severidad="dura",
                ok=False,
                detalle=detalle,
                fix_ruta=ruta,
            )

        if not plantilla_id or plantilla is None:
            return _falla("No hay una plantilla de franjas seleccionada o no existe.")
        if not franjas:
            return _falla("La plantilla seleccionada no tiene franjas horarias definidas.")
        if not (getattr(plantilla, "dias_activos", None) or []):
            return _falla("La plantilla no tiene días activos configurados.")
        n_lectivas = sum(1 for f in franjas if getattr(f, "es_lectiva", True))
        if n_lectivas == 0:
            return _falla("La plantilla solo tiene franjas de descanso; añade franjas lectivas.")
        return PuertaDTO(
            id="plantilla_suficiente",
            titulo="Plantilla de franjas lista",
            severidad="dura",
            ok=True,
            detalle=(
                f"Plantilla con {n_lectivas} franja(s) lectiva(s) en "
                f"{len(plantilla.dias_activos)} día(s) activo(s)."
            ),
        )

    # ------------------------------------------------------------------
    # Puerta 7 — salas disponibles para tipos requeridos
    # ------------------------------------------------------------------

    def _p7_salas_suficientes(self, asignaturas, salas) -> PuertaDTO:
        if not salas:
            return PuertaDTO(
                id="salas_suficientes",
                titulo="Salas disponibles",
                severidad="advertencia",
                ok=True,
                detalle="No hay salas registradas; el generador asignará sin restricción de sala.",
                fix_ruta="/admin/salas",
            )
        tipos_requeridos = {
            a.tipo_sala_requerido
            for a in asignaturas
            if getattr(a, "tipo_sala_requerido", None)
        }
        tipos_disponibles = {s.tipo for s in salas}
        faltantes = tipos_requeridos - tipos_disponibles
        if faltantes:
            return PuertaDTO(
                id="salas_suficientes",
                titulo="Salas disponibles",
                severidad="advertencia",
                ok=False,
                detalle=f"Tipos de sala requeridos sin sala disponible: {', '.join(sorted(faltantes))}.",
                fix_ruta="/admin/salas",
            )
        return PuertaDTO(
            id="salas_suficientes",
            titulo="Salas disponibles",
            severidad="advertencia",
            ok=True,
            detalle=f"{len(salas)} sala(s) disponibles, tipos requeridos cubiertos.",
        )


__all__ = ["PuertaDTO", "ReportePreparacionDTO", "PreparacionHorarioService"]
