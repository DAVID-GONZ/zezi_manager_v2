# obs_00 — Roadmap de observabilidad, auditoría y rol ADMIN

> Auditoría del estado real a 2026-09-19, tras cerrar `obs_01`…`obs_05`.
> Toda afirmación de este documento está verificada contra el código o contra
> `data/app.db`. Las cifras son las de la base de desarrollo el 2026-09-19.

## Contexto

La épica `obs_01`…`obs_05` resolvió el problema de **escritura**: hoy la huella de
auditoría existe, es universal (23 servicios llaman `auditar_cambio`), está protegida
por una puerta (`scripts/check_auditoria.py`) y encadenada por hash. Lo que esta
épica ataca es el problema de **lectura y de señal**: la bitácora se escribe, pero
no se puede leer con provecho, nadie dentro del colegio puede consultarla, y los
eventos más sensibles no identifican a nadie.

El disparador es empírico. En `auditoria` hay 508 filas:

| Hecho medido | Cifra |
| --- | --- |
| Eventos totales | 508 |
| `ACCESO_DENEGADO` con `usuario = "anon"` y `usuario_id` nulo | **484 (95,3 %)** |
| — de ellos, `Cross-tenant: objeto institucion 2` | 379 |
| — de ellos, `Intento de escritura en modo solo lectura` | 105 |
| Filas con `ip_address` no nula | **0 de 508 (0 %)** |
| Filas con `institucion_id` nulo | 116 |
| Eventos `LOGOUT` | 0 |
| Eventos `VER_COMO_INICIO` / `VER_COMO_FIN` | 0 |
| Filas en `audit_log` | 6 |

Es decir: la pestaña «Sesiones» de `/admin/auditoria` es, a día de hoy, un 95 % de
ruido anónimo sin IP; y la pestaña «Cambios» está vacía porque esta base no ha
ejercitado la huella nueva. Ninguna de las dos sirve todavía como evidencia.

---

## Criterio de niveles

| Nivel | Significado |
| --- | --- |
| **N0 — Bloqueante** | La bitácora no es evidencia válida sin esto. Va primero. |
| **N1 — Producto** | Lo que un colegio espera poder hacer con la auditoría. |
| **N2 — Comercial** | Necesario para vender multitenant / pasar una inspección. |
| **N3 — Diferido** | Se activa con la API REST (`backend_00`) o el fork Vue. |

Dificultad: **Código-Bajo** (un módulo) · **Código-Medio** (varios) ·
**Código-Alto** (esquema o arquitectura) · **Config**.

---

# Parte 1 — Revisión del rol ADMIN

## Lo que está bien (no se toca)

| Punto | Evidencia |
| --- | --- |
| Admin **no edita datos de negocio**. Sus únicas rutas propias son `/admin/usuarios`, `/admin/instituciones`, `/admin/auditoria`, `/diagnostico`. | `main.py:224-228` |
| Admin solo puede crear y gestionar **directores**, no profesores ni coordinadores. | `rbac_usuarios.py` → `_ASIGNABLES["admin"] = {"director"}` |
| Deny-by-default real: `roles` es obligatorio en `registrar_pagina`, sin default, y rechaza el conjunto vacío. | `route_guard.py:_normalizar_roles` |
| El NAV deriva su visibilidad del **mismo** registro que autoriza, sin lista duplicada. | `layout.py:_rol_permitido_en_ruta` |
| «Ver como» es solo lectura con bloqueo **central** en servicios, no página por página. | `solo_lectura.verificar_escritura` |
| La huella de una impersonación pertenece al **admin real**, no al suplantado. | `contexto_actor.py`, regla de impersonación |

Esto confirma la decisión ya registrada: *admin = auditor técnico, no edita*.

## Hallazgos del rol

**A1 · Nadie dentro del colegio puede auditar su propia institución.** `N0`
`/admin/auditoria` es `{Rol.ADMIN}` y no existe ninguna otra vista de auditoría.
El rector es el responsable del tratamiento de datos personales (Ley 1581) y el
custodio del libro de convivencia (Ley 1620), pero no puede responder *«¿quién
borró esta observación?»* sin escribir al proveedor. Para un producto que se
posiciona por convivencia y asistencia, esto es un hueco de producto, no solo
técnico.

