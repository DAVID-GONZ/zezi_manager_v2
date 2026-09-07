# Diseño: datos_04_decimal_notas

## El fallo, demostrado

No es un riesgo teórico. Con las tres notas **exactamente en el umbral de aprobación**:

```
pesos = [0.7, 0.29, 0.01]   notas = 3.0 cada una   umbral = 3.0

  float   ->  0.7*3.0 + 0.29*3.0 + 0.01*3.0  =  2.9999999999999996   aprueba = False
  Decimal ->  mismos operandos                =  3.000               aprueba = True
```

**Un estudiante con 3.0 en todas sus categorías reprueba el periodo** por la
representación binaria. Los mismos pesos suman `0.9999999999999999` en `float`, así que
tampoco superan una comprobación exacta de «los pesos suman 1».

Ese segundo efecto ya está parcheado en el código, y el parche documenta el problema:

```python
# src/domain/models/evaluacion.py:602
@staticmethod
def pesos_validos(categorias: list[Categoria]) -> bool:
    """
    True si la suma de pesos de las categorías es <= 1.0.
    Margen de 0.001 para errores de redondeo de flotantes.
    """
    return CalculadorNotas.peso_total(categorias) <= 1.001
```

Ese `1.001` es exactamente el margen arbitrario que **R12 prohíbe**. Con aritmética
decimal la comparación vuelve a ser exacta y el margen desaparece.

## Alcance medido

29 columnas `REAL` y 84 campos `float` en los modelos. **Cero usos de `Decimal`** en todo
el proyecto.

| Familia | Columnas | Cuantización | Requisito |
|---|---|---|---|
| Calificaciones | `notas.valor`, `cierres_periodo.nota_definitiva`, `cierres_anio.nota_promedio_periodos`, `cierres_anio.nota_habilitacion`, `cierres_anio.nota_definitiva_anual`, `habilitaciones.nota_antes`, `habilitaciones.nota_habilitacion`, `notas_corte_plan.nota_al_corte`, `notas_corte_plan.nota_definitiva_plan`, `notas_actividad_plan.valor`, `notas_nivelacion.valor`, `nota_comportamiento_periodo.valor`, `actividades.valor_maximo` | 2 decimales | R2 |
| Umbrales y escala | `configuracion_anio.nota_minima_aprobacion`, `nota_minima_escala`, `nota_maxima_escala`, `criterios_promocion.nota_minima_habilitacion`, `criterios_promocion.nota_minima_anual`, `cortes_plan.nota_umbral`, `cortes_plan.nota_minima_aprobacion`, `configuracion_alertas.umbral` | 2 decimales | R2 |
| Rangos de desempeño | `niveles_desempeno.rango_min`, `rango_max` | 2 decimales | R2 |
| Pesos de ponderación | `categorias.peso`, `periodos.peso_porcentual`, `cortes_plan.peso_registrado`, `actividades_plan.peso`, `actividades_nivelacion.peso`, `configuracion_siee.porcentaje_autonomia_docente` | 4 decimales | R3 |

**Fuera de ámbito (R25):** los estadísticos agregados de solo lectura, los porcentajes de
progreso y los pesos heurísticos del generador de horarios. Ninguno determina la
aprobación de un estudiante, y convertirlos añadiría coste sin cerrar ningún riesgo.

## Decisiones

### D1 — Tipo y cuantización centralizados

Un único módulo define el tipo anotado y la operación de cuantización, y todos los
modelos lo importan (R7). Dos precisiones distintas:

- **Nota**: 2 decimales, `ROUND_HALF_UP`.
- **Peso**: 4 decimales, `ROUND_HALF_UP`.

`ROUND_HALF_UP` y no el `ROUND_HALF_EVEN` que Python trae por defecto: en calificación
académica, un 2.995 debe subir a 3.00 de forma predecible y siempre en el mismo sentido.
El redondeo bancario alternaría según la paridad del dígito anterior, que es indefendible
ante un acudiente que pregunte por qué su hijo no aprobó.

La cuantización se aplica en un `field_validator(mode="before")` que acepta `str`, `int`,
`float` y `Decimal` y produce siempre el mismo valor cuantizado (R5, R6).

### D2 — Persistencia: el punto técnico central

`sqlite3` **rechaza** `Decimal`. Verificado:

```
sqlite3.ProgrammingError: Error binding parameter 1: type 'decimal.Decimal' is not supported
```

