"""
AuditoriaService
================
Punto de acceso de la UI a los datos de auditoría.

Responsabilidades:
  - Listar cambios del audit_log con filtros opcionales (paginado).
  - Listar eventos de sesión con filtros opcionales (paginado).

La auditoría es de solo lectura desde la perspectiva de los servicios
de aplicación. Las escrituras las realizan otros servicios vía
IAuditoriaRepository.registrar_cambio / registrar_evento.
"""
from __future__ import annotations

from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.models.auditoria import (
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
)


class AuditoriaService:
    """
    Servicio de lectura de auditoría.

    Expone los datos de auditoría a la capa de interfaz sin
    exponer el repositorio directamente.
    """

    def __init__(self, repo: IAuditoriaRepository) -> None:
        self._repo = repo

    def listar_cambios(
        self,
        filtro: FiltroAuditoriaDTO,
    ) -> list[RegistroCambio]:
        """
        Retorna registros del audit_log ordenados por timestamp descendente.

        Args:
            filtro: Criterios de búsqueda y paginación.

        Returns:
            Lista de RegistroCambio (puede ser vacía).
        """
        return self._repo.listar_cambios(filtro)

    def listar_eventos_sesion(
        self,
        filtro: FiltroAuditoriaDTO,
    ) -> list[EventoSesion]:
        """
        Retorna eventos de sesión (login, logout, fallos) paginados.

        Args:
            filtro: Criterios de búsqueda y paginación.

        Returns:
            Lista de EventoSesion (puede ser vacía).
        """
        return self._repo.listar_eventos(filtro)


__all__ = ["AuditoriaService"]