**A2 · Auto-auditoría sin segregación.** `N2`
El mismo admin que crea directores es el único que lee la bitácora donde consta
que los creó, y el único que puede verificar la cadena de hash. La cadena
SHA-256 detecta manipulación, pero no hay exportación externa ni copia fuera del
alcance del admin. En una auditoría comercial esto se marca siempre.

**A3 · La impersonación no deja rastro utilizable.** `N0`
Dos pérdidas encadenadas: (a) en `auditoria` hay **0 filas** `VER_COMO_*` pese a
que la función existe y se invoca desde `SessionContext`; (b) en el log de
seguridad, `SecurityLogger.ver_como(admin, objetivo, accion)` recibe `objetivo`
pero lo **descarta**, porque `_CAMPOS_PERMITIDOS` no lo contiene. El registro
resultante dice que hubo una impersonación y quién la hizo, nunca a quién. A
`gestion_usuario` le pasa lo mismo.

**A4 · `_ADMIN_DIRECTOR` definido y nunca usado.** `N1` · trivial
`main.py:122`. Residuo de la matriz de `paso_35`. Ruff no lo bloquea (F841 solo
informa). Se retira o se usa.

---

# Parte 2 — Revisión de la UI de auditoría y observabilidad

## B · Bitácora (`/admin/auditoria`)

**B1 · No existe vista de detalle: el diff nunca se muestra.** `N0`
La tabla de cambios muestra `timestamp · acción · tabla · registro · usuario_id`
y nada más. `valor_anterior` y `valor_nuevo` se escriben en cada fila y no se
leen nunca. El backend para hacerlo **ya está construido**: `get_cambio(id)` y
`listar_cambios_por_registro(tabla, id)` existen en el puerto
(`auditoria_repo.py:121,134`), en el repositorio SQLite (`:316,332`) y en los
dobles de test — con **cero consumidores**. Es exactamente el patrón de código
muerto que `obs_05` corrigió con `resumen_uso`.

**B2 · La columna dice «Usuario ID» y muestra un entero.** `N1`
Sin join a `usuarios`, sin nombre. Un auditor humano no trabaja con `7`.

**B3 · La identidad del actor es inconsistente entre puntos de emisión.** `N0`
Cuatro formatos distintos en la misma columna:

| Origen | Valor de `usuario` |
| --- | --- |
| `login.py:224` | `user_db.usuario` — username |
| `main.py:pagina_logout` | `usuario_nombre` — nombre para mostrar |
| `session_context.py:_auditar_ver_como` | `admin_nombre` — nombre para mostrar |
| `solo_lectura.py:68`, `contexto_tenant.py:89` | `str(uid or "anon")` — entero o literal |

**B4 · El 95 % de la bitácora es ruido anónimo.** `N0`
484 de 508 eventos son denegaciones con `usuario="anon"` y `usuario_id` nulo:
`actor_actual()` devuelve `None` en el punto donde se deniega. Los eventos más
relevantes para la seguridad son precisamente los que no identifican a nadie.
Aparte, 379 denegaciones cross-tenant contra la institución 2 en nueve días es
en sí misma una señal que nada en la UI destaca: o hay una fuga intentada, o
—más probable— un flujo legítimo mal enfocado que lleva meses gritando al vacío.

**B5 · La IP es nula en el 100 % de las filas, y eso mata la alerta de IP.** `N0`
`_obtener_ip()` (`login.py:86`, anidado dentro de la página) falla siempre en
este entorno: 0 de 508 filas tienen IP, ni siquiera los logins. Consecuencia en
cadena: la columna IP de la UI muestra siempre «—», y
`AuditoriaService.registrar_evento` solo llama a `alerta_ip.registrar_fallo_ip`
`if evento.ip_address is not None`, así que **toda la política de ráfaga por IP
de `obs_03` está muerta en ejecución**. Verde en tests, inerte en producción.

