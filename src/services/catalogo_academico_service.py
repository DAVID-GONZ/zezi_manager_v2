"""
src/services/catalogo_academico_service.py
===========================================
Sub-servicio cohesivo del subdominio de Catálogo académico (mejora_01).
Extraído de InfraestructuraService: CRUD de AreaConocimiento, Asignatura y
Grupo. Recibe el mismo IInfraestructuraRepository por inyección; la lógica se
movió idéntica (firmas, retornos y `@requiere_escritura` en los mutadores).
"""
from __future__ import annotations

from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    Grupo,
)
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.services.solo_lectura import requiere_escritura


class CatalogoAcademicoService:

    def __init__(
        self,
        repo: IInfraestructuraRepository,
        asignacion_svc_provider=None,
    ) -> None:
        """Inyecta el repositorio de infraestructura y un provider lazy del
        servicio de asignaciones (usado solo para director de grupo:
        candidatos/validación). El provider evita acoplar el composition root a
        una dependencia circular y deja los tests con repos falsos sin él."""
        self._repo = repo
        # Provider lazy (callable que retorna AsignacionService) — se resuelve
        # bajo demanda en los métodos de director de grupo (convivencia_02).
        self._asignacion_svc_provider = asignacion_svc_provider

    # ── Resolución de institución (multi-tenant — paso_29, frente B1) ──────────

    @staticmethod
    def _resolver_institucion(institucion_id: int | None) -> int | None:
        """
        Resuelve el tenant en este orden (espejo de configuracion_service):
          1. `institucion_id` explícito (el caller manda y no se toca).
          2. `institucion_actual()` — scope de la sesión (director → su
             institución; admin → None, ve todo).
          3. `id_por_defecto()` (#1) — fallback de arranque/seed sin sesión.

        Devuelve None si no hay catálogo de instituciones todavía (single-tenant
        temprano) o si el Container no está disponible (tests con repos falsos).
        """
        if institucion_id is not None:
            return institucion_id
        from src.services.contexto_tenant import institucion_actual
        scope = institucion_actual()
        if scope is not None:
            return scope
        try:
            from container import Container
            return Container.institucion_service().id_por_defecto()
        except Exception:
            return None

    # ── Autorización a nivel de objeto (paso_36 — hallazgo E) ───────────────────

    @staticmethod
    def _verificar_pertenencia_obj(obj, etiqueta: str) -> None:
        """
        Verifica que `obj` (leído del repo por su id) pertenezca a la institución
        activa. `obj` None → ValueError (no existe). Scope None (admin/seed) → pasa.
        """
        if obj is None:
            raise ValueError(f"{etiqueta} no existe.")
        from src.services.contexto_tenant import verificar_pertenencia
        verificar_pertenencia(obj.institucion_id)

    # ── Áreas ─────────────────────────────────────────────────────────────────

    def listar_areas(self) -> list[AreaConocimiento]:
        """Lista las áreas del tenant activo (o todas si admin/sin sesión)."""
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_areas(institucion_id=institucion_actual())

    @requiere_escritura
    def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        """Crea un área inyectando el tenant resuelto si no está explícito."""
        inst_id = self._resolver_institucion(area.institucion_id)
        if inst_id != area.institucion_id:
            area = area.model_copy(update={"institucion_id": inst_id})
        return self._repo.guardar_area(area)

    @requiere_escritura
    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        """Actualiza un área verificando pertenencia al tenant."""
        actual = self._repo.get_area(area.id)
        self._verificar_pertenencia_obj(actual, "El área")
        return self._repo.actualizar_area(area)

    @requiere_escritura
    def eliminar_area(self, area_id: int) -> bool:
        """Elimina un área de conocimiento (delegado al repositorio)."""
        return self._repo.eliminar_area(area_id)

    @requiere_escritura
    def set_color_area(self, area_id: int, color: str | None) -> bool:
        """Asigna (o limpia) el color hex de un área. Valida vía el modelo."""
        normalizado = AreaConocimiento(id=area_id, nombre="_", color=color).color
        return self._repo.actualizar_color_area(area_id, normalizado)

    # ── Asignaturas ───────────────────────────────────────────────────────────

    def listar_asignaturas(self, area_id: int | None = None) -> list[Asignatura]:
        """Lista las asignaturas del scope actual, opcionalmente filtradas por área."""
        # Scope multi-tenant (paso_29): None (admin / arranque) → sin filtro de
        # institución (ve todo); director → su institución. NO se cae al
        # id_por_defecto aquí: admin debe ver todas las instituciones.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_asignaturas(
            area_id=area_id, institucion_id=institucion_actual()
        )

    @requiere_escritura
    def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        """Crea una asignatura, asignándole la institución del scope si falta."""
        # Asigna la institución del scope (o #1 en seed/arranque) si no viene ya.
        institucion_id = self._resolver_institucion(asignatura.institucion_id)
        asignatura = asignatura.model_copy(update={"institucion_id": institucion_id})
        return self._repo.guardar_asignatura(asignatura)

    @requiere_escritura
    def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        """Actualiza una asignatura verificando su tenant y preservando su institución."""
        # Autorización a nivel de objeto (paso_36): se lee la asignatura
        # persistida por id y se verifica su tenant; NO se confía en el
        # institucion_id del objeto recibido (podría venir forjado). Además se
        # preserva la institución existente (un update no puede mover de tenant).
        actual = self._repo.get_asignatura(asignatura.id)
        self._verificar_pertenencia_obj(actual, "La asignatura")
        asignatura = asignatura.model_copy(
            update={"institucion_id": actual.institucion_id}
        )
        return self._repo.actualizar_asignatura(asignatura)

    @requiere_escritura
    def eliminar_asignatura(self, asignatura_id: int) -> bool:
        """Elimina una asignatura tras verificar que pertenece al tenant activo."""
        self._verificar_pertenencia_obj(
            self._repo.get_asignatura(asignatura_id), "La asignatura"
        )
        return self._repo.eliminar_asignatura(asignatura_id)

    # ── Grupos ────────────────────────────────────────────────────────────────

    def get_grupo(self, grupo_id: int) -> Grupo | None:
        """Lee un grupo por id (lectura; sin scope de escritura)."""
        return self._repo.get_grupo(grupo_id)

    def listar_grupos(self, grado: int | None = None) -> list[Grupo]:
        """Lista los grupos del scope actual, opcionalmente filtrados por grado."""
        # Scope multi-tenant (paso_29): None (admin / arranque) → sin filtro;
        # director → su institución.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_grupos(
            grado=grado, institucion_id=institucion_actual()
        )

    @requiere_escritura
    def guardar_grupo(self, grupo: Grupo) -> Grupo:
        """Crea un grupo, asignándole la institución del scope si falta."""
        # Asigna la institución del scope (o #1 en seed/arranque) si no viene ya.
        institucion_id = self._resolver_institucion(grupo.institucion_id)
        grupo = grupo.model_copy(update={"institucion_id": institucion_id})
        return self._repo.guardar_grupo(grupo)

    @requiere_escritura
    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        """Actualiza un grupo verificando su tenant y preservando su institución."""
        # Autorización a nivel de objeto (paso_36): tenant verificado contra el
        # grupo persistido; institución preservada (no se permite mover de tenant).
        actual = self._repo.get_grupo(grupo.id)
        self._verificar_pertenencia_obj(actual, "El grupo")
        grupo = grupo.model_copy(update={"institucion_id": actual.institucion_id})
        return self._repo.actualizar_grupo(grupo)

    @requiere_escritura
    def eliminar_grupo(self, grupo_id: int) -> bool:
        """Elimina un grupo tras verificar que pertenece al tenant activo."""
        self._verificar_pertenencia_obj(
            self._repo.get_grupo(grupo_id), "El grupo"
        )
        return self._repo.eliminar_grupo(grupo_id)

    # ── Director de grupo (convivencia_02) ──────────────────────────────────────

    def candidatos_director_grupo(self, grupo_id: int) -> dict[int, str]:
        """Docentes elegibles como director del grupo = docentes con asignación
        ACTIVA en el grupo, como mapa {usuario_id: nombre} listo para el selector.

        La fuente son las asignaciones (AsignacionInfo) del grupo, resueltas por
        el servicio de asignaciones inyectado; se deduplica por docente (un
        docente puede dictar varias materias en el mismo grupo). Sin provider
        (tests con repos falsos que no lo pasan) → mapa vacío.
        """
        if self._asignacion_svc_provider is None:
            return {}
        asignacion_svc = self._asignacion_svc_provider()
        if asignacion_svc is None:
            return {}
        infos = asignacion_svc.listar_por_grupo(grupo_id, solo_activas=True)
        # dict dedup por usuario_id preservando el nombre resuelto por JOIN.
        return {info.usuario_id: info.docente_nombre for info in infos}

    @requiere_escritura
    def asignar_director_grupo(
        self, grupo_id: int, usuario_id: int | None
    ) -> Grupo:
        """Asigna (o quita, con `usuario_id=None`) el director de un grupo.

        Verifica el tenant del grupo (autorización a nivel de objeto, paso_36) y,
        si `usuario_id` no es None, exige que ese docente sea un candidato válido
        (con asignación activa en el grupo) antes de persistir. La institución del
        grupo se preserva. Retorna el grupo actualizado.
        """
        actual = self._repo.get_grupo(grupo_id)
        self._verificar_pertenencia_obj(actual, "El grupo")
        if usuario_id is not None:
            candidatos = self.candidatos_director_grupo(grupo_id)
            if usuario_id not in candidatos:
                raise ValueError(
                    "El docente seleccionado no tiene una asignación activa en "
                    "este grupo; no puede ser su director de grupo."
                )
            # Unicidad (convivencia_02b): un docente dirige un solo grupo. Si ya
            # es director_grupo_id de OTRO grupo (id distinto) → bloquear. Cambiar
            # el director del MISMO grupo (reemplazo) sigue permitido.
            otro = next(
                (
                    g
                    for g in self.listar_grupos()
                    if g.director_grupo_id == usuario_id and g.id != grupo_id
                ),
                None,
            )
            if otro is not None:
                nombre = candidatos.get(usuario_id, "seleccionado")
                raise ValueError(
                    f"El docente {nombre} ya es director del grupo "
                    f"'{otro.descripcion_corta}'; un docente solo puede dirigir "
                    "un grupo."
                )
        grupo_act = actual.model_copy(update={"director_grupo_id": usuario_id})
        return self._repo.actualizar_grupo(grupo_act)

    # ── Autorización por objeto: director de grupo (convivencia_03) ─────────────

    def es_director_de_grupo(self, usuario_id: int, grupo_id: int) -> bool:
        """True si `usuario_id` es el director del grupo `grupo_id`.

        Resolución de datos que consume la política pura
        `rbac_convivencia.puede_gestionar_comportamiento`. Lee el grupo por id y
        compara su `director_grupo_id`. Grupo inexistente (o `usuario_id`/
        `director_grupo_id` None) → False, sin excepción.
        """
        if usuario_id is None:
            return False
        grupo = self._repo.get_grupo(grupo_id)
        if grupo is None or grupo.director_grupo_id is None:
            return False
        return grupo.director_grupo_id == usuario_id

    def puede_gestionar_comportamiento_en_grupo(
        self, usuario_rol: object, usuario_id: int, grupo_id: int
    ) -> bool:
        """Conveniencia: combina la resolución de datos (¿es director de este
        grupo?) con la política pura de convivencia.

        directivos (director / coordinador) pasan siempre; profesor solo si
        dirige el grupo `grupo_id`. admin NO gestiona en nombre propio (auditor
        técnico); lo hace vía impersonación con el rol efectivo del objetivo.
        Fuente única de verdad consultable desde servicio y vista (defensa en
        profundidad).

        Nota: la variante por-estudiante (`es_director_de_grupo_de_estudiante`)
        se añadirá en convivencia_04, cuando se resuelva el grupo del estudiante
        desde su servicio; aquí no hay acceso trivial a esa relación.
        """
        from src.domain.policies.rbac_convivencia import (
            puede_gestionar_comportamiento,
        )
        return puede_gestionar_comportamiento(
            usuario_rol, self.es_director_de_grupo(usuario_id, grupo_id)
        )


# Re-export de símbolos de dominio para la capa de interfaz (mejora_05): las
# páginas importan los TIPOS desde su servicio cohesivo, no desde `src.domain`
# (prohibido en `src/interface/pages` por check_imports / convención §2).
__all__ = ["AreaConocimiento", "Asignatura", "CatalogoAcademicoService", "Grupo"]
