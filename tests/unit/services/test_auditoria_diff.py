"""
Tests de AuditoriaService: diff_cambio, detalle_cambio, resolver_actores
(obs_09, T4/T5/T6/T7).

Cubre:
  - diff_cambio: CREATE/DELETE/UPDATE, campos sensibles, JSON malformado.
  - detalle_cambio: devuelve None si el cambio no existe; compone DTO completo.
  - resolver_actores: una sola consulta, ids vacíos → {}, repo=None → {}.
"""
from __future__ import annotations

from src.domain.models.auditoria import (
    AccionCambio,
    RegistroCambio,
    TipoCambioCampo,
)
from src.domain.models.usuario import Rol, Usuario
from src.services.auditoria_service import AuditoriaService


class _FakeRepo:
    """Repo de auditoría mínimo para tests."""

    def __init__(self, cambio: RegistroCambio | None = None):
        self._cambio = cambio

    def get_cambio(self, cambio_id: int) -> RegistroCambio | None:
        return self._cambio

    def verificar_cadena_eventos(self, *, completa: bool = False) -> int | None:
        return None

    def verificar_cadena_cambios(self, *, completa: bool = False) -> int | None:
        return None


class _FakeUsuarioRepo:
    """Repo de usuario mínimo con get_varios."""

    def __init__(self, usuarios: list[Usuario] | None = None):
        self._usuarios = {u.id: u for u in (usuarios or []) if u.id is not None}

    def get_by_id(self, usuario_id: int) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    def get_varios(self, ids: set[int]) -> list[Usuario]:
        return [u for uid, u in self._usuarios.items() if uid in ids]


def _svc(cambio: RegistroCambio | None = None, usuarios: list[Usuario] | None = None) -> AuditoriaService:
    usuario_repo = _FakeUsuarioRepo(usuarios) if usuarios is not None else None
    return AuditoriaService(_FakeRepo(cambio), usuario_repo=usuario_repo)


# ---------------------------------------------------------------------------
# Helpers de construcción
# ---------------------------------------------------------------------------

def _cambio_create(datos_nuevos: dict) -> RegistroCambio:
    return RegistroCambio.para_creacion(
        tabla="estudiantes",
        datos_nuevos=datos_nuevos,
        registro_id=1,
    )


def _cambio_delete(datos_anteriores: dict) -> RegistroCambio:
    return RegistroCambio.para_eliminacion(
        tabla="estudiantes",
        datos_anteriores=datos_anteriores,
        registro_id=1,
    )


def _cambio_update(anterior: dict, nuevo: dict) -> RegistroCambio:
    return RegistroCambio.para_actualizacion(
        tabla="estudiantes",
        datos_anteriores=anterior,
        datos_nuevos=nuevo,
        registro_id=1,
    )


# ---------------------------------------------------------------------------
# CREATE → todo ANADIDO
# ---------------------------------------------------------------------------

class TestDiffCreate:
    def test_todos_campos_son_anadidos(self):
        cambio = _cambio_create({"nombre": "Ana", "edad": 10})
        resultado = _svc().diff_cambio(cambio)

        tipos = {c.tipo for c in resultado}
        assert tipos == {TipoCambioCampo.ANADIDO}

    def test_campo_anadido_tiene_solo_valor_nuevo(self):
        cambio = _cambio_create({"nombre": "Ana"})
        resultado = _svc().diff_cambio(cambio)

        assert len(resultado) == 1
        campo = resultado[0]
        assert campo.nombre == "nombre"
        assert campo.valor_anterior is None
        assert campo.valor_nuevo == "Ana"

    def test_campos_en_orden_alfabetico(self):
        cambio = _cambio_create({"z_campo": 1, "a_campo": 2, "m_campo": 3})
        resultado = _svc().diff_cambio(cambio)
        nombres = [c.nombre for c in resultado]
        assert nombres == sorted(nombres)


# ---------------------------------------------------------------------------
# DELETE → todo ELIMINADO
# ---------------------------------------------------------------------------

