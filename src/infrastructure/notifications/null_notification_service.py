"""
NullNotificationService — implementación placeholder de INotificationService.
"""
from __future__ import annotations

import logging

from src.domain.ports.service_ports import INotificationService


class NullNotificationService(INotificationService):
    """
    Implementación placeholder para v2.0.
    No envía nada — solo registra en el log que debería enviar.
    En v3.0 se reemplaza por EmailNotificationService o
    SMSNotificationService sin cambiar ningún servicio.
    """

    def __init__(self) -> None:
        self._log = logging.getLogger("NOTIFICATION.NULL")

    def notificar_acudiente(self, acudiente_id: int, asunto: str, cuerpo: str) -> bool:
        self._log.info("NOTIFICACIÓN PENDIENTE → acudiente %s: %s", acudiente_id, asunto)
        return True

    def notificar_docente(self, usuario_id: int, asunto: str, cuerpo: str) -> bool:
        self._log.info("NOTIFICACIÓN PENDIENTE → docente %s: %s", usuario_id, asunto)
        return True

    def notificar_directivos(self, asunto: str, cuerpo: str) -> int:
        self._log.info("NOTIFICACIÓN PENDIENTE → directivos: %s", asunto)
        return 0


__all__ = ["NullNotificationService"]
