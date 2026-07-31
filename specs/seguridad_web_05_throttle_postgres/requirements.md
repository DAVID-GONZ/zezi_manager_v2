# Requisitos: Throttle de login persistente en Postgres (seguridad_web_05)

> **Nivel:** N0 — Bloqueante de deploy
> **Dificultad:** Código-Alto (cambio arquitectónico; toca auth crítica)
> **Depende de:** backend_00 Fase 1 (Postgres disponible con SQLAlchemy)
> **Relacionado con:** S07 (multi-tenant en Postgres)

## Contexto del problema

`src/services/login_throttle.py` mantiene el estado de intentos fallidos en memoria
del proceso Python (diccionario en-proceso). En un entorno de escritorio single-user
esto es correcto. En producción web con Postgres ocurren dos problemas:

1. **Reinicio del proceso**: cualquier reinicio (deploy, crash, OOM kill) borra el
   historial de intentos. Un atacante puede reiniciar entre ráfagas de intentos.
2. **Múltiples workers**: si el servidor corre con más de un proceso Python (gunicorn,
   uvicorn con workers > 1), cada worker tiene su propio diccionario. Un atacante
   puede distribuir intentos entre workers sin alcanzar el umbral en ninguno.

El throttle en memoria es una vulnerabilidad real en producción web multiusuario.

## Requisitos

R1: EL SISTEMA DEBE persistir el estado de intentos fallidos de login en la base de
    datos (Postgres en producción, SQLite en desarrollo/tests), de modo que sobreviva
    reinicios del proceso y sea compartido entre todos los workers.

R2: EL SISTEMA DEBE mantener el contrato externo actual del throttle: 5 intentos
    fallidos consecutivos → bloqueo de 300 segundos por `username`. Los valores
    concretos DEBEN ser configurables vía `config.py` sin modificar código.

R3: EL SISTEMA DEBE implementar el throttle a través del patrón de puertos y
    adaptadores existente: un puerto `ILoginThrottleRepository` en `domain/ports/`
    con implementaciones `SqliteLoginThrottleRepository` y `PostgresLoginThrottleRepository`
    (o una única implementación SQLAlchemy).

R4: EL SISTEMA DEBE limpiar automáticamente los registros de throttle expirados
    para evitar crecimiento indefinido de la tabla. La limpieza puede ser lazy
    (al consultar) o mediante un job periódico.

R5: LA TABLA DE THROTTLE DEBE contener como mínimo: `username` (PK o índice único),
    `intentos_fallidos` (entero), `bloqueado_hasta` (timestamp con zona horaria),
    `ultimo_intento` (timestamp). No debe contener passwords ni información sensible.

R6: LA OPERACIÓN de registrar un intento fallido DEBE ser atómica: si dos workers
    registran fallos simultáneos para el mismo username, el conteo final debe ser
    consistente (usar `UPDATE ... SET intentos = intentos + 1` o equivalente atómico
    en SQLAlchemy, no read-modify-write en Python).

R7: EL COMPORTAMIENTO ante error de base de datos en el throttle DEBE ser fail-open
    con log de alerta: si no se puede consultar el throttle, se permite el intento
    de login y se registra la anomalía. Un throttle caído no debe impedir el acceso
    legítimo, pero sí debe alertar.

R8: LOS TESTS EXISTENTES de login throttle DEBEN seguir pasando con el nuevo
    adaptador usando `FakeLoginThrottleRepository` (en-memoria) para los tests
    unitarios. Los tests de integración usan el adaptador SQLite real.

R9: EL MÓDULO `login_throttle.py` EN MEMORIA DEBE eliminarse o reemplazarse
    completamente. No puede coexistir la implementación en memoria con la persistente
    en producción.

## Criterio de done

- `python init.py` verde tras el cambio.
- Test de integración: 5 logins fallidos consecutivos desde workers distintos
  (simulados con threads) resultan en bloqueo persistente.
- Test de integración: reiniciar la app entre intentos no resetea el contador.
- `pytest -m throttle` verde en SQLite y Postgres.
