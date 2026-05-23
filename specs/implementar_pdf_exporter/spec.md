# Spec — implementar_pdf_exporter

## Módulo: Exportador PDF para informes y boletines
**Versión:** 1.0 — 2026-05-21  
**Tipo:** Nueva implementación de infraestructura  
**Notación:** EARS

---

## Diagnóstico

### Cadena del error

```
boletin_anual.py:65
  svc.generar_boletin_anual(estudiante_id, grupo_id, anio_id, "pdf")
    → InformeService.generar_boletin_anual (informe_service.py:277)
      → exporter.exportar_pdf(html)
        → OpenpyxlExporter.exportar_pdf (openpyxl_exporter.py:95)
          → NotImplementedError: "PDF no implementado en OpenpyxlExporter"
```

### Causas raíz

| # | Causa | Archivo |
|---|---|---|
| 1 | `pdf_exporter.py` existe como placeholder vacío (1 línea, sin implementación) | `src/infrastructure/exporters/pdf_exporter.py` |
| 2 | `exporter_factory.py` nunca intenta usar el PDF exporter — solo prueba openpyxl o NullExporter | `src/infrastructure/exporters/exporter_factory.py` |
| 3 | Ninguna biblioteca PDF está en `requirements.txt` | `requirements.txt` |
| 4 | `InformeService._datos_a_html()` genera HTML sin `<meta charset>` — riesgo de encoding para caracteres españoles | `src/services/informe_service.py` |
| 5 | `boletin_anual.py` y `boletin_periodo.py` capturan `Exception` genérica pero no `NotImplementedError` explícitamente — el mensaje de error no es claro para el usuario | Ambas páginas |

### Alcance de páginas afectadas

Todo flujo que llame `exporter.exportar_pdf(html)` falla:
- `/informes/boletin-periodo` → `InformeService.generar_boletin_periodo(..., "pdf")`
- `/informes/boletin-anual` → `InformeService.generar_boletin_anual(..., "pdf")`
- `/informes/estadisticos` (nuevo) → `exporter.exportar_pdf(html)` para tipos ranking_grupo, consolidado_notas, consolidado_asistencia, consolidado_anual

---

## Biblioteca elegida: `weasyprint`

**Justificación:**
- Convierte HTML+CSS a PDF con alta fidelidad visual — importante para boletines escolares
- Desde la versión 54+ no requiere GTK3 en Windows (usa Pango/Cairo vía cffi)
- Instalación simple: `pip install weasyprint`
- Maneja UTF-8 y caracteres españoles correctamente con el meta charset
- Genera PDFs de aspecto profesional desde HTML tabular simple

**Fallback documentado:**
- Si `weasyprint` no puede instalarse en el entorno específico, la alternativa
  es `xhtml2pdf` (`pip install xhtml2pdf`) con el mismo patrón de llamada:
  se documenta en comentarios del archivo pero no se implementa simultáneamente.

---

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `requirements.txt` | Agregar `weasyprint` |
| `src/infrastructure/exporters/pdf_exporter.py` | Implementar `WeasyPrintExporter` (actualmente vacío) |
| `src/infrastructure/exporters/exporter_factory.py` | Actualizar para priorizar `WeasyPrintExporter` |
| `src/services/informe_service.py` | Agregar `<meta charset="utf-8">` en `_datos_a_html()` |
| `src/interface/pages/informes/boletin_anual.py` | Capturar `NotImplementedError` explícitamente |
| `src/interface/pages/informes/boletin_periodo.py` | Capturar `NotImplementedError` explícitamente |

---

## Requisitos funcionales

### R1 — Implementar `WeasyPrintExporter`

**R1.1** `src/infrastructure/exporters/pdf_exporter.py` debe implementar
`WeasyPrintExporter(IExporterService)` con los tres métodos del contrato:

```python
class WeasyPrintExporter(IExporterService):
    """
    Exportador completo: PDF via weasyprint, Excel via openpyxl, CSV nativo.
    """
    
    def exportar_pdf(
        self,
        html_content: str,
        ruta_destino: Path | None = None,
    ) -> bytes:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
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
```

**R1.2** El import de `weasyprint` se hace dentro del método (lazy import),
no a nivel de módulo. Esto evita que el módulo falle al importarse si
weasyprint no está instalado.

**R1.3** `__all__ = ["WeasyPrintExporter"]`

---

### R2 — Actualizar `exporter_factory.py`

**R2.1** La factory debe intentar los exportadores en orden de capacidad
descendente: PDF+Excel+CSV → Excel+CSV → solo CSV.

```python
def crear_exporter() -> IExporterService:
    # Nivel 1: PDF + Excel + CSV (completo)
    try:
        import weasyprint  # noqa: F401
        import openpyxl    # noqa: F401
        from .pdf_exporter import WeasyPrintExporter
        _log.info("Exportador activo: WeasyPrintExporter (PDF + Excel + CSV)")
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
```

---

