"""
Tests de AprovisionamientoInstitucionService (mejora_09a).

Usa MagicMock para IInstitucionRepository y monkeypatch de
Container.usuario_service para no depender de infraestructura real.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.models.institucion import NuevaInstitucionConDirectorDTO
from src.domain.models.usuario import NuevoUsuarioDTO, Rol, Usuario
from src.services.aprovisionamiento_institucion_service import (
    AprovisionamientoInstitucionService,
)


def _dto(**overrides) -> NuevaInstitucionConDirectorDTO:
    datos = {
        "nombre": "Colegio San José",
        "codigo_dane": "111001000001",
        "pais": "Colombia",
        "departamento": "Cundinamarca",
        "municipio": "Bogotá",
        "director_usuario": "director.sj",
        "director_nombre_completo": "María Elena Directora",
        "director_email": "director@sanjose.edu.co",
    }
    datos.update(overrides)
    return NuevaInstitucionConDirectorDTO(**datos)


def _crear_svc_y_repo() -> tuple[AprovisionamientoInstitucionService, MagicMock]:
    repo = MagicMock()
    repo.existe_nombre.return_value = False
    repo.guardar.side_effect = lambda inst: inst.model_copy(update={"id": 42})
    svc = AprovisionamientoInstitucionService(repo)
    return svc, repo


def _patch_usuario_service(monkeypatch, usuario_creado: Usuario) -> MagicMock:
    usuario_service = MagicMock()
    usuario_service.crear_usuario.return_value = usuario_creado
    import container
    monkeypatch.setattr(
        container.Container, "usuario_service", staticmethod(lambda: usuario_service)
    )
    return usuario_service


class TestCrearInstitucionConDirector:

    def test_crear_institucion_con_director_ok(self, monkeypatch):
        svc, _repo = _crear_svc_y_repo()
        director = Usuario(
            id=7, usuario="director.sj", nombre_completo="María Elena Directora",
            rol=Rol.DIRECTOR, institucion_id=42,
        ).model_copy(update={"password_temporal": "Temp1234*"})
        usuario_svc = _patch_usuario_service(monkeypatch, director)

        resultado = svc.crear_institucion_con_director(_dto(), actor_rol="admin")

        assert resultado.institucion.id == 42
        assert resultado.director_usuario == "director.sj"
        assert resultado.password_temporal == "Temp1234*"
        usuario_svc.crear_usuario.assert_called_once()

    def test_flag_inicial_false(self, monkeypatch):
        svc, repo = _crear_svc_y_repo()
        director = Usuario(
            id=7, usuario="director.sj", nombre_completo="María Elena Directora",
            rol=Rol.DIRECTOR, institucion_id=42,
        )
        _patch_usuario_service(monkeypatch, director)

        svc.crear_institucion_con_director(_dto(), actor_rol="admin")

        inst_guardada = repo.guardar.call_args[0][0]
        assert inst_guardada.configuracion_inicial_completa is False

    def test_siembra_defaults_llamada(self, monkeypatch):
        svc, repo = _crear_svc_y_repo()
        director = Usuario(
            id=7, usuario="director.sj", nombre_completo="María Elena Directora",
            rol=Rol.DIRECTOR, institucion_id=42,
        )
        _patch_usuario_service(monkeypatch, director)

        svc.crear_institucion_con_director(_dto(), actor_rol="admin")

        repo.sembrar_defaults_tenant.assert_called_once_with(42)

    def test_nombre_duplicado_rechazado(self, monkeypatch):
        svc, repo = _crear_svc_y_repo()
        repo.existe_nombre.return_value = True
        _patch_usuario_service(monkeypatch, MagicMock())

        with pytest.raises(ValueError, match="Ya existe"):
            svc.crear_institucion_con_director(_dto(), actor_rol="admin")

        repo.guardar.assert_not_called()
        repo.sembrar_defaults_tenant.assert_not_called()

    def test_director_en_tenant_correcto(self, monkeypatch):
        svc, _repo = _crear_svc_y_repo()
        director = Usuario(
            id=7, usuario="director.sj", nombre_completo="María Elena Directora",
            rol=Rol.DIRECTOR, institucion_id=42,
        )
        usuario_svc = _patch_usuario_service(monkeypatch, director)

        svc.crear_institucion_con_director(_dto(), actor_rol="admin")

        dto_pasado: NuevoUsuarioDTO = usuario_svc.crear_usuario.call_args[0][0]
        assert dto_pasado.institucion_id == 42
        assert dto_pasado.rol == Rol.DIRECTOR
        assert usuario_svc.crear_usuario.call_args.kwargs["actor_rol"] == "admin"
