# API Reference — Dominio · Políticas

> Generado automáticamente desde `src/domain/policies/` por `tools/gen_api_reference.py` (firmas del fuente + primera línea del docstring). Los métodos sin docstring se marcan `⚠️ sin docstring`. **No editar a mano** — re-generar con el script.

**Cobertura de docstrings:** 9/9 métodos (100%).

| Archivo | Con docstring | Total | % |
|---|---:|---:|---:|
| `src/domain/policies/audit_chain.py` | 2 | 2 | 100% |
| `src/domain/policies/password_policy.py` | 3 | 3 | 100% |
| `src/domain/policies/rbac_usuarios.py` | 4 | 4 | 100% |

## `audit_chain.py`

### Funciones de módulo

- `def calcular_hash(hash_previo: str | None, campos: dict) -> str` — Calcula el `hash_cadena` de un registro a partir del hash del anterior.
- `def primer_eslabon_roto(secuencia: list[tuple[dict, str]]) -> int | None` — Devuelve el índice (0-based) del primer eslabón roto de la cadena, o None.

## `password_policy.py`

### Funciones de módulo

- `def errores_password( password: str, *, username: str | None = None ) -> list[str]` — Devuelve la lista de mensajes de error de la contraseña dada.
- `def validar_password(password: str, *, username: str | None = None) -> None` — Valida la contraseña; lanza `ValueError` con el primer mensaje si hay errores.
- `def requisitos_password() -> list[str]` — Textos legibles de las reglas de la política, para mostrar en la UI.

## `rbac_usuarios.py`

### Funciones de módulo

- `def _normalizar(rol: object) -> str` — Normaliza un rol (string o enum con `.value`) a string en minúsculas.
- `def roles_asignables(actor_rol: object) -> set[str]` — Conjunto de roles (strings) que `actor_rol` puede asignar o crear.
- `def puede_asignar_rol(actor_rol: object, target_rol: object) -> bool` — True si `actor_rol` puede asignar/crear el rol `target_rol`.
- `def puede_gestionar(actor_rol: object, target_rol: object) -> bool` — True si `actor_rol` puede gestionar (reactivar / desactivar / resetear

