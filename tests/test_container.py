"""
Tests del Container — verifican que todo el grafo de dependencias
se puede instanciar sin errores de import ni de configuración.
No son tests de funcionalidad — son tests de configuración.
"""
from __future__ import annotations

import pytest

from container import Container


@pytest.fixture(autouse=True)
def reset_container():
    """Asegurar que cada test parte con un container limpio."""
    Container.reset()
    yield
    Container.reset()


class TestContainer:

    def test_auth_service_instanciable(self):
        svc = Container.auth_service()
        assert svc is not None

    def test_singleton_mismo_objeto(self):
        svc1 = Container.evaluacion_service()
        svc2 = Container.evaluacion_service()
        assert svc1 is svc2

    def test_reset_crea_instancias_nuevas(self):
        svc1 = Container.usuario_service()
        Container.reset()
        svc2 = Container.usuario_service()
        assert svc1 is not svc2

    def test_todos_los_servicios_instanciables(self):
        resultado = Container.diagnostico()
        errores = {k: v for k, v in resultado.items() if v != "OK"}
        assert not errores, f"Servicios con error: {errores}"

    def test_no_hay_imports_circulares(self):
        Container.reset()
        Container.cierre_service()
        Container.informe_service()
        Container.estadisticos_service()

    def test_repos_son_singleton(self):
        r1 = Container.usuario_repo()
        r2 = Container.usuario_repo()
        assert r1 is r2

    def test_auth_service_tiene_repo_inyectado(self):
        from src.infrastructure.auth.bcrypt_auth_service import BcryptAuthService
        svc = Container.auth_service()
        assert isinstance(svc, BcryptAuthService)
        assert svc._repo is not None

    def test_auth_repo_es_mismo_que_usuario_repo(self):
        # auth_service y usuario_service comparten la misma instancia del repo
        auth = Container.auth_service()
        repo = Container.usuario_repo()
        assert auth._repo is repo

    def test_exporter_service_instanciable(self):
        from src.domain.ports.service_ports import IExporterService
        svc = Container.exporter_service()
        assert isinstance(svc, IExporterService)

    def test_notification_service_instanciable(self):
        from src.domain.ports.service_ports import INotificationService
        svc = Container.notification_service()
        assert isinstance(svc, INotificationService)

    def test_cache_no_crece_con_llamadas_repetidas(self):
        for _ in range(5):
            Container.usuario_service()
            Container.evaluacion_service()
        # Solo hay una entrada por componente — el cache no crece
        assert len(Container._cache) == len(set(Container._cache.keys()))
