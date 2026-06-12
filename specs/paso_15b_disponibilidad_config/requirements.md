# paso_15b_disponibilidad_config — requirements

Segundo paso del épico generador de horarios (paso_15). Introduce dos elementos
que el motor de generación (paso_15c) necesita como entrada:

1. **Disponibilidad docente**: qué franjas de qué días NO puede dar clase un
   profesor (restricción dura adicional al solver).
2. **Configuración de generación** (`config_generacion`): parámetros y filtros
   de una ejecución del generador — qué periodo, qué plantilla de franjas, a qué
   escenario volcar, qué grupos incluir y con qué pesos de calidad.

Depende de `paso_15a` (franjas) y del modelo base de usuarios/grupos/periodos.
Notación EARS. Fuente de verdad: `src/infrastructure/db/schema.py`,
`src/domain/models/`, `src/domain/ports/infraestructura_repo.py`,
`src/services/infraestructura_service.py`.

---

## Disponibilidad docente

- **R1** — El sistema DEBERÁ persistir la **disponibilidad docente** en una tabla
  `disponibilidad_docente` con columnas: `id`, `usuario_id` (FK usuarios),
  `dia_semana` (mismo CHECK que `horarios`), `franja_orden` (entero ≥ 1),
  `disponible` (bool, default 1). Unicidad: `UNIQUE(usuario_id, dia_semana,
  franja_orden)`.
- **R2** — La semántica DEBERÁ ser de **lista de excepciones**: por defecto un
  docente está disponible en todo; solo se almacenan las entradas donde
  `disponible = 0`. El sistema DEBERÁ tratar como disponible cualquier
  `(usuario_id, dia_semana, franja_orden)` no registrado.
- **R3** — El sistema DEBERÁ exponer métodos para: registrar/actualizar la
  disponibilidad de un docente en una franja (`upsert`), listar las restricciones
  de un docente (`listar_por_docente(usuario_id)`), consultar si un docente está
  disponible en un slot concreto (`es_disponible(usuario_id, dia, orden) -> bool`,
  devuelve `True` si no existe fila o si `disponible = 1`), y borrar todas las
  restricciones de un docente (`limpiar_docente(usuario_id)`).
- **R4** — La disponibilidad DEBERÁ poderse cargar en bloque desde una lista de
  dicts (`cargar_disponibilidad_lote(usuario_id, slots: list[dict])`) con claves
  `dia_semana` y `franja_orden`, marcando todos como `disponible = 0`. Deberá ser
  idempotente (upsert).

## Configuración de generación

- **R5** — El sistema DEBERÁ persistir las **configuraciones de generación** en
  `config_generacion` con: `id`, `nombre` (único), `periodo_id` (FK), `anio_id`
  (FK configuracion_anio), `plantilla_id` (FK plantillas_franja), `estado`
  (`borrador` | `generado` | `aplicado`), `grupos_json` (lista de grupo_ids
  incluidos, vacío = todos), `pesos_json` (pesos de restricciones blandas),
  `escenario_destino_id` (FK escenarios_horario, nullable — se crea en la
  generación), `created_at`, `updated_at`.
- **R6** — `grupos_json` y `pesos_json` DEBERÁN almacenarse como texto JSON en
  SQLite. Al leer, deserializarse a `list[int]` y `dict` respectivamente.
  Valores por defecto: `grupos_json = []` (todos los grupos del periodo),
  `pesos_json = {"huecos": 1.0, "distribucion": 1.0, "compactacion": 0.5}`.
- **R7** — El sistema DEBERÁ exponer CRUD completo para `config_generacion`:
  `crear`, `get`, `listar`, `actualizar`, `eliminar` y `cambiar_estado`.
  `cambiar_estado` DEBERÁ validar transiciones válidas:
  `borrador → generado`, `generado → aplicado`, `generado → borrador` (re-generar).
  No deberá permitir volver de `aplicado` a otro estado.
- **R8** — Un `config_generacion` en estado `borrador` DEBERÁ poder duplicarse
  (`duplicar_config(id)`) generando una copia con nombre `"<nombre> (copia)"` en
  estado `borrador`. Útil para experimentar con distintos parámetros.

## Modelos de dominio

- **R9** — El sistema DEBERÁ exponer `DisponibilidadDocente(BaseModel)` y
  `ConfigGeneracion(BaseModel)` en `src/domain/models/infraestructura.py` con
  todos los validadores necesarios. DTOs de creación: `NuevaDisponibilidadDTO` y
  `NuevaConfigGeneracionDTO`. Actualizar `__all__`.
- **R10** — `ConfigGeneracion.pesos` DEBERÁ deserializarse a un objeto tipado
  `PesosGeneracion(BaseModel)` con campos `huecos: float = 1.0`,
  `distribucion: float = 1.0`, `compactacion: float = 0.5`, valores en [0.0, 2.0].

## Puerto y repositorio

- **R11** — `IInfraestructuraRepository` DEBERÁ declarar los métodos abstractos
  de disponibilidad (R3–R4) y de config_generacion (R7–R8). `FakeInfraRepo` en
  los tests existentes DEBERÁ recibir stubs para no romper (patrón paso_15a).
- **R12** — `SqliteInfraestructuraRepository` DEBERÁ implementarlos. La operación
  `upsert` de disponibilidad DEBERÁ usar `INSERT OR REPLACE`.

## Servicio fachada

- **R13** — `InfraestructuraService` DEBERÁ exponer fachada de tipos simples para:
  `es_disponible_docente(usuario_id, dia, franja_orden) -> bool`,
  `bloquear_franjas_docente(usuario_id, slots: list[dict])`,
  `limpiar_disponibilidad_docente(usuario_id)`,
  `listar_disponibilidad_docente(usuario_id)`,
  `crear_config_generacion(nombre, periodo_id, anio_id, plantilla_id,
  grupos=None, pesos=None) -> ConfigGeneracion`,
  `listar_configs`, `get_config`, `actualizar_config`, `eliminar_config`,
  `cambiar_estado_config`, `duplicar_config`.

## Seed

- **R14** — `seed_test` DEBERÁ crear al menos una `config_generacion` en estado
  `borrador` asociada al periodo y plantilla del seed. No es necesario poblar
  `disponibilidad_docente` en el seed (por defecto todo disponible).

## Tests

- **R15** — Unit (`test_disponibilidad_config_model.py`): validadores de
  `DisponibilidadDocente`, `ConfigGeneracion`, `PesosGeneracion`, transiciones
  de estado, DTOs.
- **R16** — Integración (`test_disponibilidad_config_repo.py`): upsert/limpiar
  disponibilidad, `es_disponible` para slot registrado vs no registrado; CRUD
  completo de config_generacion; exclusividad de transiciones de estado;
  duplicar_config.
- **R17** — `python init.py` DEBERÁ quedar verde; suite sin regresiones
  (baseline: 832 passed).

## Fuera de alcance

- Motor de generación (paso_15c).
- UI de configuración (paso_15g).
- Columna `color` en `areas_conocimiento` (paso_15e).
- Modificaciones a la tabla `horarios` o `escenarios_horario`.