Tres opciones, y ninguna es gratis:

| Opción | Qué pasa | Veredicto |
|---|---|---|
| `float(valor)` al escribir | Funciona. Reintroduce el error binario en el almacenamiento | Aceptable **solo** porque el valor ya está cuantizado a 2 o 4 decimales antes de convertir |
| `str(valor)` al escribir | En columna `REAL`, SQLite lo convierte igualmente a real por afinidad de tipo. Verificado: `str(Decimal('3.05'))` acaba guardado como `3.05 real` | **No aporta nada** sobre `float` mientras la columna sea `REAL` |
| `sqlite3.register_adapter` | Centraliza la conversión, pero es estado global del módulo `sqlite3` y afecta a cualquier conexión del proceso | Se descarta: efecto a distancia sobre los tests |

**Decisión:** conversión explícita a `float` en la frontera del repositorio, sobre un
valor ya cuantizado, y reconstrucción a `Decimal` **vía `str()`** al leer:

```
Decimal(str(3.05))   ->  Decimal('3.05')      correcto
Decimal(3.05)        ->  Decimal('3.0499999…') incorrecto
```

Ese `str()` intermedio es lo que satisface R19: sin él, el ruido binario del
almacenamiento entra de vuelta en el dominio.

La garantía real de R18 y R20 es que **un decimal de 2 dígitos sobrevive intacto el ciclo
`Decimal → float → REAL → float → str → Decimal`**, porque un `float` de doble precisión
representa sin ambigüedad cualquier decimal corto. T1 lo demuestra antes de tocar nada.

Cuando `backend_04_metadata_schema` sustituya `REAL` por `NUMERIC(4,2)`, esta frontera es
el único punto que cambia.

### D3 — Cálculo: cuantizar una sola vez

`CalculadorNotas.calcular_definitiva` acumula los productos `peso × promedio` en precisión
decimal completa y cuantiza **solo el resultado** (R8, R9). Hoy hace `round(..., 2)` sobre
un `float`, que redondea sobre un valor ya contaminado.

`pesos_validos` pierde el margen `1.001` y compara exacto contra `Decimal("1")` (R12).

### D4 — Frontera con pandas y los exportadores

`fetch_df` devuelve DataFrames y los informes operan sobre ellos. pandas no tiene tipo
decimal nativo: una columna de `Decimal` queda como `dtype=object`, y cualquier
`.mean()` o `.sum()` sobre ella o bien falla o bien vuelve a `float`.

Es el punto donde más probablemente se rompa algo. La regla (R23, R24): dentro de un
DataFrame los valores pueden viajar como `object`, pero **todo valor que vuelva a
compararse contra un umbral o a acumularse en una suma ponderada debe reconvertirse a
`Decimal` antes**. Los exportadores entregan valores numéricos, nunca texto (R21).

### D5 — Mezclas accidentales (R26)

`Decimal * float` lanza `TypeError` por sí solo en Python. No hace falta maquinaria
adicional: la propia aritmética señala el error de forma inmediata y explícita, que es lo
que el requisito pide. La tarea es **no** silenciarlo con conversiones defensivas.

## Interacción con otros pasos

- **`datos_02`**: `validate_assignment=True` hace que asignar una nota después de
  construir el modelo vuelva a pasar por la cuantización. Refuerza R5.
- **`backend_04_metadata_schema`**: este paso debe ir **antes**, para que el tipo de
  columna se fije con el dominio ya correcto.

## Hallazgo colateral

`src/domain/models/evaluacion.py:464` construye un diccionario por comprensión y descarta
el resultado:

```python
{a.id: a for a in actividades if a.id}   # no se asigna a nada
```

Código muerto en el corazón del cálculo. No es de este paso, pero conviene retirarlo al
pasar por ahí y dejar constancia.

## Alternativa descartada

**Escalar a enteros: guardar las notas en centésimas (`int`), y dividir solo al mostrar.**

Es exacto, rápido y elimina toda cuestión de representación. Se descarta porque cambia el
significado de cada valor almacenado —un `300` que hay que leer como `3.00`—, obliga a
reinterpretar las 29 columnas y todo dato existente, y traslada a cada punto de lectura la
responsabilidad de escalar. `Decimal` da la misma exactitud conservando la legibilidad del
dato en la base y en los informes, y es lo que `NUMERIC(4,2)` ofrecerá de forma nativa
cuando el motor cambie.
