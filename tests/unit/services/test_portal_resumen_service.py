"""
test_portal_resumen_service.py — portal_37/A5: PortalResumenService.

El servicio ya NO reimplementa el conteo de convivencia: agrega los
`PortalProvider` registrados. Los fakes usan firmas EXPLÍCITAS (M8).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.portal_provider import PortalContext, SubItem
from src.services.portal_resumen_service import (
    PortalResumenService,
    ResumenGlobalDTO,
)

# ── Contexto fake ─────────────────────────────────────────────────────────────

@dataclass
class FakeCtx:
    institucion_id: int | None = None
    periodo_id: int | None = None


# ── Providers fake (firmas explícitas, sin **kwargs) ──────────────────────────

class FakeProvider:
    def __init__(self, nombre: str, alertas: list[SubItem] | None = None):
        self._nombre = nombre
        self._alertas = alertas or []
        self.ctx_recibido: list[PortalContext] = []

    def recientes(self, ctx: PortalContext) -> list[SubItem]:
        return []

    def alertas(self, ctx: PortalContext) -> list[SubItem]:
        self.ctx_recibido.append(ctx)
        return list(self._alertas)

    def hitos(self, ctx: PortalContext) -> list[SubItem]:
        return []


class ProviderRoto:
    def recientes(self, ctx: PortalContext) -> list[SubItem]:
        raise RuntimeError("DB error")

    def alertas(self, ctx: PortalContext) -> list[SubItem]:
        raise RuntimeError("DB error")

    def hitos(self, ctx: PortalContext) -> list[SubItem]:
        raise RuntimeError("DB error")


def _alerta(label: str, ruta: str, severidad: str = "warning", conteo: int = 1) -> SubItem:
    return SubItem(
        label=label,
        detalle="Revisar",
        ruta_destino=ruta,
        severidad=severidad,
        conteo=conteo,
    )


def _svc(*providers) -> PortalResumenService:
    return PortalResumenService(providers_provider=lambda: list(providers))


# ── Casos base ────────────────────────────────────────────────────────────────

def test_resumen_sin_providers_retorna_vacio():
    result = _svc().resumen_global(FakeCtx())
    assert isinstance(result, ResumenGlobalDTO)
    assert result.lineas == []
    assert result.total_notificaciones == 0


def test_resumen_sin_alertas_retorna_vacio():
    result = _svc(FakeProvider("conv")).resumen_global(FakeCtx())
    assert result.lineas == []
    assert result.total_notificaciones == 0


def test_resumen_con_alertas_genera_linea():
    conv = FakeProvider("conv", [_alerta("3 alertas pendientes", "/convivencia/seguimiento")])
    result = _svc(conv).resumen_global(FakeCtx())
    assert len(result.lineas) == 1
    linea = result.lineas[0]
    assert "3" in linea.texto
    assert linea.ruta_destino == "/convivencia/seguimiento"
    assert linea.severidad == "warning"


# ── A5: el resumen agrega TODOS los providers ─────────────────────────────────

def test_resumen_incluye_alertas_de_ambos_providers():
    """Cazaría el bug A5: Evaluación jamás llegaba al resumen global.

    Y fija la semántica del badge: 3 alertas + 2 habilitaciones ⇒ 5 REGISTROS,
    no 2 líneas. Si `resumen_global` vuelve a contar ítems, esto falla.
    """
    conv = FakeProvider(
        "conv",
        [_alerta("3 alertas pendientes", "/convivencia/seguimiento", conteo=3)],
    )
    eva = FakeProvider(
        "eva",
        [_alerta("2 habilitaciones pendientes", "/evaluacion/habilitaciones", conteo=2)],
    )
    result = _svc(conv, eva).resumen_global(FakeCtx())

    rutas = [linea.ruta_destino for linea in result.lineas]
    assert rutas == ["/convivencia/seguimiento", "/evaluacion/habilitaciones"]
    assert len(result.lineas) == 2
    assert result.total_notificaciones == 5


def test_modulo_nuevo_aparece_solo_con_registrarse():
    """El punto de extensión debe ser real: sin tocar el servicio."""
    nuevo = FakeProvider(
        "asistencia",
        [_alerta("7 inasistencias sin justificar", "/inicio", conteo=7)],
    )
    result = _svc(nuevo).resumen_global(FakeCtx())
    assert len(result.lineas) == 1
    assert result.total_notificaciones == 7


# ── Mapeo SubItem → LineaResumenDTO ───────────────────────────────────────────

def test_texto_concatena_label_y_detalle():
    p = FakeProvider("x", [SubItem(label="L", detalle="D", ruta_destino="/r", severidad="warning")])
    linea = _svc(p).resumen_global(FakeCtx()).lineas[0]
    assert linea.texto == "L — D"


def test_texto_sin_detalle_usa_solo_label():
    p = FakeProvider("x", [SubItem(label="L", detalle="", ruta_destino="/r", severidad="warning")])
    linea = _svc(p).resumen_global(FakeCtx()).lineas[0]
    assert linea.texto == "L"


def test_severidad_success_degrada_a_info_y_no_notifica():
    """LineaResumenDTO no admite 'success'; y sólo warning/error cuentan al badge."""
    p = FakeProvider("x", [_alerta("Hito", "/r", severidad="success", conteo=9)])
    result = _svc(p).resumen_global(FakeCtx())
    assert result.lineas[0].severidad == "info"
    assert result.total_notificaciones == 0


def test_total_notificaciones_suma_registros_no_lineas():
    """Semántica del badge: REGISTROS accionables (suma de `conteo`)."""
    p = FakeProvider(
        "x",
        [
            _alerta("3 alertas", "/a", severidad="warning", conteo=3),
            _alerta("1 crítica", "/b", severidad="error", conteo=1),
            _alerta("10 avisos", "/c", severidad="info", conteo=10),
        ],
    )
    result = _svc(p).resumen_global(FakeCtx())
    assert len(result.lineas) == 3
    # 3 + 1 accionables; los 10 informativos no suman.
    assert result.total_notificaciones == 4


def test_subitem_sin_conteo_explicito_vale_uno():
    """Default 1: un aviso suelto sigue notificando exactamente una unidad."""
    p = FakeProvider("x", [_alerta("Aviso suelto", "/a", severidad="warning")])
    assert _svc(p).resumen_global(FakeCtx()).total_notificaciones == 1


def test_servicio_no_parsea_el_texto_para_deducir_el_conteo():
    """El label dice 99 pero el DTO dice 2: manda el DTO, nadie parsea texto."""
    p = FakeProvider("x", [_alerta("99 alertas pendientes", "/a", conteo=2)])
    assert _svc(p).resumen_global(FakeCtx()).total_notificaciones == 2


# ── Fail-open ─────────────────────────────────────────────────────────────────

def test_provider_roto_no_tumba_el_resto(caplog):
    conv = FakeProvider("conv", [_alerta("3 alertas pendientes", "/convivencia/seguimiento")])
    svc = _svc(ProviderRoto(), conv)
    with caplog.at_level("WARNING", logger="PORTAL.RESUMEN"):
        result = svc.resumen_global(FakeCtx())
    assert len(result.lineas) == 1
    assert result.lineas[0].ruta_destino == "/convivencia/seguimiento"
    assert result.total_notificaciones == 1
    # M4: el provider roto deja traza en el log.
    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_fail_open_si_falla_la_obtencion_de_providers(caplog):
    def boom():
        raise RuntimeError("container caído")

    svc = PortalResumenService(providers_provider=boom)
    with caplog.at_level("ERROR", logger="PORTAL.RESUMEN"):
        result = svc.resumen_global(FakeCtx())
    assert isinstance(result, ResumenGlobalDTO)
    assert result.lineas == []
    assert result.total_notificaciones == 0
    assert any(r.levelname == "ERROR" for r in caplog.records)


# ── ctx ───────────────────────────────────────────────────────────────────────

def test_ctx_se_propaga_a_todos_los_providers():
    """A6: el ctx debe llegar tipado y sin transformar a cada provider."""
    conv = FakeProvider("conv")
    eva = FakeProvider("eva")
    ctx = FakeCtx(institucion_id=7, periodo_id=42)
    _svc(conv, eva).resumen_global(ctx)
    assert conv.ctx_recibido == [ctx]
    assert eva.ctx_recibido == [ctx]
    assert isinstance(ctx, PortalContext)


# ── Serialización ─────────────────────────────────────────────────────────────

def test_model_dump_es_serializable():
    p = FakeProvider("x", [_alerta("2 alertas", "/r", conteo=2)])
    d = _svc(p).resumen_global(FakeCtx()).model_dump()
    assert "lineas" in d
    assert "total_notificaciones" in d
    assert isinstance(d["lineas"], list)
    assert set(d["lineas"][0]) == {"texto", "ruta_destino", "severidad"}
