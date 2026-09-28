# split_04_agents_frontend — Requisitos

## Contexto

Fase 5.2-5.4 del repo split. Crear los agentes Claude, skills, referencias y
reglas anti AI-slop para `avedra-frontend`.

**Repo destino:** `avedra-frontend`.

## Requisitos (EARS)

### Agentes

**R1** — Existe `.claude/agents/` con: `leader.md`, `implementer.md`,
`reviewer.md`, `spec_author.md`, `design_reviewer.md`.

**R2** — `leader.md` incluye: regla de contrato API (verificar endpoint
antes de implementar), skills de diseno disponibles, protocolo de migracion
legacy-to-Vue.

**R3** — `implementer.md` tiene reglas: no fetch/axios directo (usar cliente
generado), no hardcodear URLs, clases CSS solo de CLASS_CONTRACT, leer
vue-patterns.md y composable-catalog.md antes de crear componente/composable.

**R4** — `reviewer.md` incluye puerta anti AI-slop con las 7 categorias
(over-commenting, abstracciones prematuras, nombres grandilocuentes, codigo
defensivo injustificado, inflacion estructural, verbosidad sintactica,
testing slop).

**R5** — `design_reviewer.md` revisa calidad visual y UX, ejecuta los
checklists de design-check, deslop-ui y a11y-check. Aprueba o rechaza.
Criterio: 0 hallazgos rojos, <= 3 amarillos con plan de correccion.

### Skills

**R6** — Existe `.claude/commands/` con 5 skills invocables:
- `design-check.md` — auditoria visual (7 puntos)
- `deslop-ui.md` — limpiar patrones AI en UI (8 patrones)
- `component-audit.md` — validar contra design system (9 verificaciones)
- `a11y-check.md` — accesibilidad WCAG 2.2 AA (9 verificaciones)
- `migrate-page.md` — flujo legacy-to-Vue (7 pasos)

### Referencias

**R7** — Existe `.claude/references/` con 3 archivos:
- `vue-patterns.md` — patrones y anti-patrones Vue
- `composable-catalog.md` — inventario de composables
- `design-system-rules.md` — reglas del design system para Vue

### Raiz

**R8** — Existe `CLAUDE.md` en la raiz del frontend adaptado al contexto
Vue/TypeScript.

## Fuera de alcance

- Agentes del backend (split_03).
- CI/CD (split_05).
- Implementacion de componentes Vue (va en el roadmap Vue).
