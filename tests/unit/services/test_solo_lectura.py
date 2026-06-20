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

from src.services import solo_lectura
from src.services.solo_lectura import (
    OperacionSoloLecturaError,
    activar_solo_lectura,
    es_solo_lectura,
    requiere_escritura,
    verificar_escritura,
)
from src.domain.models.usuario import FiltroUsuariosDTO, NuevoUsuarioDTO
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
    from datetime import datetime
    from src.domain.models.auditoria import (
        EventoSesion, FiltroAuditoriaDTO, TipoEventoSesion,
    )
    from src.services.auditoria_service import AuditoriaService

    ahora = datetime.now()

    class FakeAuditoriaRepo:
        def listar_eventos(self, filtro: FiltroAuditoriaDTO):
            return [
                EventoSesion(usuario="x", usuario_id=1,
                             tipo_evento=TipoEventoSesion.LOGIN_EXITOSO, fecha_hora=ahora),
                EventoSesion(usuario="y", usuario_id=2,
                             tipo_evento=TipoEventoSesion.LOGIN_EXITOSO, fecha_hora=ahora),
                EventoSesion(usuario="x", usuario_id=1,
                             tipo_evento=TipoEventoSesion.LOGIN_EXITOSO, fecha_hora=ahora),
                EventoSesion(usuario="z", usuario_id=3,
                             tipo_evento=TipoEventoSesion.ACCESO_DENEGADO, fecha_hora=ahora),
            ]

    svc = AuditoriaService(repo=FakeAuditoriaRepo())
    uso = svc.resumen_uso(7)
    assert uso.sesiones_periodo == 3
    assert uso.usuarios_activos == 2   # ids 1 y 2 distintos
    assert uso.accesos_denegados == 1
    assert uso.logins_hoy == 3
