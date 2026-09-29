# Tareas: backend_18_css_desacoplado

> SCOPE — archivos que pueden editarse:
> `scripts/audit_css_portability.py` (crear),
> `docs/design_system/portability_audit.md` (crear),
> `docs/design_system/portability_test.html` (crear).
>
> Fuera de scope: archivos CSS (no se modifica el CSS, solo se audita).
>
> No depende de la API REST. Puede ejecutarse en paralelo con Fase 3.

---

## T1 — Script de auditoria CSS

Crear `scripts/audit_css_portability.py` que recorra `styles/`,
clasifique archivos, cuente lineas, extraiga selectores de framework
y cuente `!important`. Salida: markdown a stdout.

**Verificacion:** `python scripts/audit_css_portability.py` genera
informe con al menos 20 archivos clasificados.

---

## T2 — Generar informe

Ejecutar el script y guardarlo como
`docs/design_system/portability_audit.md`. Revisar y ajustar
la clasificacion manual si el script la hizo mal.

**Verificacion:** el informe tiene las secciones de D3 completas.

---

## T3 — Verificar frontera con check_design.py

Ejecutar `python scripts/check_design.py --all` y confirmar que
la regla N pasa. Si hay violaciones nuevas, documentarlas en el
informe.

---

## T4 — HTML de verificacion

Crear `docs/design_system/portability_test.html` segun D2.
Abrir en el navegador y verificar que los componentes se renderizan
correctamente sin NiceGUI.

**Verificacion visual:** badges, buttons, cards, alerts, page header
y layout se ven como en la app, con los colores del design system.

---

## T5 — Seccion de recomendaciones para Vue

Completar la seccion "Recomendaciones para Vue" del informe con:
- Lista de archivos que copiar tal cual al repo Vue.
- Lista de archivos que requieren reescritura y contra que.
- Lista de CSS muerto o innecesario.

---

## T6 — Cierre

El informe esta completo. El HTML de test renderiza los componentes.
La Fase 5 del design system portable esta cerrada.

**Artefacto:** `progress/impl_backend_18.md`.