**B6 · Sin exportación.** `N1`
No hay CSV ni PDF de la bitácora. Un proceso disciplinario o una visita de la
Secretaría exigen entregar evidencia; hoy la única salida es abrir la base.

**B7 · Paginación sin total.** `N1`
`obs_05` sustituyó el techo silencioso por look-ahead, que es correcto, pero no
hay conteo total, ni salto a página, ni tamaño de página configurable. No existe
ningún `contar_*` en el repositorio.

**B8 · Filtros pobres.** `N1`
El filtro de tabla es texto libre con igualdad exacta (`AND tabla = ?`): hay que
conocer el nombre físico de la tabla. No hay búsqueda de texto libre, ni filtro
por `registro_id`, ni por rol del actor.

**B9 · «Verificar integridad» no escala y bloquea el hilo.** `N0`
`_verificar_cadena` hace `SELECT * FROM {tabla} WHERE hash_cadena IS NOT NULL
ORDER BY id ASC`, materializa **toda** la tabla en memoria y recalcula la cadena
completa de forma síncrona dentro de la petición. Con la huella universal de
`obs_04` y volúmenes reales (60 480 notas, 3 920 registros de asistencia), ese
botón congela la UI. Hoy no se nota porque `audit_log` tiene 6 filas.

**B10 · El filtro de institución oculta 116 eventos sin decirlo.** `N1`
`institucion_id IS NULL` en 116 filas; el SQL es `AND institucion_id = ?`, así
que al filtrar por cualquier institución esas filas desaparecen y no hay opción
«sin institución».

**B11 · No hay historial por registro en la ficha de negocio.** `N1`
No existe un «ver historial» en una observación, una nota, un estudiante o un
usuario. Es lo que un colegio pide primero, y el backend ya está (ver B1).

**B12 · `audit_log` no conserva ni el username ni la IP ni el motivo.** `N0`
Columnas: `usuario_id, accion, tabla, registro_id, valor_anterior, valor_nuevo,
timestamp, hash_cadena, institucion_id`. La tabla `auditoria` sí guarda `usuario`
como texto «para preservar tras borrado» — `audit_log` no hizo lo mismo. Si un
usuario se desactiva o se renombra, sus cambios quedan huérfanos de identidad.

## C · Observabilidad y logging

**C1 · El logger de seguridad está apagado por defecto.** `N0` · Config
`SECURITY_LOG_FILE: Path | None = None` (`config.py:137`) → `NullHandler`. Y en
`.env.example` las tres variables están **comentadas** (líneas 56-58). En una
instalación por defecto, todo `obs_03` no escribe absolutamente nada.

**C2 · Ninguna pantalla lee el log de seguridad.** `N1`
Es un JSONL en disco. El admin no tiene forma de verlo desde la aplicación: la
observabilidad real vive fuera del producto, en un fichero al que el rector de
un colegio no va a llegar nunca.

**C3 · La whitelist descarta el sujeto de la acción.** `N0`
`_CAMPOS_PERMITIDOS` no incluye `objetivo`. Ver A3. El diseño de whitelist es
correcto y hay que conservarlo; lo que falta es añadir el campo, no abrirla.

**C4 · `/diagnostico` no mide salud, mide instanciación.** `N1`
`Container.diagnostico()` construye los servicios y reporta OK/ERROR. Es un
smoke test de arranque, no observabilidad. No hay latencia, errores por minuto,
tamaño de la base, último backup, versión ni uptime.

**C5 · `/health` es correcto y nadie lo ve.** `N1`
Devuelve 503 si `verify_db_integrity()` falla — bien hecho en `obs_03` — pero no
está expuesto en ninguna pantalla ni monitorizado.

**C6 · Sin correlación.** `N3`
No hay `request_id` que una una excepción del log con una fila de auditoría y
con una sesión. Con el manejador global de excepciones ya en su sitio es el
siguiente paso natural, pero cobra sentido con la API REST.

**C7 · Sin retención ni archivado.** `N2`
El repositorio no tiene purga ni exportación de `audit_log`. Crece sin límite y
no hay política declarada — lo cual, con datos personales de menores de por
medio, es exactamente lo que la Ley 1581 no permite dejar indefinido.

