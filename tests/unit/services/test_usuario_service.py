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

    def marcar_debe_cambiar_password(self, uid: int, valor: bool) -> bool:
        u = self._users.get(uid)
        if u is None:
            return False
        self._users[uid] = u.model_copy(update={"debe_cambiar_password": valor})
        return True

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

    def autenticar_usuario(
        self, nombre_usuario: str, password_plain: str
    ):
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


def _crear(svc: UsuarioService, *args, **kwargs) -> Usuario:
    """Atajo: crea y retorna el Usuario (la temporal viaja en .password_temporal)."""
    return svc.crear_usuario(*args, **kwargs)


# ===========================================================================
# Tests
# ===========================================================================

class TestCrearUsuario:
    def test_crea_usuario_nuevo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("prof1"))
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
        u = _crear(svc, _dto("prof1"))
        assert u.id in auth._hashes

    def test_sin_password_genera_temporal_y_flag(self):
        # R-A2: crear sin contraseña → temporal aleatoria fuerte (no el username)
        # + debe_cambiar_password=True, y la temporal viaja en .password_temporal.
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        usuario = svc.crear_usuario(_dto("prof_tmp"))
        temporal = usuario.password_temporal
        assert temporal is not None
        assert temporal != "prof_tmp"
        assert len(temporal) >= 12
        assert usuario.debe_cambiar_password is True
        assert auth._hashes[usuario.id] == f"hash:{temporal}"

    def test_temporal_no_se_serializa_ni_persiste(self):
        # R-A2: el campo efímero NO aparece en model_dump (auditoría/logs).
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=FakeAuth())
        usuario = svc.crear_usuario(_dto("prof_tmp2"))
        assert usuario.password_temporal is not None
        assert "password_temporal" not in usuario.model_dump()

    def test_con_password_explicita_no_fuerza_cambio(self):
        # R-A2: si el admin fija contraseña, no hay temporal ni cambio forzado.
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        dto = NuevoUsuarioDTO(
            usuario="prof_fija", nombre_completo="Profesor Fija",
            rol=Rol.PROFESOR, password="claveDelAdmin1",
        )
        usuario = svc.crear_usuario(dto)
        assert usuario.password_temporal is None
        assert usuario.debe_cambiar_password is False
        assert auth._hashes[usuario.id] == "hash:claveDelAdmin1"

    def test_password_explicita_debil_es_rechazada(self):
        # M4: contraseña explícita al crear debe cumplir la política de dominio.
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=FakeAuth())
        dto = NuevoUsuarioDTO(
            usuario="prof_debil", nombre_completo="Prof Debil",
            rol=Rol.PROFESOR, password="abcdefgh",  # sin dígito
        )
        with pytest.raises(ValueError):
            svc.crear_usuario(dto)

    def test_temporal_generada_cumple_la_policy(self):
        # T5: N temporales generadas cumplen la política por construcción.
        from src.domain.policies.password_policy import errores_password
        for _ in range(200):
            temp = UsuarioService._generar_password_temporal()
            assert errores_password(temp) == []


class TestDesactivar:
    def test_desactiva_usuario_activo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto())
        resultado = svc.desactivar(u.id)
        assert resultado.activo is False

    def test_lanza_si_ya_inactivo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto())
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
            svc.cambiar_password(1, "vieja", "Clave2026")

    def test_cambia_password_correctamente(self):
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=FakeAuth(pass_ok=True))
        svc.cambiar_password(1, "vieja", "Clave2026")  # no lanza

    def test_cambiar_password_limpia_flag_forzado(self):
        # R-A2: cuando el dueño cambia su contraseña, se limpia el flag.
        repo = FakeUsuarioRepo()
        auth = FakeAuth(pass_ok=True)
        svc = UsuarioService(repo, auth_service=auth)
        usuario = svc.crear_usuario(_dto("prof_flag"))  # nace forzado
        assert repo.get_by_id(usuario.id).debe_cambiar_password is True
        svc.cambiar_password(usuario.id, "temporal", "nuevaClave1")
        assert repo.get_by_id(usuario.id).debe_cambiar_password is False

    # M4 — enforcement de la política en el servidor (seguridad_02).
    def test_rechaza_password_solo_letras(self):
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=FakeAuth(pass_ok=True))
        with pytest.raises(ValueError):
            svc.cambiar_password(1, "vieja", "abcdefgh")

    def test_rechaza_password_solo_digitos(self):
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=FakeAuth(pass_ok=True))
        with pytest.raises(ValueError):
            svc.cambiar_password(1, "vieja", "1234567")

    def test_rechaza_password_igual_al_username(self):
        repo = FakeUsuarioRepo()
        auth = FakeAuth(pass_ok=True)
        svc = UsuarioService(repo, auth_service=auth)
        u = svc.crear_usuario(_dto("juan2026"))
        with pytest.raises(ValueError):
            svc.cambiar_password(u.id, "vieja", "juan2026")

    def test_acepta_password_que_cumple_policy(self):
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=FakeAuth(pass_ok=True))
        svc.cambiar_password(1, "vieja", "Clave2026")  # no lanza


