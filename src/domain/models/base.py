"""
Base común de modelos de dominio — ZECI Manager v2.0
======================================================

Define las tres clases raíz de las que derivan todos los modelos:

  ZeciModel       — base común: from_attributes, str_strip_whitespace,
                    validate_assignment.

  EntidadDominio  — + extra="ignore": tolera columnas SELECT * que el
                    modelo aún no declara (institucion_id añadido por
                    backend_07, marcas de tiempo, columnas futuras).
                    Diseño D1/D2 de datos_02_model_config_base.

  DTODominio      — + extra="forbid": rechaza campos no declarados de
                    la API. Activa la detección de construcciones con
                    campos fantasma (R19).

Opciones deliberadamente ausentes:
  - use_enum_values=True: rompería las 123 propiedades que comparan
    miembros por identidad (R16).
  - frozen=True: hay 5 asignaciones post-construcción sobre DTOs de
    resultado en los servicios; se congela en un paso propio.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class ZeciModel(BaseModel):
    """Base común a todos los modelos de dominio de ZECI Manager."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class EntidadDominio(ZeciModel):
    """
    Base para modelos que representan una fila de tabla.

    extra="ignore" — explícito y justificado (R10): los repositorios usan
    SELECT * y algunas tablas incluyen columnas que este modelo aún no
    representa (ej. institucion_id antes de backend_07_repos_migracion).
    Cuando esas consultas se migren a columnas nombradas, esta opción
    podrá endurecerse a "forbid" en un paso propio.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="ignore",
    )


class DTODominio(ZeciModel):
    """
    Base para modelos de transporte de datos entre capas.

    extra="forbid" — rechaza campos no declarados (R7, R8, R19).
    Si un test o un llamador pasa un campo que el DTO no declara,
    Pydantic lanza ValidationError identificando el campo sobrante.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )


# =============================================================================
# Tipos de texto con cota de longitud (datos_07_restricciones_str)
#
# Fuente única de verdad para las cotas semánticas de los campos de texto.
# Cambiar el max_length aquí propaga la cota a todos los campos que usan el tipo.
# Ver design.md §1 (R4, R5).
# =============================================================================

DocumentoStr = Annotated[str, StringConstraints(max_length=30)]
"""Números de documento (TI, CC, CE, NUIP, PASAPORTE). max=30 con margen doble."""

GrupoCodigoStr = Annotated[str, StringConstraints(max_length=20)]
"""Códigos de grupo escolar (601, A1, 1101-B, …). max=20."""

TelefonoStr = Annotated[str, StringConstraints(max_length=20)]
"""Teléfono/celular con prefijo internacional y separadores. max=20."""

EtiquetaStr = Annotated[str, StringConstraints(max_length=50)]
"""Etiquetas de pantalla cortas (nombre nivel desempeño, sala, etiqueta franja). max=50."""

CodigoStr = Annotated[str, StringConstraints(max_length=50)]
"""Identificadores cortos de sistema (username, código externo, NIT, código área). max=50."""

DaneStr = Annotated[str, StringConstraints(min_length=12, max_length=12)]
"""Código DANE: longitud fija exacta de 12 dígitos (estándar externo). min=max=12."""

PasswordStr = Annotated[str, StringConstraints(max_length=128)]
"""Campos que transportan contraseñas — política vigente max=128 (R20)."""

NombrePropioStr = Annotated[str, StringConstraints(max_length=100)]
"""Nombres de persona (nombre/apellido individuales), nombres cortos de entidades. max=100."""

NombreAreaStr = Annotated[str, StringConstraints(max_length=120)]
"""Nombres de área de conocimiento (Ley 115; max real ~80 chars colombianos). max=120."""

NombrePersonaStr = Annotated[str, StringConstraints(max_length=150)]
"""Nombre completo de persona natural (nombre_completo). max=150."""

NombreInstStr = Annotated[str, StringConstraints(max_length=200)]
"""Nombres de institución educativa, nombres oficiales, referencias a resoluciones. max=200."""

DireccionStr = Annotated[str, StringConstraints(max_length=200)]
"""Direcciones físicas (calle + número + complemento). max=200."""

EmailStr = Annotated[str, StringConstraints(max_length=254)]
"""Correo electrónico — máximo RFC 5321 para una dirección enrutable (R16). max=254."""

TextoCortStr = Annotated[str, StringConstraints(max_length=500)]
"""Descripciones cortas, enunciados de logros, descripciones de escenario. max=500."""

RutaLocalStr = Annotated[str, StringConstraints(max_length=500)]
"""Rutas del sistema de archivos local (R21). max=500."""

TextoMedioStr = Annotated[str, StringConstraints(max_length=1000)]
"""Descripciones de registros de comportamiento, protocolos breves. max=1000."""

TextoLargoStr = Annotated[str, StringConstraints(max_length=2000)]
"""Textos narrativos libres (observaciones de periodo, seguimientos, plantillas). max=2000."""

UrlStr = Annotated[str, StringConstraints(max_length=2048)]
"""URLs de recursos remotos (logo_url); límite práctico de cliente HTTP (R21). max=2048."""


__all__ = [
    "CodigoStr",
    "DaneStr",
    "DireccionStr",
    "DTODominio",
    "DocumentoStr",
    "EmailStr",
    "EntidadDominio",
    "EtiquetaStr",
    "GrupoCodigoStr",
    "NombreAreaStr",
    "NombreInstStr",
    "NombrePersonaStr",
    "NombrePropioStr",
    "PasswordStr",
    "RutaLocalStr",
    "TelefonoStr",
    "TextoCortStr",
    "TextoLargoStr",
    "TextoMedioStr",
    "UrlStr",
    "ZeciModel",
]
