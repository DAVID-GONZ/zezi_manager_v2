# infra_01_retirar_weasyprint — Diseño

## Problema técnico

`weasyprint` es un binding CFFI: el paquete de PyPI no trae las DLL de
GTK/Pango. En `weasyprint/text/ffi.py` el módulo llama a `ffi.dlopen()` sobre
`libgobject-2.0-0`, `libpango-1.0-0`, `libharfbuzz-0`, `libfontconfig-1` y
`libpangoft2-1.0-0` **en tiempo de import**, buscando en dos rutas fijas
(`C:\msys64\mingw64\bin` y `C:\Program Files\GTK3-Runtime Win64\bin`, o lo que
indique `WEASYPRINT_DLL_DIRECTORIES`). Si falla, hace `print()` a stdout —
no `logging` — y relanza `OSError`.

Consecuencia: el simple `import weasyprint` de `exporter_factory` imprime un
bloque de advertencia en cada arranque, fuera de todo control del logger del
proyecto, y el nivel 1 de la factory nunca se alcanza. `reportlab` ya es el
motor real. El código describe un motor que no se usa.

## Decisión

Retirar `weasyprint` de la cadena de exportación. `reportlab` pasa de fallback
a motor único y declarado.

## Archivos y responsabilidad exacta

| Archivo | Cambio |
|---|---|
| `src/infrastructure/exporters/pdf_exporter.py` | Renombrar `WeasyPrintExporter` → `ReportLabExporter`. En `exportar_pdf`, eliminar el intento `weasyprint` y llamar directo a `_html_to_pdf_reportlab`. Actualizar docstrings, mensaje de `NotImplementedError` y `__all__`. |
| `src/infrastructure/exporters/exporter_factory.py` | Colapsar niveles 1 y 1b en un solo nivel 1 (`reportlab` + `openpyxl` → `ReportLabExporter`). Estrechar `except Exception` a `except ImportError`. Actualizar docstring de prioridades y los dos mensajes de `_log.warning`. |
| `src/infrastructure/exporters/null_exporter.py` | Mensaje de error: nombrar solo `reportlab`. |
| `src/infrastructure/exporters/openpyxl_exporter.py` | Mensaje de error: nombrar solo `reportlab`. |
| `src/domain/ports/service_ports.py` | Docstring del puerto: la lista de ejemplos de librerías de infraestructura deja de citar `weasyprint`. |
| `src/interface/pages/informes/boletin_anual.py` | Toast: `"PDF no disponible. Instala reportlab."` |
| `src/interface/pages/informes/boletin_periodo.py` | Toast: idéntico al anterior. |
| `tests/unit/infrastructure/test_exporters.py` | Importar y afirmar `ReportLabExporter`; ajustar los `match=` de los mensajes; renombrar `test_retorna_weasyprint_cuando_reportlab_disponible` a un nombre que describa el nivel 1. |
| `requirements.txt` | Quitar la línea `weasyprint`. |

## Por qué `except ImportError` y no `except Exception`

El `except Exception` de la factory existía por una única razón, documentada en
su propio comentario: `weasyprint` podía fallar con `OSError` al cargar libs
nativas, no solo con `ImportError`. Sin `weasyprint`, el bloque importa
`reportlab` y `openpyxl`, ambos Python puro: el único fallo esperable es
`ImportError`. Mantener `except Exception` ahí convertiría cualquier error de
programación dentro del `try` (un `AttributeError`, un `TypeError` en el
constructor) en un silencioso descenso a Excel-sin-PDF, imposible de
diagnosticar. Estrecharlo es parte del cambio, no un extra.

## Nombre de la clase

`ReportLabExporter` — nombra el motor, igual que `OpenpyxlExporter` nombra el
suyo. La alternativa `PdfExporter` describiría la salida y no el motor,
rompiendo la simetría con los otros dos exportadores y volviendo a ocultar
qué dependencia hay que instalar cuando falla.

## Alternativa descartada

**Instalar el runtime GTK y dejar `weasyprint` como nivel 1.** Habría dado
render HTML/CSS real (reutilizable con el design system y sus tokens) y PDF de
mejor fidelidad. Descartada: obliga a cada máquina de desarrollo y a cada
entorno de despliegue a instalar librerías nativas fuera de `pip`, un requisito
que el proyecto no tiene hoy en ninguna otra dependencia. La puerta de calidad
del proyecto se ejecuta con `pip install` y nada más; añadir un binario del
sistema operativo al contrato de arranque es coste permanente a cambio de una
fidelidad que los informes tabulares actuales no necesitan.

Nota para el futuro: si un informe llega a exigir maquetación CSS real, el
punto de reentrada es un nivel nuevo en `crear_exporter()` por delante de
`ReportLabExporter`, sin tocar el resto de la cadena.

## Entorno (fuera del scope de código, lo ejecuta el leader)

`pip uninstall -y weasyprint` en `.venv`, para que el entorno instalado
coincida con `requirements.txt`. Los paquetes que `weasyprint` arrastró
(`pydyf`, `tinycss2`, `cssselect2`, `pyphen`) quedan huérfanos sin efecto;
`fonttools` lo usa `matplotlib`/otros y no se toca.