class TestCambiarRol:
    def test_cambia_rol_de_usuario_activo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto())
        resultado = svc.cambiar_rol(u.id, Rol.COORDINADOR)
        assert resultado.rol == Rol.COORDINADOR

    def test_lanza_si_usuario_inactivo(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto())
        svc.desactivar(u.id)
        with pytest.raises(ValueError, match="desactivado"):
            svc.cambiar_rol(u.id, Rol.DIRECTOR)


# ===========================================================================
# RBAC — política de roles en el servicio (paso_23, T1)
# ===========================================================================

class TestRbacCrear:
    def test_admin_puede_crear_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("nuevo_admin", Rol.ADMIN), actor_rol="admin")
        assert u.rol == Rol.ADMIN

    def test_admin_puede_crear_director(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("nuevo_dir", Rol.DIRECTOR), actor_rol="admin")
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
        u = _crear(svc, _dto("prof_x", Rol.PROFESOR), actor_rol="director")
        assert u.rol == Rol.PROFESOR

    def test_sin_actor_rol_no_hay_enforcement(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("libre", Rol.ADMIN))  # actor_rol=None
        assert u.rol == Rol.ADMIN


class TestRbacCambiarRol:
    def test_admin_puede_promover_a_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("dir1", Rol.DIRECTOR))
        r = svc.cambiar_rol(u.id, Rol.ADMIN, actor_rol="admin")
        assert r.rol == Rol.ADMIN

    def test_director_no_puede_cambiar_rol_de_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("adm1", Rol.ADMIN))
        with pytest.raises(ValueError, match="permiso"):
            svc.cambiar_rol(u.id, Rol.COORDINADOR, actor_rol="director")

    def test_director_no_puede_promover_a_director(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("prof_p1", Rol.PROFESOR))
        with pytest.raises(ValueError, match="permiso"):
            svc.cambiar_rol(u.id, Rol.DIRECTOR, actor_rol="director")

    def test_director_puede_cambiar_profesor_a_coordinador(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("prof_p2", Rol.PROFESOR))
        r = svc.cambiar_rol(u.id, Rol.COORDINADOR, actor_rol="director")
        assert r.rol == Rol.COORDINADOR


class TestRbacGestion:
    def test_director_no_puede_desactivar_admin(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("adm2", Rol.ADMIN))
        with pytest.raises(ValueError, match="permiso"):
            svc.desactivar(u.id, actor_rol="director")

    def test_director_puede_desactivar_profesor(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("prof_p3", Rol.PROFESOR))
        r = svc.desactivar(u.id, actor_rol="director")
        assert r.activo is False

    def test_director_puede_reactivar_coordinador(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("coord1", Rol.COORDINADOR))
        svc.desactivar(u.id)
        r = svc.reactivar(u.id, actor_rol="director")
        assert r.activo is True

    def test_director_no_puede_reactivar_director(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("dir2", Rol.DIRECTOR))
        svc.desactivar(u.id)
        with pytest.raises(ValueError, match="permiso"):
            svc.reactivar(u.id, actor_rol="director")


