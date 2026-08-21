"""
Modelo de dominio: Búsqueda Global
====================================

DTOs para el sistema de búsqueda cross-entidad con scoping por rol.

El servicio de búsqueda (BusquedaService) produce estos objetos;
la capa de interfaz los consume sin conocer los repos subyacentes.

Entidades searchables (en orden de prioridad):
  estudiante  — nombre, apellido, número de documento
  usuario     — nombre completo, username (solo admin/director)
  grupo       — código, nombre (filtrado en Python por volumen bajo)
  asignatura  — nombre, código (filtrado en Python; solo directivos)

Scoping:
  - admin       → cross-tenant (None = todas las instituciones), read-only
  - director    → su institución
  - coordinador → su institución (sin acceso a búsqueda de usuarios)
  - profesor    → su institución, restringido a sus grupos asignados
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class TipoResultadoBusqueda(StrEnum):
    ESTUDIANTE = "estudiante"
    USUARIO = "usuario"
    GRUPO = "grupo"
    ASIGNATURA = "asignatura"


class ResultadoBusquedaDTO(BaseModel):
    """Resultado individual de búsqueda, normalizado para cualquier entidad."""

    tipo: TipoResultadoBusqueda
    id: int
    titulo: str       # texto principal (nombre completo, código)
    subtitulo: str = ""   # contexto secundario (grupo, rol, área)
    icono: str = ""   # nombre de Material Symbol
    ruta: str = ""    # deep link URL para navegar al detalle


class ResultadosBusquedaDTO(BaseModel):
    """Agregado de resultados de búsqueda cross-entidad."""

    termino: str
    resultados: list[ResultadoBusquedaDTO] = []
    total_por_tipo: dict[str, int] = {}  # e.g. {"estudiante": 12, "grupo": 2}
    limitado: bool = False  # True si los resultados fueron truncados por límite
