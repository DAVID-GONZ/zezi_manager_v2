"""
Modelo de dominio: Estudiante
==============================

Contiene:
  Enums         — TipoDocumento, Genero, EstadoMatricula
  Entidad       — Estudiante
  DTOs          — NuevoEstudianteDTO, ActualizarEstudianteDTO,
                  FiltroEstudiantesDTO, EstudianteResumenDTO

Reglas de negocio encapsuladas en este módulo:
  - El número de documento no puede estar vacío ni contener caracteres no alfanuméricos.
  - Nombre y apellido se normalizan a title-case al construir el objeto.
  - La fecha de nacimiento no puede ser futura ni implicar una edad > 25 años
    (rango razonable para educación básica y media).
  - TI (Tarjeta de Identidad) es para menores. Si el documento es CC y la
    fecha de nacimiento indica menos de 17 años, se alerta como inconsistencia.
  - El estado activo/inactivo se consulta a través de propiedades, nunca
    comparando strings directamente en el código cliente.

Dependencias:
  Solo librería estándar de Python + Pydantic.
  Sin imports de SQLite, pandas, NiceGUI ni ninguna capa de infraestructura.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class TipoDocumento(str, Enum):
    TI      = "TI"       # Tarjeta de Identidad (menores)
    CC      = "CC"       # Cédula de Ciudadanía (adultos)
    CE      = "CE"       # Cédula de Extranjería
    NUIP    = "NUIP"     # Número Único de Identificación Personal (nuevo sistema)


class Genero(str, Enum):
    M       = "M"
    F       = "F"
    OTRO    = "OTRO"


class EstadoMatricula(str, Enum):
    ACTIVO      = "activo"
    INACTIVO    = "inactivo"
    RETIRADO    = "retirado"
    GRADUADO    = "graduado"


# =============================================================================
# Entidad principal
# =============================================================================

class Estudiante(BaseModel):
    """
    Entidad de dominio que representa a un estudiante matriculado.

    Invariantes garantizadas al construir el objeto:
      - numero_documento es alfanumérico, sin espacios.
      - nombre y apellido están normalizados a title-case y no están vacíos.
      - fecha_nacimiento, si existe, no es futura ni implica edad > 25 años.
      - La combinación (tipo_documento=CC, edad<17) genera un ValueError
        porque es probable que sea un error de carga de datos.

    Uso típico desde un repositorio:
        row = fetch_one("SELECT * FROM estudiantes WHERE id = ?", (est_id,))
        estudiante = Estudiante(**row)   # Pydantic valida en construcción

    Uso típico desde un servicio:
        dto = NuevoEstudianteDTO(
            numero_documento="1098765432",
            nombre="Ana",
            apellido="García",
        )
        estudiante = Estudiante(**dto.model_dump())
        repo.guardar(estudiante)
    """

    # Campos de identidad
    id:                 int | None          = None
    id_publico:         str | None          = None
    tipo_documento:     TipoDocumento       = TipoDocumento.TI
    numero_documento:   str

    # Datos personales
    nombre:             str
    apellido:           str
    genero:             Genero | None       = None
    fecha_nacimiento:   date | None         = None
    direccion:          str | None          = None

    # Contexto académico
    grupo_id:           int | None          = None
    posee_piar:         bool                = False
    fecha_ingreso:      date                = Field(default_factory=date.today)
    estado_matricula:   EstadoMatricula     = EstadoMatricula.ACTIVO

    # ------------------------------------------------------------------
    # Validadores de campo individual
    # ------------------------------------------------------------------

    @field_validator("numero_documento", mode="before")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El número de documento no puede estar vacío.")
        if not v.replace("-", "").replace(" ", "").isalnum():
            raise ValueError(
                f"El número de documento '{v}' contiene caracteres inválidos. "
                "Solo se permiten letras, números y guiones."
            )
        return v.upper()

    @field_validator("nombre", "apellido", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El valor no puede estar vacío.")
        if len(v) > 100:
            raise ValueError(f"No puede exceder 100 caracteres (tiene {len(v)}).")
        # Normalización: "ANA SOFÍA" → "Ana Sofía", "garcia" → "Garcia"
        return v.title()

    @field_validator("fecha_nacimiento", mode="before")
    @classmethod
    def validar_fecha_nacimiento(cls, v: date | str | None) -> date | None:
        if v is None:
            return None
        if isinstance(v, str):
            try:
                v = date.fromisoformat(v)
            except ValueError:
                raise ValueError(
                    f"Formato de fecha inválido: '{v}'. Use YYYY-MM-DD."
                )
        hoy = date.today()
        if v >= hoy:
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        edad = (hoy - v).days // 365
        if edad > 25:
            raise ValueError(
                f"La fecha indica {edad} años (máximo permitido: 25). "
                "Verifique que la fecha de nacimiento corresponde a un estudiante "
                "de educación básica o media."
            )
        return v

    @field_validator("id_publico", mode="before")
    @classmethod
    def validar_id_publico(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip().upper()
        if not v:
            return None
        return v

    # ------------------------------------------------------------------
    # Validador de modelo — reglas que cruzan varios campos
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validar_coherencia_documento_edad(self) -> Self:
        """
        Detecta inconsistencias entre tipo de documento y edad.

        En Colombia:
          TI → Tarjeta de Identidad, emitida a menores de edad (7-17 años).
          CC → Cédula de Ciudadanía, para mayores de 18 años.

        Un estudiante de 14 años con CC es probablemente un error de digitación.
        Un estudiante de 20 años con TI podría ser válido (extraedad), pero
        se alerta para que el operador confirme.
        """
        if self.fecha_nacimiento is None:
            return self

        edad = (date.today() - self.fecha_nacimiento).days // 365

        if self.tipo_documento == TipoDocumento.CC and edad < 17:
            raise ValueError(
                f"Inconsistencia: tipo de documento CC con {edad} años. "
                "La CC es para mayores de 18 años. "
                "Si el estudiante tiene TI use ese tipo de documento."
            )

        if self.tipo_documento == TipoDocumento.TI and edad >= 19:
            raise ValueError(
                f"Inconsistencia: tipo de documento TI con {edad} años. "
                "La TI es para menores. Verifique si debe usar CC o NUIP."
            )

        return self

    # ------------------------------------------------------------------
    # Propiedades computadas — lógica de negocio sin persistencia
    # ------------------------------------------------------------------

    @property
    def nombre_completo(self) -> str:
        """Nombre completo para mostrar: 'Ana Sofía García Pérez'."""
        return f"{self.nombre} {self.apellido}"

    @property
    def edad(self) -> int | None:
        """Edad en años completos. None si no hay fecha de nacimiento."""
        if self.fecha_nacimiento is None:
            return None
        return (date.today() - self.fecha_nacimiento).days // 365

    @property
    def es_activo(self) -> bool:
        """True si el estudiante está matriculado activamente."""
        return self.estado_matricula == EstadoMatricula.ACTIVO

    @property
    def puede_recibir_calificaciones(self) -> bool:
        """
        Un estudiante puede recibir calificaciones si está activo o reactivado.
        Los retirados y graduados no deben aparecer en las planillas.
        """
        return self.estado_matricula in (
            EstadoMatricula.ACTIVO,
            EstadoMatricula.INACTIVO,   # inactivo temporal (permiso, enfermedad)
        )

    @property
    def requiere_atencion_diferencial(self) -> bool:
        """True si el estudiante tiene PIAR activo."""
        return self.posee_piar

    @property
    def documento_display(self) -> str:
        """Cadena formateada para mostrar en UI: 'TI 1098765432'."""
        return f"{self.tipo_documento.value} {self.numero_documento}"

    # ------------------------------------------------------------------
    # Método de transición de estado
    # ------------------------------------------------------------------

    def retirar(self, motivo: str | None = None) -> "Estudiante":
        """
        Retorna una nueva instancia con estado RETIRADO.
        No modifica el objeto actual (inmutabilidad funcional).
        El motivo se registra en historial_estudiantes, no en el modelo.
        """
        if not self.es_activo:
            raise ValueError(
                f"No se puede retirar a '{self.nombre_completo}': "
                f"su estado actual es '{self.estado_matricula.value}'."
            )
        return self.model_copy(
            update={"estado_matricula": EstadoMatricula.RETIRADO}
        )

    def reactivar(self) -> "Estudiante":
        """Retorna una nueva instancia con estado ACTIVO."""
        if self.estado_matricula != EstadoMatricula.RETIRADO:
            raise ValueError(
                f"Solo se puede reactivar un estudiante RETIRADO. "
                f"Estado actual: '{self.estado_matricula.value}'."
            )
        return self.model_copy(
            update={"estado_matricula": EstadoMatricula.ACTIVO}
        )

    def asignar_grupo(self, grupo_id: int) -> "Estudiante":
        """Retorna una nueva instancia con el grupo actualizado."""
        if grupo_id <= 0:
            raise ValueError("grupo_id debe ser un entero positivo.")
        return self.model_copy(update={"grupo_id": grupo_id})


# =============================================================================
# DTOs — objetos de transferencia de datos
# =============================================================================

class NuevoEstudianteDTO(BaseModel):
    """
    Datos necesarios para matricular un estudiante nuevo.

    Solo incluye los campos que el operador debe proveer.
    Los campos opcionales se inicializan con valores por defecto en Estudiante.
    """
    tipo_documento:   TipoDocumento     = TipoDocumento.TI
    numero_documento: str
    nombre:           str
    apellido:         str
    genero:           Genero | None     = None
    fecha_nacimiento: date | None       = None
    grupo_id:         int | None        = None
    posee_piar:       bool              = False
    direccion:        str | None        = None

    # Los mismos validadores de Estudiante aplican aquí
    @field_validator("numero_documento", mode="before")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El número de documento no puede estar vacío.")
        return v.upper()

    @field_validator("nombre", "apellido", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El valor no puede estar vacío.")
        if len(v) > 100:
            raise ValueError(f"No puede exceder 100 caracteres.")
        return v.title()

    def to_estudiante(self) -> Estudiante:
        """Construye el Estudiante completo desde este DTO."""
        return Estudiante(**self.model_dump())


class ActualizarEstudianteDTO(BaseModel):
    """
    Campos actualizables de un estudiante existente.

    Todos son opcionales: solo se actualiza lo que se provee.
    El número de documento no es actualizable (es el identificador principal).
    """
    nombre:           str | None        = None
    apellido:         str | None        = None
    genero:           Genero | None     = None
    fecha_nacimiento: date | None       = None
    grupo_id:         int | None        = None
    posee_piar:       bool | None       = None
    direccion:        str | None        = None
    estado_matricula: EstadoMatricula | None = None

    @field_validator("nombre", "apellido", mode="before")
    @classmethod
    def validar_nombre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if not v:
            raise ValueError("El valor no puede estar vacío.")
        if len(v) > 100:
            raise ValueError("No puede exceder 100 caracteres.")
        return v.title()

    def aplicar_a(self, estudiante: Estudiante) -> Estudiante:
        """
        Retorna una copia del estudiante con los campos del DTO aplicados.
        Ignora los campos que son None (no se actualizan).
        """
        cambios = {
            k: v for k, v in self.model_dump().items()
            if v is not None
        }
        if not cambios:
            return estudiante
        return estudiante.model_copy(update=cambios)


class FiltroEstudiantesDTO(BaseModel):
    """
    Parámetros de filtrado para listar estudiantes.
    Consumido por IEstudianteRepository.listar_filtrado().
    """
    grupo_id:         int | None                = None
    estado_matricula: EstadoMatricula | None    = None
    posee_piar:       bool | None               = None
    busqueda:         str | None                = None   # nombre, apellido o documento
    pagina:           int                       = Field(default=1, ge=1)
    por_pagina:       int                       = Field(default=50, ge=1, le=200)

    @field_validator("busqueda", mode="before")
    @classmethod
    def limpiar_busqueda(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class EstudianteResumenDTO(BaseModel):
    """
    Vista reducida de un estudiante para listados y selects.
    No incluye campos de auditoría ni direcciones.
    """
    id:               int
    id_publico:       str | None
    documento_display: str
    nombre_completo:  str
    genero:           Genero | None
    grupo_id:         int | None
    estado_matricula: EstadoMatricula
    posee_piar:       bool

    @classmethod
    def desde_estudiante(cls, est: Estudiante) -> "EstudianteResumenDTO":
        if est.id is None:
            raise ValueError("No se puede crear un resumen de un estudiante sin id.")
        return cls(
            id               = est.id,
            id_publico       = est.id_publico,
            documento_display= est.documento_display,
            nombre_completo  = est.nombre_completo,
            genero           = est.genero,
            grupo_id         = est.grupo_id,
            estado_matricula = est.estado_matricula,
            posee_piar       = est.posee_piar,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "TipoDocumento",
    "Genero",
    "EstadoMatricula",
    # Entidad
    "Estudiante",
    # DTOs
    "NuevoEstudianteDTO",
    "ActualizarEstudianteDTO",
    "FiltroEstudiantesDTO",
    "EstudianteResumenDTO",
]