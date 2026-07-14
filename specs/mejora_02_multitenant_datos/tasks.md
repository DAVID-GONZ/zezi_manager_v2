# Tasks: Aislamiento multi-tenant en datos (mejora_02_multitenant_datos)

> ⚠️ **NO ejecutar sin aprobación del rumbo multi-tenant (David).**
> Migración por tabla raíz, una a la vez, con tests de aislamiento y suite verde
> entre cada una.

- [ ] T1: Auditar `src/infrastructure/db/schema.py` y listar las tablas académicas
      raíz que necesitan `institucion_id` (vs. las que lo heredan por FK). Documentar
      el plan de columnas en este spec (design.md §1) antes de tocar código.
  Verifica: `python -c "print('plan de columnas confirmado')"` (revisión manual)
  Produce: lista definitiva de tablas a alterar

- [ ] T2: Añadir la migración de schema (ALTER + backfill a institución #1) para la
      primera tabla raíz (`grupos`), idempotente.
  Verifica: `python -m pytest tests/integration/ -q`
  Produce: columna `grupos.institucion_id` + backfill; integración verde

- [ ] T3: Hacer tenant-aware el repo y el servicio de grupos (listado con scope +
      `verificar_pertenencia` en get-by-id) con tests de aislamiento entre dos
      instituciones.
  Verifica: `python -m pytest tests/unit/services/ tests/integration/ -q`
  Produce: repo/servicio de grupos scopeados + test de aislamiento verde

- [ ] T4: Repetir T2–T3 para `estudiantes`.
  Verifica: `python -m pytest tests/unit/services/ tests/integration/ -q`
  Produce: estudiantes scopeados + test de aislamiento

- [ ] T5: Repetir T2–T3 para `asignaciones` y la configuración/años.
  Verifica: `python -m pytest tests/unit/services/ tests/integration/ -q`
  Produce: asignaciones y config/años scopeados + tests de aislamiento

- [ ] T6: Ajustar el seed (`seed_base`/`seed_dev`) para crear registros con
      `institucion_id` correcto usando `usar_institucion(id)`.
  Verifica: `python -m pytest tests/integration/ -q`
  Produce: seed tenant-aware

- [ ] T7: Verificar entorno completo y aislamiento global.
  Verifica: `python init.py`
  Produce: suite completa verde, incluyendo aislamiento entre instituciones
