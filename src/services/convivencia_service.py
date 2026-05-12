"""
ConvivenciaService
===================
Orquesta los casos de uso del módulo de Convivencia.
"""
from __future__ import annotations

from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.domain.ports.alerta_repo import IAlertaRepository
from src.domain.models.convivencia import (
    FiltroConvivenciaDTO,
    NotaComportamiento,
    NuevaNotaComportamientoDTO,
    NuevaObservacionDTO,
    NuevoRegistroComportamientoDTO,
    ObservacionPeriodo,
    RegistroComportamiento,
    TipoRegistro,
)
from src.domain.models.alerta import Alerta, TipoAlerta, NivelAlerta


class ConvivenciaService:
    """
    Orquesta los casos de uso del módulo de Convivencia.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IConvivenciaRepository,
        alerta_repo: IAlertaRepository | None = None,
    ) -> None:
        self._repo        = repo
        self._alerta_repo = alerta_repo

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_registro_o_lanzar(self, registro_id: int) -> RegistroComportamiento:
        reg = self._repo.get_registro(registro_id)
        if reg is None:
            raise ValueError(
                f"Registro de comportamiento con id {registro_id} no existe."
            )
        return reg

    def _get_observacion_o_lanzar(self, observacion_id: int) -> ObservacionPeriodo:
        obs = self._repo.get_observacion(observacion_id)
        if obs is None:
            raise ValueError(
                f"Observación con id {observacion_id} no existe."
            )
        return obs

    def _verificar_alerta_comportamiento(
        self,
        estudiante_id: int,
        anio_id: int,
        filtro: FiltroConvivenciaDTO,
    ) -> None:
        """
        Genera una alerta si el número de registros negativos supera el umbral.
        Solo actúa si el repositorio de alertas está disponible.
        """
        if self._alerta_repo is None:
            return

        cfg = self._alerta_repo.get_configuracion(
            anio_id, TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO
        )
        # Reutilizamos un tipo de alerta apropiado; en ausencia de tipo específico
        # para comportamiento, se omite la alerta.
        if cfg is None or not cfg.activa:
            return

        conteo = self._repo.contar_registros(filtro)
        if conteo < cfg.umbral:
            return

        if self._alerta_repo.existe_pendiente(
            estudiante_id, TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO
        ):
            return

        nivel = (
            NivelAlerta.CRITICA
            if conteo >= cfg.umbral * 2
            else NivelAlerta.ADVERTENCIA
        )
        alerta = Alerta(
            estudiante_id=estudiante_id,
            tipo_alerta=TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO,
            nivel=nivel,
            descripcion=(
                f"El estudiante tiene {conteo} registro(s) negativos de comportamiento "
                f"(umbral configurado: {int(cfg.umbral)})."
            ),
        )
        self._alerta_repo.guardar_alerta(alerta)

    # ------------------------------------------------------------------
    # Observaciones de periodo
    # ------------------------------------------------------------------

    def registrar_observacion(
        self,
        dto: NuevaObservacionDTO,
        usuario_id: int | None = None,
    ) -> ObservacionPeriodo:
        """
        Registra una observación narrativa de un estudiante en un periodo.

        Si ya existe una observación para esa asignación/periodo/estudiante,
        se actualiza; si no, se crea una nueva.
        """
        existente = self._repo.get_observacion_por_asignacion(
            dto.estudiante_id, dto.asignacion_id, dto.periodo_id
        )

        if existente is not None:
            obs_actualizada = existente.model_copy(
                update={"texto": dto.texto, "es_publica": dto.es_publica}
            )
            return self._repo.actualizar_observacion(obs_actualizada)

        observacion = dto.to_observacion(usuario_id=usuario_id)
        return self._repo.guardar_observacion(observacion)

    def listar_observaciones(
        self,
        estudiante_id: int,
        periodo_id: int | None = None,
        solo_publicas: bool = False,
    ) -> list[ObservacionPeriodo]:
        """Retorna las observaciones de un estudiante."""
        return self._repo.listar_observaciones_por_estudiante(
            estudiante_id, periodo_id, solo_publicas
        )

    def eliminar_observacion(self, observacion_id: int) -> bool:
        """Elimina una observación. Retorna True si fue eliminada."""
        self._get_observacion_o_lanzar(observacion_id)
        return self._repo.eliminar_observacion(observacion_id)

    # ------------------------------------------------------------------
    # Registros de comportamiento
    # ------------------------------------------------------------------

    def registrar_comportamiento(
        self,
        dto: NuevoRegistroComportamientoDTO,
        usuario_id: int | None = None,
        anio_id: int | None = None,
    ) -> RegistroComportamiento:
        """
        Registra un evento puntual de comportamiento.

        Después de guardar, verifica si se deben generar alertas para
        el estudiante (si hay repositorio de alertas y anio_id disponibles).
        """
        registro = dto.to_registro(usuario_id=usuario_id)
        registro = self._repo.guardar_registro(registro)

        # Verificar alertas si el registro es negativo
        if anio_id is not None and registro.es_negativo:
            filtro = FiltroConvivenciaDTO(
                estudiante_id=dto.estudiante_id,
                periodo_id=dto.periodo_id,
                solo_negativos=True,
            )
            self._verificar_alerta_comportamiento(
                dto.estudiante_id, anio_id, filtro
            )

        return registro

    def notificar_acudiente(self, registro_id: int) -> RegistroComportamiento:
        """
        Marca un registro de comportamiento como notificado al acudiente.

        Transición de estado: acudiente_notificado=False → True.
        Lanza si el registro no existe o ya fue notificado.
        """
        registro = self._get_registro_o_lanzar(registro_id)
        registro_notificado = registro.registrar_notificacion()
        return self._repo.actualizar_registro(registro_notificado)

    def agregar_seguimiento(
        self,
        registro_id: int,
        texto: str,
    ) -> RegistroComportamiento:
        """Agrega o actualiza el texto de seguimiento de un registro."""
        registro = self._get_registro_o_lanzar(registro_id)
        registro_con_seguimiento = registro.agregar_seguimiento(texto)
        return self._repo.actualizar_registro(registro_con_seguimiento)

    def listar_registros(
        self,
        filtro: FiltroConvivenciaDTO,
    ) -> list[RegistroComportamiento]:
        """Retorna registros de comportamiento según los filtros indicados."""
        return self._repo.listar_registros(filtro)

    def eliminar_registro(self, registro_id: int) -> bool:
        """Elimina un registro de comportamiento. Retorna True si fue eliminado."""
        self._get_registro_o_lanzar(registro_id)
        return self._repo.eliminar_registro(registro_id)

    # ------------------------------------------------------------------
    # Notas de comportamiento
    # ------------------------------------------------------------------

    def registrar_nota_comportamiento(
        self,
        dto: NuevaNotaComportamientoDTO,
        usuario_id: int | None = None,
    ) -> NotaComportamiento:
        """
        Registra o actualiza la nota de comportamiento de un estudiante
        en un periodo (upsert: una nota por estudiante/grupo/periodo).
        """
        nota = dto.to_nota(usuario_id=usuario_id)
        return self._repo.guardar_nota(nota)

    def get_nota_comportamiento(
        self,
        estudiante_id: int,
        periodo_id: int,
    ) -> NotaComportamiento | None:
        """Retorna la nota de comportamiento de un estudiante en un periodo."""
        return self._repo.get_nota(estudiante_id, periodo_id)

    def listar_notas_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
    ) -> list[NotaComportamiento]:
        """Retorna las notas de comportamiento de todos los estudiantes del grupo."""
        return self._repo.listar_notas_por_grupo(grupo_id, periodo_id)


__all__ = ["ConvivenciaService"]
