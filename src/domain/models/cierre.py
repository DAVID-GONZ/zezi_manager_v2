"""
Modelo de dominio: Cierres y Promoción
========================================

Contiene:
  Enums    — EstadoPromocion
  Entidades — CierrePeriodo, CierreAnio, PromocionAnual
  DTOs     — CrearCierrePeriodoDTO, CrearCierreAnioDTO, DecidirPromocionDTO

Dos categorías de entidades con comportamiento distinto:

  Registros inmutables (libro mayor):
    CierrePeriodo  — nota definitiva de una asignatura en un periodo.
    CierreAnio     — nota definitiva anual de una asignatura.
    Se crean y no se modifican. Si hay una corrección, el repositorio
    reemplaza el registro (ON CONFLICT REPLACE en la BD).

  Entidad con estado mutable:
    PromocionAnual — decisión de promoción del estudiante al año siguiente.
    Máquina de estados: PENDIENTE → PROMOVIDO | REPROBADO | CONDICIONAL.
    Una vez decidida, la promoción es inmutable.

Responsabilidades del servicio (no del modelo):
  - Determinar si nota_definitiva >= nota_minima_aprobacion.
  - Calcular nota_promedio_periodos como promedio ponderado.
  - Verificar que todos los periodos están cerrados antes de crear CierreAnio.
  - Contabilizar asignaturas_perdidas para PromocionAnual.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class EstadoPromocion(str, Enum):
    PENDIENTE   = "pendiente"
    PROMOVIDO   = "promovido"
    REPROBADO   = "reprobado"
    CONDICIONAL = "condicional"   # promovido con materias pendientes


# =============================================================================
# CierrePeriodo — registro inmutable
# =============================================================================

class CierrePeriodo(BaseModel):
    """
    Nota definitiva de un estudiante en una asignatura al cierre de un periodo.

    Es un registro de libro mayor: una vez creado, representa la calificación
    oficial. Si se requiere corrección, el repositorio lo reemplaza usando
    ON CONFLICT REPLACE — el modelo no tiene un método de corrección.

    nota_definitiva: calculada por el servicio a partir de las categorías
                     y actividades. El modelo solo valida el rango.
    desempeno_id:    FK al nivel de desempeño correspondiente (Bajo, Básico…).
                     Lo resuelve el servicio comparando la nota con los rangos
                     configurados en niveles_desempeno.
    """
    id:               int | None  = None
    estudiante_id:    int
    asignacion_id:    int
    periodo_id:       int
    nota_definitiva:  float
    desempeno_id:     int | None  = None
    logro_id:         int | None  = None
    fecha_cierre:     date        = Field(default_factory=date.today)
    usuario_cierre_id: int | None = None

    @field_validator("estudiante_id", "asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("nota_definitiva")
    @classmethod
    def validar_nota(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(
                f"La nota definitiva debe estar entre 0 y 100 (recibido: {v})."
            )
        return round(v, 2)

    @field_validator("fecha_cierre", mode="before")
    @classmethod
    def validar_fecha(cls, v: date | str) -> date:
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(
                f"La fecha de cierre ({v}) no puede ser futura."
            )
        return v

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    def aprobo(self, nota_minima: float) -> bool:
        """
        Indica si la nota definitiva es aprobatoria.

        Args:
            nota_minima: Umbral configurable por institución
                         (configuracion_anio.nota_minima_aprobacion).
        """
        return self.nota_definitiva >= nota_minima

    @property
    def nota_display(self) -> str:
        """Nota formateada con un decimal: '75.5'."""
        return f"{self.nota_definitiva:.1f}"


# =============================================================================
# CierreAnio — registro inmutable
# =============================================================================

class CierreAnio(BaseModel):
    """
    Nota definitiva anual de un estudiante en una asignatura.

    Representa el resultado final después de ponderar los cuatro periodos
    y, si aplica, la nota de habilitación.

    nota_promedio_periodos: promedio ponderado de los cierres_periodo.
    nota_habilitacion:      nota obtenida en la habilitación anual, si existe.
    nota_definitiva_anual:  la nota que determina si aprobó:
                              - Si hay habilitación: nota_habilitacion
                              - Si no: nota_promedio_periodos
                            El servicio la calcula; el modelo la valida.
    perdio:                 True si nota_definitiva_anual < nota_minima.
                            El servicio lo determina; el modelo lo almacena.
    """
    id:                     int | None  = None
    estudiante_id:          int
    asignacion_id:          int
    anio_id:                int
    nota_promedio_periodos: float
    nota_habilitacion:      float | None = None
    nota_definitiva_anual:  float
    perdio:                 bool
    desempeno_id:           int | None  = None
    fecha_cierre:           date        = Field(default_factory=date.today)
    usuario_cierre_id:      int | None  = None

    @field_validator("estudiante_id", "asignacion_id", "anio_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator(
        "nota_promedio_periodos",
        "nota_habilitacion",
        "nota_definitiva_anual",
    )
    @classmethod
    def validar_nota(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if not (0 <= v <= 100):
            raise ValueError(
                f"La nota debe estar entre 0 y 100 (recibido: {v})."
            )
        return round(v, 2)

    @field_validator("fecha_cierre", mode="before")
    @classmethod
    def validar_fecha(cls, v: date | str) -> date:
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(f"La fecha de cierre ({v}) no puede ser futura.")
        return v

    @model_validator(mode="after")
    def validar_coherencia_notas(self) -> Self:
        """
        Si hay habilitación, nota_definitiva_anual debe ser nota_habilitacion.
        Si no hay habilitación, debe ser nota_promedio_periodos.
        Margen de 0.01 para errores de redondeo.
        """
        if self.nota_habilitacion is not None:
            if abs(self.nota_definitiva_anual - self.nota_habilitacion) > 0.01:
                raise ValueError(
                    f"Con habilitación, nota_definitiva_anual "
                    f"({self.nota_definitiva_anual}) debe ser igual a "
                    f"nota_habilitacion ({self.nota_habilitacion})."
                )
        else:
            if abs(self.nota_definitiva_anual - self.nota_promedio_periodos) > 0.01:
                raise ValueError(
                    f"Sin habilitación, nota_definitiva_anual "
                    f"({self.nota_definitiva_anual}) debe ser igual a "
                    f"nota_promedio_periodos ({self.nota_promedio_periodos})."
                )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def tiene_habilitacion(self) -> bool:
        return self.nota_habilitacion is not None

    @property
    def mejoro_con_habilitacion(self) -> bool | None:
        """
        True si la habilitación mejoró la nota del promedio de periodos.
        None si no hubo habilitación.
        """
        if self.nota_habilitacion is None:
            return None
        return self.nota_habilitacion > self.nota_promedio_periodos

    @property
    def nota_display(self) -> str:
        return f"{self.nota_definitiva_anual:.1f}"


# =============================================================================
# PromocionAnual — entidad con máquina de estados
# =============================================================================

class PromocionAnual(BaseModel):
    """
    Decisión de promoción de un estudiante al año siguiente.

    Máquina de estados:
      PENDIENTE → PROMOVIDO | REPROBADO | CONDICIONAL

    CONDICIONAL: el estudiante pasa al año siguiente con materias
    pendientes (permitido según criterios_promocion).

    Una vez decidida (salida del estado PENDIENTE), la promoción
    es inmutable — cambiar una decisión de promoción requiere
    intervención administrativa directa en la BD.
    """
    id:                  int | None         = None
    estudiante_id:       int
    anio_id:             int
    estado:              EstadoPromocion     = EstadoPromocion.PENDIENTE
    asignaturas_perdidas: int               = Field(default=0, ge=0)
    observacion:         str | None         = None
    fecha_decision:      date | None        = None
    usuario_decision_id: int | None         = None

    @field_validator("estudiante_id", "anio_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("fecha_decision", mode="before")
    @classmethod
    def validar_fecha(cls, v: date | str | None) -> date | None:
        if v is None:
            return None
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(
                f"La fecha de decisión ({v}) no puede ser futura."
            )
        return v

    @model_validator(mode="after")
    def validar_coherencia_estado(self) -> Self:
        """
        Una promoción decidida debe tener fecha_decision.
        Una promoción pendiente no debe tener fecha_decision.
        """
        if self.esta_finalizado and self.fecha_decision is None:
            raise ValueError(
                f"Una promoción '{self.estado.value}' debe tener fecha_decision."
            )
        if self.esta_pendiente and self.fecha_decision is not None:
            raise ValueError(
                "Una promoción PENDIENTE no puede tener fecha_decision."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def esta_pendiente(self) -> bool:
        return self.estado == EstadoPromocion.PENDIENTE

    @property
    def esta_finalizado(self) -> bool:
        return self.estado != EstadoPromocion.PENDIENTE

    @property
    def fue_promovido(self) -> bool:
        return self.estado in (
            EstadoPromocion.PROMOVIDO,
            EstadoPromocion.CONDICIONAL,
        )

    @property
    def fue_reprobado(self) -> bool:
        return self.estado == EstadoPromocion.REPROBADO

    @property
    def es_condicional(self) -> bool:
        return self.estado == EstadoPromocion.CONDICIONAL

    # ------------------------------------------------------------------
    # Método de transición
    # ------------------------------------------------------------------

    def decidir(
        self,
        estado: EstadoPromocion,
        asignaturas_perdidas: int = 0,
        observacion: str | None = None,
        usuario_id: int | None = None,
        fecha: date | None = None,
    ) -> "PromocionAnual":
        """
        Registra la decisión de promoción. PENDIENTE → otro estado.

        Args:
            estado:               Estado final (no puede ser PENDIENTE).
            asignaturas_perdidas: Número de asignaturas que el estudiante perdió.
            observacion:          Justificación, especialmente para CONDICIONAL.
            usuario_id:           Quien toma la decisión (director/coordinador).
            fecha:                Fecha de la decisión. Default: hoy.

        Raises:
            ValueError: Si la promoción ya fue decidida o el estado es inválido.
        """
        if self.esta_finalizado:
            raise ValueError(
                f"La promoción ya fue decidida como '{self.estado.value}'. "
                "No se puede cambiar."
            )
        if estado == EstadoPromocion.PENDIENTE:
            raise ValueError(
                "No se puede decidir PENDIENTE como resultado final. "
                "Use PROMOVIDO, REPROBADO o CONDICIONAL."
            )
        if asignaturas_perdidas < 0:
            raise ValueError(
                f"asignaturas_perdidas no puede ser negativo "
                f"(recibido: {asignaturas_perdidas})."
            )
        return self.model_copy(update={
            "estado":               estado,
            "asignaturas_perdidas": asignaturas_perdidas,
            "observacion":          observacion.strip() if observacion else None,
            "fecha_decision":       fecha or date.today(),
            "usuario_decision_id":  usuario_id,
        })


# =============================================================================
# DTOs
# =============================================================================

class CrearCierrePeriodoDTO(BaseModel):
    """Datos para registrar el cierre de un periodo."""
    estudiante_id:    int
    asignacion_id:    int
    periodo_id:       int
    nota_definitiva:  float
    desempeno_id:     int | None = None
    logro_id:         int | None = None
    usuario_cierre_id: int | None = None

    @field_validator("nota_definitiva")
    @classmethod
    def validar_nota(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    def to_cierre(self) -> CierrePeriodo:
        return CierrePeriodo(**self.model_dump())


class CrearCierreAnioDTO(BaseModel):
    """Datos para registrar el cierre anual de una asignatura."""
    estudiante_id:          int
    asignacion_id:          int
    anio_id:                int
    nota_promedio_periodos: float
    nota_habilitacion:      float | None = None
    nota_definitiva_anual:  float
    perdio:                 bool
    desempeno_id:           int | None   = None
    usuario_cierre_id:      int | None   = None

    @field_validator(
        "nota_promedio_periodos",
        "nota_habilitacion",
        "nota_definitiva_anual",
    )
    @classmethod
    def validar_nota(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    def to_cierre(self) -> CierreAnio:
        return CierreAnio(**self.model_dump())


class DecidirPromocionDTO(BaseModel):
    """Datos para registrar la decisión de promoción."""
    estado:               EstadoPromocion
    asignaturas_perdidas: int         = Field(default=0, ge=0)
    observacion:          str | None  = None
    usuario_id:           int | None  = None
    fecha:                date | None = None

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: EstadoPromocion) -> EstadoPromocion:
        if v == EstadoPromocion.PENDIENTE:
            raise ValueError(
                "No se puede usar PENDIENTE como estado de decisión."
            )
        return v

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EstadoPromocion",
    "CierrePeriodo",
    "CierreAnio",
    "PromocionAnual",
    "CrearCierrePeriodoDTO",
    "CrearCierreAnioDTO",
    "DecidirPromocionDTO",
]