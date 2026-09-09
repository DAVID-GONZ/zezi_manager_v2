# Diseño: Huella completa y atribuible (obs_01_huella_actor)

## 1. Archivos a crear

| Archivo | Responsabilidad |
|---|---|
| `src/services/contexto_actor.py` | ContextVar del usuario que origina la operación. |
| `src/services/auditoria_helpers.py` | Helper único de auditoría; sustituye las 7 copias de `_auditar`. |
| `tests/unit/services/test_contexto_actor.py` | Aislamiento y limpieza del ContextVar. |
| `tests/unit/services/test_auditoria_helpers.py` | Resolución de actor/institución y no propagación de errores. |
| `tests/integration/test_huella_actor.py` | Huella real contra base en memoria + cadena íntegra. |

## 2. Archivos a modificar

- `container.py` — añadir `auditoria=cls.auditoria_repo()` a `HabilitacionService` (L431-435).
- `src/domain/models/auditoria.py` — `institucion_id` en las 3 factories de `RegistroCambio`.
- `src/services/{usuario,estudiante,periodo,asignacion,evaluacion,cierre,habilitacion}_service.py`
  — borrar el `_auditar` local e importar el helper.
- `src/interface/context/session_context.py` — sembrar el actor en `desde_storage()`.
- `src/interface/auth/route_guard.py` — emitir `ACCESO_DENEGADO`.
- `src/services/contexto_tenant.py`, `src/services/solo_lectura.py` — emitir `ACCESO_DENEGADO`.
- `main.py` — emitir `LOGOUT` antes de `app.storage.user.clear()`.
- `src/interface/pages/login.py` — pasar la dirección de red del cliente.

## 3. Métodos de Container a usar

- `Container.auditoria_repo()` → `IAuditoriaRepository` (`registrar_cambio`, `registrar_evento`)
- `Container.auditoria_service()` → `AuditoriaService` (`registrar_evento`)

## 4. Punto de siembra del contexto

`SessionContext.desde_storage()` es el único choke point: lo invoca `route_guard` en cada
petición y ya sincroniza las ContextVar de `solo_lectura` y de institución. El actor se
siembra en la misma línea, así que hereda gratis la cobertura y el interceptor de eventos
de `tenant_01`.

`contexto_actor.py` se calca de `contexto_tenant.py`: ContextVar de módulo más
`activar_actor()` / `actor_actual()` / `limpiar_actor()`, sin dependencias de interfaz.

**Bajo impersonación**: actor = `admin_real_id`; el usuario suplantado va en `detalles`.
Hoy `solo_lectura` bloquea las escrituras, así que es defensa en profundidad, no un caso
vivo — pero deja el registro correcto si alguna vez se abre una excepción a esa regla.

## 5. Integración

```python
# Así llama el servicio al helper: no construye el RegistroCambio ni toca ContextVars
from src.services.auditoria_helpers import auditar_cambio

auditar_cambio(
    self._auditoria,
    accion=AccionCambio.UPDATE,
    tabla="habilitaciones",
    registro_id=hab.id,
    anterior=antes,
    nuevo=despues,
)   # actor e institucion_id los resuelve el helper desde el contexto

# Así NO: el call site no debe pasar el actor a mano ni construir la entidad
RegistroCambio.para_actualizacion(..., usuario_id=ctx.usuario_id)
```

El parámetro `usuario_id=` se conserva como override explícito para tests y para la futura
API REST, donde no habrá `SessionContext`.

## 6. Alternativa descartada

**Auditar dentro de los repositorios** en lugar de en los servicios. Sería automático y
cubriría el 100% sin tocar 118 métodos. Se descarta por dos razones: el repositorio no
conoce la intención de negocio —vería un `UPDATE` de fila, no "anular habilitación"— ni al
actor; y `backend_07` reescribe los 21 repositorios, así que la huella quedaría atrapada
justo en la capa que está a punto de cambiar. Los servicios son estables y son donde ya
viven `contexto_tenant` y `solo_lectura`.

## 7. Manejo de errores

El helper nunca propaga:

```python
try:
    repo.registrar_cambio(cambio)
except Exception as exc:
    logger.warning("No se pudo registrar auditoria de %s: %s", tabla, exc)
```

Sustituye los `except Exception: pass` actuales (`session_context.py:320-322`,
`auditoria_service.py:49-50`). R8 exige el aviso, no el bloqueo: la operación de negocio
sigue, pero el fallo deja rastro. Cuando llegue S09 ese aviso será además un WARNING de
seguridad.

## 8. Riesgo a vigilar

El payload que alimenta el hash de la cadena (`_payload_cambio`, `_payload_evento` en
`sqlite_auditoria_repo.py:64-87`) **no debe cambiar de forma** para los campos existentes,
o `verificar_integridad()` reportará como alterados los registros ya escritos.

Regla para el implementer: comprobar primero si `institucion_id` ya forma parte del
payload. Si no lo está, **dejarlo fuera del hash** y escribirlo solo en la columna. La
verificación de R9 (cadena íntegra sobre registros preexistentes) es la prueba de que esto
se respetó.
