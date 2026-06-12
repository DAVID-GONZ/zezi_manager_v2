# paso_14e_gestor_escenarios — tasks

Scope: `src/interface/pages/academico/horarios.py`,
`src/interface/design/styles/domain/` (si requiere CSS de panel/grilla),
`tests/unit/interface/`.

---

### T1 — Panel de escenarios
Listar escenarios del año con badge de activo; botones Crear/Activar/Renombrar/
Duplicar/Eliminar con `form_dialog`/`confirm_dialog`/acciones directas.
**Verif:** smoke: crear, renombrar, duplicar, eliminar y activar escenarios.

### T2 — Activación con exclusión mutua
Activar un escenario desactiva el anterior (vía servicio); el badge se mueve.
**Verif:** smoke: tras activar B, A deja de mostrar "Activo".

### T3 — Grilla de edición por escenario y grupo
Selector de grupo + `listar_horario_grupo_escenario`; celdas con editar/eliminar,
celdas vacías con crear. `empty_state` con CTA si el escenario no tiene bloques.
**Verif:** smoke: la grilla refleja el escenario seleccionado, no solo el activo.

### T4 — Diálogo de bloque con validaciones y cupo
`form_dialog` (asignación activa, día, horas, sala) → `horario_service`. Captura
`ValueError` y muestra el motivo. Mostrar disponibilidad de materia y docente.
**Verif:** smoke: cruce y exceso de tope son rechazados con mensaje; alta válida
persiste.

### T5 — Limpieza design system
Sin `ui.button().props()` ni `style=` estático; uso de `btn_*`, `toast_*`.
**Verif:** `python scripts/check_design.py --file src/interface/pages/academico/horarios.py`

### T6 — Verificación integral
**Verif:** `python init.py` exit 0; `python -m pytest tests/ -q` sin regresiones.

Al terminar: `step_list.json` → `spec_ready`.
