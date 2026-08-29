"""
Port: IConvivenciaRepository
============================
Contrato de acceso a datos para el módulo de convivencia.

Cubre:
  ObservacionPeriodo     — Texto narrativo (público o privado) en el periodo.
  RegistroComportamiento — Eventos puntuales (fortalezas, dificultades, descargos, etc.).
  NotaComportamiento     — Calificación cuantitativa de convivencia por periodo.

Patrones de uso principales:

  Registrar un evento disciplinario:
    registro = repo.guardar_registro(nuevo_registro)

  Actualizar un registro (ej. notificar acudiente o agregar seguimiento):
    repo.actualizar_registro(registro_modificado)

  Guardar o actualizar nota de comportamiento (Upsert):
    repo.guardar_nota(nueva_nota)

  Listar historial de un estudiante:
    registros = repo.listar_registros(FiltroConvivenciaDTO(estudiante_id=est_id))
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.tenant import TenantScope
from ..models.convivencia import (
    CategoriaObservacion,
    EntradaSeguimiento,
    FiltroConvivenciaDTO,
    MedidaPedagogica,
    NotaComportamiento,
    ObservacionPeriodo,
    PlantillaObservacion,
    RegistroComportamiento,
    TipoSituacion,
)


class IConvivenciaRepository(ABC):
    # =========================================================================
    # Observaciones de Periodo
    # =========================================================================

    @abstractmethod
    def get_observacion(self, observacion_id: int) -> ObservacionPeriodo | None:
        """Retorna una observación por su ID, o None si no existe."""
        ...

    @abstractmethod
    def get_observacion_por_asignacion(
        self, estudiante_id: int, asignacion_id: int, periodo_id: int
    ) -> ObservacionPeriodo | None:
        """
        Retorna la observación de una asignatura específica en un periodo.
        Solo debería haber una observación por asignatura/periodo/estudiante.
        """
        ...

    @abstractmethod
    def listar_observaciones_por_estudiante(
        self, estudiante_id: int, periodo_id: int | None = None, solo_publicas: bool = False
    ) -> list[ObservacionPeriodo]:
        """
        Retorna las observaciones de un estudiante.
        Si se especifica periodo_id, filtra por ese periodo.
        Si solo_publicas es True, omite las observaciones privadas.
        """
        ...

    @abstractmethod
    def listar_observaciones_por_grupo(
        self, grupo_id: int, periodo_id: int | None = None, solo_publicas: bool = False
    ) -> list[ObservacionPeriodo]:
        """
        Retorna las observaciones de todos los estudiantes de un grupo,
        resolviendo el grupo vía join a `asignaciones` (por `asignacion_id`).

        Batch para el hub de Seguimiento (convivencia_21): evita el patrón N+1
        de pedir observaciones estudiante por estudiante.
        Si se especifica periodo_id, filtra por ese periodo.
        Si solo_publicas es True, omite las observaciones privadas.
        """
        ...

    @abstractmethod
    def guardar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo:
        """
        Guarda una nueva observación.
        Retorna la entidad con su id asignado.
        """
        ...

    @abstractmethod
    def actualizar_observacion(self, observacion: ObservacionPeriodo) -> ObservacionPeriodo:
        """
        Actualiza una observación existente (texto o visibilidad).
        Requiere que observacion.id no sea None.
        """
        ...

    @abstractmethod
    def eliminar_observacion(self, observacion_id: int) -> bool:
        """
        Elimina (o desactiva lógicamente) una observación.
        Retorna True si fue eliminada.
        """
        ...

    # =========================================================================
    # Registros de Comportamiento
    # =========================================================================

    @abstractmethod
    def get_registro(self, registro_id: int) -> RegistroComportamiento | None:
        """Retorna un registro de comportamiento por su ID, o None si no existe."""
        ...

    @abstractmethod
    def listar_registros(
        self,
        filtro: FiltroConvivenciaDTO,
        institucion_id: TenantScope,
    ) -> list[RegistroComportamiento]:
        """
        Retorna una lista paginada de registros que cumplen con los criterios
        del filtro (estudiante, grupo, periodo, tipo, etc.).

        `institucion_id` es obligatorio (TenantScope):
          - int  → acota a esa institución vía JOIN a grupos
          - "*"  → cross-tenant (admin)
        """
        ...

    @abstractmethod
    def contar_registros(
        self,
        filtro: FiltroConvivenciaDTO,
        institucion_id: TenantScope,
    ) -> int:
        """
        Retorna la cantidad total de registros que cumplen con el filtro,
        útil para paginación o métricas.

        `institucion_id` es obligatorio (TenantScope):
          - int  → acota a esa institución
          - "*"  → cross-tenant (admin)
        """
        ...

    @abstractmethod
    def guardar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento:
        """
        Guarda un nuevo registro de comportamiento.
        Retorna la entidad con su id asignado.
        """
        ...

    @abstractmethod
    def actualizar_registro(self, registro: RegistroComportamiento) -> RegistroComportamiento:
        """
        Actualiza un registro existente (ej. se agregó seguimiento o se
        notificó al acudiente). Requiere que registro.id no sea None.
        """
        ...

    @abstractmethod
    def eliminar_registro(self, registro_id: int) -> bool:
        """
        Elimina un registro de comportamiento (físico o lógico).
        Generalmente usado si un docente comete un error al crearlo.
        Retorna True si la fila fue afectada.
        """
        ...

    # =========================================================================
    # Notas de Comportamiento
    # =========================================================================

    @abstractmethod
    def get_nota(self, estudiante_id: int, periodo_id: int) -> NotaComportamiento | None:
        """
        Retorna la nota de comportamiento de un estudiante en un periodo,
        o None si no ha sido evaluado.
        """
        ...

    @abstractmethod
    def listar_notas_por_estudiante(self, estudiante_id: int) -> list[NotaComportamiento]:
        """
        Retorna todas las notas de comportamiento de un estudiante en los
        diferentes periodos del año activo.
        """
        ...

    @abstractmethod
    def listar_notas_por_grupo(self, grupo_id: int, periodo_id: int) -> list[NotaComportamiento]:
        """
        Retorna las notas de comportamiento de todos los estudiantes de un grupo
        en un periodo específico.
        """
        ...

    @abstractmethod
    def guardar_nota(self, nota: NotaComportamiento) -> NotaComportamiento:
        """
        Guarda o actualiza la nota de comportamiento (Upsert).
        Si ya existe una nota para ese estudiante y periodo, la reemplaza.
        Retorna la entidad guardada con su id.
        """
        ...

    # =========================================================================
    # Categorías de Observación (convivencia_09)
    # =========================================================================

    @abstractmethod
    def listar_categorias(
        self, institucion_id: TenantScope, solo_activas: bool = True
    ) -> list[CategoriaObservacion]:
        """
        Retorna la lista de categorías de observación.
        Si solo_activas=True (default), excluye las categorías desactivadas.

        `institucion_id` es obligatorio (TenantScope):
          - int  → filtra por esa institución
          - "*"  → cross-tenant (admin)
        """
        ...

    @abstractmethod
    def get_categoria(self, categoria_id: int) -> CategoriaObservacion | None:
        """Retorna una categoría por su ID, o None si no existe."""
        ...

    @abstractmethod
    def guardar_categoria(self, categoria: CategoriaObservacion) -> CategoriaObservacion:
        """
        Guarda una nueva categoría de observación.
        Retorna la entidad con su id asignado.
        """
        ...

    @abstractmethod
    def actualizar_categoria(self, categoria: CategoriaObservacion) -> CategoriaObservacion:
        """
        Actualiza nombre, es_comportamental y/o activa de una categoría existente.
        Requiere que categoria.id no sea None.
        """
        ...

    # =========================================================================
    # Catálogo de plantillas de observación (convivencia_12)
    # =========================================================================

    @abstractmethod
    def listar_plantillas(
        self,
        institucion_id: TenantScope,
        categoria_id: int | None = None,
        solo_activas: bool = True,
    ) -> list[PlantillaObservacion]:
        """
        Retorna la lista de plantillas de observación.
        Si categoria_id no es None, filtra por esa categoría.
        Si solo_activas=True (default), excluye las plantillas desactivadas.
        Ordena por uso_count DESC (las más usadas primero).

        `institucion_id` es obligatorio (TenantScope):
          - int  → filtra por esa institución
          - "*"  → cross-tenant (admin)
        """
        ...

    @abstractmethod
    def get_plantilla(self, plantilla_id: int) -> PlantillaObservacion | None:
        """Retorna una plantilla por su ID, o None si no existe."""
        ...

    @abstractmethod
    def guardar_plantilla(self, plantilla: PlantillaObservacion) -> PlantillaObservacion:
        """
        Guarda una nueva plantilla de observación.
        Retorna la entidad con su id asignado.
        """
        ...

    @abstractmethod
    def actualizar_plantilla(self, plantilla: PlantillaObservacion) -> PlantillaObservacion:
        """
        Actualiza texto, categoria_id y/o activa de una plantilla existente.
        Requiere que plantilla.id no sea None.
        """
        ...

    @abstractmethod
    def incrementar_uso_plantilla(self, plantilla_id: int) -> None:
        """
        Incrementa en 1 el uso_count de la plantilla indicada.
        Operación atómica (UPDATE SET uso_count = uso_count + 1).
        """
        ...

    # =========================================================================
    # Catálogo de tipos de situación — Ley 1620 (convivencia_34)
    # =========================================================================

    @abstractmethod
    def listar_tipos_situacion(
        self, institucion_id: TenantScope, solo_activas: bool = True
    ) -> list[TipoSituacion]:
        """
        Retorna tipos de situación, opcionalmente filtrados por institución y estado.

        `institucion_id` es obligatorio (TenantScope):
          - int  → filtra por esa institución
          - "*"  → cross-tenant (admin)
        """
        ...

    @abstractmethod
    def get_tipo_situacion(self, tipo_situacion_id: int) -> TipoSituacion | None:
        """Retorna un tipo de situación por ID, o None si no existe."""
        ...

    @abstractmethod
    def guardar_tipo_situacion(self, tipo_situacion: TipoSituacion) -> TipoSituacion:
        """Guarda un nuevo tipo de situación. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_tipo_situacion(self, tipo_situacion: TipoSituacion) -> TipoSituacion:
        """Actualiza nombre/nivel/descripción/protocolo/activa de un tipo existente."""
        ...

    # =========================================================================
    # Entradas de seguimiento (convivencia_35)
    # =========================================================================

    @abstractmethod
    def listar_entradas_seguimiento(self, registro_id: int) -> list[EntradaSeguimiento]:
        """Retorna todas las entradas de seguimiento de un registro, ordenadas por fecha ASC."""
        ...

    def listar_entradas_seguimiento_batch(
        self, registro_ids: list[int],
    ) -> dict[int, list[EntradaSeguimiento]]:
        """Retorna entradas de seguimiento para múltiples registros en una sola consulta."""
        result: dict[int, list[EntradaSeguimiento]] = {}
        for rid in registro_ids:
            entries = self.listar_entradas_seguimiento(rid)
            if entries:
                result[rid] = entries
        return result

    @abstractmethod
    def guardar_entrada_seguimiento(self, entrada: EntradaSeguimiento) -> EntradaSeguimiento:
        """Guarda una nueva entrada de seguimiento. Retorna la entidad con id asignado."""
        ...

    # =========================================================================
    # Catálogo de medidas pedagógicas (convivencia_36)
    # =========================================================================

    @abstractmethod
    def listar_medidas(
        self, institucion_id: TenantScope, solo_activas: bool = True
    ) -> list[MedidaPedagogica]:
        """
        Retorna medidas pedagógicas, opcionalmente filtradas por institución y estado.

        `institucion_id` es obligatorio (TenantScope):
          - int  → filtra por esa institución
          - "*"  → cross-tenant (admin)
        """
        ...

    @abstractmethod
    def get_medida(self, medida_id: int) -> MedidaPedagogica | None:
        """Retorna una medida pedagógica por ID, o None si no existe."""
        ...

    @abstractmethod
    def guardar_medida(self, medida: MedidaPedagogica) -> MedidaPedagogica:
        """Guarda una nueva medida pedagógica. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_medida(self, medida: MedidaPedagogica) -> MedidaPedagogica:
        """Actualiza nombre/descripcion/nivel_minimo/activa de una medida existente."""
        ...

    # =========================================================================
    # Lookup auxiliar
    # =========================================================================

    @abstractmethod
    def resolver_nombres_usuario(self, usuario_ids: list[int]) -> dict[int, str]:
        """Devuelve {usuario_id: nombre_completo} para los IDs dados."""
        ...

    @abstractmethod
    def resolver_nombres_asignatura(self, asignacion_ids: list[int]) -> dict[int, str]:
        """Devuelve {asignacion_id: nombre_asignatura} via JOIN asignaciones→asignaturas."""
        ...

    @abstractmethod
    def resolver_grupo_grado(self, grupo_id: int) -> dict:
        """Devuelve {grupo_codigo, grupo_nombre, grado_nombre} para un grupo_id."""
        ...

    @abstractmethod
    def resolver_acudiente_principal(self, estudiante_id: int) -> dict:
        """Devuelve datos del acudiente principal del estudiante, o dict vacío."""
        ...
