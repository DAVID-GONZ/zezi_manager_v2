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
    RegistroAsistenciaItemDTO,
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
        return self._repo.get_por_fecha_estudiante(
            estudiante_id, asignacion_id, fecha
        )

    def listar_por_grupo_y_fecha(
        self,
        grupo_id: int,
        asignacion_id: int,
        fecha: object,
    ) -> list[ControlDiario]:
        """
        Retorna todos los registros de asistencia de un grupo en una fecha.
        Usado internamente y por informes que necesitan ControlDiario completo.
        """
        return self._repo.listar_por_grupo_y_fecha(grupo_id, asignacion_id, fecha)

    # ------------------------------------------------------------------
    # API primitiva para la capa de interfaz
    # La UI solo importa Container; nunca construye ni importa modelos
    # de dominio. Estos métodos actúan como anti-corruption layer.
    # ------------------------------------------------------------------

    def estados_por_grupo_y_fecha(
        self,
        grupo_id: int,
        asignacion_id: int,
        fecha: object,
    ) -> dict[int, dict[str, str]]:
        """
        Retorna {estudiante_id: {"estado": "P"|"FJ"|..., "observacion": str}}
        para todos los registros existentes de un grupo en una fecha.

        La capa de interfaz usa este método para pre-cargar la grilla sin
        necesitar importar ControlDiario ni EstadoAsistencia.
        Si no hay registros, retorna dict vacío.
        """
        controles = self._repo.listar_por_grupo_y_fecha(grupo_id, asignacion_id, fecha)
        return {
            c.estudiante_id: {
                "estado":      c.estado.value,
                "observacion": c.observacion or "",
            }
            for c in controles
        }

    def guardar_asistencia_masiva(
        self,
        grupo_id: int,
        asignacion_id: int,
        periodo_id: int,
        fecha: object,
        lista: list[dict],
        usuario_id: int | None = None,
        anio_id:    int | None = None,
    ) -> int:
        """
        Persiste la asistencia de un grupo a partir de una lista de dicts
        primitivos. La capa de interfaz llama este método en lugar de
        construir RegistrarAsistenciaMasivaDTO directamente.

        Args:
            lista: [{"estudiante_id": int, "estado": str, "observacion": str|None}]
                   "estado" debe ser un código válido: "P","FJ","FI","R","E".

        Returns:
            Número de registros guardados.

        Raises:
            ValueError: si algún código de estado es inválido o la lista
                        está vacía (propagado desde el DTO de dominio).
        """
        items = [
            RegistroAsistenciaItemDTO(
                estudiante_id = r["estudiante_id"],
                estado        = EstadoAsistencia(r["estado"]),
                observacion   = r.get("observacion") or None,
            )
            for r in lista
        ]
        dto = RegistrarAsistenciaMasivaDTO(
            grupo_id            = grupo_id,
            asignacion_id       = asignacion_id,
            periodo_id          = periodo_id,
            fecha               = fecha,
            registros           = items,
            usuario_registro_id = usuario_id,
        )
        return self.registrar_masivo(dto, usuario_id=usuario_id, anio_id=anio_id)


    def contar_clases_mes(self, usuario_id: int, anio: int, mes: int) -> int:
        """
        Retorna el total de clases dictadas por el docente en el mes indicado.
        Raises ValueError si mes está fuera del rango 1–12.
        """
        if not 1 <= mes <= 12:
            raise ValueError("Mes fuera de rango (1–12).")
        return self._repo.contar_clases_dictadas_docente(usuario_id, anio, mes)

    def clases_mes_por_asignacion(self, usuario_id: int, anio: int, mes: int) -> dict[int, int]:
        """
        Retorna el desglose {asignacion_id: n_clases} para el docente en el mes.
        Raises ValueError si mes está fuera del rango 1–12.
        """
        if not 1 <= mes <= 12:
            raise ValueError("Mes fuera de rango (1–12).")
        return self._repo.clases_dictadas_por_asignacion(usuario_id, anio, mes)


__all__ = ["AsistenciaService"]
