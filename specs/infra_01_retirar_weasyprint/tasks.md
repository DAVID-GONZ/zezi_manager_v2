# infra_01_retirar_weasyprint — Tareas

Scope: solo los archivos listados en `destino_v2` del paso. Cualquier otro
archivo → PARAR y reportar al leader.

---

## T1 — `ReportLabExporter` en `pdf_exporter.py`

**Artefacto:** `src/infrastructure/exporters/pdf_exporter.py`

- Renombrar `class WeasyPrintExporter(IExporterService)` → `class ReportLabExporter(IExporterService)`.
- Docstring del módulo (línea 2) y de la clase: describen PDF via `reportlab`,
  Excel via `openpyxl`, CSV nativo. Sin "fallback", sin "Estrategia PDF" de
  dos intentos.
- `exportar_pdf`: eliminar el bloque `import weasyprint` / `weasyprint.HTML(...)`
  y su `except Exception`. Queda un solo `try: pdf_bytes = _html_to_pdf_reportlab(html_content)`
  con `except Exception as exc: raise NotImplementedError("PDF no disponible. Instala reportlab: pip install reportlab") from exc`.
- No tocar `_HTMLTableParser` ni `_html_to_pdf_reportlab`.
- `__all__ = ["ReportLabExporter"]`.

**Verificación:**
```
python -m ruff check src/infrastructure/exporters/pdf_exporter.py --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
python -c "from src.infrastructure.exporters.pdf_exporter import ReportLabExporter; print(ReportLabExporter)"
```

---

## T2 — Colapsar niveles en `exporter_factory.py`

**Artefacto:** `src/infrastructure/exporters/exporter_factory.py`

- Docstring de `crear_exporter`: tres niveles, no cuatro.
  ```
  Nivel 1: ReportLabExporter — PDF + Excel + CSV (requiere reportlab + openpyxl)
  Nivel 2: OpenpyxlExporter  — Excel + CSV       (requiere openpyxl)
  Nivel 3: NullExporter      — solo CSV          (sin dependencias)
  ```
- Eliminar el bloque del nivel 1 actual (el de `import weasyprint`) junto con
  su comentario sobre `libgobject`/`libpango`.
- El bloque de `reportlab` pasa a ser el nivel 1, con
  `except ImportError: pass` (ya no `except Exception`) y
  `_log.info("Exportador activo: ReportLabExporter (PDF + Excel + CSV)")`.
- Nivel 2: `_log.warning("reportlab no disponible. PDF no funcionará. Instala: pip install reportlab")`.
- Nivel 3: `_log.warning("openpyxl y reportlab no disponibles. Solo CSV funcionará. Instala: pip install openpyxl reportlab")`.

**Verificación:**
```
python -m ruff check src/infrastructure/exporters/exporter_factory.py --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
python -c "from src.infrastructure.exporters.exporter_factory import crear_exporter; print(type(crear_exporter()).__name__)"
```
Debe imprimir `ReportLabExporter` y **ninguna** advertencia de librerías externas.

---

## T3 — Mensajes de error en los otros dos exportadores y en el puerto

**Artefactos:** `src/infrastructure/exporters/null_exporter.py`,
`src/infrastructure/exporters/openpyxl_exporter.py`,
`src/domain/ports/service_ports.py`

- `null_exporter.py:49`: `"Instala reportlab: pip install reportlab"`.
- `openpyxl_exporter.py:143`: `"Registra un exportador HTML→PDF (reportlab) para esta operación."`
- `service_ports.py:209`: la enumeración de librerías de infraestructura queda
  `(openpyxl, reportlab, etc.)`.
- Cambios de texto únicamente: ninguna firma, ninguna clase, ninguna excepción distinta.

**Verificación:**
```
grep -rn -i "weasyprint" src/infrastructure/ src/domain/ --include="*.py"
```
Sin resultados.

---

## T4 — Avisos al usuario en las páginas de boletín

**Artefactos:** `src/interface/pages/informes/boletin_anual.py`,
`src/interface/pages/informes/boletin_periodo.py`

- Ambos `toast_warning(...)`: `"PDF no disponible. Instala reportlab."`
- No tocar nada más de esas páginas.

**Verificación:**
```
grep -rn -i "weasyprint" src/interface/ --include="*.py"
```
Sin resultados.

---

## T5 — Tests del exportador

**Artefacto:** `tests/unit/infrastructure/test_exporters.py` en verde

- Línea 17: importar `ReportLabExporter`.
- Línea 52 y 191: los `match=` / asserts de mensaje esperan `reportlab`
  (dejar de aceptar `weasyprint` como alternativa: ya no puede aparecer).
- Línea 225: renombrar el test a `test_retorna_reportlab_exporter_en_nivel_1`
  y ajustar su comentario y su assert a `ReportLabExporter`.
- Los tests siguen llamando a `crear_exporter()` y a los métodos reales del
  exportador. Prohibido reimplementar la selección de nivel en el test.

**Verificación:**
```
python -m pytest tests/unit/infrastructure/test_exporters.py -q
```

---

## T6 — `requirements.txt`

**Artefacto:** `requirements.txt`

- Quitar la línea `weasyprint`. No reordenar ni tocar las demás.

**Verificación:**
```
grep -c -i "weasyprint" requirements.txt
```
Debe dar `0`.

---

## Cierre del paso

```
python -m ruff check . --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
python scripts/init.py
grep -rn -i "weasyprint" src/ tests/ requirements.txt
```
`init.py` en `RESULTADO FINAL: TODO VERDE`, y el grep sin resultados.

Escribir el resumen en `progress/impl_infra_01_retirar_weasyprint.md` y
devolver al leader solo esa referencia.
