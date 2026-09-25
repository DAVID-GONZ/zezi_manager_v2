# Tasks: Identidad del actor e IP en toda la bitácora (obs_06)

- [ ] T1: Modificar `src/services/contexto_actor.py`: añadir el dataclass
      `ActorContexto(usuario_id, username, ip)`, cambiar el `ContextVar` para
      que lo transporte, ampliar `activar_actor(usuario_id, username=None,
      ip=None)` y `usar_actor(...)` con los mismos opcionales, y añadir
      `actor_username()` y `actor_ip()`. `actor_actual()` conserva su firma y
      su semántica. El módulo sigue sin importar interfaz ni infraestructura.
  Verifica: `python -m pytest tests/unit/services/test_contexto_actor.py -q`
  Produce: `src/services/contexto_actor.py` modificado

- [ ] T2: Crear `tests/unit/services/test_contexto_actor.py` (si no existe,
      ampliarlo si existe) con: activación de los tres campos, aislamiento
      entre contextos, `usar_actor` restaura el valor previo, y compatibilidad
      de `activar_actor(id)` con un solo argumento.
  Verifica: `python -m pytest tests/unit/services/test_contexto_actor.py -q`
  Produce: test verde

- [ ] T3: Crear `src/interface/context/request_ip.py` con `_de_request(request)`
      (pura) e `ip_de_peticion()`, incluyendo el `logger.warning` en los tres
      caminos de fallo (R2).
  Verifica: `python -c "from src.interface.context.request_ip import ip_de_peticion"`
  Produce: `src/interface/context/request_ip.py`

- [ ] T4: Crear `tests/unit/interface/context/test_request_ip.py` con dobles de
      petición: (a) `X-Forwarded-For` con varios saltos → devuelve el primero;
      (b) sin cabecera pero con `client.host` → devuelve el host; (c) sin nada
      → devuelve `None` **y** emite el warning. El test (a) y (b) fallan si el
      resultado es `None` (R3).
  Verifica: `python -m pytest tests/unit/interface/context/test_request_ip.py -q`
  Produce: test verde

- [ ] T5: Modificar `src/domain/models/auditoria.py`: añadir el enum
      `SeveridadEvento(StrEnum)` con `INFO`/`ADVERTENCIA`/`CRITICA`; añadir a
      `EventoSesion` los campos `objetivo: str | None = None` y
      `severidad: SeveridadEvento = SeveridadEvento.INFO`; añadir a
      `RegistroCambio` los campos `usuario: str | None = None` e
      `ip_address: str | None = None`; ampliar los tres factories
      (`para_creacion`, `para_actualizacion`, `para_eliminacion`) con esos dos
      parámetros **al final** de la firma.
  Verifica: `python -m pytest tests/unit/domain/ -q -k auditoria`
  Produce: `src/domain/models/auditoria.py` modificado

- [ ] T6: Modificar `src/infrastructure/db/schema.py`: `auditoria` gana
      `objetivo TEXT` y `severidad TEXT NOT NULL DEFAULT 'INFO' CHECK(...)`;
      `audit_log` gana `usuario TEXT` e `ip_address TEXT`. Comentar en el DDL,
      igual que hizo `mejora_07-T7` con `institucion_id`, qué columnas
      participan en el hash y cuáles no.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k schema`
  Produce: `src/infrastructure/db/schema.py` modificado

- [ ] T7: Modificar `src/infrastructure/db/repositories/sqlite_auditoria_repo.py`:
      `_payload_evento` incorpora `objetivo` (no `severidad`, que es
      clasificación y no contenido); `_payload_cambio` incorpora `usuario` e
      `ip_address` (R11); `registrar_evento`, `registrar_cambio` y
      `registrar_cambios_masivos` insertan las columnas nuevas; `_row_to_evento`
      y `_row_to_cambio` las leen.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k auditoria`
  Produce: `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` modificado

