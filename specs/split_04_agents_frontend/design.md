# split_04_agents_frontend — Diseno

## Estructura de archivos

```
avedra-frontend/.claude/
├── agents/
│   ├── leader.md
│   ├── implementer.md
│   ├── reviewer.md
│   ├── spec_author.md
│   └── design_reviewer.md
├── commands/
│   ├── design-check.md
│   ├── deslop-ui.md
│   ├── component-audit.md
│   ├── a11y-check.md
│   └── migrate-page.md
├── references/
│   ├── vue-patterns.md
│   ├── composable-catalog.md
│   └── design-system-rules.md
└── settings.json
```

Total: **17 archivos** (5 agents, 5 skills, 3 references, 1 settings, 1 CLAUDE.md,
mas los directorios).

## Contenido fuente

Todo el contenido detallado de estos archivos esta en `repo_split_00_pasos.md`:
- Skills: secciones 5.2.1 (design-check, deslop-ui, component-audit, a11y-check, migrate-page)
- Referencias: seccion 5.2.2 (vue-patterns, composable-catalog, design-system-rules)
- Design reviewer: seccion 5.2.3
- Protocolo legacy-to-Vue: seccion 5.3
- Anti AI-slop: seccion 5.4

El implementer copia y adapta de ahi, no re-inventa.

## Diferencias con agentes del backend

| Aspecto | Backend | Frontend |
|---|---|---|
| Lenguaje | Python | TypeScript / Vue SFC |
| Scope implementer | src/ + app/ | src/ (Vue) |
| Reglas de design | No | Si: tokens.css, CLASS_CONTRACT |
| Reviewer valida | API contracts, ruff | TypeScript strict, ESLint, axe a11y |
| Design reviewer | No existe | Si |
| Skills | No | 5 skills invocables |
| Referencias | No | 3 archivos de patrones |
| init.py equivalente | python init.py | npm run typecheck && npm run lint && npm run build |

## Reglas anti AI-slop

Se incrustan en `reviewer.md` como puerta obligatoria post-review funcional.
7 categorias, cada una con ejemplos concretos. Ver seccion 5.4 de
repo_split_00_pasos.md para el contenido completo.

Severidad:
- Patrones 1-3 (over-commenting, abstracciones, nombres): bloquean merge
- Patrones 4-7 (defensivo, inflacion, verbosidad, testing): merge con
  compromiso de limpiar en el mismo PR

## migrate-page.md — Flujo critico

Este skill es el puente entre legacy y Vue. Obliga al implementer a:
1. Leer la pagina NiceGUI equivalente
2. Extraer estructura, campos, permisos, flujos
3. Escribir referencia en docs/migration-refs/
4. Verificar endpoints en contrato API
5. Generar scaffold Vue
6. Ejecutar /design-check y /a11y-check

Sin esta disciplina, las paginas Vue se reinventan desde cero y pierden
paridad con lo ya validado en NiceGUI.
