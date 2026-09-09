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

    Prioridad:
      Nivel 1: ReportLabExporter — PDF + Excel + CSV (requiere reportlab + openpyxl)
      Nivel 2: OpenpyxlExporter  — Excel + CSV       (requiere openpyxl)
      Nivel 3: NullExporter      — solo CSV          (sin dependencias)
    """
    # Nivel 1: PDF via reportlab + Excel + CSV (completo)
    try:
        import openpyxl
        import reportlab  # noqa: F401

        from .pdf_exporter import ReportLabExporter

        _log.info("Exportador activo: ReportLabExporter (PDF + Excel + CSV)")
        return ReportLabExporter()
    except ImportError:
        pass

    # Nivel 2: Excel + CSV (sin PDF)
    try:
        import openpyxl  # noqa: F401

        from .openpyxl_exporter import OpenpyxlExporter

        _log.warning("reportlab no disponible. PDF no funcionará. Instala: pip install reportlab")
        return OpenpyxlExporter()
    except ImportError:
        pass

    # Nivel 3: Solo CSV
    _log.warning(
        "openpyxl y reportlab no disponibles. "
        "Solo CSV funcionará. Instala: pip install openpyxl reportlab"
    )
    from .null_exporter import NullExporter

    return NullExporter()


__all__ = ["crear_exporter"]
