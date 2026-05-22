"""
tokens.py — Constantes Python del design system "Andes Minimal v2"
===================================================================
Uso: cuando no es posible usar CSS puro (ag-grid column defs,
color calculado en Python, estilos inline condicionales, etc.).

Regla: los valores deben coincidir EXACTAMENTE con las variables
CSS definidas en styles.css. Si cambias un color aquí, cámbialo
también en :root { ... } de styles.css.

FUENTE CANÓNICA: styles.css — este archivo es derivado de ella.
"""
from __future__ import annotations


class Colors:
    """Paleta base del design system. Valores importados de styles.css :root."""

    # Primario — Escala Borgoña/Carmesí
    PRIMARY          = "#B3325D"
    PRIMARY_DARK     = "#8A2748"
    PRIMARY_DARKER   = "#611B32"
    PRIMARY_LIGHT    = "#DB3D72"
    PRIMARY_LIGHTER  = "#FCE8ED"
    PRIMARY_HOVER    = "#8A2748"
    PRIMARY_DISABLED = "#DDA8B8"
    PRIMARY_CONTRAST = "#FFFFFF"

    # Secundario — Neutro puro (Escala Zinc)
    SECONDARY        = "#71717A"
    SECONDARY_DARK   = "#52525B"
    SECONDARY_LIGHT  = "#F4F4F5"

    # Semánticos
    ERROR            = "#DC2626"
    ERROR_LIGHT      = "#FEF2F2"
    ERROR_DARK       = "#B91C1C"
    WARNING          = "#FFCB47"
    WARNING_LIGHT    = "#FFFBEB"
    SUCCESS          = "#47FF97"
    SUCCESS_LIGHT    = "#ECFDF5"
    INFO             = "#4778FF"
    INFO_LIGHT       = "#F0F9FF"

    # Neutros
    BG               = "#FAFAFA"
    SURFACE          = "#FFFFFF"
    SURFACE_ALT      = "#FDF8F9"
    DIVIDER          = "rgba(0, 0, 0, 0.12)"
    BORDER           = "#E4E4E7"
    TEXT_PRIMARY     = "#18181B"
    TEXT_SECONDARY   = "#52525B"
    TEXT_DISABLED    = "#A1A1AA"
    TEXT_INVERSE     = "#FFFFFF"
    DISABLED_BG      = "#E4E4E7"
    DISABLED_TEXT    = "#71717A"

    # Navegación
    SIDEBAR_BG        = "#18181B"   # base del gradient linear-gradient(180deg, #18181B 0%, #09090B 100%)
    SIDEBAR_TEXT      = "#A1A1AA"
    SIDEBAR_HOVER     = "#27272A"
    SIDEBAR_ACTIVE    = "#B3325D"
    SIDEBAR_ACTIVE_BG = "#B3325D"
    TOPBAR_BG         = "rgba(255, 255, 255, 0.82)"
    TOPBAR_BORDER     = "#E4E4E7"


class AsistenciaColors:
    """Colores para los estados de asistencia."""

    PRESENTE     = "#47FF59"
    PRESENTE_BG  = "#ECFDF5"
    FJ           = "#FFCB47"
    FJ_BG        = "#FFFBEB"
    FI           = "#DC2626"
    FI_BG        = "#FEF2F2"
    RETRASO      = "#7C3AED"
    RETRASO_BG   = "#F5F3FF"
    EXCUSA       = "#4778FF"
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
    BASICO       = "#FFCB47"
    BASICO_BG    = "#FFFBEB"
    ALTO         = "#0284C7"
    ALTO_BG      = "#F0F9FF"
    SUPERIOR     = "#47FF59"
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
    """Valores de espaciado — deben coincidir con --space-* en styles.css."""
    XS  = "4px"
    SM  = "8px"
    MD  = "16px"
    LG  = "28px"
    XL  = "40px"
    XXL = "56px"


class Layout:
    """Dimensiones de layout — deben coincidir con las variables CSS de layout."""
    SIDEBAR_WIDTH     = 180   # px  (--sidebar-width)
    SIDEBAR_COLLAPSED = 58    # px  (--sidebar-collapsed)
    TOPBAR_HEIGHT     = 60    # px  (--topbar-height)
    CONTENT_PADDING   = 24    # px  (--content-padding)


__all__ = [
    "Colors",
    "AsistenciaColors",
    "DesempenoColors",
    "Icons",
    "Spacing",
    "Layout",
]
