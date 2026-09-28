# rebrand_02_loggers_internos — Tareas

Scope: solo archivos en `src/` (excepto seed data de `seed.py`).
Cualquier otro archivo -> PARAR y reportar al leader.

**IMPORTANTE:** este paso QUIEBRA tests que referencian `ZeciModel`,
`ZeciError` y `zeci.security`. Se debe ejecutar Paso 4 (rebrand_04_tests)
inmediatamente despues, en el mismo commit.

---

## T1 — Loggers: `zeci.security` -> `avedra.security`

**Artefactos:** `src/infrastructure/logging/security_logger.py`,
`src/domain/policies/alerta_ip.py`

- `security_logger.py:19`: docstring `zeci.security` -> `avedra.security`.
- `security_logger.py:101`: `logging.getLogger("zeci.security")` ->
  `logging.getLogger("avedra.security")`.
- `security_logger.py:118`: docstring `zeci.security` -> `avedra.security`.
- `alerta_ip.py:7,15,65`: docstrings `zeci.security` -> `avedra.security`.
- `alerta_ip.py:32`: `logging.getLogger("zeci.security")` ->
  `logging.getLogger("avedra.security")`.

**Verificacion:**
```
grep -rn "zeci" src/infrastructure/logging/ src/domain/policies/alerta_ip.py
```
Sin resultados.

---

## T2 — ContextVars

**Artefactos:** `src/infrastructure/context/solo_lectura.py`,
`src/infrastructure/context/contexto_tenant.py`,
`src/infrastructure/context/contexto_actor.py`

- `solo_lectura.py:40`: `"zeci_solo_lectura"` -> `"avedra_solo_lectura"`.
- `contexto_tenant.py:46`: `"zeci_institucion_actual"` -> `"avedra_institucion_actual"`.
- `contexto_actor.py:47`: `"zeci_actor_actual"` -> `"avedra_actor_actual"`.

**Verificacion:**
```
grep -rn "zeci" src/infrastructure/context/
```
Sin resultados.

---

## T3 — `AvedraModel` en `base.py`

**Artefacto:** `src/domain/models/base.py`

- Linea 2: docstring `ZECI Manager v2.0` -> `AVEDRA v2.0`.
- Linea 7: comentario `ZeciModel` -> `AvedraModel`.
- Linea 33: `class ZeciModel(BaseModel):` -> `class AvedraModel(BaseModel):`.
- Linea 34: docstring `ZECI Manager` -> `AVEDRA`.
- Linea 43: `class EntidadDominio(ZeciModel):` -> `class EntidadDominio(AvedraModel):`.
- Linea 62: `class DTODominio(ZeciModel):` -> `class DTODominio(AvedraModel):`.
- Linea 163: `"ZeciModel"` -> `"AvedraModel"` en `__all__`.

**Verificacion:**
```
python -c "from src.domain.models.base import AvedraModel; print(AvedraModel)"
grep -n "Zeci" src/domain/models/base.py
```
Import exitoso, grep sin resultados.

---

## T4 — `AvedraError` en `exceptions.py`

**Artefacto:** `src/domain/exceptions.py`

- Linea 2: docstring `ZECI Manager` -> `AVEDRA`.
- Linea 7: comentario `ZeciError` -> `AvedraError`.
- Linea 47: `class ZeciError(Exception):` -> `class AvedraError(Exception):`.
- Linea 72: `class ReglaDeNegocioError(ZeciError, ValueError):` ->
  `class ReglaDeNegocioError(AvedraError, ValueError):`.
- Linea 77: `class NoEncontradoError(ZeciError, ValueError):` ->
  `class NoEncontradoError(AvedraError, ValueError):`.
- Linea 82: `class ConflictoError(ZeciError, ValueError):` ->
  `class ConflictoError(AvedraError, ValueError):`.
- Linea 87: `class PermisoDenegadoError(ZeciError, PermissionError):` ->
  `class PermisoDenegadoError(AvedraError, PermissionError):`.
- Linea 92: `class DependenciaNoDisponibleError(ZeciError, RuntimeError):` ->
  `class DependenciaNoDisponibleError(AvedraError, RuntimeError):`.

**Verificacion:**
```
python -c "from src.domain.exceptions import AvedraError; print(AvedraError)"
grep -n "Zeci" src/domain/exceptions.py
```
Import exitoso, grep sin resultados.

---

## T5 — Docstrings de modulo (lote)

**Artefactos:** ~35 archivos en `src/` (ver lista en design.md C4).

Patron unico: reemplazar `ZECI Manager v2.0` por `AVEDRA v2.0` y
`ZECI Manager` por `AVEDRA` en la primera linea del docstring de modulo.

Incluye la linea 2 del docstring de `src/infrastructure/db/seed.py`
(el docstring, NO los datos de seed).

**Verificacion:**
```
grep -rn "ZECI Manager" src/
grep -rn "ZECI" src/ --include="*.py" | grep -v seed.py
```
Ambos sin resultados.

---

## Cierre del paso

```
grep -rni "zeci" src/ --include="*.py" | grep -v seed.py
python -m ruff check src/ --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```
El grep solo retorna lineas de `seed.py`. Ruff verde.

**NOTA:** los tests estan rotos en este punto. Ejecutar rebrand_04_tests
inmediatamente despues.

Escribir el resumen en `progress/impl_rebrand_02_loggers_internos.md` y
devolver al leader solo esa referencia.
