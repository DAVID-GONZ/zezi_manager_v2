"""
Tests unitarios para src/services/auditoria_helpers.py (obs_01 — T3).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.domain.models.auditoria import AccionCambio
from src.services.auditoria_helpers import auditar_cambio
from src.services.contexto_actor import limpiar_actor, usar_actor
from src.services.contexto_tenant import usar_institucion


def test_repo_none_no_lanza():
    """Con repo=None, auditar_cambio no debe lanzar ninguna excepción."""
    auditar_cambio(None, accion=AccionCambio.CREATE, tabla="t", nuevo={"x": 1})


def test_repo_mock_llama_registrar_cambio():
    """Con un repo mock, auditar_cambio llama a registrar_cambio con usuario_id del contexto."""
    repo = MagicMock()
    with usar_actor(5), usar_institucion(1):
        auditar_cambio(repo, accion=AccionCambio.CREATE, tabla="test", nuevo={"a": 1})
    repo.registrar_cambio.assert_called_once()
    cambio = repo.registrar_cambio.call_args[0][0]
    assert cambio.usuario_id == 5
    assert cambio.institucion_id == 1


def test_override_usuario_id_usa_override():
    """Con override explícito usuario_id=7, usa 7 (no el contexto)."""
    repo = MagicMock()
    with usar_actor(99):
        auditar_cambio(
            repo,
            accion=AccionCambio.UPDATE,
            tabla="test",
            anterior={"a": 0},
            nuevo={"a": 1},
            usuario_id=7,
        )
    cambio = repo.registrar_cambio.call_args[0][0]
    assert cambio.usuario_id == 7


def test_repo_que_lanza_no_propaga():
    """Si el repo lanza una excepción, auditar_cambio no la propaga (R8)."""
    repo = MagicMock()
    repo.registrar_cambio.side_effect = RuntimeError("DB error")
    # No debe lanzar
    limpiar_actor()
    auditar_cambio(repo, accion=AccionCambio.CREATE, tabla="t", nuevo={"x": 1})


def test_accion_delete_usa_anterior():
    """Para AccionCambio.DELETE, el campo anterior se pasa correctamente."""
    repo = MagicMock()
    with usar_actor(1), usar_institucion(2):
        auditar_cambio(
            repo,
            accion=AccionCambio.DELETE,
            tabla="tabla_x",
            registro_id=10,
            anterior={"campo": "viejo"},
        )
    cambio = repo.registrar_cambio.call_args[0][0]
    assert cambio.accion == AccionCambio.DELETE
    assert cambio.registro_id == 10
