# paso_37 — Username único global + login simple (revertir guard ambiguo de paso_33)

## Contexto y decisión (David)

El flujo de login ambiguo de paso_33 **filtra información** (revela que un username existe en varias instituciones y muestra sus nombres a alguien sin autenticar) y su advertencia es innecesaria. Decisión (Opción B): **username único GLOBAL** → el login vuelve a ser simple (usuario+contraseña, sin selector de institución, sin guard de ambigüedad, sin advertencia). **Cero divulgación.**

Esto revierte ÚNICAMENTE la dimensión de *unicidad de username* de paso_33. **Todo lo demás del multi-tenant se mantiene:** `institucion_id` en usuarios y tablas académicas, scope central (`institucion_actual()`), config por institución, autorización por objeto (paso_36), guard central de rutas (paso_35). La sesión sigue cargando `institucion_id` del usuario autenticado (ahora sin ambigüedad: un username = un usuario = una institución).

Coste aceptado: dos instituciones no pueden repetir username (se hace namespacing, p.ej. `director.prueba`).

## Tareas

### T1 — Schema: username global de nuevo
- En `usuarios`: cambiar `UNIQUE(institucion_id, usuario)` → `usuario TEXT NOT NULL UNIQUE` (global). `institucion_id` se mantiene (sigue scopeando todo lo demás). (No hay migraciones desde paso_34: solo el `CREATE TABLE`.)

### T2 — Servicio: unicidad global al crear
- `usuario_service.crear_usuario`: validar unicidad **global** del username (`existe_usuario(usuario)` sin institución / global). Rechazar si el username existe en CUALQUIER institución.
- Revertir/limpiar lo añadido en paso_33 que ya no aplica: el parámetro `institucion_id` de `existe_usuario`/`get_by_username` puede volver a su forma global (o quedar con default None = global), y **eliminar `listar_por_username`** si ya no se usa. Quitar código muerto.

### T3 — Auth: login simple
- `bcrypt_auth_service.autenticar_usuario(usuario, password)`: volver al flujo simple — `get_by_username(usuario)` → verificar password → ok/falla. **Eliminar** `LoginAmbiguoError`, la lógica de `candidatos`/desambiguación y el parámetro `institucion_id`. Mensaje de credenciales inválidas genérico (sin revelar nada).

### T4 — Login UI: quitar selector e advertencia
- `src/interface/pages/login.py`: eliminar el `ui.select` de institución, el manejo de ambigüedad y la advertencia asociada. Volver al formulario simple (usuario + contraseña). Al autenticar, `SessionContext.institucion_id` se puebla del usuario (un username → una institución; sin ambigüedad).

### T5 — Seed: 2ª institución con username distinto
- En `seed_dev`, el director de la 2ª institución hoy comparte username `director` (paso_34) → ahora viola la unicidad global. Cambiarlo a un username **distinto y global-único** (p.ej. `director.prueba`), con su contraseña conocida. Mantener el resto del dataset de la 2ª institución (grupo `601`, documento reutilizado siguen válidos: `(institucion_id, codigo)` y `(institucion_id, numero_documento)` siguen siendo compuestos — NO se tocan).
- El objetivo de prueba se mantiene: aislamiento por institución (cada director ve lo suyo); ya NO hay login ambiguo.

### T6 — Tests + verificación
- Retirar/ajustar los tests de login ambiguo de paso_33 y el de "login ambiguo de `director`" de paso_34.
- Tests: crear el mismo username en dos instituciones **falla** (unicidad global); login simple entra sin pedir institución; el seed_dev de la 2ª institución usa el username distinto; sigue habiendo 2 instituciones con aislamiento (un director no ve la otra).
- `python init.py` VERDE (baseline 1181 passed, 1 skipped; corregir fallout — `get_by_username`/`existe_usuario` y los fakes que los implementan vuelven a la forma global). check_imports + check_design en verde.
- `progress/impl_paso_37.md`.

## criterio_done
`usuarios.usuario` es `UNIQUE` global; la creación valida unicidad global; el login es simple (usuario+contraseña, sin selector de institución, sin guard de ambigüedad, sin advertencia, sin divulgación); `LoginAmbiguoError`/`listar_por_username` y el código de desambiguación eliminados; el seed_dev usa un username distinto para el director de la 2ª institución; el resto del multi-tenant (scope, config por institución, autorización por objeto, guard de rutas) intacto; `python init.py` verde.
