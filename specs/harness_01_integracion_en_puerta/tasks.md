# Tareas: harness_01_integracion_en_puerta

> ⚠ **Depende de `datos_08_fecha_zona_horaria`.** No iniciar T4 (encadenar la puerta)
> antes de que `datos_08` esté `done`: 5 de los 30 fallos son de aquel defecto y la puerta
> no puede quedar verde sin él. T1–T3 sí pueden avanzar en paralelo.
>
> SCOPE — únicos archivos que pueden editarse:
> `tests/integration/test_repositories.py`,
> `tests/integration/test_convivencia_categorias.py`,
> `tests/integration/test_convivencia_14_promocion_comportamiento.py`,
> `tests/integration/test_convivencia_35_entradas_seguimiento.py`,
> `tests/integration/test_disponibilidad_config_repo.py`,
> `tests/integration/test_franjas_repo.py`,
> `scripts/init.py`, `scripts/run_tests.py`.
>
> **No se toca `src/`.** Si alguna prueba solo pudiera arreglarse cambiando código de
> producción, eso significa que el fallo **no** es de firma → **PARAR y reportar al
> leader**: es un defecto real y merece su propio paso.

Puerta obligatoria tras **cada** tarea:

```
.venv/Scripts/python.exe -m ruff check . --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```

---

## T1 — Línea base y clasificación  [ ]

**Artefacto:** `progress/impl_harness_01.md` con el recuento exacto de partida, cada fallo
clasificado en «firma desactualizada» o «defecto real», y el inventario de repositorios
sin ninguna prueba de integración.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "integration or slow" 2>&1 | tail -40
```

Punto de partida a fecha 2026-09-06: **30 failed, 246 passed, 1 skipped**. Si el recuento
de partida difiere, **anotarlo y reportar** antes de seguir: significa que algo cambió
desde la auditoría y la clasificación debe rehacerse.

`CLAUDE.md`: comparar contra `HEAD` antes de atribuir un fallo a un cambio.

---

## T2 — Actualizar las 25 llamadas con firma desactualizada  [ ]

**Artefacto:** las llamadas a los 14 métodos pasan el `institucion_id` que sus interfaces
exigen.

Requisitos: R1, R2, R3, R14, R15.

Un fichero por tanda, de menor a mayor: `test_convivencia_14_promocion_comportamiento.py`
(2), `test_disponibilidad_config_repo.py` (3), `test_franjas_repo.py` (4),
`test_convivencia_categorias.py` (5), `test_convivencia_35_entradas_seguimiento.py` (5),
`test_repositories.py` (11).

**Regla que no se puede saltar (D1):** se pasa el identificador de la institución sembrada,
**no `"*"`**. `"*"` hace pasar la prueba sin verificar el aislamiento que `tenant_02`–`04`
construyeron. Solo se admite `"*"` si la prueba verifica deliberadamente el comportamiento
de administrador, y entonces su nombre debe decirlo.

**Verificación tras cada fichero:**
```
.venv/Scripts/python.exe -m pytest tests/integration/<fichero> -q
```

Al terminar T2 el recuento debe ser **5 failed** (los de zona horaria) si `datos_08` aún
no está hecho, o **0** si ya lo está.

---

## T3 — Cobertura de hidratación de los repositorios sin prueba  [ ]

**Artefacto:** por cada repositorio del inventario de T1 sin cobertura, una prueba que
recupere una fila real y construya su entidad.

Requisitos: R4, R5, R6.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "integration"
```

Esta es la ruta `SELECT * → Modelo(**dict(row))` de los 25 puntos de los repositorios, que
hoy no verifica nadie. Si alguna entidad **no** se construye desde su fila real, es un
defecto de producción: **PARAR y reportar**, no ajustar la prueba para que pase (R15).

---

## T4 — Encadenar integración a la puerta  [ ] ⚠ requiere `datos_08` done

**Artefacto:** `scripts/init.py` ejecuta `rapido` e `integration` como bloques separados,
cada uno con su encabezado y su resultado, y aborta si cualquiera falla.

Requisitos: R7, R8, R10.

`scripts/run_tests.py` **no cambia su modo `rapido`** (R9, D2): lo que gana una familia es
la puerta, no la herramienta del día a día.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE, con ambos bloques visibles y diferenciados en la salida.

Comprobar que **la puerta detiene un fallo de integración**: romper una prueba de
integración a propósito, ver `init.py` en rojo atribuyendo el fallo al bloque correcto, y
revertir. Una puerta que no se ha visto fallar no prueba nada — es exactamente el defecto
que este paso corrige.

Medir el tiempo total (R11). Referencia: ~18 s + ~27 s ≈ 45 s. Si se disparara muy por
encima, reportar antes de dar por buena la tarea.

---

## T5 — Que no vuelva a quedar una familia fuera  [ ]

**Artefacto:** comprobación que falle si `scripts/init.py` deja de ejecutar alguna de las
familias declaradas.

Requisitos: R12, R13.

Debe dejar constancia explícita de que `e2e` y `browser` siguen **deliberadamente** fuera
de la puerta —`e2e` exige el entrypoint `tests/e2e/e2e_app.py`, `browser` exige
`playwright install`—, de modo que sean una decisión registrada y no un olvido como lo fue
`integration`.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
Comprobar que **detecta**: retirar `integration` de la puerta, ver el rojo, revertir.

---

## T6 — Cierre  [ ]

**Artefacto:** `progress/impl_harness_01.md` completado con las 25 llamadas actualizadas,
las pruebas de hidratación añadidas, los defectos reales encontrados en T3 (si los hubo) y
el tiempo final de la puerta.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
.venv/Scripts/python.exe -m pytest -q -m "integration or slow"
```
La primera, TODO VERDE. La segunda, **0 failed**.

Sin ambas cosas el paso no se declara `done` (`CLAUDE.md`).