class TestDiffDelete:
    def test_todos_campos_son_eliminados(self):
        cambio = _cambio_delete({"nombre": "Pedro", "nota": 4.5})
        resultado = _svc().diff_cambio(cambio)

        tipos = {c.tipo for c in resultado}
        assert tipos == {TipoCambioCampo.ELIMINADO}

    def test_campo_eliminado_tiene_solo_valor_anterior(self):
        cambio = _cambio_delete({"nombre": "Pedro"})
        resultado = _svc().diff_cambio(cambio)

        assert len(resultado) == 1
        campo = resultado[0]
        assert campo.valor_anterior == "Pedro"
        assert campo.valor_nuevo is None


# ---------------------------------------------------------------------------
# UPDATE → solo los campos cambiados (omite iguales por defecto)
# ---------------------------------------------------------------------------

class TestDiffUpdate:
    def test_solo_devuelve_campo_cambiado(self):
        """Un campo distinto + dos iguales → solo el distinto."""
        ant = {"nombre": "Ana", "nota": 3.0, "activo": True}
        nue = {"nombre": "Ana", "nota": 4.0, "activo": True}
        cambio = _cambio_update(ant, nue)

        resultado = _svc().diff_cambio(cambio)

        assert len(resultado) == 1
        assert resultado[0].nombre == "nota"
        assert resultado[0].tipo == TipoCambioCampo.MODIFICADO
        assert resultado[0].valor_anterior == "3.0"
        assert resultado[0].valor_nuevo == "4.0"

    def test_incluir_sin_cambio_devuelve_todos(self):
        """Con incluir_sin_cambio=True aparecen también los campos iguales."""
        ant = {"nombre": "Ana", "nota": 3.0}
        nue = {"nombre": "Ana", "nota": 4.0}
        cambio = _cambio_update(ant, nue)

        resultado = _svc().diff_cambio(cambio, incluir_sin_cambio=True)

        tipos = {c.tipo for c in resultado}
        assert TipoCambioCampo.SIN_CAMBIO in tipos
        assert TipoCambioCampo.MODIFICADO in tipos
        assert len(resultado) == 2

    def test_campo_nuevo_en_update_es_anadido(self):
        """Campo que no existía antes → ANADIDO."""
        ant = {"nombre": "Ana"}
        nue = {"nombre": "Ana", "extra": "nuevo"}
        cambio = _cambio_update(ant, nue)

        resultado = _svc().diff_cambio(cambio)
        assert resultado[0].nombre == "extra"
        assert resultado[0].tipo == TipoCambioCampo.ANADIDO

    def test_campo_quitado_en_update_es_eliminado(self):
        """Campo que desaparece → ELIMINADO."""
        ant = {"nombre": "Ana", "campo_viejo": "x"}
        nue = {"nombre": "Ana"}
        cambio = _cambio_update(ant, nue)

        resultado = _svc().diff_cambio(cambio)
        assert resultado[0].nombre == "campo_viejo"
        assert resultado[0].tipo == TipoCambioCampo.ELIMINADO


# ---------------------------------------------------------------------------
# Campos sensibles → oculto=True, valores None (R3)
# ---------------------------------------------------------------------------

class TestDiffCamposSensibles:
    def test_password_hash_oculto(self):
        """password_hash debe aparecer con oculto=True y valores None."""
        ant = {"username": "ana", "password_hash": "viejo_hash"}
        nue = {"username": "ana", "password_hash": "nuevo_hash"}
        cambio = _cambio_update(ant, nue)

        resultado = _svc().diff_cambio(cambio)

        campo_pwd = next((c for c in resultado if c.nombre == "password_hash"), None)
        assert campo_pwd is not None, "password_hash no aparece en el diff"
        assert campo_pwd.oculto is True
        assert campo_pwd.valor_anterior is None
        assert campo_pwd.valor_nuevo is None

    def test_password_oculto(self):
        ant = {"password": "old"}
        nue = {"password": "new"}
        resultado = _svc().diff_cambio(_cambio_update(ant, nue))
        campo = next(c for c in resultado if c.nombre == "password")
        assert campo.oculto is True
        assert campo.valor_anterior is None
        assert campo.valor_nuevo is None

    def test_token_oculto(self):
        ant = {"token": "tok1"}
        nue = {"token": "tok2"}
        resultado = _svc().diff_cambio(_cambio_update(ant, nue))
        campo = next(c for c in resultado if c.nombre == "token")
        assert campo.oculto is True

    def test_campo_no_sensible_no_es_oculto(self):
        cambio = _cambio_update({"nombre": "X"}, {"nombre": "Y"})
        resultado = _svc().diff_cambio(cambio)
        assert not resultado[0].oculto


