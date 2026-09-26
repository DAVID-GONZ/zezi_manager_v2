# Verificación de integridad de la bitácora exportada

> **Público objetivo:** un tercero (un auditor, la Secretaría de Educación, un
> apoderado o un experto forense) que ha recibido un archivo exportado por
> ZECI Manager y quiere comprobar, **sin acceso a la aplicación**, que el
> contenido no ha sido alterado desde que se exportó.
>
> Herramientas necesarias: Python 3.8+ (o cualquier shell con `sha256sum`/
> `certutil`). No se requiere ninguna dependencia adicional.

---

## Qué contiene el archivo exportado

Un archivo CSV exportado por ZECI Manager tiene dos partes:

1. **Hoja de verificación** — un bloque de líneas que empiezan con `#` al
   inicio del archivo. Contiene los hashes y el veredicto de integridad del
   momento de la exportación.
2. **Datos** — las filas de la bitácora, en CSV estándar (coma como
   separador, UTF-8-sig, encabezado de columnas en la primera línea sin `#`).

---

## Parte A: verificar que el archivo no se modificó después de exportar

El campo `hash_contenido` de la hoja de verificación es el SHA-256 de los
**bytes del CSV de datos** (todo lo que viene después de la línea que
empieza con la cabecera de columnas, es decir, excluyendo las líneas `#`).

### Paso A1: separar la hoja de verificación de los datos

```python
# verificar_contenido.py
import hashlib, sys

archivo = sys.argv[1]  # ruta al archivo exportado

lineas = open(archivo, encoding="utf-8-sig").readlines()

# Separar las líneas de comentario (#) de las de datos
datos_lineas = [l for l in lineas if not l.startswith("#")]
datos_str = "".join(datos_lineas)
datos_bytes = datos_str.encode("utf-8")

hash_calculado = hashlib.sha256(datos_bytes).hexdigest()
print("Hash calculado:", hash_calculado)
```

### Paso A2: comparar con la hoja

Busca en la cabecera del archivo la línea:

```
# hash_contenido: <valor>
```

Si `hash_calculado` coincide con `<valor>`, los **datos no han sido
modificados** desde la exportación.

Si no coincide, el archivo fue alterado después de ser producido por la
aplicación.

---

## Parte B: verificar la cadena SHA-256 del tramo

La bitácora de ZECI Manager encadena cada registro con el anterior mediante
SHA-256. La verificación de la cadena garantiza que ninguna fila fue editada,
insertada o borrada **dentro** de la base de datos antes de la exportación.

### La fórmula canónica del hash (fuente de verdad)

```
hash_cadena_N = SHA256( hash_cadena_(N-1) || payload_canónico_N )
```

donde `||` es concatenación de cadenas UTF-8 y:

- `hash_cadena_(N-1)` es el valor `hash_cadena` del registro anterior en la
  misma tabla (o la cadena literal `"GENESIS"` para el primer registro).
- `payload_canónico_N` es la serialización JSON del registro con:
  - **Claves ordenadas alfabéticamente** (`sort_keys=True`).
  - **Sin espacios** (`separators=(",", ":")`).
  - **Sin el campo `id`** (SQLite lo asigna tras el INSERT; no entra en el hash).
  - `ensure_ascii=False`.
  - Valores `None` como `null` en JSON.

### Campos que entran en el hash para `audit_log`

```json
{
  "accion": "UPDATE",
  "ip_address": "192.168.1.1",
  "registro_id": 42,
  "tabla": "estudiantes",
  "timestamp": "2026-09-01T10:00:00.000000",
  "usuario": "maria.docente",
  "usuario_id": 7,
  "valor_anterior": "{\"nombre\":\"Ana\"}",
  "valor_nuevo": "{\"nombre\":\"Ana María\"}"
}
```

> **Nota:** `institucion_id` **no** entra en el hash (es scope informacional).
> El campo `id` de la fila **no** entra en el hash.

### Campos que entran en el hash para `auditoria` (eventos de sesión)

```json
{
  "detalles": "Ruta /admin/usuarios accedida",
  "fecha_hora": "2026-09-01T08:30:00.000000",
  "ip_address": "192.168.1.2",
  "objetivo": null,
  "tipo_evento": "LOGIN_EXITOSO",
  "usuario": "director.colegio",
  "usuario_id": 3
}
```

> **Nota:** `severidad` e `institucion_id` **no** entran en el hash.

### Paso B1: extraer el tramo desde el CSV exportado

