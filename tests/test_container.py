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


class TestEngineFactory:
    """Tests de backend_05_engine_factory (R1–R12)."""

    @pytest.fixture(autouse=True)
    def reset(self):
        Container.reset()
        yield
        Container.reset()

    def test_engine_sqlite_por_defecto(self, monkeypatch):
        # R1, R2, R4
        monkeypatch.delenv("DB_BACKEND", raising=False)
        engine = Container.engine()
        assert "sqlite" in str(engine.url)

    def test_engine_es_singleton(self):
        # R7
        e1 = Container.engine()
        e2 = Container.engine()
        assert e1 is e2

    def test_connection_context_manager(self):
        # R8
        from sqlalchemy import text
        with Container.connection() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1

    def test_sqlite_pragmas_aplicados(self):
        # R5, R6
        from sqlalchemy import text
        with Container.connection() as conn:
            jm = conn.execute(text("PRAGMA journal_mode")).scalar()
            fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert jm.lower() == "wal"
        assert fk == 1

    def test_connection_py_sigue_funcionando(self):
        # R10
        from src.infrastructure.db.connection import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1

    def test_config_documenta_db_backend_y_url(self):
        # R12
        from config import DATABASE_URL, DB_BACKEND, settings
        assert DB_BACKEND == "sqlite"
        assert isinstance(DATABASE_URL, str)
        assert hasattr(settings, "DB_BACKEND")
        assert hasattr(settings, "DATABASE_URL")
