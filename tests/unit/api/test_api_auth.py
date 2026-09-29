"""
Tests unitarios para la autenticacion JWT de la API REST (backend_11).

Todos los tests mockean Container.auth_service() y Container.auditoria_service()
para ejecutar sin base de datos.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from config import settings
from src.api.schemas.auth import CurrentUserDTO
from src.api.security import InMemoryRateLimiter, get_current_user, require_role
from src.domain.models.usuario import Rol, Usuario
from src.infrastructure.auth.jwt_handler import JWTHandler

# =========================================================================
# Fixtures
# =========================================================================


def _usuario_activo() -> Usuario:
    """Usuario de prueba activo."""
    return Usuario(
        id=1,
        usuario="admin",
        nombre_completo="Admin Test",
        rol=Rol.ADMIN,
        activo=True,
        institucion_id=1,
    )


def _usuario_inactivo() -> Usuario:
    """Usuario de prueba inactivo."""
    return Usuario(
        id=2,
        usuario="inactivo",
        nombre_completo="Inactivo Test",
        rol=Rol.PROFESOR,
        activo=False,
        institucion_id=1,
    )


def _crear_token(user: Usuario) -> str:
    """Crea un token JWT valido para el usuario dado."""
    return JWTHandler(
        secret=settings.JWT_SECRET,
        expiracion_horas=int(settings.JWT_EXPIRE_MINUTES / 60),
    ).crear_token(
        {
            "usuario_id": user.id,
            "username": user.usuario,
            "rol": user.rol.value,
            "institucion_id": user.institucion_id,
        }
    )


@pytest.fixture()
def mock_auth_service():
    """Mock del BcryptAuthService."""
    mock = MagicMock()
    return mock


@pytest.fixture()
def mock_auditoria_service():
    """Mock del AuditoriaService."""
    mock = MagicMock()
    return mock


@pytest.fixture()
def app(mock_auth_service, mock_auditoria_service):
    """App FastAPI minima con los routers de API."""
    # Reset rate limiter entre tests
    from src.api.security import rate_limiter
    rate_limiter._intentos.clear()

    test_app = FastAPI()

    from src.api.errors import avedra_error_handler
    from src.api.router import api_router
    from src.domain.exceptions import AvedraError

    test_app.include_router(api_router)
    test_app.add_exception_handler(AvedraError, avedra_error_handler)

    # Endpoint protegido de prueba (para tests de autorizacion)
    @test_app.get("/test-protegido")
    async def _protegido(user: CurrentUserDTO = Depends(get_current_user)):  # noqa: B008
        return {"usuario_id": user.usuario_id, "rol": user.rol}

    # Endpoint protegido con require_role
    @test_app.get("/test-solo-admin")
    async def _solo_admin(user: CurrentUserDTO = Depends(require_role("admin"))):  # noqa: B008
        return {"usuario_id": user.usuario_id, "rol": user.rol}

    with (
        patch("src.api.auth.Container") as mock_container,
        patch("src.api.security.settings", settings),
    ):
        mock_container.auth_service.return_value = mock_auth_service
        mock_container.auditoria_service.return_value = mock_auditoria_service
        yield test_app, mock_auth_service, mock_auditoria_service


@pytest.fixture()
def client(app):
    """TestClient con los mocks aplicados."""
    test_app, mock_auth, mock_audit = app

    with (
        patch("src.api.auth.Container") as mock_container,
    ):
        mock_container.auth_service.return_value = mock_auth
        mock_container.auditoria_service.return_value = mock_audit
        yield TestClient(test_app), mock_auth, mock_audit


# =========================================================================
# T1 — Login exitoso
# =========================================================================


def test_login_exitoso(client):
    """POST /api/v1/auth/login con credenciales validas retorna 200 + token."""
    tc, mock_auth, _mock_audit = client
    user = _usuario_activo()
    mock_auth.autenticar_usuario.return_value = user

    resp = tc.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.JWT_EXPIRE_MINUTES * 60

    # Verificar que el token es valido
    payload = JWTHandler(secret=settings.JWT_SECRET).verificar_token(
        data["access_token"]
    )
    assert payload is not None
    assert payload["usuario_id"] == user.id
    assert payload["username"] == user.usuario
    assert payload["rol"] == user.rol.value


# =========================================================================
# T2 — Login con credenciales invalidas
# =========================================================================


def test_login_credenciales_invalidas(client):
    """POST /api/v1/auth/login con password incorrecta retorna 401."""
    tc, mock_auth, _mock_audit = client
    mock_auth.autenticar_usuario.side_effect = ValueError("credenciales_invalidas")

    resp = tc.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpass"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "credenciales_invalidas"


# =========================================================================
# T3 — Login con cuenta inactiva
# =========================================================================


def test_login_cuenta_inactiva(client):
    """POST /api/v1/auth/login con cuenta inactiva retorna 403."""
    tc, mock_auth, _mock_audit = client
    mock_auth.autenticar_usuario.side_effect = ValueError("cuenta_inactiva")

    resp = tc.post(
        "/api/v1/auth/login",
        json={"username": "inactivo", "password": "password123"},
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "cuenta_inactiva"


# =========================================================================
# T4 — Rate limiting
# =========================================================================


def test_rate_limiting(client):
    """Mas de 5 intentos fallidos desde la misma IP retorna 429."""
    tc, mock_auth, _mock_audit = client
    mock_auth.autenticar_usuario.side_effect = ValueError("credenciales_invalidas")

    # 5 fallos
    for _ in range(5):
        resp = tc.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "bad"},
        )
        assert resp.status_code == 401

    # El 6to debe ser 429
    resp = tc.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "bad"},
    )
    assert resp.status_code == 429


# =========================================================================
# T5 — Endpoint protegido sin token
# =========================================================================


def test_endpoint_protegido_sin_token(client):
    """Acceso a endpoint protegido sin token retorna 401 o 403."""
    tc, _mock_auth, _mock_audit = client

    resp = tc.get("/test-protegido")

    # HTTPBearer retorna 401 (o 403 en versiones anteriores) sin Authorization
    assert resp.status_code in (401, 403)


# =========================================================================
# T6 — Endpoint protegido con rol incorrecto
# =========================================================================


def test_endpoint_protegido_con_rol_incorrecto(client):
    """Token valido pero rol no autorizado retorna 403."""
    tc, _mock_auth, _mock_audit = client
    _usuario_activo()
    # Crear usuario con rol profesor (no admin)
    user_profesor = Usuario(
        id=3,
        usuario="profesor",
        nombre_completo="Profesor Test",
        rol=Rol.PROFESOR,
        activo=True,
        institucion_id=1,
    )
    token = _crear_token(user_profesor)

    resp = tc.get(
        "/test-solo-admin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Rol insuficiente"


# =========================================================================
# T7 — Endpoint protegido con token valido
# =========================================================================


def test_endpoint_protegido_con_token_valido(client):
    """Token valido con rol correcto retorna 200."""
    tc, _mock_auth, _mock_audit = client
    user = _usuario_activo()
    token = _crear_token(user)

    resp = tc.get(
        "/test-protegido",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["usuario_id"] == user.id
    assert data["rol"] == user.rol.value


# =========================================================================
# T8 — Token invalido
# =========================================================================


def test_endpoint_protegido_con_token_invalido(client):
    """Token malformado retorna 401."""
    tc, _mock_auth, _mock_audit = client

    resp = tc.get(
        "/test-protegido",
        headers={"Authorization": "Bearer token.invalido.aqui"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token invalido o expirado"


# =========================================================================
# T9 — InMemoryRateLimiter unit tests
# =========================================================================


class TestInMemoryRateLimiter:
    """Tests unitarios del rate limiter."""

    def test_permite_dentro_del_limite(self):
        """Permite intentos dentro del limite."""
        rl = InMemoryRateLimiter(max_intentos=3, ventana_seg=300)
        rl.registrar_fallo("1.2.3.4")
        rl.registrar_fallo("1.2.3.4")
        # Tercer intento (aun dentro del limite), no debe lanzar
        rl.check("1.2.3.4")

    def test_bloquea_al_exceder_limite(self):
        """Bloquea al exceder el limite."""
        from fastapi import HTTPException

        rl = InMemoryRateLimiter(max_intentos=2, ventana_seg=300)
        rl.registrar_fallo("1.2.3.4")
        rl.registrar_fallo("1.2.3.4")
        with pytest.raises(HTTPException) as exc_info:
            rl.check("1.2.3.4")
        assert exc_info.value.status_code == 429

    def test_ips_independientes(self):
        """IPs distintas no se afectan entre si."""
        rl = InMemoryRateLimiter(max_intentos=1, ventana_seg=300)
        rl.registrar_fallo("1.1.1.1")
        # Otra IP debe pasar
        rl.check("2.2.2.2")


__all__ = []
