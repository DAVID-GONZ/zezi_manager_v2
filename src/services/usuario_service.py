"""
UsuarioService
================
Orquesta los casos de uso del módulo de Usuarios.
"""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from src.domain.ports.usuario_repo import IUsuarioRepository
from src.domain.ports.auditoria_repo import IAuditoriaRepository
from src.domain.ports.service_ports import IAuthenticationService
from src.domain.models.usuario import (
    DocenteInfoDTO,
    FiltroUsuariosDTO,
    NuevoUsuarioDTO,
    ActualizarUsuarioDTO,
    Rol,
    Usuario,
    UsuarioResumenDTO,
    ResumenUsuariosDTO,
)
from src.domain.models.auditoria import (
    AccionCambio,
    EventoSesion,
    RegistroCambio,
    TipoEventoSesion,
)
from src.domain.policies.rbac_usuarios import (
    puede_gestionar,
    roles_asignables,
)


class UsuarioService:
    """
    Orquesta los casos de uso del módulo de Usuarios.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(
        self,
        repo: IUsuarioRepository,
        auth_service: IAuthenticationService | None = None,
        auditoria: IAuditoriaRepository | None = None,
    ) -> None:
        self._repo      = repo
        self._auth      = auth_service
        self._auditoria = auditoria

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _auditar(
        self,
        accion: AccionCambio,
        tabla: str,
        registro_id: int | None,
        datos_ant: dict | None,
        datos_nue: dict | None,
        usuario_id: int | None,
    ) -> None:
        if self._auditoria is None:
            return
        if accion == AccionCambio.CREATE:
            cambio = RegistroCambio.para_creacion(
                tabla, datos_nue or {}, registro_id, usuario_id
            )
        elif accion == AccionCambio.UPDATE:
            cambio = RegistroCambio.para_actualizacion(
                tabla, datos_ant or {}, datos_nue or {}, registro_id, usuario_id
            )
        else:
            cambio = RegistroCambio.para_eliminacion(
                tabla, datos_ant or {}, registro_id, usuario_id
            )
        self._auditoria.registrar_cambio(cambio)

    def _get_usuario_o_lanzar(self, usuario_id: int) -> Usuario:
        usuario = self._repo.get_by_id(usuario_id)
        if usuario is None:
            raise ValueError(f"Usuario con id {usuario_id} no existe.")
        return usuario

    def _registrar_evento(
        self,
        tipo_evento: TipoEventoSesion,
        usuario: Usuario,
        actor_id: int | None,
        detalles: str | None = None,
    ) -> None:
        """Registra un evento de sesión en la auditoría (no-op si no hay repo)."""
        if self._auditoria is None:
            return
        self._auditoria.registrar_evento(
            EventoSesion(
                usuario     = usuario.usuario,
                usuario_id  = usuario.id,
                tipo_evento = tipo_evento,
                detalles    = detalles,
            )
        )

    @staticmethod
    def _verificar_gestion(actor_rol: str | None, target: Usuario) -> None:
        """Defensa en profundidad: valida que el actor pueda gestionar al destino.

        `actor_rol=None` desactiva el enforcement (callers internos / tests).
        """
        if actor_rol is None:
            return
        if not puede_gestionar(actor_rol, target.rol):
            raise ValueError(
                f"Tu rol no tiene permiso para gestionar al usuario "
                f"'{target.usuario}'."
            )

    # ------------------------------------------------------------------
    # Consultas de política (solo lectura) — para gating en la vista
    # ------------------------------------------------------------------

    def roles_asignables(self, actor_rol: str | None) -> set[str]:
        """Roles (strings) que `actor_rol` puede asignar o crear."""
        return roles_asignables(actor_rol)

    def puede_gestionar(self, actor_rol: str | None, target_rol: str) -> bool:
        """True si `actor_rol` puede gestionar a un usuario con rol `target_rol`."""
        if actor_rol is None:
            return False
        return puede_gestionar(actor_rol, target_rol)

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    @requiere_escritura
    def crear_usuario(
        self,
        dto: NuevoUsuarioDTO,
        creado_por_id: int | None = None,
        actor_rol: str | None = None,
    ) -> Usuario:
        """
        Crea un usuario nuevo.

        - Si `actor_rol` se provee, valida que pueda asignar `dto.rol` (RBAC).
        - Verifica que el username no exista.
        - Hashea la contraseña (usa el username si no se provee password).
        - Guarda el usuario y audita la creación.
        """
        if actor_rol is not None:
            rol_str = dto.rol.value if hasattr(dto.rol, "value") else str(dto.rol)
            if rol_str not in roles_asignables(actor_rol):
                raise ValueError(
                    f"Tu rol no tiene permiso para crear usuarios con rol "
                    f"'{rol_str}'."
                )
        if self._repo.existe_usuario(dto.usuario):
            raise ValueError(
                f"Ya existe un usuario con el nombre '{dto.usuario}'."
            )
        usuario = dto.to_usuario()
        usuario = self._repo.guardar(usuario)

        # Hash de contraseña
        if self._auth is not None:
            password = dto.password or dto.usuario
            self._auth.resetear_password(usuario.id, password)

        self._auditar(
            AccionCambio.CREATE, "usuarios", usuario.id,
            None, usuario.model_dump(mode="json"), creado_por_id,
        )
        return usuario

    @requiere_escritura
    def actualizar(
        self,
        usuario_id: int,
        dto: ActualizarUsuarioDTO,
        actualizado_por_id: int | None = None,
    ) -> Usuario:
        """Actualiza nombre completo, email y/o teléfono de un usuario."""
        usuario = self._get_usuario_o_lanzar(usuario_id)
        datos_ant = usuario.model_dump(mode="json")
        usuario_actualizado = dto.aplicar_a(usuario)
        self._repo.actualizar(usuario_actualizado)
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            datos_ant, usuario_actualizado.model_dump(mode="json"),
            actualizado_por_id,
        )
        return usuario_actualizado

    @requiere_escritura
    def cambiar_rol(
        self,
        usuario_id: int,
        nuevo_rol: Rol,
        cambiado_por_id: int | None = None,
        actor_rol: str | None = None,
    ) -> Usuario:
        """Cambia el rol de un usuario.

        Si `actor_rol` se provee, valida (defensa en profundidad) que el actor
        pueda asignar `nuevo_rol` Y pueda gestionar el rol actual del destino.
        """
        usuario = self._get_usuario_o_lanzar(usuario_id)
        if actor_rol is not None:
            self._verificar_gestion(actor_rol, usuario)
            rol_str = (
                nuevo_rol.value if hasattr(nuevo_rol, "value") else str(nuevo_rol)
            )
            if rol_str not in roles_asignables(actor_rol):
                raise ValueError(
                    f"Tu rol no tiene permiso para asignar el rol '{rol_str}'."
                )
        if not usuario.activo:
            raise ValueError(
                f"El usuario '{usuario.usuario}' está desactivado y no puede modificarse."
            )
        datos_ant = usuario.model_dump(mode="json")
        self._repo.cambiar_rol(usuario_id, nuevo_rol)
        usuario_actualizado = usuario.model_copy(update={"rol": nuevo_rol})
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            datos_ant, usuario_actualizado.model_dump(mode="json"),
            cambiado_por_id,
        )
        self._registrar_evento(
            TipoEventoSesion.CAMBIAR_ROL, usuario_actualizado, cambiado_por_id,
            detalles=f"Rol cambiado a '{usuario_actualizado.rol.value}'",
        )
        return usuario_actualizado

    @requiere_escritura
    def desactivar(
        self,
        usuario_id: int,
        desactivado_por_id: int | None = None,
        actor_rol: str | None = None,
    ) -> Usuario:
        """Desactiva un usuario (soft delete).

        Si `actor_rol` se provee, valida que pueda gestionar al destino (RBAC).
        """
        usuario = self._get_usuario_o_lanzar(usuario_id)
        self._verificar_gestion(actor_rol, usuario)
        usuario_desactivado = usuario.desactivar()  # lanza si ya está inactivo
        self._repo.desactivar(usuario_id)
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            usuario.model_dump(mode="json"),
            usuario_desactivado.model_dump(mode="json"),
            desactivado_por_id,
        )
        self._registrar_evento(
            TipoEventoSesion.DESACTIVAR_USUARIO, usuario_desactivado,
            desactivado_por_id,
        )
        return usuario_desactivado

    @requiere_escritura
    def reactivar(
        self,
        usuario_id: int,
        reactivado_por_id: int | None = None,
        actor_rol: str | None = None,
    ) -> Usuario:
        """Reactiva un usuario desactivado.

        Si `actor_rol` se provee, valida que pueda gestionar al destino (RBAC).
        """
        usuario = self._get_usuario_o_lanzar(usuario_id)
        self._verificar_gestion(actor_rol, usuario)
        usuario_reactivado = usuario.reactivar()  # lanza si ya está activo
        self._repo.reactivar(usuario_id)
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            usuario.model_dump(mode="json"),
            usuario_reactivado.model_dump(mode="json"),
            reactivado_por_id,
        )
        self._registrar_evento(
            TipoEventoSesion.ACTIVAR_USUARIO, usuario_reactivado,
            reactivado_por_id,
        )
        return usuario_reactivado

    @requiere_escritura
    def resetear_password(
        self,
        usuario_id: int,
        nueva_password: str,
        actor_rol: str | None = None,
        reset_por_id: int | None = None,
    ) -> None:
        """
        Restablece la contraseña de un usuario SIN verificar la anterior.

        Flujo administrativo (admin/director recuperando una cuenta):
        - Si `actor_rol` se provee, valida que pueda gestionar al destino (RBAC).
        - Si `nueva_password` viene vacía, usa el username como contraseña.
        - Delega el hash al servicio de autenticación.
        - Audita el evento con TipoEventoSesion.RESETEAR_PASSWORD.
        """
        if self._auth is None:
            raise ValueError(
                "El servicio de autenticación no está configurado."
            )
        usuario = self._get_usuario_o_lanzar(usuario_id)
        self._verificar_gestion(actor_rol, usuario)
        password = (nueva_password or "").strip() or usuario.usuario
        self._auth.resetear_password(usuario_id, password)
        self._registrar_evento(
            TipoEventoSesion.RESETEAR_PASSWORD, usuario, reset_por_id,
            detalles=f"Contraseña restablecida para '{usuario.usuario}'",
        )

    @requiere_escritura
    def cambiar_password(
        self,
        usuario_id: int,
        password_actual: str,
        password_nuevo: str,
    ) -> None:
        """
        Cambia la contraseña verificando la actual.
        Lanza ValueError si la contraseña actual es incorrecta.
        """
        if self._auth is None:
            raise ValueError(
                "El servicio de autenticación no está configurado."
            )
        exito = self._auth.cambiar_password(
            usuario_id, password_actual, password_nuevo
        )
        if not exito:
            raise ValueError("La contraseña actual no es correcta.")

    def listar_docentes(
        self,
        periodo_id: int | None = None,
    ) -> list[DocenteInfoDTO]:
        """Retorna los docentes con su carga académica calculada."""
        return self._repo.listar_docentes_info(
            periodo_id=periodo_id, solo_activos=True
        )

    def listar_filtrado(self, filtro: FiltroUsuariosDTO) -> list[Usuario]:
        """Retorna usuarios según los filtros indicados."""
        return self._repo.listar_filtrado(filtro)

    def listar_resumenes(self, filtro: FiltroUsuariosDTO) -> list[UsuarioResumenDTO]:
        """Retorna la vista resumida de usuarios para selects y lookups."""
        return self._repo.listar_resumenes(filtro)

    def listar_para_ver_como(
        self, institucion_id: int | None = None
    ) -> list[UsuarioResumenDTO]:
        """
        Listado de SOLO LECTURA de usuarios activos candidatos a 'Ver como',
        con scope por institución (multi-tenant, paso_24).

        `institucion_id`:
          - None  → todos los usuarios activos (vista de plataforma / admin).
          - int   → solo los usuarios activos de esa institución.

        El filtro se aplica en el repositorio (FiltroUsuariosDTO.institucion_id),
        de modo que el resumen ya viene scopeado por tenant.
        """
        return self._repo.listar_resumenes(
            FiltroUsuariosDTO(
                solo_activos=True,
                por_pagina=200,
                institucion_id=institucion_id,
            )
        )

    def get_by_id(self, usuario_id: int) -> Usuario:
        """Retorna un usuario por id. Lanza si no existe."""
        return self._get_usuario_o_lanzar(usuario_id)

    def resumen_por_rol(self) -> ResumenUsuariosDTO:
        """
        Agregación de SOLO LECTURA para el dashboard de plataforma.

        Cuenta usuarios por rol (incluye inactivos en el total) y expone el
        número de activos. No muta nada.
        """
        todos = self._repo.listar_resumenes(
            FiltroUsuariosDTO(solo_activos=False, por_pagina=200)
        )
        por_rol: dict[str, int] = {}
        activos = 0
        for u in todos:
            rol_str = u.rol.value if hasattr(u.rol, "value") else str(u.rol)
            por_rol[rol_str] = por_rol.get(rol_str, 0) + 1
            if u.activo:
                activos += 1
        return ResumenUsuariosDTO(
            por_rol=por_rol, total=len(todos), activos=activos
        )

    def carga_horaria_max(self, usuario_id: int) -> int | None:
        """Retorna la carga horaria máxima del usuario, o None si no está definida."""
        usuario = self._get_usuario_o_lanzar(usuario_id)
        return usuario.carga_horaria_max

    @requiere_escritura
    def configurar_carga(
        self,
        usuario_id: int,
        carga_horaria_max: int | None,
        horas_extra: int = 0,
        actualizado_por_id: int | None = None,
    ) -> Usuario:
        """Configura el tope semanal y las horas extra de un docente.

        `carga_horaria_max=None` significa sin límite. `horas_extra` amplía el
        tope efectivo. Valida rangos vía el modelo Usuario.
        """
        usuario = self._get_usuario_o_lanzar(usuario_id)
        if carga_horaria_max is not None and carga_horaria_max < 0:
            raise ValueError("La carga máxima no puede ser negativa.")
        if horas_extra < 0:
            raise ValueError("Las horas extra no pueden ser negativas.")
        datos_ant = usuario.model_dump(mode="json")
        self._repo.actualizar_carga(usuario_id, carga_horaria_max, horas_extra)
        actualizado = usuario.model_copy(update={
            "carga_horaria_max": carga_horaria_max,
            "horas_extra": horas_extra,
        })
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            datos_ant, actualizado.model_dump(mode="json"), actualizado_por_id,
        )
        return actualizado


__all__ = ["UsuarioService"]
