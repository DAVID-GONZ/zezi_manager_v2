"""Tests de LogNotificationService — registro en memoria de notificaciones."""
from __future__ import annotations

from src.infrastructure.notifications import LogNotificationService


def test_log_service_registra_notificaciones():
    svc = LogNotificationService()
    svc.notificar_acudiente(1, "Citación", "Su hijo fue citado")
    svc.notificar_docente(2, "Alerta", "Estudiante en riesgo")
    assert svc.conteo() == 2
    assert svc.conteo("acudiente") == 1
    assert svc.conteo("docente") == 1


def test_log_service_limpiar():
    svc = LogNotificationService()
    svc.notificar_directivos("Cierre", "Periodo 1 cerrado")
    svc.limpiar()
    assert svc.conteo() == 0
