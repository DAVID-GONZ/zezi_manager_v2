from .activity_feed import ActivityItem, activity_feed
from .alerts_panel import AlertItem, alerts_panel
from .base_form import base_form
from .buttons import btn_danger, btn_ghost, btn_icon, btn_primary, btn_secondary
from .confirm_dialog import confirm_dialog
from .confirmation_card import confirmation_card
from .counter_card import counter_card
from .custom_dialog import custom_dialog
from .data_table import data_table
from .date_input import date_input, date_range_input
from .empty_state import empty_state
from .followup_panel import FollowupItem, followup_panel
from .form_dialog import form_dialog
from .greeting_hero import greeting_hero
from .groups_attention import GroupRisk, groups_attention_panel
from .inline_selectors import inline_periodo_grupo, inline_periodo_grupo_asignatura
from .milestones_panel import MilestoneItem, milestones_panel
from .mini_chart import mini_chart
from .page_header import page_header
from .pending_items import PendingItem, pending_list
from .performance_indicator import performance_indicator
from .period_status import PeriodData, period_status_card
from .pipeline import pipeline_nav

# Hub / dashboard components (inicio_34 fase 2)
from .section_panel import section_panel
from .skeleton_loader import skeleton_cards, skeleton_form, skeleton_table
from .stat_card import stat_card
from .stats_grid import StatItem, stats_grid
from .status_badge import (
    badge_asistencia,
    badge_desempeno,
    badge_estado_general,
    status_badge,
)
from .toast import toast, toast_error, toast_info, toast_success, toast_warning

__all__ = [
    "ActivityItem",
    "AlertItem",
    "FollowupItem",
    "GroupRisk",
    "MilestoneItem",
    "PendingItem",
    "PeriodData",
    "StatItem",
    "activity_feed",
    "alerts_panel",
    "badge_asistencia",
    "badge_desempeno",
    "badge_estado_general",
    # Formulario base reutilizable
    "base_form",
    "btn_danger",
    "btn_ghost",
    "btn_icon",
    # Botones del design system
    "btn_primary",
    "btn_secondary",
    # Diálogos y confirmaciones
    "confirm_dialog",
    "confirmation_card",
    # Tile contador + mini gráfica (convivencia_22)
    "counter_card",
    "custom_dialog",
    # Tabla de datos con búsqueda y paginación
    "data_table",
    # Componentes de fecha (paso_21 T7)
    "date_input",
    "date_range_input",
    # Estado vacío (paso_12b)
    "empty_state",
    "followup_panel",
    # Modal de formulario CRUD
    "form_dialog",
    "greeting_hero",
    "groups_attention_panel",
    "inline_periodo_grupo",
    # Selectores inline en cascada (chip_01)
    "inline_periodo_grupo_asignatura",
    "milestones_panel",
    "mini_chart",
    # Cabecera de página
    "page_header",
    "pending_list",
    # Indicador de desempeño
    "performance_indicator",
    "period_status_card",
    "pipeline_nav",
    # Hub / dashboard components (inicio_34 fase 2)
    "section_panel",
    "skeleton_cards",
    "skeleton_form",
    # Skeleton loaders (paso_12b)
    "skeleton_table",
    # Tarjeta de estadística / KPI
    "stat_card",
    "stats_grid",
    # Badges de estado
    "status_badge",
    # Toasts / notificaciones (paso_12b)
    "toast",
    "toast_error",
    "toast_info",
    "toast_success",
    "toast_warning",
]
