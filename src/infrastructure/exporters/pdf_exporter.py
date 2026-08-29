"""
WeasyPrintExporter — PDF via weasyprint (con fallback a reportlab), Excel via openpyxl, CSV nativo.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from src.domain.ports.service_ports import IExporterService

# ── Fallback: HTML → PDF via reportlab ───────────────────────────────────────


class _HTMLTableParser(HTMLParser):
    """Parser mínimo que extrae título, cabeceras, filas y metadatos de un HTML tabular simple."""

    def __init__(self) -> None:
        super().__init__()
        self.title: str = ""
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self.meta: dict[str, str] = {}
        self.vertical_cols: list[bool] = []
        self._current_row: list[str] = []
        self._cell: str = ""
        self._in_h1 = self._in_th = self._in_td = False
        self._th_is_vertical = False

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = dict(attrs)
        if tag == "h1":
            self._in_h1 = True
        elif tag == "meta":
            name = attrs_dict.get("name", "")
            content = attrs_dict.get("content", "")
            if name and content:
                self.meta[name] = content
        elif tag == "th":
            self._in_th = True
            self._cell = ""
            self._th_is_vertical = "v" in (attrs_dict.get("class", "").split())
        elif tag == "td":
            self._in_td = True
            self._cell = ""
        elif tag == "tr":
            self._current_row = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._in_h1 = False
        elif tag == "th":
            self._in_th = False
            self.headers.append(self._cell.strip())
            self.vertical_cols.append(self._th_is_vertical)
        elif tag == "td":
            self._in_td = False
            self._current_row.append(self._cell.strip())
        elif tag == "tr" and self._current_row:
            self.rows.append(self._current_row[:])

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self.title += data
        elif self._in_th or self._in_td:
            self._cell += data


def _html_to_pdf_reportlab(html_content: str) -> bytes:
    """
    Convierte HTML simple (tabla + título) a PDF via reportlab.

    - Membrete con institución, tipo de informe, grupo, periodo y fecha.
    - Columnas anchas para texto, estrechas para datos numéricos.
    - Encabezados verticales (rotados 90°) en columnas estrechas cuando
      hay >5 columnas, evitando el apilamiento de letras.
    """
    import io
    from datetime import date as _date

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import (
        ParagraphStyle,
        getSampleStyleSheet,
    )
    from reportlab.lib.units import cm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import (
        Flowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    class _RotatedText(Flowable):
        """Flowable que dibuja texto rotado 90° (lectura de abajo hacia arriba)."""

        def __init__(self, text: str, font_name: str = "Helvetica-Bold",
                     font_size: float = 7, text_color=None):
            super().__init__()
            self.text = text
            self.font_name = font_name
            self.font_size = font_size
            self.text_color = text_color
            self.width = font_size + 6
            self.height = stringWidth(text, font_name, font_size) + 8

        def wrap(self, avail_width, avail_height):
            return self.width, self.height

        def draw(self):
            self.canv.saveState()
            self.canv.rotate(90)
            self.canv.setFont(self.font_name, self.font_size)
            if self.text_color:
                self.canv.setFillColor(self.text_color)
            self.canv.drawString(2, -(self.font_size + 1), self.text)
            self.canv.restoreState()

    parser = _HTMLTableParser()
    parser.feed(html_content)

    buf = io.BytesIO()
    num_cols = len(parser.headers) if parser.headers else 1
    page_size = landscape(A4) if num_cols > 5 else A4

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    story: list = []

    # ── Membrete ──────────────────────────────────────────────────────────────
    page_w = page_size[0] - 3 * cm
    fecha_str = _date.today().strftime("%d/%m/%Y")

    grupo = parser.meta.get("report-grupo", "")
    periodo = parser.meta.get("report-periodo", "")
    asignatura = parser.meta.get("report-asignatura", "")

    col_izq_items = ["INSTITUCIÓN EDUCATIVA ZECI"]
    if parser.title.strip():
        col_izq_items.append(parser.title.strip())
    if grupo:
        col_izq_items.append(f"Curso: {grupo}")
    if asignatura:
        col_izq_items.append(f"Asignatura: {asignatura}")
    if periodo:
        col_izq_items.append(f"Periodo: {periodo}")

    col_izq_text = "<br/>".join(col_izq_items)
    col_der_text = f"Generado: {fecha_str}"

    membrete_style_izq = ParagraphStyle(
        "MembreteIzq",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#2B3674"),
    )
    membrete_style_der = ParagraphStyle(
        "MembreteDerechaStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#555555"),
        alignment=2,
    )

    membrete_data = [
        [
            Paragraph(col_izq_text, membrete_style_izq),
            Paragraph(col_der_text, membrete_style_der),
        ]
    ]
    membrete_tbl = Table(
        membrete_data,
        colWidths=[page_w * 0.7, page_w * 0.3],
    )
    membrete_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#2B6CB0")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(membrete_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # ── Tabla de datos ────────────────────────────────────────────────────────
    if parser.headers:
        has_vertical = any(parser.vertical_cols)

        if has_vertical:
            n_wide = sum(1 for v in parser.vertical_cols if not v)
            n_narrow = sum(1 for v in parser.vertical_cols if v)
            w_narrow = 1.4 * cm
            w_wide_total = page_w - n_narrow * w_narrow
            w_wide = w_wide_total / max(n_wide, 1)
            w_wide = max(w_wide, 3 * cm)
            col_widths = [
                w_narrow if parser.vertical_cols[i] else w_wide
                for i in range(num_cols)
            ]
        elif num_cols > 2:
            col_w_nombre = page_w * 0.35
            col_w_resto = (page_w - col_w_nombre) / (num_cols - 1)
            col_w_resto = max(col_w_resto, 1.5 * cm)
            col_widths = [col_w_nombre] + [col_w_resto] * (num_cols - 1)
        else:
            col_widths = [page_w / num_cols] * num_cols

        total_w = sum(col_widths)
        if total_w > page_w:
            factor = page_w / total_w
            col_widths = [w * factor for w in col_widths]

        cell_style_normal = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
        )
        cell_style_header = ParagraphStyle(
            "CellHeader",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        )

        def _wrap(text, style: ParagraphStyle) -> Paragraph:
            txt = "—" if text is None or str(text).strip().lower() == "none" else str(text)
            return Paragraph(txt, style)

        header_row = []
        for i, h in enumerate(parser.headers):
            if has_vertical and i < len(parser.vertical_cols) and parser.vertical_cols[i]:
                header_row.append(
                    _RotatedText(h, font_size=7, text_color=colors.white)
                )
            else:
                header_row.append(_wrap(h, cell_style_header))

        table_data = [header_row] + [
            [_wrap(c, cell_style_normal) for c in row] for row in parser.rows
        ]

        ts_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#f5f5f5")],
            ),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle(ts_cmds))
        story.append(tbl)
    else:
        story.append(Paragraph("No hay datos para mostrar.", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()


# ── Exportador principal ──────────────────────────────────────────────────────


class WeasyPrintExporter(IExporterService):
    """
    Exportador completo: PDF (weasyprint con fallback a reportlab), Excel via openpyxl, CSV nativo.

    Estrategia PDF:
      1. Intenta weasyprint (mejor fidelidad visual).
      2. Si weasyprint falla (ImportError u OSError por libs nativas), usa reportlab.
      3. Si ambos fallan, lanza NotImplementedError.
    """

    def exportar_pdf(
        self,
        html_content: str,
        ruta_destino: Path | None = None,
    ) -> bytes:
        # Intento 1: weasyprint
        try:
            import weasyprint

            pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        except Exception:
            # Intento 2: reportlab (sin dependencias nativas)
            try:
                pdf_bytes = _html_to_pdf_reportlab(html_content)
            except Exception as exc2:
                raise NotImplementedError(
                    "PDF no disponible. Instala weasyprint o reportlab: "
                    "pip install weasyprint  # o: pip install reportlab"
                ) from exc2

        if ruta_destino is not None:
            Path(ruta_destino).write_bytes(pdf_bytes)
            return b""
        return pdf_bytes

    def exportar_excel(
        self,
        datos: list[dict],
        nombre_hoja: str = "Datos",
        ruta_destino: Path | None = None,
    ) -> bytes:
        from .openpyxl_exporter import OpenpyxlExporter

        return OpenpyxlExporter().exportar_excel(datos, nombre_hoja, ruta_destino)

    def exportar_csv(
        self,
        datos: list[dict],
        ruta_destino: Path | None = None,
        encoding: str = "utf-8-sig",
    ) -> bytes:
        from .null_exporter import _csv_bytes

        contenido = _csv_bytes(datos, encoding)
        if ruta_destino is not None:
            Path(ruta_destino).write_bytes(contenido)
            return b""
        return contenido


__all__ = ["WeasyPrintExporter"]