Las columnas del CSV incluyen `id` y `hash_cadena` (columna explícita en el
CSV exportado). Si el archivo fue exportado como `audit_log`, las columnas
relevantes para la verificación de la cadena son las descritas arriba más
`id` y `hash_cadena`.

### Paso B2: reconstruir la cadena con Python

```python
# verificar_cadena.py
import csv, hashlib, json, sys

GENESIS = "GENESIS"

def calcular_hash(hash_previo, campos):
    base = hash_previo or GENESIS
    payload = json.dumps(campos, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), default=str)
    return hashlib.sha256((base + payload).encode("utf-8")).hexdigest()

archivo = sys.argv[1]
hash_semilla = sys.argv[2] if len(sys.argv) > 2 else None
# hash_semilla = valor de hash_primera_fila de la hoja de verificación
# Si es el origen de la tabla, usar None (equivale a GENESIS).

# Columnas que entran en el hash (audit_log)
CAMPOS_HASH = [
    "accion", "ip_address", "registro_id", "tabla",
    "timestamp", "usuario", "usuario_id",
    "valor_anterior", "valor_nuevo",
]

# Leer el CSV omitiendo líneas de comentario
lineas = [l for l in open(archivo, encoding="utf-8-sig") if not l.startswith("#")]
reader = csv.DictReader(lineas)

hash_previo = hash_semilla  # None → GENESIS en la primera fila
primer_roto = None

for i, fila in enumerate(reader):
    campos = {}
    for c in CAMPOS_HASH:
        v = fila.get(c)
        if v == "" or v == "None":
            v = None
        # registro_id y usuario_id son enteros o None
        if c in ("registro_id", "usuario_id") and v is not None:
            try:
                v = int(v)
            except ValueError:
                pass
        campos[c] = v

    hash_esperado = calcular_hash(hash_previo, campos)
    hash_almacenado = fila.get("hash_cadena", "")

    if hash_esperado != hash_almacenado:
        print(f"FALLA en fila {i+1}, id={fila.get('id')}")
        print(f"  Esperado:  {hash_esperado}")
        print(f"  Almacenado:{hash_almacenado}")
        primer_roto = fila.get("id")
        break
    hash_previo = hash_almacenado

if primer_roto is None:
    print("CADENA INTEGRA: todos los eslabones verificados correctamente.")
else:
    print(f"CADENA ROTA: primer registro no íntegro id={primer_roto}")
```

### Paso B3: usar la semilla correcta

La hoja de verificación incluye:

```
# hash_primera_fila: <hash>
```

Este valor es el `hash_cadena` almacenado en la base de datos para la
**primera fila del tramo exportado**. Si el tramo arranca desde el origen
de la tabla, la semilla es implícitamente `GENESIS`; en ese caso, pasa
`None` como segundo argumento al script.

Si el tramo **no** arranca desde el origen (es un tramo del medio, por
ejemplo porque se han archivado filas antiguas), `hash_primera_fila` es la
semilla que el script necesita para arrancar la verificación desde ese punto.
En ese caso, el script recibe ese hash como argumento y lo usa como `hash_previo`
en la primera iteración.

---

## Parte C: limitación conocida (R14)

El encadenamiento SHA-256 detecta **edición, inserción o borrado intermedio**
de filas. **No detecta el truncado del final de la cadena**: si alguien borra
las últimas N filas, la verificación sobre las filas restantes sigue siendo
íntegra. Detectar ese caso requiere un ancla externa (un registro notarial, un
sellado de tiempo externo, etc.) fuera del alcance de esta aplicación.

Esta limitación está documentada en `src/domain/policies/audit_chain.py`.

---

## Ejemplo completo de verificación

Dado un archivo `bitacora_export.csv` con hoja de verificación:

```
# hash_contenido: a1b2c3...
# hash_primera_fila: d4e5f6...
# hash_ultima_fila: 7890ab...
# integridad_ok: True
```

1. Ejecutar `python verificar_contenido.py bitacora_export.csv`
   → compara el hash calculado con `hash_contenido`.

2. Ejecutar `python verificar_cadena.py bitacora_export.csv d4e5f6...`
   → reconstruye la cadena desde `hash_primera_fila` y verifica cada eslabón.

3. Si ambos verifican → el archivo es fiel a lo que estaba en la base en el
   momento de la exportación.

4. Si `integridad_ok` en la hoja era `False` → la cadena ya estaba rota antes
   de exportar; el campo `id_roto` apunta al primer registro comprometido.
   Esto no es un defecto de la exportación: es justamente la evidencia que hay
   que entregar.
