"""eventos_sesion.py — constructor único de EventoSesion desde la interfaz.

Concentra la construcción de EventoSesion en la capa de interfaz (obs_06, R6).
Garantiza que:
  - `usuario` siempre es el **username** (no nombre para mostrar, no ID, no "anon").
  - `ip_address` siempre se resuelve desde el contexto de petición actual.
  - `severidad` se deriva automáticamente de `severidad_de(tipo_evento, motivo)`
    (obs_07, T9). El llamador pasa el motivo; este módulo es el punto único
    de derivación de severidad para la capa de interfaz.

Los emisores de la capa de servicios (`solo_lectura.py`, `contexto_tenant.py`)
NO pueden importar este módulo (regla de capas). Ellos construyen `EventoSesion`
directamente usando `actor_username()` y `actor_ip()` del contexto neutral, y
llaman a `severidad_de(...)` directamente.

Regla AST (obs_06, T17): ningún archivo fuera de este módulo debe instanciar
`EventoSesion(...)` directamente desde la capa de interfaz.
"""
from __future__ import annotations

from src.domain.models.auditoria import EventoSesion, TipoEventoSesion
from src.domain.policies.severidad_evento import severidad_de
from src.interface.context.request_ip import ip_de_peticion


def construir_evento(
    *,
    usuario: str,
    usuario_id: int | None,
    tipo_evento: TipoEventoSesion,
    detalles: str | None = None,
    objetivo: str | None = None,
    motivo: str | None = None,
    institucion_id: int | None = None,
) -> EventoSesion:
    """
    Construye un EventoSesion con identidad completa desde el contexto actual.

    `usuario` es SIEMPRE el username (login), nunca el nombre para mostrar
    ni un entero ni el literal 'anon'. El llamador es responsable de pasar
    el username correcto.

    `ip_address` se resuelve automáticamente desde la petición en curso.
    Si no hay contexto de petición, ip_de_peticion() lo advierte y devuelve None.

    `severidad` se deriva internamente usando `severidad_de(tipo_evento, motivo)`.
    El llamador pasa el motivo (una constante MOTIVO_* de severidad_evento.py);
    no debe calcular la severidad externamente (obs_07, T9).
    """
    sev = severidad_de(tipo_evento, motivo)
    return EventoSesion(
        usuario=usuario,
        usuario_id=usuario_id,
        tipo_evento=tipo_evento,
        ip_address=ip_de_peticion(),
        detalles=detalles,
        objetivo=objetivo,
        severidad=sev,
        institucion_id=institucion_id,
    )


__all__ = ["construir_evento"]
