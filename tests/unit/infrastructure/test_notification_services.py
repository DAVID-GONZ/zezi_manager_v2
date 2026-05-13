"""Tests unitarios para NullNotificationService y LogNotificationService."""
from __future__ import annotations

import logging

import pytest

from src.infrastructure.notifications.null_notification_service import NullNotificationService
from src.infrastructure.notifications.log_notification_service import LogNotificationService
from src.domain.ports.service_ports import INotificationService


# ===========================================================================
# NullNotificationService
# ===========================================================================

class TestNullNotificationService:
    def test_implementa_el_port(self):
        assert isinstance(NullNotificationService(), INotificationService)

    def test_notificar_acudiente_retorna_true(self):
        svc = NullNotificationService()
        assert svc.notificar_acudiente(1, "Asunto", "Cuerpo") is True

    def test_notificar_docente_retorna_true(self):
        svc = NullNotificationService()
        assert svc.notificar_docente(2, "Asunto", "Cuerpo") is True

    def test_notificar_directivos_retorna_int(self):
        svc = NullNotificationService()
        resultado = svc.notificar_directivos("Asunto", "Cuerpo")
        assert isinstance(resultado, int)

    def test_notificar_acudiente_registra_en_log(self, caplog):
        svc = NullNotificationService()
        with caplog.at_level(logging.INFO, logger="NOTIFICATION.NULL"):
            svc.notificar_acudiente(7, "Asunto test", "msg")
        assert "acudiente" in caplog.text
        assert "7" in caplog.text

    def test_notificar_docente_registra_en_log(self, caplog):
        svc = NullNotificationService()
        with caplog.at_level(logging.INFO, logger="NOTIFICATION.NULL"):
            svc.notificar_docente(3, "Aviso", "msg")
        assert "docente" in caplog.text
        assert "3" in caplog.text

    def test_notificar_directivos_registra_en_log(self, caplog):
        svc = NullNotificationService()
        with caplog.at_level(logging.INFO, logger="NOTIFICATION.NULL"):
            svc.notificar_directivos("Circular", "msg")
        assert "directivos" in caplog.text


# ===========================================================================
# LogNotificationService
# ===========================================================================

class TestLogNotificationService:
    def test_implementa_el_port(self):
        assert isinstance(LogNotificationService(), INotificationService)

    def test_es_subclase_de_null(self):
        assert issubclass(LogNotificationService, NullNotificationService)

    def test_lista_enviadas_comienza_vacia(self):
        svc = LogNotificationService()
        assert svc.enviadas == []

    # --- notificar_acudiente ---

    def test_acudiente_se_registra_en_enviadas(self):
        svc = LogNotificationService()
        svc.notificar_acudiente(5, "Asunto", "Cuerpo")
        assert len(svc.enviadas) == 1
        entrada = svc.enviadas[0]
        assert entrada["tipo"] == "acudiente"
        assert entrada["destinatario"] == 5
        assert entrada["asunto"] == "Asunto"
        assert entrada["mensaje"] == "Cuerpo"

    def test_acudiente_retorna_true(self):
        svc = LogNotificationService()
        assert svc.notificar_acudiente(1, "a", "b") is True

    # --- notificar_docente ---

    def test_docente_se_registra_en_enviadas(self):
        svc = LogNotificationService()
        svc.notificar_docente(9, "Reunión", "Detalle")
        assert svc.enviadas[0]["tipo"] == "docente"
        assert svc.enviadas[0]["destinatario"] == 9

    def test_docente_retorna_true(self):
        svc = LogNotificationService()
        assert svc.notificar_docente(1, "a", "b") is True

    # --- notificar_directivos ---

    def test_directivos_se_registra_en_enviadas(self):
        svc = LogNotificationService()
        svc.notificar_directivos("Informe", "Detalle")
        assert svc.enviadas[0]["tipo"] == "directivos"
        assert svc.enviadas[0]["destinatario"] is None

    def test_directivos_retorna_int_positivo(self):
        svc = LogNotificationService()
        assert svc.notificar_directivos("a", "b") >= 1

    # --- acumulación y conteo ---

    def test_acumula_multiples_notificaciones(self):
        svc = LogNotificationService()
        svc.notificar_acudiente(1, "a", "b")
        svc.notificar_acudiente(2, "a", "b")
        svc.notificar_docente(3, "a", "b")
        assert len(svc.enviadas) == 3

    def test_conteo_sin_filtro(self):
        svc = LogNotificationService()
        svc.notificar_acudiente(1, "a", "b")
        svc.notificar_docente(2, "a", "b")
        svc.notificar_directivos("a", "b")
        assert svc.conteo() == 3

    def test_conteo_por_tipo(self):
        svc = LogNotificationService()
        svc.notificar_acudiente(1, "a", "b")
        svc.notificar_acudiente(2, "a", "b")
        svc.notificar_docente(3, "a", "b")
        assert svc.conteo("acudiente") == 2
        assert svc.conteo("docente") == 1
        assert svc.conteo("directivos") == 0

    def test_limpiar_vacia_enviadas(self):
        svc = LogNotificationService()
        svc.notificar_acudiente(1, "a", "b")
        svc.limpiar()
        assert svc.enviadas == []
        assert svc.conteo() == 0

    def test_limpiar_permite_reusar_instancia(self):
        svc = LogNotificationService()
        svc.notificar_docente(1, "a", "b")
        svc.limpiar()
        svc.notificar_docente(2, "x", "y")
        assert svc.conteo() == 1
        assert svc.enviadas[0]["destinatario"] == 2
