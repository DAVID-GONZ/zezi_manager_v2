# Tasks: Logging de seguridad estructurado (obs_03_security_logger)

- [ ] T1: Crear el puerto `ISecurityLogger` en `src/domain/ports/security_logger.py` con
      un método por familia de evento de R1 (login_exitoso, login_fallido, logout,
      acceso_denegado, ver_como, gestion_usuario).
  Verifica: `python -c "from src.domain.ports.security_logger import ISecurityLogger; print('ok')"`
  Produce: `src/domain/ports/security_logger.py`

- [ ] T2: Crear `src/infrastructure/logging/__init__.py` y
      `src/infrastructure/logging/security_logger.py` con logger dedicado `zeci.security`,
      formatter JSON, `RotatingFileHandler`, lista blanca `_CAMPOS_PERMITIDOS` y soporte
      `NullHandler` cuando `SECURITY_LOG_FILE` es `None`.
  Verifica: `python -m pytest tests/unit/infrastructure/test_security_logger.py -q`
  Produce: `src/infrastructure/logging/security_logger.py`

- [ ] T3: Test R7 — un login fallido con un password largo no deja el password en el log,
      ni completo ni en fragmentos (buscar en el JSON serializado).
  Verifica: `python -m pytest tests/unit/infrastructure/test_security_logger.py -q -k password`
  Produce: test verde dentro de `test_security_logger.py`

- [ ] T4: Añadir `SECURITY_LOG_FILE`, `SECURITY_LOG_MAX_BYTES` y
      `SECURITY_LOG_BACKUP_COUNT` a `config.py` con validador de ruta; documentarlos en
      `.env.example`; añadir `logs/` a `.gitignore`.
  Verifica: `python -m pytest tests/unit/ -q -k config`
  Produce: `config.py`, `.env.example`, `.gitignore` modificados

- [ ] T5: Crear `src/domain/policies/alerta_ip.py` (umbral y ventana por dirección de red)
      que emita `logger.warning` al superarse. Dominio puro, sin I/O.
  Verifica: `python -m pytest tests/unit/domain/test_alerta_ip.py -q`
  Produce: `src/domain/policies/alerta_ip.py`

- [ ] T6: Cablear `Container.security_logger()` en `container.py`; inyectarlo en
      `AuditoriaService`; emitir al logger en `registrar_evento` sin que la interfaz lo
      toque. La interfaz sigue llamando solo a `Container.auditoria_service()`.
  Verifica: `python -m pytest tests/unit/services/ -q -k auditoria`
  Produce: `container.py`, `src/services/auditoria_service.py` modificados

- [ ] T7: Actualizar `/health` en `main.py` para que llame a `verify_db_integrity()` y
      devuelva 503 si falla; instalar manejador global de excepciones que registre con
      `logger.exception`.
  Verifica: `python -m pytest tests/unit/ -q -k health`
  Produce: `main.py` modificado

- [ ] T8: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Una línea JSON por cada evento de R1 en el fichero de log tras ejercitarlos manualmente.
- `grep -i password <log>` no devuelve nada tras un login fallido de prueba.
- 6 logins fallidos desde la misma dirección producen una línea `WARNING` del módulo `alerta_ip`.
- Los logs sobreviven un reinicio de la app (presentes en disco, no solo en memoria).
- Con `SECURITY_LOG_MAX_BYTES` bajo (p.ej. 1024), aparece el fichero rotado `.1`.
- `/health` devuelve 503 con una copia de `app.db` corrompida a propósito.