### R3 — Corregir `InformeService._datos_a_html()`

**R3.1** El HTML generado debe incluir la declaración de charset UTF-8
para que weasyprint (y cualquier otro motor) maneje correctamente los
caracteres españoles (á, é, í, ó, ú, ñ, ü) presentes en nombres de
estudiantes, asignaturas y títulos.

```python
@staticmethod
def _datos_a_html(datos: list[dict], titulo: str = "Informe") -> str:
    if not datos:
        return (
            f"<html><head><meta charset='utf-8'></head>"
            f"<body><h1>{titulo}</h1><p>No hay datos para mostrar.</p></body></html>"
        )
    
    encabezados = list(datos[0].keys())
    filas_html = "".join(
        "<tr>" + "".join(f"<td>{fila.get(col, '')}</td>" for col in encabezados) + "</tr>"
        for fila in datos
    )
    encabezados_html = "".join(f"<th>{col}</th>" for col in encabezados)
    
    return (
        f"<html><head><meta charset='utf-8'>"
        f"<style>"
        f"body {{ font-family: Arial, sans-serif; font-size: 11px; }}"
        f"h1 {{ font-size: 15px; color: #2B3674; margin-bottom: 8px; }}"
        f"table {{ border-collapse: collapse; width: 100%; }}"
        f"th {{ background-color: #2B6CB0; color: white; padding: 6px 8px; text-align: center; }}"
        f"td {{ border: 1px solid #ddd; padding: 4px 8px; }}"
        f"tr:nth-child(even) {{ background-color: #f5f5f5; }}"
        f"</style></head>"
        f"<body>"
        f"<h1>{titulo}</h1>"
        f"<table>"
        f"<thead><tr>{encabezados_html}</tr></thead>"
        f"<tbody>{filas_html}</tbody>"
        f"</table>"
        f"</body></html>"
    )
```

> El CSS inline es mínimo e intencional — solo para que el PDF generado
> tenga un aspecto aceptable sin necesidad de un motor de plantillas externo.

---

### R4 — Manejo de error explícito en páginas de boletines

**R4.1** `boletin_anual.py` y `boletin_periodo.py`: en `_descargar_boletin()`,
capturar `NotImplementedError` **antes** del `Exception` genérico y mostrar
un mensaje claro:

```python
def _descargar_boletin(...) -> None:
    try:
        svc = Container.informe_service()
        contenido = svc.generar_boletin_...(...)
        ui.download(content=contenido, filename=filename)
    except ValueError as exc:
        ui.notify(f"Exportador no disponible: {exc}", type="negative")
    except NotImplementedError:
        ui.notify(
            "La generación de PDF no está disponible. "
            "Contacta al administrador para instalar weasyprint.",
            type="warning",
        )
    except Exception as exc:
        logger.error("Error generando boletín de %s: %s", nombre, exc, exc_info=True)
        ui.notify(f"Error al generar boletín de {nombre}.", type="negative")
```

---

### R5 — Agregar `weasyprint` a `requirements.txt`

**R5.1** Agregar la línea `weasyprint` al final de `requirements.txt`.

---

## Verificación

Después de implementar, verificar:

1. `pip install weasyprint` ejecutado (o ya instalado en el venv)
2. `pytest -x -q` pasa sin regresiones
3. En el arranque del servidor, el log muestra:
   `Exportador activo: WeasyPrintExporter (PDF + Excel + CSV)`
4. El método `exportar_pdf` en `WeasyPrintExporter` genera bytes no vacíos
   para un HTML de prueba simple

> **Si weasyprint falla en la instalación en Windows:** usar `xhtml2pdf` como
> alternativa. El patrón de llamada es:
> ```python
> from xhtml2pdf import pisa
> import io
> result = io.BytesIO()
> pisa.CreatePDF(io.StringIO(html_content), dest=result, encoding="utf-8")
> return result.getvalue()
> ```
> Agregar `xhtml2pdf` a requirements en su lugar.

---

## Tests de aceptación

**T1** `pytest -x -q` pasa sin errores (≥607 tests).

**T2** `WeasyPrintExporter().exportar_pdf("<html><head><meta charset='utf-8'></head><body><h1>Test</h1></body></html>")` retorna `bytes` no vacíos sin lanzar excepción.

**T3** `WeasyPrintExporter().exportar_excel([{"a": 1, "b": 2}])` retorna bytes de un archivo `.xlsx` válido.

**T4** `exporter_factory.crear_exporter()` retorna una instancia de `WeasyPrintExporter` (verificable con `isinstance`).

**T5** `InformeService._datos_a_html([], "Titulo")` incluye `<meta charset='utf-8'>` en su output.

**T6** El HTML generado por `_datos_a_html([{"Nombre": "García López"}], "Boletín")` procesado por `WeasyPrintExporter().exportar_pdf()` produce bytes > 1000 (PDF real, no vacío).

---

*Spec listo. Paso: `implementar_pdf_exporter`.*
