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

from datetime import datetime, timedelta

from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    TipoEventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    ResumenUsoDTO,
)


class AuditoriaService:
    """
    Servicio de lectura de auditoría.

    Expone los datos de auditoría a la capa de interfaz sin
    exponer el repositorio directamente.
    """

    def __init__(self, repo: IAuditoriaRepository) -> None:
        self._repo = repo

    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        return self._repo.registrar_evento(evento)

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

    def resumen_uso(self, dias: int = 7) -> ResumenUsoDTO:
        """
        Agregación de SOLO LECTURA del uso de la plataforma para el dashboard
        de admin. Calcula, a partir de los eventos de sesión recientes:

          - logins exitosos de hoy y de la ventana de `dias`.
          - accesos denegados en la ventana.
          - usuarios distintos con login en la ventana (activos recientes).
          - total de sesiones (logins) en la ventana.

        No muta nada. Robusto ante repos vacíos.
        """
        dias = max(1, dias)
        ahora = datetime.now()
        desde = ahora - timedelta(days=dias)
        inicio_hoy = datetime(ahora.year, ahora.month, ahora.day)

        eventos = self._repo.listar_eventos(
            FiltroAuditoriaDTO(desde=desde, pagina=1, por_pagina=500)
        )

        logins_hoy = 0
        logins_periodo = 0
        accesos_denegados = 0
        usuarios: set = set()

        for ev in eventos:
            fecha = getattr(ev, "fecha_hora", None)
            tipo = getattr(ev, "tipo_evento", None)
            if tipo == TipoEventoSesion.LOGIN_EXITOSO:
                logins_periodo += 1
                if ev.usuario_id is not None:
                    usuarios.add(ev.usuario_id)
                else:
                    usuarios.add(ev.usuario)
                if fecha is not None and fecha >= inicio_hoy:
                    logins_hoy += 1
            elif tipo == TipoEventoSesion.ACCESO_DENEGADO:
                accesos_denegados += 1

        return ResumenUsoDTO(
            logins_hoy        = logins_hoy,
            logins_periodo    = logins_periodo,
            accesos_denegados = accesos_denegados,
            usuarios_activos  = len(usuarios),
            sesiones_periodo  = logins_periodo,
            dias              = dias,
        )


__all__ = [
    "AuditoriaService",
    "FiltroAuditoriaDTO",
    "RegistroCambio",
    "EventoSesion",
    "AccionCambio",
    "TipoEventoSesion",
    "ResumenUsoDTO",
]
