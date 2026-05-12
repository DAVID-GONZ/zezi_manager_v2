"""
AlertaService
==============
Orquesta los casos de uso del módulo de Alertas.
"""
from __future__ import annotations

from datetime import datetime

from src.domain.ports.alerta_repo import IAlertaRepository
from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.domain.models.alerta import (
    Alerta,
    ConfiguracionAlerta,
    FiltroAlertasDTO,
    NivelAlerta,
    TipoAlerta,
)


class AlertaService:
    """
    Orquesta los casos de uso del módulo de Alertas.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IAlertaRepository,
        estadisticos_repo: IEstadisticosRepository | None = None,
    ) -> None:
        self._repo              = repo
        self._estadisticos_repo = estadisticos_repo

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_alerta_o_lanzar(self, alerta_id: int) -> Alerta:
        alerta = self._repo.get_alerta(alerta_id)
        if alerta is None:
            raise ValueError(f"Alerta con id {alerta_id} no existe.")
        return alerta

    # ------------------------------------------------------------------
    # Configuración de alertas
    # ------------------------------------------------------------------

    def configurar_alerta(
        self,
        config: ConfiguracionAlerta,
    ) -> ConfiguracionAlerta:
        """
        Guarda o actualiza la configuración de un tipo de alerta para un año.

        Verifica que el umbral sea positivo (el modelo Pydantic lo valida).
        """
        return self._repo.guardar_configuracion(config)

    def desactivar_configuracion(
        self,
        anio_id: int,
        tipo_alerta: TipoAlerta,
    ) -> bool:
        """Desactiva una configuración de alerta. Retorna True si fue desactivada."""
        return self._repo.desactivar_configuracion(anio_id, tipo_alerta)

    def listar_configuraciones(
        self,
        anio_id: int,
        solo_activas: bool = True,
    ) -> list[ConfiguracionAlerta]:
        """Retorna las configuraciones de alerta de un año."""
        return self._repo.listar_configuraciones(anio_id, solo_activas)

    def get_configuracion(
        self,
        anio_id: int,
        tipo_alerta: TipoAlerta,
    ) -> ConfiguracionAlerta | None:
        """Retorna la configuración de un tipo de alerta para un año."""
        return self._repo.get_configuracion(anio_id, tipo_alerta)

    # ------------------------------------------------------------------
    # Alertas
    # ------------------------------------------------------------------

    def listar_alertas(
        self,
        filtro: FiltroAlertasDTO,
    ) -> list[Alerta]:
        """Retorna alertas según los filtros indicados."""
        return self._repo.listar_alertas(filtro)

    def contar_pendientes(
        self,
        estudiante_id: int | None = None,
        nivel: NivelAlerta | None = None,
    ) -> int:
        """Cuenta las alertas pendientes del sistema o de un estudiante."""
        return self._repo.contar_pendientes(estudiante_id, nivel)

    def resolver_alerta(
        self,
        alerta_id: int,
        usuario_id: int,
        observacion: str | None = None,
    ) -> bool:
        """
        Resuelve una alerta existente.

        Lanza si la alerta no existe.
        Retorna True si la fila fue afectada.
        """
        alerta = self._get_alerta_o_lanzar(alerta_id)
        if alerta.resuelta:
            raise ValueError(
                f"La alerta con id {alerta_id} ya está resuelta."
            )
        return self._repo.resolver_alerta(
            alerta_id, usuario_id, observacion, datetime.now()
        )

    def resolver_alertas_de_estudiante(
        self,
        estudiante_id: int,
        tipo_alerta: TipoAlerta,
        usuario_id: int,
        observacion: str | None = None,
    ) -> int:
        """
        Resuelve todas las alertas pendientes de un tipo para un estudiante.

        Retorna el número de alertas resueltas.
        """
        return self._repo.resolver_alertas_de_estudiante(
            estudiante_id, tipo_alerta, usuario_id, observacion
        )

    # ------------------------------------------------------------------
    # Detección automática de riesgo académico
    # ------------------------------------------------------------------

    def detectar_riesgo_academico(
        self,
        grupo_id: int,
        periodo_id: int,
        anio_id: int,
        nota_minima: float = 60.0,
        min_asignaturas: int = 1,
    ) -> int:
        """
        Detecta estudiantes en riesgo académico y genera alertas masivas.

        Usa el repositorio de estadísticos para identificar estudiantes con
        varias asignaturas por debajo de la nota mínima. Solo genera alertas
        para estudiantes que no tienen una alerta pendiente del mismo tipo.

        Retorna el número de alertas generadas.
        """
        if self._estadisticos_repo is None:
            return 0

        cfg = self._repo.get_configuracion(
            anio_id, TipoAlerta.MATERIAS_EN_RIESGO
        )
        if cfg is None or not cfg.activa:
            return 0

        estudiantes_riesgo = self._estadisticos_repo.estudiantes_en_riesgo_academico(
            grupo_id, periodo_id, nota_minima, min_asignaturas
        )

        alertas_nuevas: list[Alerta] = []
        for est_id in estudiantes_riesgo:
            if self._repo.existe_pendiente(est_id, TipoAlerta.MATERIAS_EN_RIESGO):
                continue
            alerta = Alerta(
                estudiante_id=est_id,
                tipo_alerta=TipoAlerta.MATERIAS_EN_RIESGO,
                nivel=NivelAlerta.ADVERTENCIA,
                descripcion=(
                    f"El estudiante tiene {min_asignaturas} o más asignaturas "
                    f"con promedio inferior a {nota_minima:.1f}."
                ),
            )
            alertas_nuevas.append(alerta)

        if alertas_nuevas:
            return self._repo.guardar_alertas_masivas(alertas_nuevas)
        return 0


__all__ = ["AlertaService"]
