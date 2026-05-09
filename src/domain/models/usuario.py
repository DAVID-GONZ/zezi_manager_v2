"""
Modelo de dominio: Usuario
===========================

Contiene:
  Enums    — Rol
  Entidad  — Usuario
  Read models — DocenteInfoDTO, AsignacionDocenteInfoDTO
  DTOs     — NuevoUsuarioDTO, ActualizarUsuarioDTO,
              UsuarioResumenDTO, FiltroUsuariosDTO

Reglas de negocio:
  - `usuario` (username) no puede estar vacío ni contener espacios.
    Una vez creado, no se modifica — es el identificador de inicio de sesión.
  - `nombre_completo` debe tener al menos 3 caracteres después de normalizar.
  - `email` debe tener formato mínimo válido (contiene '@' con dominio).
  - Soft delete: los usuarios no se eliminan, se desactivan (activo=False).
  - El hash de contraseña es responsabilidad exclusiva del servicio de auth
    (IAuthenticationService). El modelo nunca recibe ni genera contraseñas.
  - Un usuario con rol 'profesor' puede tener carga académica (asignaciones).
    Un 'admin' o 'director' no tiene asignaciones en el modelo educativo.

Separación de responsabilidades:
  - Usuario          → entidad persistida (lo que va a la BD)
  - DocenteInfoDTO   → read model para el grid de docentes (con estadísticas)
  - UsuarioResumenDTO → read model para selects y lookups
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class Rol(str, Enum):
    ADMIN        = "admin"
    DIRECTOR     = "director"
    COORDINADOR  = "coordinador"
    PROFESOR     = "profesor"
    ESTUDIANTE   = "estudiante"   # acceso de consulta futuro
    APODERADO    = "apoderado"    # portal de acudientes (v3.0)


# =============================================================================
# Entidad principal
# =============================================================================

class Usuario(BaseModel):
    """
    Entidad que representa a cualquier usuario del sistema.

    La password_hash nunca se incluye en este modelo.
    El servicio de autenticación la maneja de forma independiente.

    Roles y sus usos habituales:
      admin        → acceso total, gestión del sistema
      director     → configuración académica, cierre de periodos
      coordinador  → seguimiento disciplinario y académico
      profesor     → notas, asistencia, observaciones de sus grupos
      estudiante   → consulta (v3.0)
      apoderado    → portal de acudientes (v3.0)
    """
    id:              int | None     = None
    usuario:         str            # username — inmutable tras creación
    nombre_completo: str
    email:           str | None     = None
    telefono:        str | None     = None
    rol:             Rol            = Rol.PROFESOR
    activo:          bool           = True
    fecha_creacion:  date           = Field(default_factory=date.today)
    ultima_sesion:   datetime | None = None

    # ------------------------------------------------------------------
    # Validadores de campo
    # ------------------------------------------------------------------

    @field_validator("usuario", mode="before")
    @classmethod
    def validar_usuario(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de usuario no puede estar vacío.")
        if " " in v:
            raise ValueError(
                f"El nombre de usuario no puede contener espacios: '{v}'."
            )
        if len(v) < 3:
            raise ValueError(
                f"El nombre de usuario debe tener al menos 3 caracteres (tiene {len(v)})."
            )
        if len(v) > 50:
            raise ValueError(
                f"El nombre de usuario no puede exceder 50 caracteres (tiene {len(v)})."
            )
        return v.lower()

    @field_validator("nombre_completo", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 3:
            raise ValueError(
                f"El nombre completo debe tener al menos 3 caracteres "
                f"(tiene {len(v)}: '{v}')."
            )
        if len(v) > 150:
            raise ValueError(
                f"El nombre no puede exceder 150 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("email", mode="before")
    @classmethod
    def validar_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip().lower()
        if not v:
            return None
        if "@" not in v:
            raise ValueError(f"El email debe contener '@': '{v}'.")
        partes = v.split("@")
        if len(partes) != 2 or not partes[0] or "." not in partes[1]:
            raise ValueError(
                f"El email no tiene un formato válido: '{v}'."
            )
        return v

    @field_validator("telefono", mode="before")
    @classmethod
    def limpiar_telefono(cls, v: str | None) -> str | None:
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
    def es_docente(self) -> bool:
        return self.rol == Rol.PROFESOR

    @property
    def es_directivo(self) -> bool:
        return self.rol in (Rol.ADMIN, Rol.DIRECTOR, Rol.COORDINADOR)

    @property
    def puede_gestionar_evaluaciones(self) -> bool:
        """Puede registrar notas y asistencia."""
        return self.rol in (Rol.PROFESOR, Rol.DIRECTOR,
                            Rol.COORDINADOR, Rol.ADMIN)

    @property
    def nombre_display(self) -> str:
        """Nombre para mostrar en la UI: 'Carlos López (c.lopez)'"""
        return f"{self.nombre_completo} ({self.usuario})"

    # ------------------------------------------------------------------
    # Transiciones de estado
    # ------------------------------------------------------------------

    def desactivar(self) -> "Usuario":
        """Retorna una copia con activo=False (soft delete)."""
        if not self.activo:
            raise ValueError(
                f"El usuario '{self.usuario}' ya está desactivado."
            )
        return self.model_copy(update={"activo": False})

    def reactivar(self) -> "Usuario":
        """Retorna una copia con activo=True."""
        if self.activo:
            raise ValueError(
                f"El usuario '{self.usuario}' ya está activo."
            )
        return self.model_copy(update={"activo": True})

    def registrar_sesion(self, momento: datetime | None = None) -> "Usuario":
        """Retorna una copia con ultima_sesion actualizada."""
        return self.model_copy(
            update={"ultima_sesion": momento or datetime.now()}
        )


# =============================================================================
# Read models — producidos por JOINs, no persistidos
# =============================================================================

class DocenteInfoDTO(BaseModel):
    """
    Vista estadística de un docente para el grid principal de profesores.

    Producida por la query de `obtener_listado_profesores()` que hace
    JOIN con horarios y asignaciones para calcular la carga académica.
    """
    id:                    int
    usuario:               str
    nombre_completo:       str
    email:                 str | None
    telefono:              str | None
    activo:                bool
    fecha_creacion:        date | None
    ultima_sesion:         datetime | None
    total_asignaciones:    int = 0
    grupos_asignados:      int = 0
    asignaturas_asignadas: int = 0
    horas_totales:         int = 0
    bloques_horarios:      int = 0

    @property
    def tiene_carga(self) -> bool:
        return self.total_asignaciones > 0

    @property
    def resumen_carga(self) -> str:
        """'3 grupos · 5 materias · 18 hrs/sem'"""
        if not self.tiene_carga:
            return "Sin carga asignada"
        return (
            f"{self.grupos_asignados} grupos · "
            f"{self.asignaturas_asignadas} materias · "
            f"{self.horas_totales} hrs/sem"
        )


class AsignacionDocenteInfoDTO(BaseModel):
    """
    Detalle de una asignación de un docente específico.

    Producida por `obtener_asignaciones_profesor()` con JOIN entre
    asignaciones, grupos, asignaturas y periodos.
    Incluye el comparativo entre horas teóricas y horas programadas.
    """
    id:                int
    grupo_id:          int
    grupo_codigo:      str
    grupo_nombre:      str | None
    asignatura_id:     int
    asignatura_nombre: str
    asignatura_codigo: str | None
    horas_teoricas:    int         = 0
    horas_programadas: int         = 0
    periodo_id:        int
    periodo_nombre:    str
    activo:            bool        = True

    @property
    def horas_pendientes(self) -> int:
        """Horas teóricas sin bloque horario asignado."""
        return max(0, self.horas_teoricas - self.horas_programadas)

    @property
    def horario_completo(self) -> bool:
        """True si todas las horas teóricas tienen bloque horario."""
        return self.horas_programadas >= self.horas_teoricas

    @property
    def display(self) -> str:
        """'601 — Matemáticas (P1)'"""
        return f"{self.grupo_codigo} — {self.asignatura_nombre} ({self.periodo_nombre})"


# =============================================================================
# DTOs
# =============================================================================

class NuevoUsuarioDTO(BaseModel):
    """
    Datos para crear un usuario nuevo.

    La contraseña se gestiona por separado en el servicio de autenticación.
    Si no se provee, el servicio usa el username como contraseña inicial.
    """
    usuario:         str
    nombre_completo: str
    rol:             Rol             = Rol.PROFESOR
    email:           str | None      = None
    telefono:        str | None      = None
    password:        str | None      = None  # gestionada por IAuthenticationService

    @field_validator("usuario", mode="before")
    @classmethod
    def validar_usuario(cls, v: str) -> str:
        v = str(v).strip()
        if not v or " " in v or len(v) < 3:
            raise ValueError(
                "El nombre de usuario debe tener mínimo 3 caracteres y sin espacios."
            )
        return v.lower()

    @field_validator("nombre_completo", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 3:
            raise ValueError(
                f"El nombre completo debe tener al menos 3 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("email", mode="before")
    @classmethod
    def validar_email(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = str(v).strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError(f"El email no tiene un formato válido: '{v}'.")
        return v

    def to_usuario(self) -> Usuario:
        return Usuario(**self.model_dump(exclude={"password"}))


class ActualizarUsuarioDTO(BaseModel):
    """
    Campos actualizables de un usuario. Todos opcionales.
    El username y el rol no se actualizan aquí.
    """
    nombre_completo: str | None  = None
    email:           str | None  = None
    telefono:        str | None  = None

    @field_validator("nombre_completo", mode="before")
    @classmethod
    def validar_nombre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if len(v) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres.")
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

    def aplicar_a(self, usuario: Usuario) -> Usuario:
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return usuario.model_copy(update=cambios) if cambios else usuario


class UsuarioResumenDTO(BaseModel):
    """Vista mínima para selects, lookups y referencias en otros módulos."""
    id:              int
    usuario:         str
    nombre_completo: str
    rol:             Rol
    activo:          bool

    @classmethod
    def desde_usuario(cls, u: Usuario) -> "UsuarioResumenDTO":
        if u.id is None:
            raise ValueError("No se puede crear un resumen de un usuario sin id.")
        return cls(
            id=u.id,
            usuario=u.usuario,
            nombre_completo=u.nombre_completo,
            rol=u.rol,
            activo=u.activo,
        )


class FiltroUsuariosDTO(BaseModel):
    """Parámetros para listar usuarios."""
    rol:           Rol | None   = None
    solo_activos:  bool         = True
    busqueda:      str | None   = None   # nombre o username
    pagina:        int          = Field(default=1, ge=1)
    por_pagina:    int          = Field(default=50, ge=1, le=200)

    @field_validator("busqueda", mode="before")
    @classmethod
    def limpiar_busqueda(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Rol",
    "Usuario",
    "DocenteInfoDTO",
    "AsignacionDocenteInfoDTO",
    "NuevoUsuarioDTO",
    "ActualizarUsuarioDTO",
    "UsuarioResumenDTO",
    "FiltroUsuariosDTO",
]