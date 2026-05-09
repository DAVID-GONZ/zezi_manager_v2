"""
Modelo de dominio: Asignación
==============================

La asignación es el pivot central del sistema: conecta un docente
con una asignatura, un grupo y un periodo. Toda la evaluación,
la asistencia y las observaciones están ligadas a una asignación.

Contiene:
  Entidades — Asignacion, AsignacionInfo
  DTOs      — NuevaAsignacionDTO, FiltroAsignacionesDTO

Dos modelos distintos por una razón concreta:
  Asignacion      — el objeto que se persiste. Solo IDs, sin nombres.
                    Lo que el repositorio guarda y actualiza.
  AsignacionInfo  — el objeto que se muestra. Incluye nombres de grupo,
                    asignatura y docente obtenidos por JOIN.
                    Lo que las páginas y los informes consumen.

Reglas de negocio:
  - Todos los IDs de FK deben ser enteros positivos.
  - activo=False es un soft-delete: la asignación existe en historia
    pero no acepta nuevos registros de evaluación ni asistencia.
  - La unicidad (grupo, asignatura, docente, periodo) la garantiza la BD
    con UNIQUE constraint; el servicio la verifica antes de insertar.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Self


# =============================================================================
# Entidad de escritura — lo que persiste
# =============================================================================

class Asignacion(BaseModel):
    """
    Pivot docente-asignatura-grupo-periodo.

    Cada asignación genera su propio conjunto de categorías, actividades
    y notas. Una asignación inactiva (activo=False) no acepta nuevos datos
    pero mantiene el histórico intacto.
    """
    id:            int | None = None
    grupo_id:      int
    asignatura_id: int
    usuario_id:    int        # docente
    periodo_id:    int
    activo:        bool       = True

    @field_validator("grupo_id", "asignatura_id", "usuario_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser un entero positivo (recibido: {v}).")
        return v

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def esta_activa(self) -> bool:
        return self.activo

    # ------------------------------------------------------------------
    # Métodos de dominio
    # ------------------------------------------------------------------

    def desactivar(self) -> "Asignacion":
        """Retorna una copia con activo=False (soft-delete)."""
        if not self.activo:
            raise ValueError("La asignación ya está inactiva.")
        return self.model_copy(update={"activo": False})

    def reactivar(self) -> "Asignacion":
        """Retorna una copia con activo=True."""
        if self.activo:
            raise ValueError("La asignación ya está activa.")
        return self.model_copy(update={"activo": True})


# =============================================================================
# Modelo de lectura — lo que muestran las páginas e informes
# =============================================================================

class AsignacionInfo(BaseModel):
    """
    Vista enriquecida de una asignación con nombres resueltos por JOIN.

    Este modelo no se persiste: lo construye el repositorio a partir
    de una consulta que hace JOIN con grupos, asignaturas y usuarios.
    Las páginas nunca deben recibir una Asignacion desnuda y hacer
    sus propias queries para obtener los nombres.

    Uso típico en un servicio:
        info = asignacion_repo.get_info(asignacion_id)
        # info.display_completo → "601 — Matemáticas | Carlos López (P1)"
    """
    asignacion_id:     int
    grupo_id:          int
    grupo_codigo:      str
    asignatura_id:     int
    asignatura_nombre: str
    usuario_id:        int
    docente_nombre:    str
    periodo_id:        int
    periodo_nombre:    str
    periodo_numero:    int
    activo:            bool

    @field_validator("grupo_codigo", "asignatura_nombre", "docente_nombre",
                     "periodo_nombre", mode="before")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El campo no puede estar vacío.")
        return v

    # ------------------------------------------------------------------
    # Propiedades de display
    # ------------------------------------------------------------------

    @property
    def display_completo(self) -> str:
        """
        Representación larga para encabezados de planillas e informes:
        '601 — Matemáticas | Carlos López García (Período 1)'
        """
        return (
            f"{self.grupo_codigo} — {self.asignatura_nombre} | "
            f"{self.docente_nombre} ({self.periodo_nombre})"
        )

    @property
    def display_corto(self) -> str:
        """
        Representación corta para selectores y chips de UI:
        '601 · Matemáticas · P1'
        """
        return f"{self.grupo_codigo} · {self.asignatura_nombre} · P{self.periodo_numero}"

    @property
    def display_docente_materia(self) -> str:
        """Para listas de asignaciones de un docente: 'Matemáticas — 601'"""
        return f"{self.asignatura_nombre} — {self.grupo_codigo}"


# =============================================================================
# DTOs
# =============================================================================

class NuevaAsignacionDTO(BaseModel):
    """Datos necesarios para crear una asignación."""
    grupo_id:      int
    asignatura_id: int
    usuario_id:    int
    periodo_id:    int

    @field_validator("grupo_id", "asignatura_id", "usuario_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser un entero positivo (recibido: {v}).")
        return v

    def to_asignacion(self) -> Asignacion:
        return Asignacion(**self.model_dump())


class FiltroAsignacionesDTO(BaseModel):
    """Parámetros para listar asignaciones."""
    usuario_id:    int | None = None   # filtrar por docente
    grupo_id:      int | None = None
    asignatura_id: int | None = None
    periodo_id:    int | None = None
    solo_activas:  bool       = True
    pagina:        int        = Field(default=1, ge=1)
    por_pagina:    int        = Field(default=100, ge=1, le=500)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Asignacion",
    "AsignacionInfo",
    "NuevaAsignacionDTO",
    "FiltroAsignacionesDTO",
]