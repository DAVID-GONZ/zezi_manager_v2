"""
tokens.py — Constantes Python del design system "Andes Minimal v2"
===================================================================
Uso: cuando no es posible usar CSS puro (ag-grid column defs,
color calculado en Python, estilos inline condicionales, etc.).

Regla: los valores deben coincidir EXACTAMENTE con las variables
CSS definidas en styles.css. Si cambias un color aquí, cámbialo
también en :root { ... } de styles.css.
"""
from __future__ import annotations


class Colors:
    """Paleta base del design system."""

    # Primarios
    PRIMARY          = "#00509E"
    PRIMARY_DARK     = "#003B73"
    PRIMARY_DARKER   = "#002A54"
    PRIMARY_LIGHT    = "#4281C1"
    PRIMARY_LIGHTER  = "#D6E6F7"
    PRIMARY_HOVER    = "#004A93"
    PRIMARY_DISABLED = "#A0BCD8"
    PRIMARY_CONTRAST = "#FFFFFF"

    # Secundarios
    SECONDARY        = "#F5B041"
    SECONDARY_DARK   = "#D68910"
    SECONDARY_LIGHT  = "#FAD7A1"

    # Semánticos
    ERROR            = "#D32F2F"
    ERROR_LIGHT      = "#FFEBEE"
    WARNING          = "#F57C00"
    WARNING_LIGHT    = "#FFF3E0"
    SUCCESS          = "#2E7D32"
    SUCCESS_LIGHT    = "#E8F5E9"
    INFO             = "#0288D1"
    INFO_LIGHT       = "#E1F5FE"

    # Neutros
    BG               = "#F4F6F8"
    SURFACE          = "#FFFFFF"
    SURFACE_ALT      = "#F9FAFB"
    DIVIDER          = "#E0E0E0"
    BORDER           = "#D1D5DB"
    TEXT_PRIMARY     = "#1A2027"
    TEXT_SECONDARY   = "#5C6A79"
    TEXT_DISABLED    = "#9CA3AF"

    # Navegación
    SIDEBAR_BG       = "#0A2540"
    SIDEBAR_TEXT     = "#B8C8D8"
    SIDEBAR_HOVER    = "#1A3A5C"
    SIDEBAR_ACTIVE   = "#00509E"
    SIDEBAR_ACTIVE_BG = "#1E3F6E"
    TOPBAR_BG        = "#FFFFFF"
    TOPBAR_BORDER    = "#E0E0E0"


class AsistenciaColors:
    """Colores para los estados de asistencia."""

    PRESENTE     = "#2E7D32"
    PRESENTE_BG  = "#E8F5E9"
    FJ           = "#F57C00"
    FJ_BG        = "#FFF3E0"
    FI           = "#D32F2F"
    FI_BG        = "#FFEBEE"
    RETRASO      = "#7B1FA2"
    RETRASO_BG   = "#F3E5F5"
    EXCUSA       = "#0288D1"
    EXCUSA_BG    = "#E1F5FE"

    @classmethod
    def para_estado(cls, estado: str) -> tuple[str, str]:
        """
        Retorna (color_texto, color_fondo) para un estado de asistencia.

        Args:
            estado: Código de asistencia — "P", "FJ", "FI", "R" o "E".

        Returns:
            Tupla (color_texto, color_fondo) en formato hex.
            Fallback a (TEXT_SECONDARY, BG) si el estado no se reconoce.
        """
        mapa: dict[str, tuple[str, str]] = {
            "P":  (cls.PRESENTE, cls.PRESENTE_BG),
            "FJ": (cls.FJ,       cls.FJ_BG),
            "FI": (cls.FI,       cls.FI_BG),
            "R":  (cls.RETRASO,  cls.RETRASO_BG),
            "E":  (cls.EXCUSA,   cls.EXCUSA_BG),
        }
        return mapa.get(estado, (Colors.TEXT_SECONDARY, Colors.BG))

    @classmethod
    def css_badge(cls, estado: str) -> str:
        """
        Retorna el string de clase CSS del badge para un estado.
        Ej: "badge badge-P", "badge badge-FJ"
        """
        codigos_validos = {"P", "FJ", "FI", "R", "E"}
        if estado in codigos_validos:
            return f"badge badge-{estado}"
        return "badge badge-neutral"


