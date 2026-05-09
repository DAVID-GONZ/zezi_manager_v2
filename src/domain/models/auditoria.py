"""
Modelo de dominio: Auditoría
=============================

Contiene:
  Enums    — TipoEventoSesion, AccionCambio
  Entidades — EventoSesion, RegistroCambio
  DTOs     — CrearEventoSesionDTO, CrearRegistroCambioDTO, FiltroAuditoriaDTO

Dos tablas con propósitos distintos:

  EventoSesion  → tabla `auditoria`
    Registra eventos de autenticación y acceso:
    login exitoso, login fallido, logout, creación de usuarios.
    Fuente de verdad para el trigger `tg_actualizar_ultima_sesion`.

  RegistroCambio → tabla `audit_log`
    Registra operaciones CRUD sobre datos académicos.
    Reemplaza las llamadas a `registrar_cambio()` del legacy,
    que serializaba `datos_anteriores`/`datos_nuevos` como dicts.
    En v2.0, `valor_anterior` y `valor_nuevo` son JSON strings.

Ambas entidades son inmutables: se crean y se leen, nunca se modifican.
No tienen métodos de transición de estado.

Compatibilidad con v1.0:
  El `registrar_cambio()` del legacy recibía:
    tabla, accion, datos_anteriores (dict), datos_nuevos (dict),
    descripcion, id_registro
  En v2.0, `CrearRegistroCambioDTO.desde_cambio_legacy()` hace
  la conversión para facilitar la migración progresiva.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class TipoEventoSesion(str, Enum):
    LOGIN_EXITOSO      = "LOGIN_EXITOSO"
    LOGIN_FALLIDO      = "LOGIN_FALLIDO"
    LOGOUT             = "LOGOUT"
    CREAR_USUARIO      = "CREAR_USUARIO"
    EDITAR_USUARIO     = "EDITAR_USUARIO"
    RESETEAR_PASSWORD  = "RESETEAR_PASSWORD"
    CAMBIAR_ROL        = "CAMBIAR_ROL"
    DESACTIVAR_USUARIO = "DESACTIVAR_USUARIO"
    ACTIVAR_USUARIO    = "ACTIVAR_USUARIO"
    ACCESO_DENEGADO    = "ACCESO_DENEGADO"


class AccionCambio(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    READ   = "READ"    # accesos sensibles que conviene auditar


# =============================================================================
# Entidades — inmutables
# =============================================================================

class EventoSesion(BaseModel):
    """
    Registro de un evento de autenticación o acceso.

    Inmutable: se crea una vez y no se modifica.
    El trigger `tg_actualizar_ultima_sesion` de la BD reacciona
    a inserciones con tipo=LOGIN_EXITOSO para actualizar `ultima_sesion`.
    """
    id:          int | None            = None
    usuario:     str                   # username (texto, no FK, para preservar tras borrado)
    usuario_id:  int | None            = None
    tipo_evento: TipoEventoSesion
    ip_address:  str | None            = None
    fecha_hora:  datetime              = Field(default_factory=datetime.now)
    detalles:    str | None            = None

    @field_validator("usuario", mode="before")
    @classmethod
    def validar_usuario(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de usuario no puede estar vacío.")
        return v

    @field_validator("detalles", mode="before")
    @classmethod
    def limpiar_detalles(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("ip_address", mode="before")
    @classmethod
    def limpiar_ip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def es_exitoso(self) -> bool:
        return self.tipo_evento == TipoEventoSesion.LOGIN_EXITOSO

    @property
    def es_fallido(self) -> bool:
        return self.tipo_evento == TipoEventoSesion.LOGIN_FALLIDO

    @property
    def es_acceso_denegado(self) -> bool:
        return self.tipo_evento == TipoEventoSesion.ACCESO_DENEGADO

    @property
    def fecha_display(self) -> str:
        return self.fecha_hora.strftime("%Y-%m-%d %H:%M:%S")


class RegistroCambio(BaseModel):
    """
    Registro de una operación CRUD sobre datos del sistema.

    `valor_anterior` y `valor_nuevo` son JSON strings que representan
    el estado del registro antes y después del cambio. Pueden ser None
    para operaciones CREATE (sin valor anterior) o DELETE (sin valor nuevo).

    Reemplaza el `registrar_cambio()` del legacy, que recibía dicts
    y los serializaba implícitamente.
    """
    id:              int | None      = None
    usuario_id:      int | None      = None
    accion:          AccionCambio
    tabla:           str
    registro_id:     int | None      = None
    valor_anterior:  str | None      = None  # JSON string
    valor_nuevo:     str | None      = None  # JSON string
    timestamp:       datetime        = Field(default_factory=datetime.now)

    @field_validator("tabla", mode="before")
    @classmethod
    def validar_tabla(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la tabla no puede estar vacío.")
        if len(v) > 100:
            raise ValueError(
                f"El nombre de tabla no puede exceder 100 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("valor_anterior", "valor_nuevo", mode="before")
    @classmethod
    def validar_json(cls, v: str | dict | None) -> str | None:
        """Acepta dict (lo serializa) o JSON string (lo valida)."""
        if v is None:
            return None
        if isinstance(v, dict):
            return json.dumps(v, ensure_ascii=False, default=str)
        v = str(v).strip()
        if not v:
            return None
        # Validar que sea JSON válido
        try:
            json.loads(v)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"valor_anterior/valor_nuevo debe ser JSON válido: {exc}"
            )
        return v

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def anterior_como_dict(self) -> dict | None:
        """Deserializa valor_anterior como dict."""
        if self.valor_anterior is None:
            return None
        return json.loads(self.valor_anterior)

    @property
    def nuevo_como_dict(self) -> dict | None:
        """Deserializa valor_nuevo como dict."""
        if self.valor_nuevo is None:
            return None
        return json.loads(self.valor_nuevo)

    @property
    def es_creacion(self) -> bool:
        return self.accion == AccionCambio.CREATE

    @property
    def es_eliminacion(self) -> bool:
        return self.accion == AccionCambio.DELETE

    @property
    def timestamp_display(self) -> str:
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def para_creacion(
        cls,
        tabla: str,
        datos_nuevos: dict,
        registro_id: int | None = None,
        usuario_id: int | None = None,
    ) -> "RegistroCambio":
        """Construye un registro de creación (sin valor anterior)."""
        return cls(
            usuario_id    = usuario_id,
            accion        = AccionCambio.CREATE,
            tabla         = tabla,
            registro_id   = registro_id,
            valor_anterior= None,
            valor_nuevo   = datos_nuevos,
        )

    @classmethod
    def para_actualizacion(
        cls,
        tabla: str,
        datos_anteriores: dict,
        datos_nuevos: dict,
        registro_id: int | None = None,
        usuario_id: int | None = None,
    ) -> "RegistroCambio":
        """Construye un registro de actualización."""
        return cls(
            usuario_id    = usuario_id,
            accion        = AccionCambio.UPDATE,
            tabla         = tabla,
            registro_id   = registro_id,
            valor_anterior= datos_anteriores,
            valor_nuevo   = datos_nuevos,
        )

    @classmethod
    def para_eliminacion(
        cls,
        tabla: str,
        datos_anteriores: dict,
        registro_id: int | None = None,
        usuario_id: int | None = None,
    ) -> "RegistroCambio":
        """Construye un registro de eliminación (sin valor nuevo)."""
        return cls(
            usuario_id    = usuario_id,
            accion        = AccionCambio.DELETE,
            tabla         = tabla,
            registro_id   = registro_id,
            valor_anterior= datos_anteriores,
            valor_nuevo   = None,
        )


# =============================================================================
# DTOs
# =============================================================================

class CrearEventoSesionDTO(BaseModel):
    """Datos para registrar un evento de sesión."""
    usuario:     str
    usuario_id:  int | None            = None
    tipo_evento: TipoEventoSesion
    ip_address:  str | None            = None
    detalles:    str | None            = None

    def to_evento(self) -> EventoSesion:
        return EventoSesion(**self.model_dump())


class CrearRegistroCambioDTO(BaseModel):
    """
    Datos para registrar un cambio de datos.

    `desde_legacy()` permite migrar llamadas al `registrar_cambio()`
    de v1.0 sin reescribir todo el código de servicios de una vez.
    """
    usuario_id:      int | None      = None
    accion:          AccionCambio
    tabla:           str
    registro_id:     int | None      = None
    valor_anterior:  dict | None     = None
    valor_nuevo:     dict | None     = None

    def to_registro(self) -> RegistroCambio:
        return RegistroCambio(**self.model_dump())

    @classmethod
    def desde_legacy(
        cls,
        tabla: str,
        accion: str,
        datos_anteriores: dict | None = None,
        datos_nuevos: dict | None = None,
        id_registro: int | None = None,
        usuario_id: int | None = None,
        descripcion: str | None = None,   # ignorado en v2.0
    ) -> "CrearRegistroCambioDTO":
        """
        Compatibilidad con la firma de `registrar_cambio()` del legacy.

        El campo `descripcion` de v1.0 no tiene equivalente directo;
        se puede incluir en `datos_nuevos` como `{'_descripcion': ...}`.
        """
        # Normalizar accion al enum
        accion_map = {
            "INSERT": AccionCambio.CREATE,
            "CREATE": AccionCambio.CREATE,
            "UPDATE": AccionCambio.UPDATE,
            "DELETE": AccionCambio.DELETE,
            "READ":   AccionCambio.READ,
        }
        accion_enum = accion_map.get(str(accion).upper(), AccionCambio.UPDATE)

        # Agregar descripcion a datos_nuevos si hay
        datos_n = dict(datos_nuevos) if datos_nuevos else {}
        if descripcion:
            datos_n["_descripcion"] = descripcion

        return cls(
            usuario_id     = usuario_id,
            accion         = accion_enum,
            tabla          = tabla,
            registro_id    = id_registro,
            valor_anterior = datos_anteriores,
            valor_nuevo    = datos_n if datos_n else None,
        )


class FiltroAuditoriaDTO(BaseModel):
    """Parámetros para consultar registros de auditoría."""
    usuario_id:   int | None                = None
    tabla:        str | None                = None
    accion:       AccionCambio | None       = None
    tipo_evento:  TipoEventoSesion | None   = None
    desde:        datetime | None           = None
    hasta:        datetime | None           = None
    pagina:       int                       = Field(default=1, ge=1)
    por_pagina:   int                       = Field(default=100, ge=1, le=500)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TipoEventoSesion",
    "AccionCambio",
    "EventoSesion",
    "RegistroCambio",
    "CrearEventoSesionDTO",
    "CrearRegistroCambioDTO",
    "FiltroAuditoriaDTO",
]