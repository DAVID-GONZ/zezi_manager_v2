"""Tests unitarios para BcryptAuthService."""
from __future__ import annotations

import pytest

from src.infrastructure.auth.bcrypt_auth_service import BcryptAuthService
from src.domain.ports.usuario_repo import IUsuarioRepository
from src.domain.models.usuario import (
    AsignacionDocenteInfoDTO, DocenteInfoDTO,
    FiltroUsuariosDTO, Rol, Usuario, UsuarioResumenDTO,
)


# ===========================================================================
# Fake mínimo de IUsuarioRepository para las pruebas de auth
# ===========================================================================

class FakeRepoAuth(IUsuarioRepository):
    """Fake de IUsuarioRepository que solo soporta operaciones de contraseña."""

    def __init__(self, hashes: dict[int, str] | None = None) -> None:
        self._hashes: dict[int, str] = hashes or {}

    # --- credenciales ---
    def get_password_hash(self, usuario_id: int) -> str | None:
        return self._hashes.get(usuario_id)

    def actualizar_password_hash(self, usuario_id: int, nuevo_hash: str) -> bool:
        self._hashes[usuario_id] = nuevo_hash
        return True

    # --- stubs obligatorios del port ---
    def get_by_id(self, uid): return None
    def get_by_username(self, u): return None
    def get_by_email(self, e): return None
    def existe_usuario(self, u): return False
    def listar_filtrado(self, f): return []
    def listar_resumenes(self, f): return []
    def listar_docentes_info(self, periodo_id=None, solo_activos=True): return []
    def get_docente_info(self, uid, periodo_id=None): return None
    def listar_asignaciones_docente(self, uid, periodo_id=None): return []
    def guardar(self, u): return u
    def actualizar(self, u): return u
    def cambiar_rol(self, uid, rol): return True
    def desactivar(self, uid): return True
    def reactivar(self, uid): return True


# ===========================================================================
# hashear_password
# ===========================================================================

class TestHashearPassword:
    def test_retorna_string_no_vacio(self):
        svc = BcryptAuthService(FakeRepoAuth())
        h = svc.hashear_password("secret")
        assert isinstance(h, str) and len(h) > 0

    def test_hash_bcrypt_comienza_con_dolar_2b(self):
        svc = BcryptAuthService(FakeRepoAuth())
        h = svc.hashear_password("secret")
        assert h.startswith("$2b$")

    def test_dos_hashes_del_mismo_password_son_distintos(self):
        svc = BcryptAuthService(FakeRepoAuth())
        assert svc.hashear_password("abc") != svc.hashear_password("abc")


# ===========================================================================
# verificar_password
# ===========================================================================

class TestVerificarPassword:
    def test_verifica_hash_bcrypt_correcto(self):
        svc = BcryptAuthService(FakeRepoAuth())
        h = svc.hashear_password("clave123")
        assert svc.verificar_password("clave123", h) is True

    def test_falla_con_password_incorrecto(self):
        svc = BcryptAuthService(FakeRepoAuth())
        h = svc.hashear_password("clave123")
        assert svc.verificar_password("incorrecta", h) is False

    def test_verifica_hash_sha256_legacy(self):
        import hashlib
        digest = hashlib.sha256("seedpass".encode()).hexdigest()
        legacy = f"sha256:{digest}"
        svc = BcryptAuthService(FakeRepoAuth())
        assert svc.verificar_password("seedpass", legacy) is True

    def test_falla_sha256_legacy_con_password_incorrecto(self):
        import hashlib
        digest = hashlib.sha256("seedpass".encode()).hexdigest()
        legacy = f"sha256:{digest}"
        svc = BcryptAuthService(FakeRepoAuth())
        assert svc.verificar_password("otra", legacy) is False

    def test_retorna_false_con_hash_invalido(self):
        svc = BcryptAuthService(FakeRepoAuth())
        assert svc.verificar_password("abc", "hash_completamente_invalido") is False


# ===========================================================================
# cambiar_password
# ===========================================================================

class TestCambiarPassword:
    def _svc_con_hash(self, usuario_id: int, password: str):
        """Helper: crea servicio con el hash de 'password' ya almacenado."""
        svc = BcryptAuthService(FakeRepoAuth())
        hash_inicial = svc.hashear_password(password)
        repo = FakeRepoAuth(hashes={usuario_id: hash_inicial})
        return BcryptAuthService(repo), repo

    def test_cambia_password_exitosamente(self):
        svc, repo = self._svc_con_hash(1, "vieja")
        resultado = svc.cambiar_password(1, "vieja", "nueva")
        assert resultado is True

    def test_nuevo_hash_es_verificable(self):
        svc, repo = self._svc_con_hash(1, "vieja")
        svc.cambiar_password(1, "vieja", "nueva_clave")
        hash_nuevo = repo.get_password_hash(1)
        assert svc.verificar_password("nueva_clave", hash_nuevo) is True

    def test_lanza_si_usuario_no_existe(self):
        svc = BcryptAuthService(FakeRepoAuth())  # repo vacío
        with pytest.raises(ValueError, match="no encontrado"):
            svc.cambiar_password(99, "cualquiera", "nueva")

    def test_lanza_si_password_actual_incorrecta(self):
        svc, _ = self._svc_con_hash(1, "correcta")
        with pytest.raises(ValueError, match="no es correcta"):
            svc.cambiar_password(1, "incorrecta", "nueva")

    def test_hash_no_cambia_si_password_actual_falla(self):
        svc, repo = self._svc_con_hash(1, "correcta")
        hash_antes = repo.get_password_hash(1)
        with pytest.raises(ValueError):
            svc.cambiar_password(1, "mal", "nueva")
        assert repo.get_password_hash(1) == hash_antes


# ===========================================================================
# resetear_password
# ===========================================================================

class TestResetearPassword:
    def test_resetea_sin_verificar_actual(self):
        repo = FakeRepoAuth(hashes={5: "hash_viejo"})
        svc = BcryptAuthService(repo)
        svc.resetear_password(5, "clave_nueva")
        assert repo.get_password_hash(5) != "hash_viejo"

    def test_nuevo_hash_es_verificable_tras_reset(self):
        repo = FakeRepoAuth(hashes={5: "hash_viejo"})
        svc = BcryptAuthService(repo)
        svc.resetear_password(5, "clave_nueva")
        assert svc.verificar_password("clave_nueva", repo.get_password_hash(5)) is True

    def test_resetear_sobre_usuario_inexistente_crea_entrada(self):
        repo = FakeRepoAuth()
        svc = BcryptAuthService(repo)
        svc.resetear_password(42, "pass")
        assert repo.get_password_hash(42) is not None
