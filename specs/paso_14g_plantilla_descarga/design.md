# paso_14g_plantilla_descarga — design

## Columnas canónicas (única definición)

```
asignacion_id, grupo, asignatura, docente, dia_semana, hora_inicio, hora_fin, sala
```

- `asignacion_id` — clave de re-carga.
- `grupo`, `asignatura`, `docente` — referencia legible, ignoradas por el parser.
- `dia_semana`, `hora_inicio`, `hora_fin`, `sala` — datos del bloque.

Definir una constante de módulo en `horario_service.py`:
`COLUMNAS_HORARIO = ["asignacion_id", "grupo", "asignatura", "docente", "dia_semana", "hora_inicio", "hora_fin", "sala"]`.

## Servicio: `HorarioService` (dos métodos nuevos, datos puros)

```python
def plantilla_filas(self, periodo_id: int) -> list[dict]
def filas_exportables(self, escenario_id: int, grupo_id: int | None = None) -> list[dict]
```

### `plantilla_filas` (R1–R2)

1. `asignaciones = self._asig.listar_info(FiltroAsignacionesDTO(periodo_id=periodo_id))`.
2. Una fila por asignación:
   ```python
   {
     "asignacion_id": a.asignacion_id,
     "grupo": a.grupo_codigo,
     "asignatura": a.asignatura_nombre,
     "docente": a.docente_nombre,
     "dia_semana": "",
     "hora_inicio": "",
     "hora_fin": "",
     "sala": "Aula",
   }
   ```
3. Retorna `list[dict]` (vacío si no hay asignaciones; la interfaz avisa).

`FiltroAsignacionesDTO` se importa en `horario_service.py` desde
`src.domain.models.asignacion` (mismo origen que ya usa `asignacion_repo`). El
servicio recibe `asignacion_repo` por inyección (ya disponible como `self._asig`).

### `filas_exportables` (R5–R6)

1. `bloques = self._infra.listar_horario_escenario(escenario_id)` (cada item es
   `HorarioInfo` con `asignatura_nombre`, `docente_nombre`, etc.).
2. Si `grupo_id` no es None, filtrar por `b.grupo_id == grupo_id`.
3. Una fila por bloque, normalizando día/hora a string:
   ```python
   {
     "asignacion_id": getattr(b, "asignacion_id", ""),
     "grupo": getattr(b, "grupo_codigo", getattr(b, "grupo_nombre", b.grupo_id)),
     "asignatura": b.asignatura_nombre,
     "docente": b.docente_nombre,
     "dia_semana": _dia_str(b.dia_semana),
     "hora_inicio": _hora_str(b.hora_inicio),
     "hora_fin": _hora_str(b.hora_fin),
     "sala": getattr(b, "sala", "Aula") or "Aula",
   }
   ```
4. Escenario vacío → `[]` (R6: la interfaz exporta solo cabeceras o avisa).

Helpers `_dia_str` / `_hora_str` ya existen como patrón inline en
`analizar_lote`; extraerlos a funciones módulo reutilizables.

## Interfaz (`horarios.py`, rama gestión, solo `puede_escribir`)

En `_seccion_carga_masiva` (paso_14f):

- **Reemplazar** `_descargar_plantilla` para que use el servicio + exportador:
  ```python
  filas = Container.horario_service().plantilla_filas(_s["periodo_id"])
  if not filas:
      toast_warning("No hay asignaciones activas en el periodo.")
      return
  data = Container.exporter_service().exportar_csv(filas)
  ui.download(data, filename="plantilla_horario.csv")
  ```
- **Añadir** botón **Descargar horario** (junto al de plantilla):
  ```python
  esc = _s.get("escenario_sel")
  filas = Container.horario_service().filas_exportables(esc.id)
  if not filas:
      toast_warning("El escenario no tiene bloques para exportar.")
      return
  data = Container.exporter_service().exportar_csv(filas)
  ui.download(data, filename=f"horario_{esc.nombre}.csv")
  ```

`exporter_service().exportar_csv(datos)` retorna `bytes` (utf-8-sig) — apto para
`ui.download`. Si `datos` está vacío pero se quiere archivo con cabeceras, el
exportador maneja `list` vacía; por simplicidad la UI avisa y no descarga (R6).

El exportador ya está cableado en el container (`Container.exporter_service()`),
no requiere wiring nuevo. `HorarioService` no cambia su firma de constructor
(usa `asignacion_repo` e `infra_repo` ya inyectados).

## Tests

### Carga (`tests/unit/services/test_horario_lote.py` — ampliar) — R8
- Ida y vuelta: construir un escenario con N bloques (FakeRepo), `filas_exportables`
  → pasar esas filas a `analizar_lote` sobre un **escenario vacío** → todas `ok`
  (el formato exportado es re-cargable). Verifica que las columnas de referencia
  no rompen el parser.

### Descarga (`tests/unit/services/test_horario_export.py` — nuevo) — R9
- `plantilla_filas`: con FakeAsignacionRepo que retorna 3 asignaciones activas →
  3 filas, claves == `COLUMNAS_HORARIO`, día/hora vacíos, sala "Aula".
- `filas_exportables`: con FakeInfraRepo con 2 bloques → 2 filas con columnas
  completas; filtro por `grupo_id`; escenario vacío → `[]`.

### Integración (`tests/integration/test_asignacion_asignatura_horario.py` — nuevo) — R10
Usa `db_conn`, `seed_result` y los repos reales:
- Toda asignación referencia una asignatura existente y un grupo existente
  (JOIN sin huérfanos).
- Para una asignación del seed, crear un bloque con
  `SqliteInfraestructuraRepository.guardar_horario` sobre el escenario activo y
  verificar que el bloque persistido tiene `grupo_id`/`asignatura_id`/`usuario_id`
  iguales a los de su asignación.
- `listar_horario_escenario(escenario_activo)` incluye el bloque creado y trae
  nombres resueltos (asignatura, docente) no vacíos.

> El escenario activo se obtiene del seed_test (paso_14a, R17 garantiza ≥1
> escenario activo con ≥1 bloque). Resolver su id vía
> `SqliteInfraestructuraRepository(conn).get_escenario_activo(anio_id)` con
> `anio_id` del `seed_result`.

### Alternativa descartada

**Generar el CSV con `csv.writer` dentro de la página (como en 14f).** Funciona
para la plantilla mínima pero duplica la lógica de columnas y no reusa el
exportador del sistema (que ya da utf-8-sig y, si hay openpyxl, Excel). Centralizar
las filas en el servicio y delegar el formato al `IExporterService` mantiene una
sola definición de columnas y abre la puerta a Excel sin tocar la página.

## Verificación

- `python -m pytest tests/ -q -k "lote or export or asignacion_asignatura_horario"`.
- `python scripts/check_design.py --file src/interface/pages/academico/horarios.py`.
- `python init.py` exit 0; suite sin regresiones.
