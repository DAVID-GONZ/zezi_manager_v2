"""Presenter puro del hub de horarios (`/horarios`).

Sin import de NiceGUI. El hub agrupa varias sub-vistas (visualizar/editar la
parrilla, carga masiva, generación, vista docente). El presenter mantiene el
estado completo y las transiciones de navegación primaria (sección, modo/
perspectiva de la parrilla, pestaña de generación). La generación de horarios y
las consultas viven en los servicios.
"""
from __future__ import annotations


class HorariosHubPresenter:
    """View-model del hub de horarios: estado global + navegación primaria."""

    def __init__(self, seccion_inicial: str, dia_hoy_es: str | None) -> None:
        self.estado: dict = {
            # Sección activa
            "seccion": seccion_inicial,
            # Shared / visualizar-editar
            "config": None,
            "anio_id": None,
            "periodo_id": None,
            "grupos": [],
            "docentes": [],
            "escenarios": [],
            "escenario_sel": None,
            "bloques": [],
            "asignaciones": [],
            "parrilla_perspectiva": "Grupo",
            "parrilla_eje_sel": None,
            "parrilla_filtro_areas": None,
            "parrilla_filtro_dias": None,
            "parrilla_modo": "Por entidad",
            "parrilla_dia_maestro": None,
            "grupo_id": None,
            # Carga masiva
            "lote_reporte": None,
            "lote_filas_raw": [],
            # Generar (gen_ prefix)
            "gen_configs": [],
            "gen_config_sel": None,
            "gen_plantillas": [],
            "gen_plantilla_sel": None,
            "gen_franjas_sel": [],
            "gen_resultado": None,
            "gen_datos_preview": None,
            "gen_perspectiva": "Grupo",
            "gen_eje_sel": None,
            "gen_generando": False,
            "gen_anio_id": None,
            "gen_periodo_id": None,
            "gen_error_contexto": None,
            "gen_tab": "generacion",
            # Docente (doc_ prefix)
            "doc_vista_grid": "semana",
            "doc_dia_sel": dia_hoy_es,
            "doc_parrilla_datos": {"dias": [], "franjas": [], "celdas": []},
            "doc_asignaciones": [],
        }

    def set_seccion(self, seccion: str) -> None:
        self.estado["seccion"] = seccion

    def set_parrilla_modo(self, valor: str) -> None:
        self.estado["parrilla_modo"] = valor

    def set_parrilla_perspectiva(self, valor: str) -> None:
        self.estado["parrilla_perspectiva"] = valor

    def set_gen_tab(self, valor: str) -> None:
        self.estado["gen_tab"] = valor


__all__ = ["HorariosHubPresenter"]
