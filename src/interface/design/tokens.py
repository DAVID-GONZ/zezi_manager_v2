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
    """Paleta base del design system. Valores importados de tokens.css :root.
    Paleta Aula Serena: tinta académica + ocre + neutros cálidos."""

    # Primario — Índigo académico (ink-700)
    PRIMARY          = "#2E3192"
    PRIMARY_DARK     = "#1A1B6E"
    PRIMARY_DARKER   = "#1A1B6E"
    PRIMARY_LIGHT    = "#4B50C0"
    PRIMARY_LIGHTER  = "#E8E9F8"
    PRIMARY_HOVER    = "#1A1B6E"
    PRIMARY_DISABLED = "#9297D9"
    PRIMARY_CONTRAST = "#FFFFFF"

    # Secundario — Grafito neutro
    SECONDARY        = "#6B6B6B"
    SECONDARY_DARK   = "#3D3D3D"
    SECONDARY_LIGHT  = "#F2F2EC"

    # Semánticos desaturados
    ERROR            = "#C13030"
    ERROR_LIGHT      = "#FBEAEA"
    ERROR_DARK       = "#9D2525"
    WARNING          = "#C8841C"
    WARNING_LIGHT    = "#FBF3E2"
    SUCCESS          = "#2E7D5B"
    SUCCESS_LIGHT    = "#EAF4EE"
    INFO             = "#4B50C0"
    INFO_LIGHT       = "#E8E9F8"

    # Neutros cálidos (paper/graphite)
    BG               = "#FAFAF7"
    SURFACE          = "#FFFFFF"
    SURFACE_ALT      = "#F2F2EC"
    DIVIDER          = "rgba(0, 0, 0, 0.08)"
    BORDER           = "#E5E5DE"
    TEXT_PRIMARY     = "#1A1A1A"
    TEXT_SECONDARY   = "#6B6B6B"
    TEXT_DISABLED    = "#9D9D9D"
    TEXT_INVERSE     = "#FFFFFF"
    DISABLED_BG      = "#E5E5DE"
    DISABLED_TEXT    = "#6B6B6B"

    # Navegación — Sidebar claro, topbar índigo
    SIDEBAR_BG        = "#FAFAF7"   # paper-050
    SIDEBAR_TEXT      = "#3D3D3D"   # graphite-700
    SIDEBAR_HOVER     = "#E8E9F8"   # ink-100
    SIDEBAR_ACTIVE    = "#2E3192"   # ink-700
    SIDEBAR_ACTIVE_BG = "#2E3192"   # ink-700
    TOPBAR_BG         = "#2E3192"   # ink-700 sólido
    TOPBAR_BORDER     = "rgba(255, 255, 255, 0.10)"


class AsistenciaColors:
    """Colores para los estados de asistencia. Paleta Aula Serena."""

    PRESENTE     = "#2E7D5B"
    PRESENTE_BG  = "#EAF4EE"
    FJ           = "#C8841C"
    FJ_BG        = "#FBF3E2"
    FI           = "#C13030"
    FI_BG        = "#FBEAEA"
    RETRASO      = "#6D4E9C"
    RETRASO_BG   = "#F0EAFA"
    EXCUSA       = "#4B50C0"
    EXCUSA_BG    = "#E8E9F8"

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
    """Colores para los niveles de desempeño académico. Paleta Aula Serena."""

    BAJO         = "#B4322E"
    BAJO_BG      = "#FAE7E6"
    BASICO       = "#B8763A"
    BASICO_BG    = "#F7ECDD"
    ALTO         = "#4B50C0"
    ALTO_BG      = "#E8E9F8"
    SUPERIOR     = "#2E7D5B"
    SUPERIOR_BG  = "#EAF4EE"

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
    SIDEBAR_WIDTH     = 220   # px  (--sidebar-width)
    SIDEBAR_COLLAPSED = 58    # px  (--sidebar-collapsed)
    TOPBAR_HEIGHT     = 60    # px  (--topbar-height)
    CONTENT_PADDING   = 24    # px  (--content-padding)



# >>> AUTOGEN START
# Este bloque es generado automáticamente por scripts/sync_tokens.py
# NO editar manualmente — editar tokens.css y re-ejecutar el script

# Autogen — Colors
    PRIMARY              = "var(--ink-700)"
    PRIMARY_DARK         = "var(--ink-900)"
    PRIMARY_DARKER       = "var(--ink-900)"
    PRIMARY_LIGHT        = "var(--ink-500)"
    PRIMARY_LIGHTER      = "var(--ink-100)"
    PRIMARY_HOVER        = "var(--ink-900)"
    PRIMARY_DISABLED     = "var(--ink-300)"
    PRIMARY_CONTRAST     = "#FFFFFF"
    SECONDARY            = "var(--graphite-500)"
    SECONDARY_DARK       = "var(--graphite-700)"
    SECONDARY_LIGHT      = "var(--paper-100)"
    ERROR                = "#C13030"
    ERROR_LIGHT          = "#FBEAEA"
    ERROR_DARK           = "#9D2525"
    WARNING              = "#C8841C"
    WARNING_LIGHT        = "#FBF3E2"
    SUCCESS              = "#2E7D5B"
    SUCCESS_LIGHT        = "#EAF4EE"
    INFO                 = "var(--ink-500)"
    INFO_LIGHT           = "var(--ink-100)"
    BG                   = "var(--paper-050)"
    SURFACE              = "var(--paper-000)"
    SURFACE_ALT          = "var(--paper-100)"
    BORDER               = "var(--paper-200)"
    TEXT_PRIMARY         = "var(--graphite-900)"
    TEXT_SECONDARY       = "var(--graphite-500)"
    TEXT_DISABLED        = "var(--graphite-300)"
    TEXT_INVERSE         = "#FFFFFF"
    DISABLED_BG          = "var(--paper-200)"
    DISABLED_TEXT        = "var(--graphite-500)"
    SIDEBAR_TEXT         = "var(--graphite-700)"
    SIDEBAR_HOVER        = "var(--ink-100)"
    SIDEBAR_ACTIVE_BG    = "var(--ink-700)"

# Autogen — AsistenciaColors
    PRESENTE             = "#2E7D5B"
    PRESENTE_BG          = "#EAF4EE"
    FJ                   = "#C8841C"
    FJ_BG                = "#FBF3E2"
    FI                   = "#C13030"
    FI_BG                = "#FBEAEA"
    RETRASO              = "#6D4E9C"
    RETRASO_BG           = "#F0EAFA"
    EXCUSA               = "#4B50C0"
    EXCUSA_BG            = "#E8E9F8"

# Autogen — DesempenoColors
    BAJO                 = "#B4322E"
    BAJO_BG              = "#FAE7E6"
    BASICO               = "#B8763A"
    BASICO_BG            = "#F7ECDD"
    ALTO                 = "#4B50C0"
    ALTO_BG              = "#E8E9F8"
    SUPERIOR             = "#2E7D5B"
    SUPERIOR_BG          = "#EAF4EE"

# Autogen — Spacing
    XS                   = "4px"
    SM                   = "8px"
    MD                   = "16px"
    LG                   = "28px"
    XL                   = "40px"
    XXL                  = "56px"

# Autogen — Layout
    SIDEBAR_WIDTH        = 220
    SIDEBAR_COLLAPSED    = 58
    TOPBAR_HEIGHT        = 60
    CONTENT_PADDING      = 24

# <<< AUTOGEN END

__all__ = [
    "Colors",
    "AsistenciaColors",
    "DesempenoColors",
    "Icons",
    "Spacing",
    "Layout",
]
