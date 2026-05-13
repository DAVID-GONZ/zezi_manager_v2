"""
Port: IUsuarioRepository
==========================
Contrato de acceso a datos para el módulo de usuarios.

Cubre:
  Usuario              — entidad persistida (datos personales, rol, estado)
  DocenteInfoDTO       — read model con estadísticas de carga académica
  AsignacionDocenteInfoDTO — detalle de asignaciones de un docente
  UsuarioResumenDTO    — vista mínima para selects y lookups

Principios:
  - Soft delete: los usuarios no se eliminan, se desactivan (activo=False).
  - El username no se actualiza nunca — es el identificador de inicio de sesión.
  - Las contraseñas las gestiona exclusivamente IAuthenticationService;
    este repositorio nunca recibe ni expone password_hash.
  - DocenteInfoDTO se construye por JOIN con asignaciones y horarios;
    el repositorio ejecuta el JOIN, los servicios consumen el read model.

Patrones de uso principales:

  Crear un usuario:
    if repo.existe_usuario(dto.usuario):
        raise ValueError("El nombre de usuario ya existe.")
    usuario = repo.guardar(dto.to_usuario())

  Listar docentes con su carga:
    docentes = repo.listar_docentes_info(periodo_id=periodo_activo.id)

  Obtener selector de docentes para asignar:
    opciones = repo.listar_resumenes(FiltroUsuariosDTO(
        rol=Rol.PROFESOR, solo_activos=True
    ))
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.usuario import (
    AsignacionDocenteInfoDTO,
    DocenteInfoDTO,
    FiltroUsuariosDTO,
    Rol,
    Usuario,
    UsuarioResumenDTO,
)


class IUsuarioRepository(ABC):

    # =========================================================================
    # Lectura — usuarios
    # =========================================================================

    @abstractmethod
    def get_by_id(self, usuario_id: int) -> Usuario | None:
        """Retorna el usuario con ese id, o None si no existe."""
        ...

    @abstractmethod
    def get_by_username(self, username: str) -> Usuario | None:
        """
        Busca un usuario por su nombre de usuario (case-insensitive).
        Usado en el proceso de autenticación.
        Retorna None si no existe o está desactivado.
        """
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> Usuario | None:
        """
        Busca un usuario por email. Retorna None si no existe.
        Usado para recuperación de contraseña y deduplicación.
        """
        ...

    @abstractmethod
    def existe_usuario(self, username: str) -> bool:
        """
        True si ya existe un usuario con ese nombre de usuario.
        El servicio verifica esto antes de insertar para emitir un
        error útil antes de llegar al UNIQUE constraint de la BD.
        """
        ...

    @abstractmethod
    def listar_filtrado(
        self,
        filtro: FiltroUsuariosDTO,
    ) -> list[Usuario]:
        """
        Retorna usuarios según los filtros indicados.
        Ordenados por nombre_completo.
        Soporta paginación mediante filtro.pagina y filtro.por_pagina.
        """
        ...

    @abstractmethod
    def listar_resumenes(
        self,
        filtro: FiltroUsuariosDTO,
    ) -> list[UsuarioResumenDTO]:
        """
        Versión optimizada para selects y lookups: retorna solo los campos
        necesarios para identificar a un usuario en la UI.
        """
        ...

    # =========================================================================
    # Lectura — read models docentes
    # =========================================================================

    @abstractmethod
    def listar_docentes_info(
        self,
        periodo_id: int | None = None,
        solo_activos: bool = True,
    ) -> list[DocenteInfoDTO]:
        """
        Retorna los docentes con su carga académica calculada por JOIN.
        Si periodo_id es None, agrega la carga de todos los periodos activos.
        Es la query principal del grid de gestión de docentes.
        Ordenados por nombre_completo.
        """
        ...

    @abstractmethod
    def get_docente_info(
        self,
        usuario_id: int,
        periodo_id: int | None = None,
    ) -> DocenteInfoDTO | None:
        """
        Retorna la vista estadística de un docente específico.
        None si el usuario no existe o no es docente.
        """
        ...

    @abstractmethod
    def listar_asignaciones_docente(
        self,
        usuario_id: int,
        periodo_id: int | None = None,
    ) -> list[AsignacionDocenteInfoDTO]:
        """
        Retorna el detalle de las asignaciones de un docente, con la
        comparativa de horas teóricas vs. horas programadas en horario.
        Usado en el perfil de docente y en el modal de asignaciones.
        """
        ...

    # =========================================================================
    # Escritura
    # =========================================================================

    @abstractmethod
    def guardar(self, usuario: Usuario) -> Usuario:
        """
        Inserta un usuario nuevo. Retorna la entidad con id asignado.
        El servicio debe verificar unicidad de username con `existe_usuario`.
        La contraseña se gestiona por separado en IAuthenticationService.
        """
        ...

    @abstractmethod
    def actualizar(self, usuario: Usuario) -> Usuario:
        """
        Actualiza nombre_completo, email y teléfono de un usuario.
        No actualiza username ni rol — use `cambiar_rol` para eso.
        Requiere que usuario.id no sea None.
        """
        ...

    @abstractmethod
    def cambiar_rol(self, usuario_id: int, nuevo_rol: Rol) -> bool:
        """
        Cambia el rol de un usuario.
        Retorna True si la fila fue afectada.
        El servicio debe registrar el cambio en auditoría.
        """
        ...

    @abstractmethod
    def desactivar(self, usuario_id: int) -> bool:
        """
        Marca el usuario como inactivo (activo=False, soft-delete).
        Retorna True si la fila fue afectada.
        El usuario no puede iniciar sesión mientras esté inactivo.
        """
        ...

    @abstractmethod
    def reactivar(self, usuario_id: int) -> bool:
        """
        Marca el usuario como activo (activo=True).
        Retorna True si la fila fue afectada.
        """
        ...

    # =========================================================================
    # Credenciales — uso exclusivo de IAuthenticationService
    # =========================================================================

    @abstractmethod
    def get_password_hash(self, usuario_id: int) -> str | None:
        """
        Retorna el hash de contraseña almacenado para el usuario.
        None si el usuario no existe.
        Solo debe llamarse desde IAuthenticationService — nunca exponer
        el hash en capas superiores.
        """
        ...

    @abstractmethod
    def actualizar_password_hash(self, usuario_id: int, nuevo_hash: str) -> bool:
        """
        Persiste el hash de contraseña en la BD.
        Retorna True si la fila fue afectada.
        Solo debe llamarse desde IAuthenticationService.
        """
        ...


__all__ = ["IUsuarioRepository"]
