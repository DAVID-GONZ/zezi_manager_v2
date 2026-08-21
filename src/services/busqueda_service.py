"""
BusquedaService
================
Orquesta la búsqueda global cross-entidad con scoping estricto por rol.

Reglas de acceso (ver plan de implementación):
  admin       → cross-tenant (todas las instituciones), resultado read-only
  director    → su institución, puede buscar estudiantes + usuarios + grupos + asignaturas
  coordinador → su institución, sin acceso a búsqueda de usuarios
  profesor    → su institución, solo estudiantes y grupos de sus grupos asignados

El servicio NO tiene lógica de presentación ni accede a repositorios directamente.
Delega a los servicios existentes que ya aplican scoping multi-tenant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from src.domain.models.busqueda import (
    ResultadoBusquedaDTO,
    ResultadosBusquedaDTO,
    TipoResultadoBusqueda,
)
from src.domain.models.usuario import FiltroUsuariosDTO, Rol

if TYPE_CHECKING:
    from src.domain.models.estudiante import FiltroEstudiantesDTO
    from src.services.asignacion_service import AsignacionService
    from src.services.catalogo_academico_service import CatalogoAcademicoService
    from src.services.estudiante_service import EstudianteService
    from src.services.usuario_service import UsuarioService

_ICONO: dict[TipoResultadoBusqueda, str] = {
    TipoResultadoBusqueda.ESTUDIANTE: "person",
    TipoResultadoBusqueda.USUARIO: "manage_accounts",
    TipoResultadoBusqueda.GRUPO: "groups",
    TipoResultadoBusqueda.ASIGNATURA: "book",
}

_TERMINO_MINIMO = 2


class BusquedaService:
    """Búsqueda global con scoping por rol. No es un repositorio."""

    def __init__(
        self,
        estudiante_svc_provider: Callable[[], EstudianteService],
        usuario_svc_provider: Callable[[], UsuarioService],
        catalogo_svc_provider: Callable[[], CatalogoAcademicoService],
        asignacion_svc_provider: Callable[[], AsignacionService],
    ) -> None:
        self._est_svc = estudiante_svc_provider
        self._usr_svc = usuario_svc_provider
        self._cat_svc = catalogo_svc_provider
        self._asig_svc = asignacion_svc_provider

    # ──────────────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────────────

    def buscar_rapido(
        self,
        termino: str,
        *,
        rol: str,
        usuario_id: int,
        limite_por_tipo: int = 5,
    ) -> ResultadosBusquedaDTO:
        """Búsqueda rápida para el dropdown del topbar. Máx `limite_por_tipo` por entidad."""
        termino = termino.strip()
        if len(termino) < _TERMINO_MINIMO:
            return ResultadosBusquedaDTO(termino=termino)

        resultados: list[ResultadoBusquedaDTO] = []
        total_por_tipo: dict[str, int] = {}

        for tipo, items in self._ejecutar_busqueda(termino, rol=rol, usuario_id=usuario_id):
            total_por_tipo[tipo.value] = len(items)
            resultados.extend(items[:limite_por_tipo])

        limitado = any(v > limite_por_tipo for v in total_por_tipo.values())
        return ResultadosBusquedaDTO(
            termino=termino,
            resultados=resultados,
            total_por_tipo=total_por_tipo,
            limitado=limitado,
        )

    def buscar_completo(
        self,
        termino: str,
        *,
        rol: str,
        usuario_id: int,
        tipo_filtro: TipoResultadoBusqueda | None = None,
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> ResultadosBusquedaDTO:
        """Búsqueda paginada para la página /buscar con todos los resultados."""
        termino = termino.strip()
        if len(termino) < _TERMINO_MINIMO:
            return ResultadosBusquedaDTO(termino=termino)

        todos: list[ResultadoBusquedaDTO] = []
        total_por_tipo: dict[str, int] = {}

        for tipo, items in self._ejecutar_busqueda(termino, rol=rol, usuario_id=usuario_id):
            if tipo_filtro is None or tipo == tipo_filtro:
                todos.extend(items)
            total_por_tipo[tipo.value] = len(items)

        offset = (pagina - 1) * por_pagina
        pagina_resultados = todos[offset : offset + por_pagina]
        return ResultadosBusquedaDTO(
            termino=termino,
            resultados=pagina_resultados,
            total_por_tipo=total_por_tipo,
            limitado=len(todos) > offset + por_pagina,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────────────────────────────────

    def _ejecutar_busqueda(
        self,
        termino: str,
        *,
        rol: str,
        usuario_id: int,
    ) -> list[tuple[TipoResultadoBusqueda, list[ResultadoBusquedaDTO]]]:
        """Ejecuta la búsqueda en todas las entidades permitidas para el rol."""
        grupos_ids_docente: list[int] | None = None
        if rol == Rol.PROFESOR:
            asignaciones = self._asig_svc().listar_por_docente(usuario_id)
            grupos_ids_docente = list({a.grupo_id for a in asignaciones})

        resultados: list[tuple[TipoResultadoBusqueda, list[ResultadoBusquedaDTO]]] = []

        resultados.append((
            TipoResultadoBusqueda.ESTUDIANTE,
            self._buscar_estudiantes(termino, rol=rol, grupos_ids=grupos_ids_docente),
        ))

        if rol in (Rol.ADMIN, Rol.DIRECTOR):
            resultados.append((
                TipoResultadoBusqueda.USUARIO,
                self._buscar_usuarios(termino),
            ))

        resultados.append((
            TipoResultadoBusqueda.GRUPO,
            self._buscar_grupos(termino, rol=rol, grupos_ids=grupos_ids_docente),
        ))

        if rol in (Rol.ADMIN, Rol.DIRECTOR, Rol.COORDINADOR):
            resultados.append((
                TipoResultadoBusqueda.ASIGNATURA,
                self._buscar_asignaturas(termino),
            ))

        return resultados

    def _buscar_estudiantes(
        self,
        termino: str,
        *,
        rol: str,
        grupos_ids: list[int] | None,
    ) -> list[ResultadoBusquedaDTO]:
        from src.domain.models.estudiante import FiltroEstudiantesDTO

        filtro = FiltroEstudiantesDTO(busqueda=termino, por_pagina=100)
        if rol == Rol.PROFESOR:
            # grupos_ids vacío → docente sin asignaciones → sin resultados
            filtro = filtro.model_copy(update={"grupos_ids": grupos_ids or []})

        estudiantes = self._est_svc().listar_filtrado(filtro)
        return [
            ResultadoBusquedaDTO(
                tipo=TipoResultadoBusqueda.ESTUDIANTE,
                id=e.id,
                titulo=e.nombre_completo,
                subtitulo=e.documento_display,
                icono=_ICONO[TipoResultadoBusqueda.ESTUDIANTE],
                ruta=f"/estudiantes?busqueda={e.numero_documento}",
            )
            for e in estudiantes
            if e.id is not None
        ]

    def _buscar_usuarios(self, termino: str) -> list[ResultadoBusquedaDTO]:
        filtro = FiltroUsuariosDTO(busqueda=termino, solo_activos=False, por_pagina=50)
        usuarios = self._usr_svc().listar_filtrado(filtro)
        return [
            ResultadoBusquedaDTO(
                tipo=TipoResultadoBusqueda.USUARIO,
                id=u.id,
                titulo=u.nombre_completo,
                subtitulo=f"{u.rol.value.capitalize()} · @{u.usuario}",
                icono=_ICONO[TipoResultadoBusqueda.USUARIO],
                ruta=f"/admin/usuarios?busqueda={u.usuario}",
            )
            for u in usuarios
            if u.id is not None
        ]

    def _buscar_grupos(
        self,
        termino: str,
        *,
        rol: str,
        grupos_ids: list[int] | None,
    ) -> list[ResultadoBusquedaDTO]:
        termino_lower = termino.lower()
        grupos = self._cat_svc().listar_grupos()
        coincidencias = [
            g for g in grupos
            if termino_lower in (g.codigo or "").lower()
            or termino_lower in (g.nombre or "").lower()
        ]
        if rol == Rol.PROFESOR and grupos_ids is not None:
            ids_set = set(grupos_ids)
            coincidencias = [g for g in coincidencias if g.id in ids_set]

        return [
            ResultadoBusquedaDTO(
                tipo=TipoResultadoBusqueda.GRUPO,
                id=g.id,
                titulo=g.codigo,
                subtitulo=g.nombre or f"Grado {g.grado}" if g.grado else g.nombre or "",
                icono=_ICONO[TipoResultadoBusqueda.GRUPO],
                ruta="/admin/grupos",
            )
            for g in coincidencias
            if g.id is not None
        ]

    def _buscar_asignaturas(self, termino: str) -> list[ResultadoBusquedaDTO]:
        termino_lower = termino.lower()
        asignaturas = self._cat_svc().listar_asignaturas()
        coincidencias = [
            a for a in asignaturas
            if termino_lower in a.nombre.lower()
            or termino_lower in (a.codigo or "").lower()
        ]
        return [
            ResultadoBusquedaDTO(
                tipo=TipoResultadoBusqueda.ASIGNATURA,
                id=a.id,
                titulo=a.nombre,
                subtitulo=a.codigo or "",
                icono=_ICONO[TipoResultadoBusqueda.ASIGNATURA],
                ruta="/admin/asignaturas",
            )
            for a in coincidencias
            if a.id is not None
        ]
