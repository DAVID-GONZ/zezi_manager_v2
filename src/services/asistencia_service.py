"""
AsistenciaService
==================
Orquesta los casos de uso del módulo de Asistencia.
"""
from __future__ import annotations

from src.domain.ports.asistencia_repo import IAsistenciaRepository
from src.domain.ports.alerta_repo import IAlertaRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.models.asistencia import (
    ControlDiario,
    EstadoAsistencia,
    RegistrarAsistenciaDTO,
    RegistrarAsistenciaMasivaDTO,
    ResumenAsistenciaDTO,
)
from src.domain.models.alerta import Alerta, TipoAlerta, NivelAlerta


class AsistenciaService:
    """
    Orquesta los casos de uso del módulo de Asistencia.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IAsistenciaRepository,
        alerta_repo: IAlertaRepository | None = None,
        config_repo: IConfiguracionRepository | None = None,
    ) -> None:
        self._repo       = repo
        self._alerta_repo = alerta_repo
        self._config_repo = config_repo

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _verificar_alerta_asistencia(
        self,
        estudiante_id: int,
        periodo_id: int,
        anio_id: int,
    ) -> None:
        """
        Genera una alerta de faltas injustificadas si se supera el umbral.
        Solo actúa si el repositorio de alertas está disponible.
        """
        if self._alerta_repo is None:
            return

        cfg = self._alerta_repo.get_configuracion(
            anio_id, TipoAlerta.FALTAS_INJUSTIFICADAS
        )
        if cfg is None or not cfg.activa:
            return

        conteo = self._repo.contar_faltas_injustificadas(
            estudiante_id, periodo_id
        )

        if conteo < cfg.umbral:
            return

        if self._alerta_repo.existe_pendiente(
            estudiante_id, TipoAlerta.FALTAS_INJUSTIFICADAS
        ):
            return

        # Determinar nivel
        nivel = (
            NivelAlerta.CRITICA
            if conteo >= cfg.umbral * 2
            else NivelAlerta.ADVERTENCIA
        )
        alerta = Alerta(
            estudiante_id=estudiante_id,
            tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
            nivel=nivel,
            descripcion=(
                f"El estudiante tiene {conteo} falta(s) injustificada(s) "
                f"(umbral configurado: {int(cfg.umbral)})."
            ),
        )
        self._alerta_repo.guardar_alerta(alerta)

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    def registrar(
        self,
        dto: RegistrarAsistenciaDTO,
        usuario_id: int | None = None,
    ) -> ControlDiario:
        """
        Registra un control de asistencia individual.

        Si el estado es FI, verifica si se debe generar una alerta.
        """
        control = dto.to_control()
        control = self._repo.registrar(control)
        return control

    def registrar_masivo(
        self,
        dto: RegistrarAsistenciaMasivaDTO,
        usuario_id: int | None = None,
        anio_id: int | None = None,
    ) -> int:
        """
        Registra la asistencia de todos los estudiantes de un grupo.

        Después de registrar, verifica alertas para los estudiantes
        con falta injustificada.

        Retorna el número de registros guardados.
        """
        controles = dto.to_controles()
        conteo = self._repo.registrar_masivo(controles)

        # Verificar alertas para estudiantes con FI
        if anio_id is not None and controles:
            periodo_id = controles[0].periodo_id
            for ctrl in controles:
                if ctrl.estado == EstadoAsistencia.FALTA_INJUSTIFICADA:
                    self._verificar_alerta_asistencia(
                        ctrl.estudiante_id, periodo_id, anio_id
                    )

        return conteo

    def resumen_estudiante(
        self,
        estudiante_id: int,
        periodo_id: int,
        asignacion_id: int | None = None,
    ) -> ResumenAsistenciaDTO:
        """Retorna el resumen de asistencia de un estudiante en un periodo."""
        return self._repo.resumen_por_estudiante(
            estudiante_id, periodo_id, asignacion_id
        )

    def resumen_grupo(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ResumenAsistenciaDTO]:
        """Retorna el resumen de asistencia de todos los estudiantes del grupo."""
        return self._repo.resumen_por_grupo(grupo_id, asignacion_id, periodo_id)

    def get_por_fecha(
        self,
        estudiante_id: int,
        grupo_id: int,
        asignacion_id: int,
        fecha: object,
    ) -> ControlDiario | None:
        """Retorna el registro de asistencia de un estudiante en una fecha."""
        return self._repo.get_por_fecha(
            estudiante_id, grupo_id, asignacion_id, fecha
        )


__all__ = ["AsistenciaService"]
