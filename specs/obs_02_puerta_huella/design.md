# Diseño: Puerta de huella (obs_02_puerta_huella)

## 1. Archivos a crear

| Archivo | Responsabilidad |
|---|---|
| `scripts/check_auditoria.py` | La puerta: inventario y verificación de cobertura. |
| `tests/unit/test_check_auditoria.py` | Replica la puerta como test y comprueba que detecta un mutador sin huella. |
| `tests/integration/test_huella_cobertura.py` | Verificación en ejecución contra base real (R6). |

## 2. Archivos a modificar

- `scripts/init.py` — encadenar `check_auditoria` junto a `check_enums`, mismo contrato.

## 3. Cómo detecta (R1, R5)

Análisis con `ast` de la stdlib, en dos pasadas:

1. **Inventario de escritura por repositorio.** Métodos de
   `src/infrastructure/db/repositories/*.py` cuyo cuerpo contiene un literal con
   `INSERT INTO`, `UPDATE ... SET` o `DELETE FROM`.
2. **Recorrido de servicios.** En `src/services/*.py`, un método público es *mutador* si
   llama a alguno de esos métodos de repositorio; tiene *huella* si él —o un helper
   privado que invoque— llama a `auditar_cambio`.

**Por qué `ast` y no regex ni análisis por líneas.** `check_design.py` fue ciego a las
violaciones partidas en varias líneas hasta 2026-08-17, y al arreglarlo aparecieron 18
violaciones que llevaban meses ocultas. La misma trampa aplica aquí: una llamada a
`auditar_cambio(...)` repartida en cinco líneas es lo normal, no la excepción. Para
estructura de Python el árbol sintáctico evita el problema por construcción, y es una
garantía más fuerte que `_logical_lines()` — que resuelve el mismo riesgo para reglas de
texto, donde no hay árbol disponible.

## 4. Lista de deuda (R2, R3)

`SERVICIOS_SIN_HUELLA_DEUDA: dict[str, frozenset[str]]` — mismo formato y filosofía que
`ENUMS_SIN_CHECK_DEUDA` en `scripts/check_enums.py:62-68`. Arranca con los ~16 servicios
descubiertos y cada tramo de `obs_04` la reduce.

**Doble filo, y es lo que hace de trinquete:**

- Falla si aparece un mutador sin huella **fuera** de la lista → la deuda no puede crecer.
- Falla si una entrada de la lista **ya tiene** huella → la deuda no puede quedarse
  obsoleta.

El segundo filo existe por precedente propio: `RESTRICCIONES_DEUDA`
(`check_enums.py:52-58`) quedó con 5 entradas muertas tras `datos_05` y hoy puede
enmascarar una regresión futura, porque un CHECK nuevo que coincidiera con uno de esos
nombres pasaría como "deuda conocida". Que la entrada obsoleta falle en vez de ignorarse
impide que esta lista repita esa historia.

## 5. Alternativa descartada

**Solo el test de integración (R6), sin puerta estática.** Se descarta porque el test únicamente
cubre lo que alguien se acordó de ejercitar: un servicio nuevo sin test pasaría invisible,
que es exactamente cómo se llegó a 118 métodos sin huella.

Se necesitan los dos mecanismos y son complementarios: **la puerta estática enumera** —ve
todo el código, incluido lo que nadie probó— **y el test dinámico verifica que lo enumerado
es cierto** —una llamada a `auditar_cambio` puede existir y no escribir nada, que es
literalmente el bug de `HabilitacionService`—. El estático se puede engañar; el dinámico no
es exhaustivo.

## 6. Manejo de errores y salida

Código de salida 0 = sin pendientes fuera de la deuda declarada; 1 = falla la puerta. El
informe lista servicio, método y estado, más los totales de R4.

Copiar el bloque «Consola UTF-8» de `scripts/check_design.py` (regla de CLAUDE.md: los
scripts fuerzan UTF-8 en su propia salida desde 2026-08-17; sin él, imprimir un check verde
revienta con `UnicodeEncodeError` en consolas cp1252 de Windows, y ese rojo del terminal se
confunde con un rojo del proyecto).
