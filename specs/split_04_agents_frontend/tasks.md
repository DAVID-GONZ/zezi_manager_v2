# split_04_agents_frontend — Tareas

Scope: `.claude/` y `CLAUDE.md` en avedra-frontend.
Fuente de contenido: `repo_split_00_pasos.md` secciones 5.2-5.4.

---

## T1 — leader.md del frontend

**Artefacto:** `.claude/agents/leader.md`

Incluir:
- Regla de contrato API (verificar endpoint existe antes de implementar).
- Skills de diseno disponibles (design-check, deslop-ui, a11y-check).
- Protocolo migrate-page para paginas legacy.
- Protocolo de arranque (npm run typecheck/lint/build).

---

## T2 — implementer.md del frontend

**Artefacto:** `.claude/agents/implementer.md`

Reglas duras:
- No fetch/axios directo (usar cliente generado src/api/generated.ts).
- No hardcodear URLs (usar VITE_API_URL).
- No duplicar tipos del contrato generado.
- Clases CSS solo de CLASS_CONTRACT. Tokens solo de tokens.css.
- Leer vue-patterns.md antes de crear componente.
- Leer composable-catalog.md antes de crear composable.

---

## T3 — reviewer.md del frontend

**Artefacto:** `.claude/agents/reviewer.md`

Checklist funcional:
1. TypeScript strict sin errores
2. ESLint limpio
3. Tests unitarios pasan
4. Puerta de imports (cliente generado, no fetch directo)

Puerta anti AI-slop (7 categorias de seccion 5.4):
1. Over-commenting
2. Abstracciones prematuras
3. Nombres grandilocuentes
4. Codigo defensivo injustificado
5. Inflacion estructural
6. Verbosidad sintactica
7. Testing slop

---

## T4 — spec_author.md del frontend

**Artefacto:** `.claude/agents/spec_author.md`

Formato: requirements.md + design.md + tasks.md.
Adaptado a Vue/TypeScript.

---

## T5 — design_reviewer.md

**Artefacto:** `.claude/agents/design_reviewer.md`

Contenido de seccion 5.2.3. Protocolo:
1. Leer componente/vista
2. Leer design-system-rules.md
3. Ejecutar design-check, deslop-ui, a11y-check
4. Emitir veredicto (0 rojos, <=3 amarillos)

---

## T6 — Skill /design-check

**Artefacto:** `.claude/commands/design-check.md`

Contenido de seccion 5.2.1 (7 puntos: jerarquia visual, spacing,
tipografia, color, layout, estados, densidad).

---

## T7 — Skill /deslop-ui

**Artefacto:** `.claude/commands/deslop-ui.md`

Contenido de seccion 5.2.1 (8 patrones AI-slop en UI).

---

## T8 — Skill /component-audit

**Artefacto:** `.claude/commands/component-audit.md`

Contenido de seccion 5.2.1 (9 verificaciones contra design system).

---

## T9 — Skill /a11y-check

**Artefacto:** `.claude/commands/a11y-check.md`

Contenido de seccion 5.2.1 (9 verificaciones WCAG 2.2 AA).

---

## T10 — Skill /migrate-page

**Artefacto:** `.claude/commands/migrate-page.md`

Contenido de seccion 5.2.1 (7 pasos del flujo legacy-to-Vue).

---

## T11 — Referencia vue-patterns.md

**Artefacto:** `.claude/references/vue-patterns.md`

Contenido de seccion 5.2.2 (estructura SFC, composables, anti-patrones).

---

## T12 — Referencia composable-catalog.md

**Artefacto:** `.claude/references/composable-catalog.md`

Contenido de seccion 5.2.2 (composables del proyecto + VueUse).

---

## T13 — Referencia design-system-rules.md

**Artefacto:** `.claude/references/design-system-rules.md`

Contenido de seccion 5.2.2 (tokens, CLASS_CONTRACT, reglas visuales,
librerias aprobadas: Radix Vue, Iconify, Floating UI, Chart.js/ECharts).

---

## T14 — settings.json

**Artefacto:** `.claude/settings.json`

Configuracion base de Claude Code para el repo frontend.

---

## T15 — CLAUDE.md del frontend

**Artefacto:** `CLAUDE.md`

Instrucciones raiz adaptadas a Vue/TypeScript:
- Rol leader obligatorio.
- Reglas de design system (tokens, CLASS_CONTRACT).
- Regla de contrato API.
- Skills disponibles.
- Regla anti AI-slop.
- Equivalente de init.py: npm run typecheck && lint && build.

---

## Cierre del paso

Verificar que los 17 archivos existen:
```bash
ls .claude/agents/leader.md .claude/agents/implementer.md \
   .claude/agents/reviewer.md .claude/agents/spec_author.md \
   .claude/agents/design_reviewer.md
ls .claude/commands/design-check.md .claude/commands/deslop-ui.md \
   .claude/commands/component-audit.md .claude/commands/a11y-check.md \
   .claude/commands/migrate-page.md
ls .claude/references/vue-patterns.md .claude/references/composable-catalog.md \
   .claude/references/design-system-rules.md
ls .claude/settings.json CLAUDE.md
```

Escribir resumen en `progress/impl_split_04_agents_frontend.md` y
devolver al leader solo esa referencia.
