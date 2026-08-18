"""
Tests unitarios de dominio — modelos de convivencia (convivencia_09).

Cubre CategoriaObservacion y NuevaCategoriaDTO; los modelos existentes
(ObservacionPeriodo, RegistroComportamiento, NotaComportamiento) se
ejercitan en otros módulos de test de dominio.
"""
from __future__ import annotations

from src.domain.models.convivencia import CategoriaObservacion, NuevaCategoriaDTO

# ---------------------------------------------------------------------------
# CategoriaObservacion
# ---------------------------------------------------------------------------

class TestCategoriaObservacion:

    def test_defaults(self):
        """Defaults: activa=True, es_comportamental=False, id=None."""
        c = CategoriaObservacion(nombre="Académico")
        assert c.id is None
        assert c.activa is True
        assert c.es_comportamental is False

    def test_comportamental_true(self):
        """es_comportamental puede ser True."""
        c = CategoriaObservacion(nombre="Convivencia y normas", es_comportamental=True)
        assert c.es_comportamental is True
        assert c.activa is True

    def test_inactiva(self):
        """activa puede ser False (categoría desactivada)."""
        c = CategoriaObservacion(nombre="Antigua", activa=False)
        assert c.activa is False

    def test_con_id(self):
        """El campo id se puede asignar (proveniente de la BD)."""
        c = CategoriaObservacion(id=5, nombre="Responsabilidad")
        assert c.id == 5

    def test_model_dump(self):
        """model_dump() devuelve el dict completo (sin .dict())."""
        c = CategoriaObservacion(id=1, nombre="Test", es_comportamental=True, activa=False)
        d = c.model_dump()
        assert d["id"] == 1
        assert d["nombre"] == "Test"
        assert d["es_comportamental"] is True
        assert d["activa"] is False


# ---------------------------------------------------------------------------
# NuevaCategoriaDTO
# ---------------------------------------------------------------------------

class TestNuevaCategoriaDTO:

    def test_defaults(self):
        """es_comportamental es False por defecto."""
        dto = NuevaCategoriaDTO(nombre="Participación")
        assert dto.nombre == "Participación"
        assert dto.es_comportamental is False

    def test_comportamental_true(self):
        """es_comportamental puede sobreescribirse."""
        dto = NuevaCategoriaDTO(nombre="Comportamiento positivo", es_comportamental=True)
        assert dto.es_comportamental is True

    def test_model_dump(self):
        """model_dump() incluye los dos campos."""
        dto = NuevaCategoriaDTO(nombre="X", es_comportamental=False)
        d = dto.model_dump()
        assert set(d.keys()) == {"nombre", "es_comportamental"}