class TestResetearPassword:
    def test_lanza_si_sin_auth(self):
        svc = UsuarioService(FakeUsuarioRepo())
        u = _crear(svc, _dto("prof_p4"))
        with pytest.raises(ValueError, match="autenticaci"):
            svc.resetear_password(u.id, "clave123")

    def test_resetea_con_password_dada(self):
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = _crear(svc, _dto("prof_p5"))
        svc.resetear_password(u.id, "claveNueva1")
        assert auth._hashes[u.id] == "hash:claveNueva1"

    def test_resetea_rechaza_password_explicita_debil(self):
        # M4: una contraseña explícita en el reset debe cumplir la política.
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = _crear(svc, _dto("prof_p5b"))
        with pytest.raises(ValueError):
            svc.resetear_password(u.id, "abcdefgh")  # sin dígito

    def test_password_vacia_genera_temporal_no_username(self):
        # R-A2: un reset sin contraseña explícita NO usa el username (predecible);
        # genera una temporal aleatoria fuerte y la retorna.
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = _crear(svc, _dto("prof_p6"))
        temporal = svc.resetear_password(u.id, "")
        assert temporal is not None
        assert temporal != "prof_p6"
        assert len(temporal) >= 12
        assert auth._hashes[u.id] == f"hash:{temporal}"

    def test_reset_con_password_dada_no_retorna_temporal(self):
        # R-A2: con contraseña explícita no hay temporal que comunicar.
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = _crear(svc, _dto("prof_p6b"))
        temporal = svc.resetear_password(u.id, "claveExplicita1")
        assert temporal is None

    def test_reset_marca_debe_cambiar_password(self):
        # R-A2: tras un reset administrativo el dueño debe re-elegir.
        repo = FakeUsuarioRepo()
        auth = FakeAuth()
        svc = UsuarioService(repo, auth_service=auth)
        u = _crear(svc, _dto("prof_p6c"))
        svc.resetear_password(u.id, "claveExplicita1")
        assert repo.get_by_id(u.id).debe_cambiar_password is True

    def test_audita_evento_reset(self):
        from src.domain.models.auditoria import TipoEventoSesion
        auth = FakeAuth()
        audit = FakeAuditoria()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth, auditoria=audit)
        u = _crear(svc, _dto("prof_p7"))
        svc.resetear_password(u.id, "Clave2026")
        tipos = [e.tipo_evento for e in audit.eventos]
        assert TipoEventoSesion.RESETEAR_PASSWORD in tipos

    def test_director_no_puede_resetear_admin(self):
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = _crear(svc, _dto("adm3", Rol.ADMIN))
        with pytest.raises(ValueError, match="permiso"):
            svc.resetear_password(u.id, "x", actor_rol="director")

    def test_director_puede_resetear_profesor(self):
        auth = FakeAuth()
        svc = UsuarioService(FakeUsuarioRepo(), auth_service=auth)
        u = _crear(svc, _dto("prof_p8", Rol.PROFESOR))
        svc.resetear_password(u.id, "Clave2026", actor_rol="director")
        assert auth._hashes[u.id] == "hash:Clave2026"


# ===========================================================================
# Auto-scope por institución desde el contextvar (frente C — paso_28)
# ===========================================================================

class _SpyResumenRepo(FakeUsuarioRepo):
    """Captura el FiltroUsuariosDTO con que se invoca listar_resumenes."""

    def __init__(self):
        super().__init__()
        self.ultimo_filtro: FiltroUsuariosDTO | None = None

    def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]:
        self.ultimo_filtro = filtro
        return []


class TestAutoScopeInstitucion:
    @pytest.fixture(autouse=True)
    def _reset_scope(self):
        from src.services.contexto_tenant import activar_institucion
        activar_institucion(None)
        yield
        activar_institucion(None)

    def test_listar_resumenes_auto_scopea_director(self):
        from src.services.contexto_tenant import usar_institucion

        repo = _SpyResumenRepo()
        svc = UsuarioService(repo)
        with usar_institucion(7):  # sesión de director scopeada a la institución 7
            svc.listar_resumenes(FiltroUsuariosDTO())
        assert repo.ultimo_filtro.institucion_id == 7

    def test_listar_resumenes_no_filtra_admin(self):
        repo = _SpyResumenRepo()
        svc = UsuarioService(repo)
        # Sin scope (admin → contextvar None): no se inyecta institucion_id.
        svc.listar_resumenes(FiltroUsuariosDTO())
        assert repo.ultimo_filtro.institucion_id is None

    def test_filtro_explicito_admin_no_se_pisa(self):
        from src.services.contexto_tenant import usar_institucion

        repo = _SpyResumenRepo()
        svc = UsuarioService(repo)
        # Aunque hubiese scope, un institucion_id explícito manda.
        with usar_institucion(7):
            svc.listar_resumenes(FiltroUsuariosDTO(institucion_id=3))
        assert repo.ultimo_filtro.institucion_id == 3

    def test_solo_activos_se_conserva_al_auto_scopear(self):
        from src.services.contexto_tenant import usar_institucion

        repo = _SpyResumenRepo()
        svc = UsuarioService(repo)
        with usar_institucion(7):
            svc.listar_resumenes(FiltroUsuariosDTO(solo_activos=False))
        assert repo.ultimo_filtro.institucion_id == 7
        assert repo.ultimo_filtro.solo_activos is False

    def test_listar_para_ver_como_auto_scopea(self):
        from src.services.contexto_tenant import usar_institucion

        repo = _SpyResumenRepo()
        svc = UsuarioService(repo)
        with usar_institucion(7):
            svc.listar_para_ver_como()
        assert repo.ultimo_filtro.institucion_id == 7
        assert repo.ultimo_filtro.solo_activos is True
