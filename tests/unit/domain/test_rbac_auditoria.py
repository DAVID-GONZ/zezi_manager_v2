"""Tests de la política pura RBAC de auditoría (obs_10, T1/T2; obs_12, T13)."""
from __future__ import annotations

from src.domain.models.usuario import Rol
from src.domain.policies.rbac_auditoria import (
    puede_exportar_bitacora,
    puede_purgar_bitacora,
    puede_ver_historial,
)


class TestPuedeVerHistorial:
    # --- roles auditores (True) ---

    def test_admin_puede_ver(self):
        assert puede_ver_historial("admin") is True

    def test_director_puede_ver(self):
        assert puede_ver_historial("director") is True

    def test_coordinador_puede_ver(self):
        assert puede_ver_historial("coordinador") is True

    # --- roles sin acceso (False) ---

    def test_profesor_no_puede(self):
        assert puede_ver_historial("profesor") is False

    def test_estudiante_no_puede(self):
        assert puede_ver_historial("estudiante") is False

    def test_apoderado_no_puede(self):
        assert puede_ver_historial("apoderado") is False

    def test_none_no_puede(self):
        assert puede_ver_historial(None) is False

    def test_cadena_vacia_no_puede(self):
        assert puede_ver_historial("") is False

    # --- acepta enum Rol ---

    def test_acepta_rol_enum_director(self):
        assert puede_ver_historial(Rol.DIRECTOR) is True

    def test_acepta_rol_enum_coordinador(self):
        assert puede_ver_historial(Rol.COORDINADOR) is True

    def test_acepta_rol_enum_admin(self):
        assert puede_ver_historial(Rol.ADMIN) is True

    def test_acepta_rol_enum_profesor(self):
        assert puede_ver_historial(Rol.PROFESOR) is False

    # --- normalización ---

    def test_mayusculas_normalizadas(self):
        assert puede_ver_historial("ADMIN") is True
        assert puede_ver_historial("DIRECTOR") is True
        assert puede_ver_historial("COORDINADOR") is True

    def test_espacios_normalizados(self):
        assert puede_ver_historial("  admin  ") is True
        assert puede_ver_historial("  profesor  ") is False


# ---------------------------------------------------------------------------
# Tests obs_12 T13: puede_exportar_bitacora
# ---------------------------------------------------------------------------


class TestPuedeExportarBitacora:
    """obs_12 R13: admin, director y coordinador pueden exportar."""

    # --- roles con permiso (True) ---

    def test_admin_puede_exportar(self):
        assert puede_exportar_bitacora("admin") is True

    def test_director_puede_exportar(self):
        assert puede_exportar_bitacora("director") is True

    def test_coordinador_puede_exportar(self):
        assert puede_exportar_bitacora("coordinador") is True

    # --- roles sin permiso (False) ---

    def test_profesor_no_puede_exportar(self):
        assert puede_exportar_bitacora("profesor") is False

    def test_estudiante_no_puede_exportar(self):
        assert puede_exportar_bitacora("estudiante") is False

    def test_none_no_puede_exportar(self):
        assert puede_exportar_bitacora(None) is False

    def test_cadena_vacia_no_puede_exportar(self):
        assert puede_exportar_bitacora("") is False

    # --- acepta enum Rol ---

    def test_acepta_enum_admin(self):
        assert puede_exportar_bitacora(Rol.ADMIN) is True

    def test_acepta_enum_director(self):
        assert puede_exportar_bitacora(Rol.DIRECTOR) is True

    def test_acepta_enum_coordinador(self):
        assert puede_exportar_bitacora(Rol.COORDINADOR) is True

    def test_acepta_enum_profesor_rechazado(self):
        assert puede_exportar_bitacora(Rol.PROFESOR) is False

    # --- normalización ---

    def test_mayusculas_normalizadas(self):
        assert puede_exportar_bitacora("ADMIN") is True
        assert puede_exportar_bitacora("DIRECTOR") is True


# ---------------------------------------------------------------------------
# Tests obs_12 T13: puede_purgar_bitacora
# ---------------------------------------------------------------------------


class TestPuedePurgarBitacora:
    """obs_12 R13: solo admin puede purgar."""

    # --- único rol con permiso (True) ---

    def test_admin_puede_purgar(self):
        assert puede_purgar_bitacora("admin") is True

    # --- todos los demás, incluyendo directivos (False) ---

    def test_director_no_puede_purgar(self):
        assert puede_purgar_bitacora("director") is False

    def test_coordinador_no_puede_purgar(self):
        assert puede_purgar_bitacora("coordinador") is False

    def test_profesor_no_puede_purgar(self):
        assert puede_purgar_bitacora("profesor") is False

    def test_none_no_puede_purgar(self):
        assert puede_purgar_bitacora(None) is False

    def test_cadena_vacia_no_puede_purgar(self):
        assert puede_purgar_bitacora("") is False

    # --- acepta enum Rol ---

    def test_acepta_enum_admin(self):
        assert puede_purgar_bitacora(Rol.ADMIN) is True

    def test_acepta_enum_director_rechazado(self):
        assert puede_purgar_bitacora(Rol.DIRECTOR) is False

    # --- normalización ---

    def test_mayusculas_normalizadas(self):
        assert puede_purgar_bitacora("ADMIN") is True
        assert puede_purgar_bitacora("DIRECTOR") is False
