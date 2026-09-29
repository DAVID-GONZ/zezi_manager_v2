from __future__ import annotations

from container import Container


def get_engine():
    return Container.engine()


def get_auth_service():
    return Container.auth_service()
