"""
src/services/portal_resumen_service.py
=======================================
Agrega el resumen global del portal (portal_37) a partir de los
`PortalProvider` registrados (portal_38).

A5: este servicio NO reimplementa el conteo de ningún módulo. Itera los
providers y consume su punto de extensión (`alertas()`), de modo que un
módulo nuevo aparece en el resumen y en el badge de notificaciones con sólo
registrarse en `container.py`.

Fail-open POR PROVIDER: si uno revienta se registra en log y se salta ese
provider; el resto del resumen se conserva. Sólo un fallo al obtener la
propia lista de providers degrada a resumen vacío.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from src.domain.portal_provider import PortalContext, PortalProvider, SubItem

logger = logging.getLogger("PORTAL.RESUMEN")

# Severidades de SubItem cuyo `conteo` suma al badge de notificaciones.
_SEVERIDADES_NOTIFICABLES = frozenset({"warning", "error"})

# SubItem admite "success"; LineaResumenDTO no. Se degrada a "info".
_MAPA_SEVERIDAD = {"success": "info"}


@dataclass
class LineaResumenDTO:
    texto: str
    ruta_destino: str
    severidad: str  # "info" | "warning" | "error"

    def model_dump(self) -> dict:
        return asdict(self)


@dataclass
class ResumenGlobalDTO:
    lineas: list[LineaResumenDTO] = field(default_factory=list)
    total_notificaciones: int = 0

    def model_dump(self) -> dict:
        return {
            "lineas": [linea.model_dump() for linea in self.lineas],
            "total_notificaciones": self.total_notificaciones,
        }


def _a_linea(item: SubItem) -> LineaResumenDTO:
    """Mapea un `SubItem` de módulo a una línea del resumen global.

    Mapeo (documentado porque los DTO no son isomorfos):
      - `texto`         ← `"{label} — {detalle}"`; si `detalle` viene vacío,
                          sólo `label`. El label ya trae el dato accionable
                          ("3 alertas pendientes") y el detalle la acción
                          ("Revisar en Seguimiento"), así que concatenarlos
                          produce una frase legible sin perder información.
      - `ruta_destino`  ← idéntico (es el contrato de navegación del portal).
      - `severidad`     ← idéntica, salvo "success" → "info", porque
                          LineaResumenDTO sólo admite info/warning/error.
    """
    detalle = (item.detalle or "").strip()
    texto = f"{item.label} — {detalle}" if detalle else item.label
    return LineaResumenDTO(
        texto=texto,
        ruta_destino=item.ruta_destino,
        severidad=_MAPA_SEVERIDAD.get(item.severidad, item.severidad),
    )


class PortalResumenService:
    """Calcula el resumen global del portal para un contexto de sesión."""

    def __init__(self, *, providers_provider: Callable[[], list[PortalProvider]]):
        self._providers_provider = providers_provider

    def resumen_global(self, ctx: PortalContext) -> ResumenGlobalDTO:
        """Agrega las alertas de todos los `PortalProvider` registrados.

        SEMÁNTICA DEL BADGE — sin regresión: `total_notificaciones` sigue
        contando REGISTROS, no líneas. Suma `SubItem.conteo` de los sub-ítems
        accionables (severidad "warning" o "error"), de modo que 3 alertas de
        convivencia + 2 habilitaciones ⇒ badge 5, igual que antes de portal_38
        y ahora además incluyendo Evaluación.

        El entero llega por el DTO (`SubItem.conteo`), que cada provider
        rellena con el número que ya tenía a mano. Ni este servicio ni el DTO
        inspeccionan `label` ni `detalle` para deducir cantidades: el punto de
        extensión sigue siendo genérico y nadie parsea texto.

        Los ítems informativos (`info`/`success`) aparecen como línea pero no
        suman al badge, con independencia de su `conteo`.
        """
        try:
            providers = list(self._providers_provider())
        except Exception:
            logger.exception("No se pudo obtener la lista de PortalProvider; resumen vacío.")
            return ResumenGlobalDTO()

        lineas: list[LineaResumenDTO] = []
        total = 0

        for provider in providers:
            try:
                items = provider.alertas(ctx)
            except Exception:
                # Fail-open POR PROVIDER: un módulo roto no tumba el resumen.
                logger.warning(
                    "PortalProvider %s falló en alertas(); se omite del resumen.",
                    type(provider).__name__,
                    exc_info=True,
                )
                continue
            for item in items or []:
                lineas.append(_a_linea(item))
                if item.severidad in _SEVERIDADES_NOTIFICABLES:
                    total += item.conteo

        return ResumenGlobalDTO(lineas=lineas, total_notificaciones=total)


__all__ = ["LineaResumenDTO", "PortalResumenService", "ResumenGlobalDTO"]
