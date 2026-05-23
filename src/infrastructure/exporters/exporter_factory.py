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
      Nivel 1:  WeasyPrintExporter — PDF via weasyprint + Excel + CSV (requiere weasyprint + openpyxl)
      Nivel 1b: WeasyPrintExporter — PDF via reportlab  + Excel + CSV (requiere reportlab  + openpyxl)
      Nivel 2:  OpenpyxlExporter   — Excel + CSV        (requiere openpyxl)
      Nivel 3:  NullExporter       — solo CSV           (sin dependencias)
    """
    # Nivel 1: PDF via weasyprint + Excel + CSV (completo)
    # Catch Exception (no solo ImportError) porque weasyprint puede fallar con OSError
    # al intentar cargar libgobject/libpango en Windows sin las libs nativas instaladas.
    try:
        import weasyprint  # noqa: F401
        import openpyxl    # noqa: F401
        from .pdf_exporter import WeasyPrintExporter
        _log.info("Exportador activo: WeasyPrintExporter (PDF via weasyprint + Excel + CSV)")
        return WeasyPrintExporter()
    except Exception:
        pass

    # Nivel 1b: PDF via reportlab + Excel + CSV
    # Fallback cuando weasyprint no puede cargar sus librerías nativas.
    try:
        import reportlab  # noqa: F401
        import openpyxl   # noqa: F401
        from .pdf_exporter import WeasyPrintExporter
        _log.info("Exportador activo: WeasyPrintExporter (PDF via reportlab + Excel + CSV)")
        return WeasyPrintExporter()
    except ImportError:
        pass

    # Nivel 2: Excel + CSV (sin PDF)
    try:
        import openpyxl  # noqa: F401
        from .openpyxl_exporter import OpenpyxlExporter
        _log.warning(
            "weasyprint no disponible. PDF no funcionará. "
            "Instala: pip install weasyprint"
        )
        return OpenpyxlExporter()
    except ImportError:
        pass

    # Nivel 3: Solo CSV
    _log.warning(
        "openpyxl y weasyprint no disponibles. "
        "Solo CSV funcionará. Instala: pip install openpyxl weasyprint"
    )
    from .null_exporter import NullExporter
    return NullExporter()


__all__ = ["crear_exporter"]
