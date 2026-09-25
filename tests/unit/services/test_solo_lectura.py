"""
Tests del mecanismo central de solo lectura (paso_21 — "Ver como").

Cubre:
  - Primitivas del módulo solo_lectura (activar / consultar / verificar).
  - Que un método de MUTACIÓN representativo (usuario_service.crear_usuario)
    lanza OperacionSoloLecturaError cuando el flag está activo, y funciona
    normal cuando está apagado (default).
  - Que un método de LECTURA (listar_filtrado) NO se bloquea.
  - Que el default es False (los tests existentes no cambian de comportamiento).
"""
from __future__ import annotations

import pytest

from src.domain.models.usuario import FiltroUsuariosDTO, NuevoUsuarioDTO
from src.services.solo_lectura import (
    OperacionSoloLecturaError,
    activar_solo_lectura,
    es_solo_lectura,
    requiere_escritura,
    verificar_escritura,
)
from src.services.usuario_service import UsuarioService
from tests.unit.services.test_usuario_service import FakeUsuarioRepo


@pytest.fixture(autouse=True)
def _reset_flag():
    """Garantiza que cada test arranca y termina con el flag apagado."""
    activar_solo_lectura(False)
    yield
    activar_solo_lectura(False)


# ── Primitivas del módulo ───────────────────────────────────────────────────

def test_default_es_false():
    assert es_solo_lectura() is False


def test_activar_y_consultar():
    activar_solo_lectura(True)
    assert es_solo_lectura() is True
    activar_solo_lectura(False)
    assert es_solo_lectura() is False


def test_verificar_escritura_no_lanza_en_modo_normal():
    verificar_escritura()  # no debe lanzar


def test_verificar_escritura_lanza_en_solo_lectura():
    activar_solo_lectura(True)
    with pytest.raises(OperacionSoloLecturaError):
        verificar_escritura()


def test_es_subclase_de_permission_error():
    assert issubclass(OperacionSoloLecturaError, PermissionError)


def test_decorador_requiere_escritura():
    @requiere_escritura
    def _mutar():
        return "ok"

    assert _mutar() == "ok"
    activar_solo_lectura(True)
    with pytest.raises(OperacionSoloLecturaError):
        _mutar()


# ── Guard central aplicado a un servicio real ───────────────────────────────

def _build_service() -> UsuarioService:
    return UsuarioService(repo=FakeUsuarioRepo())


def test_crear_usuario_funciona_en_modo_normal():
    svc = _build_service()
    dto = NuevoUsuarioDTO(usuario="c.lopez", nombre_completo="Carlos López", rol="profesor")
    usuario = svc.crear_usuario(dto)
    assert usuario.id is not None
    assert usuario.usuario == "c.lopez"


def test_crear_usuario_bloqueado_en_solo_lectura():
    svc = _build_service()
    activar_solo_lectura(True)
    dto = NuevoUsuarioDTO(usuario="a.gomez", nombre_completo="Ana Gómez", rol="profesor")
    with pytest.raises(OperacionSoloLecturaError):
        svc.crear_usuario(dto)


def test_lectura_no_se_bloquea_en_solo_lectura():
    svc = _build_service()
    activar_solo_lectura(True)
    # Las lecturas NO llevan el guard: deben funcionar siempre.
    resultado = svc.listar_filtrado(FiltroUsuariosDTO())
    assert resultado == []


# ── Agregaciones de solo lectura del dashboard admin (paso_21) ──────────────

def test_resumen_por_rol_cuenta_y_activos():
    from src.domain.models.usuario import UsuarioResumenDTO

    repo = FakeUsuarioRepo()

    def _resumenes(filtro):
        return [
            UsuarioResumenDTO(id=1, usuario="a", nombre_completo="A", rol="director", activo=True),
            UsuarioResumenDTO(id=2, usuario="b", nombre_completo="B", rol="profesor", activo=True),
            UsuarioResumenDTO(id=3, usuario="c", nombre_completo="C", rol="profesor", activo=False),
        ]

    repo.listar_resumenes = _resumenes  # type: ignore[assignment]
    svc = UsuarioService(repo=repo)
    resumen = svc.resumen_por_rol()
    assert resumen.total == 3
    assert resumen.activos == 2
    assert resumen.por_rol["profesor"] == 2
    assert resumen.directores == 1


