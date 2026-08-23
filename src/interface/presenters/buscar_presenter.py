"""Presenter puro de la página de resultados de búsqueda (`/buscar`).

Sin import de NiceGUI. Guarda el estado del buscador (término, pestaña activa,
página, resultados) y sus transiciones de vista. La regla de negocio —qué tipos
puede buscar cada rol y el mínimo de caracteres— vive en el backend
(`busqueda_service.tipos_buscables` / `TERMINO_MINIMO`); el presenter solo la
consume. El formateo del contador de resultados es presentación → vive aquí.
"""
from __future__ import annotations

from src.services.busqueda_service import TERMINO_MINIMO


class BuscarPresenter:
    """View-model de `/buscar` (estado + transiciones + formato de presentación)."""

    def __init__(self, termino_inicial: str = "") -> None:
        self.estado: dict = {
            "termino": (termino_inicial or "").strip(),
            "tipo_filtro": None,  # None = "Todos"
            "pagina": 1,
            "resultados": None,  # None = aún no se ha buscado
        }

    # ── Transiciones de vista ───────────────────────────────────────────────

    def set_termino(self, valor) -> None:
        """Nuevo término → normaliza y vuelve a la primera página."""
        self.estado["termino"] = str(valor or "").strip()
        self.estado["pagina"] = 1

    def set_tab(self, tipo: str | None) -> None:
        """Cambiar de pestaña de tipo → vuelve a la primera página."""
        self.estado["tipo_filtro"] = tipo
        self.estado["pagina"] = 1

    def set_pagina(self, pagina: int) -> None:
        self.estado["pagina"] = pagina

    def set_resultados(self, resultados) -> None:
        self.estado["resultados"] = resultados

    # ── Consultas ───────────────────────────────────────────────────────────

    def termino_buscable(self) -> bool:
        """True si el término alcanza el mínimo de caracteres (regla del backend)."""
        return len(self.estado["termino"]) >= TERMINO_MINIMO

    def total_texto(self, resultado) -> str:
        """Contador de resultados ya pluralizado (presentación).

        Si hay pestaña activa, cuenta ese tipo; si es "Todos", suma todos.
        """
        if resultado is None:
            return ""
        tipo_filtro = self.estado["tipo_filtro"]
        if tipo_filtro:
            count = resultado.total_por_tipo.get(tipo_filtro, 0)
        else:
            count = sum(resultado.total_por_tipo.values())
        return f"{count} resultado{'s' if count != 1 else ''}"


__all__ = ["BuscarPresenter"]
