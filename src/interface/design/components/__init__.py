from .base_form import base_form
from .inline_selectors import inline_periodo_grupo, inline_periodo_grupo_asignatura
from .buttons import btn_danger, btn_ghost, btn_icon, btn_primary, btn_secondary
from .confirm_dialog import confirm_dialog
from .confirmation_card import confirmation_card
from .counter_card import counter_card
from .custom_dialog import custom_dialog
from .data_table import data_table
from .date_input import date_input, date_range_input
from .empty_state import empty_state
from .form_dialog import form_dialog
from .mini_chart import mini_chart
from .page_header import page_header
from .performance_indicator import performance_indicator
from .pipeline import pipeline_nav
from .skeleton_loader import skeleton_cards, skeleton_form, skeleton_table
from .stat_card import stat_card
from .status_badge import (
    badge_asistencia,
    badge_desempeno,
    badge_estado_general,
    status_badge,
)
from .toast import toast, toast_error, toast_info, toast_success, toast_warning

__all__ = [
    # Badges de estado
    "status_badge",
    "badge_asistencia",
    "badge_desempeno",
    "badge_estado_general",
    # Diálogos y confirmaciones
    "confirm_dialog",
    "confirmation_card",
    "custom_dialog",
    # Cabecera de página
    "page_header",
    # Tarjeta de estadística / KPI
    "stat_card",
    # Tile contador + mini gráfica (convivencia_22)
    "counter_card",
    "mini_chart",
    # Tabla de datos con búsqueda y paginación
    "data_table",
    # Indicador de desempeño
    "performance_indicator",
    # Formulario base reutilizable
    "base_form",
    # Modal de formulario CRUD
    "form_dialog",
    # Botones del design system
    "btn_primary",
    "btn_secondary",
    "btn_danger",
    "btn_ghost",
    "btn_icon",
    # Estado vacío (paso_12b)
    "empty_state",
    # Skeleton loaders (paso_12b)
    "skeleton_table",
    "skeleton_cards",
    "skeleton_form",
    # Toasts / notificaciones (paso_12b)
    "toast",
    "toast_info",
    "toast_success",
    "toast_warning",
    "toast_error",
    "pipeline_nav",
    # Componentes de fecha (paso_21 T7)
    "date_input",
    "date_range_input",
    # Selectores inline en cascada (chip_01)
    "inline_periodo_grupo_asignatura",
    "inline_periodo_grupo",
]
