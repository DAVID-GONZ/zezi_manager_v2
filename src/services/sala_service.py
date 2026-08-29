"""
src/services/sala_service.py
============================
Sub-servicio cohesivo del subdominio de Salas (mejora_01).
Extraído de InfraestructuraService: CRUD de salas + asignar sala a grupo.
Recibe el mismo IInfraestructuraRepository por inyección; la lógica se movió
idéntica (firmas, tipos de retorno y `@requiere_escritura` intactos).
"""

from __future__ import annotations

from src.domain.models.infraestructura import Sala
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.services.solo_lectura import requiere_escritura


class SalaService:
    def __init__(self, repo: IInfraestructuraRepository) -> None:
        """Inyecta el repositorio de infraestructura."""
        self._repo = repo

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

    # ── Salas (paso_17) ───────────────────────────────────────────────────────

    def listar_salas(self) -> list[Sala]:
        """Lista las salas del scope actual (admin ve todas)."""
        # Scope multi-tenant (paso_32): None (admin / arranque) → sin filtro;
        # director → su institución.
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar_salas(institucion_id=institucion_actual() or "*")

    def get_sala(self, sala_id: int) -> Sala | None:
        """Retorna una sala por id (delegado al repositorio)."""
        return self._repo.get_sala(sala_id)

    @requiere_escritura
    def crear_sala(self, sala: Sala) -> Sala:
        """Crea una sala, asignándole la institución del scope si falta."""
        # Asigna la institución del scope (o #1 en seed/arranque) si no viene ya.
        institucion_id = self._resolver_institucion(sala.institucion_id)
        sala = sala.model_copy(update={"institucion_id": institucion_id})
        return self._repo.crear_sala(sala)

    @requiere_escritura
    def actualizar_sala(self, sala: Sala) -> Sala:
        """Actualiza una sala verificando su tenant y preservando su institución."""
        if sala.id is None:
            raise ValueError("La sala no tiene id.")
        # Autorización a nivel de objeto (paso_36): tenant verificado contra la
        # sala persistida; institución preservada (no se permite mover de tenant).
        actual = self._repo.get_sala(sala.id)
        self._verificar_pertenencia_obj(actual, "La sala")
        sala = sala.model_copy(update={"institucion_id": actual.institucion_id})
        return self._repo.actualizar_sala(sala)

    @requiere_escritura
    def eliminar_sala(self, sala_id: int) -> bool:
        """Elimina una sala tras verificar que pertenece al tenant activo."""
        self._verificar_pertenencia_obj(self._repo.get_sala(sala_id), "La sala")
        return self._repo.eliminar_sala(sala_id)

    @requiere_escritura
    def asignar_sala_a_grupo(self, grupo_id: int, sala_id: int | None) -> bool:
        """Asigna (o quita, con None) el aula propia de un grupo."""
        return self._repo.asignar_sala_a_grupo(grupo_id, sala_id)


# Re-export de símbolos de dominio para la capa de interfaz (mejora_05): las
# páginas importan los TIPOS desde su servicio cohesivo, no desde `src.domain`
# (prohibido en `src/interface/pages` por check_imports / convención §2).
__all__ = ["Sala", "SalaService"]
