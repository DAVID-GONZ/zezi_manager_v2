"""
Modelo de dominio: Convivencia
================================

Contiene:
  Enums    — TipoRegistro
  Entidades — ObservacionPeriodo, RegistroComportamiento, NotaComportamiento
  DTOs     — NuevaObservacionDTO, NuevoRegistroComportamientoDTO,
              NuevaNotaComportamientoDTO, FiltroConvivenciaDTO

Conceptos:
  ObservacionPeriodo
      Texto narrativo que el docente escribe sobre un estudiante al cierre
      del periodo. Aparece en el boletín si es_publica=True.

  RegistroComportamiento
      Evento puntual de convivencia: fortaleza, dificultad, compromiso,
      citación al acudiente, o descargo del estudiante.
      Puede requerir firma del acudiente.

  NotaComportamiento
      Calificación cuantitativa de convivencia por periodo (si la institución
      la usa). Opcional — no todas las instituciones califican convivencia.

Reglas de negocio:
  - texto (ObservacionPeriodo) no puede estar vacío, máximo 2000 chars.
  - descripcion (RegistroComportamiento) no puede estar vacía, máximo 1000 chars.
  - fecha (RegistroComportamiento) no puede ser futura.
  - acudiente_notificado=True implica que hubo contacto; puede ser True
    incluso si requiere_firma=False (se notificó sin requerir firma).
  - valor (NotaComportamiento) debe estar en [0, 100].
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.models.alerta import NivelAlerta

# =============================================================================
# Enumeraciones
# =============================================================================


class TipoRegistro(StrEnum):
    FORTALEZA = "fortaleza"
    DIFICULTAD = "dificultad"
    COMPROMISO = "compromiso"
    CITACION_ACUDIENTE = "citacion_acudiente"
    DESCARGO = "descargo"


# Mapa de valores de TipoRegistro a etiquetas legibles para el boletín (convivencia_29).
# Fuente única de verdad: evita repetir el dict en observaciones.py y en el servicio.
TIPO_REGISTRO_DISPLAY: dict[str, str] = {
    "fortaleza": "Fortaleza",
    "dificultad": "Dificultad",
    "compromiso": "Compromiso",
    "citacion_acudiente": "Citación acudiente",
    "descargo": "Descargo",
}


# =============================================================================
# Catálogo de categorías de observación (convivencia_09)
# =============================================================================


class CategoriaObservacion(BaseModel):
    """
    Categoría para clasificar observaciones y registros de convivencia.

    es_comportamental=True agrupa categorías relacionadas con el comportamiento
    del estudiante (p.ej. "Comportamiento positivo", "Convivencia y normas").
    es_comportamental=False agrupa categorías de índole académica o de
    seguimiento (p.ej. "Académico", "Responsabilidad").

    activa=False oculta la categoría del selector sin eliminar los registros
    históricos que ya la referencien.
    """

    id: int | None = None
    nombre: str
    es_comportamental: bool = False
    activa: bool = True
    institucion_id: int | None = None


class NuevaCategoriaDTO(BaseModel):
    """DTO para crear una nueva categoría de observación."""

    nombre: str
    es_comportamental: bool = False


# =============================================================================
# Catálogo de plantillas de observación (convivencia_12)
# =============================================================================


class PlantillaObservacion(BaseModel):
    """
    Plantilla de texto reutilizable para agilizar el registro de observaciones.

    `categoria_id` vincula la plantilla a una categoría de observación;
    None significa que la plantilla aplica a cualquier categoría.
    `uso_count` se incrementa cada vez que se usa la plantilla.
    `activa=False` oculta la plantilla del selector sin eliminar el historial.
    """

    id: int | None = None
    texto: str
    categoria_id: int | None = None
    uso_count: int = 0
    activa: bool = True
    institucion_id: int | None = None


class NuevaPlantillaDTO(BaseModel):
    """DTO para crear una nueva plantilla de observación."""

    texto: str
    categoria_id: int | None = None


# =============================================================================
# Entidades
# =============================================================================


class ObservacionPeriodo(BaseModel):
    """
    Observación narrativa de un docente sobre un estudiante en un periodo.

    `es_publica=True` indica que el texto aparecerá en el boletín.
    `es_publica=False` es para notas internas del docente.
    """

    id: int | None = None
    estudiante_id: int
    asignacion_id: int
    periodo_id: int
    texto: str
    es_publica: bool = True
    fecha_registro: datetime = Field(default_factory=datetime.now)
    usuario_id: int | None = None
    # Campos añadidos en convivencia_11: clasificación por categoría y origen.
    # categoria_id=None → observación libre (sin categoría asignada).
    # origen='libre' → texto ingresado directamente; 'plantilla' → generado
    # desde una plantilla del catálogo (convivencia_12).
    categoria_id: int | None = None
    origen: str = "libre"
    # Añadido en convivencia_14: vínculo al RegistroComportamiento creado al
    # promover la observación. None = no promovida aún.
    registro_comportamiento_id: int | None = None

    @field_validator("texto", mode="before")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        """Normaliza el texto de la observación; exige no vacío y ≤2000 caracteres."""
        v = str(v).strip()
        if not v:
            raise ValueError("La observación no puede estar vacía.")
        if len(v) > 2000:
            raise ValueError(f"La observación no puede exceder 2000 caracteres (tiene {len(v)}).")
        return v

    def hacer_publica(self) -> ObservacionPeriodo:
        """Retorna una copia marcada como pública (aparece en boletín)."""
        return self.model_copy(update={"es_publica": True})

    def hacer_privada(self) -> ObservacionPeriodo:
        """Retorna una copia marcada como privada (solo visible al docente)."""
        return self.model_copy(update={"es_publica": False})


class RegistroComportamiento(BaseModel):
    """
    Evento puntual de convivencia registrado por un docente o directivo.

    La secuencia típica de un registro negativo:
      1. Se crea con tipo=DIFICULTAD, requiere_firma=True.
      2. Se llama a `registrar_notificacion()` cuando el acudiente es contactado.
      3. Se llama a `agregar_seguimiento(texto)` cuando hay acciones posteriores.

    DESCARGO es la respuesta formal del estudiante ante una falta grave.
    COMPROMISO es un acuerdo entre el estudiante/acudiente y la institución.
    """

    id: int | None = None
    estudiante_id: int
    grupo_id: int
    periodo_id: int
    fecha: date = Field(default_factory=date.today)
    tipo: TipoRegistro
    descripcion: str
    seguimiento: str | None = None
    requiere_firma: bool = False
    acudiente_notificado: bool = False
    usuario_registro_id: int | None = None

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        """Normaliza la descripción del registro; exige no vacío y ≤1000 caracteres."""
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción del registro no puede estar vacía.")
        if len(v) > 1000:
            raise ValueError(f"La descripción no puede exceder 1000 caracteres (tiene {len(v)}).")
        return v

    @field_validator("seguimiento", mode="before")
    @classmethod
    def limpiar_seguimiento(cls, v: str | None) -> str | None:
        """Normaliza el seguimiento opcional (strip); cadena vacía → None."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("fecha", mode="before")
    @classmethod
    def validar_fecha(cls, v: date | str) -> date:
        """Acepta date o string ISO; la fecha del registro no puede ser futura."""
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(f"La fecha del registro ({v}) no puede ser futura.")
        return v

    @model_validator(mode="after")
    def validar_notificacion(self) -> Self:
        """
        No tiene sentido marcar acudiente_notificado=True en un registro
        de FORTALEZA que no requiere firma. Pero sí puede notificarse
        en cualquier caso — el sistema no lo restringe; solo verifica
        que no haya inconsistencia con descargos.
        Un DESCARGO no requiere firma (es el estudiante quien habla).
        """
        if self.tipo == TipoRegistro.DESCARGO and self.requiere_firma:
            raise ValueError(
                "Un registro de tipo DESCARGO es emitido por el estudiante "
                "y no requiere firma del acudiente."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades computadas
    # ------------------------------------------------------------------

    @property
    def es_negativo(self) -> bool:
        """True para registros que implican una situación problemática."""
        return self.tipo in (
            TipoRegistro.DIFICULTAD,
            TipoRegistro.CITACION_ACUDIENTE,
        )

    @property
    def es_positivo(self) -> bool:
        """True para registros que reconocen comportamiento positivo."""
        return self.tipo == TipoRegistro.FORTALEZA

    @property
    def pendiente_notificacion(self) -> bool:
        """True si requiere firma pero el acudiente aún no ha sido notificado."""
        return self.requiere_firma and not self.acudiente_notificado

    @property
    def tiene_seguimiento(self) -> bool:
        """True si el registro tiene texto de seguimiento asociado."""
        return bool(self.seguimiento)

    # ------------------------------------------------------------------
    # Métodos de dominio
    # ------------------------------------------------------------------

    def registrar_notificacion(self) -> RegistroComportamiento:
        """
        Retorna una copia marcando que el acudiente fue notificado.

        Raises:
            ValueError: Si el registro no requería firma/notificación.
        """
        if not self.requiere_firma:
            raise ValueError("Este registro no requiere notificación al acudiente.")
        if self.acudiente_notificado:
            raise ValueError("El acudiente ya fue notificado para este registro.")
        return self.model_copy(update={"acudiente_notificado": True})

    def agregar_seguimiento(self, texto: str) -> RegistroComportamiento:
        """
        Retorna una copia con el texto de seguimiento añadido o reemplazado.

        Args:
            texto: Descripción de las acciones tomadas después del registro.
        """
        texto = texto.strip()
        if not texto:
            raise ValueError("El texto de seguimiento no puede estar vacío.")
        return self.model_copy(update={"seguimiento": texto})


class NotaComportamiento(BaseModel):
    """
    Calificación cuantitativa de convivencia por periodo.

    No todas las instituciones la usan. Cuando existe, es independiente
    de las notas académicas y puede tener su propio nivel de desempeño.
    """

    id: int | None = None
    estudiante_id: int
    grupo_id: int
    periodo_id: int
    valor: float
    desempeno_id: int | None = None
    # `observacion` es el CONCEPTO NARRATIVO que baja al boletín (Fase 3).
    # Semánticamente equivale al "concepto de comportamiento" que redacta el
    # director de grupo. El nombre del campo se conserva por compat con el
    # repositorio; la vista/DTO consolidado (ConceptoComportamientoDTO) expone
    # este texto como `concepto`.
    observacion: str | None = None
    usuario_id: int | None = None

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        """La nota de comportamiento debe estar en 0-100 (redondeada a 2)."""
        if not (0 <= v <= 100):
            raise ValueError(f"La nota de comportamiento debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        """Normaliza la observación opcional (strip); cadena vacía → None."""
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @property
    def aprobado(self, nota_minima: float = 60.0) -> bool:
        """
        Indica si la nota de comportamiento es aprobatoria.
        La nota mínima se pasa como parámetro porque es configurable
        por institución (configuracion_anio.nota_minima_aprobacion).
        """
        return self.valor >= nota_minima


# =============================================================================
# DTOs
# =============================================================================


class NuevaObservacionDTO(BaseModel):
    """Datos para registrar una observación de periodo."""

    estudiante_id: int
    asignacion_id: int
    periodo_id: int
    texto: str
    # categoria_id es obligatorio al crear (convivencia_11). Colocado antes
    # de campos con default para que Pydantic no falle en la validación.
    categoria_id: int
    es_publica: bool = True

    @field_validator("texto", mode="before")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        """Normaliza el texto y exige que no esté vacío."""
        v = str(v).strip()
        if not v:
            raise ValueError("El texto no puede estar vacío.")
        return v

    def to_observacion(self, usuario_id: int | None = None) -> ObservacionPeriodo:
        """Construye una ObservacionPeriodo del DTO, fijando el usuario autor."""
        return ObservacionPeriodo(
            **self.model_dump(),
            usuario_id=usuario_id,
        )


class NuevoRegistroComportamientoDTO(BaseModel):
    """Datos para crear un registro de comportamiento."""

    estudiante_id: int
    grupo_id: int
    periodo_id: int
    tipo: TipoRegistro
    descripcion: str
    requiere_firma: bool = False
    fecha: date = Field(default_factory=date.today)

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        """Normaliza la descripción y exige que no esté vacía."""
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción no puede estar vacía.")
        return v

    def to_registro(self, usuario_id: int | None = None) -> RegistroComportamiento:
        """Construye un RegistroComportamiento del DTO, fijando el usuario que lo registra."""
        return RegistroComportamiento(
            **self.model_dump(),
            usuario_registro_id=usuario_id,
        )


class NuevaNotaComportamientoDTO(BaseModel):
    """Datos para registrar la nota de comportamiento de un periodo."""

    estudiante_id: int
    grupo_id: int
    periodo_id: int
    valor: float
    observacion: str | None = None

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        """El valor de la nota de comportamiento debe estar en 0-100 (redondeado a 2)."""
        if not (0 <= v <= 100):
            raise ValueError(f"El valor debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    def to_nota(self, usuario_id: int | None = None) -> NotaComportamiento:
        """Construye una NotaComportamiento del DTO, fijando el usuario autor."""
        return NotaComportamiento(
            **self.model_dump(),
            usuario_id=usuario_id,
        )


class ConceptoComportamientoDTO(BaseModel):
    """
    Consolidado cuantitativo + cualitativo del comportamiento de un
    estudiante en un periodo, listo para el boletín (Fase 3) y para el
    reporte del director de grupo (convivencia_06).

    Combina la nota (`valor`), el nivel de desempeño resuelto (por
    `desempeno_id` explícito o por rango sobre `niveles_desempeno` del año)
    y el concepto narrativo (`concepto`, espejo de `NotaComportamiento.observacion`).

    Cuando el estudiante no tiene nota registrada para el periodo, se emite
    el DTO con `valor=None`, `aprobado=False` y el resto de campos en None.
    """

    estudiante_id: int
    periodo_id: int
    grupo_id: int
    valor: float | None = None
    nivel_nombre: str | None = None
    nivel_descripcion: str | None = None
    concepto: str | None = None
    aprobado: bool = False


class ReporteConvivenciaFilaDTO(BaseModel):
    """
    Fila del reporte de convivencia por grupo/periodo (convivencia_06):
    consolida la nota + concepto del estudiante con la lista de observaciones
    del periodo. Diseñado para presentación (tabla del director de grupo) y
    exportación (PDF / Excel) sin exponer entidades del dominio a la vista.
    """

    estudiante_id: int
    nombre: str
    valor: float | None = None
    nivel_nombre: str | None = None
    concepto: str | None = None
    observaciones: list[str] = Field(default_factory=list)


class FiltroConvivenciaDTO(BaseModel):
    """Parámetros para consultar registros de comportamiento."""

    estudiante_id: int | None = None
    grupo_id: int | None = None
    periodo_id: int | None = None
    tipo: TipoRegistro | None = None
    solo_negativos: bool = False
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=50, ge=1, le=200)


class NuevaAlertaSeguimientoDTO(BaseModel):
    """DTO para crear una alerta de seguimiento manual (convivencia_16)."""

    estudiante_id: int
    usuario_destino_id: int  # profesor destinatario
    descripcion: str
    nivel: NivelAlerta = NivelAlerta.ADVERTENCIA


class Seguimiento360DTO(BaseModel):
    """
    Vista consolidada 360° de un estudiante en un periodo (convivencia_18).

    Agrega nota de comportamiento, concepto narrativo, nivel de desempeño,
    observaciones públicas del periodo y alertas activas de seguimiento.
    `promedio_notas` es el promedio académico general; None si no está disponible.
    """

    estudiante_id: int
    estudiante_nombre: str
    periodo_id: int
    nota_comportamiento: float | None = None
    concepto: str | None = None
    nivel_comportamiento: str | None = None
    observaciones: list[str] = []
    alertas_activas: list[str] = []
    promedio_notas: float | None = None


class PuntoSerieDTO(BaseModel):
    """
    Un punto de una serie temporal por periodo (convivencia_21).

    Usado para graficar la evolución de la nota de comportamiento a lo largo
    de los periodos del año. `valor=None` marca un periodo sin nota registrada
    (hueco en la serie), preservando el eje de periodos completo.
    """

    periodo_id: int
    periodo_nombre: str
    valor: float | None = None


class ResumenConvivenciaDTO(BaseModel):
    """
    Resumen agregado de convivencia por estudiante en un grupo/periodo
    (convivencia_21). Alimenta el maestro-detalle del hub de Seguimiento
    sin incurrir en el patrón N+1: se compone con un número acotado de
    consultas por grupo.

    `supera_umbral=True` indica que el número de registros negativos alcanza
    o supera el umbral de alerta configurado (SEGUIMIENTO_REQUERIDO). Si no
    hay configuración de alertas disponible, permanece False.
    """

    estudiante_id: int
    nombre: str
    num_observaciones: int = 0
    num_registros_negativos: int = 0
    nota: float | None = None
    nivel_nombre: str | None = None
    supera_umbral: bool = False


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TIPO_REGISTRO_DISPLAY",
    "CategoriaObservacion",
    "ConceptoComportamientoDTO",
    "FiltroConvivenciaDTO",
    "NotaComportamiento",
    "NuevaAlertaSeguimientoDTO",
    "NuevaCategoriaDTO",
    "NuevaNotaComportamientoDTO",
    "NuevaObservacionDTO",
    "NuevaPlantillaDTO",
    "NuevoRegistroComportamientoDTO",
    "ObservacionPeriodo",
    "PlantillaObservacion",
    "PuntoSerieDTO",
    "RegistroComportamiento",
    "ReporteConvivenciaFilaDTO",
    "ResumenConvivenciaDTO",
    "Seguimiento360DTO",
    "TipoRegistro",
]
