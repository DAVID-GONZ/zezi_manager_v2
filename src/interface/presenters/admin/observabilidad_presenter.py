"""
src/interface/presenters/admin/observabilidad_presenter.py
============================================================
Presenter puro de la página de observabilidad (obs_13 — T12).

Sin import de NiceGUI (subcapa pura, portable al fork Vue).
Concentra el view-state por bloque y sus transiciones.

El presenter NO calcula nada: recibe DTOs ya compuestos del servicio (R14).
Los cálculos de uptime, tamaño de BD, parseo de log y agregación de KPIs
viven en ObservabilidadService / dominio.

Regla de capas:
  - NO importa nicegui, sqlite3, ni src.infrastructure.
  - Puede importar src.domain y src.services (solo tipos, no instancias).
"""
from __future__ import annotations


class ObservabilidadPresenter:
    """
    View-model de la página de observabilidad.

    Estado por bloque — cada bloque tiene sus datos y su propio error (R13):
      salud      — estado de salud del sistema.
      eventos    — entradas del log de seguridad.
      alertas    — alertas de IP activas.
      uso        — serie diaria de uso.

    Un bloque que falla deja error_<bloque> con el mensaje y los demás
    mantienen sus datos (fail-open por bloque).
    """

    def __init__(self) -> None:
        self.estado: dict = {
            # Bloque 1: salud
            "salud": None,
            "error_salud": None,
            # Bloque 2: eventos de seguridad
            "eventos": [],
            "error_eventos": None,
            # Bloque 3: alertas de IP
            "alertas": [],
            "error_alertas": None,
            # Bloque 4: uso diario
            "uso": [],
            "error_uso": None,
            # Filtros del log
            "filtro_nivel": None,
            "filtro_tipo": None,
            # Indica si el archivo de log está disponible (para distinguir
            # «vacío» de «inaccesible» — R7)
            "log_disponible": True,
        }

    # ── Transiciones de view-state ─────────────────────────────────────────────

    def set_filtro_tipo(self, tipo: str | None) -> None:
        """Actualiza el filtro de tipo de evento del log."""
        self.estado["filtro_tipo"] = tipo or None

    def set_filtro_nivel(self, nivel: str | None) -> None:
        """Actualiza el filtro de nivel del log."""
        self.estado["filtro_nivel"] = nivel or None

    def cargar_salud(self, salud_dto) -> None:
        """Almacena el resultado del bloque de salud."""
        self.estado["salud"] = salud_dto
        self.estado["error_salud"] = None

    def error_salud(self, msg: str) -> None:
        """Marca el bloque de salud con error sin borrar otros bloques."""
        self.estado["error_salud"] = str(msg)
        self.estado["salud"] = None

    def cargar_eventos(self, eventos: list, disponible: bool) -> None:
        """Almacena los eventos de log y la marca de disponibilidad."""
        self.estado["eventos"] = eventos
        self.estado["log_disponible"] = disponible
        self.estado["error_eventos"] = None

    def error_eventos(self, msg: str) -> None:
        """Marca el bloque de eventos con error sin borrar otros bloques."""
        self.estado["error_eventos"] = str(msg)
        self.estado["eventos"] = []

    def cargar_alertas(self, alertas: list) -> None:
        """Almacena las alertas de IP activas."""
        self.estado["alertas"] = alertas
        self.estado["error_alertas"] = None

    def error_alertas(self, msg: str) -> None:
        """Marca el bloque de alertas con error sin borrar otros bloques."""
        self.estado["error_alertas"] = str(msg)
        self.estado["alertas"] = []

    def cargar_uso(self, uso: list) -> None:
        """Almacena la serie diaria de uso."""
        self.estado["uso"] = uso
        self.estado["error_uso"] = None

    def error_uso(self, msg: str) -> None:
        """Marca el bloque de uso con error sin borrar otros bloques."""
        self.estado["error_uso"] = str(msg)
        self.estado["uso"] = []

    # ── Consultas de vista ─────────────────────────────────────────────────────

    def filtros_activos(self) -> bool:
        """True si hay algún filtro activo en el log."""
        return (
            self.estado["filtro_tipo"] is not None
            or self.estado["filtro_nivel"] is not None
        )

    def bloques_con_error(self) -> list[str]:
        """Nombres de los bloques que tienen error actualmente."""
        errores = []
        for nombre in ("salud", "eventos", "alertas", "uso"):
            if self.estado.get(f"error_{nombre}"):
                errores.append(nombre)
        return errores


__all__ = ["ObservabilidadPresenter"]
