from .status_badge import status_badge, badge_asistencia, badge_desempeno, badge_estado_general
from .confirm_dialog import confirm_dialog
from .confirmation_card import confirmation_card
from .page_header import page_header
from .stat_card import stat_card
from .data_table import data_table
from .context_selector import context_chip, abrir_selector
from .performance_indicator import performance_indicator
from .base_form import base_form

__all__ = [
    # Badges de estado
    "status_badge",
    "badge_asistencia",
    "badge_desempeno",
    "badge_estado_general",
    # Diálogos y confirmaciones
    "confirm_dialog",
    "confirmation_card",
    # Cabecera de página
    "page_header",
    # Tarjeta de estadística / KPI
    "stat_card",
    # Tabla de datos con búsqueda y paginación
    "data_table",
    # Selector de contexto académico (chip en topbar + dialog)
    "context_chip",
    "abrir_selector",
    # Indicador de desempeño
    "performance_indicator",
    # Formulario base reutilizable
    "base_form",
]
