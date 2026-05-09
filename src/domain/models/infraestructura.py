"""
Modelo de dominio: Infraestructura académica
=============================================

Entidades estructurales que soportan el funcionamiento del sistema
pero no tienen lógica de negocio compleja. Son los cimientos sobre
los que se construyen asignaciones, evaluaciones y asistencia.

Contiene:
  Enums    — Jornada, DiaSemana
  Entidades — AreaConocimiento, Asignatura, Grupo, Horario, Logro
  DTOs     — uno por entidad

Regla general: los campos de texto obligatorios se normalizan
(strip + title-case donde aplica). Los IDs de FK deben ser positivos.
"""

from __future__ import annotations

from datetime import time
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class Jornada(str, Enum):
    AM    = "AM"
    PM    = "PM"
    UNICA = "UNICA"


class DiaSemana(str, Enum):
    LUNES     = "Lunes"
    MARTES    = "Martes"
    MIERCOLES = "Miércoles"
    JUEVES    = "Jueves"
    VIERNES   = "Viernes"
    SABADO    = "Sábado"


# =============================================================================
# Entidades
# =============================================================================

class AreaConocimiento(BaseModel):
    """
    Área del currículo colombiano (Ley 115 de 1994, Art. 23).
    Ejemplos: 'Matemáticas', 'Ciencias Naturales y Educación Ambiental'.
    """
    id:     int | None  = None
    nombre: str
    codigo: str | None  = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre del área no puede estar vacío.")
        if len(v) > 120:
            raise ValueError(
                f"El nombre no puede exceder 120 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("codigo", mode="before")
    @classmethod
    def limpiar_codigo(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip().upper()
        return v if v else None


class Asignatura(BaseModel):
    """
    Asignatura que se dicta en la institución.
    Pertenece a un área de conocimiento.
    """
    id:              int | None = None
    nombre:          str
    codigo:          str | None = None
    area_id:         int | None = None
    horas_semanales: int        = Field(default=1, ge=1)

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la asignatura no puede estar vacío.")
        if len(v) > 100:
            raise ValueError(
                f"El nombre no puede exceder 100 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("codigo", mode="before")
    @classmethod
    def limpiar_codigo(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip().upper()
        return v if v else None

    @field_validator("area_id")
    @classmethod
    def validar_area_id(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError(f"area_id debe ser positivo (recibido: {v}).")
        return v


class Grupo(BaseModel):
    """
    Grupo escolar (curso). Cada grupo tiene un grado, jornada y
    capacidad máxima de estudiantes.

    El código es el identificador legible: '601', '1101', 'A1', etc.
    """
    id:               int | None = None
    codigo:           str
    nombre:           str | None = None
    grado:            int | None = None
    jornada:          Jornada    = Jornada.UNICA
    capacidad_maxima: int        = Field(default=40, ge=1)

    @field_validator("codigo", mode="before")
    @classmethod
    def validar_codigo(cls, v: str) -> str:
        v = str(v).strip().upper()
        if not v:
            raise ValueError("El código del grupo no puede estar vacío.")
        if len(v) > 20:
            raise ValueError(
                f"El código no puede exceder 20 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("nombre", mode="before")
    @classmethod
    def limpiar_nombre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("grado")
    @classmethod
    def validar_grado(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 13):
            raise ValueError(
                f"El grado debe estar entre 1 y 13 (recibido: {v})."
            )
        return v

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def descripcion_completa(self) -> str:
        """
        Descripción larga para encabezados:
          Con nombre: '601 — Sexto A (AM)'
          Sin nombre: '601 (AM)'
        """
        jornada = f"({self.jornada.value})"
        if self.nombre:
            return f"{self.codigo} — {self.nombre} {jornada}"
        return f"{self.codigo} {jornada}"

    @property
    def descripcion_corta(self) -> str:
        """'601' o 'Sexto A' si hay nombre."""
        return self.nombre or self.codigo

    def esta_lleno(self, matriculados: int) -> bool:
        """True si el número de matriculados alcanza la capacidad máxima."""
        if matriculados < 0:
            raise ValueError(
                f"El número de matriculados no puede ser negativo (recibido: {matriculados})."
            )
        return matriculados >= self.capacidad_maxima

    def cupos_disponibles(self, matriculados: int) -> int:
        """Cupos libres. 0 si ya está lleno."""
        return max(0, self.capacidad_maxima - matriculados)


class Horario(BaseModel):
    """
    Franja horaria de una asignatura para un grupo en un periodo.

    hora_inicio y hora_fin aceptan objetos time o strings "HH:MM".
    Invariante: hora_inicio < hora_fin.
    """
    id:            int | None  = None
    grupo_id:      int
    asignatura_id: int
    usuario_id:    int
    asignacion_id: int | None  = None
    periodo_id:    int
    dia_semana:    DiaSemana
    hora_inicio:   time
    hora_fin:      time
    sala:          str         = "Aula"

    @field_validator("grupo_id", "asignatura_id", "usuario_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser un entero positivo (recibido: {v}).")
        return v

    @field_validator("hora_inicio", "hora_fin", mode="before")
    @classmethod
    def parsear_hora(cls, v: time | str) -> time:
        if isinstance(v, time):
            return v
        if isinstance(v, str):
            partes = v.strip().split(":")
            if len(partes) < 2:
                raise ValueError(
                    f"Formato de hora inválido: '{v}'. Use HH:MM."
                )
            try:
                return time(int(partes[0]), int(partes[1]))
            except ValueError:
                raise ValueError(
                    f"Hora fuera de rango: '{v}'."
                )
        raise ValueError(f"Tipo de hora no soportado: {type(v)}.")

    @field_validator("sala", mode="before")
    @classmethod
    def validar_sala(cls, v: str) -> str:
        v = str(v).strip()
        return v if v else "Aula"

    @model_validator(mode="after")
    def validar_orden_horas(self) -> Self:
        if self.hora_inicio >= self.hora_fin:
            raise ValueError(
                f"hora_inicio ({self.hora_inicio}) debe ser anterior "
                f"a hora_fin ({self.hora_fin})."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def duracion_minutos(self) -> int:
        """Duración de la clase en minutos."""
        inicio = self.hora_inicio.hour * 60 + self.hora_inicio.minute
        fin    = self.hora_fin.hour    * 60 + self.hora_fin.minute
        return fin - inicio

    @property
    def franja_display(self) -> str:
        """
        Representación para mostrar en grillas de horario:
        'Lunes 07:00–07:55'
        """
        return (
            f"{self.dia_semana.value} "
            f"{self.hora_inicio.strftime('%H:%M')}–"
            f"{self.hora_fin.strftime('%H:%M')}"
        )


class Logro(BaseModel):
    """
    Logro o competencia evaluado en una asignación durante un periodo.

    El logro es el enunciado del aprendizaje esperado que aparece
    en el boletín junto a la nota. Ejemplo:
    'Comprende y aplica los conceptos de función cuadrática.'
    """
    id:            int | None = None
    asignacion_id: int
    periodo_id:    int
    descripcion:   str
    orden:         int        = Field(default=0, ge=0)

    @field_validator("asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción del logro no puede estar vacía.")
        if len(v) > 500:
            raise ValueError(
                f"La descripción no puede exceder 500 caracteres (tiene {len(v)})."
            )
        return v


# =============================================================================
# DTOs
# =============================================================================

class NuevaAreaDTO(BaseModel):
    nombre: str
    codigo: str | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    def to_area(self) -> AreaConocimiento:
        return AreaConocimiento(**self.model_dump())


class NuevaAsignaturaDTO(BaseModel):
    nombre:          str
    codigo:          str | None = None
    area_id:         int | None = None
    horas_semanales: int        = 1

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    def to_asignatura(self) -> Asignatura:
        return Asignatura(**self.model_dump())


class NuevoGrupoDTO(BaseModel):
    codigo:           str
    nombre:           str | None = None
    grado:            int | None = None
    jornada:          Jornada    = Jornada.UNICA
    capacidad_maxima: int        = 40

    @field_validator("codigo", mode="before")
    @classmethod
    def validar_codigo(cls, v: str) -> str:
        v = str(v).strip().upper()
        if not v:
            raise ValueError("El código no puede estar vacío.")
        return v

    def to_grupo(self) -> Grupo:
        return Grupo(**self.model_dump())


class NuevoHorarioDTO(BaseModel):
    grupo_id:      int
    asignatura_id: int
    usuario_id:    int
    periodo_id:    int
    dia_semana:    DiaSemana
    hora_inicio:   time
    hora_fin:      time
    asignacion_id: int | None = None
    sala:          str        = "Aula"

    @field_validator("hora_inicio", "hora_fin", mode="before")
    @classmethod
    def parsear_hora(cls, v: time | str) -> time:
        if isinstance(v, time):
            return v
        partes = str(v).strip().split(":")
        return time(int(partes[0]), int(partes[1]))

    @model_validator(mode="after")
    def validar_horas(self) -> Self:
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("hora_inicio debe ser anterior a hora_fin.")
        return self

    def to_horario(self) -> Horario:
        return Horario(**self.model_dump())


class NuevoLogroDTO(BaseModel):
    asignacion_id: int
    periodo_id:    int
    descripcion:   str
    orden:         int = 0

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción no puede estar vacía.")
        return v

    def to_logro(self) -> Logro:
        return Logro(**self.model_dump())


# =============================================================================
# Modelos de lectura (read models desde JOINs)
# =============================================================================

class HorarioInfo(BaseModel):
    """
    Vista enriquecida de un bloque horario con nombres resueltos por JOIN.

    Equivalente a AsignacionInfo para el módulo de horarios. No se persiste:
    lo construye el repositorio desde una consulta con JOINs sobre grupos,
    asignaturas, usuarios y periodos.

    El grid de la página de horarios consume este modelo directamente.
    Los nombres de campo son los que el repositorio mapea desde las columnas
    del JOIN; la página v2.0 los usa sin transformación adicional.
    """
    id:                int
    grupo_id:          int
    grupo_codigo:      str          # grupos.codigo
    asignatura_id:     int
    asignatura_nombre: str          # asignaturas.nombre
    usuario_id:        int
    docente_nombre:    str          # usuarios.nombre_completo
    asignacion_id:     int | None
    periodo_id:        int
    periodo_nombre:    str          # periodos.nombre
    dia_semana:        DiaSemana
    hora_inicio:       time
    hora_fin:          time
    sala:              str          = "Aula"

    @field_validator("grupo_codigo", "asignatura_nombre",
                     "docente_nombre", "periodo_nombre", mode="before")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El campo no puede estar vacío.")
        return v

    @field_validator("hora_inicio", "hora_fin", mode="before")
    @classmethod
    def parsear_hora(cls, v: time | str) -> time:
        if isinstance(v, time):
            return v
        partes = str(v).strip().split(":")
        if len(partes) < 2:
            raise ValueError(f"Formato de hora inválido: '{v}'. Use HH:MM.")
        try:
            return time(int(partes[0]), int(partes[1]))
        except ValueError:
            raise ValueError(f"Hora fuera de rango: '{v}'.")

    # ------------------------------------------------------------------
    # Propiedades de display
    # ------------------------------------------------------------------

    @property
    def franja_display(self) -> str:
        """'Lunes 07:00–07:55'"""
        return (
            f"{self.dia_semana.value} "
            f"{self.hora_inicio.strftime('%H:%M')}–"
            f"{self.hora_fin.strftime('%H:%M')}"
        )

    @property
    def duracion_minutos(self) -> int:
        inicio = self.hora_inicio.hour * 60 + self.hora_inicio.minute
        fin    = self.hora_fin.hour    * 60 + self.hora_fin.minute
        return fin - inicio

    @property
    def display_completo(self) -> str:
        """
        Descripción completa para encabezados de horario:
        '601 | Matemáticas | Carlos López | Lunes 07:00–07:55'
        """
        return (
            f"{self.grupo_codigo} | {self.asignatura_nombre} | "
            f"{self.docente_nombre} | {self.franja_display}"
        )

    @property
    def display_corto(self) -> str:
        """Para chips o tooltips: 'Lunes 07:00–07:55 — Matemáticas'"""
        return f"{self.franja_display} — {self.asignatura_nombre}"


class HorarioEstadisticasDTO(BaseModel):
    """
    Métricas del horario maestro para el panel de estadísticas.

    El servicio calcula estos valores a partir de queries de agregación;
    la página los muestra directamente sin lógica adicional.
    """
    total_bloques:        int = 0   # filas totales en horarios
    grupos_cubiertos:     int = 0   # grupos con al menos un bloque
    materias_cargadas:    int = 0   # asignaturas distintas con horario
    docentes_con_horario: int = 0   # docentes con al menos un bloque


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Jornada",
    "DiaSemana",
    "AreaConocimiento",
    "Asignatura",
    "Grupo",
    "Horario",
    "HorarioInfo",
    "HorarioEstadisticasDTO",
    "Logro",
    "NuevaAreaDTO",
    "NuevaAsignaturaDTO",
    "NuevoGrupoDTO",
    "NuevoHorarioDTO",
    "NuevoLogroDTO",
]