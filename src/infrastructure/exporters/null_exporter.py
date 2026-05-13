"""
NullExporter — fallback cuando las dependencias de exportación no están instaladas.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from src.domain.ports.service_ports import IExporterService


def _csv_bytes(datos: list[dict], encoding: str) -> bytes:
    """Genera CSV en memoria sin dependencias externas."""
    if not datos:
        return b""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(datos[0].keys()))
    writer.writeheader()
    writer.writerows(datos)
    return buffer.getvalue().encode(encoding)


class NullExporter(IExporterService):
    """
    Exportador fallback registrado en el container cuando openpyxl o
    reportlab no están disponibles. Excel y PDF lanzan RuntimeError;
    CSV siempre funciona porque no necesita dependencias externas.
    """

    def exportar_excel(
        self,
        datos: list[dict],
        nombre_hoja: str = "Datos",
        ruta_destino: Path | None = None,
    ) -> bytes:
        raise RuntimeError(
            "El exportador Excel no está disponible. "
            "Instala openpyxl: pip install openpyxl"
        )

    def exportar_pdf(
        self,
        html_content: str,
        ruta_destino: Path | None = None,
    ) -> bytes:
        raise RuntimeError(
            "El exportador PDF no está disponible. "
            "Instala weasyprint o reportlab: pip install weasyprint"
        )

    def exportar_csv(
        self,
        datos: list[dict],
        ruta_destino: Path | None = None,
        encoding: str = "utf-8-sig",
    ) -> bytes:
        contenido = _csv_bytes(datos, encoding)
        if ruta_destino is not None:
            Path(ruta_destino).write_bytes(contenido)
            return b""
        return contenido


__all__ = ["NullExporter"]
