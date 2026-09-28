# rebrand_00 — Renombrado de marca: ZECI Manager a AVEDRA

> Fecha: 2026-09-28
> AVEDRA = Administracion y Visualizacion Educativa para la Direccion y el Registro Academico

---

## Alcance del cambio

| Elemento | Antes | Despues |
|---|---|---|
| Nombre de producto | ZECI Manager | AVEDRA |
| Repo backend | zeci-backend | avedra-backend |
| Repo frontend | zeci-frontend | avedra-frontend |
| Repo contratos | zeci-shared-contracts | avedra-shared-contracts |
| Repo legado | zeci-legacy-nicegui | avedra-legacy-nicegui |
| Repo actual | zeci_manager_v2 | avedra (al hacer el split) |
| OpenAPI spec | zeci-openapi.yaml | avedra-openapi.yaml |
| Paquete Android | com.zeci.app | com.avedra.app |
| Design system | Aula Serena | Aula Serena (NO cambia) |

**No cambia:**
- El nombre del design system "Aula Serena" (es identidad visual, no marca de producto)
- La estructura de carpetas src/domain/, src/services/, etc.
- Los nombres de clases Python (no se llaman ZeciService ni similar)

---

## Inventario de archivos afectados

### Codigo fuente (src/) — 100 ocurrencias en 60 archivos

| Patron | Archivos | Tipo de cambio |
|---|---|---|
| Titulos de UI | login.py, theme.py, e2e_app.py | String visible al usuario |
| Nombres de logger | security_logger.py, 15+ repos | logging.getLogger |
| Docstrings y comentarios | models, config, exceptions | Documentacion interna |
| Seed data | seed.py (22 ocurrencias) | Datos de ejemplo |
| Exporters | observador_pdf.py, observador_excel.py | Titulos de documentos |
| Tests | 10+ archivos de test | Assertions y fixtures |

### Configuracion raiz — 5 archivos

config.py (3), container.py (1), main.py (1), pyproject.toml, CLAUDE.md (1)

### Documentacion (docs/) — 30 ocurrencias en 12 archivos

### Specs — 20 ocurrencias en 10+ archivos

### Roadmaps — 184 ocurrencias en 7 archivos (se actualizan en Paso 0)

### Agentes Claude — leader.md (4), CLAUDE.md (1)

---

## Pasos de ejecucion

### Paso 0 — Roadmaps, docs de proceso, agentes (sin implementer)

Archivos fuera de src/ que el leader edita directamente.
Incluye: roadmaps, CLAUDE.md, .claude/agents/, docs/, specs/

Criterio: grep -ri "zeci" en archivos fuera de src/ retorna 0.

### Paso 1 — Strings visibles al usuario (implementer)

config.py, main.py, login.py, theme.py, exporters.
Criterio: la app muestra AVEDRA en login, barra de titulo, exports.

### Paso 2 — Loggers y strings internos (implementer)

Patron: logging.getLogger("zeci.*") a logging.getLogger("avedra.*")
60+ archivos en infrastructure/, domain/, context/.
Criterio: grep -r "zeci" src/ solo retorna seed.py.

### Paso 3 — Seed data (implementer)

seed.py (22 ocurrencias). Datos de ejemplo.
No afecta bases existentes, solo bases nuevas.
Criterio: grep -ri "zeci" src/ retorna 0.

### Paso 4 — Tests (implementer)

12 archivos de test. Assertions, fixtures, nombres.
Criterio: grep -ri "zeci" tests/ retorna 0. Suite verde.

### Paso 5 — pyproject.toml (implementer)

Metadata del paquete: name = "avedra".

### Paso 6 — Repos en GitHub (post-split)

Se absorbe en repo_split_00_pasos.md.
Usar nombres avedra-* al crear los repos nuevos.

---

## Orden y estimacion

```
Paso 0 (hoy)     -- roadmaps, docs, specs, .claude
Paso 1 (1 hora)  -- strings visibles al usuario
Paso 2 (2 horas) -- loggers y strings internos
Paso 3 (30 min)  -- seed data
Paso 4 (1 hora)  -- tests
Paso 5 (10 min)  -- pyproject.toml
Total: aprox 1 dia de trabajo
Paso 6 (split)   -- repos en GitHub, junto con repo_split_00
```

## Regla de transicion

- **Codigo nuevo:** siempre AVEDRA / avedra
- **Codigo existente:** se renombra en commit aislado, no mezclado con trabajo funcional
- **Git:** el historial conserva las referencias antiguas (no se reescribe)
- **Comunicacion:** desde hoy se usa AVEDRA

## Verificacion final

```bash
grep -ri "zeci" src/ tests/ docs/ specs/ roadmaps/ .claude/ CLAUDE.md config.py main.py container.py pyproject.toml
# Debe retornar 0 resultados
```
