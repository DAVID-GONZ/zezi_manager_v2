from .status_badge import status_badge, badge_asistencia, badge_desempeno, badge_estado_general
from .confirm_dialog import confirm_dialog
from .page_header import page_header
from .stat_card import stat_card
from .data_table import data_table

__all__ = [
    # Badges de estado
    "status_badge",
    "badge_asistencia",
    "badge_desempeno",
    "badge_estado_general",
    # Diálogo de confirmación
    "confirm_dialog",
    # Cabecera de página
    "page_header",
    # Tarjeta de estadística / KPI
    "stat_card",
    # Tabla de datos con búsqueda y paginación
    "data_table",
]
