# Diseño: backend_02b_tests_esquema

## Punto de partida medido

| Métrica | Valor |
|---|---|
| Tablas en `SCHEMA` | 65 |
| Líneas en `schema.py` | 1,654 |
| Índices en `INDICES` | por contar |
| Triggers en `TRIGGERS` | por contar |
| Tests de esquema existentes | **0** |

Defectos conocidos que estos tests deben atrapar:
- **D1:** orden de dependencias violado (`grupos` → `usuarios`, `observaciones_periodo` → `registro_comportamiento`).
- **D2:** `grupos.sala_id` sin FK declarada.

## D1 — Fuente de verdad: sqlite_master

Para verificar el esquema aplicado se usa `PRAGMA table_info(tabla)`,
`PRAGMA foreign_key_list(tabla)`, `PRAGMA index_list(tabla)` y
`SELECT * FROM sqlite_master WHERE type='trigger'`.

Estas son introspecciones del esquema real, no del DDL declarado. Si el DDL
tiene un error que SQLite tolera silenciosamente (como D1), los PRAGMAs
lo reflejan.

## D2 — Extracción de las tablas declaradas

Parsear la lista `SCHEMA` para extraer los nombres de tabla: cada string
empieza con `CREATE TABLE IF NOT EXISTS <nombre>`. Un regex sencillo basta.

Para las FKs declaradas, parsear `FOREIGN KEY (...) REFERENCES tabla(col)`.
No se usa un parser SQL completo — las declaraciones siguen un formato
consistente en todo `schema.py`.

## D3 — Test de orden de dependencias (R6)

Para cada tabla en el orden de `SCHEMA`:
1. Extraer sus `REFERENCES tabla` del DDL.
2. Verificar que cada tabla referenciada ya apareció antes en la lista.

Si una referencia apunta a una tabla posterior → fallo, con el nombre de
la tabla y la referencia adelantada.

D1 se convierte en `xfail`: la suite espera que este test falle para `grupos`
y `observaciones_periodo`, con `reason="D1: orden de dependencias — se resuelve
en backend_04"`.

## D4 — Test de FKs fantasma vs. reales (R3)

Para cada tabla:
1. Extraer FKs declaradas del DDL (`FOREIGN KEY`).
2. Extraer FKs reales de `PRAGMA foreign_key_list(tabla)`.
3. Comparar conjuntos.

Si hay una columna `_id` sin FK declarada y sin justificación → fallo.

D2 se convierte en `xfail` para `grupos.sala_id`.

## D5 — Estructura de archivos

```
tests/unit/infrastructure/test_schema_integrity.py   (NUEVO)
```

Un solo archivo. Usa la fixture `db_schema` de conftest (schema sin datos,
scope session). No necesita seed ni datos.

## Alternativa descartada

**Generar el esquema esperado como snapshot y comparar texto.** Frágil ante
reformateos inocuos del DDL. Los PRAGMAs comparan la semántica, no la sintaxis.
