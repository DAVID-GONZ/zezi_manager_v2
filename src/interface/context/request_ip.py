"""request_ip.py — resolución única de la IP de la petición en curso.

Sustituye la función `_obtener_ip()` anidada en login.py (obs_06, D1).
Separa la parte pura (_de_request) — testeable con un doble de petición —
de la parte que depende del contexto de NiceGUI (ip_de_peticion).

Los tres caminos de fallo emiten logger.warning en vez de silenciar (R2).
"""
from __future__ import annotations

import logging

logger = logging.getLogger("INTERFACE.REQUEST_IP")


def _de_request(request) -> str | None:
    """
    Extrae la IP de un objeto request (función pura, sin efectos).

    Respeta X-Forwarded-For (primer salto) y cae a request.client.host.
    Separada para facilitar los tests sin servidor NiceGUI.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    cliente = getattr(request, "client", None)
    return getattr(cliente, "host", None)


def ip_de_peticion() -> str | None:
    """IP del cliente, o None si no hay petición resoluble (y lo advierte)."""
    request = None
    try:
        from nicegui import app as _app
        request = _app.storage.request
    except Exception:
        try:
            from nicegui import Client
            request = Client.current().request
        except Exception:
            request = None

    if request is None:
        logger.warning("IP no resuelta: no hay petición accesible en el contexto")
        return None
    try:
        ip = _de_request(request)
    except Exception as exc:
        logger.warning("IP no resuelta: %s", exc)
        return None
    if ip is None:
        logger.warning(
            "IP no resuelta: la petición no expone X-Forwarded-For ni client.host"
        )
    return ip


__all__ = ["_de_request", "ip_de_peticion"]