- [ ] T8: Ampliar los tests del repositorio de auditoría: una fila insertada con
      `usuario`/`ip_address` se relee con esos valores; alterar `usuario` o
      `ip_address` de una fila por SQL directo hace que
      `verificar_cadena_cambios()` devuelva su `id`.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k auditoria`
  Produce: test verde

- [ ] T9: Crear `src/interface/context/eventos_sesion.py` con
      `construir_evento(...)` según §4 del diseño, resolviendo la IP vía
      `ip_de_peticion()`.
  Verifica: `python -m pytest tests/unit/interface/context/ -q`
  Produce: `src/interface/context/eventos_sesion.py`

- [ ] T10: Migrar los puntos de emisión de la **interfaz** al constructor único:
      `src/interface/pages/login.py` (retirar `_obtener_ip()` anidado; los dos
      eventos de login pasan por `construir_evento`), `main.py` →
      `pagina_logout` (pasa el **username** de la sesión, no `usuario_nombre`),
      `src/interface/context/session_context.py` → `_auditar_ver_como` (usa
      `objetivo=` para el usuario impersonado), y
      `src/interface/auth/route_guard.py` → `ACCESO_DENEGADO`.
  Verifica: `python -m pytest tests/unit/interface/ -q`
  Produce: cuatro archivos modificados

- [ ] T11: Migrar los puntos de emisión de **servicios**: `solo_lectura.py:68` y
      `contexto_tenant.py:89` sustituyen `str(uid or "anon")` por
      `actor_username() or "desconocido"` y pasan `ip_address=actor_ip()`.
      No importan interfaz.
  Verifica: `python -m pytest tests/unit/services/ -q -k "solo_lectura or tenant"`
  Produce: dos archivos modificados

- [ ] T12: Modificar `src/interface/context/session_context.py` →
      `desde_storage()` para que active el actor con los tres datos
      (`activar_actor(actor_id, username, ip_de_peticion())`), conservando la
      regla de impersonación: con `impersonando=True` el actor es el admin real.
  Verifica: `python -m pytest tests/unit/interface/context/ -q`
  Produce: `src/interface/context/session_context.py` modificado

- [ ] T13: Modificar `src/services/auditoria_helpers.py` para que
      `auditar_cambio` resuelva `usuario` e `ip` desde `contexto_actor` y los
      pase a los factories. Mantener intacta la garantía de que nunca propaga
      excepciones.
  Verifica: `python -m pytest tests/unit/services/ -q -k auditoria`
  Produce: `src/services/auditoria_helpers.py` modificado

- [ ] T14: Modificar `src/infrastructure/logging/security_logger.py`: añadir
      `objetivo` a `_CAMPOS_PERMITIDOS` y emitirlo desde `ver_como()` y
      `gestion_usuario()`. No se admite `**kwargs` libre.
  Verifica: `python -m pytest tests/unit/infrastructure/ -q -k security_logger`
  Produce: `src/infrastructure/logging/security_logger.py` modificado

- [ ] T15: Modificar `config.py` (`SECURITY_LOG_FILE` por defecto
      `Path("logs/security.log")`) y descomentar las tres variables
      `SECURITY_LOG_*` en `.env.example`. Verificar que `logs/` está en
      `.gitignore`.
  Verifica: `python -c "from config import settings; print(settings.SECURITY_LOG_FILE)"`
  Produce: `config.py` y `.env.example` modificados

- [ ] T16: Añadir a los tests del logger de seguridad el caso de ráfaga de IP
      (R14): `MAX_FALLOS_IP` eventos `LOGIN_FALLIDO` con la misma IP producen
      el `WARNING` `ALERTA_IP`; con IP `None` no se invoca la política.
  Verifica: `python -m pytest tests/unit/ -q -k alerta_ip`
  Produce: test verde

- [ ] T17: Crear `tests/unit/interface/test_emision_eventos.py`: análisis **por
      AST** de `src/interface/` que falla si aparece una llamada
      `EventoSesion(...)` fuera de `src/interface/context/eventos_sesion.py`.
      No usar regex (precedente de `check_design.py` ciego a multilínea).
  Verifica: `python -m pytest tests/unit/interface/test_emision_eventos.py -q`
  Produce: test verde

- [ ] T18: Recrear la base de desarrollo con el esquema nuevo (no hay
      migraciones) y verificar el entorno completo.
  Verifica: `python scripts/init.py`
  Produce: todos los checks verdes

## Verificación manual antes de declarar done

- Recrear la base, iniciar sesión y consultar:
  `SELECT usuario, usuario_id, ip_address, severidad FROM auditoria ORDER BY id DESC LIMIT 5`
  → el username correcto y una IP no nula (`127.0.0.1` en local).
- Editar cualquier dato y consultar:
  `SELECT usuario, usuario_id, ip_address FROM audit_log ORDER BY id DESC LIMIT 5`
  → las tres columnas pobladas.
- Fallar el login cinco veces seguidas → `logs/security.log` contiene una línea
  con `"tipo_evento": "ALERTA_IP"`.
- Iniciar y terminar un «Ver como» → `logs/security.log` contiene dos líneas con
  `objetivo` poblado, y `auditoria` tiene las filas `VER_COMO_INICIO`/`_FIN`.
- Cerrar sesión → la fila `LOGOUT` lleva el **username**, no el nombre completo.
- `python scripts/init.py` completamente verde, `check_auditoria.py` sin nuevas
  entradas de deuda.