**C8 · Los KPIs del dashboard admin ya son incorrectos hoy.** `N0`
`resumen_uso` pide `por_pagina=500` y agrega en Python. Con 484 denegaciones en
nueve días el techo ya está tocado: «Logins hoy» y «Usuarios activos» se calculan
sobre una muestra truncada. Debe ser un `COUNT`/`GROUP BY` en SQL.

**C9 · Las alertas no llegan a ningún sitio.** `N1`
`alerta_ip` escribe un WARNING en un fichero que nadie lee (C2), que por defecto
no se escribe (C1), y que nunca se dispara (B5). Tres capas de inercia sobre la
misma función.

---

# Parte 3 — Épica de mejora

Siete pasos más uno diferido. El orden no es negociable en los dos primeros: sin
identidad ni IP, todo lo que se construya encima hereda el ruido.

## N0 — La bitácora como evidencia

### `obs_06_identidad_y_ip` · Código-Medio · sin dependencias
Cierra B3, B5, B12, C1, C3 y A3(b).
- Helper único `src/interface/context/request_ip.py` con la captura de IP, sacada
  de la clausura de `login.py`, con `X-Forwarded-For` y fallback, y **con un test
  que falle si devuelve `None` en una petición simulada** — el fallo actual es
  silencioso por diseño (`except: return None` anidado dos veces).
- Un único constructor de `EventoSesion` en la capa de interfaz que fije siempre
  `usuario = username`, `usuario_id`, `ip_address` e `institucion_id`. Los cinco
  puntos de emisión pasan por él.
- `audit_log` gana `usuario` (snapshot del username) e `ip_address`. Cambio de
  esquema: recrear la base (decisión permanente de `CLAUDE.md`, sin migraciones).
- `_CAMPOS_PERMITIDOS` gana `objetivo`. La whitelist sigue siendo cerrada.
- Reactivar la ruta de `alerta_ip` ahora que la IP existe, con test de ráfaga.
- `SECURITY_LOG_FILE` con valor por defecto real y descomentado en `.env.example`.

### `obs_07_denegaciones_con_actor` · Código-Medio · depende de `obs_06`
Cierra B4 y A3(a). Es tanto un arreglo como una investigación con evidencia.
- Averiguar por qué `actor_actual()` es `None` en `solo_lectura.py:68` y
  `contexto_tenant.py:89`, y por qué `VER_COMO_*` y `LOGOUT` tienen 0 filas pese
  a emitirse. Hipótesis a descartar: la denegación ocurre en una task donde el
  `ContextVar` no se resincronizó (`tenant_01` cubrió los event handlers, no
  necesariamente estos caminos).
- Diagnosticar las **379** denegaciones cross-tenant contra la institución 2: o
  es un flujo legítimo mal enfocado, o es una fuga. Ninguna de las dos respuestas
  puede seguir sin darse.
- Clasificar el evento con una `severidad` (esperada / anómala) para que la UI
  pueda separar el ruido operativo de la señal.
- Test de regresión: ninguna denegación se escribe con `usuario_id` nulo cuando
  hay sesión.

### `obs_08_integridad_incremental` · Código-Medio · depende de `obs_06`
Cierra B9 y C8.
- `verificar_integridad` pasa a incremental: verificación por rango de `id` con
  checkpoint persistido, o ejecución en background con resultado cacheado. La UI
  nunca recalcula 60 000 filas dentro de la petición.
- `resumen_uso` pasa a agregación SQL (`COUNT`/`GROUP BY`), con scope de tenant
  explícito y sin el techo de 500.
- Añadir `contar_eventos` / `contar_cambios` al puerto (los necesita `obs_09`).
- Test con base sembrada de ~50 000 filas que verifique el tiempo de respuesta.

## N1 — Lo que un colegio espera

### `obs_09_detalle_y_diff` · Código-Medio · depende de `obs_06`, `obs_08`
Cierra B1, B2, B8, B10.
- Diálogo de detalle del cambio consumiendo `get_cambio()`, con diff campo a
  campo anterior→nuevo, legible, no JSON crudo.
