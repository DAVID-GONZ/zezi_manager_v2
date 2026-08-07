"""
src/services/aprovisionamiento_institucion_service.py
========================================================
Servicio de aprovisionamiento de un tenant nuevo (mejora_09a).

Orquesta, en una sola operación de admin:
  1. Crear la institución (nace con `configuracion_inicial_completa=False`).
  2. Sembrar sus catálogos estándar + preferencias por defecto
     (`IInstitucionRepository.sembrar_defaults_tenant`, infra→infra).
  3. Crear el usuario director de ese tenant vía `UsuarioService`.

No se reutilizan los servicios scopeados por sesión (`guardar_area`,
`crear_categoria`) porque inyectan `institucion_actual()` (el scope del
admin es `None`); el aprovisionamiento delega en infraestructura con
`institucion_id` explícito.
"""
from __future__ import annotations

from src.domain.models.institucion import (
    Institucion,
    NuevaInstitucionConDirectorDTO,
    ResultadoAprovisionamientoDTO,
)
from src.domain.models.usuario import NuevoUsuarioDTO, Rol
from src.domain.ports.institucion_repo import IInstitucionRepository
from src.services.solo_lectura import requiere_escritura


class AprovisionamientoInstitucionService:
    """Aprovisiona un tenant nuevo (institución + director) para el admin."""

    def __init__(self, institucion_repo: IInstitucionRepository):
        self._repo = institucion_repo

    @requiere_escritura
    def crear_institucion_con_director(
        self,
        dto: NuevaInstitucionConDirectorDTO,
        actor_rol: str | None = None,
    ) -> ResultadoAprovisionamientoDTO:
        """
        Crea una institución nueva con su director y la deja aprovisionada
        (catálogos + preferencias sembrados), marcada como pendiente de
        configuración inicial.

        Lanza `ValueError` si el nombre ya existe o si el actor no tiene
        permiso para crear el rol director (RBAC delegado en UsuarioService).
        """
        if self._repo.existe_nombre(dto.nombre):
            raise ValueError(f"Ya existe una institución con el nombre '{dto.nombre}'.")

        inst = self._repo.guardar(Institucion(
            nombre=dto.nombre,
            nombre_oficial=dto.nombre_oficial,
            codigo_dane=dto.codigo_dane,
            municipio=dto.municipio,
            configuracion_inicial_completa=False,
        ))

        self._repo.sembrar_defaults_tenant(inst.id)

        from container import Container

        director = Container.usuario_service().crear_usuario(
            NuevoUsuarioDTO(
                usuario=dto.director_usuario,
                nombre_completo=dto.director_nombre_completo,
                email=dto.director_email,
                rol=Rol.DIRECTOR,
                institucion_id=inst.id,
            ),
            actor_rol=actor_rol,
        )

        return ResultadoAprovisionamientoDTO(
            institucion=inst,
            director_usuario=director.usuario,
            password_temporal=director.password_temporal,
        )


__all__ = [
    "AprovisionamientoInstitucionService",
    "NuevaInstitucionConDirectorDTO",
    "ResultadoAprovisionamientoDTO",
]
