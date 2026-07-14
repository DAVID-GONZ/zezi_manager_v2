"""
src/services/franja_service.py
==============================
Sub-servicio cohesivo del subdominio de Plantillas y Franjas (mejora_01).
Extraído de InfraestructuraService: plantillas de franja + franjas +
activar/eliminar plantilla. Recibe el mismo IInfraestructuraRepository por
inyección; la lógica se movió idéntica (firmas, retornos y `@requiere_escritura`).
"""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.models.infraestructura import DiaSemana, Franja, PlantillaFranja


class FranjaService:

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

    # ── Plantillas de franja (rejilla) ─────────────────────────────────────────

    @requiere_escritura
    def crear_plantilla_simple(
        self,
        nombre: str,
        jornada: str = "UNICA",
        dias: list[str] | None = None,
    ) -> PlantillaFranja:
        """Crea una plantilla a partir de parámetros primitivos (la UI no importa modelos)."""
        from src.domain.models.infraestructura import (
            DIAS_VALIDOS,
            NuevaPlantillaFranjaDTO,
        )
        dto = NuevaPlantillaFranjaDTO(
            nombre=nombre,
            jornada=jornada,
            dias_activos=dias if dias is not None else list(DIAS_VALIDOS[:5]),
        )
        # Multi-tenant (paso_32): asigna la institución del scope (o #1 en
        # seed/arranque) si no viene ya en la plantilla.
        plantilla = dto.to_plantilla()
        institucion_id = self._resolver_institucion(plantilla.institucion_id)
        plantilla = plantilla.model_copy(update={"institucion_id": institucion_id})
        return self._repo.crear_plantilla_franja(plantilla)

    def listar_plantillas(self) -> list[PlantillaFranja]:
        """Lista las plantillas de franja del scope actual (admin ve todas)."""
        # Scope multi-tenant (paso_32): None (admin / arranque) → sin filtro;
        # director → su institución.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.listar_plantillas_franja(
            institucion_id=institucion_actual()
        )

    def plantilla_activa(self, jornada: str = "UNICA") -> PlantillaFranja | None:
        """Retorna la plantilla activa de una jornada para la institución del scope."""
        # Scope multi-tenant (paso_32): la plantilla activa es por institución.
        from src.services.contexto_tenant import institucion_actual
        return self._repo.get_plantilla_activa(
            jornada, institucion_id=institucion_actual()
        )

    @requiere_escritura
    def guardar_franjas(self, plantilla_id: int, filas: list[dict]) -> int:
        """
        Reemplaza el set de franjas de una plantilla. `filas` son dicts con claves
        orden, hora_inicio, hora_fin, tipo, etiqueta (los DTOs se construyen aquí).
        """
        from src.domain.models.infraestructura import NuevaFranjaDTO
        franjas: list[Franja] = []
        for fila in filas:
            dto = NuevaFranjaDTO(
                plantilla_id=plantilla_id,
                orden=fila["orden"],
                hora_inicio=fila["hora_inicio"],
                hora_fin=fila["hora_fin"],
                tipo=fila.get("tipo", "lectiva"),
                etiqueta=fila.get("etiqueta"),
            )
            franjas.append(dto.to_franja())
        return self._repo.reemplazar_franjas(plantilla_id, franjas)

    def listar_franjas(self, plantilla_id: int) -> list[Franja]:
        """Lista las franjas de una plantilla (delegado al repositorio)."""
        return self._repo.listar_franjas(plantilla_id)

    @requiere_escritura
    def activar_plantilla(self, plantilla_id: int) -> None:
        """Marca una plantilla de franja como activa (delegado al repositorio)."""
        return self._repo.activar_plantilla_franja(plantilla_id)

    @requiere_escritura
    def eliminar_plantilla(self, plantilla_id: int) -> bool:
        """Elimina una plantilla tras verificar que pertenece al tenant activo."""
        # Autorización a nivel de objeto (paso_36): la plantilla debe ser del
        # tenant activo (se lee del repo por id; scope None → cross-tenant).
        self._verificar_pertenencia_obj(
            self._repo.get_plantilla_franja(plantilla_id), "La plantilla"
        )
        return self._repo.eliminar_plantilla_franja(plantilla_id)


# Re-export de símbolos de dominio para la capa de interfaz (mejora_05): las
# páginas importan los TIPOS desde su servicio cohesivo, no desde `src.domain`
# (prohibido en `src/interface/pages` por check_imports / convención §2).
__all__ = ["FranjaService", "DiaSemana", "Franja", "PlantillaFranja"]
