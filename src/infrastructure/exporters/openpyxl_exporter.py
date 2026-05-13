"""
OpenpyxlExporter — implementación de IExporterService usando openpyxl.
"""
from __future__ import annotations

import io
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.domain.ports.service_ports import IExporterService
from .null_exporter import _csv_bytes

_HEADER_FILL = PatternFill(fill_type="solid", fgColor="2B6CB0")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_ALIGN = Alignment(horizontal="center")
_RIGHT_ALIGN = Alignment(horizontal="right")
_FLOAT_FORMAT = "0.00"
_MAX_COL_WIDTH = 50


class OpenpyxlExporter(IExporterService):
    """
    Genera archivos Excel (.xlsx) con formato institucional.
    PDF no está implementado — usar un exportador especializado en HTML→PDF.
    CSV se sirve directamente sin openpyxl.
    """

    def exportar_excel(
        self,
        datos: list[dict],
        nombre_hoja: str = "Datos",
        ruta_destino: Path | None = None,
    ) -> bytes:
        """
        Crea un workbook Excel con:
          - Fila de headers en azul institucional (negrita, texto blanco)
          - Filas de datos con números alineados a la derecha
          - Ancho de columna auto-ajustado (máximo 50 chars)
        Retorna bytes si ruta_destino es None; escribe el archivo si se provee.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = nombre_hoja[:31]  # Excel limita el nombre de hoja a 31 chars

        if not datos:
            ws.cell(1, 1, "Sin datos")
        else:
            headers = list(datos[0].keys())

            # Fila de encabezados
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(1, col_idx, header)
                cell.fill = _HEADER_FILL
                cell.font = _HEADER_FONT
                cell.alignment = _HEADER_ALIGN

            # Filas de datos
            for row_idx, fila in enumerate(datos, 2):
                for col_idx, key in enumerate(headers, 1):
                    valor = fila.get(key, "")
                    cell = ws.cell(row_idx, col_idx, valor)
                    if isinstance(valor, float):
                        cell.alignment = _RIGHT_ALIGN
                        cell.number_format = _FLOAT_FORMAT
                    elif isinstance(valor, int):
                        cell.alignment = _RIGHT_ALIGN

            # Auto-ancho de columnas
            for col_idx, header in enumerate(headers, 1):
                max_len = max(
                    len(str(header)),
                    max((len(str(fila.get(header, ""))) for fila in datos), default=0),
                )
                ws.column_dimensions[get_column_letter(col_idx)].width = min(
                    max_len + 4, _MAX_COL_WIDTH
                )

        buffer = io.BytesIO()
        wb.save(buffer)
        contenido = buffer.getvalue()

        if ruta_destino is not None:
            Path(ruta_destino).write_bytes(contenido)
            return b""
        return contenido

    def exportar_pdf(
        self,
        html_content: str,
        ruta_destino: Path | None = None,
    ) -> bytes:
        raise NotImplementedError(
            "PDF no implementado en OpenpyxlExporter. "
            "Registra un exportador HTML→PDF (weasyprint, reportlab) para esta operación."
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


__all__ = ["OpenpyxlExporter"]
