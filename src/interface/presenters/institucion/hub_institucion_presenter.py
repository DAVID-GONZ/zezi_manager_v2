"""Presenter puro del hub de institución (`/institucion/configuracion`).

Sin import de NiceGUI. Página de settings: el view-state es el modelo del
formulario (identidad, preferencias, módulos, apariencia, convivencia). El
presenter lo construye y lo mantiene; los campos se enlazan por `bind_value` a los
sub-dicts. La carga y el guardado viven en los servicios.
"""
from __future__ import annotations

from src.domain.modulos import modulos_desactivables


class HubInstitucionPresenter:
    """View-model del hub de institución: modelo del formulario de settings."""

    def __init__(self) -> None:
        self.estado: dict = {
            "identidad": {
                "nombre": "",
                "nombre_oficial": "",
                "rector": "",
                "municipio": "",
                "codigo_dane": "",
                "nit": "",
                "direccion": "",
                "telefono": "",
                "email_institucional": "",
                "resolucion_aprobacion": "",
                "lema": "",
                "jornada_principal": None,
                "tipo_institucion": None,
                "calendario": None,
            },
            "preferencias": {
                "nota_minima_aprobacion_default": 60.0,
                "nota_minima_escala_default": 0.0,
                "nota_maxima_escala_default": 100.0,
                "numero_periodos_default": 4,
            },
            "modulos": {d.clave_preferencia: True for d in modulos_desactivables()},
            "apariencia": {
                "color_primario": None,
                "color_secundario": None,
            },
            # Política de registros de convivencia en el boletín (convivencia_29).
            "convivencia": {
                "registros_boletin_tipos": ["fortaleza", "compromiso", "citacion_acudiente"],
                "registros_boletin_dificultad_requiere_notificacion": True,
                "registros_boletin_incluye_descargo": False,
                "registros_boletin_dedup_observaciones": True,
            },
        }


__all__ = ["HubInstitucionPresenter"]
