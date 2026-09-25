"""
Port: IAuditoriaRepository
============================
Contrato de acceso a datos para el módulo de auditoría.

Cubre dos tablas con propósitos distintos:
  EventoSesion   — tabla `auditoria`
    Eventos de autenticación y acceso: login, logout, fallos, cambios de rol.
    Solo INSERT y SELECT — nunca se modifican ni eliminan.

  RegistroCambio — tabla `audit_log`
    Operaciones CRUD sobre datos académicos.
    Almacena valor_anterior y valor_nuevo como JSON strings.
    Solo INSERT y SELECT — la auditoría es inmutable por definición.

Principios:
  - Nunca se actualizan ni eliminan registros de auditoría.
  - Los métodos de escritura solo reciben entidades ya construidas
    (la validación ocurre en el modelo de dominio).
  - Los métodos de lectura soportan paginación para evitar cargar
    tablas potencialmente grandes en memoria.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models.auditoria import (
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
)
from ..models.tenant import TenantScope


class IAuditoriaRepository(ABC):
    # =========================================================================
    # EventoSesion — escritura
    # =========================================================================

    @abstractmethod
    def registrar_evento(self, evento: EventoSesion) -> EventoSesion:
        """
        Inserta un evento de sesión en la tabla `auditoria`.
        Retorna la entidad con id asignado.
        El trigger `tg_actualizar_ultima_sesion` reacciona a
        eventos con tipo=LOGIN_EXITOSO actualizando ultima_sesion del usuario.
        """
        ...

    # =========================================================================
    # EventoSesion — lectura
    # =========================================================================

    @abstractmethod
    def listar_eventos(self, filtro: FiltroAuditoriaDTO) -> list[EventoSesion]:
        """
        Retorna eventos de sesión según los filtros indicados.
        Ordenados por fecha_hora descendente (más recientes primero).
        Soporta paginación mediante filtro.pagina y filtro.por_pagina.
        """
        ...

    @abstractmethod
    def get_ultimo_login(self, usuario_id: int) -> EventoSesion | None:
        """
        Retorna el último evento LOGIN_EXITOSO del usuario.
        None si el usuario nunca ha iniciado sesión.
        Útil para mostrar "Último acceso:" en el perfil de usuario.
        """
        ...

    @abstractmethod
    def contar_fallos_recientes(
        self,
        usuario: str,
        ventana_minutos: int = 30,
    ) -> int:
        """
        Cuenta los eventos LOGIN_FALLIDO del usuario en los últimos
        `ventana_minutos` minutos.
        Usado por el servicio de auth para implementar bloqueo temporal
        por intentos fallidos (ej. bloquear tras 5 fallos en 30 min).
        """
        ...

    # =========================================================================
    # RegistroCambio — escritura
    # =========================================================================

    @abstractmethod
    def registrar_cambio(self, registro: RegistroCambio) -> RegistroCambio:
        """
        Inserta un registro de cambio en la tabla `audit_log`.
        Retorna la entidad con id asignado.
        """
        ...

    @abstractmethod
    def registrar_cambios_masivos(self, registros: list[RegistroCambio]) -> int:
        """
        Inserta múltiples registros de cambio en una sola operación.
        Retorna el número de registros insertados.
        Más eficiente que llamar registrar_cambio en bucle para operaciones batch.
        """
        ...

    # =========================================================================
    # RegistroCambio — lectura
    # =========================================================================

    @abstractmethod
    def listar_cambios(self, filtro: FiltroAuditoriaDTO) -> list[RegistroCambio]:
        """
        Retorna registros de cambio según los filtros indicados.
        Ordenados por timestamp descendente (más recientes primero).
        Soporta paginación mediante filtro.pagina y filtro.por_pagina.
        """
        ...

    @abstractmethod
    def listar_cambios_por_registro(
        self,
        tabla: str,
        registro_id: int,
    ) -> list[RegistroCambio]:
        """
        Retorna el historial de cambios de un registro específico.
        Ordenados por timestamp ascendente (cronológico).
        Usado para mostrar el historial de ediciones de una entidad.
        """
        ...

    @abstractmethod
    def get_cambio(self, cambio_id: int) -> RegistroCambio | None:
        """Retorna el registro de cambio con ese id, o None si no existe."""
        ...

    # =========================================================================
    # Verificación de integridad (encadenamiento por hash — seguridad_03, M3)
    # =========================================================================
    #
    # Métodos CONCRETOS (no abstractos) a propósito: los repos sin soporte de
    # cadena (fakes de tests) los heredan sin cambios y se consideran "no
    # verificables" (devuelven None). El repo SQLite los sobreescribe.

    def verificar_cadena_eventos(self, *, completa: bool = False) -> int | None:
        """
        Verifica el encadenamiento por hash de la tabla `auditoria`.

        Con `completa=False` (por defecto) reanuda desde el último punto de
        control guardado (verificación incremental — R6). Con `completa=True`
        verifica desde el origen, ignorando el punto de control (R8).

        Retorna el `id` del primer evento cuya cadena no cuadra, o None si el
        tramo verificado es íntegro. Los repos sin soporte de cadena devuelven
        None (se consideran no verificables).
        """
        return None

    def verificar_cadena_cambios(self, *, completa: bool = False) -> int | None:
        """
        Verifica el encadenamiento por hash de la tabla `audit_log`.

        Con `completa=False` (por defecto) reanuda desde el último punto de
        control. Con `completa=True` verifica desde el origen (R8).

        Retorna el `id` del primer cambio cuya cadena no cuadra, o None si el
        tramo verificado es íntegro. Los repos sin soporte de cadena devuelven None.
        """
        return None

    # =========================================================================
    # Conteos y agregados (obs_08 — R1, R2, R3)
    # =========================================================================
    #
    # Métodos CONCRETOS (no abstractos) con valor por defecto neutro (R3),
    # al igual que `verificar_cadena_*`. Los fakes de tests los heredan sin
    # modificarse. El repo SQLite los sobreescribe con implementaciones SQL.

    def contar_eventos(self, filtro: FiltroAuditoriaDTO) -> int:
        """
        Cuenta los eventos de sesión que satisfacen `filtro`, ignorando
        `filtro.pagina` y `filtro.por_pagina`.

        Permite mostrar el total de resultados («N resultados») junto a los
        controles de paginación sin necesidad de materializar todas las filas.
        """
        return 0

    def contar_cambios(self, filtro: FiltroAuditoriaDTO) -> int:
        """
        Cuenta los registros de cambio que satisfacen `filtro`, ignorando
        `filtro.pagina` y `filtro.por_pagina`.
        """
        return 0

    def resumen_eventos(
        self,
        desde: datetime,
        hasta: datetime | None = None,
        institucion_id: TenantScope = "*",
    ) -> dict:
        """
        Devuelve los agregados de uso calculados en SQL para la ventana temporal
        `[desde, hasta]` (o hasta el momento presente si `hasta` es None),
        acotados por `institucion_id` cuando no es `"*"`.

        Claves garantizadas en el dict devuelto:
          - ``por_tipo``          dict[str, int] — conteo de eventos por tipo.
          - ``logins_hoy``        int  — LOGIN_EXITOSO desde inicio del día actual.
          - ``usuarios_distintos`` int — usuarios únicos con login en la ventana.
          - ``denegados_criticos`` int — ACCESO_DENEGADO con severidad=CRITICA.

        Los repos sin soporte devuelven `{}` (valor neutro; el consumidor usa
        `.get(clave, 0)` para un comportamiento fail-open).
        """
        return {}


__all__ = ["IAuditoriaRepository"]
