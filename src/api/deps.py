from __future__ import annotations

from container import Container
from src.api.schemas.auth import CurrentUserDTO


def get_engine():
    return Container.engine()


def get_auth_service():
    return Container.auth_service()


def scope_from_user(user: CurrentUserDTO):
    """Construye TenantScope desde el usuario del JWT."""
    if user.rol == "admin":
        return "*"
    return user.institucion_id


class PaginationParams:
    def __init__(self, page: int = 1, per_page: int = 25):
        self.page = max(1, page)
        self.per_page = min(100, max(1, per_page))
        self.offset = (self.page - 1) * self.per_page
