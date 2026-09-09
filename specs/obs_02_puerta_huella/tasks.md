# Tasks: Puerta de huella (obs_02_puerta_huella)

- [ ] T1: Crear `scripts/check_auditoria.py` con el inventario AST de escrituras por
      repositorio, el recorrido de servicios y el bloque «Consola UTF-8» de
      `check_design.py`.
  Verifica: `python scripts/check_auditoria.py`
  Produce: `scripts/check_auditoria.py`

- [ ] T2: Añadir `SERVICIOS_SIN_HUELLA_DEUDA` con el inventario real y la doble regla:
      falla si crece y falla si contiene una entrada que ya tiene huella.
  Verifica: `python scripts/check_auditoria.py`
  Produce: exit code 0 con la deuda declarada

- [ ] T3: Test que replica la puerta como subproceso (patrón de
      `tests/unit/domain/test_enums_schema.py`) y comprueba que detecta un mutador sin
      huella introducido a propósito.
  Verifica: `python -m pytest tests/unit/test_check_auditoria.py -q`
  Produce: `tests/unit/test_check_auditoria.py` verde

- [ ] T4: Test de integración que ejercita una escritura por servicio cubierto y afirma
      que `audit_log` crece con usuario e institución no nulos.
  Verifica: `python -m pytest tests/integration/test_huella_cobertura.py -q`
  Produce: `tests/integration/test_huella_cobertura.py` verde

- [ ] T5: Encadenar `check_auditoria` a `scripts/init.py` con el mismo contrato que
      `check_enums`.
  Verifica: `python scripts/init.py`
  Produce: `scripts/init.py` modificado, todos los checks verdes
