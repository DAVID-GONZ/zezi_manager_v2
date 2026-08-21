"""
src/services/portal/convivencia_provider.py
============================================
PortalProvider para el módulo Convivencia (portal_38).
Fail-open: cualquier excepción retorna lista vacía, pero SIEMPRE se registra
en el log (M4) — un provider roto no puede ser invisible en producción.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from src.domain.portal_provider import PortalContext, SubItem

logger = logging.getLogger("PORTAL.CONVIVENCIA")


class ConvivenciaProvider:
    """Proveedor de mini-dashboard para el módulo de Convivencia."""

    def __init__(self, *, alerta_svc_provider: Callable):
        self._alerta_svc = alerta_svc_provider

    def recientes(self, ctx: PortalContext) -> list[SubItem]:
        # Atajo de navegación, no un conteo: `conteo` se queda en su default 1.
        return [
            SubItem(
                label="Observaciones",
                detalle="Ver registros del periodo",
                ruta_destino="/convivencia/observaciones",
                severidad="info",
            )
        ]

    def alertas(self, ctx: PortalContext) -> list[SubItem]:
        # TODO(multitenant): este conteo NO está acotado por institución y no
        # puede estarlo todavía. `AlertaService.contar_pendientes()` sólo admite
        # (estudiante_id, nivel) y `sqlite_alerta_repo.contar_pendientes` hace
        # `COUNT(*) FROM alertas` sin filtro de tenant porque la tabla `alertas`
        # no tiene columna `institucion_id`. Acotarlo exige migración de esquema
        # + parámetro nuevo en el puerto `alerta_repo`. No se simula el scope
        # aquí: deuda declarada, no deuda oculta.
        try:
            n = self._alerta_svc().contar_pendientes()
            if n > 0:
                plural = "s" if n > 1 else ""
                return [
                    SubItem(
                        label=f"{n} alerta{plural} pendiente{plural}",
                        detalle="Revisar en Seguimiento",
                        ruta_destino="/convivencia/alertas",
                        severidad="warning",
                        # El entero real viaja en el DTO; el resumen global lo
                        # suma sin tener que leer el texto del label.
                        conteo=n,
                    )
                ]
        except Exception:
            # `getattr` sólo aquí: el logger de la ruta degradada nunca debe
            # ser la causa de una segunda excepción.
            logger.warning(
                "ConvivenciaProvider.alertas degradó a lista vacía (institucion_id=%s)",
                getattr(ctx, "institucion_id", None),
                exc_info=True,
            )
        return []

    def hitos(self, ctx: PortalContext) -> list[SubItem]:
        # Hito informativo, no un conteo: `conteo` se queda en su default 1.
        return [
            SubItem(
                label="Reporte de periodo",
                detalle="Ver consolidado de convivencia",
                ruta_destino="/convivencia/reporte-periodo",
                severidad="info",
            )
        ]


__all__ = ["ConvivenciaProvider"]
