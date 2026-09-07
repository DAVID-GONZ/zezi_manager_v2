# Diseño: datos_02_model_config_base

## Punto de partida medido

Introspección sobre los 180 modelos de `src/domain/models/` (24 módulos, 9.684 líneas):

| Opción de `model_config` | Modelos que la declaran |
|---|---|
| `from_attributes` | 0 |
| `extra="forbid"` | 0 |
| `frozen` | 0 |
| `str_strip_whitespace` | 0 |
| `validate_assignment` | 0 |
| `use_enum_values` | 0 |

**Ninguno de los 180 modelos declara `model_config`.** Hay 275 validadores, de los cuales
135 son `field_validator(mode="before")` y una parte sustancial solo hace `.strip()` y
`"" → None`.

## Evidencia experimental

No se dio por supuesto el impacto de las opciones de riesgo: se midió forzándolas sobre
los 180 modelos mediante un plugin de pytest y ejecutando la suite.

### `extra="forbid"` — viable

| Suite | Sin forzar | Con `extra="forbid"` | Delta |
|---|---|---|---|
| Rápida (la que ejecuta la puerta) | 1868 passed | 1855 passed, **13 failed** | **+13** |
| `-m "integration or slow"` | 30 failed, 246 passed | 30 failed, 246 passed | **0** |

Los 13 fallos de la suite rápida tienen **una sola causa**: los tests construyen
`Actividad(asignacion_id=3, periodo_id=5, ...)` y `ResumenAsistenciaDTO(...)` con campos
que esos modelos no declaran.

```
Actividad.model_fields = [id, nombre, descripcion, fecha, valor_maximo, estado, categoria_id]
                          # no existen asignacion_id ni periodo_id
```

Hoy esos campos se descartan en silencio. **`extra="forbid"` no rompe nada: destapa 13
construcciones con campos fantasma**, que es exactamente el defecto que la opción existe
para cazar (R19).

### Límite honesto de esa evidencia

Los 30 fallos de `-m "integration or slow"` son **preexistentes y ajenos a este paso**:
son llamadas a repositorios con firmas anteriores al `institucion_id` obligatorio que
introdujeron `tenant_02`/`tenant_03`.

```
TypeError: SqliteConvivenciaRepository.listar_categorias() missing 1 required positional argument
TypeError: SqliteEstudianteRepository.get_by_documento() missing 1 required positional argument
ValidationError: 1 validation error for RegistroComportamiento
```

Consecuencia para este diseño: **la ruta `Modelo(**dict(row))` sobre un `SELECT *` real no
queda demostrada por la suite**, porque esos tests fallan antes de llegar a construir el
modelo. Hay 25 puntos con ese patrón en los repositorios. Por eso T2 no confía en la
suite y mide la hidratación directamente contra la base sembrada.

### `frozen` — se descarta en este paso

Mutaciones de modelos ya construidos localizadas en el código de producción:

```
src/services/evaluacion_service.py:492    resultado.definitiva = definitiva
src/services/evaluacion_service.py:493    resultado.promedio_ajustado = promedio_ajustado
src/services/generador_horario_service.py:1306  metricas.costo_inicial = costo_inicial
src/services/generador_horario_service.py:1374  resultado.valido = False
src/services/generador_horario_service.py:1396  resultado.escenario_id = escenario_id
```

Todas recaen sobre DTO de resultado, no sobre entidades. No se encontró ninguna
asignación `entidad.id = ...` tras un INSERT: los repositorios reconstruyen el modelo con
`id=cursor.lastrowid`.

Aun así `frozen=True` **no entra en este paso**. `validate_assignment=True` cubre la
invariante que importa (R14, R15) sin obligar a reescribir esos cinco puntos, y deja la
inmutabilidad como decisión separada y medible. Congelar entidades es un cambio de
contrato de la capa de dominio; merece su propio paso, no un efecto colateral de este.

## Decisiones

### D1 — Dos bases, no una

