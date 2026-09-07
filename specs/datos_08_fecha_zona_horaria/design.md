# Diseño: datos_08_fecha_zona_horaria

## El defecto, reproducido

Ejecutado el 2026-09-06 a las 19:50, hora de Colombia (UTC−5):

```
SQLite CURRENT_DATE (UTC) : 2026-09-07     <-- mañana
SQLite CURRENT_TIMESTAMP  : 2026-09-07 00:50:47
Python date.today() local : 2026-09-06     <-- hoy
Hora local                : 2026-09-06 19:50:47
```

SQLite resuelve `CURRENT_DATE` y `CURRENT_TIMESTAMP` **siempre en UTC**. Los validadores
del dominio comparan contra `date.today()`, que es **hora local del proceso**. Son dos
relojes distintos con cinco horas de diferencia.

### Cómo se manifiesta

```
19:00–24:00 hora de Colombia  ->  la base sella con la fecha de MAÑANA
                              ->  el modelo valida contra HOY
                              ->  ValidationError: la fecha no puede ser futura
```

**Cinco horas de cada día, el 21% del tiempo.** Fuera de esa franja el sistema funciona,
y por eso el defecto ha pasado inadvertido: quien trabaja de mañana no lo ve nunca.

Es lo que hace fallar a 5 de los 30 tests de integración:

```
ValidationError: 1 validation error for RegistroComportamiento
  fecha: Value error, La fecha del registro (2026-09-07) no puede ser futura.
```

Esos tests no están mal escritos. **Están detectando un defecto real** que solo se
manifiesta a partir de las 19:00.

### El daño silencioso

El `ValidationError` es la cara visible y benigna: falla ruidosamente. La cara grave es la
que no falla.

Una fila sellada con fecha de mañana **y que nunca se relee por un modelo con validador**
se queda en la base con la fecha equivocada, sin error ni traza:

| Tabla | Columna | Consecuencia de un sellado a las 19:30 |
|---|---|---|
| `control_diario` | `fecha` | La asistencia de hoy se registra como la de mañana |
| `registro_comportamiento` | `fecha` | Un registro de convivencia queda fechado un día después del hecho |
| `entradas_seguimiento` | `fecha` | El seguimiento se desordena cronológicamente |
| `notas.fecha_registro` | | La nota consta registrada fuera del plazo real |
| `observaciones_periodo` | `fecha_registro` | Igual |
| `estudiantes` | `fecha_ingreso` | La matrícula consta un día después |

En un sistema cuyo objeto es acreditar asistencia y convivencia ante la Ley 1620, una
fecha corrida un día no es un detalle cosmético: es la fecha que aparecerá en un
observador del estudiante o en un acta.

## Alcance medido

- **20 columnas** con `DEFAULT CURRENT_DATE` o `DEFAULT CURRENT_TIMESTAMP` en
  `schema.py`.
- **3 puntos** de repositorios en producción con `datetime('now')` (también UTC):
  `sqlite_infraestructura_repo.py:1187`, `:1228`, `sqlite_periodo_repo.py:151`.
- **9 o más validadores** `> date.today()` en `asistencia.py`, `cierre.py`,
  `convivencia.py`, y los `default_factory=date.today` repartidos por los modelos.

## Decisiones

### D1 — Un único origen del instante actual (R1)

Una función de dominio es la única autorizada a responder «qué día es hoy» y «qué hora
es». Todo validador y todo `default_factory` la usan; ningún módulo llama directamente a
`date.today()` ni a `datetime.now()`.

Beneficio inmediato más allá del defecto: **hace comprobable el tiempo** (R13). Hoy
`Estudiante.edad`, `HitoPeriodo.esta_vencido` y las 9 propiedades del grupo C de
`datos_03` no se pueden verificar de forma reproducible porque leen el reloj real.

### D2 — La zona horaria es configuración, no constante (R3)

La zona de referencia se resuelve desde la configuración. Valor por omisión
`America/Bogota`, coherente con el ámbito actual del producto, pero **declarado en
configuración** porque el objetivo es multi-institución: una institución en otro huso
necesita el suyo, y una constante incrustada obligaría a tocar código para cada cliente.

Python 3.12 trae `zoneinfo` en la biblioteca estándar; no hace falta dependencia nueva.

### D3 — El sellado deja de hacerlo la base (R2, R5, R6)

Los `DEFAULT CURRENT_DATE` y `DEFAULT CURRENT_TIMESTAMP` **no pueden resolverse en la zona
correcta desde SQLite**: no conoce la zona de referencia de la institución.

La fecha pasa a asignarse en el dominio, por el origen único de D1, y viaja como parámetro
explícito del `INSERT`. Los `DEFAULT` del esquema se conservan como red de seguridad para
escrituras que no pasen por el dominio, pero dejan de ser el camino normal.

Los 3 `datetime('now')` de los repositorios se sustituyen por un parámetro.

**Alternativa evaluada y rechazada:** `DEFAULT (datetime('now','-5 hours'))`. Funciona, es
un cambio mínimo y no toca código Python. Se rechaza porque incrusta el huso en el
esquema, contradice R3, y se rompe sola en cualquier institución fuera de Colombia — es
exactamente la clase de atajo que habría que deshacer al primer cliente nuevo.

### D4 — Las filas ya selladas por delante (R11, R12)

Puede haber filas con fecha de mañana escritas por el comportamiento actual. Los
validadores no deben impedir **leerlas**: un dato ya escrito se recupera, se muestra y se
puede corregir; rechazarlo al leer deja la fila inaccesible desde la aplicación, que es
peor que el desfase.

La validación de «no futura» sigue aplicándose a lo que **entra**. Lo que **sale** del
almacenamiento se entrega. La spec debe fijar el mecanismo para esa asimetría y una
consulta que permita localizar las filas afectadas (R12).

### D5 — Puerta contra la reaparición (R15)

Una comprobación estática que falle si aparece un `date.today()`, `datetime.now()`,
`CURRENT_DATE`, `CURRENT_TIMESTAMP` o `datetime('now')` fuera del origen único, con una
lista de exenciones explícita. Sin ella, el defecto vuelve con el siguiente módulo que se
escriba.

## Dependencias

- **Bloquea a `harness_01_integracion_en_puerta`**: mientras este defecto exista, 5 tests
  de integración siguen en rojo y la puerta no puede encadenar la suite de integración.
- **Ayuda a `datos_03_computed_fields`**: el origen único es lo que permite congelar la
  fecha en los tests de las 9 propiedades del grupo C (su R14).
- **Toca `schema.py` → puerta de aprobación de David** (`CLAUDE.md`).

## Alternativa global descartada

**Fijar la zona horaria del proceso a UTC y trabajar en UTC de extremo a extremo.**

Es la práctica habitual en sistemas distribuidos y elimina toda ambigüedad interna. Se
descarta porque la fecha aquí **no es un instante técnico sino un hecho escolar**: «la
asistencia del 6 de septiembre» es el día lectivo tal como lo vive el colegio, no un punto
en la línea temporal universal. Con el proceso en UTC, la jornada de la tarde seguiría
cayendo en el día siguiente y el problema sería idéntico, solo que sin la discrepancia
visible que hoy lo delata. La zona de referencia de la institución es el criterio correcto
precisamente porque el dato es local por naturaleza.
