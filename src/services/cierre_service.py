"""
CierreService
==============
Orquesta el proceso de cierre de periodo y cierre anual.
Es el servicio más complejo del sistema: coordina múltiples repos
para calcular definitivas y generar los registros de cierre.
"""
from __future__ import annotations

from datetime import date

from src.domain.ports.cierre_repo import ICierreRepository
from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.ports.alerta_repo import IAlertaRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.domain.models.cierre import (
    CierreAnio,
    CierrePeriodo,
    DecidirPromocionDTO,
    EstadoPromocion,
    PromocionAnual,
)
from src.domain.models.evaluacion import CalculadorNotas
from src.domain.models.alerta import Alerta, TipoAlerta, NivelAlerta
from src.domain.models.dtos import ContextoAcademicoDTO
from src.domain.models.auditoria import AccionCambio, RegistroCambio


class CierreService:
    """
    Orquesta los procesos de cierre de periodo y cierre anual.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        cierre_repo: ICierreRepository,
        evaluacion_repo: IEvaluacionRepository,
        periodo_repo: IPeriodoRepository,
        config_repo: IConfiguracionRepository,
        estudiante_repo: IEstudianteRepository,
        alerta_repo: IAlertaRepository | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        self._cierre_repo    = cierre_repo
        self._eval_repo      = evaluacion_repo
        self._periodo_repo   = periodo_repo
        self._config_repo    = config_repo
        self._estudiante_repo = estudiante_repo
        self._alerta_repo    = alerta_repo
        self._auditoria      = auditoria

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _auditar(
        self,
        accion: AccionCambio,
        tabla: str,
        registro_id: int | None,
        datos_ant: dict | None,
        datos_nue: dict | None,
        usuario_id: int | None,
    ) -> None:
        if self._auditoria is None:
            return
        if accion == AccionCambio.CREATE:
            cambio = RegistroCambio.para_creacion(
                tabla, datos_nue or {}, registro_id, usuario_id
            )
        elif accion == AccionCambio.UPDATE:
            cambio = RegistroCambio.para_actualizacion(
                tabla, datos_ant or {}, datos_nue or {}, registro_id, usuario_id
            )
        else:
            cambio = RegistroCambio.para_eliminacion(
                tabla, datos_ant or {}, registro_id, usuario_id
            )
        self._auditoria.registrar_cambio(cambio)

    def _verificar_alerta_academica(
        self,
        estudiante_id: int,
        nota: float,
        nota_minima: float,
        anio_id: int,
    ) -> None:
        """Genera alerta de promedio bajo si la nota no es aprobatoria."""
        if self._alerta_repo is None:
            return
        if nota >= nota_minima:
            return

        cfg = self._alerta_repo.get_configuracion(
            anio_id, TipoAlerta.PROMEDIO_BAJO
        )
        if cfg is None or not cfg.activa:
            return

        if nota > cfg.umbral:
            return  # no es tan baja como para alertar

        if self._alerta_repo.existe_pendiente(
            estudiante_id, TipoAlerta.PROMEDIO_BAJO
        ):
            return

        nivel = NivelAlerta.CRITICA if nota < cfg.umbral / 2 else NivelAlerta.ADVERTENCIA
        alerta = Alerta(
            estudiante_id=estudiante_id,
            tipo_alerta=TipoAlerta.PROMEDIO_BAJO,
            nivel=nivel,
            descripcion=(
                f"Promedio de {nota:.1f} está por debajo del mínimo "
                f"de aprobación ({nota_minima:.1f})."
            ),
        )
        self._alerta_repo.guardar_alerta(alerta)

    # ------------------------------------------------------------------
    # Cierre de periodo
    # ------------------------------------------------------------------

    def cerrar_periodo(
        self,
        asignacion_id: int,
        periodo_id: int,
        ctx: ContextoAcademicoDTO,
        usuario_id: int | None = None,
    ) -> list[CierrePeriodo]:
        """
        Calcula y registra la nota definitiva de cada estudiante del grupo
        para una asignación al cierre del periodo.

        Pasos:
        1. Verificar que el periodo está abierto.
        2. Para cada estudiante: calcular definitiva con CalculadorNotas.
        3. Clasificar en nivel de desempeño.
        4. Guardar CierrePeriodo (upsert).
        5. Verificar alertas académicas.

        Retorna la lista de cierres generados.
        """
        # 1. Verificar periodo
        periodo = self._periodo_repo.get_by_id(periodo_id)
        if periodo is None:
            raise ValueError(f"Periodo con id {periodo_id} no existe.")
        if not periodo.esta_abierto:
            raise ValueError(
                f"El periodo '{periodo.nombre}' ya está cerrado."
            )

        # Obtener config del año para nota mínima y clasificación
        config = self._config_repo.get_by_id(ctx.anio_id)
        nota_minima = config.nota_minima_aprobacion if config else 60.0

        # Obtener actividades y categorías (comunes para todos los estudiantes)
        categorias   = self._eval_repo.listar_categorias(asignacion_id, periodo_id)
        actividades  = self._eval_repo.listar_actividades(asignacion_id, periodo_id)

        # Obtener estudiantes del grupo
        estudiantes = self._estudiante_repo.listar_por_grupo(
            ctx.grupo_id, solo_activos=True
        )

        cierres: list[CierrePeriodo] = []
        for est in estudiantes:
            notas = self._eval_repo.listar_notas_por_estudiante(
                est.id, asignacion_id, periodo_id
            )
            definitiva = CalculadorNotas.calcular_definitiva(
                notas, actividades, categorias
            )

            # Clasificar nivel de desempeño
            nivel = self._config_repo.clasificar_nota(definitiva, ctx.anio_id)

            cierre = CierrePeriodo(
                estudiante_id     = est.id,
                asignacion_id     = asignacion_id,
                periodo_id        = periodo_id,
                nota_definitiva   = definitiva,
                desempeno_id      = nivel.id if nivel else None,
                fecha_cierre      = date.today(),
                usuario_cierre_id = usuario_id,
            )
            cierre = self._cierre_repo.guardar_cierre_periodo(cierre)
            cierres.append(cierre)

            # Verificar alerta académica
            self._verificar_alerta_academica(
                est.id, definitiva, nota_minima, ctx.anio_id
            )

        return cierres

    # ------------------------------------------------------------------
    # Cierre de año
    # ------------------------------------------------------------------

    def cerrar_anio(
        self,
        grupo_id: int,
        anio_id: int,
        ctx: ContextoAcademicoDTO,
        usuario_id: int | None = None,
    ) -> list[CierreAnio]:
        """
        Calcula y registra la nota definitiva anual de cada estudiante.

        Pasos:
        1. Obtener periodos del año (deben estar todos cerrados).
        2. Para cada estudiante+asignación: calcular promedio ponderado.
        3. Verificar si hay habilitación registrada.
        4. Guardar CierreAnio y PromocionAnual(PENDIENTE).

        Retorna la lista de cierres anuales generados.
        """
        periodos = self._periodo_repo.listar_por_anio(anio_id)
        abiertos = [p for p in periodos if p.esta_abierto]
        if abiertos:
            nombres = ", ".join(p.nombre for p in abiertos)
            raise ValueError(
                f"Los siguientes periodos aún están abiertos: {nombres}. "
                "Cierre todos los periodos antes de cerrar el año."
            )

        config = self._config_repo.get_by_id(anio_id)
        nota_minima = config.nota_minima_aprobacion if config else 60.0

        estudiantes = self._estudiante_repo.listar_por_grupo(
            grupo_id, solo_activos=True
        )

        cierres_anio: list[CierreAnio] = []

        for est in estudiantes:
            # Obtener cierres de periodo de todos los periodos
            cierres_periodo = self._cierre_repo.listar_cierres_periodo_por_estudiante(
                est.id, periodo_id=None
            )

            # Agrupar por asignacion_id
            por_asignacion: dict[int, list[CierrePeriodo]] = {}
            for cp in cierres_periodo:
                por_asignacion.setdefault(cp.asignacion_id, []).append(cp)

            for asignacion_id, cps in por_asignacion.items():
                # Calcular promedio ponderado
                total_peso = sum(
                    p.peso_porcentual
                    for p in periodos
                    if any(cp.periodo_id == p.id for cp in cps)
                )
                if total_peso == 0:
                    promedio = 0.0
                else:
                    promedio = sum(
                        cp.nota_definitiva * next(
                            (p.peso_porcentual for p in periodos if p.id == cp.periodo_id), 0
                        )
                        for cp in cps
                    ) / total_peso

                promedio = round(promedio, 2)

                # Verificar habilitación
                nota_hab = None
                nota_definitiva_anual = promedio
                from src.domain.models.habilitacion import TipoHabilitacion
                # Buscar en cierres anio si ya existe con habilitación
                cierre_existente = self._cierre_repo.get_cierre_anio(
                    est.id, asignacion_id, anio_id
                )
                if cierre_existente and cierre_existente.nota_habilitacion is not None:
                    nota_hab = cierre_existente.nota_habilitacion
                    nota_definitiva_anual = nota_hab

                nivel = self._config_repo.clasificar_nota(nota_definitiva_anual, anio_id)
                perdio = nota_definitiva_anual < nota_minima

                cierre_anio = CierreAnio(
                    estudiante_id          = est.id,
                    asignacion_id          = asignacion_id,
                    anio_id                = anio_id,
                    nota_promedio_periodos = promedio,
                    nota_habilitacion      = nota_hab,
                    nota_definitiva_anual  = nota_definitiva_anual,
                    perdio                 = perdio,
                    desempeno_id           = nivel.id if nivel else None,
                    fecha_cierre           = date.today(),
                    usuario_cierre_id      = usuario_id,
                )
                cierre_anio = self._cierre_repo.guardar_cierre_anio(cierre_anio)
                cierres_anio.append(cierre_anio)

            # Crear PromocionAnual en estado PENDIENTE si no existe
            promocion_existente = self._cierre_repo.get_promocion(est.id, anio_id)
            if promocion_existente is None:
                promocion = PromocionAnual(
                    estudiante_id=est.id,
                    anio_id=anio_id,
                )
                self._cierre_repo.guardar_promocion(promocion)

        return cierres_anio

    # ------------------------------------------------------------------
    # Decisión de promoción
    # ------------------------------------------------------------------

    def decidir_promocion(
        self,
        est_id: int,
        anio_id: int,
        dto: DecidirPromocionDTO,
        usuario_id: int | None = None,
    ) -> PromocionAnual:
        """
        Registra la decisión de promoción de un estudiante.

        La decisión es PENDIENTE → PROMOVIDO | REPROBADO | CONDICIONAL.
        Una vez tomada, es inmutable.
        """
        promocion = self._cierre_repo.get_promocion(est_id, anio_id)
        if promocion is None:
            raise ValueError(
                f"No existe registro de promoción para el estudiante {est_id} "
                f"en el año {anio_id}. Ejecute el cierre de año primero."
            )
        datos_ant = promocion.model_dump(mode="json")
        promocion_decidida = promocion.decidir(
            estado               = dto.estado,
            asignaturas_perdidas = dto.asignaturas_perdidas,
            observacion          = dto.observacion,
            usuario_id           = usuario_id,
        )
        self._cierre_repo.actualizar_promocion(promocion_decidida)
        self._auditar(
            AccionCambio.UPDATE, "promociones_anuales", promocion.id,
            datos_ant, promocion_decidida.model_dump(mode="json"), usuario_id,
        )
        return promocion_decidida

    def get_promocion(self, est_id: int, anio_id: int) -> PromocionAnual | None:
        """Retorna el registro de promoción de un estudiante."""
        return self._cierre_repo.get_promocion(est_id, anio_id)

    def get_cierre_periodo(
        self,
        est_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> CierrePeriodo | None:
        """Retorna el cierre de periodo de un estudiante en una asignación."""
        return self._cierre_repo.get_cierre_periodo(est_id, asignacion_id, periodo_id)


__all__ = ["CierreService"]
