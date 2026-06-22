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
    institucion_id:  int | None = None   # multi-tenant (paso_24)
    anio_id:         int | None = None
    periodo_id:      int | None = None
    grupo_id:        int | None = None
    asignacion_id:   int | None = None

    # Nombres legibles para mostrar en UI (no IDs)
    anio_nombre:       str = field(default="")
    periodo_nombre:    str = field(default="")
    grupo_nombre:      str = field(default="")
    asignacion_nombre: str = field(default="")

    # ── Estado de impersonación "Ver como" (paso_21) ──────────────────────────
    # Cuando un admin asume la vista de otro usuario en SOLO LECTURA, guardamos
    # su identidad real para poder restaurarla con salir_ver_como().
    impersonando:      bool        = False
    admin_real_id:     int | None  = None
    admin_real_nombre: str         = field(default="")
    admin_real_rol:    str         = field(default="")
    admin_real_institucion_id: int | None = None
    solo_lectura:      bool        = False

    @classmethod
    def desde_storage(cls) -> "SessionContext | None":
        """
        Construye el contexto desde app.storage.user de NiceGUI.
        Retorna None si no hay sesión activa.

        Choke point único de activación del modo solo lectura: cada página y
        cada handler que relee el contexto pasa por aquí, de modo que el flag
        global de la capa de servicios queda sincronizado en la task actual.
        """
        storage = app.storage.user
        if not storage.get("autenticado"):
            # Sesión cerrada: el contexto deja de imponer solo lectura ni scope.
            cls._sincronizar_solo_lectura(False)
            cls._sincronizar_institucion(None, None)
            return None
        solo_lectura = bool(storage.get("solo_lectura", False))
        # Sincroniza el ContextVar de servicios con el estado persistido.
        cls._sincronizar_solo_lectura(solo_lectura)
        # Sincroniza el scope de institución (regla admin→None / resto→su tenant).
        cls._sincronizar_institucion(
            storage.get("usuario_rol", ""),
            storage.get("institucion_id"),
        )
        return cls(
            usuario_id        = storage.get("usuario_id"),
            usuario_nombre    = storage.get("usuario_nombre", ""),
            usuario_rol       = storage.get("usuario_rol", ""),
            institucion_id    = storage.get("institucion_id"),
            anio_id           = storage.get("anio_id"),
            periodo_id        = storage.get("periodo_id"),
            grupo_id          = storage.get("grupo_id"),
            asignacion_id     = storage.get("asignacion_id"),
            anio_nombre       = storage.get("anio_nombre", ""),
            periodo_nombre    = storage.get("periodo_nombre", ""),
            grupo_nombre      = storage.get("grupo_nombre", ""),
            asignacion_nombre = storage.get("asignacion_nombre", ""),
            impersonando      = bool(storage.get("impersonando", False)),
            admin_real_id     = storage.get("admin_real_id"),
            admin_real_nombre = storage.get("admin_real_nombre", ""),
            admin_real_rol    = storage.get("admin_real_rol", ""),
            admin_real_institucion_id = storage.get("admin_real_institucion_id"),
            solo_lectura      = solo_lectura,
        )

    @staticmethod
    def _sincronizar_solo_lectura(valor: bool) -> None:
        """Refleja el flag de impersonación en la capa de servicios."""
        from src.services.solo_lectura import activar_solo_lectura
        activar_solo_lectura(valor)

    @staticmethod
    def _sincronizar_institucion(rol: str, institucion_id: int | None) -> None:
        """
        Refleja el scope de institución en la capa de servicios (frente C).

        REGLA DE SCOPE: el admin opera cross-tenant → scope None (los
        servicios no auto-filtran y respetan el filtro explícito). Cualquier
        otro rol queda acotado a su institución. Durante "Ver como" el rol
        efectivo es el del objetivo (no admin), así que queda scopeado a la
        institución del objetivo; al salir vuelve a None (admin real).
        """
        from src.services.contexto_tenant import activar_institucion
        scope = None if rol == "admin" else institucion_id
        activar_institucion(scope)

    def guardar(self) -> None:
        """Persiste el contexto completo en app.storage.user."""
        app.storage.user.update({
            "usuario_id":        self.usuario_id,
            "usuario_nombre":    self.usuario_nombre,
            "usuario_rol":       self.usuario_rol,
            "institucion_id":    self.institucion_id,
            "anio_id":           self.anio_id,
            "periodo_id":        self.periodo_id,
            "grupo_id":          self.grupo_id,
            "asignacion_id":     self.asignacion_id,
            "anio_nombre":       self.anio_nombre,
            "periodo_nombre":    self.periodo_nombre,
            "grupo_nombre":      self.grupo_nombre,
            "asignacion_nombre": self.asignacion_nombre,
            "impersonando":      self.impersonando,
            "admin_real_id":     self.admin_real_id,
            "admin_real_nombre": self.admin_real_nombre,
            "admin_real_rol":    self.admin_real_rol,
            "admin_real_institucion_id": self.admin_real_institucion_id,
            "solo_lectura":      self.solo_lectura,
        })
        # Mantener el flag de servicios coherente tras cualquier persistencia.
        self._sincronizar_solo_lectura(self.solo_lectura)
        # Mantener el scope de institución coherente (regla admin→None).
        self._sincronizar_institucion(self.usuario_rol, self.institucion_id)

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

    # ── Impersonación "Ver como" (paso_21) ───────────────────────────────────

    def iniciar_ver_como(
        self,
        target_usuario_id: int,
        target_rol: str,
        target_nombre: str,
        contexto_academico_target: dict | None = None,
        target_institucion_id: int | None = None,
    ) -> None:
        """
        Activa la impersonación en SOLO LECTURA: el admin asume la identidad
        del usuario objetivo conservando su identidad real para volver.

        - Guarda la identidad real del admin (solo si no estaba ya impersonando).
        - Sustituye usuario_id/rol/nombre por los del objetivo.
        - Toma la institución del usuario objetivo (multi-tenant, paso_24); el
          `institucion_id` del admin se restaura al salir.
        - Carga el contexto académico del objetivo si se provee; si no, queda
          incompleto y las pantallas muestran sus empty states.
        - Marca impersonando=True, solo_lectura=True, persiste y audita.
        """
        if not self.impersonando:
            self.admin_real_id     = self.usuario_id
            self.admin_real_nombre = self.usuario_nombre
            self.admin_real_rol    = self.usuario_rol
            # Conservar la institución real del admin para restaurarla al salir.
            self.admin_real_institucion_id = self.institucion_id

        admin_id     = self.admin_real_id
        admin_nombre = self.admin_real_nombre

        self.usuario_id     = target_usuario_id
        self.usuario_rol    = target_rol
        self.usuario_nombre = target_nombre
        self.institucion_id = target_institucion_id

        ctx_target = contexto_academico_target or {}
        self.anio_id           = ctx_target.get("anio_id")
        self.periodo_id        = ctx_target.get("periodo_id")
        self.grupo_id          = ctx_target.get("grupo_id")
        self.asignacion_id     = ctx_target.get("asignacion_id")
        self.anio_nombre       = ctx_target.get("anio_nombre", "")
        self.periodo_nombre    = ctx_target.get("periodo_nombre", "")
        self.grupo_nombre      = ctx_target.get("grupo_nombre", "")
        self.asignacion_nombre = ctx_target.get("asignacion_nombre", "")

        self.impersonando = True
        self.solo_lectura = True
        self.guardar()

        self._auditar_ver_como(
            inicio=True,
            admin_id=admin_id,
            admin_nombre=admin_nombre,
            target_usuario_id=target_usuario_id,
            target_nombre=target_nombre,
            target_rol=target_rol,
        )

    def salir_ver_como(self) -> None:
        """
        Restaura la identidad real del admin y limpia el modo solo lectura.
        Audita el fin de la impersonación.
        """
        if not self.impersonando:
            return

        target_id     = self.usuario_id
        target_nombre = self.usuario_nombre
        target_rol    = self.usuario_rol
        admin_id      = self.admin_real_id
        admin_nombre  = self.admin_real_nombre

        self.usuario_id     = self.admin_real_id
        self.usuario_nombre = self.admin_real_nombre
        self.usuario_rol    = self.admin_real_rol
        self.institucion_id = self.admin_real_institucion_id

        # Limpiar contexto académico del objetivo y estado de impersonación.
        self.anio_id = self.periodo_id = self.grupo_id = self.asignacion_id = None
        self.anio_nombre = self.periodo_nombre = ""
        self.grupo_nombre = self.asignacion_nombre = ""
        self.impersonando      = False
        self.solo_lectura      = False
        self.admin_real_id     = None
        self.admin_real_nombre = ""
        self.admin_real_rol    = ""
        self.admin_real_institucion_id = None
        self.guardar()

        self._auditar_ver_como(
            inicio=False,
            admin_id=admin_id,
            admin_nombre=admin_nombre,
            target_usuario_id=target_id,
            target_nombre=target_nombre,
            target_rol=target_rol,
        )

    @staticmethod
    def _auditar_ver_como(
        *,
        inicio: bool,
        admin_id: int | None,
        admin_nombre: str,
        target_usuario_id: int | None,
        target_nombre: str,
        target_rol: str,
    ) -> None:
        """Registra el evento de inicio/fin de impersonación (append-only)."""
        try:
            from container import Container
            from src.services.auditoria_service import (
                EventoSesion,
                TipoEventoSesion,
            )
            tipo = (
                TipoEventoSesion.VER_COMO_INICIO if inicio
                else TipoEventoSesion.VER_COMO_FIN
            )
            verbo = "inicia" if inicio else "finaliza"
            detalles = (
                f"Admin '{admin_nombre}' (id={admin_id}) {verbo} 'Ver como' "
                f"usuario '{target_nombre}' (id={target_usuario_id}, rol={target_rol})"
            )
            Container.auditoria_service().registrar_evento(
                EventoSesion(
                    usuario     = admin_nombre or "admin",
                    usuario_id  = admin_id,
                    tipo_evento = tipo,
                    detalles    = detalles,
                )
            )
        except Exception:
            # La auditoría no debe bloquear la operación de UI.
            pass

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
