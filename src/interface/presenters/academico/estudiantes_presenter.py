"""Presenter puro de la página de estudiantes (`/estudiantes`).

Sin import de NiceGUI. El filtrado es server-side (`estudiante_service` con un
`FiltroEstudiantesDTO`); aquí el view-state son los filtros y el flag
`filtro_tocado`, que distingue "aún no filtró" (página vacía) de "eligió ver
todos". El predicado `hay_filtro_activo` decide si se consulta.
"""
from __future__ import annotations


class EstudiantesPresenter:
    """View-model de estudiantes: filtros + flag de interacción + lista."""

    def __init__(self) -> None:
        self.estado: dict = {
            "estudiantes": [],
            "filtro_grupo_id": None,
            "filtro_estado": None,
            "filtro_piar": None,
            "filtro_busqueda": "",
            "filtro_tocado": False,
            # datos de soporte (los puebla la página)
            "grupos": [],
            "grupos_ids_docente": None,
            "config": None,
            "resultado_masivo": None,
        }

    # ── Transiciones de filtro (marcan filtro_tocado) ───────────────────────

    def set_grupo(self, valor) -> None:
        self.estado.update({"filtro_grupo_id": valor, "filtro_tocado": True})

    def set_estado(self, valor) -> None:
        self.estado.update({"filtro_estado": valor, "filtro_tocado": True})

    def set_piar(self, valor) -> None:
        self.estado.update({"filtro_piar": True if valor else None, "filtro_tocado": True})

    def set_busqueda(self, valor) -> None:
        self.estado.update({"filtro_busqueda": valor, "filtro_tocado": True})

    def set_estudiantes(self, estudiantes) -> None:
        self.estado["estudiantes"] = list(estudiantes)

    # ── Predicado de vista ──────────────────────────────────────────────────

    def hay_filtro_activo(self) -> bool:
        """True si el usuario tocó algún filtro o hay una búsqueda no vacía.

        Sin filtro activo, la página arranca (y permanece) vacía: no se consulta.
        """
        return self.estado["filtro_tocado"] or bool((self.estado["filtro_busqueda"] or "").strip())


__all__ = ["EstudiantesPresenter"]
