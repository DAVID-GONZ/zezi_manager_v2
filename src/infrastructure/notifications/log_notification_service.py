"""
LogNotificationService — NullNotificationService con memoria de notificaciones.
Útil en tests para verificar que los servicios generan las notificaciones correctas.
"""
from __future__ import annotations

from .null_notification_service import NullNotificationService


class LogNotificationService(NullNotificationService):
    """
    Extiende NullNotificationService almacenando cada notificación en memoria.
    Permite inspeccionar en tests cuántas y qué notificaciones se generaron.
    """

    def __init__(self) -> None:
        super().__init__()
        self.enviadas: list[dict] = []

    def notificar_acudiente(self, acudiente_id: int, asunto: str, cuerpo: str) -> bool:
        self.enviadas.append({
            "tipo": "acudiente",
            "destinatario": acudiente_id,
            "asunto": asunto,
            "mensaje": cuerpo,
        })
        return super().notificar_acudiente(acudiente_id, asunto, cuerpo)

    def notificar_docente(self, usuario_id: int, asunto: str, cuerpo: str) -> bool:
        self.enviadas.append({
            "tipo": "docente",
            "destinatario": usuario_id,
            "asunto": asunto,
            "mensaje": cuerpo,
        })
        return super().notificar_docente(usuario_id, asunto, cuerpo)

    def notificar_directivos(self, asunto: str, cuerpo: str) -> int:
        self.enviadas.append({
            "tipo": "directivos",
            "destinatario": None,
            "asunto": asunto,
            "mensaje": cuerpo,
        })
        super().notificar_directivos(asunto, cuerpo)
        return 1  # simula un envío exitoso al grupo de directivos

    def limpiar(self) -> None:
        self.enviadas.clear()

    def conteo(self, tipo: str | None = None) -> int:
        if tipo is None:
            return len(self.enviadas)
        return sum(1 for n in self.enviadas if n["tipo"] == tipo)


__all__ = ["LogNotificationService"]
