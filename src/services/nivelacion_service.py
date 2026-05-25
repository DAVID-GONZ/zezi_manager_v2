"""
NivelacionService
==================
Orquesta los casos de uso del módulo de Nivelación.
Sin SQL. Sin lógica de presentación.
"""
from __future__ import annotations

from datetime import date

from src.domain.ports.nivelacion_repo import INivelacionRepository
from src.domain.ports.cierre_repo import ICierreRepository
from src.domain.ports.configuracion_repo import IConfiguracionRepository
from src.domain.models.nivelacion import (
    ActividadNivelacion,
    CalificarNotaNivelacionDTO,
    CalculadorNivelacion,
    CierreNivelacion,
    NotaNivelacion,
    NuevaActividadNivelacionDTO,
)
from src.domain.models.cierre import CierrePeriodo


class NivelacionService:
    """
    Casos de uso para el módulo de nivelación.

    Flujo nominal:
      1. listar_bajo_desempeno() — detecta estudiantes bajo el umbral
      2. agregar_actividad()     — crea columna + notas vacías para cada estudiante
      3. calificar_nota()        — registra la nota de un estudiante en una actividad
      4. cerrar_nivelacion()     — valida y persiste el CierreNivelacion
    """

    def __init__(
        self,
        repo: INivelacionRepository,
        cierre_repo: ICierreRepository,
        config_repo: IConfiguracionRepository | None = None,
    ) -> None:
        self._repo        = repo
        self._cierre_repo = cierre_repo
        self._config_repo = config_repo

    # ------------------------------------------------------------------
    # Detección de bajo desempeño
    # ------------------------------------------------------------------

    def listar_bajo_desempeno(
        self,
        asignacion_ids: list[int],
        periodo_id: int,
        nota_maxima: float | None = None,
    ) -> list[CierrePeriodo]:
        """
        Retorna cierres de período con nota ≤ nota_maxima (bajo desempeño).
        Si nota_maxima es None, usa nota_minima_aprobacion de configuracion_anio
        (default 60.0 si no hay config).
        """
        if nota_maxima is None:
            nota_maxima = self._get_nota_minima() - 0.01  # estrictamente menor
        if not asignacion_ids:
            return []
        return self._cierre_repo.listar_cierres_periodo_por_asignaciones(
            asignacion_ids=asignacion_ids,
            periodo_id=periodo_id,
            nota_maxima=nota_maxima,
        )

    def _get_nota_minima(self) -> float:
        if self._config_repo is None:
            return 60.0
        config = self._config_repo.get_activa()
        if config is None:
            return 60.0
        return config.nota_minima_aprobacion

    # ------------------------------------------------------------------
    # Actividades
    # ------------------------------------------------------------------

    def listar_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ActividadNivelacion]:
        """Lista actividades de nivelación para una asignacion+periodo."""
        return self._repo.listar_actividades(asignacion_id, periodo_id)

    def agregar_actividad(
        self,
        dto: NuevaActividadNivelacionDTO,
        estudiante_ids: list[int],
        usuario_id: int | None = None,
    ) -> ActividadNivelacion:
        """
        Crea una actividad de nivelación y genera NotaNivelacion vacías
        para cada estudiante de bajo desempeño.

        Valida que la suma de pesos no supere 1.0.
        No valida que sume exactamente 1.0 (eso es responsabilidad de cerrar_nivelacion).

        Args:
            dto:             Datos de la nueva actividad.
            estudiante_ids:  IDs de los estudiantes bajo desempeño para esta asignacion+periodo.
            usuario_id:      Docente que crea la actividad.

        Returns:
            ActividadNivelacion creada (con id).

        Raises:
            ValueError: Si al agregar el nuevo peso la suma supera 1.0.
        """
        # Validar que la suma de pesos existente + nuevo peso no supera 1.0
        suma_actual = self._repo.suma_pesos_actividades(
            dto.asignacion_id, dto.periodo_id
        )
        if round(suma_actual + dto.peso, 4) > 1.001:
            raise ValueError(
                f"Agregar esta actividad (peso={dto.peso:.0%}) supera el 100% "
                f"— pesos actuales: {suma_actual:.0%}."
            )

        # Crear la actividad
        actividad = dto.to_actividad(usuario_id=usuario_id)
        actividad = self._repo.guardar_actividad(actividad)

        # Generar NotaNivelacion vacías para cada estudiante
        for est_id in estudiante_ids:
            nota = NotaNivelacion(
                actividad_nivelacion_id=actividad.id,
                estudiante_id=est_id,
                asignacion_id=dto.asignacion_id,
                periodo_id=dto.periodo_id,
                valor=None,
                usuario_id=usuario_id,
            )
            self._repo.guardar_nota(nota)

        return actividad

    # ------------------------------------------------------------------
    # Notas
    # ------------------------------------------------------------------

    def listar_notas(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[NotaNivelacion]:
        """Lista todas las notas de nivelación para una asignacion+periodo."""
        return self._repo.listar_notas_por_asignacion(asignacion_id, periodo_id)

    def calificar_nota(
        self,
        actividad_nivelacion_id: int,
        estudiante_id: int,
        dto: CalificarNotaNivelacionDTO,
    ) -> NotaNivelacion:
        """
        Registra o actualiza la nota de un estudiante en una actividad.

        Raises:
            ValueError: Si la nivelación ya está cerrada o la nota no existe.
        """
        nota = self._repo.get_nota(actividad_nivelacion_id, estudiante_id)
        if nota is None:
            raise ValueError(
                f"No existe registro de nivelación para el estudiante {estudiante_id} "
                f"en la actividad {actividad_nivelacion_id}."
            )
        # Verificar que la nivelación no esté cerrada
        cierre = self._repo.get_cierre(nota.asignacion_id, nota.periodo_id)
        if cierre is not None:
            raise ValueError(
                "La nivelación ya está cerrada. No se pueden modificar notas."
            )
        nota_actualizada = nota.model_copy(update={
            "valor":      dto.valor,
            "usuario_id": dto.usuario_id or nota.usuario_id,
        })
        return self._repo.actualizar_nota(nota_actualizada)

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------

    def get_cierre(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> CierreNivelacion | None:
        """Retorna el cierre si existe (nivelación cerrada), None si está abierta."""
        return self._repo.get_cierre(asignacion_id, periodo_id)

    def cerrar_nivelacion(
        self,
        asignacion_id: int,
        periodo_id: int,
        usuario_id: int | None = None,
    ) -> CierreNivelacion:
        """
        Cierra la nivelación para una asignacion+periodo.

        Validaciones:
          1. No esté ya cerrada.
          2. Existan actividades.
          3. Los pesos sumen 1.0 (tolerancia 0.005).
          4. Todas las notas estén calificadas (valor is not None).

        Raises:
            ValueError: Si alguna validación falla.
        """
        # 1. ¿Ya cerrada?
        existente = self._repo.get_cierre(asignacion_id, periodo_id)
        if existente is not None:
            raise ValueError(
                "La nivelación ya fue cerrada para esta asignación y período."
            )

        # 2. Actividades existentes
        actividades = self._repo.listar_actividades(asignacion_id, periodo_id)
        if not actividades:
            raise ValueError(
                "No hay actividades de nivelación registradas. "
                "Agregue al menos una actividad antes de cerrar."
            )

        # 3. Pesos suman 1.0
        if not CalculadorNivelacion.pesos_completos(actividades):
            suma = CalculadorNivelacion.suma_pesos(actividades)
            raise ValueError(
                f"Los pesos de las actividades suman {suma:.0%} — deben sumar 100% "
                "para poder cerrar la nivelación."
            )

        # 4. Todas las notas calificadas
        notas = self._repo.listar_notas_por_asignacion(asignacion_id, periodo_id)
        pendientes = [n for n in notas if n.valor is None]
        if pendientes:
            raise ValueError(
                f"Hay {len(pendientes)} nota(s) sin calificar. "
                "Complete todas las notas antes de cerrar."
            )

        # Persistir cierre
        cierre = CierreNivelacion(
            asignacion_id=asignacion_id,
            periodo_id=periodo_id,
            fecha_cierre=date.today(),
            usuario_cierre_id=usuario_id,
        )
        return self._repo.guardar_cierre(cierre)

    def calcular_nota_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int,
        periodo_id: int,
    ) -> float | None:
        """
        Calcula la nota definitiva de nivelación de un estudiante.
        Retorna None si hay actividades sin calificar o no hay actividades.
        """
        actividades = self._repo.listar_actividades(asignacion_id, periodo_id)
        notas = [
            n for n in self._repo.listar_notas_por_asignacion(asignacion_id, periodo_id)
            if n.estudiante_id == estudiante_id
        ]
        return CalculadorNivelacion.nota_definitiva(notas, actividades)


__all__ = [
    "NivelacionService",
    # Re-exports para la capa de interfaz
    "ActividadNivelacion",
    "NotaNivelacion",
    "CierreNivelacion",
    "NuevaActividadNivelacionDTO",
    "CalificarNotaNivelacionDTO",
    "CierrePeriodo",
]
