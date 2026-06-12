# paso_14f_carga_masiva — design

## Servicio: extensión de `HorarioService`

`src/services/horario_service.py`. Métodos nuevos:

```python
def analizar_lote(escenario_id: int, periodo_id: int, filas: list[dict]) -> ReporteLoteDTO
def aplicar_lote(escenario_id: int, periodo_id: int, filas: list[dict],
                 solo_validas: bool = False) -> ResultadoLoteDTO
```

`filas` son dicts primitivos (la interfaz parsea el archivo y no construye
modelos de dominio).

### `analizar_lote` (R3–R7)

1. Resolver cada fila a una asignación del periodo (por `asignacion_id` directo o
   por la terna grupo+asignatura+docente). Fila sin asignación válida → error.
2. Acumular un "escenario virtual" = bloques existentes del escenario + bloques
   válidos ya aceptados del lote. Cada fila se valida contra ese acumulado:
   cruces docente/grupo/sala (incluye cruces internos del lote, R5) y topes
   materia/docente sobre el acumulado (R6).
3. Producir `ReporteLoteDTO` con una `FilaReporteDTO` por fila: `indice`,
   `ok: bool`, `motivo: str | None`, datos normalizados.

### `aplicar_lote` (R8–R10)

- `solo_validas=False` (defecto): si hay cualquier error → no persiste nada,
  retorna el reporte (R8 "todo o nada").
- `solo_validas=True`: persiste únicamente las filas `ok`.
- Persistencia dentro de una transacción del repo (atómica, R10) reutilizando
  `crear_bloque` o un `crear_bloques_masivo(escenario_id, horarios)` del repo.

## DTOs (`src/domain/models/infraestructura.py`)

- `FilaReporteDTO(indice:int, ok:bool, motivo:str|None, resumen:str)`
- `ReporteLoteDTO(filas:list[FilaReporteDTO])` con props `validas`, `invalidas`,
  `todo_ok`.
- `ResultadoLoteDTO(creados:int, omitidos:int, reporte:ReporteLoteDTO)`.

## Repo

`crear_bloques_masivo(horarios: list[Horario]) -> int` en
`IInfraestructuraRepository` + SQLite (un solo `executemany`/transacción).

## Interfaz (`horarios.py`, rama gestión)

Sección "Carga masiva" junto al gestor de escenarios (14e):

- Botón **Descargar plantilla** → `ui.download` de un CSV de ejemplo generado en
  memoria (cabeceras + 1 fila modelo). No requiere exporter.
- **`ui.upload`** que recibe el archivo; al subir, parsear (csv estándar o
  `openpyxl` si `.xlsx`) a `list[dict]`, llamar `analizar_lote`, mostrar
  `skeleton_*` durante el análisis.
- **Reporte**: tabla con `status_badge` verde/rojo por fila y el motivo. Botones
  **Aplicar todo** (deshabilitado si hay errores) y **Aplicar solo válidas**.
- Tras aplicar → `toast_success("N bloques creados, M omitidos")` y refrescar la
  grilla del escenario.

Parsing del archivo: la página convierte a `list[dict]` con claves canónicas;
la normalización de día/hora la hace el DTO/servicio. `ui.upload` ya se usa en
`estudiantes.py` (carga CSV) — seguir ese patrón.

### Alternativa descartada

**Persistir fila por fila a medida que se sube, sin reporte previo.** Descartada:
impide el modo "todo o nada", no detecta cruces internos del lote antes de
escribir, y deja el escenario en estado parcial ante un error a mitad de archivo.
El análisis previo + aplicación atómica da control y previsibilidad.

## Verificación

- `python -m pytest tests/ -q -k lote` cubre R3–R6 (incl. cruce interno y topes
  acumulados).
- `python scripts/check_design.py --file src/interface/pages/academico/horarios.py`
- `python init.py` exit 0.
