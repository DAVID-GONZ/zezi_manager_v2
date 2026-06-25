# seguridad_03_auditoria_integridad — Bitácora a prueba de manipulación (M3)

> Tercer y último paso del épico de seguridad. Cierra **M3**: hoy las dos tablas
> de auditoría (`auditoria` = eventos de sesión, `audit_log` = cambios CRUD) son
> append-only *solo por convención*; quien tenga acceso al archivo `data/app.db`
> puede alterar o borrar registros sin dejar rastro. Se añade un
> **encadenamiento por hash** (cada registro firma al anterior) que vuelve
> detectable cualquier edición, inserción o borrado intermedio.

## Contexto y decisión (David)

- Encadenamiento: `hash_cadena = SHA256(hash_previo || payload_canónico)` por
  registro, donde `hash_previo` es el `hash_cadena` del registro inmediatamente
  anterior de la MISMA tabla (o un `GENESIS` constante si la tabla está vacía).
- El `payload` cubre los campos persistidos del registro (sin el `id`, que lo
  asigna SQLite tras el INSERT). La verificación recalcula la cadena en orden
  `id ASC` y reporta el `id` del primer registro roto.
- Limitación conocida (documentar, no resolver aquí): el encadenamiento detecta
  edición/inserción/borrado **intermedio**; el truncado del final (borrar los
  últimos N) requiere un ancla externa y queda fuera de alcance.

### Decisiones de bajo blast-radius (NO negociar sin motivo)
- **Modelos de dominio NO cambian.** El mapper del repo (`_row_to_evento` /
  `_row_to_cambio`) **descarta** la columna `hash_cadena` del `dict(row)` antes
  de construir la entidad Pydantic (que prohíbe campos extra). El paso toca
  schema pero NO entidades de dominio.
- **Port sin `@abstractmethod` nuevos.** Los métodos de verificación se añaden a
  `IAuditoriaRepository` como **métodos concretos** (con implementación por
  defecto que devuelve "no verificable") para NO romper los fakes de auditoría
  existentes (`tests/integration/audit_ports.py`, `tests/unit/services/test_usuario_service.py`,
  `tests/unit/services/test_solo_lectura.py`). El repo SQLite los sobreescribe.

## Scope (destino_v2)

```
src/domain/policies/audit_chain.py             (NUEVO — hash puro + verificador)
src/domain/policies/__init__.py
src/infrastructure/db/schema.py
src/domain/ports/auditoria_repo.py
src/infrastructure/db/repositories/sqlite_auditoria_repo.py
src/services/auditoria_service.py
src/interface/pages/admin/auditoria.py
tests/unit/domain/test_audit_chain.py          (NUEVO)
tests/unit/services/test_auditoria_service.py  (NUEVO)
tests/integration/test_repositories.py
```

Baseline antes de empezar: `python init.py` → **1260 passed, 1 skipped**
(usar SIEMPRE `.venv/Scripts/python.exe`).

---

## Tareas

### [x] T1 — Policy de dominio `audit_chain.py` (hash puro)
- Nuevo `src/domain/policies/audit_chain.py`, puro (sin IO/infra/interfaz; estilo
  `password_policy.py`/`rbac_usuarios.py`). API:
  - `GENESIS: str` (constante para el primer eslabón).
  - `calcular_hash(hash_previo: str | None, campos: dict) -> str`: serializa
    `campos` de forma canónica (claves ordenadas, JSON estable) y devuelve
    `sha256(hash_previo_or_GENESIS + payload).hexdigest()`.
  - `primer_eslabon_roto(secuencia: list[tuple[dict, str]]) -> int | None`:
    dada la secuencia ordenada de `(campos, hash_almacenado)`, recalcula
    encadenando y devuelve el índice (0-based) del primer hash que no cuadra, o
    `None` si la cadena es íntegra.
- Exportar desde `src/domain/policies/__init__.py`.
- **Verificación:** `.venv/Scripts/python.exe scripts/check_imports.py --layer domain` exit 0;
  `.venv/Scripts/python.exe -m pytest tests/unit/domain/test_audit_chain.py -q`.

### [x] T2 — Schema: columna `hash_cadena` en ambas tablas (idempotente)
- En `schema.py`, añadir `hash_cadena TEXT` a los CREATE de `auditoria` y
  `audit_log`, **y** `ALTER TABLE ... ADD COLUMN hash_cadena TEXT` idempotente en
  la ruta de migración de `init_db` (no romper BDs existentes; los registros
  previos quedan con `hash_cadena` NULL = "pre-cadena", documentar que la
  verificación arranca desde el primer registro con hash no nulo).
