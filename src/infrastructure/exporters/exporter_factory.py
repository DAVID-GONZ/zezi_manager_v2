"""
exporter_factory — selecciona el mejor exportador disponible en tiempo de arranque.
"""
from __future__ import annotations

import logging

from src.domain.ports.service_ports import IExporterService

_log = logging.getLogger("EXPORTER")


def crear_exporter() -> IExporterService:
    """
    Retorna el mejor exportador disponible según las dependencias instaladas.
    El container llama a esta función una vez al arrancar.
    """
    try:
        import openpyxl  # noqa: F401
        from .openpyxl_exporter import OpenpyxlExporter
        return OpenpyxlExporter()
    except ImportError:
        _log.warning(
            "openpyxl no instalado. Excel no disponible. "
            "Solo CSV funcionará. Instala: pip install openpyxl"
        )
        from .null_exporter import NullExporter
        return NullExporter()


__all__ = ["crear_exporter"]
