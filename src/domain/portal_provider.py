"""
src/domain/portal_provider.py
==============================
Protocolo PortalProvider, contexto PortalContext y DTO SubItem — portal_38.
El dominio no importa de services, interface, infrastructure ni src.db.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SubItem:
    """Ítem de sub-sección del mini-dashboard."""

    label: str
    detalle: str
    ruta_destino: str
    severidad: str  # "info" | "warning" | "error" | "success"
    # Cuántos registros representa este ítem. El provider lo rellena con el
    # entero que YA tiene a mano (p. ej. las 3 alertas pendientes que contó),
    # de modo que el resumen global pueda sumar registros sin parsear `label`.
    # Default 1: un ítem que no representa un conteo (un hito, un aviso suelto)
    # vale por sí mismo, y ningún constructor existente se rompe.
    conteo: int = 1

    def model_dump(self) -> dict:
        return {
            "label": self.label,
            "detalle": self.detalle,
            "ruta_destino": self.ruta_destino,
            "severidad": self.severidad,
            "conteo": self.conteo,
        }


@runtime_checkable
class PortalContext(Protocol):
    """Contexto mínimo que los PortalProvider necesitan leer.

    Protocolo ESTRUCTURAL a propósito (A6): el objeto real que viaja en
    runtime es `SessionContext` (capa interfaz). El dominio no puede
    importarlo sin invertir la dirección de dependencias, así que declara
    aquí sólo los campos que los providers consumen. `SessionContext` es un
    dataclass que ya los expone, de modo que lo satisface sin heredar ni
    importar nada.

    Sólo se declaran los campos realmente usados hoy:
      - `institucion_id`: scope multi-tenant (None = admin cross-tenant).
      - `periodo_id`: periodo académico activo, usado por Evaluación.
    Añadir un campo aquí obliga a que todo contexto que se pase lo tenga:
    no ampliar "por si acaso".
    """

    institucion_id: int | None
    periodo_id: int | None


@runtime_checkable
class PortalProvider(Protocol):
    """Proveedor de datos para el mini-dashboard de un módulo.

    Cada método devuelve lista de SubItem. Debe ser fail-open:
    cualquier excepción interna retorna lista vacía (y se registra en log,
    nunca se silencia sin traza).
    """

    def recientes(self, ctx: PortalContext) -> list[SubItem]: ...
    def alertas(self, ctx: PortalContext) -> list[SubItem]: ...
    def hitos(self, ctx: PortalContext) -> list[SubItem]: ...


__all__ = ["PortalContext", "PortalProvider", "SubItem"]
