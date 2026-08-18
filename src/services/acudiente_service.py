"""
AcudienteService
=================
Orquesta los casos de uso del módulo de Acudientes.
"""

from __future__ import annotations

from src.domain.ports.acudiente_repo import IAcudienteRepository


class AcudienteService:
    """
    Orquesta los casos de uso del módulo de Acudientes.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(self, repo: IAcudienteRepository) -> None:
        """Inyecta el repositorio de acudientes."""
        self._repo = repo

    # ── Resolución de institución (multi-tenant — mejora_07-T4) ─────────────────

    @staticmethod
    def _resolver_institucion(institucion_id: int | None) -> int | None:
        """Resuelve tenant: explícito → sesión → id_por_defecto → None."""
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

    def listar(self, activos_solo: bool = False) -> list:
        """Retorna todos los acudientes del tenant activo."""
        from src.services.contexto_tenant import institucion_actual

        return self._repo.listar(activos_solo=activos_solo, institucion_id=institucion_actual())

    def buscar_por_documento(self, numero: str):
        """Busca un acudiente por documento dentro del tenant activo."""
        from src.services.contexto_tenant import institucion_actual

        return self._repo.buscar_por_documento(numero, institucion_id=institucion_actual())

    def get_principal(self, estudiante_id: int):
        """Retorna el acudiente principal de un estudiante, o None si no existe."""
        return self._repo.get_principal(estudiante_id)

    def listar_por_estudiante(self, estudiante_id: int):
        """Retorna todos los acudientes vinculados a un estudiante."""
        return self._repo.listar_por_estudiante(estudiante_id)


__all__ = ["AcudienteService"]
