"""
Modelo de dominio: Acudiente
=============================

Contiene:
  Enums    — TipoDocumentoAcudiente, Parentesco
  Entidades — Acudiente, EstudianteAcudiente
  DTOs     — NuevoAcudienteDTO, ActualizarAcudienteDTO,
              VincularAcudienteDTO, AcudienteResumenDTO

Reglas de negocio:
  - numero_documento es único en la tabla de acudientes.
  - Un acudiente puede estar vinculado a múltiples estudiantes
    (ej: un padre con varios hijos en la institución).
  - Un estudiante puede tener múltiples acudientes, pero solo
    uno puede ser marcado como principal (es_principal=True).
    La restricción de "solo uno principal" la verifica el servicio.
  - usuario_id es null en v2.0; se activa en v3.0 cuando se
    implemente el portal de acudientes.
  - Los acudientes no se eliminan; se desactivan (activo=False).

Diferencia con TipoDocumento de estudiante:
  Los adultos pueden tener PASAPORTE pero raramente NUIP.
  Los estudiantes tienen TI o CC pero raramente PASAPORTE.
  Por eso son enums separados con valores ligeramente distintos.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class TipoDocumentoAcudiente(str, Enum):
    CC        = "CC"        # Cédula de Ciudadanía
    CE        = "CE"        # Cédula de Extranjería
    TI        = "TI"        # Tarjeta de Identidad (acudiente menor)
    PASAPORTE = "PASAPORTE"


class Parentesco(str, Enum):
    PADRE       = "padre"
    MADRE       = "madre"
    ABUELO      = "abuelo"
    ABUELA      = "abuela"
    TIO         = "tio"
    TIA         = "tia"
    HERMANO     = "hermano"
    HERMANA     = "hermana"
    TUTOR_LEGAL = "tutor_legal"
    OTRO        = "otro"


# =============================================================================
# Entidades
# =============================================================================

class Acudiente(BaseModel):
    """
    Acudiente o responsable legal de uno o más estudiantes.

    En v1.0, los datos del acudiente estaban embebidos en la tabla
    `estudiantes` (celular_acudiente, email_acudiente), lo que impedía
    que un acudiente tuviera múltiples estudiantes a cargo y que los
    acudientes tuvieran acceso al portal.
    """
    id:               int | None                = None
    tipo_documento:   TipoDocumentoAcudiente    = TipoDocumentoAcudiente.CC
    numero_documento: str
    nombre_completo:  str
    parentesco:       Parentesco
    celular:          str | None                = None
    email:            str | None                = None
    direccion:        str | None                = None
    activo:           bool                      = True
    usuario_id:       int | None                = None  # portal v3.0

    @field_validator("numero_documento", mode="before")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El número de documento no puede estar vacío.")
        if not v.replace("-", "").replace(" ", "").isalnum():
            raise ValueError(
                f"El documento solo puede contener letras, números y guiones: '{v}'."
            )
        return v.upper()

    @field_validator("nombre_completo", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 3:
            raise ValueError(
                f"El nombre debe tener al menos 3 caracteres (tiene {len(v)})."
            )
        if len(v) > 150:
            raise ValueError(
                f"El nombre no puede exceder 150 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("celular", mode="before")
    @classmethod
    def limpiar_celular(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip().replace(" ", "").replace("-", "")
        return v if v else None

    @field_validator("email", mode="before")
    @classmethod
    def validar_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip().lower()
        if not v:
            return None
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError(f"El email no tiene un formato válido: '{v}'.")
        return v

    @field_validator("direccion", mode="before")
    @classmethod
    def limpiar_direccion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def esta_activo(self) -> bool:
        return self.activo

    @property
    def tiene_contacto(self) -> bool:
        """True si tiene al menos un medio de contacto."""
        return bool(self.celular or self.email)

    @property
    def contacto_display(self) -> str:
        """Primer medio de contacto disponible para notificaciones."""
        if self.celular:
            return f"📱 {self.celular}"
        if self.email:
            return f"✉️ {self.email}"
        return "Sin contacto registrado"

    @property
    def documento_display(self) -> str:
        return f"{self.tipo_documento.value} {self.numero_documento}"

    # ------------------------------------------------------------------
    # Transiciones de estado
    # ------------------------------------------------------------------

    def desactivar(self) -> "Acudiente":
        if not self.activo:
            raise ValueError(
                f"El acudiente '{self.nombre_completo}' ya está desactivado."
            )
        return self.model_copy(update={"activo": False})

    def reactivar(self) -> "Acudiente":
        if self.activo:
            raise ValueError(
                f"El acudiente '{self.nombre_completo}' ya está activo."
            )
        return self.model_copy(update={"activo": True})


class EstudianteAcudiente(BaseModel):
    """
    Vínculo entre un estudiante y un acudiente.

    es_principal=True indica que este es el acudiente de contacto
    principal: aparece en el boletín y recibe notificaciones prioritarias.
    El servicio garantiza que solo haya un acudiente principal por estudiante.
    """
    estudiante_id: int
    acudiente_id:  int
    es_principal:  bool = False

    @field_validator("estudiante_id", "acudiente_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v


# =============================================================================
# DTOs
# =============================================================================

class NuevoAcudienteDTO(BaseModel):
    """Datos para registrar un acudiente nuevo."""
    tipo_documento:   TipoDocumentoAcudiente    = TipoDocumentoAcudiente.CC
    numero_documento: str
    nombre_completo:  str
    parentesco:       Parentesco
    celular:          str | None                = None
    email:            str | None                = None
    direccion:        str | None                = None

    @field_validator("numero_documento", mode="before")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El número de documento no puede estar vacío.")
        return v.upper()

    @field_validator("nombre_completo", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 3:
            raise ValueError(f"El nombre debe tener al menos 3 caracteres (tiene {len(v)}).")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def validar_email(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = str(v).strip().lower()
        if "@" not in v:
            raise ValueError(f"El email debe contener '@': '{v}'.")
        return v

    def to_acudiente(self) -> Acudiente:
        return Acudiente(**self.model_dump())


class ActualizarAcudienteDTO(BaseModel):
    """Campos actualizables de un acudiente. Todos opcionales."""
    nombre_completo: str | None = None
    parentesco:      Parentesco | None = None
    celular:         str | None = None
    email:           str | None = None
    direccion:       str | None = None

    @field_validator("nombre_completo", mode="before")
    @classmethod
    def validar_nombre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if len(v) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres.")
        return v

    def aplicar_a(self, acudiente: Acudiente) -> Acudiente:
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return acudiente.model_copy(update=cambios) if cambios else acudiente


class VincularAcudienteDTO(BaseModel):
    """Vincula un acudiente existente a un estudiante."""
    estudiante_id: int
    acudiente_id:  int
    es_principal:  bool = False

    @field_validator("estudiante_id", "acudiente_id")
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    def to_vinculo(self) -> EstudianteAcudiente:
        return EstudianteAcudiente(**self.model_dump())


class AcudienteResumenDTO(BaseModel):
    """Vista mínima para mostrar en el perfil del estudiante."""
    id:              int
    nombre_completo: str
    parentesco:      Parentesco
    celular:         str | None
    email:           str | None
    es_principal:    bool

    @classmethod
    def desde_acudiente(
        cls,
        acudiente: Acudiente,
        es_principal: bool = False,
    ) -> "AcudienteResumenDTO":
        if acudiente.id is None:
            raise ValueError("El acudiente no tiene id asignado.")
        return cls(
            id              = acudiente.id,
            nombre_completo = acudiente.nombre_completo,
            parentesco      = acudiente.parentesco,
            celular         = acudiente.celular,
            email           = acudiente.email,
            es_principal    = es_principal,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TipoDocumentoAcudiente",
    "Parentesco",
    "Acudiente",
    "EstudianteAcudiente",
    "NuevoAcudienteDTO",
    "ActualizarAcudienteDTO",
    "VincularAcudienteDTO",
    "AcudienteResumenDTO",
]