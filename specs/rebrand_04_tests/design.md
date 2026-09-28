# rebrand_04_tests — Diseno

## Archivos afectados (12 archivos)

### Imports y clases renombradas

| Archivo | Cambio |
|---|---|
| `tests/unit/domain/test_model_config.py` | `ZeciModel` -> `AvedraModel` (~20 ocurrencias): imports, asserts, nombres de test, constante `_EXCEPCIONES_ZECIMODEL` -> `_EXCEPCIONES_AVEDRAMODEL`, docstrings, mensajes de error. |
| `tests/unit/domain/test_exceptions.py` | `ZeciError` -> `AvedraError` (~15 ocurrencias): import, nombres de test (`test_todas_las_familias_son_zeci_error` -> `test_todas_las_familias_son_avedra_error`, `test_zecierror_no_es_value_error` -> `test_avedraerror_no_es_value_error`), asserts, docstrings. |

### Logger `avedra.security`

| Archivo | Cambio |
|---|---|
| `tests/unit/infrastructure/test_auditoria_repo.py:177,181` | `logging.getLogger("zeci.security")` -> `logging.getLogger("avedra.security")` |
| `tests/unit/infrastructure/test_security_logger.py:41,170` | `name="zeci.security"` -> `name="avedra.security"`, docstring |
| `tests/unit/domain/test_alerta_ip.py:6` | Docstring `zeci.security` -> `avedra.security` |

### Datos de fixtures

| Archivo | Cambio |
|---|---|
| `tests/unit/domain/test_configuracion_usuario_auditoria.py:51,144` | `@zeci.edu.co` -> `@avedra.edu.co` |
| `tests/unit/infrastructure/test_exporters.py:273,277` | `"INSTITUCION EDUCATIVA ZECI"` -> nombre coherente con seed |
| `tests/unit/infrastructure/exporters/test_observador_pdf.py:21` | `"IE ZECI"` -> `"IE Demo"` |
| `tests/integration/test_institucion_repo.py:32` | `"Institucion Educativa ZECI"` -> `"Institucion Educativa Demo"` |
| `tests/unit/services/test_convivencia_service.py:733` | Comentario `ZECI` -> `AVEDRA` |

### Entrypoint E2E

| Archivo | Cambio |
|---|---|
| `tests/e2e/e2e_app.py:25` | `ZECI_E2E_DB` -> `AVEDRA_E2E_DB`, `zeci_e2e.db` -> `avedra_e2e.db` |
| `tests/e2e/e2e_app.py:53,55` | `ZECI_E2E_SEEDED` -> `AVEDRA_E2E_SEEDED` |

### Docstring de conftest

| Archivo | Cambio |
|---|---|
| `tests/conftest.py:2` | `ZECI Manager v2.0` -> `AVEDRA v2.0` |

## Riesgo

Bajo. Son cambios de string e import. La suite debe quedar verde
inmediatamente despues. Si algun test falla, es porque se omitio un
renombrado en src/ (Paso 2) o un dato de fixture.
