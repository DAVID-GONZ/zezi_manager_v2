# rebrand_04_tests — Tareas

Scope: solo archivos en `tests/` y `tests/conftest.py`.
Cualquier otro archivo -> PARAR y reportar al leader.

---

## T1 — `AvedraModel` en `test_model_config.py`

**Artefacto:** `tests/unit/domain/test_model_config.py`

- Reemplazar `ZeciModel` por `AvedraModel` en todo el archivo (~20 ocurrencias):
  imports, constantes, nombres de test, asserts, docstrings, mensajes de error.
- Renombrar constante `_EXCEPCIONES_ZECIMODEL` -> `_EXCEPCIONES_AVEDRAMODEL`.

**Verificacion:**
```
grep -c "Zeci" tests/unit/domain/test_model_config.py
```
Debe dar `0`.

---

## T2 — `AvedraError` en `test_exceptions.py`

**Artefacto:** `tests/unit/domain/test_exceptions.py`

- Reemplazar `ZeciError` por `AvedraError` en todo el archivo (~15 ocurrencias):
  import, nombres de test, asserts, docstrings.
- Renombrar `test_todas_las_familias_son_zeci_error` ->
  `test_todas_las_familias_son_avedra_error`.
- Renombrar `test_zecierror_no_es_value_error` ->
  `test_avedraerror_no_es_value_error`.
- Renombrar `test_zecierror_lanzados_usan_codigoerror` ->
  `test_avedraerror_lanzados_usan_codigoerror`.

**Verificacion:**
```
grep -c "Zeci" tests/unit/domain/test_exceptions.py
```
Debe dar `0`.

---

## T3 — Logger `avedra.security` en tests

**Artefactos:** `tests/unit/infrastructure/test_auditoria_repo.py`,
`tests/unit/infrastructure/test_security_logger.py`,
`tests/unit/domain/test_alerta_ip.py`

- `test_auditoria_repo.py:177,181`: `"zeci.security"` -> `"avedra.security"`.
- `test_security_logger.py:41`: `name="zeci.security"` -> `name="avedra.security"`.
- `test_security_logger.py:170`: docstring `zeci.security` -> `avedra.security`.
- `test_alerta_ip.py:6`: docstring `zeci.security` -> `avedra.security`.

**Verificacion:**
```
grep -rn "zeci" tests/unit/infrastructure/test_auditoria_repo.py tests/unit/infrastructure/test_security_logger.py tests/unit/domain/test_alerta_ip.py
```
Sin resultados.

---

## T4 — Datos de fixtures

**Artefactos:** `tests/unit/domain/test_configuracion_usuario_auditoria.py`,
`tests/unit/infrastructure/test_exporters.py`,
`tests/unit/infrastructure/exporters/test_observador_pdf.py`,
`tests/integration/test_institucion_repo.py`,
`tests/unit/services/test_convivencia_service.py`

- `test_configuracion_usuario_auditoria.py:51,144`:
  `@zeci.edu.co` -> `@avedra.edu.co`.
- `test_exporters.py:273`: `inst_nombre="INSTITUCION EDUCATIVA ZECI"` ->
  `inst_nombre="INSTITUCION EDUCATIVA DEMO"`.
- `test_exporters.py:277`: assert `"INSTITUCION EDUCATIVA ZECI"` ->
  `"INSTITUCION EDUCATIVA DEMO"`.
- `test_observador_pdf.py:21`: `"IE ZECI"` -> `"IE Demo"`.
- `test_institucion_repo.py:32`: `"Institucion Educativa ZECI"` ->
  `"Institucion Educativa Demo"`.
- `test_convivencia_service.py:733`: comentario `ZECI` -> `AVEDRA`.

**Verificacion:**
```
grep -rn "ZECI\|zeci" tests/unit/domain/test_configuracion_usuario_auditoria.py tests/unit/infrastructure/test_exporters.py tests/unit/infrastructure/exporters/test_observador_pdf.py tests/integration/test_institucion_repo.py tests/unit/services/test_convivencia_service.py
```
Sin resultados.

---

## T5 — Entrypoint E2E

**Artefacto:** `tests/e2e/e2e_app.py`

- Linea 25: `ZECI_E2E_DB` -> `AVEDRA_E2E_DB`, `zeci_e2e.db` -> `avedra_e2e.db`.
- Linea 53: `ZECI_E2E_SEEDED` -> `AVEDRA_E2E_SEEDED`.
- Linea 55: `ZECI_E2E_SEEDED` -> `AVEDRA_E2E_SEEDED`.

---

## T6 — Docstring de `conftest.py`

**Artefacto:** `tests/conftest.py`

- Linea 2: `ZECI Manager v2.0` -> `AVEDRA v2.0`.

---

## Cierre del paso

```
grep -rni "zeci" tests/ --include="*.py"
python -m pytest tests/unit/ -x -q --timeout=30
python -m ruff check tests/ --select F821,F811,F632,F702,B006,B008,B023,E9 --output-format concise
```
Grep sin resultados. Tests y ruff verdes.

Escribir el resumen en `progress/impl_rebrand_04_tests.md` y
devolver al leader solo esa referencia.
