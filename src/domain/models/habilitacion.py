"""
Modelo de dominio: Habilitación y Plan de Mejoramiento
=======================================================

Contiene:
  Enums    — TipoHabilitacion, EstadoHabilitacion, EstadoPlanMejoramiento
  Entidades — Habilitacion, PlanMejoramiento
  DTOs     — NuevaHabilitacionDTO, RegistrarNotaHabilitacionDTO,
              NuevoPlanMejoramientoDTO, CerrarPlanMejoramientoDTO,
              FiltroHabilitacionesDTO

Marco legal: Decreto 1290 de 2009 — obliga a las instituciones
a ofrecer actividades de recuperación y planes de mejoramiento.

─────────────────────────────────────────────────────────────────
Máquina de estados — Habilitacion
─────────────────────────────────────────────────────────────────

  PENDIENTE ──registrar_nota()──► REALIZADA ──aprobar()──► APROBADA
                                            └──reprobar()─► REPROBADA

  - PENDIENTE:  la actividad está programada pero no se ha presentado.
  - REALIZADA:  el estudiante la presentó; la nota está registrada
                pero la decisión final aún no se ha tomado.
  - APROBADA:   la nota es suficiente para superar la materia/periodo.
  - REPROBADA:  la nota no es suficiente.

  El modelo NO decide si una nota es aprobatoria — esa regla
  depende de nota_minima_aprobacion (configuracion_anio), que
  es responsabilidad del servicio.

─────────────────────────────────────────────────────────────────
Máquina de estados — PlanMejoramiento
─────────────────────────────────────────────────────────────────

  ACTIVO ──cerrar(CUMPLIDO)────► CUMPLIDO
         └──cerrar(INCUMPLIDO)─► INCUMPLIDO

  - Un plan cerrado es inmutable.
  - observacion_cierre es obligatoria al cerrar.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class TipoHabilitacion(str, Enum):
    PERIODO = "periodo"    # recupera un periodo específico
    ANUAL   = "anual"      # recupera la materia al final del año


class EstadoHabilitacion(str, Enum):
    PENDIENTE  = "pendiente"
    REALIZADA  = "realizada"
    APROBADA   = "aprobada"
    REPROBADA  = "reprobada"


class EstadoPlanMejoramiento(str, Enum):
    ACTIVO     = "activo"
    CUMPLIDO   = "cumplido"
    INCUMPLIDO = "incumplido"


# Transiciones permitidas: estado_actual → {estados_siguientes}
_TRANSICIONES_HABILITACION: dict[EstadoHabilitacion, set[EstadoHabilitacion]] = {
    EstadoHabilitacion.PENDIENTE:  {EstadoHabilitacion.REALIZADA},
    EstadoHabilitacion.REALIZADA:  {EstadoHabilitacion.APROBADA,
                                    EstadoHabilitacion.REPROBADA},
    EstadoHabilitacion.APROBADA:   set(),
    EstadoHabilitacion.REPROBADA:  set(),
}


# =============================================================================
# Habilitación
# =============================================================================

class Habilitacion(BaseModel):
    """
    Actividad de recuperación programada para un estudiante.

    tipo=PERIODO: recupera la nota de un periodo específico.
                  periodo_id es obligatorio.
    tipo=ANUAL:   recupera la materia al final del año escolar.
                  periodo_id debe ser None.

    nota_antes:         nota del estudiante antes de la habilitación.
                        Útil para comparar progreso y para informes.
    nota_habilitacion:  nota obtenida en la habilitación.
                        Solo puede existir en estado REALIZADA, APROBADA
                        o REPROBADA — nunca en PENDIENTE.
    """
    id:                  int | None            = None
    estudiante_id:       int
    asignacion_id:       int
    periodo_id:          int | None            = None
    tipo:                TipoHabilitacion
    nota_antes:          float | None          = None
    nota_habilitacion:   float | None          = None
    fecha:               date | None           = None
    estado:              EstadoHabilitacion    = EstadoHabilitacion.PENDIENTE
    observacion:         str | None            = None
    usuario_registro_id: int | None            = None

    # ------------------------------------------------------------------
    # Validadores de campo
    # ------------------------------------------------------------------

    @field_validator("estudiante_id", "asignacion_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser un entero positivo (recibido: {v}).")
        return v

    @field_validator("nota_antes", "nota_habilitacion")
    @classmethod
    def validar_nota(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if not (0 <= v <= 100):
            raise ValueError(
                f"La nota debe estar entre 0 y 100 (recibido: {v})."
            )
        return round(v, 2)

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    # ------------------------------------------------------------------
    # Validador de modelo — reglas cruzadas
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validar_coherencia(self) -> Self:
        # tipo=PERIODO exige periodo_id
        if self.tipo == TipoHabilitacion.PERIODO and self.periodo_id is None:
            raise ValueError(
                "Una habilitación de tipo PERIODO requiere periodo_id."
            )
        # tipo=ANUAL no admite periodo_id
        if self.tipo == TipoHabilitacion.ANUAL and self.periodo_id is not None:
            raise ValueError(
                "Una habilitación de tipo ANUAL no debe tener periodo_id "
                f"(recibido: {self.periodo_id})."
            )
        # nota_habilitacion solo existe si la hab. fue realizada
        estados_sin_nota = {EstadoHabilitacion.PENDIENTE}
        if (
            self.estado in estados_sin_nota
            and self.nota_habilitacion is not None
        ):
            raise ValueError(
                f"No puede haber nota_habilitacion en estado '{self.estado.value}'. "
                "La nota solo se registra después de que la habilitación se realiza."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def esta_pendiente(self) -> bool:
        return self.estado == EstadoHabilitacion.PENDIENTE

    @property
    def fue_realizada(self) -> bool:
        return self.estado != EstadoHabilitacion.PENDIENTE

    @property
    def tiene_resultado_final(self) -> bool:
        return self.estado in (
            EstadoHabilitacion.APROBADA,
            EstadoHabilitacion.REPROBADA,
        )

    @property
    def mejoro_nota(self) -> bool | None:
        """
        True si la nota de habilitación superó la nota anterior.
        None si no hay datos suficientes para comparar.
        """
        if self.nota_antes is None or self.nota_habilitacion is None:
            return None
        return self.nota_habilitacion > self.nota_antes

    # ------------------------------------------------------------------
    # Transiciones de estado
    # ------------------------------------------------------------------

    def _validar_transicion(self, destino: EstadoHabilitacion) -> None:
        permitidos = _TRANSICIONES_HABILITACION[self.estado]
        if destino not in permitidos:
            permitidos_str = (
                ", ".join(e.value for e in permitidos) if permitidos
                else "ninguno (estado terminal)"
            )
            raise ValueError(
                f"Transición inválida: '{self.estado.value}' → '{destino.value}'. "
                f"Desde '{self.estado.value}' solo se puede ir a: {permitidos_str}."
            )

    def registrar_nota(
        self,
        nota: float,
        fecha: date | None = None,
        usuario_id: int | None = None,
        observacion: str | None = None,
    ) -> "Habilitacion":
        """
        Registra la nota obtenida. PENDIENTE → REALIZADA.

        Args:
            nota:        Nota obtenida en la habilitación (0–100).
            fecha:       Fecha en que se realizó. Default: hoy.
            usuario_id:  Docente que registra.
            observacion: Nota adicional sobre el proceso.

        Raises:
            ValueError: Si la transición no está permitida o la nota es inválida.
        """
        self._validar_transicion(EstadoHabilitacion.REALIZADA)
        if not (0 <= nota <= 100):
            raise ValueError(
                f"La nota debe estar entre 0 y 100 (recibido: {nota})."
            )
        return self.model_copy(update={
            "estado":              EstadoHabilitacion.REALIZADA,
            "nota_habilitacion":   round(nota, 2),
            "fecha":               fecha or date.today(),
            "usuario_registro_id": usuario_id or self.usuario_registro_id,
            "observacion":         observacion.strip() if observacion else self.observacion,
        })

    def aprobar(self) -> "Habilitacion":
        """
        Marca la habilitación como aprobada. REALIZADA → APROBADA.
        La decisión de si la nota es aprobatoria es del servicio.
        """
        self._validar_transicion(EstadoHabilitacion.APROBADA)
        return self.model_copy(update={"estado": EstadoHabilitacion.APROBADA})

    def reprobar(self) -> "Habilitacion":
        """Marca la habilitación como reprobada. REALIZADA → REPROBADA."""
        self._validar_transicion(EstadoHabilitacion.REPROBADA)
        return self.model_copy(update={"estado": EstadoHabilitacion.REPROBADA})


# =============================================================================
# Plan de Mejoramiento
# =============================================================================

class PlanMejoramiento(BaseModel):
    """
    Plan de trabajo diseñado para que el estudiante supere sus dificultades
    académicas dentro del mismo periodo o entre periodos.

    Decreto 1290: los planes de mejoramiento son obligatorios cuando un
    estudiante tiene desempeño bajo y deben quedar documentados.

    Estado terminal: CUMPLIDO o INCUMPLIDO — un plan cerrado no se modifica.
    """
    id:                     int | None               = None
    estudiante_id:          int
    asignacion_id:          int
    periodo_id:             int
    descripcion_dificultad: str
    actividades_propuestas: str
    fecha_inicio:           date                     = Field(default_factory=date.today)
    fecha_seguimiento:      date | None              = None
    fecha_cierre:           date | None              = None
    estado:                 EstadoPlanMejoramiento   = EstadoPlanMejoramiento.ACTIVO
    observacion_cierre:     str | None               = None
    usuario_id:             int | None               = None

    # ------------------------------------------------------------------
    # Validadores de campo
    # ------------------------------------------------------------------

    @field_validator("estudiante_id", "asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser un entero positivo (recibido: {v}).")
        return v

    @field_validator("descripcion_dificultad", "actividades_propuestas", mode="before")
    @classmethod
    def validar_texto_requerido(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El campo no puede estar vacío.")
        if len(v) > 2000:
            raise ValueError(
                f"El campo no puede exceder 2000 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("observacion_cierre", mode="before")
    @classmethod
    def limpiar_observacion_cierre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    # ------------------------------------------------------------------
    # Validador de modelo — fechas y estado
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validar_coherencia(self) -> Self:
        # fecha_seguimiento no puede ser anterior al inicio
        if (
            self.fecha_seguimiento
            and self.fecha_seguimiento < self.fecha_inicio
        ):
            raise ValueError(
                f"La fecha de seguimiento ({self.fecha_seguimiento}) no puede "
                f"ser anterior al inicio del plan ({self.fecha_inicio})."
            )
        # fecha_cierre no puede ser anterior al inicio
        if (
            self.fecha_cierre
            and self.fecha_cierre < self.fecha_inicio
        ):
            raise ValueError(
                f"La fecha de cierre ({self.fecha_cierre}) no puede "
                f"ser anterior al inicio del plan ({self.fecha_inicio})."
            )
        # Un plan cerrado debe tener observacion_cierre
        estados_cerrados = {
            EstadoPlanMejoramiento.CUMPLIDO,
            EstadoPlanMejoramiento.INCUMPLIDO,
        }
        if self.estado in estados_cerrados and not self.observacion_cierre:
            raise ValueError(
                f"Un plan en estado '{self.estado.value}' debe tener "
                "observacion_cierre."
            )
        # Un plan activo no debe tener fecha_cierre
        if (
            self.estado == EstadoPlanMejoramiento.ACTIVO
            and self.fecha_cierre is not None
        ):
            raise ValueError(
                "Un plan ACTIVO no puede tener fecha_cierre."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def esta_activo(self) -> bool:
        return self.estado == EstadoPlanMejoramiento.ACTIVO

    @property
    def esta_cerrado(self) -> bool:
        return not self.esta_activo

    @property
    def tiene_seguimiento_programado(self) -> bool:
        return self.fecha_seguimiento is not None

    @property
    def seguimiento_vencido(self) -> bool:
        """True si la fecha de seguimiento ya pasó y el plan aún está activo."""
        if self.fecha_seguimiento is None or self.esta_cerrado:
            return False
        return self.fecha_seguimiento < date.today()

    @property
    def dias_activo(self) -> int:
        """Días transcurridos desde el inicio del plan."""
        referencia = self.fecha_cierre if self.fecha_cierre else date.today()
        return (referencia - self.fecha_inicio).days

    # ------------------------------------------------------------------
    # Métodos de dominio
    # ------------------------------------------------------------------

    def programar_seguimiento(self, fecha: date) -> "PlanMejoramiento":
        """Retorna una copia con la fecha de seguimiento establecida."""
        if self.esta_cerrado:
            raise ValueError("No se puede modificar un plan cerrado.")
        if fecha < self.fecha_inicio:
            raise ValueError(
                f"La fecha de seguimiento ({fecha}) no puede ser anterior "
                f"al inicio del plan ({self.fecha_inicio})."
            )
        return self.model_copy(update={"fecha_seguimiento": fecha})

    def cerrar(
        self,
        estado: EstadoPlanMejoramiento,
        observacion: str,
        fecha: date | None = None,
    ) -> "PlanMejoramiento":
        """
        Cierra el plan con el estado y observación indicados.

        Args:
            estado:      CUMPLIDO o INCUMPLIDO.
            observacion: Descripción del resultado final (obligatoria).
            fecha:       Fecha de cierre. Default: hoy.

        Raises:
            ValueError: Si el plan ya está cerrado, el estado es inválido,
                        o la observación está vacía.
        """
        if self.esta_cerrado:
            raise ValueError(
                f"El plan ya fue cerrado con estado '{self.estado.value}'."
            )
        if estado == EstadoPlanMejoramiento.ACTIVO:
            raise ValueError(
                "No se puede cerrar un plan con estado ACTIVO. "
                "Use CUMPLIDO o INCUMPLIDO."
            )
        observacion = observacion.strip()
        if not observacion:
            raise ValueError(
                "La observación de cierre es obligatoria para cerrar el plan."
            )
        fecha_cierre = fecha or date.today()
        if fecha_cierre < self.fecha_inicio:
            raise ValueError(
                f"La fecha de cierre ({fecha_cierre}) no puede ser anterior "
                f"al inicio del plan ({self.fecha_inicio})."
            )
        return self.model_copy(update={
            "estado":             estado,
            "observacion_cierre": observacion,
            "fecha_cierre":       fecha_cierre,
        })


# =============================================================================
# DTOs
# =============================================================================

class NuevaHabilitacionDTO(BaseModel):
    """Datos para programar una habilitación."""
    estudiante_id: int
    asignacion_id: int
    tipo:          TipoHabilitacion
    periodo_id:    int | None = None
    nota_antes:    float | None = None
    fecha:         date | None = None

    @field_validator("nota_antes")
    @classmethod
    def validar_nota(cls, v: float | None) -> float | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return v

    @model_validator(mode="after")
    def validar_tipo_periodo(self) -> Self:
        if self.tipo == TipoHabilitacion.PERIODO and self.periodo_id is None:
            raise ValueError(
                "Una habilitación de tipo PERIODO requiere periodo_id."
            )
        if self.tipo == TipoHabilitacion.ANUAL and self.periodo_id is not None:
            raise ValueError(
                "Una habilitación de tipo ANUAL no debe tener periodo_id."
            )
        return self

    def to_habilitacion(self, usuario_id: int | None = None) -> Habilitacion:
        return Habilitacion(
            **self.model_dump(),
            usuario_registro_id=usuario_id,
        )


class RegistrarNotaHabilitacionDTO(BaseModel):
    """Datos para registrar la nota cuando el estudiante presenta la habilitación."""
    nota:        float
    fecha:       date | None = None
    usuario_id:  int | None  = None
    observacion: str | None  = None

    @field_validator("nota")
    @classmethod
    def validar_nota(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)


class NuevoPlanMejoramientoDTO(BaseModel):
    """Datos para crear un plan de mejoramiento."""
    estudiante_id:          int
    asignacion_id:          int
    periodo_id:             int
    descripcion_dificultad: str
    actividades_propuestas: str
    fecha_seguimiento:      date | None = None

    @field_validator("descripcion_dificultad", "actividades_propuestas", mode="before")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El campo no puede estar vacío.")
        return v

    def to_plan(self, usuario_id: int | None = None) -> PlanMejoramiento:
        return PlanMejoramiento(
            **self.model_dump(),
            usuario_id=usuario_id,
        )


class CerrarPlanMejoramientoDTO(BaseModel):
    """Datos para cerrar un plan de mejoramiento."""
    estado:      EstadoPlanMejoramiento
    observacion: str
    fecha:       date | None = None

    @field_validator("estado")
    @classmethod
    def validar_estado_cierre(cls, v: EstadoPlanMejoramiento) -> EstadoPlanMejoramiento:
        if v == EstadoPlanMejoramiento.ACTIVO:
            raise ValueError(
                "No se puede cerrar un plan con estado ACTIVO. "
                "Use CUMPLIDO o INCUMPLIDO."
            )
        return v

    @field_validator("observacion", mode="before")
    @classmethod
    def validar_observacion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La observación de cierre no puede estar vacía.")
        return v


class FiltroHabilitacionesDTO(BaseModel):
    """Parámetros para listar habilitaciones."""
    estudiante_id: int | None               = None
    asignacion_id: int | None               = None
    periodo_id:    int | None               = None
    tipo:          TipoHabilitacion | None  = None
    estado:        EstadoHabilitacion | None = None
    pagina:        int                      = Field(default=1, ge=1)
    por_pagina:    int                      = Field(default=50, ge=1, le=200)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "TipoHabilitacion",
    "EstadoHabilitacion",
    "EstadoPlanMejoramiento",
    # Entidades
    "Habilitacion",
    "PlanMejoramiento",
    # DTOs
    "NuevaHabilitacionDTO",
    "RegistrarNotaHabilitacionDTO",
    "NuevoPlanMejoramientoDTO",
    "CerrarPlanMejoramientoDTO",
    "FiltroHabilitacionesDTO",
]