# convivencia_28_boletin_anual_convivencia — Spec

## Contexto

El boletín de **periodo** ya integra convivencia:
- `InformeService.generar_boletin_periodo` (PDF y Excel) llama a
  `self.convivencia_boletin(estudiante_id, periodo_id)` y arma el bloque
  "OBSERVACIONES Y RECOMENDACIONES" (`src/infrastructure/exporters/boletin_pdf.py:377-441`)
  con: `Comportamiento: <nota>` + `nota_observacion` + viñetas por observación pública.

El boletín **anual** (`InformeService.generar_boletin_anual`, líneas 370-421 de
`src/services/informe_service.py`) **no llama a `convivencia_boletin`**:
- PDF: `_build_boletin_anual_pdf` sí invoca `_observaciones_y_firmas(page_w, datos.get("convivencia"))`
  (línea 571), pero `datos["convivencia"]` nunca se puebla → la caja de observaciones sale vacía.
- Excel: el bucle de líneas 404-420 no incluye "Nota Conv." ni "Observaciones".

Además, en el anual la política de qué convivencia mostrar no está definida:
un año tiene varios periodos y `convivencia_boletin` es por periodo. Este spec
define la política y cierra la integración.

Scope:
- `src/services/informe_service.py` (MODIFICAR)
- `src/infrastructure/exporters/boletin_pdf.py` (MODIFICAR — nueva sección de
  columnas por periodo dentro del bloque de observaciones del anual, si se
  aprueba la vista tabular)
- `tests/unit/services/test_informe_service.py` (EXTENDER)

## Política de agregación (decisión de producto)

Por defecto el boletín anual muestra la **evolución completa de la convivencia
del año**, alineada con la lógica de la tabla académica (columna por periodo +
definitiva):

1. **Nota de comportamiento por periodo** (`NotaComportamiento.valor` por
   `periodo_id`) + **definitiva** (promedio simple de las notas presentes; si
   no hay ninguna → `—`).
2. **Concepto final**: `NotaComportamiento.observacion` del **último periodo
   del año con nota registrada** (el más maduro; si ninguno → vacío).
3. **Observaciones públicas**: la unión de todas las `ObservacionPeriodo` con
   `es_publica=True` del año, **agrupadas por `CategoriaObservacion.nombre`**
   (categoría "Sin categoría" al final para las que tengan `categoria_id is None`),
   y dentro de cada categoría ordenadas por periodo. Cada viñeta se prefija
   con el nombre del periodo (`"[P1] texto…"`). Las categorías cuya
   `activa=False` siguen apareciendo si tienen observaciones históricas (no
   se ocultan datos ya emitidos).

Esta política produce un anual coherente con la tabla académica (columnas por
periodo) y evita que un periodo temprano oscurezca el año. El agrupamiento
por categoría refleja que las categorías son **gestionables por la institución**
(catálogo `CategoriaObservacion`), decisión de David 2026-08-12.

## Requisitos (EARS)

- **R1** — `generar_boletin_anual` (PDF) DEBE poblar `datos["convivencia_anual"]`
  con la estructura definida en `Diseño` y el PDF DEBE renderizar:
  (a) fila `Comportamiento: P1=x.x  P2=x.x  P3=x.x  Definitiva=y.y`,
  (b) párrafo con el concepto final,
  (c) para cada categoría con observaciones, un sub-título con el nombre de
      la categoría y una viñeta por observación con formato
      `[Periodo] · Autor: texto`.
- **R2** — `generar_boletin_anual` (Excel) DEBE añadir por asignatura las
  columnas: `Nota Conv. P1 … Pn`, `Nota Conv. Def.`. Las observaciones
  públicas van en la hoja "Convivencia" (definida en `convivencia_31`)
  agrupadas por categoría; no se añaden como columna en la hoja principal
  para no repetir el bloque en cada asignatura. En transición, mientras
  `convivencia_31` no aterrice, este spec añade también `Observaciones Conv.`
  como columna con el join `[P#][Categoría] texto | ...` para no perder el
  dato — la columna se retira cuando la hoja separada exista.
- **R3** — Si el año no tiene ninguna nota ni observación pública, la caja
  del PDF renderiza vacía como hoy (sin romper). Las columnas Excel salen en
  blanco (`None` / `""`).
- **R4** — La política aplica también a `generar_boletines_grupo(anio_id=…)`
  (masivo), ya que reutiliza `generar_boletin_anual`.
- **R5** — El PDF del anual NO DEBE reintroducir por error el bloque de
  convivencia por-periodo (solo el bloque agregado anual).

## Diseño

### 1. Nuevo método en `InformeService`

