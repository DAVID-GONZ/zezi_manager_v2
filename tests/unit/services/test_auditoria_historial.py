"""
Tests de AuditoriaService.historial_de (obs_10, T3/T4).

Cubre:
  - Orden cronológico ascendente devuelto por el repo.
  - Un director con scope=1 NO recibe cambios de la institución 2.
  - Las filas con institucion_id=None SÍ se incluyen aunque scope != "*".
  - Registro sin cambios → lista vacía.
  - scope="*" (admin) recibe todos los cambios independientemente de institución.
"""
from __future__ import annotations

from datetime import datetime

from src.domain.models.auditoria import AccionCambio, DetalleCambioDTO, RegistroCambio
from src.services.auditoria_service import AuditoriaService

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeAuditoriaRepo:
    """Repo mínimo con listar_cambios_por_registro y métodos de cadena."""

    def __init__(self, cambios: list[RegistroCambio] | None = None):
        self._cambios = cambios or []

    def listar_cambios_por_registro(
        self, tabla: str, registro_id: int
    ) -> list[RegistroCambio]:
        return list(self._cambios)

    # Métodos requeridos por AuditoriaService.__init__ implícitamente
    def verificar_cadena_eventos(self, *, completa: bool = False) -> int | None:
        return None

    def verificar_cadena_cambios(self, *, completa: bool = False) -> int | None:
        return None


# ---------------------------------------------------------------------------
# Helpers de construcción
# ---------------------------------------------------------------------------

def _cambio(
    timestamp: datetime,
    institucion_id: int | None = None,
    usuario_id: int | None = None,
) -> RegistroCambio:
    return RegistroCambio(
        accion=AccionCambio.UPDATE,
        tabla="estudiantes",
        registro_id=1,
        valor_anterior={"nombre": "Antiguo"},
        valor_nuevo={"nombre": "Nuevo"},
        timestamp=timestamp,
        institucion_id=institucion_id,
        usuario_id=usuario_id,
    )


def _svc(cambios: list[RegistroCambio]) -> AuditoriaService:
    return AuditoriaService(_FakeAuditoriaRepo(cambios))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHistorialDe:
    def test_registro_sin_cambios_devuelve_lista_vacia(self):
        svc = _svc([])
        resultado = svc.historial_de("estudiantes", 99, scope="*")
        assert resultado == []

    def test_devuelve_lista_de_detalle_cambio_dto(self):
        c = _cambio(datetime(2026, 1, 1), institucion_id=1)
        svc = _svc([c])
        resultado = svc.historial_de("estudiantes", 1, scope="*")
        assert len(resultado) == 1
        assert isinstance(resultado[0], DetalleCambioDTO)

    def test_scope_admin_recibe_todas_las_instituciones(self):
        cambios = [
            _cambio(datetime(2026, 1, 1), institucion_id=1),
            _cambio(datetime(2026, 1, 2), institucion_id=2),
            _cambio(datetime(2026, 1, 3), institucion_id=None),
        ]
        svc = _svc(cambios)
        resultado = svc.historial_de("estudiantes", 1, scope="*")
        assert len(resultado) == 3

    def test_scope_director_excluye_otra_institucion(self):
        cambios = [
            _cambio(datetime(2026, 1, 1), institucion_id=1),
            _cambio(datetime(2026, 1, 2), institucion_id=2),
        ]
        svc = _svc(cambios)
        resultado = svc.historial_de("estudiantes", 1, scope=1)
        assert len(resultado) == 1
        assert resultado[0].cambio.institucion_id == 1

    def test_filas_sin_institucion_incluidas_cuando_scope_numerico(self):
        cambios = [
            _cambio(datetime(2026, 1, 1), institucion_id=1),
            _cambio(datetime(2026, 1, 2), institucion_id=None),
        ]
        svc = _svc(cambios)
        resultado = svc.historial_de("estudiantes", 1, scope=1)
        assert len(resultado) == 2

    def test_orden_cronologico_ascendente_preservado(self):
        """El repo devuelve en orden; historial_de no debe reordenar."""
        t1 = datetime(2026, 1, 1)
        t2 = datetime(2026, 6, 1)
        t3 = datetime(2026, 9, 1)
        cambios = [
            _cambio(t1, institucion_id=1),
            _cambio(t2, institucion_id=1),
            _cambio(t3, institucion_id=1),
        ]
        svc = _svc(cambios)
        resultado = svc.historial_de("estudiantes", 1, scope="*")
        assert [r.cambio.timestamp for r in resultado] == [t1, t2, t3]

    def test_scope_2_no_ve_institucion_1(self):
        cambios = [
            _cambio(datetime(2026, 1, 1), institucion_id=1),
            _cambio(datetime(2026, 1, 2), institucion_id=2),
        ]
        svc = _svc(cambios)
        resultado = svc.historial_de("estudiantes", 1, scope=2)
        assert len(resultado) == 1
        assert resultado[0].cambio.institucion_id == 2