class DesempenoColors:
    """Colores para los niveles de desempeño académico."""

    BAJO         = "#D32F2F"
    BAJO_BG      = "#FFEBEE"
    BASICO       = "#F57C00"
    BASICO_BG    = "#FFF3E0"
    ALTO         = "#0288D1"
    ALTO_BG      = "#E1F5FE"
    SUPERIOR     = "#2E7D32"
    SUPERIOR_BG  = "#E8F5E9"

    @classmethod
    def para_nivel(cls, nivel: str) -> tuple[str, str]:
        """
        Retorna (color_texto, color_fondo) para un nivel de desempeño.

        Args:
            nivel: "Bajo", "Básico", "Alto" o "Superior".

        Returns:
            Tupla (color_texto, color_fondo) en formato hex.
        """
        mapa: dict[str, tuple[str, str]] = {
            "Bajo":     (cls.BAJO,     cls.BAJO_BG),
            "Básico":   (cls.BASICO,   cls.BASICO_BG),
            "Alto":     (cls.ALTO,     cls.ALTO_BG),
            "Superior": (cls.SUPERIOR, cls.SUPERIOR_BG),
        }
        return mapa.get(nivel, (Colors.TEXT_SECONDARY, Colors.BG))

    @classmethod
    def para_nota(cls, nota: float) -> tuple[str, str]:
        """
        Retorna (color_texto, color_fondo) según la nota numérica.
        Umbrales según el sistema colombiano de desempeño (1.0–5.0).
        """
        if nota < 3.0:
            return cls.BAJO,     cls.BAJO_BG
        if nota < 3.8:
            return cls.BASICO,   cls.BASICO_BG
        if nota < 4.6:
            return cls.ALTO,     cls.ALTO_BG
        return cls.SUPERIOR, cls.SUPERIOR_BG

    @classmethod
    def css_badge(cls, nivel: str) -> str:
        """
        Retorna el string de clase CSS del badge para un nivel.
        Ej: "badge badge-bajo", "badge badge-superior"
        """
        mapa = {
            "Bajo":     "badge badge-bajo",
            "Básico":   "badge badge-basico",
            "Alto":     "badge badge-alto",
            "Superior": "badge badge-superior",
        }
        return mapa.get(nivel, "badge badge-neutral")


class Icons:
    """
    Nombres de Material Symbols Rounded usados en la aplicación.
    Pasar a ThemeManager.icono(Icons.DASHBOARD) para renderizar.
    """

    # Navegación principal
    DASHBOARD    = "space_dashboard"
    GRADES       = "bar_chart"
    ATTENDANCE   = "fact_check"
    STUDENTS     = "school"
    TEACHERS     = "badge"
    SCHEDULE     = "calendar_today"
    REPORTS      = "summarize"
    SETTINGS     = "settings"
    CONFIG       = "tune"
    ALERTS       = "notifications"
    GROUPS       = "group"
    SUBJECTS     = "book"
    PERIODS      = "date_range"
    BEHAVIOR     = "psychology"
    PIAR         = "accessible"
    GUARDIAN     = "family_restroom"

    # Acciones CRUD
    EXPORT       = "download"
    ADD          = "add"
    EDIT         = "edit"
    DELETE       = "delete"
    SEARCH       = "search"
    FILTER       = "filter_list"
    SAVE         = "save"
    CANCEL       = "close"

    # Estado / feedback
    CHECK        = "check_circle"
    WARNING      = "warning"
    ERROR        = "error"
    INFO         = "info"

    # Navegación UI
    BACK         = "arrow_back"
    MENU         = "menu"
    LOGOUT       = "logout"
    PROFILE      = "account_circle"
    CLOSE_PERIOD = "lock"
    REFRESH      = "refresh"
    EXPAND       = "expand_more"
    COLLAPSE     = "expand_less"


class Spacing:
    """Valores de espaciado en px (como strings CSS)."""
    XS  = "4px"
    SM  = "8px"
    MD  = "16px"
    LG  = "24px"
    XL  = "32px"
    XXL = "48px"


class Layout:
    """Dimensiones de layout (valores numéricos, sin unidad)."""
    SIDEBAR_WIDTH    = 240   # px
    SIDEBAR_COLLAPSED = 64   # px
    TOPBAR_HEIGHT    = 56    # px
    CONTENT_PADDING  = 24    # px


__all__ = [
    "Colors",
    "AsistenciaColors",
    "DesempenoColors",
    "Icons",
    "Spacing",
    "Layout",
]
