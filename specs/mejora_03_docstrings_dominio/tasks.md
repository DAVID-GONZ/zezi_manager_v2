# Tasks: Docstrings de modelos de dominio (mejora_03_docstrings_dominio)

> Solo se insertan docstrings. Trabajar por módulo, de mayor a menor densidad de
> lógica, regenerando la referencia para medir el avance.

- [x] T1: Backfill de docstrings en los módulos de mayor lógica de negocio:
      `evaluacion.py`, `cierre.py`, `configuracion.py`, `habilitacion.py`,
      `infraestructura.py`.
  Verifica: `python tools/gen_api_reference.py` && `python -m pytest tests/unit/domain/ -q`
  Produce: docstrings añadidos; cobertura de esos módulos ≥ 85%

- [x] T2: Backfill en el resto de módulos con lógica (`asistencia.py`,
      `convivencia.py`, `nivelacion.py`, `plan_mejoramiento.py`, `periodo.py`,
      `estudiante.py`, `usuario.py`, `auditoria.py`, `asignacion.py`).
  Verifica: `python tools/gen_api_reference.py` && `python -m pytest tests/unit/domain/ -q`
  Produce: docstrings añadidos en esos módulos

- [x] T3: Backfill en los módulos restantes (`acudiente.py`, `alerta.py`,
      `institucion.py`, `piar.py`, `dtos.py`) hasta alcanzar la meta global.
  Verifica: `python tools/gen_api_reference.py`
  Produce: cobertura global de `dominio_modelos.md` ≥ 85%

- [x] T4: Verificar entorno completo.
  Verifica: `python init.py`
  Produce: todos los checks verdes; sin cambios de lógica en `git diff src/domain/models/`
