# convivencia_31_boletin_periodo_excel_seccion — Spec

## Contexto

`InformeService.generar_boletin_periodo` en su rama Excel (líneas 336-364 de
`src/services/informe_service.py`) genera **una fila por asignatura** con las
columnas de convivencia (`Nota Conv.`, `Observaciones`) repetidas
idénticamente en cada fila. Con 10 asignaturas la nota de comportamiento se
duplica 10 veces; el join de observaciones también. Es ruidoso y sugiere
falsamente que la convivencia depende de la asignatura.

Este spec limpia la exportación Excel del boletín de periodo (y del anual
tras `convivencia_28`) llevando la convivencia a **una sección separada**
del mismo libro/hoja, sin tocar el PDF (que ya la tiene aparte).

Scope:
- `src/services/informe_service.py` (MODIFICAR)
- `src/infrastructure/exporters/openpyxl_exporter.py` (verificar API: si ya
  soporta múltiples secciones/hojas, no tocar; si no, extender)
- `tests/unit/services/test_informe_service.py` (EXTENDER)

## Requisitos (EARS)

- **R1** — El Excel del boletín de periodo NO DEBE repetir columnas de
  convivencia por asignatura. Las columnas `Nota Conv.` y `Observaciones` (y
  `Eventos Conv.` de `convivencia_29`, si aplica) se retiran del bucle de
  asignaturas.
- **R2** — El Excel DEBE contener una **segunda sección** (idealmente segunda
  hoja del mismo libro) titulada "Convivencia" con:
  - Fila: `Nota de comportamiento`, `<valor o —>`.
  - Fila: `Concepto`, `<nota_observacion o vacío>`.
  - Sub-tablas de **Observaciones públicas agrupadas por categoría**:
    para cada `CategoriaObservacion` con al menos una observación pública
    del periodo, un mini-encabezado con el nombre de la categoría y filas
    `Fecha | Autor | Texto`. Las observaciones sin categoría van bajo el
    encabezado "Sin categoría" al final. Las categorías inactivas siguen
    apareciendo si tienen observaciones históricas (no se ocultan datos ya
    emitidos). Decisión de David 2026-08-12: al boletín van solo las
    observaciones públicas y las categorías son gestionables.
  - Sub-tabla `Eventos` con `Fecha | Tipo | Descripción` (depende de
    `convivencia_29`; si no está implementado, omitir la sub-tabla).
- **R3** — El Excel del boletín anual DEBE aplicar el mismo criterio, con la
  hoja "Convivencia" mostrando la tabla `Periodo | Nota | Concepto`, las
  sub-tablas de observaciones **agrupadas por categoría** con `Periodo | Autor
  | Texto`, y la sub-tabla de eventos agregados por año.
- **R4** — El nombre de la hoja principal se conserva ("Boletín Periodo" /
  "Boletín Anual"); la nueva hoja se llama "Convivencia" (≤31 chars).
- **R5** — Si no hay convivencia_repo (nulo), la hoja "Convivencia" NO se
  crea (no aparece hoja vacía).

## Diseño

### 1. Nuevo método de exporter (si hace falta)

Verificar `openpyxl_exporter.IExporterService.exportar_excel`: hoy acepta
`datos: list[dict], nombre_hoja: str`. Se necesita construir un libro con dos
hojas heterogéneas. Opciones:

**Opción A** (preferida — sin romper puerto): añadir un método al puerto y a
la implementación:
```
def exportar_excel_multi_hoja(
    self, hojas: list[tuple[str, list[dict] | list[list]]]
) -> bytes: ...
```
Recibe una lista `(nombre_hoja, filas)` y las escribe todas en un solo libro.
Cada `filas` puede ser lista de dicts (con encabezado desde keys) o lista de
listas (para tablas irregulares como la de Convivencia).

**Opción B** (más simple si `merge_excels` ya lo permite): generar cada hoja
con `exportar_excel` y fusionar con `merge_excels(...)` que ya existe (líneas
647-677). El coste: dos `write` intermedios y una lectura + copia. Aceptable
si no queremos ampliar el puerto.

Elegir **B** para no expandir contratos si el volumen es bajo (un boletín ≠
millones de filas).

### 2. Constructores

En `InformeService`:

