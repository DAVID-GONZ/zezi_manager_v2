# Tareas: datos_02_model_config_base

> SCOPE — únicos archivos que pueden crearse o editarse:
> `src/domain/models/base.py` (nuevo) y los 21 módulos de `src/domain/models/`,
> `tests/unit/domain/test_model_config.py` (nuevo).
>
> Fuera de scope: `src/services/`, `src/infrastructure/`, `src/interface/`.
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**
>
> Excepción acotada de T3: los 13 fallos medidos viven en `tests/unit/services/`.
> Corregirlos exige salir del scope → **T3 se detiene y reporta**; el leader decide
> si amplía el scope o abre un paso propio.

Puerta obligatoria tras **cada** tarea:

```
.venv/Scripts/python.exe -m ruff check . --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```

Debe salir en 0. Prohibido `ruff format` y `ruff check --fix` masivos.

---

## T1 — Crear la base común  [ ]

**Artefacto:** `src/domain/models/base.py` con `ZeciModel`, `EntidadDominio` y `DTODominio`
según D1 y D2. Ningún otro módulo se modifica todavía.

Requisitos: R1, R2, R4, R5, R11, R14, R16.

**Verificación:**
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from src.domain.models.base import ZeciModel, EntidadDominio, DTODominio; print(ZeciModel.model_config); print(EntidadDominio.model_config); print(DTODominio.model_config)"
```
Debe mostrar `from_attributes=True`, `str_strip_whitespace=True`, `validate_assignment=True`
en las tres; `extra='ignore'` solo en `EntidadDominio`; `extra='forbid'` solo en
`DTODominio`; y `use_enum_values` ausente o `False` en todas.

---

## T2 — Medir la hidratación real antes de tocar los modelos  [ ]

**Por qué existe:** la suite de integración está roja por una causa ajena (30 fallos de
firmas `tenant_02`/`tenant_03`), así que **no demuestra** que las entidades se hidraten
bien desde un `SELECT *`. Esta tarea produce esa evidencia por su cuenta.

**Artefacto:** un test en `tests/unit/domain/test_model_config.py` que, sobre una base
sembrada en memoria, ejecute `SELECT *` de cada tabla con entidad asociada y construya la
entidad correspondiente, comprobando que ninguna construcción falla.

Requisitos: R9.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_model_config.py -q
```

**Si alguna entidad falla al hidratarse**, anotar la tabla, la columna sobrante y el
modelo, y **reportar al leader antes de continuar**: significa que `extra="ignore"` no
basta para ese caso y el diseño debe revisarse.

---

## T3 — Sanear las construcciones con campos fantasma  [ ]

**Artefacto:** los 13 puntos que construyen modelos con campos no declarados, corregidos.
Medidos: `Actividad(asignacion_id=…, periodo_id=…)` y `ResumenAsistenciaDTO(…)` en
`tests/unit/services/test_evaluacion_service.py` y `test_asistencia_service.py`.

Requisitos: R19, R8.

**Decidir y reportar, no improvisar:** para cada campo fantasma hay dos lecturas —
o el modelo debería declararlo, o quien construye no debería pasarlo. `Actividad` se
relaciona con su asignación y su periodo **a través de `categoria_id`**; verifícalo antes
de decidir.

**Esta tarea sale del SCOPE** (los ficheros están en `tests/unit/services/`).
**PARAR y reportar al leader** con la lista de los 13 puntos y la corrección propuesta
para cada uno. No editarlos sin autorización.

**Verificación una vez autorizada:**
```
.venv/Scripts/python.exe -m pytest tests/unit/services/test_evaluacion_service.py tests/unit/services/test_asistencia_service.py -q
```

---

## T4 — Derivar los modelos de entidad  [ ]

**Artefacto:** los modelos que representan una entidad persistida derivan de
`EntidadDominio`. Un módulo por tanda; tras cada módulo, puerta de ruff y suite rápida.

Orden sugerido, de menor a mayor superficie: `preferencia_institucion`, `piar`, `busqueda`,
`nivelacion`, `asignacion`, `plan_mejoramiento`, `acudiente`, `alerta`, `periodo`,
`institucion`, `auditoria`, `asistencia`, `usuario`, `estudiante`, `cierre`, `habilitacion`,
`configuracion`, `evaluacion`, `convivencia`, `infraestructura`.

Requisitos: R1, R2, R9.

**Verificación tras cada módulo:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
```
Debe mantenerse en 1868 passed (o el número vigente tras T3), sin regresiones.

---

## T5 — Derivar los DTO  [ ]

**Artefacto:** los modelos de transporte derivan de `DTODominio` (`extra="forbid"`).
Incluye `src/domain/models/dtos.py` y los `*DTO` repartidos por los demás módulos.

Requisitos: R4, R7, R8.

**Criterio de clasificación:** es DTO todo modelo que no se hidrata desde una fila de
tabla — entradas de servicio, filtros, resultados de operación y vistas de lectura
compuestas por `JOIN`. Ante la duda, comprobar si algún repositorio lo construye con
`(**dict(row))`: si lo hace, es entidad.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
.venv/Scripts/python.exe -m pytest -q -m "integration or slow"
```
La segunda debe seguir en **30 failed / 246 passed**: ni uno más. Cualquier fallo nuevo
es una regresión de este paso.

---

## T6 — Retirar los validadores de solo espacios  [ ]

**Artefacto:** los `field_validator(mode="before")` cuyo cuerpo se limita a `.strip()`
eliminados; los que además validan contenido, longitud o formato, conservados.

Requisitos: R12, R13.

**Regla que no se puede saltar:** `str_strip_whitespace` **no** convierte `""` en `None`.
Todo validador que haga esa conversión se conserva, aunque también recorte.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from src.domain.models.estudiante import Estudiante; e=Estudiante(numero_documento='  123  ', nombre='  ana  ', apellido='  gil  '); print(repr(e.numero_documento), repr(e.nombre), repr(e.apellido))"
```
Los tres valores deben salir recortados y con la normalización propia del modelo intacta.

---

## T7 — Test estructural de la base  [ ]

**Artefacto:** en `tests/unit/domain/test_model_config.py`, un test que recorra
`src/domain/models/`, localice toda clase derivada de `BaseModel` y falle si alguna no
deriva de `ZeciModel`, nombrando módulo y clase. Lista de excepciones explícita y vacía.

Requisitos: R3.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_model_config.py -q
```
Comprobar además que **detecta** el fallo: derivar temporalmente un modelo de `BaseModel`,
ver el test en rojo, y revertir. Un test que no se ha visto fallar no prueba nada.

---

## T8 — Verificación de no regresión y cierre  [ ]

**Artefacto:** `progress/impl_datos_02.md` con lo aplicado, los validadores retirados, la
clasificación entidad/DTO y cualquier decisión que se apartara del diseño.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. El paso no se declara `done` sin esto (`CLAUDE.md`).

Comprobar también R18: que la serialización no cambió de forma inadvertida.
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from src.domain.models.estudiante import Estudiante; print(sorted(Estudiante(numero_documento='1', nombre='a', apellido='b').model_dump()))"
```
Las claves deben ser las mismas que antes del paso; este paso **no** añade campos
calculados a la serialización — eso es `datos_03`.
