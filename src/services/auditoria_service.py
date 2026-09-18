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
from typing import TYPE_CHECKING

from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    ResumenUsoDTO,
    TipoEventoSesion,
)
from src.domain.ports.auditoria_repo import IAuditoriaRepository

if TYPE_CHECKING:
    from src.domain.ports.security_logger import ISecurityLogger


class AuditoriaService:
    """
    Servicio de lectura de auditoría.

    Expone los datos de auditoría a la capa de interfaz sin
    exponer el repositorio directamente.
    """

    def __init__(
        self,
        repo: IAuditoriaRepository,
        security_logger: ISecurityLogger | None = None,
    ) -> None:
        """Inyecta el repositorio de auditoría y el logger de seguridad."""
        self._repo = repo
        self._security_logger = security_logger

    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        """Registra un evento de sesión (delegado al repositorio)."""
        if evento.institucion_id is None:
            try:
                from src.services.contexto_tenant import institucion_actual

                evento = evento.model_copy(update={"institucion_id": institucion_actual()})
            except Exception:
                pass
        resultado = self._repo.registrar_evento(evento)

        # Emitir al security logger sin romper la auditoría ante fallos de logging
        if self._security_logger is not None:
            try:
                self._emit_security_log(evento)
            except Exception:
                pass

        # alerta_ip: registrar fallo por IP cuando el evento es LOGIN_FALLIDO
        if evento.tipo_evento == TipoEventoSesion.LOGIN_FALLIDO and evento.ip_address is not None:
            try:
                from src.domain.policies import alerta_ip
                alerta_ip.registrar_fallo_ip(evento.ip_address)
            except Exception:
                pass

        return resultado

    def _emit_security_log(self, evento: EventoSesion) -> None:
        """Despacha el evento al security logger según su tipo."""
        sl = self._security_logger
        if sl is None:
            return

        usuario = evento.usuario
        ip = evento.ip_address or ""
        detalles = evento.detalles or ""
        institucion_id = evento.institucion_id or 0
        tipo = evento.tipo_evento

        if tipo == TipoEventoSesion.LOGIN_EXITOSO:
            sl.login_exitoso(usuario, ip, rol=detalles, institucion_id=institucion_id)
        elif tipo == TipoEventoSesion.LOGIN_FALLIDO:
            sl.login_fallido(usuario, ip, motivo=detalles)
        elif tipo == TipoEventoSesion.LOGOUT:
            sl.logout(usuario, ip)
        elif tipo == TipoEventoSesion.ACCESO_DENEGADO:
            sl.acceso_denegado(usuario, ip, recurso=detalles)
        elif tipo in (TipoEventoSesion.VER_COMO_INICIO, TipoEventoSesion.VER_COMO_FIN):
            sl.ver_como(admin=usuario, objetivo=detalles, accion=tipo.value)
        elif tipo in (
            TipoEventoSesion.CREAR_USUARIO,
            TipoEventoSesion.EDITAR_USUARIO,
            TipoEventoSesion.CAMBIAR_ROL,
            TipoEventoSesion.DESACTIVAR_USUARIO,
            TipoEventoSesion.ACTIVAR_USUARIO,
            TipoEventoSesion.RESETEAR_PASSWORD,
        ):
            sl.gestion_usuario(actor=usuario, objetivo=detalles, operacion=tipo.value)

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

    def verificar_integridad(self) -> dict:
        """
        Verifica el encadenamiento por hash de las dos tablas de auditoría
        (seguridad_03, M3) y compone un resultado de SOLO LECTURA.

        Delega en los métodos de verificación del repositorio. Devuelve un dict
        de primitivos (no un DTO de dominio) para que la capa de interfaz lo
        consuma sin acoplarse al dominio:

            {
              "eventos_ok":      bool,       # True si la cadena de `auditoria` es íntegra
              "cambios_ok":      bool,       # True si la cadena de `audit_log` es íntegra
              "evento_roto_id":  int | None, # id del primer evento roto, o None
              "cambio_roto_id":  int | None, # id del primer cambio roto, o None
            }

        Un repo sin soporte de cadena devuelve None en ambos, lo que se reporta
        como "íntegro" (no hay evidencia de manipulación detectable).
        """
        evento_roto_id = self._repo.verificar_cadena_eventos()
        cambio_roto_id = self._repo.verificar_cadena_cambios()
        return {
            "eventos_ok": evento_roto_id is None,
            "cambios_ok": cambio_roto_id is None,
            "evento_roto_id": evento_roto_id,
            "cambio_roto_id": cambio_roto_id,
        }

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
            logins_hoy=logins_hoy,
            logins_periodo=logins_periodo,
            accesos_denegados=accesos_denegados,
            usuarios_activos=len(usuarios),
            sesiones_periodo=logins_periodo,
            dias=dias,
        )


__all__ = [
    "AccionCambio",
    "AuditoriaService",
    "EventoSesion",
    "FiltroAuditoriaDTO",
    "RegistroCambio",
    "ResumenUsoDTO",
    "TipoEventoSesion",
]