```
src/domain/models/base.py

    ZeciModel(BaseModel)          # base común: from_attributes, str_strip_whitespace,
                                  # validate_assignment
      └── EntidadDominio          # + extra="ignore"  → se hidrata desde filas
      └── DTODominio              # + extra="forbid"  → recibe datos externos
```

La distinción responde a R4 y resuelve la tensión entre R7 y R9: un DTO que entra por la
API debe rechazar lo que no reconoce; una entidad que se hidrata desde un `SELECT *` debe
tolerar columnas que aún no representa (`institucion_id` en tablas donde el modelo no lo
declara, marcas de tiempo, columnas añadidas por trabajo posterior).

`extra="ignore"` en las entidades es **explícito y justificado** (R10), no una omisión.
Cuando `backend_07_repos_migracion` sustituya los `SELECT *` por columnas nombradas, las
entidades podrán endurecerse a `forbid` en su propio paso.

### D2 — Opciones de la base común

| Opción | Valor | Requisito | Justificación |
|---|---|---|---|
| `from_attributes` | `True` | R5, R6 | Sin ella `model_validate(objeto_orm)` no funciona; es el requisito de entrada de `backend_07` |
| `str_strip_whitespace` | `True` | R11, R13 | Retira la duplicación de los validadores de solo `.strip()` |
| `validate_assignment` | `True` | R14, R15 | Las invariantes dejan de valer solo en la construcción |
| `extra` | por subclase | R7, R9 | Ver D1 |
| `use_enum_values` | **`False`** | R16 | Activarla convertiría los miembros en `str` y rompería las 123 propiedades y las comparaciones por identidad de miembro |
| `frozen` | **no se declara** | — | Ver evidencia; queda para un paso propio |

### D3 — Retirada de validadores de espacios

Solo se retira un `field_validator` cuando su cuerpo **se limita** a normalizar espacios
y a convertir la cadena vacía en `None`. Si además valida contenido, longitud o formato,
se conserva íntegro y solo se le quita la línea de `.strip()` redundante (R12).

`str_strip_whitespace` actúa **antes** que los validadores `mode="before"`, así que los
que se conservan reciben el valor ya recortado y su lógica no cambia.

Caso que exige cuidado: los validadores que hacen `"" → None`. `str_strip_whitespace` no
convierte la cadena vacía en `None`; esa parte **debe conservarse siempre**.

### D4 — Test estructural (R3)

`tests/unit/domain/test_model_config.py` recorre `src/domain/models/`, localiza toda clase
que derive de `BaseModel` y falla si alguna no deriva de `ZeciModel`, nombrando el módulo
y la clase. Una lista de excepciones explícitas, vacía al cerrar el paso, permite
documentar cualquier caso legítimo sin desactivar la regla.

## Interacción con `datos_01`

`src/domain/exceptions.py` ya define `ReglaDeNegocioError(ZeciError, ValueError)`. La
herencia de `ValueError` es la que permite que Pydantic siga capturando las excepciones
que lanzan los `field_validator` y las envuelva en `ValidationError`. Este paso **no
altera** esa relación: los validadores siguen pudiendo lanzar cualquiera de las dos.

## Alternativa descartada

**Una sola base con `extra="forbid"` para los 180 modelos, corrigiendo los 25 puntos
`Modelo(**dict(row))` para que seleccionen columnas explícitas.**

Es el destino correcto y produce un sistema más estricto. Se descarta aquí porque
reescribir las consultas de 21 repositorios es precisamente el contenido de
`backend_07_repos_migracion`: hacerlo ahora duplicaría ese trabajo sobre SQL que va a
desaparecer, y convertiría un paso de dominio acotado en una reescritura de la capa de
infraestructura. La separación en dos bases permite que los DTO —los que la API expondrá—
obtengan hoy la garantía estricta, y deja a las entidades endurecerse cuando sus
consultas dejen de ser `SELECT *`.
