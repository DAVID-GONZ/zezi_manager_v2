"""severidad_evento.py — clasificación de eventos de sesión (dominio puro).

Fuente única de la severidad de cada TipoEventoSesion. Vive en domain/policies/
junto a rbac_usuarios y login_throttle. Solo stdlib y modelos de dominio.

Regla de diseño (obs_07):
  ACCESO_DENEGADO se parte en dos clases:
  - ADVERTENCIA: denegación esperada por diseño (escritura en solo lectura,
    acceso a ruta sin rol suficiente). El sistema está funcionando.
  - CRITICA: denegación no esperada (acceso cross-tenant, motivo desconocido).
    Requiere atención.

  Falla hacia el lado seguro: cualquier motivo desconocido es CRITICA.
"""
from __future__ import annotations

from src.domain.models.auditoria import SeveridadEvento, TipoEventoSesion

# ── Constantes de motivo (código estable, no texto legible) ──────────────────

MOTIVO_SOLO_LECTURA = "solo_lectura"
"""Denegación de escritura durante modo solo lectura (Ver como)."""

MOTIVO_ROL = "rol_insuficiente"
"""Denegación por rol insuficiente para la ruta solicitada."""

MOTIVO_CROSS_TENANT = "cross_tenant"
"""Denegación por acceso a objeto de otra institución."""

# Motivos que representan comportamiento esperado del sistema.
_DENEGACION_ESPERADA = frozenset({MOTIVO_SOLO_LECTURA, MOTIVO_ROL})


def severidad_de(
    tipo_evento: TipoEventoSesion,
    motivo: str | None = None,
) -> SeveridadEvento:
    """
    Severidad canónica de un evento de sesión.

    Args:
        tipo_evento: El tipo de evento a clasificar.
        motivo:      Código estable del motivo (constantes MOTIVO_* de este módulo).
                     Relevante solo para ACCESO_DENEGADO.

    Returns:
        SeveridadEvento apropiada para el tipo y motivo dados.

    Falla hacia el lado seguro: un motivo desconocido en ACCESO_DENEGADO
    se clasifica como CRITICA (no como ADVERTENCIA).
    """
    if tipo_evento is TipoEventoSesion.ACCESO_DENEGADO:
        return (
            SeveridadEvento.ADVERTENCIA
            if motivo in _DENEGACION_ESPERADA
            else SeveridadEvento.CRITICA
        )
    if tipo_evento is TipoEventoSesion.LOGIN_FALLIDO:
        return SeveridadEvento.ADVERTENCIA
    return SeveridadEvento.INFO


__all__ = [
    "MOTIVO_CROSS_TENANT",
    "MOTIVO_ROL",
    "MOTIVO_SOLO_LECTURA",
    "severidad_de",
]
