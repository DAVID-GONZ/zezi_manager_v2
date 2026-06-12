# paso_14d_docente_view — tasks

Scope: `src/interface/pages/academico/horarios.py`,
`src/interface/design/styles/domain/` (si requiere clases CSS para el toggle/día),
`tests/unit/interface/`.

---

### T1 — Bifurcación por rol y estado docente
Aislar la rama docente con su `_s` (vista_grid, dia_sel, mes_sel, anio_cal,
clases_mes). Conservar la rama de gestión actual para los otros roles.
**Verif:** la página carga como docente sin selectores de grupo/docente.

### T2 — Alternancia semana/día
Toggle que conmuta `vista_grid`; vista semanal reusa `_build_grilla`; vista
diaria lista los bloques de `dia_sel`. Selector de día con default hoy/lunes.
**Verif:** smoke: alternar muestra cada vista; cambiar día refiltra.

### T3 — Tarjeta de clases del mes
`stat_card` con `contar_clases_mes` + selector de mes/año que recalcula.
**Verif:** smoke: el número coincide con los registros del seed; mes vacío → 0.

### T4 — Estado vacío y limpieza de design system
`empty_state` sin CTA cuando no hay escenario activo o sin bloques. Sin
`ui.button().props()` ni `style=` estático.
**Verif:** `python scripts/check_design.py --file src/interface/pages/academico/horarios.py`

### T5 — Verificación integral
**Verif:** `python init.py` exit 0; `python -m pytest tests/ -q` sin regresiones.

Al terminar: `step_list.json` → `spec_ready`.