- Resolución de `usuario_id` a nombre; columna «Usuario» con nombre y username.
- Selector de tabla con **etiquetas de negocio**, no nombres físicos.
- Opción «Sin institución» en el filtro; búsqueda por `registro_id`.
- Contador total y salto de página apoyados en `contar_*`.

### `obs_10_historial_por_registro` · Código-Bajo · depende de `obs_09`
Cierra B11. Componente reutilizable del design system («Historial de cambios»)
que consume `listar_cambios_por_registro`, colgado de las fichas de observación,
nota, estudiante y usuario. Respeta `CLASS_CONTRACT.md` y la frontera
Core/Adapter — se va a portar a Vue.

### `obs_11_auditoria_del_rector` · Código-Medio · depende de `obs_09`
Cierra A1, el hueco de producto. Nueva ruta `/institucion/auditoria` para
`{director, coordinador}`:
- Scope de institución **forzado** vía `TenantScope` obligatorio, no un filtro
  opcional que el presenter pueda olvidar asignar — que es precisamente el bug
  que `obs_05` tuvo que arreglar en la versión de admin.
- Sin pestaña técnica ni verificación de cadena: el rector audita personas, no
  hashes.
- Test de aislamiento cross-tenant en la suite de `tenant_04`.

## N2 — Comercial

### `obs_12_exportacion_y_retencion` · Código-Medio · depende de `obs_09`
Cierra B6, C7, A2.
- Exportación CSV y PDF del rango filtrado, con sello de verificación de cadena
  incluido, para que el documento entregado sea comprobable fuera del sistema.
- Política de retención declarada y aplicada (archivado a fichero firmado +
  purga), con la ventana como configuración por institución.
- La exportación queda auditada: exportar la bitácora es un evento de la bitácora.

### `obs_13_panel_observabilidad` · Código-Medio · depende de `obs_06`, `obs_08`
Cierra C2, C4, C5, C9. Nueva ruta `/admin/observabilidad` (o ampliación de
`/diagnostico`):
- Estado de `/health`, versión, uptime, tamaño de la base, último backup.
- Últimos N errores del log, leídos desde el JSONL, con filtro por nivel.
- Alertas de IP activas, visibles y accionables, no un WARNING en disco.
- KPIs de uso reales (los de `obs_08`), con serie temporal, no tres números.

## N3 — Diferido

### `obs_14_correlacion_request_id`
Cierra C6. `request_id` propagado por `ContextVar`, escrito en el log, en
`audit_log` y en `auditoria`. Se activa con la API REST de `backend_00`, donde
un identificador de petición tiene un dueño claro.

---

## Puertas que esta épica debe respetar

- `python init.py` verde al cierre de cada paso, sin excepción.
- `scripts/check_auditoria.py`: `SERVICIOS_SIN_HUELLA_DEUDA` no crece ni queda
  obsoleta. Los servicios nuevos que se toquen aquí no pueden entrar en la lista.
- `check_design.py --all`, `sync_tokens.py --check`, `audit_design.py` tras
  cualquier CSS. Regla N (frontera Core/Adapter) en los componentes de `obs_10`.
- Nada de `ui.input/select/number` directos: `form_fields.py` es la puerta única.
- Los cambios de esquema (`obs_06`) recrean la base; no hay migraciones.
- Sin `ruff format` masivo dentro de un paso de funcionalidad.

## Lo que esta épica NO hace

- No toca la escritura de la huella: `obs_01`…`obs_04` la dejaron cubierta y con
  puerta. Aquí solo se añaden dos columnas (`obs_06`).
- No introduce APM ni telemetría externa (Sentry, OpenTelemetry). Con un despliegue
  por institución y SQLite el coste operativo no se justifica todavía; se revisa
  cuando `backend_00` lleve el producto a PostgreSQL en la nube.
- No crea un rol `auditor` separado. A2 se mitiga con exportación verificable
  (`obs_12`); la segregación real de funciones espera a que haya más de un operador.