def test_resumen_uso_agrega_logins_y_denegados():
    """
    obs_08 T9 (actualización de obs_07 T13):
    resumen_uso ahora delega en `resumen_eventos` (SQL) en vez de iterar sobre
    `listar_eventos` (R4). El contrato del resultado es el mismo: solo
    ACCESO_DENEGADO con severidad CRITICA cuenta en `accesos_denegados`.
    """
    from src.services.auditoria_service import AuditoriaService

    class FakeAuditoriaRepo:
        """Fake que implementa resumen_eventos con los mismos datos del test anterior."""

        def resumen_eventos(self, desde, hasta=None, institucion_id="*") -> dict:
            # Simula: 3 LOGIN_EXITOSO (ids 1, 2, 1), 1 ACCESO_DENEGADO CRITICA,
            # 1 ACCESO_DENEGADO ADVERTENCIA (no debe contar).
            return {
                "por_tipo": {
                    "LOGIN_EXITOSO": 3,
                    "ACCESO_DENEGADO": 2,
                },
                "logins_hoy": 3,          # todos los logins son de hoy
                "usuarios_distintos": 2,  # ids 1 y 2 distintos
                "denegados_criticos": 1,  # solo la CRITICA
            }

    svc = AuditoriaService(repo=FakeAuditoriaRepo())
    uso = svc.resumen_uso(7)
    assert uso.sesiones_periodo == 3
    assert uso.usuarios_activos == 2   # ids 1 y 2 distintos
    assert uso.accesos_denegados == 1  # solo la CRITICA
    assert uso.logins_hoy == 3


# ── T14: Test de regresión R8 (obs_07) ─────────────────────────────────────


def test_denegacion_escritura_con_actor_activo_lleva_usuario_id_y_severidad_advertencia():
    """
    R8: con actor activo en el contexto, una denegación de escritura lleva
    usuario_id no nulo y severidad=ADVERTENCIA.
    """
    from datetime import datetime
    from unittest.mock import MagicMock

    from src.domain.models.auditoria import EventoSesion, SeveridadEvento, TipoEventoSesion
    from src.services.contexto_actor import usar_actor
    from src.services.solo_lectura import activar_solo_lectura, verificar_escritura

    capturado: list[EventoSesion] = []

    fake_service = MagicMock()
    fake_service.registrar_evento.side_effect = capturado.append

    fake_container = MagicMock()
    fake_container.auditoria_service.return_value = fake_service

    import container as _container_module
    original = getattr(_container_module, "Container", None)
    try:
        _container_module.Container = fake_container
        activar_solo_lectura(True)
        with usar_actor(42, "admin_real", "10.0.0.1"):
            try:
                verificar_escritura()
            except Exception:
                pass
    finally:
        activar_solo_lectura(False)
        if original is not None:
            _container_module.Container = original

    assert len(capturado) == 1, "Se esperaba exactamente un evento capturado"
    ev = capturado[0]
    assert ev.usuario_id == 42, "usuario_id debe ser el actor activo"
    assert ev.severidad is SeveridadEvento.ADVERTENCIA, "solo_lectura → ADVERTENCIA"
    assert ev.tipo_evento is TipoEventoSesion.ACCESO_DENEGADO


def test_denegacion_cross_tenant_con_actor_activo_lleva_usuario_id_y_severidad_critica():
    """
    R8: con actor activo en el contexto, una denegación cross-tenant lleva
    usuario_id no nulo y severidad=CRITICA.
    """
    from unittest.mock import MagicMock

    from src.domain.models.auditoria import EventoSesion, SeveridadEvento, TipoEventoSesion
    from src.services.contexto_actor import usar_actor
    from src.services.contexto_tenant import usar_institucion, verificar_pertenencia

    capturado: list[EventoSesion] = []

    fake_service = MagicMock()
    fake_service.registrar_evento.side_effect = capturado.append

    fake_container = MagicMock()
    fake_container.auditoria_service.return_value = fake_service

    import container as _container_module
    original = getattr(_container_module, "Container", None)
    try:
        _container_module.Container = fake_container
        with usar_actor(7, "director1", "192.168.1.1"):
            with usar_institucion(1):  # scope = institución 1
                try:
                    verificar_pertenencia(2)  # objeto de institución 2 → DENEGADO
                except Exception:
                    pass
    finally:
        if original is not None:
            _container_module.Container = original

    assert len(capturado) == 1, "Se esperaba exactamente un evento capturado"
    ev = capturado[0]
    assert ev.usuario_id == 7, "usuario_id debe ser el actor activo"
    assert ev.severidad is SeveridadEvento.CRITICA, "cross_tenant → CRITICA"
    assert ev.tipo_evento is TipoEventoSesion.ACCESO_DENEGADO
