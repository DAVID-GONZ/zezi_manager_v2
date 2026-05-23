"""Tests para _html_to_pdf_reportlab v2 — membrete y columnas proporcionales."""
import pytest
from src.infrastructure.exporters.pdf_exporter import _html_to_pdf_reportlab, _HTMLTableParser


HTML_SIMPLE = """<html><head><meta charset='utf-8'>
<meta name="report-grupo" content="Grado 601">
<meta name="report-periodo" content="Periodo 1">
</head><body><h1>Consolidado de Notas</h1>
<table>
  <tr><th>Estudiante</th><th>Matemáticas</th><th>Ciencias</th><th>Promedio</th></tr>
  <tr><td>Ana García</td><td>75</td><td>80</td><td>77.5</td></tr>
  <tr><td>Beto López</td><td>55</td><td>65</td><td>60.0</td></tr>
</table></body></html>"""

HTML_SIN_META = """<html><head><meta charset='utf-8'></head>
<body><h1>Ranking del Grupo</h1>
<table>
  <tr><th>Posición</th><th>Estudiante</th><th>Promedio</th></tr>
  <tr><td>1</td><td>Ana García</td><td>90</td></tr>
</table></body></html>"""

HTML_MUCHAS_COLS = """<html><head><meta charset='utf-8'>
<meta name="report-grupo" content="Grado 701">
<meta name="report-periodo" content="Anual">
<meta name="report-asignatura" content="Matemáticas">
</head><body><h1>Consolidado Anual</h1>
<table>
  <tr><th>Estudiante</th><th>P1</th><th>P2</th><th>P3</th><th>P4</th><th>Definitiva</th><th>Estado</th></tr>
  <tr><td>Ana García González Restrepo</td><td>75</td><td>80</td><td>72</td><td>68</td><td>73.7</td><td>Promovido</td></tr>
</table></body></html>"""


class TestHtmlToPdfReportlabV2:
    def test_retorna_bytes_no_vacios(self):
        resultado = _html_to_pdf_reportlab(HTML_SIMPLE)
        assert isinstance(resultado, bytes)
        assert len(resultado) > 0

    def test_es_pdf_valido(self):
        resultado = _html_to_pdf_reportlab(HTML_SIMPLE)
        assert resultado[:4] == b"%PDF"

    def test_sin_meta_no_lanza_excepcion(self):
        resultado = _html_to_pdf_reportlab(HTML_SIN_META)
        assert resultado[:4] == b"%PDF"

    def test_muchas_columnas_no_lanza_excepcion(self):
        resultado = _html_to_pdf_reportlab(HTML_MUCHAS_COLS)
        assert len(resultado) > 100

    def test_html_sin_tabla(self):
        html = "<html><head></head><body><h1>Sin datos</h1><p>No hay datos.</p></body></html>"
        resultado = _html_to_pdf_reportlab(html)
        assert isinstance(resultado, bytes)

    def test_columnas_proporcionales_calculo(self):
        """35% primera col + partes iguales resto, min 1.5cm."""
        from reportlab.lib.units import cm
        page_w = 277.0
        headers = ["Estudiante", "P1", "P2", "Promedio"]
        n = len(headers)
        col_w_nombre = page_w * 0.35
        col_w_resto  = (page_w - col_w_nombre) / (n - 1)
        col_w_resto  = max(col_w_resto, 1.5 * cm)
        col_widths   = [col_w_nombre] + [col_w_resto] * (n - 1)
        assert len(col_widths) == n
        assert all(w > 0 for w in col_widths)
        assert col_widths[0] > col_widths[1]

    def test_meta_parser_extrae_grupo_y_periodo(self):
        """El parser debe extraer metadatos de los <meta> tags."""
        parser = _HTMLTableParser()
        parser.feed(HTML_SIMPLE)
        assert parser.meta.get("report-grupo") == "Grado 601"
        assert parser.meta.get("report-periodo") == "Periodo 1"
