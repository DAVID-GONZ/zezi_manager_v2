"""
PeriodoService
================
Orquesta los casos de uso del módulo de Periodos académicos.
"""
from __future__ import annotations

from datetime import datetime

from src.domain.ports.periodo_repo import IPeriodoRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.models.periodo import (
    HitoPeriodo,
    NuevoPeriodoDTO,
    NuevoHitoPeriodoDTO,
    Periodo,
)
from src.domain.models.auditoria import AccionCambio, RegistroCambio


class PeriodoService:
    """
    Orquesta los casos de uso del módulo de Periodos académicos.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IPeriodoRepository,
        config_repo: IConfiguracionRepository | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        self._repo        = repo
        self._config_repo = config_repo
        self._auditoria   = auditoria

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

    def _get_periodo_o_lanzar(self, periodo_id: int) -> Periodo:
        periodo = self._repo.get_by_id(periodo_id)
        if periodo is None:
            raise ValueError(f"Periodo con id {periodo_id} no existe.")
        return periodo

    # ------------------------------------------------------------------
    # Casos de uso — periodos
    # ------------------------------------------------------------------

    def crear_periodo(self, dto: NuevoPeriodoDTO) -> Periodo:
        """
        Crea un periodo académico nuevo.

        Verifica:
        - Que el anio_id tenga configuración activa.
        - Que el número no exista ya en el año.
        - Que la suma de pesos + dto.peso_porcentual <= 100.
        """
        # Verificar config activa
        if self._config_repo is not None:
            config = self._config_repo.get_by_id(dto.anio_id)
            if config is None:
                raise ValueError(
                    f"No existe configuración de año con id {dto.anio_id}."
                )

        # Verificar número único en el año
        existente = self._repo.get_por_numero(dto.anio_id, dto.numero)
        if existente is not None:
            raise ValueError(
                f"Ya existe el período {dto.numero} en el año {dto.anio_id}."
            )

        # Verificar suma de pesos
        suma_actual = self._repo.suma_pesos_otros(dto.anio_id)
        if suma_actual + dto.peso_porcentual > 100.01:
            raise ValueError(
                f"La suma de pesos de los períodos supera el 100% "
                f"(actual: {suma_actual:.1f}%, nuevo: {dto.peso_porcentual:.1f}%)."
            )

        periodo = dto.to_periodo()
        periodo = self._repo.guardar(periodo)
        self._auditar(
            AccionCambio.CREATE, "periodos", periodo.id,
            None, periodo.model_dump(mode="json"), None,
        )
        return periodo

    def cerrar_periodo(
        self,
        periodo_id: int,
        usuario_id: int | None = None,
    ) -> Periodo:
        """Cierra un periodo para que no acepte más notas ni asistencia."""
        periodo = self._get_periodo_o_lanzar(periodo_id)
        datos_ant = periodo.model_dump(mode="json")
        periodo_cerrado = periodo.cerrar(datetime.now())
        self._repo.actualizar(periodo_cerrado)
        self._auditar(
            AccionCambio.UPDATE, "periodos", periodo_id,
            datos_ant, periodo_cerrado.model_dump(mode="json"), usuario_id,
        )
        return periodo_cerrado

    def activar_periodo(self, periodo_id: int) -> Periodo:
        """Activa un periodo para que sea el periodo de trabajo actual."""
        periodo = self._get_periodo_o_lanzar(periodo_id)
        periodo_activo = periodo.activar()  # lanza si está cerrado o ya activo
        self._repo.actualizar(periodo_activo)
        return periodo_activo

    def listar_por_anio(self, anio_id: int) -> list[Periodo]:
        """Retorna todos los periodos del año, ordenados por número."""
        return self._repo.listar_por_anio(anio_id)

    def get_activo(self, anio_id: int) -> Periodo:
        """Retorna el periodo activo del año. Lanza si no hay activo."""
        periodo = self._repo.get_activo(anio_id)
        if periodo is None:
            raise ValueError(
                f"No hay ningún periodo activo para el año {anio_id}."
            )
        return periodo

    def get_by_id(self, periodo_id: int) -> Periodo:
        """Retorna un periodo por id. Lanza si no existe."""
        return self._get_periodo_o_lanzar(periodo_id)

    # ------------------------------------------------------------------
    # Casos de uso — hitos
    # ------------------------------------------------------------------

    def agregar_hito(
        self,
        dto: NuevoHitoPeriodoDTO,
        usuario_id: int | None = None,
    ) -> HitoPeriodo:
        """
        Agrega un hito (fecha límite) a un periodo.

        Verifica que el periodo existe y está abierto.
        """
        periodo = self._get_periodo_o_lanzar(dto.periodo_id)
        if not periodo.esta_abierto:
            raise ValueError(
                f"No se puede agregar un hito al periodo '{periodo.nombre}' "
                "porque ya está cerrado."
            )
        hito = dto.to_hito()
        return self._repo.guardar_hito(hito)


__all__ = ["PeriodoService"]