```
def convivencia_boletin_anual(self, estudiante_id: int, anio_id: int) -> dict:
    """
    Retorna:
      {
        "periodos": [{"id": int, "nombre": str}],   # todos los del año
        "notas_por_periodo": {periodo_id: float | None},
        "definitiva": float | None,                 # promedio de notas presentes
        "concepto":   str   | None,                 # última observacion no vacía
        "observaciones_por_categoria": [
            {
              "categoria": str,               # nombre, "Sin categoría" fallback
              "items": [
                {"periodo": str, "autor": str, "texto": str},
                ...
              ],
            },
            ...
        ],
      }
    Si no hay convivencia_repo → estructura con campos vacíos y lista vacía.
    Requiere periodo_svc_provider (idéntica dependencia a serie_notas_comportamiento).
    """
```

El agrupamiento por categoría se resuelve en el servicio con una consulta a
`self._repo.listar_categorias(solo_activas=False, ...)` para mapear
`categoria_id → nombre`. El orden interno de categorías: activas primero
(alfabético por nombre), inactivas después, "Sin categoría" al final.

- Reusa `self._convivencia_repo.listar_notas_por_estudiante(...)` (ya existe)
  y `self._convivencia_repo.listar_observaciones_por_estudiante(estudiante_id,
  periodo_id, solo_publicas=True)` iterando periodos.
- Alternativa aceptable: apoyarse en
  `ConvivenciaService.serie_notas_comportamiento(estudiante_id, anio_id)` para
  no duplicar la resolución de periodos (ver `convivencia_32`).

### 2. `generar_boletin_anual` populación

En la rama PDF:
```
datos = self._estadisticos_repo.boletin_datos_anual(...)
datos["convivencia_anual"] = self.convivencia_boletin_anual(estudiante_id, anio_id)
return _boletin_mod.generar_boletin_anual_pdf(datos)
```

En la rama Excel: agregar columnas por periodo del bloque devuelto por
`convivencia_boletin_anual` para cada fila del bucle (una fila por asignatura
sigue siendo la unidad; conv se repite entre filas — se acepta por simetría
con `generar_boletin_periodo` Excel).

### 3. `boletin_pdf._observaciones_y_firmas` — extensión

Añadir un modo alterno **cuando `datos.get("convivencia_anual")` está presente**:
- Sustituye/complementa al bloque per-periodo con:
  - Línea negrita: `Comportamiento — <por periodo> · Definitiva: <def>`
  - Párrafo del concepto final.
  - Viñetas de observaciones prefijadas.
- La firma queda igual.

Elegir el diseño más limpio: mantener `_observaciones_y_firmas(page_w, convivencia)`
y añadir un parámetro opcional `convivencia_anual: dict | None = None` que
tenga prioridad sobre `convivencia` si viene. El PDF de periodo sigue pasando
solo `convivencia`; el PDF anual pasa solo `convivencia_anual`.

### 4. Verificación de no regresión

- El boletín de periodo (PDF y Excel) sigue mostrando exactamente lo mismo
  (mismo objeto `convivencia`).
- La caja del PDF sigue soportando el caso "sin datos" (renderiza rectángulo
  vacío como hoy).

## Tareas

- **T1** — Añadir `InformeService.convivencia_boletin_anual` + tests unitarios
  con fake repo (año con 2 periodos con nota, 1 sin nota; observaciones mezcladas).
- **T2** — Poblar `datos["convivencia_anual"]` en `generar_boletin_anual` PDF.
- **T3** — Añadir columnas por periodo + definitiva + observaciones en la rama
  Excel de `generar_boletin_anual`. Actualizar `generar_boletines_grupo` si es
  necesario (debe heredar automáticamente).
- **T4** — Extender `boletin_pdf._observaciones_y_firmas` para soportar el modo
  anual (nuevo parámetro opcional). `_build_boletin_anual_pdf` pasa
  `convivencia_anual` en vez de (o además de) `convivencia`.
- **T5** — Tests: `test_generar_boletin_anual_incluye_convivencia_en_excel`,
  `test_generar_boletin_anual_pdf_puebla_convivencia_anual` (mock exporter/PDF
  y verificar bytes contienen strings esperados o mock cast).

## Verificación

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/services/test_informe_service.py -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/infrastructure/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py   (lo corre el leader)
```

Un boletín anual PDF de un estudiante con notas P1=80/P2=75 y una obs pública
en P2 categorizada como "Responsabilidad" muestra:
`Comportamiento — P1: 80.0 · P2: 75.0 · Definitiva: 77.5`, concepto final
del P2, sub-título "Responsabilidad" y viñeta `[P2] · <autor>: <texto>`.
El Excel del mismo estudiante tiene columnas `Nota Conv. P1=80`,
`Nota Conv. P2=75`, `Nota Conv. Def=77.5`; el bloque de observaciones va en
la hoja "Convivencia" (via `convivencia_31`), agrupado por categoría.
`init.py` verde.
