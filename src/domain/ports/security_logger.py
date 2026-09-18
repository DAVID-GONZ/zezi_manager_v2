"""
security_logger.py — Puerto ISecurityLogger (obs_03).
======================================================

Abstracción pura del logging de seguridad estructurado.
Los implementadores deben serializar solo campos autorizados (whitelist R7);
nunca aceptar **kwargs libres que puedan filtrar campos sensibles.

Regla de capas: solo stdlib/abc. Sin imports de infraestructura.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ISecurityLogger(ABC):
    """Puerto para el logging de eventos de seguridad estructurado."""

    @abstractmethod
    def login_exitoso(
        self,
        usuario: str,
        ip: str,
        rol: str,
        institucion_id: int,
    ) -> None:
        """Registra un login exitoso (INFO)."""

    @abstractmethod
    def login_fallido(
        self,
        usuario: str,
        ip: str,
        motivo: str,
    ) -> None:
        """Registra un login fallido (WARNING)."""

    @abstractmethod
    def logout(self, usuario: str, ip: str) -> None:
        """Registra un logout (INFO)."""

    @abstractmethod
    def acceso_denegado(
        self,
        usuario: str,
        ip: str,
        recurso: str,
    ) -> None:
        """Registra un acceso denegado (WARNING)."""

    @abstractmethod
    def ver_como(self, admin: str, objetivo: str, accion: str) -> None:
        """Registra inicio/fin de impersonación (INFO)."""

    @abstractmethod
    def gestion_usuario(self, actor: str, objetivo: str, operacion: str) -> None:
        """Registra una operación de gestión de usuario (INFO)."""


__all__ = ["ISecurityLogger"]
