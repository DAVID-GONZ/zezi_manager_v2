"""Tests para convivencia_04 — gating de autorización por objeto en las
páginas de Comportamiento y Notas de comportamiento.

Verifican el helper `_autorizado_para_grupo` de ambas páginas: delega en
CatalogoAcademicoService.puede_gestionar_comportamiento_en_grupo pasando
primitivos, retorna False sin grupo y es fail-closed ante excepciones.
"""
from types import SimpleNamespace

import pytest

from src.interface.pages.convivencia import comportamiento, notas_convivencia

PAGINAS = [comportamiento, notas_convivencia]


def _ctx(rol="profesor", uid=5):
    return SimpleNamespace(usuario_rol=rol, usuario_id=uid)


class _FakeCatalogo:
    def __init__(self, resultado=True, boom=False):
        self.resultado = resultado
        self.boom = boom
        self.llamadas = []

    def puede_gestionar_comportamiento_en_grupo(self, rol, uid, grupo_id):
        self.llamadas.append((rol, uid, grupo_id))
        if self.boom:
            raise RuntimeError("fallo de resolución")
        return self.resultado


@pytest.mark.parametrize("modulo", PAGINAS)
def test_sin_grupo_retorna_false_sin_llamar_servicio(modulo, monkeypatch):
    fake = _FakeCatalogo(resultado=True)
    monkeypatch.setattr(modulo.Container, "catalogo_academico_service", lambda: fake)
    assert modulo._autorizado_para_grupo(_ctx(), None) is False
    assert fake.llamadas == []  # no se consulta el servicio sin grupo


@pytest.mark.parametrize("modulo", PAGINAS)
def test_delegacion_con_primitivos(modulo, monkeypatch):
    fake = _FakeCatalogo(resultado=True)
    monkeypatch.setattr(modulo.Container, "catalogo_academico_service", lambda: fake)
    assert modulo._autorizado_para_grupo(_ctx("director", 9), 3) is True
    assert fake.llamadas == [("director", 9, 3)]


@pytest.mark.parametrize("modulo", PAGINAS)
def test_no_autorizado_propaga_false(modulo, monkeypatch):
    fake = _FakeCatalogo(resultado=False)
    monkeypatch.setattr(modulo.Container, "catalogo_academico_service", lambda: fake)
    assert modulo._autorizado_para_grupo(_ctx("profesor", 5), 7) is False


@pytest.mark.parametrize("modulo", PAGINAS)
def test_fail_closed_ante_excepcion(modulo, monkeypatch):
    fake = _FakeCatalogo(boom=True)
    monkeypatch.setattr(modulo.Container, "catalogo_academico_service", lambda: fake)
    assert modulo._autorizado_para_grupo(_ctx(), 3) is False
