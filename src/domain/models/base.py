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

from pydantic import BaseModel, ConfigDict


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


__all__ = [
    "DTODominio",
    "EntidadDominio",
    "ZeciModel",
]
