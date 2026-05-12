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
        self._repo = repo

    def get_principal(self, estudiante_id: int):
        """Retorna el acudiente principal de un estudiante, o None si no existe."""
        return self._repo.get_principal(estudiante_id)

    def listar_por_estudiante(self, estudiante_id: int):
        """Retorna todos los acudientes vinculados a un estudiante."""
        return self._repo.listar_por_estudiante(estudiante_id)


__all__ = ["AcudienteService"]
