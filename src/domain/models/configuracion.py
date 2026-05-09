"""
Modelo de dominio: Configuración del año lectivo
=================================================

Contiene:
  Entidad  — ConfiguracionAnio
  DTOs     — NuevaConfiguracionAnioDTO, ActualizarConfiguracionAnioDTO,
              ActualizarInfoInstitucionalDTO, InformacionInstitucionalDTO

ConfiguracionAnio es el eje de toda la configuración académica.
Cada año lectivo tiene exactamente una configuración activa.
La regla de "solo un año activo" es de servicio, no de modelo.

Relación con otros módulos (todo referencia anio_id):
  periodos            → configura cuántos y con qué peso
  niveles_desempeno   → rangos Bajo/Básico/Alto/Superior
  criterios_promocion → max materias perdidas, nota mínima
  configuracion_alertas → umbrales de alertas automáticas

InformacionInstitucionalDTO agrupa los campos que aparecen en
boletines e informes: nombre, DANE, rector, dirección, logo.
El generador de boletines consume este DTO directamente.
"""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Entidad principal
# =============================================================================

class ConfiguracionAnio(BaseModel):
    """
    Configuración del año lectivo activo.

    Un año puede estar activo (el actual) o inactivo (histórico).
    Los módulos de notas y asistencia usan el año activo como referencia
    para determinar qué periodos y qué configuraciones están vigentes.
    """
    id:                     int | None  = None
    anio:                   int
    fecha_inicio_clases:    date | None = None
    fecha_fin_clases:       date | None = None
    nota_minima_aprobacion: float       = 60.0
    activo:                 bool        = True

    # Datos institucionales (para boletines e informes)
    nombre_institucion:     str         = "Institución Educativa"
    dane_code:              str | None  = None
    rector:                 str | None  = None
    direccion:              str | None  = None
    municipio:              str | None  = None
    telefono_institucion:   str | None  = None
    logo_path:              str | None  = None
    resolucion_aprobacion:  str | None  = None

    # ------------------------------------------------------------------
    # Validadores de campo
    # ------------------------------------------------------------------

    @field_validator("anio")
    @classmethod
    def validar_anio(cls, v: int) -> int:
        if not (2000 <= v <= 2100):
            raise ValueError(
                f"El año debe estar entre 2000 y 2100 (recibido: {v})."
            )
        return v

    @field_validator("nota_minima_aprobacion")
    @classmethod
    def validar_nota_minima(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(
                f"La nota mínima debe estar entre 0 y 100 (recibido: {v})."
            )
        return round(v, 2)

    @field_validator("nombre_institucion", mode="before")
    @classmethod
    def validar_nombre_institucion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la institución no puede estar vacío.")
        if len(v) > 200:
            raise ValueError(
                f"El nombre no puede exceder 200 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator(
        "dane_code", "rector", "direccion", "municipio",
        "telefono_institucion", "logo_path", "resolucion_aprobacion",
        mode="before",
    )
    @classmethod
    def limpiar_campo_opcional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    # ------------------------------------------------------------------
    # Validador de modelo
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validar_fechas(self) -> Self:
        if (
            self.fecha_inicio_clases
            and self.fecha_fin_clases
            and self.fecha_inicio_clases > self.fecha_fin_clases
        ):
            raise ValueError(
                f"La fecha de inicio ({self.fecha_inicio_clases}) no puede ser "
                f"posterior a la fecha de fin ({self.fecha_fin_clases})."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def anio_display(self) -> str:
        """'2025' o '2025 (activo)'"""
        return f"{self.anio}" + (" (activo)" if self.activo else "")

    @property
    def rango_fechas_display(self) -> str:
        """'20 enero – 15 diciembre 2025' o 'Fechas no definidas'"""
        if not self.fecha_inicio_clases or not self.fecha_fin_clases:
            return "Fechas no definidas"
        return (
            f"{self.fecha_inicio_clases.strftime('%d %b')} – "
            f"{self.fecha_fin_clases.strftime('%d %b %Y')}"
        )

    @property
    def duracion_semanas(self) -> int | None:
        """Semanas de duración del año escolar."""
        if not self.fecha_inicio_clases or not self.fecha_fin_clases:
            return None
        dias = (self.fecha_fin_clases - self.fecha_inicio_clases).days
        return dias // 7

    @property
    def tiene_informacion_institucional(self) -> bool:
        """True si tiene los campos mínimos para generar boletines."""
        return bool(self.dane_code and self.rector)

    # ------------------------------------------------------------------
    # Transiciones de estado
    # ------------------------------------------------------------------

    def activar(self) -> "ConfiguracionAnio":
        """
        Retorna una copia del año marcada como activa.
        El servicio debe verificar que ningún otro año esté activo.
        """
        if self.activo:
            raise ValueError(f"El año {self.anio} ya está activo.")
        return self.model_copy(update={"activo": True})

    def desactivar(self) -> "ConfiguracionAnio":
        """Retorna una copia marcada como inactiva."""
        if not self.activo:
            raise ValueError(f"El año {self.anio} ya está inactivo.")
        return self.model_copy(update={"activo": False})


# =============================================================================
# DTOs
# =============================================================================

class NuevaConfiguracionAnioDTO(BaseModel):
    """Datos para crear un año lectivo nuevo."""
    anio:                   int
    fecha_inicio_clases:    date | None = None
    fecha_fin_clases:       date | None = None
    nota_minima_aprobacion: float       = 60.0
    nombre_institucion:     str         = "Institución Educativa"

    @field_validator("anio")
    @classmethod
    def validar_anio(cls, v: int) -> int:
        if not (2000 <= v <= 2100):
            raise ValueError(f"El año debe estar entre 2000 y 2100 (recibido: {v}).")
        return v

    @field_validator("nota_minima_aprobacion")
    @classmethod
    def validar_nota(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(f"La nota mínima debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    @model_validator(mode="after")
    def validar_fechas(self) -> Self:
        if (
            self.fecha_inicio_clases
            and self.fecha_fin_clases
            and self.fecha_inicio_clases > self.fecha_fin_clases
        ):
            raise ValueError("La fecha de inicio no puede ser posterior a la de fin.")
        return self

    def to_configuracion(self) -> ConfiguracionAnio:
        return ConfiguracionAnio(**self.model_dump())


class ActualizarConfiguracionAnioDTO(BaseModel):
    """Campos académicos actualizables. Todos opcionales."""
    anio:                   int | None   = None
    fecha_inicio_clases:    date | None  = None
    fecha_fin_clases:       date | None  = None
    nota_minima_aprobacion: float | None = None

    @field_validator("nota_minima_aprobacion")
    @classmethod
    def validar_nota(cls, v: float | None) -> float | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError(f"La nota mínima debe estar entre 0 y 100 (recibido: {v}).")
        return v

    def aplicar_a(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return config.model_copy(update=cambios) if cambios else config


class ActualizarInfoInstitucionalDTO(BaseModel):
    """
    Campos institucionales para boletines e informes.
    Separados de los campos académicos para que directivos
    puedan actualizar la información del colegio sin
    afectar la configuración de notas.
    """
    nombre_institucion:    str | None = None
    dane_code:             str | None = None
    rector:                str | None = None
    direccion:             str | None = None
    municipio:             str | None = None
    telefono_institucion:  str | None = None
    logo_path:             str | None = None
    resolucion_aprobacion: str | None = None

    @field_validator("nombre_institucion", mode="before")
    @classmethod
    def validar_nombre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede ser una cadena vacía.")
        return v

    def aplicar_a(self, config: ConfiguracionAnio) -> ConfiguracionAnio:
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return config.model_copy(update=cambios) if cambios else config


class InformacionInstitucionalDTO(BaseModel):
    """
    Datos de la institución necesarios para generar boletines.
    El generador de informes construye este DTO desde ConfiguracionAnio.
    Todos los campos son obligatorios para garantizar boletines completos.
    """
    anio:                   int
    nombre_institucion:     str
    dane_code:              str
    rector:                 str
    nota_minima_aprobacion: float
    direccion:              str | None = None
    municipio:              str | None = None
    telefono_institucion:   str | None = None
    logo_path:              str | None = None
    resolucion_aprobacion:  str | None = None

    @classmethod
    def desde_configuracion(
        cls, config: ConfiguracionAnio
    ) -> "InformacionInstitucionalDTO":
        """
        Construye el DTO desde una ConfiguracionAnio.
        Falla explícitamente si faltan campos obligatorios para boletines.
        """
        if not config.dane_code:
            raise ValueError(
                f"El año {config.anio} no tiene código DANE. "
                "Completa la información institucional antes de generar boletines."
            )
        if not config.rector:
            raise ValueError(
                f"El año {config.anio} no tiene rector registrado. "
                "Completa la información institucional antes de generar boletines."
            )
        return cls(
            anio                   = config.anio,
            nombre_institucion     = config.nombre_institucion,
            dane_code              = config.dane_code,
            rector                 = config.rector,
            nota_minima_aprobacion = config.nota_minima_aprobacion,
            direccion              = config.direccion,
            municipio              = config.municipio,
            telefono_institucion   = config.telefono_institucion,
            logo_path              = config.logo_path,
            resolucion_aprobacion  = config.resolucion_aprobacion,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ConfiguracionAnio",
    "NuevaConfiguracionAnioDTO",
    "ActualizarConfiguracionAnioDTO",
    "ActualizarInfoInstitucionalDTO",
    "InformacionInstitucionalDTO",
]