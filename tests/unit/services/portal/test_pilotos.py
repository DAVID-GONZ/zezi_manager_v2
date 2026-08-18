"""
test_pilotos.py — portal_38: pilotos Convivencia y Evaluación.

R7: los ruta_destino emitidos deben estar registrados en el guard.
M8: los fakes usan firmas EXPLÍCITAS (nada de `**kwargs`) y registran los
argumentos recibidos, para que una regresión de propagación de `ctx` falle.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.domain.portal_provider import PortalContext, SubItem

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def rutas_registradas():
    """Pobla el registro de rutas para verificar ruta_destino (R7)."""
    import main
    main.registrar_rutas_ui()
    from src.interface.auth import roles_de_ruta
    return roles_de_ruta


# ── Contexto fake ─────────────────────────────────────────────────────────────

@dataclass
class FakeCtx:
    """Réplica estructural mínima de SessionContext (capa interfaz)."""

    institucion_id: int | None = None
    periodo_id: int | None = None


# ── Fake services (firmas explícitas: sin **kwargs) ───────────────────────────

class FakeAlertaSvc:
    def __init__(self, count: int = 0):
        self._count = count
        self.llamadas: list[tuple] = []

    def contar_pendientes(self, estudiante_id=None, nivel=None) -> int:
        self.llamadas.append((estudiante_id, nivel))
        return self._count


class FakeHabilitacionSvc:
    def __init__(self, count: int = 0):
        self._count = count
        self.periodos_recibidos: list[int | None] = []

    def contar_habilitaciones_pendientes(self, periodo_id: int | None = None) -> int:
        self.periodos_recibidos.append(periodo_id)
        return self._count


# ── Helpers ───────────────────────────────────────────────────────────────────

def _all_rutas(provider, ctx: PortalContext) -> list[str]:
    rutas = []
    for item in provider.recientes(ctx):
        rutas.append(item.ruta_destino)
    for item in provider.alertas(ctx):
        rutas.append(item.ruta_destino)
    for item in provider.hitos(ctx):
        rutas.append(item.ruta_destino)
    return rutas


# ── ConvivenciaProvider ───────────────────────────────────────────────────────

def test_convivencia_recientes_retorna_subitem():
    from src.services.portal.convivencia_provider import ConvivenciaProvider
    p = ConvivenciaProvider(alerta_svc_provider=lambda: FakeAlertaSvc(0))
    items = p.recientes(FakeCtx())
    assert all(isinstance(i, SubItem) for i in items)


def test_convivencia_alertas_con_pendientes():
    from src.services.portal.convivencia_provider import ConvivenciaProvider
    p = ConvivenciaProvider(alerta_svc_provider=lambda: FakeAlertaSvc(3))
    items = p.alertas(FakeCtx(institucion_id=1))
    assert len(items) == 1
    assert "3" in items[0].label
    assert items[0].severidad == "warning"
    # El entero real viaja en el DTO, no sólo en el texto del label.
    assert items[0].conteo == 3


def test_convivencia_alertas_sin_pendientes():
    from src.services.portal.convivencia_provider import ConvivenciaProvider
    p = ConvivenciaProvider(alerta_svc_provider=lambda: FakeAlertaSvc(0))
    items = p.alertas(FakeCtx())
    assert items == []


def test_convivencia_fail_open_y_deja_traza(caplog):
    from src.services.portal.convivencia_provider import ConvivenciaProvider

    def boom():
        raise RuntimeError("BD")

    p = ConvivenciaProvider(alerta_svc_provider=boom)
    with caplog.at_level("WARNING", logger="PORTAL.CONVIVENCIA"):
        assert p.alertas(FakeCtx(institucion_id=9)) == []
    # M4: fail-open sí, silencioso no.
    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_convivencia_rutas_registradas(rutas_registradas):
    from src.services.portal.convivencia_provider import ConvivenciaProvider
    p = ConvivenciaProvider(alerta_svc_provider=lambda: FakeAlertaSvc(2))
    for ruta in _all_rutas(p, FakeCtx()):
        assert rutas_registradas(ruta) is not None, f"Ruta muerta: {ruta}"


# ── EvaluacionProvider ────────────────────────────────────────────────────────

def test_evaluacion_recientes_retorna_subitem():
    from src.services.portal.evaluacion_provider import EvaluacionProvider
    p = EvaluacionProvider(habilitacion_svc_provider=lambda: FakeHabilitacionSvc(0))
    items = p.recientes(FakeCtx())
    assert all(isinstance(i, SubItem) for i in items)


def test_evaluacion_alertas_con_habilitaciones():
    from src.services.portal.evaluacion_provider import EvaluacionProvider
    p = EvaluacionProvider(habilitacion_svc_provider=lambda: FakeHabilitacionSvc(2))
    items = p.alertas(FakeCtx(periodo_id=5))
    assert len(items) == 1
    assert items[0].severidad == "warning"
    # El entero real viaja en el DTO, no sólo en el texto del label.
    assert items[0].conteo == 2


def test_items_informativos_conservan_conteo_por_defecto():
    """Recientes e hitos no representan conteos: quedan en 1."""
    from src.services.portal.convivencia_provider import ConvivenciaProvider
    from src.services.portal.evaluacion_provider import EvaluacionProvider
    conv = ConvivenciaProvider(alerta_svc_provider=lambda: FakeAlertaSvc(0))
    eva = EvaluacionProvider(habilitacion_svc_provider=lambda: FakeHabilitacionSvc(0))
    ctx = FakeCtx()
    for provider in (conv, eva):
        for item in [*provider.recientes(ctx), *provider.hitos(ctx)]:
            assert item.conteo == 1


def test_evaluacion_propaga_periodo_del_ctx():
    """A6: el ctx debe LEERSE, no sólo viajar. Falla si vuelve a ser inerte."""
    from src.services.portal.evaluacion_provider import EvaluacionProvider
    fake = FakeHabilitacionSvc(1)
    p = EvaluacionProvider(habilitacion_svc_provider=lambda: fake)
    p.alertas(FakeCtx(institucion_id=3, periodo_id=42))
    assert fake.periodos_recibidos == [42]


def test_evaluacion_sin_periodo_conserva_conteo_global():
    from src.services.portal.evaluacion_provider import EvaluacionProvider
    fake = FakeHabilitacionSvc(4)
    p = EvaluacionProvider(habilitacion_svc_provider=lambda: fake)
    items = p.alertas(FakeCtx(periodo_id=None))
    assert fake.periodos_recibidos == [None]
    assert len(items) == 1


def test_evaluacion_fail_open_y_deja_traza(caplog):
    from src.services.portal.evaluacion_provider import EvaluacionProvider

    def boom():
        raise RuntimeError("BD")

    p = EvaluacionProvider(habilitacion_svc_provider=boom)
    with caplog.at_level("WARNING", logger="PORTAL.EVALUACION"):
        assert p.alertas(FakeCtx(periodo_id=1)) == []
    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_evaluacion_rutas_registradas(rutas_registradas):
    from src.services.portal.evaluacion_provider import EvaluacionProvider
    p = EvaluacionProvider(habilitacion_svc_provider=lambda: FakeHabilitacionSvc(1))
    for ruta in _all_rutas(p, FakeCtx()):
        assert rutas_registradas(ruta) is not None, f"Ruta muerta: {ruta}"


# ── PortalContext ↔ SessionContext ────────────────────────────────────────────

def test_session_context_satisface_portal_context():
    """A6: la compatibilidad es estructural — el dominio no importa interfaz."""
    from src.interface.context.session_context import SessionContext
    ctx = SessionContext(usuario_id=1, usuario_nombre="Ana", usuario_rol="profesor")
    assert isinstance(ctx, PortalContext)


# ── Container ─────────────────────────────────────────────────────────────────

def test_container_portal_provider_convivencia():
    from container import Container
    from src.domain.portal_provider import PortalProvider
    p = Container.portal_provider("convivencia")
    assert p is not None
    assert isinstance(p, PortalProvider)


def test_container_portal_provider_evaluacion():
    from container import Container
    from src.domain.portal_provider import PortalProvider
    p = Container.portal_provider("evaluacion")
    assert p is not None
    assert isinstance(p, PortalProvider)


def test_container_portal_provider_sin_piloto():
    from container import Container
    p = Container.portal_provider("asistencia")
    assert p is None
