# Tasks: Correlación por request_id (obs_14)

> **Nivel N3 — diferido.** No iniciar hasta que la API REST de `backend_00`
> esté en marcha: antes de eso, el paso paga complejidad sin cobrar beneficio.

- [ ] T1: Crear `src/services/contexto_peticion.py` con el `ContextVar`
      privado, `abrir_peticion()`, `request_id()` y `usar_peticion(rid)` como
      context manager para tests y scripts. Stdlib puro, sin importar interfaz
      ni infraestructura, igual que `contexto_actor.py`.
  Verifica: `python -m pytest tests/unit/services/ -q -k contexto_peticion`
  Produce: `src/services/contexto_peticion.py`

- [ ] T2: Crear `tests/unit/services/test_contexto_peticion.py`: fuera de una
      petición devuelve `None`; dos tareas concurrentes obtienen
      identificadores distintos y ninguna ve el de la otra (R10);
      `usar_peticion` restaura el valor previo.
  Verifica: `python -m pytest tests/unit/services/test_contexto_peticion.py -q`
  Produce: test verde

- [ ] T3: Añadir el middleware HTTP en `main.py` que abre el contexto por
      petición, adoptando la cabecera entrante **solo** si valida el formato
      (hexadecimal de 16 caracteres) y generando uno nuevo si no (R7).
  Verifica: petición con cabecera válida → se adopta; con basura → se genera
  Produce: `main.py` modificado

- [ ] T4: Enganchar el identificador en la resincronización de
      `src/interface/context/event_context.py`, de modo que **cada evento**
      abra su propia unidad de correlación, no la sesión completa de
      websocket.
  Verifica: `python -m pytest tests/unit/interface/context/ -q`
  Produce: `src/interface/context/event_context.py` modificado

- [ ] T5: Añadir `request_id: str | None` a `EventoSesion` y `RegistroCambio`
      (`src/domain/models/auditoria.py`), la columna en ambas tablas de
      `schema.py` y un índice por `request_id` en cada una.
  Verifica: `python -m pytest tests/unit/domain/ -q -k auditoria`
  Produce: modelo y esquema modificados

- [ ] T6: Actualizar `sqlite_auditoria_repo.py` para persistir y leer la
      columna, dejando `request_id` **fuera** de `_payload_evento` y
      `_payload_cambio` (R9), con el comentario del criterio junto al de
      `institucion_id`.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k auditoria`
  Produce: `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` modificado

- [ ] T7: Test de que la cadena de hash no cambia: dos filas idénticas con
      `request_id` distinto producen el mismo `hash_cadena`.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k cadena`
  Produce: test verde

- [ ] T8: Añadir el campo a `_CAMPOS_PERMITIDOS` del logger de seguridad y
      emitirlo desde todos sus métodos, conservando la whitelist cerrada (R5).
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k security_logger`
  Produce: `src/infrastructure/logging/security_logger.py` modificado

- [ ] T9: Modificar `auditar_cambio` en `src/services/auditoria_helpers.py`
      para resolver el identificador del contexto, sin generarlo si no existe
      (R2).
  Verifica: `python -m pytest tests/unit/services/ -q -k auditoria`
  Produce: `src/services/auditoria_helpers.py` modificado

- [ ] T10: Modificar el manejador global de excepciones de `main.py` para
      incluir el identificador en la traza y en la respuesta como
      `referencia` (R6), sin exponer ningún detalle interno.
  Verifica: provocar un error controlado → la respuesta trae la referencia
  Produce: `main.py` modificado

- [ ] T11: Añadir `ObservabilidadService.traza_de(request_id)` que reúna
      entradas de log, eventos de sesión y cambios de esa petición, ordenados
      cronológicamente.
  Verifica: `python -m pytest tests/unit/services/ -q -k traza`
  Produce: `src/services/observabilidad_service.py` modificado

- [ ] T12: Añadir la búsqueda por identificador a
      `src/interface/pages/admin/observabilidad.py`, con su vista unificada
      (R8), reutilizando componentes ya contratados.
  Verifica: `python scripts/check_design.py --all`
  Produce: `src/interface/pages/admin/observabilidad.py` modificado

- [ ] T13: Recrear la base (el esquema cambió) y verificar el entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Provocar un error controlado → la respuesta trae una referencia opaca.
- Buscar esa referencia en `/admin/observabilidad` → aparecen la traza del log,
  el evento de sesión y los cambios de datos de esa misma petición.
- Dos sesiones simultáneas guardando a la vez producen referencias distintas y
  sus trazas no se mezclan.
- «Verificar integridad» sigue en verde tras la columna nueva.
- `python scripts/init.py` completamente verde.
