"""
src/services/portal/evaluacion_provider.py
==========================================
PortalProvider para el módulo Evaluación (portal_38).
Fail-open: cualquier excepción retorna lista vacía, pero SIEMPRE se registra
en el log (M4) — un provider roto no puede ser invisible en producción.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from src.domain.portal_provider import PortalContext, SubItem

logger = logging.getLogger("PORTAL.EVALUACION")


class EvaluacionProvider:
    """Proveedor de mini-dashboard para el módulo de Evaluación."""

    def __init__(self, *, habilitacion_svc_provider: Callable):
        self._hab_svc = habilitacion_svc_provider

    def recientes(self, ctx: PortalContext) -> list[SubItem]:
        # Atajo de navegación, no un conteo: `conteo` se queda en su default 1.
        return [
            SubItem(
                label="Planilla de notas",
                detalle="Ver calificaciones del periodo",
                ruta_destino="/evaluacion/planilla",
                severidad="info",
            )
        ]

    def alertas(self, ctx: PortalContext) -> list[SubItem]:
        # `periodo_id` es el ÚNICO scope que la API subyacente soporta hoy:
        # `HabilitacionService.contar_habilitaciones_pendientes(periodo_id=None)`
        # cuenta todos los periodos, así que un contexto sin periodo activo
        # conserva exactamente el comportamiento anterior.
        #
        # TODO(multitenant): sin acotación por institución.
        # `FiltroHabilitacionesDTO` no expone `institucion_id` y el repo de
        # habilitaciones no filtra por tenant; acotarlo exige migración de
        # esquema + campo nuevo en el DTO de filtro. Fuera de alcance aquí.
        try:
            periodo_id = ctx.periodo_id
            n = self._hab_svc().contar_habilitaciones_pendientes(periodo_id=periodo_id)
            if n > 0:
                plural = "s" if n > 1 else ""
                return [
                    SubItem(
                        label=f"{n} habilitación{plural} pendiente{plural}",
                        detalle="Gestionar habilitaciones",
                        ruta_destino="/evaluacion/habilitaciones",
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
                "EvaluacionProvider.alertas degradó a lista vacía "
                "(institucion_id=%s, periodo_id=%s)",
                getattr(ctx, "institucion_id", None),
                getattr(ctx, "periodo_id", None),
                exc_info=True,
            )
        return []

    def hitos(self, ctx: PortalContext) -> list[SubItem]:
        # Hito informativo, no un conteo: `conteo` se queda en su default 1.
        return [
            SubItem(
                label="Cierre de periodo",
                detalle="Gestionar cierre académico",
                ruta_destino="/evaluacion/cierre-periodo",
                severidad="info",
            )
        ]


__all__ = ["EvaluacionProvider"]