# ---------------------------------------------------------------------------
# JSON malformado → lista vacía sin excepción
# ---------------------------------------------------------------------------

class TestDiffJsonMalformado:
    def test_json_malformado_devuelve_lista_vacia(self):
        """Si el JSON histórico está corrupto, diff_cambio devuelve [] sin lanzar."""
        # Construir un RegistroCambio con JSON inválido manipulando directamente
        # (bypass de la validación del modelo usando object.__setattr__)
        cambio = RegistroCambio(
            accion=AccionCambio.UPDATE,
            tabla="test",
            registro_id=1,
        )
        # Forzar valor_anterior inválido sin pasar por el validador
        object.__setattr__(cambio, "valor_anterior", "no-es-json-{{{")
        object.__setattr__(cambio, "valor_nuevo", '{"campo": "ok"}')

        resultado = _svc().diff_cambio(cambio)
        assert resultado == []

    def test_ambos_none_devuelve_lista_vacia(self):
        """CREATE sin datos nuevos → lista vacía."""
        cambio = RegistroCambio(
            accion=AccionCambio.CREATE,
            tabla="test",
            registro_id=1,
        )
        resultado = _svc().diff_cambio(cambio)
        assert resultado == []


# ---------------------------------------------------------------------------
# detalle_cambio (T6)
# ---------------------------------------------------------------------------

class TestDetalleCambio:
    def test_devuelve_none_si_no_existe(self):
        """detalle_cambio devuelve None si el cambio no existe en el repo."""
        svc = AuditoriaService(_FakeRepo(cambio=None))
        assert svc.detalle_cambio(999) is None

    def test_compone_dto_completo(self):
        """detalle_cambio compone DetalleCambioDTO con diff, etiqueta y actor."""
        cambio = RegistroCambio.para_actualizacion(
            tabla="usuarios",
            datos_anteriores={"nombre": "Antes"},
            datos_nuevos={"nombre": "Despues"},
            registro_id=1,
            usuario_id=7,
            usuario="profe",
        )
        usuario = Usuario(
            id=7,
            usuario="profe",
            nombre_completo="María Profesora",
            email="profe@escuela.co",
            rol=Rol.PROFESOR,
            activo=True,
        )
        svc = AuditoriaService(_FakeRepo(cambio=cambio), usuario_repo=_FakeUsuarioRepo([usuario]))
        detalle = svc.detalle_cambio(cambio.id or 1)

        assert detalle is not None
        assert detalle.actor_nombre == "María Profesora"
        assert detalle.etiqueta_tabla == "Cuentas de usuario"
        assert len(detalle.campos) == 1
        assert detalle.campos[0].nombre == "nombre"

    def test_fallback_username_si_no_hay_usuario(self):
        """Si el usuario fue borrado, el actor es el username snapshot."""
        cambio = RegistroCambio.para_creacion(
            tabla="estudiantes",
            datos_nuevos={"nombre": "X"},
            registro_id=2,
            usuario_id=99,
            usuario="ex_usuario",
        )
        # Repo de usuarios sin ese usuario
        svc = AuditoriaService(_FakeRepo(cambio=cambio), usuario_repo=_FakeUsuarioRepo([]))
        detalle = svc.detalle_cambio(1)
        assert detalle is not None
        assert detalle.actor_nombre == "ex_usuario"

    def test_fallback_id_si_no_hay_username(self):
        """Si no hay username ni usuario encontrado, el actor es 'Usuario #N'."""
        cambio = RegistroCambio.para_creacion(
            tabla="estudiantes",
            datos_nuevos={"nombre": "X"},
            registro_id=2,
            usuario_id=55,
            usuario=None,
        )
        svc = AuditoriaService(_FakeRepo(cambio=cambio), usuario_repo=_FakeUsuarioRepo([]))
        detalle = svc.detalle_cambio(1)
        assert detalle is not None
        assert detalle.actor_nombre == "Usuario #55"

    def test_sin_usuario_repo_usa_username_snapshot(self):
        """Sin repo de usuarios inyectado, el actor es el username snapshot."""
        cambio = RegistroCambio.para_creacion(
            tabla="estudiantes",
            datos_nuevos={"nombre": "X"},
            registro_id=2,
            usuario_id=10,
            usuario="snap_user",
        )
        svc = AuditoriaService(_FakeRepo(cambio=cambio))  # sin usuario_repo
        detalle = svc.detalle_cambio(1)
        assert detalle is not None
        assert detalle.actor_nombre == "snap_user"


