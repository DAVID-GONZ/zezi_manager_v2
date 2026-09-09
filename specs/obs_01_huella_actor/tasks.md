# Tasks: Huella completa y atribuible (obs_01_huella_actor)

- [ ] T1: Crear `src/services/contexto_actor.py` con ContextVar de módulo,
      `activar_actor()`, `actor_actual()` y `limpiar_actor()`, calcado de
      `contexto_tenant.py` y sin dependencias de interfaz.
  Verifica: `python -m pytest tests/unit/services/test_contexto_actor.py -q`
  Produce: `src/services/contexto_actor.py`

- [ ] T2: Añadir `institucion_id` a las 3 factories de `RegistroCambio`
      (`para_creacion`, `para_actualizacion`, `para_eliminacion`).
  Verifica: `python -m pytest tests/unit/domain/ -q -k auditoria`
  Produce: `src/domain/models/auditoria.py` modificado

- [ ] T3: Crear `src/services/auditoria_helpers.py` con `auditar_cambio()`, que resuelve
      actor e institución desde el contexto, acepta override explícito y nunca propaga
      excepciones (registra `logger.warning`).
  Verifica: `python -m pytest tests/unit/services/test_auditoria_helpers.py -q`
  Produce: `src/services/auditoria_helpers.py`

- [ ] T4: Reemplazar las 7 copias locales de `_auditar` por el helper, sin cambiar el
      comportamiento observable de los servicios ya cubiertos.
  Verifica: `python scripts/run_tests.py rapido`
  Produce: 7 servicios modificados

- [ ] T5: Cablear `auditoria=cls.auditoria_repo()` en `HabilitacionService`.
  Verifica: `python -m pytest tests/integration/ -q -k habilitacion`
  Produce: `container.py` modificado

- [ ] T6: Sembrar el actor en `SessionContext.desde_storage()`, registrando el admin real
      cuando hay impersonación.
  Verifica: `python -m pytest tests/unit/interface/ -q -k session_context`
  Produce: `src/interface/context/session_context.py` modificado

- [ ] T7: Emitir `ACCESO_DENEGADO` en `route_guard`, `verificar_pertenencia` y
      `verificar_escritura`; emitir `LOGOUT` en `main.py` antes de limpiar el storage.
  Verifica: `python -m pytest tests/unit/interface/auth/ -q`
  Produce: `route_guard.py`, `contexto_tenant.py`, `solo_lectura.py`, `main.py` modificados

- [ ] T8: Capturar la dirección de red del cliente en una única función
      (`X-Forwarded-For` primer salto, con fallback a `request.client.host`) y pasarla a
      los eventos de sesión.
  Verifica: `python -m pytest tests/unit/interface/ -q -k login`
  Produce: `src/interface/pages/login.py` modificado

- [ ] T9: Test de integración: una escritura por servicio cubierto produce fila en
      `audit_log` con `usuario_id` e `institucion_id` no nulos, y `verificar_integridad()`
      sigue en verde sobre registros preexistentes (R9).
  Verifica: `python -m pytest tests/integration/test_huella_actor.py -q`
  Produce: `tests/integration/test_huella_actor.py` verde

- [ ] T10: Verificar entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes
