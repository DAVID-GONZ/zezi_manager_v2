"""
Modelo de dominio: Institución
===============================

Contiene:
  Entidad  — Institucion
  DTOs     — NuevaInstitucionDTO, InstitucionResumenDTO

Primer ladrillo del modelo multi-tenant (paso_24). Hoy existe una sola
configuración institucional (singleton `configuracion_anio`). Esta entidad
introduce un catálogo de instituciones; la institución #1 se siembra desde
`configuracion.nombre_institucion`.

Reglas de negocio:
  - `nombre` no puede estar vacío y se normaliza (strip).
  - `nit`/`codigo` son opcionales (identificadores externos, p.ej. DANE).
  - Soft state: las instituciones no se eliminan, se marcan inactivas.
  - El servicio garantiza la unicidad del nombre (no el modelo).

Fuera de alcance (paso_24): `institucion_id` en tablas académicas
(config/años/grupos). Aislamiento total por tenant.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Enums (mejora_06)
# =============================================================================

class JornadaPrincipal(str, Enum):
    AM    = "AM"
    PM    = "PM"
    UNICA = "UNICA"


class TipoInstitucion(str, Enum):
    PUBLICA  = "publica"
    PRIVADA  = "privada"


class Calendario(str, Enum):
    A = "A"
    B = "B"


# =============================================================================
# Entidad principal
# =============================================================================

class Institucion(BaseModel):
    """
    Una institución educativa (tenant) registrada en la plataforma.

    La institución #1 representa la institución por defecto, sembrada a partir
    de la configuración institucional existente.
    """
    id:             int | None  = None
    nombre:         str
    nit:            str | None   = None   # NIT / identificador tributario
    codigo:         str | None   = None   # código externo (p.ej. DANE)
    activa:         bool         = True
    fecha_creacion: date         = Field(default_factory=date.today)

    # Campos de identidad institucional (mejora_06)
    nombre_oficial:         str | None              = None
    codigo_dane:            str | None              = None
    rector:                 str | None              = None
    direccion:              str | None              = None
    municipio:              str | None              = None
    telefono:               str | None              = None
    logo_path:              str | None              = None
    logo_url:               str | None              = None
    resolucion_aprobacion:  str | None              = None
    lema:                   str | None              = None
    email_institucional:    str | None              = None
    jornada_principal:      JornadaPrincipal | None = None
    tipo_institucion:       TipoInstitucion  | None = None
    calendario:             Calendario       | None = None

    # Aprovisionamiento (mejora_09a): indica si el tenant ya completó su
    # configuración inicial obligatoria (wizard de mejora_09b). Los tenants
    # creados por el admin nacen en False; la institución #1 (demo) se marca
    # True en el seed.
    configuracion_inicial_completa: bool = False

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la institución no puede estar vacío.")
        if len(v) > 200:
            raise ValueError(
                f"El nombre no puede exceder 200 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("nit", "codigo", mode="before")
    @classmethod
    def limpiar_opcional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("codigo_dane", mode="before")
    @classmethod
    def validar_codigo_dane(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if not v:
            return None
        if not v.isdigit() or len(v) != 12:
            raise ValueError("El código DANE debe tener exactamente 12 dígitos numéricos.")
        return v

    @field_validator("nombre_oficial", mode="before")
    @classmethod
    def validar_nombre_oficial(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre oficial no puede ser una cadena vacía.")
        if len(v) > 200:
            raise ValueError(f"El nombre oficial no puede exceder 200 caracteres.")
        return v

    @property
    def nombre_display(self) -> str:
        """'Colegio X' o 'Colegio X (inactiva)'."""
        return self.nombre + ("" if self.activa else " (inactiva)")


# =============================================================================
# DTOs
# =============================================================================

class NuevaInstitucionDTO(BaseModel):
    """Datos para crear una institución nueva."""
    nombre: str
    nit:    str | None = None
    codigo: str | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la institución no puede estar vacío.")
        if len(v) > 200:
            raise ValueError(
                f"El nombre no puede exceder 200 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("nit", "codigo", mode="before")
    @classmethod
    def limpiar_opcional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    def to_institucion(self) -> Institucion:
        return Institucion(**self.model_dump())


class ActualizarInstitucionDTO(BaseModel):
    """Campos editables de la entidad Institucion. Todos opcionales."""
    nombre:                str | None              = None
    nit:                   str | None              = None
    nombre_oficial:        str | None              = None
    codigo_dane:           str | None              = None
    rector:                str | None              = None
    direccion:             str | None              = None
    municipio:             str | None              = None
    telefono:              str | None              = None
    logo_path:             str | None              = None
    logo_url:              str | None              = None
    resolucion_aprobacion: str | None              = None
    lema:                  str | None              = None
    email_institucional:   str | None              = None
    jornada_principal:     JornadaPrincipal | None = None
    tipo_institucion:      TipoInstitucion  | None = None
    calendario:            Calendario       | None = None

    def aplicar_a(self, inst: "Institucion") -> "Institucion":
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return inst.model_copy(update=cambios) if cambios else inst


class InstitucionResumenDTO(BaseModel):
    """Vista mínima para selects, filtros y lookups."""
    id:     int
    nombre: str
    activa: bool

    @classmethod
    def desde_institucion(cls, i: Institucion) -> InstitucionResumenDTO:
        if i.id is None:
            raise ValueError("No se puede resumir una institución sin id.")
        return cls(id=i.id, nombre=i.nombre, activa=i.activa)


class NuevaInstitucionConDirectorDTO(BaseModel):
    """
    Datos para el flujo combinado (mejora_09a): un admin crea una institución
    nueva junto con su usuario director en una sola operación.

    La identidad institucional completa (rector, dirección, logo, etc.) y las
    preferencias las completa el director en el wizard de configuración
    inicial (mejora_09b); aquí solo se piden los datos mínimos de arranque.
    """
    # Institución — datos básicos.
    nombre:          str
    nombre_oficial:  str | None = None
    codigo_dane:     str | None = None
    municipio:       str | None = None

    # Director — la contraseña la genera el servicio (temporal, si no se
    # provee); no se pide aquí.
    director_usuario:         str
    director_nombre_completo: str
    director_email:           str | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la institución no puede estar vacío.")
        if len(v) > 200:
            raise ValueError(
                f"El nombre no puede exceder 200 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("nombre_oficial", mode="before")
    @classmethod
    def validar_nombre_oficial(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if not v:
            return None
        if len(v) > 200:
            raise ValueError("El nombre oficial no puede exceder 200 caracteres.")
        return v

    @field_validator("codigo_dane", mode="before")
    @classmethod
    def validar_codigo_dane(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if not v:
            return None
        if not v.isdigit() or len(v) != 12:
            raise ValueError("El código DANE debe tener exactamente 12 dígitos numéricos.")
        return v

    @field_validator("municipio", mode="before")
    @classmethod
    def limpiar_municipio(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("director_usuario", mode="before")
    @classmethod
    def validar_director_usuario(cls, v: str) -> str:
        v = str(v).strip()
        if not v or " " in v or len(v) < 3:
            raise ValueError(
                "El nombre de usuario del director debe tener mínimo 3 "
                "caracteres y sin espacios."
            )
        return v.lower()

    @field_validator("director_nombre_completo", mode="before")
    @classmethod
    def validar_director_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 3:
            raise ValueError(
                "El nombre completo del director debe tener al menos 3 caracteres."
            )
        return v

    @field_validator("director_email", mode="before")
    @classmethod
    def limpiar_director_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None


class ResultadoAprovisionamientoDTO(BaseModel):
    """
    Resultado de crear una institución con su director (mejora_09a).

    `password_temporal` viaja una sola vez para que el admin la comunique al
    director; no se persiste ni se vuelve a exponer.
    """
    institucion:       Institucion
    director_usuario:  str
    password_temporal: str | None = None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ActualizarInstitucionDTO",
    "Calendario",
    "Institucion",
    "InstitucionResumenDTO",
    "JornadaPrincipal",
    "NuevaInstitucionConDirectorDTO",
    "NuevaInstitucionDTO",
    "ResultadoAprovisionamientoDTO",
    "TipoInstitucion",
]
