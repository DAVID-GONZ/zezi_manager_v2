# convivencia_37_observador_estudiante — Spec

## Contexto

El "observador del estudiante" es el documento central del debido proceso
en colegios colombianos. Es una bitacora cronologica por estudiante que
acumula todas las intervenciones de convivencia: observaciones narrativas,
registros de comportamiento, seguimientos, compromisos, citaciones y
descargos. En la mayoria de instituciones se lleva como un cuaderno fisico
o formato impreso con:

- Encabezado: datos de la institucion y del estudiante.
- Entradas cronologicas: fecha, descripcion, tipo, medida, responsable.
- Seccion de firmas.

El sistema ya tiene la pagina `/convivencia/observaciones` (titulada
"Observador del estudiante" en el rail) pero solo sirve para CREAR
observaciones — no permite VER la cronologia completa ni EXPORTAR un
documento formal. Esta spec transforma esa pagina en un verdadero
observador: arriba la vista cronologica con exportacion PDF/Excel, abajo
el formulario de creacion.

El PDF usa formato **narrativo** (bloques con fecha en negrita, texto
corrido, seguimiento como sub-entradas indentadas) — semejante a los
reportes escritos que se llevan actualmente en papel.

Scope:
- `src/services/convivencia_service.py` (EXTENDER — metodo consolidador
  + exportacion)
- `src/infrastructure/exporters/observador_pdf.py` (NUEVO)
- `src/interface/pages/convivencia/observaciones.py` (MODIFICAR — dual
  proposito)
- `src/interface/presenters/convivencia/observaciones_presenter.py` (EXTENDER)
- `tests/` (EXTENDER)

## Requisitos (EARS)

### Servicio

- **R1** — DEBE existir un metodo `observador_estudiante(estudiante_id,
  anio_id, periodo_id=None)` que retorne un dict con:
  - `estudiante`: datos identificatorios (nombre, apellido, documento,
    grupo, grado).
  - `institucion`: datos para el membrete (nombre, DANE, rector, etc.).
  - `anio`: nombre del ano lectivo.
  - `periodo`: nombre del periodo si se filtra, None si es anual.
  - `entradas`: lista cronologica (fecha ASC) unificando observaciones
    publicas + registros de comportamiento + entradas de seguimiento.
  - `resumen`: totales (fortalezas, dificultades, compromisos, citaciones,
    descargos, notas de comportamiento por periodo).
- **R2** — Cada entrada DEBE contener: `fecha` (datetime), `tipo`
  ("observacion" | "registro" | "seguimiento"), `subtipo` (valor de
  TipoRegistro o "publica"/"privada"), `tipo_situacion` (nombre o None),
  `descripcion`, `medida` (nombre o None), `responsable` (nombre del
  usuario), `categoria` (nombre o None, solo para observaciones).
- **R3** — Las entradas de seguimiento DEBEN aparecer como sub-entradas
  del registro al que pertenecen (agrupadas por `registro_id`), no como
  entradas independientes de primer nivel.
- **R4** — DEBE existir un metodo `exportar_observador(estudiante_id,
  anio_id, formato, periodo_id=None)` que retorne bytes (PDF o Excel).

### PDF

- **R5** — El PDF DEBE tener:
  1. Membrete institucional (patron de `boletin_pdf.py`).
  2. Ficha del estudiante (nombre, documento, grupo, grado, ano).
  3. Titulo: "OBSERVADOR DEL ESTUDIANTE".
  4. Entradas cronologicas en formato narrativo:
     - Fecha en negrita ("15 de marzo de 2026").
     - Tipo y clasificacion entre corchetes ("Dificultad [Tipo II]").
     - Texto de la descripcion en corrido.
     - Medida aplicada si existe ("Medida: Citacion a acudiente").
     - Responsable.
     - Sub-entradas de seguimiento indentadas con fecha y texto.
  5. Resumen estadistico.
  6. Seccion de firmas: Director de grupo | Coordinador | Acudiente |
     Estudiante.
- **R6** — El PDF DEBE generarse con ReportLab (patron de `boletin_pdf.py`)
  para consistencia con el resto de documentos del sistema.

### Excel

- **R7** — El Excel DEBE contener una hoja con columnas: Fecha, Tipo,
  Clasificacion, Descripcion, Medida, Responsable, Seguimiento (texto
  concatenado de las entradas de seguimiento del registro).

### UI

- **R8** — La pagina `/convivencia/observaciones` DEBE dividirse en dos
  zonas:
  - **Superior**: vista cronologica del observador con selectores
    (grupo → estudiante, filtro por periodo opcional), timeline de
    entradas, y botones de exportacion PDF/Excel.
  - **Inferior**: formulario de creacion de nuevas observaciones (mantiene
    la funcionalidad actual).
- **R9** — La timeline DEBE mostrar cada entrada como un card o bloque
  con fecha prominente, tipo/subtipo, texto, y responsable.
- **R10** — RBAC: director, coordinador y director de grupo acceden a
  cualquier estudiante de sus grupos. Profesor ve solo los estudiantes
  de sus asignaciones.
- **R11** — Si no hay estudiante seleccionado, la zona superior DEBE
  mostrar un estado vacio con instruccion de seleccionar estudiante.
- **R12** — Los botones "Exportar PDF" / "Exportar Excel" DEBEN ofrecer
  `ui.download` con el archivo generado.

## Diseno

### T1 — Metodo consolidador en el servicio

En `convivencia_service.py`:
```python
def observador_estudiante(
    self,
    estudiante_id: int,
    anio_id: int,
    periodo_id: int | None = None,
) -> dict:
```

