# Tasks: Logging de seguridad y alertas (seguridad_web_09)

- [ ] T1: Crear el puerto `ISecurityLogger` en `src/domain/ports/security_logger.py` con
      un método por familia de evento de R1.
  Verifica: `python -m pytest tests/unit/domain/ -q -k security`
  Produce: `src/domain/ports/security_logger.py`

- [ ] T2: Crear `src/infrastructure/logging/security_logger.py` con logger dedicado
      `zeci.security`, formatter JSON, `RotatingFileHandler` y lista blanca de campos
      (sin `**kwargs` libre).
  Verifica: `python -m pytest tests/unit/infrastructure/test_security_logger.py -q`
  Produce: `src/infrastructure/logging/security_logger.py`

- [ ] T3: Test R7 — un login fallido con un password largo no deja el password en el log,
      ni completo ni en fragmentos.
  Verifica: `python -m pytest tests/unit/infrastructure/test_security_logger.py -q -k password`
  Produce: test verde

- [ ] T4: Añadir `SECURITY_LOG_FILE`, `SECURITY_LOG_MAX_BYTES` y
      `SECURITY_LOG_BACKUP_COUNT` a `config.py` con validador de ruta; documentarlos en
      `.env.example` y añadir `logs/` a `.gitignore`.
  Verifica: `python -m pytest tests/unit/ -q -k config`
  Produce: `config.py`, `.env.example`, `.gitignore` modificados

- [ ] T5: Crear `src/domain/policies/alerta_ip.py` (umbral y ventana por dirección de red)
      que emita `WARNING` al superarse.
  Verifica: `python -m pytest tests/unit/domain/test_alerta_ip.py -q`
  Produce: `src/domain/policies/alerta_ip.py`

- [ ] T6: Cablear `security_logger()` en `container.py` y emitir desde
      `AuditoriaService.registrar_evento`, sin que la interfaz toque el logger.
  Verifica: `python -m pytest tests/unit/services/ -q -k auditoria`
  Produce: `container.py`, `src/services/auditoria_service.py` modificados

- [ ] T7: `/health` verifica la integridad de la base y devuelve 503 si falla; instalar
      manejador global de excepciones que registre con `logger.exception`.
  Verifica: `python -m pytest tests/unit/ -q -k health`
  Produce: `main.py` modificado

- [ ] T8: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Una línea JSON por cada evento de R1 en el fichero de log.
- `grep -i password` sobre el log no devuelve nada tras un login fallido de prueba.
- 6 logins fallidos desde la misma dirección producen una línea `WARNING`.
- Los logs sobreviven un reinicio de la app.
- Con `SECURITY_LOG_MAX_BYTES` bajo, aparece el fichero rotado `.1`.
- `/health` devuelve 503 con una copia de `app.db` corrompida a propósito.
