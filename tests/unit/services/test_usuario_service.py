"""Tests unitarios para UsuarioService."""
from __future__ import annotations

import pytest

from src.domain.models.usuario import (
    DocenteInfoDTO, FiltroUsuariosDTO, NuevoUsuarioDTO,
    ActualizarUsuarioDTO, Rol, Usuario, UsuarioResumenDTO,
)
from src.domain.ports.usuario_repo import IUsuarioRepository
from src.domain.ports.service_ports import IAuthenticationService
from src.services.usuario_service import UsuarioService


# ===========================================================================
# Fakes
# ===========================================================================

class FakeUsuarioRepo(IUsuarioRepository):
    def __init__(self):
        self._users: dict[int, Usuario] = {}
        self._next_id = 1

    def guardar(self, u: Usuario) -> Usuario:
        u = u.model_copy(update={"id": self._next_id})
        self._next_id += 1
        self._users[u.id] = u
        return u

    def actualizar(self, u: Usuario) -> Usuario:
        self._users[u.id] = u
        return u

    def get_by_id(self, uid: int) -> Usuario | None:
        return self._users.get(uid)

    def get_by_username(self, username: str) -> Usuario | None:
        for u in self._users.values():
            if u.usuario == username:
                return u
        return None

    def get_by_email(self, email: str) -> Usuario | None:
        return None

    def existe_usuario(self, username: str) -> bool:
        return any(u.usuario == username for u in self._users.values())

    def desactivar(self, uid: int) -> None:
        u = self._users[uid]
        self._users[uid] = u.model_copy(update={"activo": False})

    def reactivar(self, uid: int) -> None:
        u = self._users[uid]
        self._users[uid] = u.model_copy(update={"activo": True})

    def cambiar_rol(self, uid: int, rol: Rol) -> None:
        u = self._users[uid]
        self._users[uid] = u.model_copy(update={"rol": rol})

    def listar_filtrado(self, filtro: FiltroUsuariosDTO) -> list[Usuario]:
        return list(self._users.values())

    def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]:
        return []

    def listar_docentes_info(self, periodo_id=None, solo_activos=True) -> list[DocenteInfoDTO]:
        return []

    def get_docente_info(self, uid: int) -> DocenteInfoDTO | None:
        return None

    def listar_asignaciones_docente(self, uid: int, periodo_id=None):
        return []


class FakeAuth(IAuthenticationService):
    def __init__(self, pass_ok: bool = True):
        self._pass_ok = pass_ok
        self._hashes: dict[int, str] = {}

    def hashear_password(self, p: str) -> str:
        return f"hash:{p}"

    def verificar_password(self, plain: str, hashed: str) -> bool:
        return self._pass_ok

    def cambiar_password(self, uid: int, actual: str, nueva: str) -> bool:
        return self._pass_ok

    def resetear_password(self, uid: int, nueva: str) -> None:
        self._hashes[uid] = f"hash:{nueva}"


def _dto(usuario: str = "prof1") -> NuevoUsuarioDTO:
    return NuevoUsuarioDTO(
        usuario=usuario,
        nombre_completo="Profesor Uno",
        rol=Rol.PROFESOR,
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestCrearUsuario:
    def test_crea_usuario_nuevo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("prof1"))
        assert u.id is not None
        assert u.usuario == "prof1"

    def test_lanza_si_username_duplicado(self):
        svc = UsuarioService(FakeUsuarioRepo())
        svc.crear_usuario(_dto("prof1"))
        with pytest.raises(ValueError, match="prof1"):
            svc.crear_usuario(_dto("prof1"))

    def test_llama_resetear_password_cuando_hay_auth(self):
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = svc.crear_usuario(_dto("prof1"))
        assert u.id in auth._hashes


class TestDesactivar:
    def test_desactiva_usuario_activo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto())
        resultado = svc.desactivar(u.id)
        assert resultado.activo is False

    def test_lanza_si_ya_inactivo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto())
        svc.desactivar(u.id)
        with pytest.raises(ValueError):
            svc.desactivar(u.id)

    def test_lanza_si_usuario_no_existe(self):
        svc = UsuarioService(FakeUsuarioRepo())
        with pytest.raises(ValueError, match="999"):
            svc.desactivar(999)


class TestCambiarPassword:
    def test_lanza_si_sin_auth_service(self):
        svc = UsuarioService(FakeUsuarioRepo())
        with pytest.raises(ValueError, match="autenticaci"):
            svc.cambiar_password(1, "vieja", "nueva")

    def test_lanza_si_password_incorrecta(self):
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=FakeAuth(pass_ok=False))
        with pytest.raises(ValueError, match="no es correcta"):
            svc.cambiar_password(1, "vieja", "nueva")

    def test_cambia_password_correctamente(self):
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=FakeAuth(pass_ok=True))
        svc.cambiar_password(1, "vieja", "nueva")  # no lanza


class TestCambiarRol:
    def test_cambia_rol_de_usuario_activo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto())
        resultado = svc.cambiar_rol(u.id, Rol.COORDINADOR)
        assert resultado.rol == Rol.COORDINADOR

    def test_lanza_si_usuario_inactivo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto())
        svc.desactivar(u.id)
        with pytest.raises(ValueError, match="desactivado"):
            svc.cambiar_rol(u.id, Rol.DIRECTOR)
