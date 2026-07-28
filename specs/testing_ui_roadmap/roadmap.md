# testing_ui — Roadmap: testing y validación de UI

## Contexto (David, 2026-07-27)

Antes de los roadmaps de backend (SQLAlchemy, API, fork Vue) y comercialización,
David necesita una app funcional con UI moderna, limpia e intuitiva. El problema:
no tiene forma de validar la UI sin sus propios sesgos, ni de testear los flujos
de manera automática. Este roadmap se ejecuta **después de completar la
funcionalidad pendiente** (11 pasos restantes del step_list).

## Prerequisito

App completamente funcional (los 122 pasos del step_list en `done`).

---

## Fase 1 — Auditoría visual sin sesgo (0 código, 1–2 días)

Objetivo: obtener una evaluación honesta de la UI actual antes de escribir tests.

- **ui_01_auditoria_claude** — Arrancar la app y revisarla pantalla por pantalla
  en el browser (Claude Code). Checklist: consistencia visual, jerarquía de
  información, espaciado, contraste, estados vacíos, mensajes de error, navegación
  por rol.
  - *criterio_done*: lista de hallazgos priorizada en `progress/auditoria_ui.md`.
- **ui_02_lighthouse_axe** — Correr Lighthouse + axe DevTools en cada página
  principal. Detectar problemas de accesibilidad, contraste, performance.
  - *criterio_done*: score por página documentado; issues críticos listados.

## Fase 2 — Infraestructura de tests E2E (2–3 días)

Objetivo: Playwright funcionando contra la app con seed_demo.

- **ui_03_playwright_setup** — Instalar Playwright (`pip install pytest-playwright`,
  `playwright install chromium`). Crear `tests/e2e/conftest.py` que:
  (1) levanta la app con `seed_demo` en puerto de test,
  (2) configura browser Playwright,
  (3) provee fixtures de login por rol.
  - *criterio_done*: `pytest tests/e2e/ -v` ejecuta sin errores (aunque no haya tests aún).
- **ui_04_seed_demo** — Crear `seed_demo()` en `seed.py`: colegio ficticio creíble
  con ~300 estudiantes (Faker `es_CO`), 15 docentes, notas parciales, asistencia
  de 2 meses, observaciones de convivencia, alertas activas. Usuarios por rol
  (rector@demo, coordinador@demo, profesor@demo, director6a@demo).
  - *criterio_done*: `seed_demo` corre sin error; la app arranca con datos realistas.
  - *pista*: `pip install faker`; reusar estructura de `seed_dev` agregando volumen
    y variedad.

## Fase 3 — Tests E2E por flujo crítico (1–2 semanas)

Objetivo: cubrir los flujos que un usuario real hace a diario, organizados por rol.

### Navegación y auth
- **ui_05_login_roles** — Login correcto/incorrecto, redirección por rol, permisos
  de ruta (profesor no accede a /admin, etc.), logout.
  - *pista*: `page.goto()` + `expect(page).to_have_url()`.

### Flujo del profesor (el más crítico)
- **ui_06_asistencia_flow** — Login profesor → dashboard → asistencia → seleccionar
  grupo → pasar lista (marcar presente/ausente) → guardar → verificar toast +
  persistencia.
- **ui_07_convivencia_flow** — Registrar observación → seleccionar estudiante →
  escribir texto → categoría → guardar.
- **ui_08_notas_flow** — Abrir planilla → ingresar notas → guardar → verificar
  cálculo automático de promedio.

### Flujo del coordinador
- **ui_09_gestion_grupos** — Crear/editar grupo, asignar director de grupo.
- **ui_10_reportes** — Generar boletín de periodo, consolidado de notas,
  consolidado de asistencia.

### Flujo del director de grupo
- **ui_11_comportamiento_flow** — Registrar nota de comportamiento + concepto →
  generar reporte de periodo del grupo.

### Tests negativos y edge cases
- **ui_12_campos_vacios** — Intentar guardar formularios vacíos; verificar
  validaciones y mensajes de error.
- **ui_13_permisos_ui** — Verificar que botones/acciones que el rol no tiene
  no aparecen o están deshabilitados.
- **ui_14_responsive** — Verificar que las páginas principales no se rompen en
  viewport tablet (768px) y móvil (375px).
  - *pista*: `page.set_viewport_size({"width": 375, "height": 812})`.

## Fase 4 — Tests automatizados de accesibilidad (2–3 días)

Objetivo: cada página pasa axe-core automáticamente.

- **ui_15_axe_playwright** — Integrar `axe-playwright-python` en el conftest.
  Fixture `check_a11y` que corre axe en la página actual.
  - *pista*: `pip install axe-playwright-python`.
- **ui_16_a11y_por_pagina** — Test parametrizado que recorre todas las rutas
  principales y verifica `violations_count == 0`.
  - *criterio_done*: 0 violaciones críticas; las menores documentadas como issues.

## Fase 5 — Validación sin sesgo con personas (paralelo, 0 código)

Objetivo: feedback real de usuarios que no sean David.

- **ui_17_test_de_usabilidad** — Reclutar 3–5 personas (profesor, coordinador,
  alguien fuera del sector). Darles una tarea ("registra la asistencia de 6A")
  y observar sin intervenir. Registrar: dónde dudan, dónde hacen clic mal, qué
  preguntan.
  - *criterio_done*: lista de problemas de usabilidad priorizada.
  - *pista*: puede ser remoto (compartir pantalla por Meet) o presencial con el
    .exe. No necesitas herramientas especiales — solo observar y anotar.
- **ui_18_clarity_hotjar** — Instalar Microsoft Clarity (gratis, 1 script tag)
  en la versión desplegada. Graba sesiones reales y genera mapas de calor.
  - *pista*: Clarity requiere un `<script>` en el HTML. En NiceGUI: `app.add_static_files`
    o `ui.add_head_html()` con el snippet.

## Fase 6 — Regresión visual (opcional, 1–2 días)

Objetivo: detectar cambios visuales no intencionados entre commits.

- **ui_19_screenshots_baseline** — Playwright toma screenshot de cada página
  principal con datos del seed_demo. Se guardan como baseline.
  - *pista*: `expect(page).to_have_screenshot(name="dashboard.png")`.
- **ui_20_visual_regression_ci** — En cada PR, comparar screenshots actuales
  vs. baseline. Diferencia > threshold = fallo.
  - *pista*: Playwright tiene comparación de screenshots integrada con
    `max_diff_pixel_ratio`.

---

## Estimación

| Fase | Esfuerzo | Prerequisito |
|---|---|---|
| 1 — Auditoría visual | 1–2 días | App funcional |
| 2 — Infraestructura E2E | 2–3 días | Fase 1 (para saber qué testear) |
| 3 — Tests E2E por flujo | 1–2 semanas | Fase 2 |
| 4 — Tests accesibilidad | 2–3 días | Fase 2 |
| 5 — Validación con personas | paralelo, 0 código | App funcional |
| 6 — Regresión visual | 1–2 días (opcional) | Fase 3 |
| **Total** | **~3–4 semanas** | |

## Secuencia

```
[App completa] → [F1 Auditoría] → [F2 Infra E2E] → [F3 Tests flujo] → [F6 Visual]
                                          ↑                    ↑
                                    [F4 Accesibilidad]   [F5 Personas]
                                    (paralelo a F3)      (paralelo, sin código)
```

## Cuándo arrancar

Después de los 11 pasos pendientes del step_list. La Fase 1 (auditoría visual)
se puede hacer en cuanto la app esté completa — es solo mirar y anotar. La Fase 5
(personas) se puede hacer incluso antes si la app es usable en su estado actual.
