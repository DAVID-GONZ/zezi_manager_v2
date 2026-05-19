"""
tests/unit/infrastructure/test_context_initializer.py
=======================================================
Tests del ContextInitializer con mocks del Container.
Verifican que la resolución de contexto es correcta por rol.

Se mockea `container.Container` directamente (el módulo que importa
ContextInitializer en runtime) para evitar cualquier acceso real a la BD
ni importaciones de nicegui (SessionContext importa nicegui — los tests
usan un stub del dataclass para evitarlo).
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field

from src.infrastructure.context.context_initializer import ContextInitializer


# ── Stub de SessionContext (sin nicegui) ──────────────────────────────────────

@dataclass
class _FakeSessionContext:
    """
    Reemplaza SessionContext para los tests, evitando importar nicegui.
    Tiene los mismos campos que SessionContext pero sin guardar() real.
    """
    usuario_id:       int
    usuario_nombre:   str
    usuario_rol:      str
    anio_id:          int | None = None
    periodo_id:       int | None = None
    grupo_id:         int | None = None
    asignacion_id:    int | None = None
    anio_nombre:      str = field(default="")
    periodo_nombre:   str = field(default="")
    grupo_nombre:     str = field(default="")
    asignacion_nombre: str = field(default="")

    def guardar(self) -> None:  # no-op en tests
        pass


def _ctx(rol: str, usuario_id: int = 1) -> _FakeSessionContext:
    return _FakeSessionContext(
        usuario_id     = usuario_id,
        usuario_nombre = "Test User",
        usuario_rol    = rol,
    )


# ── Factories de mocks ────────────────────────────────────────────────────────

def _mock_config(anio_id: int = 1, anio: int = 2025, activo: bool = True):
    cfg = MagicMock()
    cfg.id     = anio_id
    cfg.anio   = anio
    cfg.activo = activo
    return cfg


def _mock_periodo(
    pid: int = 1,
    nombre: str = "Periodo 1",
    cerrado: bool = False,
    activo: bool = True,
):
    p = MagicMock()
    p.id     = pid
    p.nombre = nombre
    p.cerrado = cerrado
    p.activo = activo
    return p


def _mock_asignacion_info(
    asig_id: int = 10,
    grupo_id: int = 5,
    grupo_codigo: str = "601",
    asig_nombre: str = "Matemáticas",
    activo: bool = True,
):
    """Simula un objeto AsignacionInfo con los campos que usa ContextInitializer."""
    a = MagicMock()
    a.asignacion_id     = asig_id
    a.grupo_id          = grupo_id
    a.grupo_codigo      = grupo_codigo
    a.asignatura_nombre = asig_nombre
    a.activo            = activo
    return a


def _mock_grupo(gid: int = 5, codigo: str = "601"):
    g = MagicMock()
    g.id     = gid
    g.codigo = codigo
    return g


# ═════════════════════════════════════════════════════════════════════════════
# Tests — Rol PROFESOR
# ═════════════════════════════════════════════════════════════════════════════

class TestContextInitializerProfesor:

    def test_resuelve_anio_periodo_grupo_asignatura(self):
        ctx  = _ctx("profesor")
        asig = _mock_asignacion_info()

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config()
            MockC.periodo_service.return_value.get_activo.return_value       = _mock_periodo()
            MockC.periodo_service.return_value.listar_por_anio.return_value  = []
            MockC.asignacion_service.return_value.listar_por_docente.return_value = [asig]

            resultado = ContextInitializer.inicializar(ctx)

        assert resultado.anio_id          == 1
        assert resultado.anio_nombre      == "2025"
        assert resultado.periodo_id       == 1
        assert resultado.periodo_nombre   == "Periodo 1"
        assert resultado.grupo_id         == 5
        assert resultado.grupo_nombre     == "601"
        assert resultado.asignacion_id    == 10
        assert resultado.asignacion_nombre == "Matemáticas"

    def test_sin_asignaciones_resuelve_solo_periodo(self):
        ctx = _ctx("profesor")

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config()
            MockC.periodo_service.return_value.get_activo.return_value       = _mock_periodo()
            MockC.periodo_service.return_value.listar_por_anio.return_value  = []
            MockC.asignacion_service.return_value.listar_por_docente.return_value = []

            resultado = ContextInitializer.inicializar(ctx)

        assert resultado.anio_id    is not None
        assert resultado.periodo_id is not None
        assert resultado.grupo_id   is None       # sin asignaciones → sin grupo
        assert resultado.asignacion_id is None

    def test_sin_anio_activo_ctx_permanece_vacio(self):
        ctx = _ctx("profesor")

        with patch("container.Container") as MockC:
            # get_activa retorna None → sin año activo
            MockC.configuracion_service.return_value.get_activa.return_value = None

            resultado = ContextInitializer.inicializar(ctx)

        assert resultado.anio_id    is None
        assert resultado.periodo_id is None
        assert resultado.grupo_id   is None

    def test_sin_anio_activo_lanzando_excepcion(self):
        """Si get_activa lanza, _resolver_anio captura y retorna False."""
        ctx = _ctx("profesor")

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.side_effect = \
                RuntimeError("BD caída")

            resultado = ContextInitializer.inicializar(ctx)

        assert resultado.anio_id is None

    def test_multiples_asignaciones_usa_primera_alfabetica(self):
        """Con varias asignaciones, elige la primera al ordenar por (grupo, asig)."""
        ctx  = _ctx("profesor")
        asig1 = _mock_asignacion_info(asig_id=10, grupo_codigo="801", asig_nombre="Química")
        asig2 = _mock_asignacion_info(asig_id=11, grupo_codigo="601", asig_nombre="Matemáticas")
        asig3 = _mock_asignacion_info(asig_id=12, grupo_codigo="601", asig_nombre="Biología")

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config()
            MockC.periodo_service.return_value.get_activo.return_value       = _mock_periodo()
            MockC.periodo_service.return_value.listar_por_anio.return_value  = []
            MockC.asignacion_service.return_value.listar_por_docente.return_value = [
                asig1, asig2, asig3
            ]

            resultado = ContextInitializer.inicializar(ctx)

        # 601-Biología < 601-Matemáticas < 801-Química
        assert resultado.grupo_nombre      == "601"
        assert resultado.asignacion_nombre == "Biología"
        assert resultado.asignacion_id     == 12

    def test_periodo_activo_via_fallback_lista(self):
        """Si get_activo lanza, usa el primer periodo no cerrado de la lista."""
        ctx = _ctx("profesor")
        p_cerrado   = _mock_periodo(pid=1, nombre="P1 cerrado",  cerrado=True)
        p_abierto   = _mock_periodo(pid=2, nombre="P2 abierto",  cerrado=False)

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config()
            # get_activo lanza → debe usar fallback
            MockC.periodo_service.return_value.get_activo.side_effect = \
                Exception("sin periodo activo")
            MockC.periodo_service.return_value.listar_por_anio.return_value = [
                p_cerrado, p_abierto
            ]
            MockC.asignacion_repo.return_value.listar_por_docente.return_value = []

            resultado = ContextInitializer.inicializar(ctx)

        assert resultado.periodo_id   == 2
        assert resultado.periodo_nombre == "P2 abierto"

    def test_listar_por_docente_llamado_con_periodo_y_solo_activas(self):
        """Verifica que listar_por_docente recibe usuario_id y periodo_id."""
        ctx = _ctx("profesor", usuario_id=42)

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config(anio_id=7)
            MockC.periodo_service.return_value.get_activo.return_value       = _mock_periodo(pid=3)
            MockC.periodo_service.return_value.listar_por_anio.return_value  = []
            mock_listar = MockC.asignacion_service.return_value.listar_por_docente
            mock_listar.return_value = []

            ContextInitializer.inicializar(ctx)

        mock_listar.assert_called_once_with(42, 3)


# ═════════════════════════════════════════════════════════════════════════════
# Tests — Rol ADMIN
# ═════════════════════════════════════════════════════════════════════════════

class TestContextInitializerAdmin:

    def test_admin_resuelve_anio_y_periodo_sin_grupo(self):
        ctx = _ctx("admin")

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config()
            MockC.periodo_service.return_value.get_activo.return_value       = _mock_periodo()
            MockC.periodo_service.return_value.listar_por_anio.return_value  = []

            resultado = ContextInitializer.inicializar(ctx)

        # Admin: año y periodo resueltos, sin grupo ni asignatura
        assert resultado.anio_id      is not None
        assert resultado.periodo_id   is not None
        assert resultado.grupo_id     is None
        assert resultado.asignacion_id is None

    def test_admin_sin_anio_no_colapsa(self):
        ctx = _ctx("admin")

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = None

            resultado = ContextInitializer.inicializar(ctx)

        assert resultado.anio_id is None


# ═════════════════════════════════════════════════════════════════════════════
# Tests — Rol DIRECTOR
# ═════════════════════════════════════════════════════════════════════════════

class TestContextInitializerDirector:

    def test_director_resuelve_hasta_grupo_sin_asignatura(self):
        ctx   = _ctx("director")
        grupo = _mock_grupo(gid=5, codigo="601")

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config()
            MockC.periodo_service.return_value.get_activo.return_value       = _mock_periodo()
            MockC.periodo_service.return_value.listar_por_anio.return_value  = []
            MockC.infraestructura_repo.return_value.listar_grupos.return_value = [grupo]

            resultado = ContextInitializer.inicializar(ctx)

        assert resultado.grupo_id      == 5
        assert resultado.grupo_nombre  == "601"
        assert resultado.asignacion_id is None
        assert resultado.asignacion_nombre == ""

    def test_director_sin_grupos_no_colapsa(self):
        ctx = _ctx("director")

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config()
            MockC.periodo_service.return_value.get_activo.return_value       = _mock_periodo()
            MockC.periodo_service.return_value.listar_por_anio.return_value  = []
            MockC.infraestructura_repo.return_value.listar_grupos.return_value = []

            resultado = ContextInitializer.inicializar(ctx)

        assert resultado.grupo_id is None

    def test_director_multiples_grupos_usa_primero_alfabetico(self):
        ctx = _ctx("director")
        g1 = _mock_grupo(gid=1, codigo="1101")
        g2 = _mock_grupo(gid=2, codigo="601")
        g3 = _mock_grupo(gid=3, codigo="801")

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_activa.return_value = _mock_config()
            MockC.periodo_service.return_value.get_activo.return_value       = _mock_periodo()
            MockC.periodo_service.return_value.listar_por_anio.return_value  = []
            MockC.infraestructura_repo.return_value.listar_grupos.return_value = [g1, g2, g3]

            resultado = ContextInitializer.inicializar(ctx)

        # "1101" < "601" < "801" (orden lexicográfico)
        assert resultado.grupo_nombre == "1101"


# ═════════════════════════════════════════════════════════════════════════════
# Tests — contexto_es_valido
# ═════════════════════════════════════════════════════════════════════════════

class TestContextoEsValido:

    def test_contexto_valido_sin_asignacion(self):
        ctx            = _ctx("profesor")
        ctx.anio_id    = 1
        ctx.periodo_id = 1

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_by_id.return_value = \
                _mock_config(activo=True)
            MockC.periodo_repo.return_value.get_by_id.return_value = _mock_periodo()

            assert ContextInitializer.contexto_es_valido(ctx) is True

    def test_contexto_invalido_sin_anio_id(self):
        ctx = _ctx("profesor")
        # anio_id es None por defecto
        assert ContextInitializer.contexto_es_valido(ctx) is False

    def test_contexto_invalido_sin_periodo_id(self):
        ctx         = _ctx("profesor")
        ctx.anio_id = 1
        # periodo_id es None por defecto
        assert ContextInitializer.contexto_es_valido(ctx) is False

    def test_contexto_invalido_cuando_periodo_no_existe(self):
        ctx            = _ctx("profesor")
        ctx.anio_id    = 1
        ctx.periodo_id = 99

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_by_id.return_value = \
                _mock_config(activo=True)
            MockC.periodo_service.return_value.get_by_id.side_effect = ValueError("no existe")

            assert ContextInitializer.contexto_es_valido(ctx) is False

    def test_asignacion_inactiva_invalida_contexto(self):
        ctx               = _ctx("profesor")
        ctx.anio_id       = 1
        ctx.periodo_id    = 1
        ctx.asignacion_id = 10

        asig_inactiva        = MagicMock()
        asig_inactiva.activo = False

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_by_id.return_value = \
                _mock_config(activo=True)
            MockC.periodo_service.return_value.get_by_id.return_value = _mock_periodo()
            MockC.asignacion_service.return_value.get_by_id.return_value = asig_inactiva

            assert ContextInitializer.contexto_es_valido(ctx) is False

    def test_asignacion_activa_contexto_valido(self):
        ctx               = _ctx("profesor")
        ctx.anio_id       = 1
        ctx.periodo_id    = 1
        ctx.asignacion_id = 10

        asig_activa        = MagicMock()
        asig_activa.activo = True

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_by_id.return_value = \
                _mock_config(activo=True)
            MockC.periodo_service.return_value.get_by_id.return_value = _mock_periodo()
            MockC.asignacion_service.return_value.get_by_id.return_value = asig_activa

            assert ContextInitializer.contexto_es_valido(ctx) is True

    def test_excepcion_en_verificacion_retorna_false(self):
        ctx            = _ctx("profesor")
        ctx.anio_id    = 1
        ctx.periodo_id = 1

        with patch("container.Container") as MockC:
            MockC.configuracion_service.return_value.get_by_id.side_effect = \
                RuntimeError("BD caída")

            # No debe propagar la excepción
            assert ContextInitializer.contexto_es_valido(ctx) is False


# ═════════════════════════════════════════════════════════════════════════════
# Tests — refrescar_si_invalido
# ═════════════════════════════════════════════════════════════════════════════

class TestRefrescarSiInvalido:

    def test_no_reinicializa_si_contexto_valido(self):
        ctx            = _ctx("profesor")
        ctx.anio_id    = 1
        ctx.periodo_id = 1
        ctx.anio_nombre = "2025"

        with patch.object(
            ContextInitializer, "contexto_es_valido", return_value=True
        ) as mock_valido, patch.object(
            ContextInitializer, "inicializar"
        ) as mock_init:
            resultado = ContextInitializer.refrescar_si_invalido(ctx)

        mock_valido.assert_called_once_with(ctx)
        mock_init.assert_not_called()
        # El ctx no fue tocado
        assert resultado.anio_nombre == "2025"

    def test_reinicializa_y_guarda_si_contexto_invalido(self):
        ctx = _ctx("profesor")
        ctx.anio_id    = 99    # inválido
        ctx.periodo_id = 99

        ctx_reiniciado = _FakeSessionContext(
            usuario_id     = 1,
            usuario_nombre = "Test User",
            usuario_rol    = "profesor",
            anio_id        = 1,
            periodo_id     = 1,
            anio_nombre    = "2025",
            periodo_nombre = "Periodo 1",
        )

        with patch.object(
            ContextInitializer, "contexto_es_valido", return_value=False
        ), patch.object(
            ContextInitializer, "inicializar", return_value=ctx_reiniciado
        ) as mock_init:
            resultado = ContextInitializer.refrescar_si_invalido(ctx)

        mock_init.assert_called_once()
        assert resultado.anio_id     == 1
        assert resultado.anio_nombre == "2025"