```
def _hoja_convivencia_periodo(self, estudiante_id: int, periodo_id: int) -> list[list]:
    conv = self.convivencia_boletin(estudiante_id, periodo_id)
    filas: list[list] = []
    filas.append(["CONVIVENCIA"])
    filas.append([])
    filas.append(["Nota de comportamiento", conv["nota"] if conv["nota"] is not None else "—"])
    filas.append(["Concepto",               conv["nota_observacion"] or ""])
    filas.append([])
    for grupo in conv.get("observaciones_por_categoria", []):
        # grupo = {"categoria": str, "items": [{"fecha","autor","texto"} ...]}
        if not grupo["items"]:
            continue
        filas.append([grupo["categoria"]])                 # mini-encabezado por categoría
        filas.append(["Fecha", "Autor", "Texto"])
        for it in grupo["items"]:
            filas.append([it["fecha"], it["autor"], it["texto"]])
        filas.append([])                                    # separador visual
    if conv.get("registros"):
        filas.append(["Eventos"])
        filas.append(["Fecha", "Tipo", "Descripción"])
        for r in conv["registros"]:
            filas.append([r["fecha"], r["tipo"], r["descripcion"]])
    return filas
```

Análogo `_hoja_convivencia_anual` iterando por periodos (usa
`convivencia_boletin_anual`), con la sub-tabla anual mostrando `Periodo |
Autor | Texto` en vez de `Fecha | Autor | Texto`.

**Contrato del `paquete_boletin_*` respecto a categorías**: para materializar
la agrupación por categoría con `Fecha` y `Autor` (no solo texto), la clave
`observaciones_por_categoria` NO es una lista de strings sino:
```
[
  {"categoria": "Responsabilidad",
   "items": [
     {"fecha": "2026-04-12", "autor": "Nombre docente", "texto": "..."},
     ...
   ]},
  ...
]
```
Este cambio implica que en `convivencia_28` (para el anual) y `convivencia_32`
(que centraliza en `ConvivenciaService`) los DTOs devueltos incluyan `fecha`
y `autor` por observación. Se anota como **evolución de contrato** — ver
sección "Impacto en 28/32" al final.

### 3. Wiring

- En la rama Excel de `generar_boletin_periodo`: retirar las claves
  `Nota Conv.` y `Observaciones` de las filas del bucle de asignaturas.
  Construir bytes de hoja "Boletín Periodo" con `exportar_excel` y bytes de
  hoja "Convivencia" con un `exporter.exportar_excel` alimentado con la
  matriz irregular (requiere que `exportar_excel` acepte `list[list]` — si
  hoy solo acepta `list[dict]`, extender o usar `merge_excels` con dos
  workbooks generados vía openpyxl directamente en un helper interno).
- `merge_excels` (líneas 647-677 de `informe_service.py`) DEBE aceptar la
  lista `[("Boletín Periodo", bytes_main), ("Convivencia", bytes_conv)]`.
- El helper `_serializar_hoja_matriz(filas: list[list], nombre: str) -> bytes`
  vive en `InformeService` (usa `openpyxl` directamente; no rompe el puerto,
  solo compone dentro del servicio).

### 4. Excel masivo — hoja resumen "Convivencia — todos"

Decisión de David 2026-08-12: el masivo `generar_boletines_grupo(formato="excel")`
mantiene una hoja principal por estudiante (como hoy) **y añade una hoja
resumen "Convivencia — todos"** al final del libro. La hoja "Convivencia"
individual por estudiante NO se incluye (evita explotar el número de hojas
en cursos grandes).

Estructura de "Convivencia — todos" (matriz plana, ordenada por apellido +
nombre del estudiante):

- Título: `CONVIVENCIA — <Grupo> — <Periodo|Año>`
- Encabezado modo periodo:
  `Estudiante | Nota | Concepto | # Obs. públicas | # Eventos`
- Encabezado modo anual:
  `Estudiante | P1 | P2 | ... | Pn | Definitiva | Concepto final | # Obs. públicas | # Eventos`
- Una fila por estudiante con los datos consolidados; celdas de nota vacías
  cuando no hay registro (no cero).
