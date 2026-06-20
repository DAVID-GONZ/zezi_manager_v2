"""Servicio de Plan de Mejoramiento."""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from src.domain.models.plan_mejoramiento import (
    ActividadPlan,
    CalculadorPlan,
    CortePlan,
    CerrarPlanEstudianteDTO,
    CalificarNotaPlanDTO,
    EjecutarCorteDTO,
    EstadoNotaCorte,
    NotaActividadPlan,
    NotaCortePlan,
    NuevaActividadPlanDTO,
)
from src.domain.ports.plan_mejoramiento_repo import IPlanMejoramientoRepository
from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.domain.ports.estudiante_repo import IEstudianteRepository


class PlanMejoramientoService:
    """Orquesta la lógica de Plan de Mejoramiento."""

    def __init__(
        self,
        plan_repo: IPlanMejoramientoRepository,
        eval_repo: IEvaluacionRepository,
        est_repo: IEstudianteRepository,
    ) -> None:
        self._plan_repo = plan_repo
        self._eval_repo = eval_repo
        self._est_repo = est_repo

    # ------------------------------------------------------------------
    # Corte
    # ------------------------------------------------------------------

    def ejecutar_corte(
        self, dto: EjecutarCorteDTO, grupo_id: int
    ) -> tuple[CortePlan, list[NotaCortePlan]]:
        """
        Ejecuta el corte de plan de mejoramiento para una asignación.

        Algoritmo:
        1. Valida que no exista ya un corte para asignacion+periodo.
        2. Obtiene estudiantes, categorías y actividades.
        3. Determina qué categorías tienen al menos una nota registrada.
        4. Calcula peso_registrado y nota_umbral.
        5. Crea CortePlan.
        6. Para cada estudiante, calcula nota_al_corte y crea NotaCortePlan
           con estado EN_PLAN (si nota < umbral) o SIN_PLAN.
        """
        if self._plan_repo.get_corte(dto.asignacion_id, dto.periodo_id) is not None:
            raise ValueError(
                "Ya existe un corte para esta asignación en este periodo"
            )

        estudiantes = self._est_repo.listar_por_grupo(grupo_id)
        if not estudiantes:
            raise ValueError("No hay estudiantes en el grupo")

        categorias = self._eval_repo.listar_categorias(dto.asignacion_id, dto.periodo_id)
        actividades = self._eval_repo.listar_actividades(dto.asignacion_id, dto.periodo_id)

        if not categorias:
            raise ValueError(
                "No hay categorías configuradas para esta asignación y periodo"
            )

        # Actividades agrupadas por categoria_id
        acts_por_cat: dict[int, list] = {}
        for act in actividades:
            acts_por_cat.setdefault(act.categoria_id, []).append(act)

        # Para cada actividad, sus notas registradas (cualquier estudiante)
        notas_por_act: dict[int, list] = {}
        for act in actividades:
            if act.id:
                notas_por_act[act.id] = self._eval_repo.listar_notas_por_actividad(act.id)

        # Categorías que tienen al menos una nota en alguna de sus actividades
        cats_con_notas = [
            cat for cat in categorias
            if cat.id and any(
                len(notas_por_act.get(a.id, [])) > 0
                for a in acts_por_cat.get(cat.id, [])
                if a.id
            )
        ]

        if not cats_con_notas:
            raise ValueError("No hay notas registradas para ninguna categoría")

        peso_reg = CalculadorPlan.peso_registrado(
            [{"peso": c.peso} for c in cats_con_notas]
        )
        umbral = CalculadorPlan.nota_umbral(peso_reg, dto.nota_minima_aprobacion)

        corte = self._plan_repo.guardar_corte(
            CortePlan(
                asignacion_id=dto.asignacion_id,
                periodo_id=dto.periodo_id,
                peso_registrado=peso_reg,
                nota_umbral=umbral,
                nota_minima_aprobacion=dto.nota_minima_aprobacion,
                usuario_id=dto.usuario_id,
            )
        )

        notas_corte: list[NotaCortePlan] = []
        for est in estudiantes:
            notas_est = self._eval_repo.listar_notas_por_estudiante(
                est.id, dto.asignacion_id, dto.periodo_id
            )
            nota_map = {n.actividad_id: n.valor for n in notas_est}

            cats_data = []
            for cat in cats_con_notas:
                acts = acts_por_cat.get(cat.id, [])
                if not acts:
                    continue
                promedio_cat = (
                    sum(nota_map.get(a.id, 0.0) for a in acts if a.id) / len(acts)
                )
                cats_data.append({"peso": cat.peso, "promedio": promedio_cat})

            nota_al_corte = CalculadorPlan.nota_al_corte(cats_data)
            estado = (
                EstadoNotaCorte.EN_PLAN
                if nota_al_corte < umbral
                else EstadoNotaCorte.SIN_PLAN
            )

            nota_c = self._plan_repo.guardar_nota_corte(
                NotaCortePlan(
                    corte_id=corte.id,
                    estudiante_id=est.id,
                    asignacion_id=dto.asignacion_id,
                    periodo_id=dto.periodo_id,
                    nota_al_corte=nota_al_corte,
                    estado=estado,
                )
            )
            notas_corte.append(nota_c)

        return corte, notas_corte

    def get_corte(self, asignacion_id: int, periodo_id: int) -> CortePlan | None:
        """Obtiene el corte existente para asignacion+periodo, o None."""
        return self._plan_repo.get_corte(asignacion_id, periodo_id)

    # ------------------------------------------------------------------
    # Notas de corte
    # ------------------------------------------------------------------

    def listar_notas_corte(self, corte_id: int) -> list[NotaCortePlan]:
        """Lista todas las notas de corte (todos los estudiantes)."""
        return self._plan_repo.listar_notas_corte(corte_id)

    def listar_en_plan(self, corte_id: int) -> list[NotaCortePlan]:
        """Lista solo los estudiantes que están EN_PLAN."""
        return [
            n for n in self._plan_repo.listar_notas_corte(corte_id)
            if n.estado == EstadoNotaCorte.EN_PLAN
        ]

    # ------------------------------------------------------------------
    # Actividades del plan
    # ------------------------------------------------------------------

    @requiere_escritura
    def agregar_actividad(
        self, dto: NuevaActividadPlanDTO, usuario_id: int | None = None
    ) -> ActividadPlan:
        """
        Añade una actividad al plan de mejoramiento.

        Valida que la suma de pesos (incluyendo la nueva) no supere 1.0.
        Crea NotaActividadPlan vacía para cada estudiante EN_PLAN.
        """
        suma_actual = self._plan_repo.suma_pesos_actividades(dto.corte_id)
        if suma_actual + dto.peso > 1.0 + 0.005:
            raise ValueError(
                f"La suma de pesos superaría 1.0 "
                f"(actual: {suma_actual:.3f}, nuevo: {dto.peso:.3f})"
            )

        actividad = self._plan_repo.guardar_actividad(dto.to_actividad(usuario_id))

        en_plan = self.listar_en_plan(dto.corte_id)
        for nc in en_plan:
            self._plan_repo.guardar_nota_actividad(
                NotaActividadPlan(
                    actividad_plan_id=actividad.id,
                    estudiante_id=nc.estudiante_id,
                    asignacion_id=dto.asignacion_id,
                    periodo_id=dto.periodo_id,
                )
            )

        return actividad

    def listar_actividades(self, corte_id: int) -> list[ActividadPlan]:
        """Lista actividades del plan para un corte."""
        return self._plan_repo.listar_actividades(corte_id)

    # ------------------------------------------------------------------
    # Notas de actividades
    # ------------------------------------------------------------------

    def listar_notas_actividad(self, actividad_plan_id: int) -> list[NotaActividadPlan]:
        """Lista todas las notas de una actividad del plan."""
        return self._plan_repo.listar_notas_actividad(actividad_plan_id)

    def notas_por_actividad_corte(
        self, corte_id: int
    ) -> dict[int, dict[int, NotaActividadPlan]]:
        """Devuelve las notas de TODAS las actividades de un corte en una sola
        llamada: {actividad_id: {estudiante_id: NotaActividadPlan}}.

        Reemplaza el bucle N+1 que la vista hacía llamando listar_notas_actividad
        por cada actividad."""
        resultado: dict[int, dict[int, NotaActividadPlan]] = {}
        for act in self._plan_repo.listar_actividades(corte_id):
            notas = self._plan_repo.listar_notas_actividad(act.id)
            resultado[act.id] = {n.estudiante_id: n for n in notas}
        return resultado

    def calificar_nota(
        self,
        actividad_plan_id: int,
        estudiante_id: int,
        dto: CalificarNotaPlanDTO,
    ) -> NotaActividadPlan:
        """
        Califica la nota de un estudiante en una actividad del plan.

        Guards:
        - La nota debe existir (el estudiante está en plan).
        - El plan del estudiante no debe estar cerrado (APROBADO/REPROBADO).
        """
        nota = self._plan_repo.get_nota_actividad(actividad_plan_id, estudiante_id)
        if nota is None:
            raise ValueError(
                "El estudiante no tiene asignada esta actividad de plan"
            )

        # Buscar corte_id a través de la actividad
        actividad = self._plan_repo.get_actividad(actividad_plan_id)
        if actividad is None:
            raise ValueError("Actividad de plan no encontrada")

        nota_corte = self._plan_repo.get_nota_corte(actividad.corte_id, estudiante_id)
        if nota_corte and nota_corte.estado in (
            EstadoNotaCorte.APROBADO, EstadoNotaCorte.REPROBADO
        ):
            raise ValueError("El plan del estudiante ya fue cerrado")

        actualizada = nota.model_copy(
            update={"valor": dto.valor, "usuario_id": dto.usuario_id}
        )
        return self._plan_repo.guardar_nota_actividad(actualizada)

    def calcular_nota_plan_estudiante(
        self, corte_id: int, estudiante_id: int
    ) -> float | None:
        """
        Calcula el promedio ponderado del plan para un estudiante.
        Retorna None si alguna nota no está registrada.
        """
        actividades = self._plan_repo.listar_actividades(corte_id)
        notas = self._plan_repo.listar_notas_por_corte_estudiante(corte_id, estudiante_id)
        return CalculadorPlan.nota_plan_estudiante(notas, actividades)

    # ------------------------------------------------------------------
    # Cierre por estudiante
    # ------------------------------------------------------------------

    @requiere_escritura
    def cerrar_plan_estudiante(self, dto: CerrarPlanEstudianteDTO) -> NotaCortePlan:
        """
        Cierra el plan de mejoramiento de un estudiante.

        - Si aprobado=True: nota_definitiva_plan = peso_registrado * nota_minima,
          estado = APROBADO.
        - Si aprobado=False: nota_definitiva_plan = nota_calculada del plan,
          estado = REPROBADO. Requiere todas las actividades calificadas.
        """
        nota_corte = self._plan_repo.get_nota_corte(dto.corte_id, dto.estudiante_id)
        if nota_corte is None:
            raise ValueError("No existe nota de corte para este estudiante")
        if nota_corte.estado in (EstadoNotaCorte.APROBADO, EstadoNotaCorte.REPROBADO):
            raise ValueError("El plan del estudiante ya fue cerrado")
        if nota_corte.estado == EstadoNotaCorte.SIN_PLAN:
            raise ValueError("El estudiante no está en plan de mejoramiento")

        corte = self._plan_repo.get_corte_by_id(dto.corte_id)
        if corte is None:
            raise ValueError("Corte no encontrado")

        if dto.aprobado:
            nota_definitiva = CalculadorPlan.nota_definitiva_aprobado(
                corte.peso_registrado, corte.nota_minima_aprobacion
            )
            nuevo_estado = EstadoNotaCorte.APROBADO
        else:
            nota_calculada = self.calcular_nota_plan_estudiante(
                dto.corte_id, dto.estudiante_id
            )
            if nota_calculada is None:
                raise ValueError(
                    "No todas las actividades del plan están calificadas"
                )
            nota_definitiva = nota_calculada
            nuevo_estado = EstadoNotaCorte.REPROBADO

        actualizada = nota_corte.model_copy(
            update={
                "nota_definitiva_plan": nota_definitiva,
                "estado": nuevo_estado,
                "usuario_cierre_id": dto.usuario_cierre_id,
            }
        )
        return self._plan_repo.actualizar_nota_corte(actualizada)


__all__ = [
    "PlanMejoramientoService",
    # re-exports para interface layer
    "ActividadPlan",
    "CalculadorPlan",
    "CortePlan",
    "CerrarPlanEstudianteDTO",
    "CalificarNotaPlanDTO",
    "EjecutarCorteDTO",
    "EstadoNotaCorte",
    "NotaActividadPlan",
    "NotaCortePlan",
    "NuevaActividadPlanDTO",
]
