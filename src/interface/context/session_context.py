"""
session_context.py — Contexto de sesión activa del usuario.

Wrappea app.storage.user de NiceGUI y expone el contexto académico activo
(año, periodo, grupo, asignación) para la capa de interfaz.

Los servicios NO reciben SessionContext — reciben ContextoAcademicoDTO
(del dominio). SessionContext es exclusivo de la capa de interfaz.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from nicegui import app


@dataclass
class SessionContext:
    """
    Contexto de sesión activa del usuario autenticado.

    Mantiene los datos de identidad y el contexto académico seleccionado.
    Use `desde_storage()` para reconstruir desde la sesión de NiceGUI,
    y `guardar()` para persistir cambios de contexto.
    """
    usuario_id:      int
    usuario_nombre:  str
    usuario_rol:     str
    anio_id:         int | None = None
    periodo_id:      int | None = None
    grupo_id:        int | None = None
    asignacion_id:   int | None = None

    # Nombres legibles para mostrar en UI (no IDs)
    anio_nombre:       str = field(default="")
    periodo_nombre:    str = field(default="")
    grupo_nombre:      str = field(default="")
    asignacion_nombre: str = field(default="")

    @classmethod
    def desde_storage(cls) -> "SessionContext | None":
        """
        Construye el contexto desde app.storage.user de NiceGUI.
        Retorna None si no hay sesión activa.
        """
        storage = app.storage.user
        if not storage.get("autenticado"):
            return None
        return cls(
            usuario_id        = storage.get("usuario_id"),
            usuario_nombre    = storage.get("usuario_nombre", ""),
            usuario_rol       = storage.get("usuario_rol", ""),
            anio_id           = storage.get("anio_id"),
            periodo_id        = storage.get("periodo_id"),
            grupo_id          = storage.get("grupo_id"),
            asignacion_id     = storage.get("asignacion_id"),
            anio_nombre       = storage.get("anio_nombre", ""),
            periodo_nombre    = storage.get("periodo_nombre", ""),
            grupo_nombre      = storage.get("grupo_nombre", ""),
            asignacion_nombre = storage.get("asignacion_nombre", ""),
        )

    def guardar(self) -> None:
        """Persiste el contexto completo en app.storage.user."""
        app.storage.user.update({
            "usuario_id":        self.usuario_id,
            "usuario_nombre":    self.usuario_nombre,
            "usuario_rol":       self.usuario_rol,
            "anio_id":           self.anio_id,
            "periodo_id":        self.periodo_id,
            "grupo_id":          self.grupo_id,
            "asignacion_id":     self.asignacion_id,
            "anio_nombre":       self.anio_nombre,
            "periodo_nombre":    self.periodo_nombre,
            "grupo_nombre":      self.grupo_nombre,
            "asignacion_nombre": self.asignacion_nombre,
        })

    def to_contexto_academico(self):
        """
        Convierte a ContextoAcademicoDTO para pasarle a los servicios de dominio.
        Lanza ValueError si falta anio_id o periodo_id.
        """
        from src.domain.models.dtos import ContextoAcademicoDTO
        if not self.anio_id or not self.periodo_id:
            raise ValueError(
                "Contexto incompleto: selecciona un año y periodo activos."
            )
        return ContextoAcademicoDTO(
            usuario_id    = self.usuario_id,
            anio_id       = self.anio_id,
            periodo_id    = self.periodo_id,
            grupo_id      = self.grupo_id,
            asignacion_id = self.asignacion_id,
        )

    # ── Propiedades de conveniencia ──────────────────────────────────────────

    @property
    def es_docente(self) -> bool:
        return self.usuario_rol == "profesor"

    @property
    def es_directivo(self) -> bool:
        return self.usuario_rol in ("admin", "director", "coordinador")

    @property
    def es_admin(self) -> bool:
        return self.usuario_rol == "admin"

    @property
    def tiene_grupo(self) -> bool:
        return self.grupo_id is not None

    @property
    def contexto_completo(self) -> bool:
        return all([self.anio_id, self.periodo_id,
                    self.grupo_id, self.asignacion_id])


__all__ = ["SessionContext"]
