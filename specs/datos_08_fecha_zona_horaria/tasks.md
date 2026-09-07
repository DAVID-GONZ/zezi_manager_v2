# Tareas: datos_08_fecha_zona_horaria

> ⚠ **Este paso toca `src/infrastructure/db/schema.py`.** `CLAUDE.md` exige puerta de
> aprobación de David para cambiar el esquema. No iniciar T5 sin ella.
>
> SCOPE — únicos archivos que pueden crearse o editarse:
> `src/infrastructure/db/schema.py`,
> `src/infrastructure/db/repositories/sqlite_{infraestructura,periodo}_repo.py`,
> `src/domain/models/{asistencia,cierre,convivencia,estudiante,evaluacion}.py`,
> `config.py`, `tests/unit/domain/test_fecha_zona_horaria.py`.
>
> El módulo del origen único (T2) vive en `src/domain/models/` para no salir del scope.
> Si el implementer considera que pertenece a otro sitio → **PARAR y reportar al leader.**

Puerta obligatoria tras **cada** tarea:

```
.venv/Scripts/python.exe -m ruff check . --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```

---

## T1 — Reproducir el defecto de forma independiente de la hora  [ ]

**Por qué primero:** el defecto solo se manifiesta entre las 19:00 y las 24:00 hora local.
Un test que dependa de cuándo se ejecute no sirve de criterio.

**Artefacto:** `tests/unit/domain/test_fecha_zona_horaria.py` con un test que fije el
instante a las 19:50 hora de Colombia y demuestre la discrepancia entre la fecha que
produce el almacenamiento y la que produce el dominio.

Requisitos: R13, R14.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_fecha_zona_horaria.py -q
```

Este test debe estar **en rojo** al terminar la tarea, y debe seguir en rojo a cualquier
hora del día. Si pasa en verde, no está reproduciendo el defecto.

---

## T2 — Origen único del instante actual  [ ]

**Artefacto:** el módulo con la función que responde «hoy» y «ahora» en la zona de
referencia, resuelta desde configuración, y sustituible al verificar.

Requisitos: R1, R2, R3, R13.

`zoneinfo` de la biblioteca estándar; **no** añadir dependencia.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_fecha_zona_horaria.py -q -k origen
```
Cubrir: que la zona por omisión es `America/Bogota`; que la configuración la sobreescribe;
y que a las 19:50 hora local devuelve el día en curso, no el siguiente.

---

## T3 — Zona horaria en configuración  [ ]

**Artefacto:** `config.py` expone la zona de referencia, con `America/Bogota` por omisión.

Requisitos: R3.

**Verificación:**
```
.venv/Scripts/python.exe -c "import config; print(config.__dict__.get('ZONA_HORARIA', 'NO DEFINIDA'))"
```

**No** incrustar el desfase horario como número. Una zona nombrada, no `-5`: Colombia no
aplica horario de verano hoy, pero un desfase fijo es incorrecto para cualquier otra zona
que sí lo aplique.

---

## T4 — Validadores y valores por omisión al origen único  [ ]

**Artefacto:** los validadores `> date.today()` de `asistencia.py`, `cierre.py` y
`convivencia.py`, y los `default_factory=date.today` de `estudiante.py` y `evaluacion.py`,
pasan por el origen único.

Requisitos: R8, R9, R10.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not integration and not e2e and not browser"
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_fecha_zona_horaria.py -q
```

Comprobar R9 explícitamente: una fila sellada por el propio sistema **nunca** puede ser
rechazada después por su propio validador. Es el ciclo que hoy se rompe.

---

## T5 — Sellado en el dominio, no en el almacenamiento  [ ] ⚠ requiere aprobación

**Artefacto:** las inserciones dejan de apoyarse en `DEFAULT CURRENT_DATE` /
`CURRENT_TIMESTAMP` y pasan la fecha como parámetro; los 3 `datetime('now')` de
`sqlite_infraestructura_repo.py:1187`, `:1228` y `sqlite_periodo_repo.py:151` se
sustituyen por un parámetro.

Requisitos: R4, R5, R6, R7.

**No iniciar sin la aprobación de David.** Los `DEFAULT` del esquema se **conservan** como
red de seguridad (D3): esta tarea cambia quién asigna la fecha en el camino normal, no
elimina la red.

Priorizar por daño: `control_diario.fecha`, `registro_comportamiento.fecha`,
`entradas_seguimiento.fecha`, `notas.fecha_registro`,
`observaciones_periodo.fecha_registro`, `estudiantes.fecha_ingreso`. El resto después.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "integration or slow"
```

**Línea base obligatoria:** ejecutarlo **antes** y anotar el recuento (30 fallos a fecha de
2026-09-06, de los cuales 5 son de este defecto). El criterio es **bajar a 25** sin añadir
ninguno nuevo (`CLAUDE.md`: comparar antes de culpar a un cambio).

---

## T6 — Lectura de filas ya selladas por delante  [ ]

**Artefacto:** la recuperación de una fila con fecha futura no falla (R11), y existe forma
de localizar las filas afectadas (R12).

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_fecha_zona_horaria.py -q -k recupera
```

Cubrir: sembrar una fila con fecha de mañana, recuperarla, y comprobar que se entrega.
La validación de «no futura» debe seguir rechazándola **al entrar**. Si el mecanismo
elegido para esa asimetría debilitara la validación de entrada → **PARAR y reportar**.

---

## T7 — Puerta contra la reaparición  [ ]

**Artefacto:** comprobación que falla si aparece `date.today()`, `datetime.now()`,
`CURRENT_DATE`, `CURRENT_TIMESTAMP` o `datetime('now')` fuera del origen único, con lista
de exenciones explícita.

Requisitos: R15.

Según `CLAUDE.md`, toda regla nueva debe consumir sentencias lógicas, no líneas físicas:
una violación partida en varias líneas debe detectarse igual.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/unit/domain/test_fecha_zona_horaria.py -q -k puerta
```
Comprobar que **detecta**: introducir un `date.today()` en un módulo, ver el rojo,
revertir.

---

## T8 — Cierre  [ ]

**Artefacto:** `progress/impl_datos_08.md` con las columnas migradas, las que quedaron
apoyadas en el `DEFAULT`, el contenido de la lista de exenciones y el recuento de filas
existentes con fecha por delante que se hayan encontrado.

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
.venv/Scripts/python.exe -m pytest -q -m "integration or slow"
```
La primera, TODO VERDE. La segunda debe haber bajado de 30 a 25 fallos: los 25 restantes
son de firmas y los cierra `harness_01_integracion_en_puerta`.

Ejecutar la comprobación **a dos horas distintas** del día —una antes de las 19:00 y otra
después— o simulando ambas con el instante fijado. El defecto era invisible por la mañana
y el arreglo debe verificarse en la franja donde se manifestaba (R14).
