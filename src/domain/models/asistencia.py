"""
Modelo de dominio: Asistencia
==============================

Contiene:
  Enums    — EstadoAsistencia
  Entidad  — ControlDiario
  Read models — ResumenAsistenciaDTO, RegistroAsistenciaItemDTO
  DTOs     — RegistrarAsistenciaDTO, RegistrarAsistenciaMasivaDTO,
              FiltroAsistenciaDTO

Corrección de v1.0:
  El schema de v1.0 definía estados ('P', 'A', 'R', 'J', 'E')
  pero el código usaba ('P', 'FJ', 'FI', 'R', 'E'). El schema v2.0
  usa la convención del código:
    P  → Presente
    FJ → Falta Justificada
    FI → Falta Injustificada
    R  → Retraso
    E  → Excusa médica

Reglas de negocio:
  - fecha no puede ser futura (no se puede tomar asistencia de mañana).
  - hora_entrada < hora_salida si ambas existen.
  - Un registro por estudiante por asignacion por fecha
    (UNIQUE constraint en BD, ON CONFLICT REPLACE).
  - El estado 'P' no requiere observación.
  - Los estados FJ y E típicamente requieren una justificación
    (observación), pero no se fuerza en el modelo para no bloquear
    registros rápidos en campo.

ResumenAsistenciaDTO:
  Calculado por el repositorio con GROUP BY. El servicio lo retorna
  directamente al panel de seguimiento y al boletín.
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class EstadoAsistencia(str, Enum):
    PRESENTE            = "P"
    FALTA_JUSTIFICADA   = "FJ"
    FALTA_INJUSTIFICADA = "FI"
    RETRASO             = "R"
    EXCUSA              = "E"

    @property
    def es_falta(self) -> bool:
        return self in (
            EstadoAsistencia.FALTA_JUSTIFICADA,
            EstadoAsistencia.FALTA_INJUSTIFICADA,
        )

    @property
    def afecta_porcentaje(self) -> bool:
        """False para estados que no penalizan el porcentaje de asistencia."""
        return self in (
            EstadoAsistencia.FALTA_INJUSTIFICADA
        )

    @property
    def descripcion(self) -> str:
        descripciones = {
            "P":  "Presente",
            "FJ": "Falta Justificada",
            "FI": "Falta Injustificada",
            "R":  "Retraso",
            "E":  "Excusa",
        }
        return descripciones[self.value]


# =============================================================================
# Entidad
# =============================================================================

class ControlDiario(BaseModel):
    """
    Registro de asistencia de un estudiante a una clase específica.

    El campo `fecha_actualizacion` se actualiza automáticamente cuando
    el trigger ON CONFLICT REPLACE recrea el registro. En el modelo,
    se inicializa al momento de construcción.
    """
    id:                  int | None          = None
    estudiante_id:       int
    grupo_id:            int
    asignacion_id:       int
    periodo_id:          int
    fecha:               date                = Field(default_factory=date.today)
    estado:              EstadoAsistencia    = EstadoAsistencia.PRESENTE
    hora_entrada:        time | None         = None
    hora_salida:         time | None         = None
    uniforme:            bool                = True
    materiales:          bool                = True
    observacion:         str | None          = None
    usuario_registro_id: int | None          = None
    fecha_actualizacion: datetime            = Field(default_factory=datetime.now)

    @field_validator("estudiante_id", "grupo_id", "asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("fecha", mode="before")
    @classmethod
    def validar_fecha(cls, v: date | str) -> date:
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(
                f"No se puede registrar asistencia para una fecha futura ({v})."
            )
        return v

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("hora_entrada", "hora_salida", mode="before")
    @classmethod
    def parsear_hora(cls, v: time | str | None) -> time | None:
        if v is None:
            return None
        if isinstance(v, time):
            return v
        partes = str(v).strip().split(":")
        if len(partes) < 2:
            raise ValueError(f"Formato de hora inválido: '{v}'. Use HH:MM.")
        try:
            return time(int(partes[0]), int(partes[1]))
        except ValueError:
            raise ValueError(f"Hora fuera de rango: '{v}'.")

    @model_validator(mode="after")
    def validar_horas(self) -> Self:
        if (
            self.hora_entrada is not None
            and self.hora_salida is not None
            and self.hora_entrada >= self.hora_salida
        ):
            raise ValueError(
                f"hora_entrada ({self.hora_entrada}) debe ser anterior "
                f"a hora_salida ({self.hora_salida})."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def es_presencia_efectiva(self) -> bool:
        """True si el estudiante estuvo presente (incluso con retraso)."""
        return self.estado in (
            EstadoAsistencia.PRESENTE,
            EstadoAsistencia.RETRASO,
            EstadoAsistencia.EXCUSA,
        )

    @property
    def requiere_justificacion(self) -> bool:
        """True si el estado normalmente requiere una observación."""
        return self.estado in (
            EstadoAsistencia.FALTA_JUSTIFICADA,
            EstadoAsistencia.EXCUSA,
        )

    @property
    def estado_descripcion(self) -> str:
        return self.estado.descripcion


# =============================================================================
# Read models
# =============================================================================

class ResumenAsistenciaDTO(BaseModel):
    """
    Resumen de asistencia de un estudiante en un periodo o rango de fechas.
    Calculado por el repositorio con GROUP BY; la página lo muestra directamente.
    """
    estudiante_id:        int
    total_clases:         int   = 0
    presentes:            int   = 0
    faltas_justificadas:  int   = 0
    faltas_injustificadas: int  = 0
    retrasos:             int   = 0
    excusas:              int   = 0

    @field_validator("total_clases", "presentes", "faltas_justificadas",
                     "faltas_injustificadas", "retrasos", "excusas")
    @classmethod
    def no_negativo(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"El conteo no puede ser negativo (recibido: {v}).")
        return v

    @property
    def porcentaje_asistencia(self) -> float:
        """
        Porcentaje considerando solo faltas injustificadas y retrasos
        como ausencias reales. Faltas justificadas y excusas no penalizan.
        """
        if self.total_clases == 0:
            return 0.0
        ausencias_reales = self.faltas_injustificadas + self.retrasos
        return round((1 - ausencias_reales / self.total_clases) * 100, 1)

    @property
    def total_faltas(self) -> int:
        return self.faltas_justificadas + self.faltas_injustificadas

    @property
    def en_riesgo_por_faltas(self, umbral: float = 80.0) -> bool:
        """True si el porcentaje de asistencia está por debajo del umbral."""
        return self.porcentaje_asistencia < umbral

    @property
    def resumen_display(self) -> str:
        """'P:18 FI:2 FJ:1 R:1 E:0 (90.0%)'"""
        return (
            f"P:{self.presentes} FI:{self.faltas_injustificadas} "
            f"FJ:{self.faltas_justificadas} R:{self.retrasos} "
            f"E:{self.excusas} ({self.porcentaje_asistencia}%)"
        )


class RegistroAsistenciaItemDTO(BaseModel):
    """
    Un ítem dentro de un registro masivo de asistencia.
    Representa la asistencia de un único estudiante en un registro grupal.
    """
    estudiante_id: int
    estado:        EstadoAsistencia = EstadoAsistencia.PRESENTE
    observacion:   str | None       = None

    @field_validator("estudiante_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"estudiante_id debe ser positivo (recibido: {v}).")
        return v


# =============================================================================
# DTOs
# =============================================================================

class RegistrarAsistenciaDTO(BaseModel):
    """Datos para registrar la asistencia de un único estudiante."""
    estudiante_id:       int
    grupo_id:            int
    asignacion_id:       int
    periodo_id:          int
    fecha:               date                = Field(default_factory=date.today)
    estado:              EstadoAsistencia    = EstadoAsistencia.PRESENTE
    hora_entrada:        time | None         = None
    hora_salida:         time | None         = None
    uniforme:            bool                = True
    materiales:          bool                = True
    observacion:         str | None          = None
    usuario_registro_id: int | None          = None

    @field_validator("fecha", mode="before")
    @classmethod
    def validar_fecha(cls, v: date | str) -> date:
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(f"La fecha no puede ser futura ({v}).")
        return v

    def to_control(self) -> ControlDiario:
        return ControlDiario(**self.model_dump())


class RegistrarAsistenciaMasivaDTO(BaseModel):
    """
    Registra la asistencia de todos los estudiantes de un grupo
    en una misma fecha y asignación. Operación atómica — el servicio
    crea un ControlDiario por cada item.
    """
    grupo_id:            int
    asignacion_id:       int
    periodo_id:          int
    fecha:               date                        = Field(default_factory=date.today)
    registros:           list[RegistroAsistenciaItemDTO] = Field(default_factory=list)
    usuario_registro_id: int | None                  = None

    @field_validator("fecha", mode="before")
    @classmethod
    def validar_fecha(cls, v: date | str) -> date:
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(f"La fecha no puede ser futura ({v}).")
        return v

    @field_validator("registros")
    @classmethod
    def validar_registros(cls, v: list) -> list:
        if not v:
            raise ValueError("La lista de registros no puede estar vacía.")
        return v

    @property
    def total_estudiantes(self) -> int:
        return len(self.registros)

    def to_controles(
        self,
        uniforme_default: bool = True,
        materiales_default: bool = True,
    ) -> list[ControlDiario]:
        """Construye la lista de ControlDiario para persistir."""
        return [
            ControlDiario(
                estudiante_id       = item.estudiante_id,
                grupo_id            = self.grupo_id,
                asignacion_id       = self.asignacion_id,
                periodo_id          = self.periodo_id,
                fecha               = self.fecha,
                estado              = item.estado,
                observacion         = item.observacion,
                uniforme            = uniforme_default,
                materiales          = materiales_default,
                usuario_registro_id = self.usuario_registro_id,
            )
            for item in self.registros
        ]


class FiltroAsistenciaDTO(BaseModel):
    """Parámetros para consultar registros de asistencia."""
    estudiante_id: int | None               = None
    grupo_id:      int | None               = None
    asignacion_id: int | None               = None
    periodo_id:    int | None               = None
    estado:        EstadoAsistencia | None  = None
    fecha_desde:   date | None              = None
    fecha_hasta:   date | None              = None
    pagina:        int                      = Field(default=1, ge=1)
    por_pagina:    int                      = Field(default=100, ge=1, le=500)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EstadoAsistencia",
    "ControlDiario",
    "ResumenAsistenciaDTO",
    "RegistroAsistenciaItemDTO",
    "RegistrarAsistenciaDTO",
    "RegistrarAsistenciaMasivaDTO",
    "FiltroAsistenciaDTO",
]