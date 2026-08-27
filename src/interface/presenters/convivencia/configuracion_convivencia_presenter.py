"""Presenter puro de configuración de convivencia (`/convivencia/configuracion`).

Sin import de NiceGUI. Guarda el view-state (categorías/plantillas cargadas,
edición y selección de fila) y las computaciones de vista: opciones del select de
categorías y el mapa id→nombre. La persistencia vive en `convivencia_service`.
"""
from __future__ import annotations


class ConfiguracionConvivenciaPresenter:
    """View-model de configuración de convivencia: categorías + plantillas + tipos_situacion."""

    def __init__(self) -> None:
        self.estado: dict = {
            "categorias": [],
            "plantillas": [],
            "tipos_situacion": [],
            "editando_cat": None,
            "editando_plt": None,
            "editando_tipo": None,
            "sel_cat": None,
            "sel_plt": None,
            "sel_tipo": None,
        }

    def reset_selecciones(self) -> None:
        self.estado["sel_cat"] = None
        self.estado["sel_plt"] = None
        self.estado["sel_tipo"] = None

    def set_categorias(self, categorias) -> None:
        self.estado["categorias"] = list(categorias)

    def set_plantillas(self, plantillas) -> None:
        self.estado["plantillas"] = list(plantillas)

    def set_tipos_situacion(self, tipos) -> None:
        self.estado["tipos_situacion"] = list(tipos)

    def opciones_categorias(self) -> dict:
        """{None: 'Sin categoría', cat_id: nombre} — solo categorías activas."""
        opts: dict = {None: "Sin categoría"}
        for cat in self.estado["categorias"]:
            if getattr(cat, "activa", True):
                cat_id = getattr(cat, "id", None)
                if cat_id is not None:
                    opts[cat_id] = getattr(cat, "nombre", "")
        return opts

    def cat_nombre_por_id(self) -> dict:
        return {getattr(c, "id", None): getattr(c, "nombre", "") for c in self.estado["categorias"]}


__all__ = ["ConfiguracionConvivenciaPresenter"]
