"""Presenter puro del hub de horarios (`/horarios`).

Sin import de NiceGUI. El hub agrupa varias sub-vistas (visualizar/editar la
parrilla, carga masiva, generación, vista docente). El presenter mantiene el
estado completo, las transiciones de navegación primaria, las propiedades
computadas derivadas del estado y las utilidades de visualización.
La generación de horarios y las consultas viven en los servicios.
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
            # Preparación embebida en "Generar" (prep_ prefix, T13)
            "prep_reporte": [],
            "prep_error": None,
            "prep_config_id": None,
            # Docente (doc_ prefix)
            "doc_vista_grid": "semana",
            "doc_dia_sel": dia_hoy_es,
            "doc_parrilla_datos": {"dias": [], "franjas": [], "celdas": []},
            "doc_asignaciones": [],
        }

    # ------------------------------------------------------------------
    # Utilidades estáticas de visualización
    # ------------------------------------------------------------------

    @staticmethod
    def texto_error(exc: Exception) -> str:
        """Mensaje legible para un toast a partir de una excepción.

        Extrae sólo los mensajes del validador Pydantic, sin ruido técnico.
        """
        errores = getattr(exc, "errors", None)
        if callable(errores):
            try:
                mensajes = [
                    str(e.get("msg", "")).split("Value error, ", 1)[-1].strip()
                    for e in exc.errors()
                ]
                mensajes = [m for m in mensajes if m]
                if mensajes:
                    return " · ".join(mensajes)
            except Exception:
                pass
        return str(exc)

    @staticmethod
    def magnitud_peso(v: float) -> str:
        """Traduce un peso 0.0–2.0 a una etiqueta entendible para el usuario."""
        if v <= 0.0:
            return "Ignorar"
        if v < 0.8:
            return "Bajo"
        if v < 1.4:
            return "Medio"
        if v < 2.0:
            return "Alto"
        return "Máximo"

    # ------------------------------------------------------------------
    # Propiedades computadas del view-model
    # ------------------------------------------------------------------

    def mapa_plantillas(self) -> dict:
        """Devuelve {plantilla_id: nombre} para las plantillas cargadas."""
        return {
            p.id: p.nombre
            for p in self.estado["gen_plantillas"]
            if getattr(p, "id", None) is not None
        }

    def filas_franjas_actuales(self) -> list[dict]:
        """Serializa las franjas seleccionadas a lista de dicts para el servicio."""
        return [
            {
                "orden": f.orden,
                "hora_inicio": f.hora_inicio,
                "hora_fin": f.hora_fin,
                "tipo": f.tipo if isinstance(f.tipo, str) else f.tipo.value,
                "etiqueta": f.etiqueta,
            }
            for f in self.estado["gen_franjas_sel"]
        ]

    def plantillas_en_uso(self, plantilla_id: int) -> list:
        """Retorna las configuraciones que usan la plantilla dada."""
        return [
            c
            for c in self.estado["gen_configs"]
            if getattr(c, "plantilla_id", None) == plantilla_id
        ]

    # ------------------------------------------------------------------
    # Transiciones de estado — navegación primaria
    # ------------------------------------------------------------------

    def set_seccion(self, seccion: str) -> None:
        self.estado["seccion"] = seccion

    def set_parrilla_modo(self, valor: str) -> None:
        self.estado["parrilla_modo"] = valor

    def set_parrilla_perspectiva(self, valor: str) -> None:
        self.estado["parrilla_perspectiva"] = valor
        self.estado["parrilla_eje_sel"] = None  # reset eje al cambiar perspectiva

    def set_parrilla_eje(self, valor) -> None:
        self.estado["parrilla_eje_sel"] = valor

    def set_dia_maestro(self, valor: str) -> None:
        self.estado["parrilla_dia_maestro"] = valor

    def set_filtro_areas(self, valores) -> None:
        self.estado["parrilla_filtro_areas"] = set(valores) if valores else None

    def set_filtro_dias(self, valores) -> None:
        self.estado["parrilla_filtro_dias"] = set(valores) if valores else None

    def set_doc_vista(self, valor: str) -> None:
        self.estado["doc_vista_grid"] = valor

    def set_doc_dia(self, dia: str) -> None:
        self.estado["doc_dia_sel"] = dia

    def set_gen_tab(self, valor: str) -> None:
        self.estado["gen_tab"] = valor

    def set_gen_perspectiva(self, valor: str) -> None:
        self.estado["gen_perspectiva"] = valor
        self.estado["gen_eje_sel"] = None  # reset eje al cambiar perspectiva

    def set_gen_eje(self, valor) -> None:
        self.estado["gen_eje_sel"] = valor

    def seleccionar_gen_config(self, config_id: int | None, configs: list) -> None:
        """Selecciona una configuración de generación y reinicia el resultado."""
        if config_id is None:
            self.estado["gen_config_sel"] = None
        else:
            self.estado["gen_config_sel"] = next(
                (c for c in configs if c.id == config_id), None
            )
        self.estado["gen_resultado"] = None
        self.estado["gen_datos_preview"] = None
        self.estado["gen_eje_sel"] = None

    def set_prep_reporte(
        self, reporte: list, error: str | None, config_id: int | None
    ) -> None:
        """Guarda el view-model del panel de preparación (T13).

        El cómputo de las puertas vive en `PreparacionHorarioService`
        (`validar_config` / `validar`); la página solo orquesta esa llamada y
        el presenter se limita a conservar el resultado para el render."""
        self.estado["prep_reporte"] = reporte
        self.estado["prep_error"] = error
        self.estado["prep_config_id"] = config_id


__all__ = ["HorariosHubPresenter"]
