# split_03_agents_backend — Tareas

Scope: `.claude/` y `CLAUDE.md` en avedra-backend, `CLAUDE.md` en
avedra-shared-contracts, `scripts/generar_estructura.py` en avedra-backend.

---

## T1 — leader.md del backend

**Artefacto:** `avedra-backend/.claude/agents/leader.md`

Adaptar del leader.md actual:
- Eliminar reglas de design system (tokens, check_design, audit_design).
- Agregar regla de contrato API (regenerar OpenAPI, anotar CONTRACT_CHANGED).
- Mantener protocolo de arranque (init.py, step_list, progress/current.md).
- Mantener regla de subagentes (implementer escribe, reviewer verifica).

---

## T2 — implementer.md del backend

**Artefacto:** `avedra-backend/.claude/agents/implementer.md`

Scope: `src/` (sin interface/), `app/`, `tests/`, `scripts/`.
Reglas duras: model_dump(), no src.db fuera de infrastructure, no repos
fuera de container.py. Sin reglas de CSS.

---

## T3 — reviewer.md del backend

**Artefacto:** `avedra-backend/.claude/agents/reviewer.md`

Checklist:
1. Correcccion funcional
2. Puerta de imports
3. Puerta anti AI-slop (7 categorias de repo_split_00_pasos.md seccion 5.4)
4. Validacion de contrato API
5. ruff limpio

---

## T4 — spec_author.md del backend

**Artefacto:** `avedra-backend/.claude/agents/spec_author.md`

Mismo formato que el actual (requirements.md + design.md + tasks.md),
adaptado al scope del backend.

---

## T5 — settings.json

**Artefacto:** `avedra-backend/.claude/settings.json`

Configuracion base de Claude Code para el repo.

---

## T6 — CLAUDE.md del backend

**Artefacto:** `avedra-backend/CLAUDE.md`

Instrucciones raiz. Adaptar del CLAUDE.md actual:
- Rol leader obligatorio.
- Reglas duras (sin las de design system).
- Regla de contrato API.
- Protocolo de arranque (init.py, step_list, progress).
- Regla anti AI-slop en reviewer.

---

## T7 — Adaptar generar_estructura.py

**Artefacto:** `avedra-backend/scripts/generar_estructura.py`

- Eliminar NOISE_DIRS de roadmaps/specs/progress.
- Agregar `app/` al scope del arbol.
- Simplificar NOISE_DIRS a `logs/`.
- Mantener bloque consola UTF-8.
- Mantener CACHE_DIRS.

**Verificacion:**
```bash
python scripts/generar_estructura.py
cat docs/estructura_proyecto.md | head -20  # debe incluir app/
```

---

## T8 — CLAUDE.md de shared-contracts

**Artefacto:** `avedra-shared-contracts/CLAUDE.md`

Contenido de repo_split_00_pasos.md seccion 5.5:
- Repo de solo lectura.
- Nunca editar OpenAPI/DTOs a mano.
- Flujo: backend genera -> contracts recibe -> frontend regenera.

---

## Cierre del paso

Verificar que todos los archivos existen y son coherentes entre si.
```bash
ls avedra-backend/.claude/agents/leader.md
ls avedra-backend/.claude/agents/implementer.md
ls avedra-backend/.claude/agents/reviewer.md
ls avedra-backend/.claude/agents/spec_author.md
ls avedra-backend/.claude/settings.json
ls avedra-backend/CLAUDE.md
ls avedra-shared-contracts/CLAUDE.md
```

Escribir resumen en `progress/impl_split_03_agents_backend.md` y
devolver al leader solo esa referencia.
