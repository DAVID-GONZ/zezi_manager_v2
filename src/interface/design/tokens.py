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
    PRIMARY          = "#2563EB"
    PRIMARY_DARK     = "#1D4ED8"
    PRIMARY_DARKER   = "#1E3A8A"
    PRIMARY_LIGHT    = "#60A5FA"
    PRIMARY_LIGHTER  = "#EFF6FF"
    PRIMARY_HOVER    = "#1D4ED8"
    PRIMARY_DISABLED = "#93C5FD"
    PRIMARY_CONTRAST = "#FFFFFF"

    # Secundarios
    SECONDARY        = "#F59E0B"
    SECONDARY_DARK   = "#D97706"
    SECONDARY_LIGHT  = "#FEF3C7"

    # Semánticos
    ERROR            = "#DC2626"
    ERROR_LIGHT      = "#FEF2F2"
    WARNING          = "#D97706"
    WARNING_LIGHT    = "#FFFBEB"
    SUCCESS          = "#059669"
    SUCCESS_LIGHT    = "#ECFDF5"
    INFO             = "#0284C7"
    INFO_LIGHT       = "#F0F9FF"

    # Neutros
    BG               = "#F8FAFC"
    SURFACE          = "#FFFFFF"
    SURFACE_ALT      = "#F1F5F9"
    DIVIDER          = "#E2E8F0"
    BORDER           = "#CBD5E1"
    TEXT_PRIMARY     = "#0F172A"
    TEXT_SECONDARY   = "#475569"
    TEXT_DISABLED    = "#94A3B8"

    # Navegación
    SIDEBAR_BG        = "#0F172A"
    SIDEBAR_TEXT      = "#94A3B8"
    SIDEBAR_HOVER     = "#1E293B"
    SIDEBAR_ACTIVE    = "#2563EB"
    SIDEBAR_ACTIVE_BG = "#2563EB"
    TOPBAR_BG         = "#FFFFFF"
    TOPBAR_BORDER     = "#E2E8F0"


class AsistenciaColors:
    """Colores para los estados de asistencia."""

    PRESENTE     = "#059669"
    PRESENTE_BG  = "#ECFDF5"
    FJ           = "#D97706"
    FJ_BG        = "#FFFBEB"
    FI           = "#DC2626"
    FI_BG        = "#FEF2F2"
    RETRASO      = "#7C3AED"
    RETRASO_BG   = "#F5F3FF"
    EXCUSA       = "#0284C7"
    EXCUSA_BG    = "#F0F9FF"

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

    BAJO         = "#DC2626"
    BAJO_BG      = "#FEF2F2"
    BASICO       = "#D97706"
    BASICO_BG    = "#FFFBEB"
    ALTO         = "#0284C7"
    ALTO_BG      = "#F0F9FF"
    SUPERIOR     = "#059669"
    SUPERIOR_BG  = "#ECFDF5"

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

        Delega la clasificación a ``nivel_desempeno()`` del dominio,
        donde viven los umbrales reales del sistema colombiano (1.0–5.0).
        Así tokens.py solo gestiona la presentación visual, no las
        reglas de negocio educativas.
        """
        from src.domain.models.evaluacion import nivel_desempeno
        nivel = nivel_desempeno(nota)
        return cls.para_nivel(nivel)

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
