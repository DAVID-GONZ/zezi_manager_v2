"""
auditoria_helpers.py — helper único de auditoría de cambios.

Sustituye las 7 copias locales de _auditar en los servicios.
Resuelve actor e institución desde el contexto; acepta overrides explícitos.
Nunca propaga excepciones (R8).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.models.auditoria import AccionCambio, RegistroCambio

if TYPE_CHECKING:
    from src.domain.ports.auditoria_repo import IAuditoriaRepository

logger = logging.getLogger(__name__)


def auditar_cambio(
    repo: IAuditoriaRepository | None,
    *,
    accion: AccionCambio,
    tabla: str,
    registro_id: int | None = None,
    anterior: dict | None = None,
    nuevo: dict | None = None,
    usuario_id: int | None = None,
    institucion_id: int | None = None,
) -> None:
    """
    Registra un cambio en audit_log.

    Si `usuario_id` o `institucion_id` no se pasan, los resuelve desde
    el contexto activo (actor_actual() / institucion_actual()).
    Nunca propaga excepciones — log.warning si falla (R8).
    """
    if repo is None:
        return
    try:
        from src.services.contexto_actor import actor_actual
        from src.services.contexto_tenant import institucion_actual

        uid = usuario_id if usuario_id is not None else actor_actual()
        iid = institucion_id if institucion_id is not None else institucion_actual()

        if accion == AccionCambio.CREATE:
            cambio = RegistroCambio.para_creacion(tabla, nuevo or {}, registro_id, uid, iid)
        elif accion == AccionCambio.DELETE:
            cambio = RegistroCambio.para_eliminacion(tabla, anterior or {}, registro_id, uid, iid)
        else:
            cambio = RegistroCambio.para_actualizacion(
                tabla, anterior or {}, nuevo or {}, registro_id, uid, iid
            )
        repo.registrar_cambio(cambio)
    except Exception as exc:
        logger.warning("No se pudo registrar auditoria de %s: %s", tabla, exc)
