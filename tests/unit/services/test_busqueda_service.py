"""Tests unitarios para BusquedaService.

BusquedaService orquesta la búsqueda global cross-entidad con scoping por rol.
No accede a repos: delega en 4 servicios inyectados como providers. Aquí los
sustituimos por stubs que devuelven listas fijas, de modo que el test aísla la
lógica propia del servicio: umbral de término, límites/paginación, mapeo de
resultados y —lo crítico— el gating de entidades por rol (RBAC).

Reparto de entidades por rol (ver docstring del servicio):
  admin       → estudiante + usuario + grupo + asignatura (cross-tenant)
  director    → estudiante + usuario + grupo + asignatura
  coordinador → estudiante + grupo + asignatura   (SIN usuarios)
  profesor    → estudiante + grupo                 (SIN usuarios ni asignaturas),
                además restringido a sus grupos asignados
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.domain.models.busqueda import TipoResultadoBusqueda
from src.domain.models.usuario import Rol
from src.services.busqueda_service import BusquedaService, tipos_buscables

T = TipoResultadoBusqueda


# ===========================================================================
# tipos_buscables — RBAC de tipos (fuente única, compartida con la UI)
# ===========================================================================

@pytest.mark.parametrize(
    "rol,esperado",
    [
        (Rol.ADMIN, [T.ESTUDIANTE, T.USUARIO, T.GRUPO, T.ASIGNATURA]),
        (Rol.DIRECTOR, [T.ESTUDIANTE, T.USUARIO, T.GRUPO, T.ASIGNATURA]),
        (Rol.COORDINADOR, [T.ESTUDIANTE, T.GRUPO, T.ASIGNATURA]),
        (Rol.PROFESOR, [T.ESTUDIANTE, T.GRUPO]),
    ],
)
def test_tipos_buscables_por_rol(rol, esperado):
    assert tipos_buscables(rol) == esperado


def test_tipos_buscables_orden_estable():
    # ESTUDIANTE siempre primero, ASIGNATURA siempre al final cuando aplica.
    tipos = tipos_buscables(Rol.ADMIN)
    assert tipos[0] == T.ESTUDIANTE
    assert tipos[-1] == T.ASIGNATURA

# ===========================================================================
# Stubs de entidades y de servicios inyectados
# ===========================================================================


def _est(eid, nombre="Ana Pérez", doc_display="TI 123", numero="123"):
    return SimpleNamespace(
        id=eid, nombre_completo=nombre, documento_display=doc_display, numero_documento=numero
    )


def _usr(uid, nombre="Juan Ruiz", rol=Rol.PROFESOR, usuario="juanr"):
    return SimpleNamespace(id=uid, nombre_completo=nombre, rol=rol, usuario=usuario)


def _grupo(gid, codigo="6A", nombre="Sexto A", grado=6):
    return SimpleNamespace(id=gid, codigo=codigo, nombre=nombre, grado=grado)


def _asig(aid, nombre="Matemáticas", codigo="MAT"):
    return SimpleNamespace(id=aid, nombre=nombre, codigo=codigo)


class _FakeEstudianteSvc:
    def __init__(self, estudiantes):
        self._e = list(estudiantes)
        self.ultimo_filtro = None

    def listar_filtrado(self, filtro):
        self.ultimo_filtro = filtro
        return self._e


class _FakeUsuarioSvc:
    def __init__(self, usuarios):
        self._u = list(usuarios)
        self.llamado = False

    def listar_filtrado(self, filtro):
        self.llamado = True
        return self._u


class _FakeCatalogoSvc:
    def __init__(self, grupos=(), asignaturas=()):
        self._g = list(grupos)
        self._a = list(asignaturas)

    def listar_grupos(self):
        return self._g

    def listar_asignaturas(self):
        return self._a


class _FakeAsignacionSvc:
    def __init__(self, asignaciones=()):
        self._a = list(asignaciones)
        self.usuario_id = None

    def listar_por_docente(self, usuario_id):
        self.usuario_id = usuario_id
        return self._a


def _make(*, est=(), usr=(), grupos=(), asigs=(), asignaciones=()):
    e = _FakeEstudianteSvc(est)
    u = _FakeUsuarioSvc(usr)
    c = _FakeCatalogoSvc(grupos, asigs)
    a = _FakeAsignacionSvc(asignaciones)
    svc = BusquedaService(lambda: e, lambda: u, lambda: c, lambda: a)
    return svc, e, u, c, a


# ===========================================================================
# Umbral de término
# ===========================================================================


class TestUmbralTermino:
    def test_termino_corto_no_dispara_busqueda(self):
        svc, e, u, _, _ = _make(est=[_est(1)], usr=[_usr(1)])
        res = svc.buscar_rapido("a", rol=Rol.ADMIN, usuario_id=1)
        assert res.resultados == []
        assert res.total_por_tipo == {}
        # No debió consultar ningún servicio subyacente.
        assert e.ultimo_filtro is None
        assert u.llamado is False

    def test_termino_vacio_tras_strip_no_busca(self):
        svc, e, _, _, _ = _make(est=[_est(1)])
        res = svc.buscar_rapido("   ", rol=Rol.ADMIN, usuario_id=1)
        assert res.resultados == []
        assert e.ultimo_filtro is None

    def test_termino_se_normaliza_con_strip(self):
        svc, _, _, _, _ = _make(est=[_est(1)])
        res = svc.buscar_rapido("  ab  ", rol=Rol.ADMIN, usuario_id=1)
        assert res.termino == "ab"

    def test_completo_termino_corto_devuelve_vacio(self):
        svc, e, _, _, _ = _make(est=[_est(1)])
        res = svc.buscar_completo("x", rol=Rol.ADMIN, usuario_id=1)
        assert res.resultados == []
        assert e.ultimo_filtro is None


# ===========================================================================
# RBAC — qué entidades ve cada rol
# ===========================================================================


class TestScopingPorRol:
    def _svc_lleno(self):
        return _make(
            est=[_est(1)],
            usr=[_usr(1)],
            grupos=[_grupo(10, codigo="AB1", nombre="Grupo AB")],
            asigs=[_asig(1, nombre="Ábaco", codigo="AB")],
        )

    def test_admin_ve_las_cuatro_entidades(self):
        svc, _, u, _, _ = self._svc_lleno()
        res = svc.buscar_rapido("ab", rol=Rol.ADMIN, usuario_id=1)
        assert set(res.total_por_tipo) == {"estudiante", "usuario", "grupo", "asignatura"}
        assert u.llamado is True

    def test_director_ve_usuarios(self):
        svc, _, u, _, _ = self._svc_lleno()
        res = svc.buscar_rapido("ab", rol=Rol.DIRECTOR, usuario_id=1)
        assert "usuario" in res.total_por_tipo
        assert u.llamado is True

    def test_coordinador_no_ve_usuarios_pero_si_asignaturas(self):
        svc, _, u, _, _ = self._svc_lleno()
        res = svc.buscar_rapido("ab", rol=Rol.COORDINADOR, usuario_id=1)
        assert "usuario" not in res.total_por_tipo
        assert "asignatura" in res.total_por_tipo
        assert u.llamado is False

    def test_profesor_solo_estudiantes_y_grupos(self):
        svc, _, u, _, _ = self._svc_lleno()
        res = svc.buscar_rapido("ab", rol=Rol.PROFESOR, usuario_id=1)
        assert set(res.total_por_tipo) == {"estudiante", "grupo"}
        assert u.llamado is False


# ===========================================================================
# Profesor — restricción a grupos asignados
# ===========================================================================


class TestProfesorScoping:
    def test_profesor_restringe_grupos_a_los_asignados(self):
        # Asignado al grupo 10; el 20 coincide por texto pero NO es suyo.
        svc, _, _, _, asig = _make(
            grupos=[_grupo(10, codigo="GX1"), _grupo(20, codigo="GX2")],
            asignaciones=[SimpleNamespace(grupo_id=10)],
        )
        res = svc.buscar_rapido("gx", rol=Rol.PROFESOR, usuario_id=7)
        grupos = [r for r in res.resultados if r.tipo == TipoResultadoBusqueda.GRUPO]
        assert [g.id for g in grupos] == [10]
        assert asig.usuario_id == 7

    def test_profesor_propaga_grupos_al_filtro_de_estudiantes(self):
        svc, e, _, _, _ = _make(
            est=[_est(1)],
            asignaciones=[SimpleNamespace(grupo_id=10), SimpleNamespace(grupo_id=10)],
        )
        svc.buscar_rapido("ab", rol=Rol.PROFESOR, usuario_id=7)
        # El filtro de estudiantes recibió los grupos del docente (deduplicados).
        assert getattr(e.ultimo_filtro, "grupos_ids", None) == [10]

    def test_profesor_sin_asignaciones_no_devuelve_grupos(self):
        svc, e, _, _, _ = _make(
            est=[_est(1)],
            grupos=[_grupo(10, codigo="GX1")],
            asignaciones=[],
        )
        res = svc.buscar_rapido("gx", rol=Rol.PROFESOR, usuario_id=7)
        grupos = [r for r in res.resultados if r.tipo == TipoResultadoBusqueda.GRUPO]
        assert grupos == []
        # Y el filtro de estudiantes quedó restringido a lista vacía.
        assert getattr(e.ultimo_filtro, "grupos_ids", None) == []


# ===========================================================================
# Filtrado en Python de grupos y asignaturas por término
# ===========================================================================


class TestFiltradoTexto:
    def test_grupos_filtran_por_codigo_o_nombre(self):
        svc, _, _, _, _ = _make(
            grupos=[
                _grupo(1, codigo="6A", nombre="Sexto A"),
                _grupo(2, codigo="7B", nombre="Séptimo B"),
            ],
        )
        res = svc.buscar_rapido("6a", rol=Rol.DIRECTOR, usuario_id=1)
        grupos = [r for r in res.resultados if r.tipo == TipoResultadoBusqueda.GRUPO]
        assert [g.id for g in grupos] == [1]

    def test_asignaturas_filtran_por_nombre(self):
        svc, _, _, _, _ = _make(
            asigs=[_asig(1, nombre="Matemáticas", codigo="MAT"), _asig(2, nombre="Lengua")],
        )
        res = svc.buscar_rapido("mate", rol=Rol.DIRECTOR, usuario_id=1)
        asigs = [r for r in res.resultados if r.tipo == TipoResultadoBusqueda.ASIGNATURA]
        assert [a.id for a in asigs] == [1]


# ===========================================================================
# Límite/paginación y mapeo de resultados
# ===========================================================================


class TestLimitesYPaginacion:
    def test_rapido_limita_por_tipo_y_marca_limitado(self):
        svc, _, _, _, _ = _make(est=[_est(i) for i in range(1, 8)])  # 7 estudiantes
        res = svc.buscar_rapido("ab", rol=Rol.DIRECTOR, usuario_id=1, limite_por_tipo=5)
        vistos = [r for r in res.resultados if r.tipo == TipoResultadoBusqueda.ESTUDIANTE]
        assert len(vistos) == 5
        assert res.total_por_tipo["estudiante"] == 7
        assert res.limitado is True

    def test_rapido_no_marca_limitado_si_cabe(self):
        svc, _, _, _, _ = _make(est=[_est(1), _est(2)])
        res = svc.buscar_rapido("ab", rol=Rol.DIRECTOR, usuario_id=1, limite_por_tipo=5)
        assert res.limitado is False

    def test_completo_pagina_resultados(self):
        svc, _, _, _, _ = _make(est=[_est(i) for i in range(1, 26)])  # 25 estudiantes
        p1 = svc.buscar_completo("ab", rol=Rol.PROFESOR, usuario_id=1, pagina=1, por_pagina=20)
        p2 = svc.buscar_completo("ab", rol=Rol.PROFESOR, usuario_id=1, pagina=2, por_pagina=20)
        assert len(p1.resultados) == 20
        assert p1.limitado is True
        assert len(p2.resultados) == 5
        assert p2.limitado is False

    def test_completo_filtro_por_tipo_no_altera_conteos(self):
        svc, _, _, _, _ = _make(
            est=[_est(1)],
            grupos=[_grupo(10, codigo="AB", nombre="AB")],
        )
        res = svc.buscar_completo(
            "ab", rol=Rol.DIRECTOR, usuario_id=1, tipo_filtro=TipoResultadoBusqueda.GRUPO
        )
        # Solo grupos en la página, pero el recuento total mantiene ambas entidades.
        assert {r.tipo for r in res.resultados} == {TipoResultadoBusqueda.GRUPO}
        assert res.total_por_tipo.get("estudiante") == 1

    def test_mapeo_estudiante_produce_deeplink_por_documento(self):
        svc, _, _, _, _ = _make(est=[_est(1, nombre="Ana Pérez", numero="9999")])
        res = svc.buscar_rapido("ab", rol=Rol.DIRECTOR, usuario_id=1)
        est = next(r for r in res.resultados if r.tipo == TipoResultadoBusqueda.ESTUDIANTE)
        assert est.titulo == "Ana Pérez"
        assert est.ruta == "/estudiantes?busqueda=9999"
        assert est.icono  # icono no vacío