Fuentes de datos (consultas acotadas):
1. Datos del estudiante via `_estudiante_svc_provider`.
2. Datos de la institucion via `Container.institucion_service()` o
   contexto del tenant.
3. Periodos del ano via `_periodo_svc_provider`.
4. Observaciones publicas: `listar_observaciones_por_estudiante` (filtrado
   por periodo si aplica, `solo_publicas=True`).
5. Registros de comportamiento: `listar_registros(FiltroConvivenciaDTO(...))`.
6. Entradas de seguimiento: `listar_entradas_seguimiento(registro_id)`
   por cada registro (batch si es posible, o iteracion acotada).
7. Tipos de situacion y medidas: resolverlos una sola vez con diccionarios
   `{id: nombre}` para evitar N+1.
8. Notas de comportamiento por periodo: `listar_notas_por_estudiante`.

Unificacion: armar una lista de dicts heterogenea, cada uno con los campos
de R2, ordenar por `fecha` ASC. Las entradas de seguimiento se anidan
dentro del registro padre.

### T2 — Metodo exportador

```python
def exportar_observador(
    self,
    estudiante_id: int,
    anio_id: int,
    formato: str,
    periodo_id: int | None = None,
) -> bytes:
```

- `formato="pdf"`: llama a `observador_pdf.generar_observador_pdf(datos)`.
- `formato="excel"`: aplana las entradas a dicts y usa
  `self._exporter.exportar_excel(...)`.

### T3 — Renderer PDF (nuevo archivo)

Nuevo archivo `src/infrastructure/exporters/observador_pdf.py`:
- Funcion publica: `def generar_observador_pdf(datos: dict) -> bytes`.
- Usa `SimpleDocTemplate` de ReportLab con `platypus` flowables.
- Reutiliza los estilos y dimensiones de `boletin_pdf.py` (margen, fuentes,
  tamaño de pagina A4 vertical).
- Story:
  1. Membrete (tabla con logo placeholder + nombre institucion + DANE +
     rector). Extraer de `boletin_pdf._membrete` si posible, o duplicar
     inicialmente.
  2. Ficha del estudiante (tabla compacta: Nombre, Documento, Grupo,
     Grado, Ano).
  3. Titulo centrado: "OBSERVADOR DEL ESTUDIANTE".
  4. Spacer.
  5. Por cada entrada en `datos["entradas"]`:
     - `Paragraph` con fecha en bold, tipo/subtipo entre corchetes.
     - `Paragraph` con la descripcion (indent normal).
     - Si tiene medida: `Paragraph` italic "Medida: {nombre}".
     - `Paragraph` gris con "Responsable: {nombre}".
     - Si tiene seguimiento_entries: por cada sub-entrada, `Paragraph`
       indentado con flecha "→", fecha, texto, responsable.
     - `Spacer` entre entradas.
  6. `HRFlowable` separador.
  7. Resumen: tabla compacta con totales.
  8. Seccion de firmas: tabla de 4 columnas con lineas para firma.

### T4 — Transformacion de la pagina

Modificar `observaciones.py` para dividirlo en dos zonas. El layout usa
el patron `page-body` existente:

**Zona superior** (nuevo):
```python
with ui.column().classes("page-section"):
    # Selectores: grupo → estudiante → periodo (opcional)
    # Timeline de entradas (ui.column de cards)
    # Botones de exportacion
```

**Zona inferior** (existente, preservar):
```python
with ui.column().classes("page-section"):
    # Formulario de creacion de observaciones (codigo actual)
```

La carga de datos de la timeline se dispara al seleccionar un estudiante.
Si cambia el estudiante, se recarga. Si no hay estudiante, se muestra
`empty_state("Selecciona un estudiante para ver su observador")`.

### T5 — Presenter

Extender `ObservacionesPresenter` con state adicional:
```python
"observador_entradas": [],
"observador_resumen": {},
"observador_estudiante_id": None,
"observador_periodo_filter": None,
```

Metodos:
- `cargar_observador(estudiante_id, anio_id, periodo_id=None)` — llama al
  servicio y actualiza el state.
- `puede_exportar() -> bool` — True si hay entradas cargadas.

### T6 — Tests

- Test de servicio: `observador_estudiante` retorna entradas unificadas
  y ordenadas cronologicamente.
- Test de servicio: `exportar_observador("pdf")` retorna bytes no vacios.
- Test de servicio: `exportar_observador("excel")` retorna bytes no vacios.
- Test de PDF: `generar_observador_pdf` produce PDF valido con membrete,
  ficha y entradas.
- Test de presenter: `cargar_observador` actualiza state correctamente.

## Verificacion

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Escenarios manuales:
- Seleccionar estudiante con registros → la timeline muestra entradas
  cronologicas con fechas, tipos y descripciones.
- Exportar PDF → documento con membrete, ficha, entradas narrativas,
  seguimiento indentado, resumen y firmas.
- Exportar Excel → hoja con columnas y filas por entrada.
- Estudiante sin registros → timeline vacia con mensaje apropiado.
- Filtrar por periodo → solo se muestran entradas de ese periodo.
- Crear una observacion desde el formulario inferior → aparece en la
  timeline superior sin recargar la pagina completa.

`init.py` verde.

## Dependencias

- Depende de convivencia_34 (tipos_situacion) para mostrar la
  clasificacion en las entradas del observador.
- Depende de convivencia_35 (entradas_seguimiento) para mostrar la
  bitacora de seguimiento como sub-entradas.
- Depende de convivencia_36 (medidas_pedagogicas) para mostrar la
  medida aplicada.
- Si se implementa sin las dependencias, los campos correspondientes
  aparecen como None/vacios (degradacion gracia).
