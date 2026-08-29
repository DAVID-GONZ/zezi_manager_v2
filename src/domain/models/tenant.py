"""
Modelo de dominio: TenantScope
================================
Tipo centinela para el scope de institución en métodos de repositorio.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

TenantScope: TypeAlias = int | Literal["*"]
"""
Scope de tenant obligatorio en métodos de repositorio.

- int  → filtra por esa institucion_id (WHERE institucion_id = ?)
- "*"  → cross-tenant explícito (admin). NO aplica filtro.

Omitir el parámetro es un TypeError — fail fast.
"""

__all__ = ["TenantScope"]