- Al pie, dos sub-tablas apiladas (opcionales, solo si tienen contenido):
  - "Observaciones públicas (todas)" — `Estudiante | Categoría | Fecha o
    Periodo | Autor | Texto` con TODAS las observaciones del grupo/periodo,
    agrupadas visualmente por estudiante (o pre-ordenadas por estudiante +
    categoría). Sirve al director de grupo para leer todo el material del
    boletín en un solo lugar.
  - "Eventos de convivencia" — `Estudiante | Fecha | Tipo | Descripción`
    con los eventos ya filtrados por la política del tenant
    (`convivencia_29`).

Constructor nuevo en `InformeService`:
```
def _hoja_convivencia_resumen_grupo(
    self, grupo_id: int, periodo_id: int | None, anio_id: int | None,
) -> list[list]:
    """Matriz para la hoja 'Convivencia — todos' del libro masivo."""
```
Reusa `ConvivenciaService.resumen_convivencia_grupo` para contadores y las
listas batch (`listar_observaciones_por_grupo` + `listar_registros(filtro
por grupo)`) para los pies. En anual, itera periodos.

`generar_boletines_grupo` cambia así:
1. Genera los boletines individuales (sin su hoja "Convivencia" cuando la
   fuente los produce con dos hojas: `merge_excels` toma solo la primera).
2. Añade al final una hoja adicional "Convivencia — todos" con el resultado
   de `_hoja_convivencia_resumen_grupo(...)` serializado por
   `_serializar_hoja_matriz`.
3. `merge_excels` acepta la lista completa `[(nombre, bytes), ...]` en
   orden.

## Tareas

- **T1** — Retirar las columnas duplicadas del bucle de asignaturas en las
  ramas Excel de `generar_boletin_periodo` y `generar_boletin_anual`.
- **T2** — Añadir `_hoja_convivencia_periodo` y `_hoja_convivencia_anual`.
- **T3** — Añadir `_serializar_hoja_matriz` (openpyxl inline) y fusionar con
  la hoja principal via `merge_excels`.
- **T4** — Ajustar `generar_boletines_grupo` (Excel): `merge_excels` toma
  solo la hoja principal de cada boletín individual y añade la hoja
  "Convivencia — todos" al final. Nuevo `_hoja_convivencia_resumen_grupo`.
- **T5** — Tests: `test_boletin_periodo_excel_tiene_hoja_convivencia`,
  `test_boletin_periodo_excel_no_duplica_columnas_conv`,
  `test_boletines_grupo_excel_tiene_hoja_resumen`,
  `test_hoja_resumen_ordena_por_estudiante`,
  `test_hoja_resumen_incluye_pies_obs_y_eventos_cuando_hay`.

## Verificación

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/services/test_informe_service.py -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Abrir en Excel el boletín de periodo de un estudiante: dos hojas —
"Boletín Periodo" con `Área | Asignatura | Nota | Presentes | F.Inj | F.Just
| Retrasos | Excusas` (sin columnas conv) y "Convivencia" con la sección
tabulada agrupada por categoría.

Abrir el masivo del grupo: N hojas (una por estudiante, solo la principal)
+ 1 hoja "Convivencia — todos" al final con la matriz consolidada y los
pies de observaciones/eventos. `init.py` verde.

## Dependencias

- `convivencia_28` (anual) para R3.
- `convivencia_29` (registros) para la sub-tabla de eventos.

## Impacto en 28 / 32 (evolución de contrato)

- **28**: `convivencia_boletin_anual` devuelve
  `observaciones_por_categoria: list[{"categoria", "items": [{"periodo",
  "autor", "texto"}]}]` en vez de `list[str]`. La rama PDF anual sigue
  imprimiendo un sub-título por categoría + viñetas, ahora con la línea
  `[Periodo] · Autor: texto` para preservar la información.
- **32**: `paquete_boletin_periodo` devuelve
  `observaciones_por_categoria: list[{"categoria", "items": [{"fecha",
  "autor", "texto"}]}]`. Se elimina la clave plana `observaciones` (o se
  mantiene como derivada temporal si algún consumidor externo la usa —
  auditar y limpiar en 32).
- La transición se hace en orden 28 → 29 → 31 → 32; los tests de cada spec
  cubren la nueva forma del DTO. `boletin_pdf._observaciones_y_firmas`
  itera `observaciones_por_categoria` para renderizar el bloque agrupado.
