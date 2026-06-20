"""Tests de la política pura RBAC de gestión de usuarios (paso_23, T1)."""
from __future__ import annotations

from src.domain.models.usuario import Rol
from src.domain.policies.rbac_usuarios import (
    puede_asignar_rol,
    puede_gestionar,
    roles_asignables,
)


class TestRolesAsignables:
    def test_admin_asigna_admin_y_director(self):
        assert roles_asignables("admin") == {"admin", "director"}

    def test_director_asigna_coordinador_y_profesor(self):
        assert roles_asignables("director") == {"coordinador", "profesor"}

    def test_coordinador_no_asigna_nada(self):
        assert roles_asignables("coordinador") == set()

    def test_acepta_enum_rol(self):
        assert roles_asignables(Rol.ADMIN) == {"admin", "director"}

    def test_actor_none(self):
        assert roles_asignables(None) == set()


class TestPuedeAsignarRol:
    def test_admin_puede_asignar_admin(self):
        assert puede_asignar_rol("admin", "admin") is True

    def test_director_no_puede_asignar_admin(self):
        assert puede_asignar_rol("director", "admin") is False


class TestPuedeGestionar:
    def test_admin_gestiona_cualquiera(self):
        for r in ("admin", "director", "coordinador", "profesor"):
            assert puede_gestionar("admin", r) is True

    def test_director_gestiona_solo_coordinador_y_profesor(self):
        assert puede_gestionar("director", "coordinador") is True
        assert puede_gestionar("director", "profesor") is True
        assert puede_gestionar("director", "admin") is False
        assert puede_gestionar("director", "director") is False

    def test_profesor_no_gestiona_a_nadie(self):
        assert puede_gestionar("profesor", "profesor") is False

    def test_acepta_enum(self):
        assert puede_gestionar(Rol.DIRECTOR, Rol.PROFESOR) is True
