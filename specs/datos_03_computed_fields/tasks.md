# Tareas: datos_03_computed_fields

> **Requisito de orden:** este paso va después de `datos_02_model_config_base`
> (ver design D4). No iniciarlo antes de que `datos_02` esté `done`.
>
> SCOPE — únicos archivos que pueden editarse:
> `src/domain/models/{acudiente,alerta,asignacion,asistencia,auditoria,cierre,`
> `configuracion,convivencia,dtos,estudiante,evaluacion,habilitacion,infraestructura,`
> `institucion,nivelacion,periodo}.py` y `tests/unit/domain/test_computed_fields.py`.
>
> `piar.py` y `usuario.py` contienen propiedades clasificadas pero **no están en el
> `destino_v2` del paso**. Al llegar a ellos → **PARAR y reportar al leader** para que
> amplíe el scope. No editarlos por iniciativa propia.

Puerta obligatoria tras **cada** tarea:

```
.venv/Scripts/python.exe -m ruff check . --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```

---

## T1 — Fijar el inventario y verificar el supuesto de acceso  [ ]

**Artefacto:** `tests/unit/domain/test_computed_fields.py` con:

1. El inventario completo de las 123 propiedades clasificadas en A / B / C, como dato
   del test (no como comentario), de forma que la clasificación quede versionada.
2. Un test que compruebe que **`@computed_field` preserva el acceso sin paréntesis**
   exigido por `docs/conventions.md §8`, sobre un modelo de prueba mínimo.

Requisitos: R7, R8, R9.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_computed_fields.py -q
```

**Si el punto 2 falla**, el diseño D1 es incorrecto → **PARAR y reportar**. Todo el paso
depende de ese supuesto.

---

## T2 — Medir el coste de serialización  [ ]

**Artefacto:** un test que serialice un lote de 500 modelos con valores derivados y
compruebe que el tiempo no se degrada de forma apreciable frente al mismo lote sin ellos.

Requisitos: R10, R11.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_computed_fields.py -q -k coste
```

Comprobar además, por inspección, que ninguna propiedad del grupo A o C importa
repositorios ni `Container`. Si alguna lo hace → no puede convertirse: **reportar**.

---

## T3 — Convertir el grupo A, módulo a módulo  [ ]

**Artefacto:** las 88 propiedades de negocio decoradas con `@computed_field`, conservando
el `@property` debajo y su anotación de tipo de retorno (R4).

Orden sugerido: `nivelacion`, `asignacion`, `dtos`, `acudiente`, `auditoria`, `alerta`,
`configuracion`, `cierre`, `asistencia`, `convivencia`, `habilitacion`, `evaluacion`,
`estudiante`, `infraestructura`.

Requisitos: R1, R2, R3, R4.

**Verificación tras cada módulo:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
```
Sin regresiones respecto al total vigente.

**Comprobación puntual de R3** (mismo valor como atributo y en el volcado):
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from src.domain.models.estudiante import Estudiante; e=Estudiante(numero_documento='1',nombre='ana',apellido='gil'); d=e.model_dump(); print(e.es_activo, d['es_activo'], e.nombre_completo == d['nombre_completo'])"
```

---

## T4 — Convertir el grupo C con su cautela  [ ]

**Artefacto:** las 9 propiedades dependientes de la fecha actual decoradas con
`@computed_field`, y un test por cada una que **congele la fecha** y verifique el
resultado esperado.

Requisitos: R12, R13, R14.

Las nueve: `Alerta.dias_pendiente`, `Estudiante.edad`, `PlanMejoramiento.seguimiento_vencido`,
`PlanMejoramiento.dias_activo`, `Periodo.en_curso`, `HitoPeriodo.esta_vencido`,
`HitoPeriodo.dias_restantes`, `PIAR.revision_vencida`, `PIAR.dias_para_revision`.

`PIAR.*` está fuera del scope → **PARAR y reportar** al llegar.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_computed_fields.py -q
```

Cada test debe fallar si se altera la lógica de la propiedad: comprobarlo rompiéndola a
propósito una vez y revirtiendo. Un test que no se ha visto fallar no prueba nada.

---

## T5 — Confirmar que el grupo B no viaja  [ ]

**Artefacto:** un test que compruebe que ninguna de las 26 propiedades de presentación
aparece en `model_dump()`, y que todas siguen accesibles como atributo.

Requisitos: R5, R6.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_computed_fields.py -q -k presentacion
```

---

## T6 — Verificar que los derivados no son de entrada  [ ]

**Artefacto:** un test que compruebe que pasar un valor derivado al constructor de un DTO
se rechaza, y que en una entidad no sobrescribe el valor calculado.

Requisitos: R17. **Depende de `extra="forbid"` en los DTO, que aporta `datos_02`.**

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_computed_fields.py -q -k entrada
```

---

## T7 — No regresión de consumidores  [ ]

**Artefacto:** confirmación de que ningún consumidor existente se rompe (R15, R16).

Los presenters, las páginas y los exportadores leen estas propiedades como atributo. Al
incorporarse al volcado, cambia además lo que reciben los sitios que hacen `model_dump()`
para construir tablas o exportar: **una fila puede pasar a tener columnas nuevas**.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
.venv/Scripts/python.exe -m pytest -q -m "integration or slow"
```
La segunda debe quedar en el mismo recuento de fallos preexistentes que antes del paso —
comprobarlo **antes** de empezar para tener la línea base, según `CLAUDE.md`.

Revisar en particular los exportadores a Excel y los constructores de `ag-grid`, que
iteran sobre las claves del volcado.

---

## T8 — Cierre  [ ]

**Artefacto:** `progress/impl_datos_03.md` con el recuento final por grupo, las
reclasificaciones respecto al diseño y las propiedades que quedaron fuera por scope.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. Sin esto el paso no se declara `done` (`CLAUDE.md`).
