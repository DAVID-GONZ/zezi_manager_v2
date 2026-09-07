# Tareas: datos_04_decimal_notas

> **Requisito de orden:** después de `datos_02_model_config_base` y antes de
> `backend_04_metadata_schema` (ver design).
>
> SCOPE — únicos archivos que pueden crearse o editarse:
> `src/domain/models/{evaluacion,cierre,habilitacion,nivelacion,plan_mejoramiento,`
> `configuracion,convivencia}.py`,
> `src/services/{evaluacion,cierre,habilitacion,nivelacion,plan_mejoramiento,informe}_service.py`,
> `src/infrastructure/db/repositories/sqlite_{evaluacion,cierre,habilitacion,nivelacion,plan_mejoramiento}_repo.py`,
> `tests/unit/domain/test_decimal_notas.py`.
>
> El módulo de tipo y cuantización (T1) vive en `src/domain/models/` para no salir del
> scope. Si hiciera falta ubicarlo en otro sitio → **PARAR y reportar al leader.**
>
> `src/domain/models/periodo.py` contiene `peso_porcentual`, que el diseño clasifica como
> peso de ponderación, pero **no está en el `destino_v2`** → al llegar, **PARAR y
> reportar**.

Puerta obligatoria tras **cada** tarea:

```
.venv/Scripts/python.exe -m ruff check . --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```

---

## T1 — Demostrar el ciclo de persistencia antes de tocar los modelos  [ ]

**Por qué primero:** todo el diseño descansa en que un decimal de 2 dígitos sobrevive
intacto el ciclo `Decimal → float → REAL → float → str → Decimal`. Si no fuera cierto, el
diseño es inválido y no tiene sentido convertir nada.

**Artefacto:** `tests/unit/domain/test_decimal_notas.py` con:

1. Ida y vuelta contra una base SQLite en memoria con columna `REAL`, sobre un barrido de
   todos los valores de 0.00 a 100.00 en pasos de 0.01, comprobando identidad exacta
   (R18, R20).
2. Prueba de que `Decimal(str(f))` reconstruye el valor y `Decimal(f)` no (R19).
3. Prueba de que pasar `Decimal` directo a `sqlite3` lanza `ProgrammingError` — el motivo
   de que exista la conversión de frontera (R17).

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_decimal_notas.py -q
```

**Si el barrido del punto 1 falla en algún valor → PARAR y reportar.**

---

## T2 — Tipo y cuantización centralizados  [ ]

**Artefacto:** el módulo con el tipo anotado de nota (2 decimales) y de peso
(4 decimales), y la operación de cuantización con `ROUND_HALF_UP`, aceptando `str`,
`int`, `float` y `Decimal`.

Requisitos: R1, R2, R3, R4, R5, R6, R7.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_decimal_notas.py -q -k cuantiza
```

Casos que deben estar cubiertos: `"3.005"`, `3.005`, `3`, `Decimal("3.005")` producen
todos el mismo resultado; `2.995 → 3.00` (mitad hacia arriba, no hacia el par).

---

## T3 — Reproducir el fallo actual como test en rojo  [ ]

**Artefacto:** un test que fije el contraejemplo del diseño —pesos `[0.7, 0.29, 0.01]`,
notas `3.0`, umbral `3.0`— y exija que el estudiante **apruebe**.

Requisitos: R10, R11.

Con el cálculo actual en `float` este test **debe fallar** (`2.9999999999999996 < 3.0`).
Ejecutarlo y **ver el rojo** antes de seguir: es la prueba de que el paso arregla algo
real y no solo cambia tipos.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_decimal_notas.py -q -k umbral
```

---

## T4 — Convertir los modelos  [ ]

**Artefacto:** los campos de las cuatro familias del diseño anotados con el tipo decimal
correspondiente, en `evaluacion`, `cierre`, `habilitacion`, `nivelacion`,
`plan_mejoramiento`, `configuracion` y `convivencia`.

Requisitos: R1, R2, R3, R5, R6.

Un módulo por tanda, con puerta de ruff y suite rápida tras cada uno.

**No convertir** (R25): estadísticos agregados, porcentajes de progreso y pesos
heurísticos del generador de horarios.

**Verificación tras cada módulo:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
```

---

## T5 — Cálculo en precisión decimal  [ ]

**Artefacto:** `CalculadorNotas.calcular_definitiva` y `calcular_promedio_ajustado`
acumulan en decimal y cuantizan una sola vez al final;
`pesos_validos` compara exacto contra `Decimal("1")` y **pierde el margen `1.001`**.

Requisitos: R8, R9, R10, R11, R12, R13.

Al pasar por ahí, retirar el diccionario por comprensión muerto de
`evaluacion.py:464` y dejar constancia en el informe.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_decimal_notas.py -q
.venv/Scripts/python.exe -m pytest tests/unit/services/test_evaluacion_service.py -q
```
El test de T3 debe pasar de rojo a verde. Ese cambio es el criterio de éxito de la tarea.

---

## T6 — Propiedades algebraicas del promedio ponderado  [ ]

**Artefacto:** tests que verifiquen, sobre combinaciones generadas de pesos que sumen la
unidad:

- la definitiva queda entre la menor y la mayor de las notas que la componen (R15);
- subir una nota sin variar las demás nunca baja la definitiva (R16);
- con todas las notas iguales al umbral, la definitiva es exactamente el umbral (R10).

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_decimal_notas.py -q -k propiedades
```

Incluir explícitamente los pesos `[0.7, 0.29, 0.01]`, `[0.05, 0.15, 0.8]` y
`[0.33, 0.33, 0.34]`, que son los que exhiben el error en `float`.

---

## T7 — Frontera de persistencia en los repositorios  [ ]

**Artefacto:** los cinco repositorios del scope convierten a `float` al escribir (sobre
valor ya cuantizado) y reconstruyen con `Decimal(str(...))` al leer.

Requisitos: R17, R18, R19, R20.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "integration or slow"
```

**Línea base obligatoria:** ejecutar este mismo comando **antes** de la tarea y anotar el
recuento. Hay 30 fallos preexistentes por firmas de `tenant_02`/`tenant_03`, ajenos a este
paso. El criterio es **no aumentar** ese número, no que salga verde (`CLAUDE.md`: comparar
antes de culpar a un cambio).

---

## T8 — Clasificación de desempeño en los extremos  [ ]

**Artefacto:** tests que verifiquen que una nota situada exactamente en un extremo de un
rango de desempeño se clasifica de forma determinista y siempre en el mismo nivel (R14).

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_decimal_notas.py -q -k desempeno
```

Cubrir los cuatro límites de `niveles_desempeno` sembrados, y el caso de una nota que cae
justo en la frontera entre dos niveles.

---

## T9 — Informes, exportadores y pandas  [ ]

**Artefacto:** `informe_service` y los exportadores entregan valores numéricos (R21),
conservan el valor cuantizado (R24) y no reconvierten a `float` ningún valor que vuelva a
compararse o acumularse (R23).

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/services/test_informe_service.py -q
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
```

Punto de mayor riesgo del paso: una columna de `Decimal` en un DataFrame queda como
`dtype=object` y cualquier `.mean()` o `.sum()` sobre ella falla o vuelve a `float`.
Revisar toda agregación de pandas sobre columnas de nota.

---

## T10 — Cierre  [ ]

**Artefacto:** `progress/impl_datos_04.md` con los campos convertidos, los descartados con
su motivo, el resultado del barrido de T1 y las agregaciones de pandas que hubo que tocar.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. Sin esto el paso no se declara `done` (`CLAUDE.md`).
