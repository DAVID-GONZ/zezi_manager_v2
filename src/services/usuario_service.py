"""
UsuarioService
================
Orquesta los casos de uso del módulo de Usuarios.
"""
from __future__ import annotations

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
)
from src.domain.models.auditoria import AccionCambio, RegistroCambio


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

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    def crear_usuario(
        self,
        dto: NuevoUsuarioDTO,
        creado_por_id: int | None = None,
    ) -> Usuario:
        """
        Crea un usuario nuevo.

        - Verifica que el username no exista.
        - Hashea la contraseña (usa el username si no se provee password).
        - Guarda el usuario y audita la creación.
        """
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

    def cambiar_rol(
        self,
        usuario_id: int,
        nuevo_rol: Rol,
        cambiado_por_id: int | None = None,
    ) -> Usuario:
        """Cambia el rol de un usuario."""
        usuario = self._get_usuario_o_lanzar(usuario_id)
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
        return usuario_actualizado

    def desactivar(
        self,
        usuario_id: int,
        desactivado_por_id: int | None = None,
    ) -> Usuario:
        """Desactiva un usuario (soft delete)."""
        usuario = self._get_usuario_o_lanzar(usuario_id)
        usuario_desactivado = usuario.desactivar()  # lanza si ya está inactivo
        self._repo.desactivar(usuario_id)
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            usuario.model_dump(mode="json"),
            usuario_desactivado.model_dump(mode="json"),
            desactivado_por_id,
        )
        return usuario_desactivado

    def reactivar(
        self,
        usuario_id: int,
        reactivado_por_id: int | None = None,
    ) -> Usuario:
        """Reactiva un usuario desactivado."""
        usuario = self._get_usuario_o_lanzar(usuario_id)
        usuario_reactivado = usuario.reactivar()  # lanza si ya está activo
        self._repo.reactivar(usuario_id)
        self._auditar(
            AccionCambio.UPDATE, "usuarios", usuario_id,
            usuario.model_dump(mode="json"),
            usuario_reactivado.model_dump(mode="json"),
            reactivado_por_id,
        )
        return usuario_reactivado

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

    def get_by_id(self, usuario_id: int) -> Usuario:
        """Retorna un usuario por id. Lanza si no existe."""
        return self._get_usuario_o_lanzar(usuario_id)


__all__ = ["UsuarioService"]
