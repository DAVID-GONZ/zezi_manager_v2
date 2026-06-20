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

    def actualizar_carga(self, usuario_id, carga_horaria_max, horas_extra) -> bool:
        u = self._users.get(usuario_id)
        if u is None:
            return False
        self._users[usuario_id] = u.model_copy(update={
            "carga_horaria_max": carga_horaria_max, "horas_extra": horas_extra,
        })
        return True

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

    def get_password_hash(self, usuario_id: int) -> str | None:
        return None

    def actualizar_password_hash(self, usuario_id: int, nuevo_hash: str) -> bool:
        return True


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

    def autenticar_usuario(self, nombre_usuario: str, password_plain: str):
        if not self._pass_ok:
            raise ValueError("Credenciales incorrectas")
        from unittest.mock import MagicMock
        u = MagicMock()
        u.id = 1
        return u


class FakeAuditoria:
    """Captura eventos de sesión y registros de cambio para aserciones."""
    def __init__(self):
        self.eventos: list = []
        self.cambios: list = []

    def registrar_evento(self, evento):
        self.eventos.append(evento)
        return evento

    def registrar_cambio(self, registro):
        self.cambios.append(registro)
        return registro

    def registrar_cambios_masivos(self, registros):
        self.cambios.extend(registros)
        return len(registros)

    def listar_eventos(self, filtro):
        return list(self.eventos)

    def get_ultimo_login(self, usuario_id):
        return None

    def contar_fallos_recientes(self, usuario, ventana_minutos=30):
        return 0

    def listar_cambios(self, filtro):
        return list(self.cambios)

    def listar_cambios_por_registro(self, tabla, registro_id):
        return []

    def get_cambio(self, cambio_id):
        return None


def _dto(usuario: str = "prof1", rol: Rol = Rol.PROFESOR) -> NuevoUsuarioDTO:
    return NuevoUsuarioDTO(
        usuario=usuario,
        nombre_completo="Profesor Uno",
        rol=rol,
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


# ===========================================================================
# RBAC — política de roles en el servicio (paso_23, T1)
# ===========================================================================

class TestRbacCrear:
    def test_admin_puede_crear_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("nuevo_admin", Rol.ADMIN), actor_rol="admin")
        assert u.rol == Rol.ADMIN

    def test_admin_puede_crear_director(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("nuevo_dir", Rol.DIRECTOR), actor_rol="admin")
        assert u.rol == Rol.DIRECTOR

    def test_director_no_puede_crear_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        with pytest.raises(ValueError, match="permiso"):
            svc.crear_usuario(_dto("x_admin", Rol.ADMIN), actor_rol="director")

    def test_director_no_puede_crear_director(self):
        svc = UsuarioService(FakeUsuarioRepo())
        with pytest.raises(ValueError, match="permiso"):
            svc.crear_usuario(_dto("x_dir", Rol.DIRECTOR), actor_rol="director")

    def test_director_puede_crear_profesor(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("prof_x", Rol.PROFESOR), actor_rol="director")
        assert u.rol == Rol.PROFESOR

    def test_sin_actor_rol_no_hay_enforcement(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("libre", Rol.ADMIN))  # actor_rol=None
        assert u.rol == Rol.ADMIN


class TestRbacCambiarRol:
    def test_admin_puede_promover_a_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("dir1", Rol.DIRECTOR))
        r = svc.cambiar_rol(u.id, Rol.ADMIN, actor_rol="admin")
        assert r.rol == Rol.ADMIN

    def test_director_no_puede_cambiar_rol_de_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("adm1", Rol.ADMIN))
        with pytest.raises(ValueError, match="permiso"):
            svc.cambiar_rol(u.id, Rol.COORDINADOR, actor_rol="director")

    def test_director_no_puede_promover_a_director(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("prof_p1", Rol.PROFESOR))
        with pytest.raises(ValueError, match="permiso"):
            svc.cambiar_rol(u.id, Rol.DIRECTOR, actor_rol="director")

    def test_director_puede_cambiar_profesor_a_coordinador(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("prof_p2", Rol.PROFESOR))
        r = svc.cambiar_rol(u.id, Rol.COORDINADOR, actor_rol="director")
        assert r.rol == Rol.COORDINADOR


class TestRbacGestion:
    def test_director_no_puede_desactivar_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("adm2", Rol.ADMIN))
        with pytest.raises(ValueError, match="permiso"):
            svc.desactivar(u.id, actor_rol="director")

    def test_director_puede_desactivar_profesor(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("prof_p3", Rol.PROFESOR))
        r = svc.desactivar(u.id, actor_rol="director")
        assert r.activo is False

    def test_director_puede_reactivar_coordinador(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("coord1", Rol.COORDINADOR))
        svc.desactivar(u.id)
        r = svc.reactivar(u.id, actor_rol="director")
        assert r.activo is True

    def test_director_no_puede_reactivar_director(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("dir2", Rol.DIRECTOR))
        svc.desactivar(u.id)
        with pytest.raises(ValueError, match="permiso"):
            svc.reactivar(u.id, actor_rol="director")


class TestResetearPassword:
    def test_lanza_si_sin_auth(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = svc.crear_usuario(_dto("prof_p4"))
        with pytest.raises(ValueError, match="autenticaci"):
            svc.resetear_password(u.id, "clave123")

    def test_resetea_con_password_dada(self):
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = svc.crear_usuario(_dto("prof_p5"))
        svc.resetear_password(u.id, "claveNueva")
        assert auth._hashes[u.id] == "hash:claveNueva"

    def test_password_vacia_usa_username(self):
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = svc.crear_usuario(_dto("prof_p6"))
        svc.resetear_password(u.id, "")
        assert auth._hashes[u.id] == "hash:prof_p6"

    def test_audita_evento_reset(self):
        from src.domain.models.auditoria import TipoEventoSesion
        auth = FakeAuth()
        audit = FakeAuditoria()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth, auditoria=audit)
        u = svc.crear_usuario(_dto("prof_p7"))
        svc.resetear_password(u.id, "clave")
        tipos = [e.tipo_evento for e in audit.eventos]
        assert TipoEventoSesion.RESETEAR_PASSWORD in tipos

    def test_director_no_puede_resetear_admin(self):
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = svc.crear_usuario(_dto("adm3", Rol.ADMIN))
        with pytest.raises(ValueError, match="permiso"):
            svc.resetear_password(u.id, "x", actor_rol="director")

    def test_director_puede_resetear_profesor(self):
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = svc.crear_usuario(_dto("prof_p8", Rol.PROFESOR))
        svc.resetear_password(u.id, "x", actor_rol="director")
        assert auth._hashes[u.id] == "hash:x"
