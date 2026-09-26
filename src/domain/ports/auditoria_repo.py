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
from collections.abc import Iterator
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

    # =========================================================================
    # Consultas de tramo (obs_12 — T2/T9)
    # =========================================================================
    #
    # Métodos CONCRETOS con valor neutro por defecto; el repo SQLite los
    # sobreescribe con SQL real. Los fakes de tests los heredan sin cambios.

    def rango_de(
        self,
        tabla: str,
        filtro: FiltroAuditoriaDTO,
    ) -> tuple[int, int] | None:
        """
        Devuelve ``(id_min, id_max)`` del tramo que satisface ``filtro`` en
        ``tabla`` ('audit_log' o 'auditoria'), o ``None`` si el tramo está vacío.

        El tramo son los ids mínimo y máximo de las filas que cumplen los
        criterios del filtro (incluyendo scope de institución). Se usa para
        delimitar el tramo antes de exportar o purgar.
        """
        return None

    def listar_cambios_tramo(
        self,
        tabla: str,
        id_desde: int,
        id_hasta: int,
        scope: TenantScope,
        *,
        lote: int = 5_000,
    ) -> Iterator[list[RegistroCambio]]:
        """
        Itera por lotes las filas de ``tabla`` en el rango ``[id_desde, id_hasta]``,
        respetando el ``scope`` de institución.

        Devuelve un iterador de listas (lotes de tamaño ``lote``). La iteración
        por lotes evita materializar el tramo completo en memoria para tramos
        grandes (R7 del diseño de obs_12).

        Solo soporta la tabla 'audit_log'; para 'auditoria' los eventos de sesión
        no tienen un campo RegistroCambio equivalente. El repo SQLite implementa
        ambas tablas usando el mapeador correspondiente.
        """
        return iter([])

    def eliminar_hasta(
        self,
        tabla: str,
        id_hasta: int,
        scope: TenantScope,
    ) -> int:
        """
        Elimina las filas de ``tabla`` con ``id <= id_hasta`` que pertenezcan al
        scope indicado.

        INVARIANTE APPEND-ONLY: este es el único ``DELETE`` admisible en las
        tablas de auditoría, y SOLO se invoca desde ``archivar_y_purgar`` del
        servicio de retención, que lo hace:
          1. Después de escribir el archivo de archivado.
          2. Después de verificar el hash del archivo.
          3. Dejando constancia del borrado en la propia bitácora
             (evento ``AUDITORIA_PURGADA`` con ruta, hash, rango y filas).

        No hay ``UPDATE``. El único ``DELETE`` admisible deja constancia.

        Retorna el número de filas eliminadas.
        """
        return 0

    def uso_diario(
        self,
        dias: int = 14,
    ) -> list[dict]:
        """
        Devuelve una lista de dicts ``{fecha, logins, denegados}`` para cada
        día de la ventana de ``dias`` días, calculados mediante
        ``GROUP BY date(fecha_hora)`` sobre la tabla ``auditoria``.

        Los días sin actividad se devuelven con ceros (obs_13 — T9).
        Cada dict garantiza las claves: ``fecha`` (YYYY-MM-DD), ``logins`` (int),
        ``denegados`` (int).

        Los repos sin soporte devuelven ``[]`` (valor neutro).
        """
        return []

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
