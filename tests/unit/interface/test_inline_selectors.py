"""
tests/unit/interface/test_inline_selectors.py
==============================================
Tests de lógica pura del componente inline_selectors (sin render NiceGUI).

Verifican:
  - Pre-selección de periodo (preselect_periodo True/False).
  - Cascada: cambio de periodo limpia grupo y asignación.
  - Cascada: cambio de grupo limpia asignación.
  - _seleccion_completa_3d y _seleccion_completa_2d.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.interface.design.components.inline_selectors import (
    _estado_inicial,
    _on_asignacion_cambio,
    _on_grupo_cambio,
    _on_periodo_cambio,
    _preseleccionar_periodo,
    _seleccion_completa_2d,
    _seleccion_completa_3d,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _s_vacio() -> dict:
    """Retorna un estado con las claves en sus valores por defecto."""
    s: dict = {}
    _estado_inicial(s)
    return s


def _mock_periodo(
    pid: int,
    nombre: str,
    activo: bool = True,
    cerrado: bool = False,
) -> MagicMock:
    p = MagicMock()
    p.id = pid
    p.nombre = nombre
    p.activo = activo
    p.cerrado = cerrado
    return p


# ─── Tests — pre-selección ────────────────────────────────────────────────────

class TestPreseleccion:

    def test_preselect_false_no_modifica_s(self):
        """Sin llamar _preseleccionar_periodo, s queda vacío tras _estado_inicial."""
        s = _s_vacio()
        # preselect_periodo=False significa que el caller NO llama
        # _preseleccionar_periodo → el estado debe permanecer con None.
        assert s["sel_periodo_id"] is None
        assert s["sel_grupo_id"] is None
        assert s["sel_asignacion_id"] is None

    def test_preselect_true_selecciona_primer_abierto(self):
        """El primer periodo con activo=True y cerrado=False se escribe en s."""
        s = _s_vacio()
        p_abierto = _mock_periodo(pid=1, nombre="2025-1", activo=True, cerrado=False)
        p_cerrado = _mock_periodo(pid=2, nombre="2024-4", activo=False, cerrado=True)
        mock_config = MagicMock()
        mock_config.id = 10

        with patch(
            "src.interface.design.components.inline_selectors.Container"
        ) as mock_c:
            mock_c.configuracion_service.return_value.get_activa.return_value = (
                mock_config
            )
            mock_c.periodo_service.return_value.listar_por_anio.return_value = [
                p_cerrado,
                p_abierto,
            ]
            _preseleccionar_periodo(s, institucion_id=1)

        assert s["sel_periodo_id"] == 1
        assert s["sel_periodo_nombre"] == "2025-1"

    def test_preselect_true_sin_abiertos_deja_none(self):
        """Sin periodos activos, sel_periodo_id permanece None."""
        s = _s_vacio()
        p_cerrado = _mock_periodo(pid=1, nombre="2024-4", activo=False, cerrado=True)
        mock_config = MagicMock()
        mock_config.id = 10

        with patch(
            "src.interface.design.components.inline_selectors.Container"
        ) as mock_c:
            mock_c.configuracion_service.return_value.get_activa.return_value = (
                mock_config
            )
            mock_c.periodo_service.return_value.listar_por_anio.return_value = [
                p_cerrado
            ]
            _preseleccionar_periodo(s, institucion_id=1)

        assert s["sel_periodo_id"] is None
        assert s["sel_periodo_nombre"] == ""


# ─── Tests — cascada ─────────────────────────────────────────────────────────

class TestCascada:

    def test_cambio_periodo_limpia_grupo_y_asignacion(self):
        """Al cambiar periodo, sel_grupo_id y sel_asignacion_id quedan en None."""
        s = _s_vacio()
        # Establecer estado previo con grupo y asignación
        s["sel_grupo_id"] = 5
        s["sel_grupo_nombre"] = "10A"
        s["sel_asignacion_id"] = 99
        s["sel_asignacion_nombre"] = "Matematicas"

        _on_periodo_cambio(s, periodo_id=2, periodo_nombre="2025-2")

        assert s["sel_periodo_id"] == 2
        assert s["sel_periodo_nombre"] == "2025-2"
        assert s["sel_grupo_id"] is None
        assert s["sel_grupo_nombre"] == ""
        assert s["sel_asignacion_id"] is None
        assert s["sel_asignacion_nombre"] == ""

    def test_cambio_grupo_limpia_asignacion(self):
        """Al cambiar grupo, sel_asignacion_id queda en None."""
        s = _s_vacio()
        s["sel_periodo_id"] = 1
        s["sel_periodo_nombre"] = "2025-1"
        s["sel_asignacion_id"] = 77
        s["sel_asignacion_nombre"] = "Fisica"

        _on_grupo_cambio(s, grupo_id=3, grupo_nombre="11B")

        assert s["sel_grupo_id"] == 3
        assert s["sel_grupo_nombre"] == "11B"
        assert s["sel_asignacion_id"] is None
        assert s["sel_asignacion_nombre"] == ""
        # Periodo no se toca
        assert s["sel_periodo_id"] == 1


# ─── Tests — selección completa ───────────────────────────────────────────────

class TestSeleccionCompleta:

    def test_on_change_solo_cuando_completa_3d(self):
        """_seleccion_completa_3d retorna False con solo periodo; True con los 3."""
        s = _s_vacio()
        _on_periodo_cambio(s, 1, "2025-1")
        # Solo periodo: incompleto
        assert not _seleccion_completa_3d(s)

        # Con grupo: aun incompleto
        s["sel_grupo_id"] = 5
        assert not _seleccion_completa_3d(s)

        # Con asignación: completo
        s["sel_asignacion_id"] = 10
        assert _seleccion_completa_3d(s)

    def test_on_change_solo_cuando_completa_2d(self):
        """_seleccion_completa_2d retorna False con solo periodo; True con periodo+grupo."""
        s = _s_vacio()
        _on_periodo_cambio(s, 1, "2025-1")
        assert not _seleccion_completa_2d(s)

        _on_grupo_cambio(s, 5, "10A")
        assert _seleccion_completa_2d(s)
        # La asignación NO es requisito en 2D
        assert s["sel_asignacion_id"] is None
