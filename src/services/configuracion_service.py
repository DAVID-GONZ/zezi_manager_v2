"""
ConfiguracionService
======================
Orquesta los casos de uso de configuración del año lectivo.
"""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.models.configuracion import (
    ConfiguracionAnio,
    NivelDesempeno,
    CriterioPromocion,
    NuevaConfiguracionAnioDTO,
    ActualizarConfiguracionAnioDTO,
    ActualizarInfoInstitucionalDTO,
    InformacionInstitucionalDTO,
    NuevoNivelDesempenoDTO,
)


class ConfiguracionService:
    """
    Orquesta los casos de uso del módulo de Configuración.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(self, repo: IConfiguracionRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # ConfiguracionAnio
    # ------------------------------------------------------------------

    @requiere_escritura
    def crear_anio(self, dto: NuevaConfiguracionAnioDTO) -> ConfiguracionAnio:
        """
        Crea un año lectivo nuevo.

        Verifica que no exista ya un año con ese número, crea la
        configuración y registra cuántos periodos tendrá.
        """
        if self._repo.get_by_anio(dto.anio) is not None:
            raise ValueError(
                f"Ya existe una configuración para el año {dto.anio}."
            )
        config = dto.to_configuracion()
        config = self._repo.guardar(config)
        # Registrar configuración de 4 periodos con pesos iguales
        self._repo.guardar_numero_periodos(config.id, 4, pesos_iguales=True)
        return config

    @requiere_escritura
    def activar_anio(self, anio_id: int) -> ConfiguracionAnio:
        """
        Activa un año lectivo (solo puede haber uno activo).

        Desactiva el actual activo y activa el indicado.
        """
        config = self._repo.get_by_id(anio_id)
        if config is None:
            raise ValueError(f"No existe configuración con id {anio_id}.")
        self._repo.activar(anio_id)
        return self._repo.get_by_id(anio_id)

    @requiere_escritura
    def actualizar_info_institucional(
        self,
        anio_id: int,
        dto: ActualizarInfoInstitucionalDTO,
    ) -> ConfiguracionAnio:
        """Actualiza los datos institucionales del año indicado."""
        config = self._repo.get_by_id(anio_id)
        if config is None:
            raise ValueError(f"No existe configuración con id {anio_id}.")
        config_actualizada = dto.aplicar_a(config)
        return self._repo.actualizar(config_actualizada)

    def get_activa(self) -> ConfiguracionAnio:
        """Retorna la configuración del año activo. Lanza si no hay activo."""
        config = self._repo.get_activa()
        if config is None:
            raise ValueError(
                "No hay ningún año lectivo activo. "
                "Configure y active un año antes de operar."
            )
        return config

    def get_by_id(self, anio_id: int) -> ConfiguracionAnio:
        """Retorna una configuración por id. Lanza si no existe."""
        config = self._repo.get_by_id(anio_id)
        if config is None:
            raise ValueError(f"No existe configuración con id {anio_id}.")
        return config

    def get_info_institucional(self, anio_id: int) -> InformacionInstitucionalDTO:
        """
        Retorna el DTO de información institucional.
        Lanza ValueError si faltan campos obligatorios para boletines.
        """
        config = self.get_by_id(anio_id)
        return InformacionInstitucionalDTO.desde_configuracion(config)

    # ------------------------------------------------------------------
    # NivelDesempeno
    # ------------------------------------------------------------------

    @requiere_escritura
    def configurar_niveles(
        self,
        anio_id: int,
        niveles: list[NuevoNivelDesempenoDTO],
    ) -> list[NivelDesempeno]:
        """
        Reemplaza los niveles de desempeño del año con los nuevos.

        Valida que:
        - Los rangos no se solapen entre sí.
        - Al menos un nivel cubre el rango completo 0-100.
        """
        if not niveles:
            raise ValueError(
                "Debe especificar al menos un nivel de desempeño."
            )
        # Verificar que el año existe
        self.get_by_id(anio_id)

        # Ordenar por rango_min para facilitar la validación
        ordenados = sorted(niveles, key=lambda n: n.rango_min)

        # Verificar que los rangos no se solapen
        for i in range(len(ordenados) - 1):
            actual = ordenados[i]
            siguiente = ordenados[i + 1]
            if actual.rango_max >= siguiente.rango_min:
                raise ValueError(
                    f"Los rangos de '{actual.nombre}' ({actual.rango_min}–{actual.rango_max}) "
                    f"y '{siguiente.nombre}' ({siguiente.rango_min}–{siguiente.rango_max}) "
                    "se solapan. Los rangos deben ser disjuntos."
                )

        entidades = [
            dto.to_nivel().model_copy(update={"anio_id": anio_id, "orden": i})
            for i, dto in enumerate(ordenados)
        ]
        return self._repo.reemplazar_niveles(anio_id, entidades)

    def listar_niveles(self, anio_id: int) -> list[NivelDesempeno]:
        """Retorna los niveles de desempeño del año."""
        return self._repo.listar_niveles(anio_id)

    # ------------------------------------------------------------------
    # CRUD granular de niveles (sin reconstruir la lista en la vista)
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_rangos_disjuntos(niveles: list[NivelDesempeno]) -> None:
        ordenados = sorted(niveles, key=lambda n: n.rango_min)
        for i in range(len(ordenados) - 1):
            actual, sig = ordenados[i], ordenados[i + 1]
            if actual.rango_max >= sig.rango_min:
                raise ValueError(
                    f"Los rangos de '{actual.nombre}' ({actual.rango_min}–{actual.rango_max}) "
                    f"y '{sig.nombre}' ({sig.rango_min}–{sig.rango_max}) se solapan. "
                    "Los rangos deben ser disjuntos."
                )

    def _reindexar_orden(self, anio_id: int) -> None:
        """Reasigna `orden` por rango_min ascendente tras un alta/baja."""
        niveles = sorted(self._repo.listar_niveles(anio_id), key=lambda n: n.rango_min)
        for i, n in enumerate(niveles):
            if n.orden != i:
                self._repo.actualizar_nivel(n.model_copy(update={"orden": i}))

    @requiere_escritura
    def agregar_nivel(
        self, anio_id: int, dto: NuevoNivelDesempenoDTO
    ) -> NivelDesempeno:
        """Agrega un nivel validando que su rango no se solape con los existentes."""
        self.get_by_id(anio_id)
        existentes = self._repo.listar_niveles(anio_id)
        nuevo = dto.to_nivel().model_copy(
            update={"anio_id": anio_id, "id": None}
        )
        self._validar_rangos_disjuntos(existentes + [nuevo])
        guardado = self._repo.guardar_nivel(nuevo)
        self._reindexar_orden(anio_id)
        return guardado

    @requiere_escritura
    def actualizar_nivel(
        self, anio_id: int, nivel_id: int, dto: NuevoNivelDesempenoDTO
    ) -> NivelDesempeno:
        """Actualiza un nivel concreto validando rangos contra el resto."""
        self.get_by_id(anio_id)
        existentes = self._repo.listar_niveles(anio_id)
        actual = next((n for n in existentes if n.id == nivel_id), None)
        if actual is None:
            raise ValueError(f"El nivel {nivel_id} no existe en el año {anio_id}.")
        modificado = dto.to_nivel().model_copy(
            update={"anio_id": anio_id, "id": nivel_id}
        )
        otros = [n for n in existentes if n.id != nivel_id]
        self._validar_rangos_disjuntos(otros + [modificado])
        guardado = self._repo.actualizar_nivel(modificado)
        self._reindexar_orden(anio_id)
        return guardado

    @requiere_escritura
    def eliminar_nivel(self, anio_id: int, nivel_id: int) -> bool:
        """Elimina un nivel y reindexa el `orden` de los restantes."""
        self.get_by_id(anio_id)
        ok = self._repo.eliminar_nivel(nivel_id)
        if ok:
            self._reindexar_orden(anio_id)
        return ok

    def clasificar_nota(self, nota: float, anio_id: int) -> NivelDesempeno | None:
        """Clasifica una nota en el nivel de desempeño correspondiente."""
        return self._repo.clasificar_nota(nota, anio_id)

    # ------------------------------------------------------------------
    # CriterioPromocion
    # ------------------------------------------------------------------

    def get_criterios(self, anio_id: int) -> CriterioPromocion | None:
        """Retorna los criterios de promoción del año."""
        return self._repo.get_criterios(anio_id)

    @requiere_escritura
    def guardar_criterios(self, criterios: CriterioPromocion) -> CriterioPromocion:
        """Guarda o actualiza los criterios de promoción del año."""
        self.get_by_id(criterios.anio_id)
        return self._repo.guardar_criterios(criterios)

    @requiere_escritura
    def actualizar_configuracion_academica(
        self,
        anio_id: int,
        dto: ActualizarConfiguracionAnioDTO,
    ) -> ConfiguracionAnio:
        """Actualiza campos académicos: nota_minima_aprobacion, nota_minima_escala, nota_maxima_escala, fechas."""
        config = self.get_by_id(anio_id)
        config_actualizada = dto.aplicar_a(config)
        return self._repo.actualizar(config_actualizada)


__all__ = ["ConfiguracionService"]
