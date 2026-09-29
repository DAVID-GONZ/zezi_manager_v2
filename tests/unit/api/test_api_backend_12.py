"""
Tests unitarios para los endpoints CRUD (backend_12).

Mockean Container para ejecutar sin base de datos.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import settings
from src.api.router import api_router, docs_router
from src.infrastructure.auth.jwt_handler import JWTHandler

# =========================================================================
# Fixtures de aplicacion y tokens
# =========================================================================


@pytest.fixture
def app():
    _app = FastAPI()
    _app.include_router(api_router)
    _app.include_router(docs_router)
    return _app


def _token(rol: str = "admin", usuario_id: int = 1, institucion_id: int = 1) -> str:
    return JWTHandler(
        secret=settings.JWT_SECRET,
        expiracion_horas=int(settings.JWT_EXPIRE_MINUTES / 60),
    ).crear_token(
        {
            "usuario_id": usuario_id,
            "username": "testuser",
            "rol": rol,
            "institucion_id": institucion_id,
        }
    )


def _headers(rol: str = "admin") -> dict:
    return {"Authorization": f"Bearer {_token(rol)}"}


# =========================================================================
# Tests — Usuarios
# =========================================================================


class TestUsuariosEndpoints:
    def test_listar_usuarios_requiere_auth(self, app):
        client = TestClient(app)
        resp = client.get("/api/v1/usuarios")
        # Sin token: 403 (no bearer scheme) o 401
        assert resp.status_code in (401, 403)

    def test_listar_usuarios_ok(self, app):
        from src.domain.models.usuario import Rol, Usuario

        mock_svc = MagicMock()
        mock_svc.listar_filtrado.return_value = [
            Usuario(
                id=1,
                usuario="prof1",
                nombre_completo="Profesor Uno",
                rol=Rol.PROFESOR,
                activo=True,
                institucion_id=1,
            )
        ]
        with patch("src.api.routes.usuarios.Container") as mock_c:
            mock_c.usuario_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get("/api/v1/usuarios", headers=_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["usuario"] == "prof1"

    def test_obtener_usuario_ok(self, app):
        from src.domain.models.usuario import Rol, Usuario

        mock_svc = MagicMock()
        mock_svc.get_by_id.return_value = Usuario(
            id=5,
            usuario="dir1",
            nombre_completo="Director Uno",
            rol=Rol.DIRECTOR,
            activo=True,
            institucion_id=1,
        )
        with patch("src.api.routes.usuarios.Container") as mock_c:
            mock_c.usuario_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get("/api/v1/usuarios/5", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == 5

    def test_crear_usuario_403_sin_admin(self, app):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/usuarios",
            json={
                "usuario": "nuevo",
                "nombre_completo": "Nuevo Usuario",
                "rol": "profesor",
            },
            headers=_headers("profesor"),
        )
        assert resp.status_code == 403


# =========================================================================
# Tests — Estudiantes
# =========================================================================


class TestEstudiantesEndpoints:
    def test_listar_estudiantes_ok(self, app):
        from src.domain.models.estudiante import EstadoMatricula, Estudiante, TipoDocumento

        mock_svc = MagicMock()
        mock_svc.listar_filtrado.return_value = [
            Estudiante(
                id=10,
                tipo_documento=TipoDocumento.TI,
                numero_documento="123456",
                nombre="Juan",
                apellido="Garcia",
                estado_matricula=EstadoMatricula.ACTIVO,
                institucion_id=1,
            )
        ]
        with patch("src.api.routes.estudiantes.Container") as mock_c:
            mock_c.estudiante_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get("/api/v1/estudiantes", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_obtener_estudiante_ok(self, app):
        from src.domain.models.estudiante import EstadoMatricula, Estudiante, TipoDocumento

        mock_svc = MagicMock()
        mock_svc.get_by_id.return_value = Estudiante(
            id=10,
            tipo_documento=TipoDocumento.TI,
            numero_documento="123456",
            nombre="Juan",
            apellido="Garcia",
            estado_matricula=EstadoMatricula.ACTIVO,
            institucion_id=1,
        )
        with patch("src.api.routes.estudiantes.Container") as mock_c:
            mock_c.estudiante_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get("/api/v1/estudiantes/10", headers=_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == 10


# =========================================================================
# Tests — Contexto
# =========================================================================


class TestContextoEndpoints:
    def test_listar_grupos_ok(self, app):
        mock_svc = MagicMock()
        grupo = MagicMock()
        grupo.id = 1
        grupo.nombre = "601"
        grupo.grado = 6
        grupo.codigo = "601"
        grupo.institucion_id = 1
        mock_svc.listar_grupos.return_value = [grupo]
        with patch("src.api.routes.contexto.Container") as mock_c:
            mock_c.catalogo_academico_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get("/api/v1/contexto/grupos", headers=_headers())
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_listar_periodos_ok(self, app):
        mock_svc = MagicMock()
        periodo = MagicMock()
        periodo.id = 1
        periodo.nombre = "Periodo 1"
        periodo.numero = 1
        periodo.anio_id = 1
        periodo.activo = True
        mock_svc.listar_por_anio.return_value = [periodo]
        with patch("src.api.routes.contexto.Container") as mock_c:
            mock_c.periodo_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get("/api/v1/contexto/periodos?anio_id=1", headers=_headers())
        assert resp.status_code == 200


# =========================================================================
# Tests — Asistencia
# =========================================================================


class TestAsistenciaEndpoints:
    def test_estados_grupo_ok(self, app):
        mock_svc = MagicMock()
        mock_svc.estados_por_grupo_y_fecha.return_value = {
            1: {"estado": "P", "observacion": ""}
        }
        with patch("src.api.routes.asistencia.Container") as mock_c:
            mock_c.asistencia_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get(
                "/api/v1/asistencia/estados?grupo_id=1&asignacion_id=1&fecha=2026-03-01",
                headers=_headers(),
            )
        assert resp.status_code == 200

    def test_resumen_grupo_ok(self, app):
        from src.domain.models.asistencia import ResumenAsistenciaDTO

        mock_svc = MagicMock()
        mock_svc.resumen_grupo.return_value = [
            ResumenAsistenciaDTO(estudiante_id=1)
        ]
        with patch("src.api.routes.asistencia.Container") as mock_c:
            mock_c.asistencia_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get(
                "/api/v1/asistencia/resumen-grupo?grupo_id=1&asignacion_id=1&periodo_id=1",
                headers=_headers(),
            )
        assert resp.status_code == 200


# =========================================================================
# Tests — Auditoria (requiere admin)
# =========================================================================


class TestAuditoriaEndpoints:
    def test_eventos_requiere_admin(self, app):
        client = TestClient(app)
        resp = client.get("/api/v1/auditoria/eventos", headers=_headers("profesor"))
        assert resp.status_code == 403

    def test_eventos_ok_con_admin(self, app):
        mock_svc = MagicMock()
        mock_svc.listar_eventos_sesion.return_value = []
        with patch("src.api.routes.auditoria.Container") as mock_c:
            mock_c.auditoria_service.return_value = mock_svc
            client = TestClient(app)
            resp = client.get("/api/v1/auditoria/eventos", headers=_headers("admin"))
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