# ---------------------------------------------------------------------------
# resolver_actores (T7)
# ---------------------------------------------------------------------------

class TestResolverActores:
    def test_ids_vacios_devuelve_dict_vacio(self):
        """Sin cambios con usuario_id, el resultado es {}."""
        cambio = RegistroCambio.para_creacion(
            tabla="notas",
            datos_nuevos={"v": 1},
            registro_id=1,
            usuario_id=None,
        )
        svc = AuditoriaService(_FakeRepo(), usuario_repo=_FakeUsuarioRepo([]))
        assert svc.resolver_actores([cambio]) == {}

    def test_sin_repo_devuelve_dict_vacio(self):
        """Sin usuario_repo inyectado, resolver_actores devuelve {}."""
        cambio = RegistroCambio.para_creacion(
            tabla="notas",
            datos_nuevos={"v": 1},
            registro_id=1,
            usuario_id=5,
        )
        svc = AuditoriaService(_FakeRepo())
        assert svc.resolver_actores([cambio]) == {}

    def test_resuelve_actores_en_una_sola_consulta(self):
        """Los actores de la página se resuelven y el mapa es correcto."""
        u1 = Usuario(id=1, usuario="usu1", nombre_completo="Usuario Uno",
                     email="u1@test.co", rol=Rol.PROFESOR, activo=True)
        u2 = Usuario(id=2, usuario="usu2", nombre_completo="Usuario Dos",
                     email="u2@test.co", rol=Rol.COORDINADOR, activo=True)

        c1 = RegistroCambio.para_creacion(tabla="t", datos_nuevos={}, usuario_id=1)
        c2 = RegistroCambio.para_creacion(tabla="t", datos_nuevos={}, usuario_id=2)

        svc = AuditoriaService(_FakeRepo(), usuario_repo=_FakeUsuarioRepo([u1, u2]))
        resultado = svc.resolver_actores([c1, c2])

        assert resultado == {1: "Usuario Uno", 2: "Usuario Dos"}

    def test_usuario_borrado_no_aparece_en_mapa(self):
        """Un usuario_id que no existe en el repo simplemente no aparece en el mapa."""
        u1 = Usuario(id=1, usuario="usu1", nombre_completo="Solo Uno",
                     email="u1@test.co", rol=Rol.PROFESOR, activo=True)

        c1 = RegistroCambio.para_creacion(tabla="t", datos_nuevos={}, usuario_id=1)
        c_borrado = RegistroCambio.para_creacion(tabla="t", datos_nuevos={}, usuario_id=999)

        svc = AuditoriaService(_FakeRepo(), usuario_repo=_FakeUsuarioRepo([u1]))
        resultado = svc.resolver_actores([c1, c_borrado])

        assert 1 in resultado
        assert 999 not in resultado
