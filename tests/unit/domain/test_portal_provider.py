"""
test_portal_provider.py — portal_38: protocolo PortalProvider, PortalContext y SubItem.

M8: los fakes declaran firmas EXPLÍCITAS (nada de `**kwargs`) — ese agujero fue
justamente lo que dejó pasar A5/A6 sin que ningún test fallara.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.portal_provider import PortalContext, PortalProvider, SubItem


@dataclass
class FakeCtx:
    """Réplica estructural mínima de SessionContext (capa interfaz)."""

    institucion_id: int | None = None
    periodo_id: int | None = None


class _StubProvider:
    def __init__(self) -> None:
        self.ctx_visto: list[PortalContext] = []

    def recientes(self, ctx: PortalContext) -> list[SubItem]:
        self.ctx_visto.append(ctx)
        return [SubItem(label="R", detalle="d", ruta_destino="/inicio", severidad="info")]

    def alertas(self, ctx: PortalContext) -> list[SubItem]:
        self.ctx_visto.append(ctx)
        return []

    def hitos(self, ctx: PortalContext) -> list[SubItem]:
        self.ctx_visto.append(ctx)
        return [SubItem(label="H", detalle="d", ruta_destino="/inicio", severidad="success")]


# ── SubItem ───────────────────────────────────────────────────────────────────

def test_subitem_es_dataclass_inmutable():
    item = SubItem(label="X", detalle="y", ruta_destino="/r", severidad="info")
    assert item.label == "X"
    assert item.model_dump()["ruta_destino"] == "/r"


def test_subitem_conteo_default_es_uno():
    """Default 1: ningún constructor existente de SubItem se rompe."""
    item = SubItem(label="X", detalle="y", ruta_destino="/r", severidad="info")
    assert item.conteo == 1


def test_subitem_transporta_el_conteo_real():
    """El entero viaja por el DTO — nadie tiene que parsear `label`."""
    item = SubItem(label="3 alertas", detalle="d", ruta_destino="/r", severidad="warning", conteo=3)
    assert item.conteo == 3
    assert item.model_dump()["conteo"] == 3


def test_subitem_model_dump_expone_todos_los_campos():
    item = SubItem(label="X", detalle="y", ruta_destino="/r", severidad="info", conteo=4)
    assert set(item.model_dump()) == {"label", "detalle", "ruta_destino", "severidad", "conteo"}


# ── PortalProvider ────────────────────────────────────────────────────────────

def test_stub_satisface_protocolo():
    stub = _StubProvider()
    assert isinstance(stub, PortalProvider)


def test_stub_recientes_retorna_lista():
    stub = _StubProvider()
    items = stub.recientes(FakeCtx())
    assert isinstance(items, list)
    assert all(isinstance(i, SubItem) for i in items)


def test_provider_recibe_el_ctx_que_se_le_pasa():
    """A6: el ctx no puede seguir siendo un parámetro inerte."""
    stub = _StubProvider()
    ctx = FakeCtx(institucion_id=7, periodo_id=3)
    stub.recientes(ctx)
    stub.alertas(ctx)
    stub.hitos(ctx)
    assert stub.ctx_visto == [ctx, ctx, ctx]


# ── PortalContext ─────────────────────────────────────────────────────────────

def test_portal_context_declara_los_campos_usados():
    anotaciones = PortalContext.__annotations__
    assert "institucion_id" in anotaciones
    assert "periodo_id" in anotaciones


def test_dataclass_estructuralmente_compatible_satisface_portal_context():
    """PortalContext es estructural: no hace falta heredar ni importar nada."""
    assert isinstance(FakeCtx(institucion_id=1, periodo_id=2), PortalContext)


def test_objeto_sin_los_campos_no_satisface_portal_context():
    class Vacio:
        pass

    assert not isinstance(Vacio(), PortalContext)