- **Verificación:** `.venv/Scripts/python.exe scripts/check_imports.py --layer infrastructure`;
  `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py` sigue verde (schema aplica).

### [x] T3 — Repo: calcular hash al insertar + descartar columna en el mapper
- `sqlite_auditoria_repo.py`:
  - Helper privado `_ultimo_hash(conn, tabla) -> str | None` (SELECT hash_cadena
    ... ORDER BY id DESC LIMIT 1).
  - `registrar_evento`: antes del INSERT, calcular `hash_cadena` con
    `calcular_hash(_ultimo_hash, payload)` donde `payload` son los valores
    insertados (usuario, usuario_id, tipo_evento.value, ip_address,
    fecha_hora.isoformat(), detalles); incluir la columna en el INSERT.
  - `registrar_cambio`: idem con su payload de `audit_log`.
  - `registrar_cambios_masivos`: precomputar los hashes en memoria de forma
    **secuencial** (cada uno encadena con el anterior, partiendo de
    `_ultimo_hash`), luego `executemany` con la columna incluida. NO usar un
    hash constante por lote.
  - `_row_to_evento` / `_row_to_cambio`: **descartar** `hash_cadena` (y cualquier
    columna no mapeada) del dict antes de construir la entidad.
- **Verificación:** `.venv/Scripts/python.exe -m pytest tests/integration/test_repositories.py -q`
  (cobertura: insertar N eventos/cambios encadena; alterar una fila por SQL
  directo y `primer_eslabon_roto` la detecta).

### [x] T4 — Port + repo: métodos de verificación (concretos, sin romper fakes)
- `auditoria_repo.py` (port): añadir como **métodos concretos** (NO
  `@abstractmethod`):
  - `verificar_cadena_eventos() -> int | None` (id del primer evento roto o None)
  - `verificar_cadena_cambios() -> int | None`
  - Implementación por defecto en el port: `return None` con docstring "los
    repos sin soporte de cadena se consideran no verificables". (Así los fakes
    heredan sin cambios.)
- `sqlite_auditoria_repo.py`: sobreescribir ambos: leer todas las filas en orden
  `id ASC` (solo las que tengan `hash_cadena` no nulo), reconstruir `(payload,
  hash_almacenado)` y delegar en `primer_eslabon_roto`; traducir el índice al
  `id` real del registro roto.
- **Verificación:** test de integración: cadena íntegra → None; tras UPDATE
  manipulando `detalles` de un registro → devuelve su id.

### [x] T5 — Servicio: `verificar_integridad()`
- `auditoria_service.py`: método `verificar_integridad() -> ResultadoIntegridadDTO`
  (o un dict simple de primitivos si no quieres añadir DTO al modelo —
  preferible un dict `{"eventos_ok": bool, "cambios_ok": bool, "evento_roto_id":
  int|None, "cambio_roto_id": int|None}` para NO tocar modelos de dominio).
  Llama a los dos métodos del repo y compone el resultado.
- **Verificación:** `.venv/Scripts/python.exe -m pytest tests/unit/services/test_auditoria_service.py -q`
  (con un fake que devuelve None / un id, el servicio compone bien el resultado).

### [x] T6 — UI mínima en `admin/auditoria.py`
- Añadir un control **read-only** (botón "Verificar integridad" + badge de estado
  con `status_badge`/clases del design system) que llame
  `Container.auditoria_service().verificar_integridad()` y muestre
  "Íntegra" (success) o "Alterada (registro #N)" (danger). Sin tocar el resto de
  la página. La página NO importa `src.domain.*`; usa primitivos del servicio.
- **Verificación:** `.venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/admin/auditoria.py` exit 0;
  `check_imports --layer interface` exit 0.

### T7 — Verificación integral
- `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py` **VERDE** (≥1260 passed + nuevos).
- `.venv/Scripts/python.exe scripts/check_tasks.py`.
- `progress/impl_seguridad_03_auditoria_integridad.md` (formato implementer.md).

## criterio_done
Cada INSERT en `auditoria` y `audit_log` almacena un `hash_cadena` encadenado al
registro anterior; alterar/insertar/borrar un registro intermedio rompe la cadena
y `verificar_integridad()` lo detecta devolviendo el id del primer registro roto;
la verificación es accesible desde `/admin/auditoria` (admin) como indicador
read-only; los modelos de dominio y los fakes de tests quedan intactos;
`python init.py` verde sin regresiones.
