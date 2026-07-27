"""Tests de la política pura RBAC de convivencia (convivencia_03, T2)."""
from __future__ import annotations

from src.domain.models.usuario import Rol
from src.domain.policies.rbac_convivencia import puede_gestionar_comportamiento


class TestDirectivos:
    def test_admin_nunca_gestiona_en_nombre_propio(self):
        # admin es auditor técnico: nunca edita datos directamente. Gestiona
        # convivencia solo vía impersonación ("ver como"), con el rol del objetivo.
        assert puede_gestionar_comportamiento("admin", True) is False
        assert puede_gestionar_comportamiento("admin", False) is False

    def test_director_siempre_puede(self):
        assert puede_gestionar_comportamiento("director", True) is True
        assert puede_gestionar_comportamiento("director", False) is True

    def test_coordinador_siempre_puede(self):
        assert puede_gestionar_comportamiento("coordinador", True) is True
        assert puede_gestionar_comportamiento("coordinador", False) is True


class TestProfesor:
    def test_profesor_director_del_grupo_puede(self):
        assert puede_gestionar_comportamiento("profesor", True) is True

    def test_profesor_de_otro_grupo_no_puede(self):
        assert puede_gestionar_comportamiento("profesor", False) is False


class TestOtros:
    def test_rol_desconocido_no_puede(self):
        assert puede_gestionar_comportamiento("estudiante", True) is False
        assert puede_gestionar_comportamiento("apoderado", True) is False

    def test_rol_none_no_puede(self):
        assert puede_gestionar_comportamiento(None, True) is False


class TestAceptaEnum:
    def test_acepta_enum_rol(self):
        assert puede_gestionar_comportamiento(Rol.COORDINADOR, False) is True
        assert puede_gestionar_comportamiento(Rol.PROFESOR, True) is True
        assert puede_gestionar_comportamiento(Rol.PROFESOR, False) is False
