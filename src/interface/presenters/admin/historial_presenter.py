"""Presenter puro del diálogo de historial de cambios (obs_10).

Sin import de NiceGUI. Sin reglas de negocio (R12): el diff, la etiqueta de
tabla y la resolución de actores vienen del servicio.

El presenter concentra el view-state del diálogo:
  - abierto / cargando
  - qué tabla y registro_id se están consultando
  - items cargados (list[DetalleCambioDTO])
  - error si la consulta falló

La carga es perezosa (R11): ``abrir()`` marca ``cargando=True`` y la página
invoca al servicio y luego ``set_items`` o ``set_error``. Abrir la ficha sin
pulsar el botón no toca ``audit_log``.
"""
from __future__ import annotations


class HistorialPresenter:
    """View-state del diálogo de historial. Sin NiceGUI, sin reglas de negocio."""

    def __init__(self) -> None:
        self.estado: dict = {
            "abierto": False,
            "cargando": False,
            "tabla": None,           # str | None
            "registro_id": None,     # int | None
            "items": [],             # list[DetalleCambioDTO]
            "error": None,           # str | None
        }

    # ── Transiciones ────────────────────────────────────────────────────────

    def abrir(self, tabla: str, registro_id: int) -> None:
        """Abre el diálogo para el registro indicado y marca como cargando.

        La página debe invocar al servicio después de llamar a este método y
        luego llamar a ``set_items`` o ``set_error``.
        """
        self.estado["abierto"] = True
        self.estado["cargando"] = True
        self.estado["tabla"] = tabla
        self.estado["registro_id"] = registro_id
        self.estado["items"] = []
        self.estado["error"] = None

    def cerrar(self) -> None:
        """Cierra el diálogo y limpia todo el estado."""
        self.estado["abierto"] = False
        self.estado["cargando"] = False
        self.estado["tabla"] = None
        self.estado["registro_id"] = None
        self.estado["items"] = []
        self.estado["error"] = None

    def set_items(self, items: list) -> None:
        """Almacena los items cargados y apaga el indicador de carga."""
        self.estado["items"] = list(items)
        self.estado["cargando"] = False

    def set_error(self, mensaje: str | None) -> None:
        """Almacena el mensaje de error y apaga el indicador de carga."""
        self.estado["error"] = mensaje
        self.estado["cargando"] = False


__all__ = ["HistorialPresenter"]
