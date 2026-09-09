# Auditoría de logs, huella, observabilidad y persistencia

> Fecha: 2026-09-08 · Commit auditado: `2403ee7` · Árbol limpio
> Alcance pedido: arquitectura de logging/auditoría/observabilidad; visualización y gestión
> de informes desde el rol admin; estructura de persistencia de la base de datos.

## Resumen ejecutivo

**La auditoría de negocio está bien diseñada pero mal cableada: escribe muchísimo menos de
lo que el código aparenta escribir. La observabilidad de sistema es prácticamente
inexistente.** La persistencia está sana como SQLite —sin drift, con enums alineados— pero
arrastra defectos que romperán al pasar a `MetaData` y PostgreSQL.

| Dimensión | Madurez | Veredicto |
|---|---|---|
| Diseño de la auditoría (modelo, cadena SHA-256, UI, tests) | ★★★★☆ | Lo mejor del sistema. Dominio puro, integridad verificable, append-only. |
| **Cobertura real de la auditoría** | ★☆☆☆☆ | **~118 de 137 métodos que escriben no dejan rastro.** |
| Excepciones de dominio | ★★★★☆ | Jerarquía con códigos estables y `to_dict()`. Mixins de compatibilidad sin retirar. |
| Logging | ★★☆☆☆ | Config correcta, pero texto plano, sin rotación, sin fichero, sin trazas y ausente en servicios y repositorios. |
| Observabilidad de sistema | ★☆☆☆☆ | `/health` trivial y `Container.diagnostico()` solo en dev. Sin métricas, alertas ni correlación. |
| Persistencia (SQLite) | ★★★★☆ | 64 tablas sin drift, PRAGMAs correctos, puerta de enums en verde. |
| Persistencia (preparación a Postgres) | ★★☆☆☆ | Doce defectos registrados, tres bloqueantes. |
| Planificación previa | ★★★★☆ | El hueco de logging ya estaba especificado (S09) y sin implementar. |

> **Hallazgo urgente, verificado durante esta auditoría:** el bug de zona horaria que
> `datos_08_fecha_zona_horaria` declaró resuelto **sigue vivo y rompe la puerta de calidad**.
> Ver §0.

---

## 0. Urgente: el bug de zona horaria de `datos_08` sigue vivo

`step_list.json` marca `datos_08_fecha_zona_horaria` como `done`. **No lo está.**

Al ejecutar `python scripts/init.py` durante esta auditoría, la suite de integración falló:

```
FAILED tests/integration/test_convivencia_35_entradas_seguimiento.py — 5 tests
ValidationError: La fecha del registro (2026-09-09) no puede ser futura
```

Comprobado en el momento (20:05, hora de Colombia, UTC-5):

| Fuente | Valor |
|---|---|
| `SELECT CURRENT_DATE` (SQLite) | `2026-09-09` |
| `datetime.date.today()` (local) | `2026-09-08` |

**Verificado contra HEAD en un worktree limpio**: los mismos 5 tests fallan en el commit
`2403ee7` sin ninguno de los cambios de esta sesión. Es preexistente, no una regresión.

### Por qué sigue vivo

El paso declaraba `src/infrastructure/db/schema.py` entre sus destinos, pero **el commit
`2403ee7` no tocó `schema.py`**. Las 20 columnas con `DEFAULT CURRENT_DATE` /
`CURRENT_TIMESTAMP` siguen intactas (líneas 42, 261, 310, 337, 514, 533, 554, 582, 649,
671, 780, 849, 867, 894, 919, 985, 1005, 1027, 1052, 1078). `progress/impl_datos_08.md:70-77`
lo admite como decisión D3, "red de seguridad".

### Por qué nadie lo nota

**Solo falla entre las 19:00 y las 24:00 hora de Colombia.** Las otras 19 horas del día,
UTC y hora local coinciden en la fecha y todo pasa en verde. Es un fallo de ventana horaria,
y por eso sobrevivió a un paso que se declaró `done` con la puerta supuestamente verde —
probablemente ejecutada por la mañana.

### Impacto real en producción

Durante esas cinco horas diarias, **toda fila que tome su fecha por defecto de la base queda
sellada con el día siguiente**, y al releerla el validador de dominio la rechaza con
`ValidationError`. Afecta a `registro_comportamiento.fecha`, `entradas_seguimiento.fecha`,
`control_diario`, `notas.fecha_registro`, `observaciones_periodo.fecha_registro` y
`estudiantes.fecha_ingreso`: la asistencia y los registros de convivencia creados a esa hora
quedan fechados un día después, o directamente no se pueden releer.

### Consecuencia para esta épica

**Ningún paso de este backlog puede declararse `done` mientras esto siga así**, porque el
criterio es `python scripts/init.py` completamente verde y la puerta está en rojo cinco horas
al día. Hay que decidir entre reabrir `datos_08` o abrir un paso correctivo, y hacerlo antes
que `obs_01`.

---

## 1. El hallazgo central: la huella hoy

Conteo sobre `src/services/*.py` — métodos públicos que escriben en la base frente a los
que registran la operación:

| Servicio | Métodos que escriben | Con huella |
|---|---|---|
| `infraestructura_service` | 37 | **0** |
| `convivencia_service` | 21 | **0** |
| `restriccion_generacion_service` | 14 | **0** |
| `catalogo_academico_service` | 11 | **0** |
| `configuracion_service` | 7 | **0** |
| `plan_estudios_service`, `escenario_horario_service` | 5 c/u | **0** |
| `sala_service`, `franja_service` | 4 c/u | **0** |
| `horario_service`, `asistencia_service` | 3 c/u | **0** |
| `institucion_service` | 2 | **0** |
| `plan_mejoramiento`, `nivelacion`, `alerta`, `aprovisionamiento` | 1 c/u | **0** |
| `evaluacion`, `usuario`, `estudiante`, `asignacion`, `periodo`, `cierre` | ~32 | sí |
| `habilitacion_service` | 3 | código sí, **efecto 0** (§2.1) |

**Aproximadamente 118 de 137 métodos que persisten datos no dejan ningún rastro.** El dato
de producción lo confirma: `audit_log` contiene **6 filas** frente a 60.480 notas y 3.920
registros de asistencia.

Lo que queda sin huella incluye **toda la convivencia** —observaciones, comportamiento y
seguimiento, es decir el material de Ley 1620— y **toda la asistencia**. Son los dos
módulos con exposición legal directa y la puerta de entrada comercial del producto.

> El conteo procede de heurística sobre nombres de método. El inventario autoritativo lo
> producirá `scripts/check_auditoria.py` (paso `obs_02_puerta_huella`) por análisis AST.

---

## 2. Auditoría de negocio

### Lo que existe y funciona

- `src/domain/models/auditoria.py` — dos bitácoras append-only: `EventoSesion` (tabla
  `auditoria`, eventos de sesión y gestión de usuarios) y `RegistroCambio` (tabla
  `audit_log`, mutaciones de negocio con valor anterior y nuevo).
- `src/domain/policies/audit_chain.py` — cadena SHA-256 encadenada, dominio puro.
  `primer_eslabon_roto()` localiza la primera alteración. Su docstring documenta la
  limitación conocida: detecta edición, inserción y borrado intermedio, **no** el truncado
  del final, que exigiría un ancla externa.
- `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` — encadenamiento correcto,
  incluso en lotes (`registrar_cambios_masivos`).
- `src/services/auditoria_service.py` — `verificar_integridad()`, `listar_*`, `resumen_uso()`.
- `/admin/auditoria` — consulta con filtros, badge de integridad y verificación bajo demanda.
- Trigger `tg_actualizar_ultima_sesion` sobre `auditoria` para `LOGIN_EXITOSO`.

El diseño es sólido. El problema es todo lo que no llega hasta él.

### 2.1 Defectos verificados

**`HabilitacionService` audita a la nada.**
El servicio acepta `auditoria: IAuditoriaRepository | None = None` y su `_auditar` hace
`if self._auditoria is None: return`. Pero `container.py:431-435` lo construye con
`repo=`, `cierre_repo=` y `config_repo=` — **sin `auditoria=`**. Sus cuatro llamadas a
`_auditar` son no-ops silenciosos en producción. Ninguna habilitación queda registrada.

**`audit_log.institucion_id` es siempre NULL.**
`AuditoriaService.registrar_evento()` autorrellena la institución desde `contexto_tenant`,
pero los servicios llaman a `self._auditoria.registrar_cambio(...)` directamente al
repositorio, saltándose el servicio. Y las tres factories de `RegistroCambio`
(`auditoria.py:243-296`) no aceptan ni asignan el campo. La columna existe, el índice
existe (`schema.py:1354`) y el filtro del repo existe (`sqlite_auditoria_repo.py:306-308`),
pero **nunca se puebla**: la auditoría de cambios no es consultable por tenant.

**`ACCESO_DENEGADO` no se emite nunca.**
El valor está en `TipoEventoSesion`, en el `CHECK` de SQL (`schema.py:1048`), tiene
propiedad `es_acceso_denegado` y lo cuenta `resumen_uso()`. Pero `route_guard.py:255-260`
solo hace `toast_error("Acceso no autorizado")` y redirige. Lo mismo
`contexto_tenant.verificar_pertenencia()` y `solo_lectura.verificar_escritura()`: lanzan
la excepción sin registrar nada.
**Un intento de acceso cross-tenant o de escalada de privilegios no deja rastro alguno.**

**`LOGOUT` no se emite nunca.** Definido en el enum y en el `CHECK`, sin un solo call site:
`pagina_logout()` limpia el storage y navega.

**`ip_address` es siempre NULL.** Está en el modelo (`auditoria.py:89`), en la tabla
(`schema.py:1051`), en el payload del hash (`sqlite_auditoria_repo.py:71`) y se pinta en la
UI (`admin/auditoria.py:208` → `e.ip_address or "—"`). Ningún call site la rellena. NiceGUI
3.15 sí expone `ui.context.client.request`, así que es obtenible.

### 2.2 Defectos estructurales

**El actor viaja a mano.** No existe ContextVar de actor: unas 40 llamadas pasan
`usuario_id=ctx.usuario_id` explícitamente. Si una se olvida, la fila se escribe con
`usuario_id = NULL` **sin error ni aviso**. Una huella anónima es casi no tener huella.
Contrasta con `solo_lectura` y `contexto_tenant`, que resuelven exactamente este problema
con ContextVar sembrada en un único choke point (`SessionContext.desde_storage()`).

**`_auditar` está copiado literalmente 7 veces** (`usuario_service.py:72-93`,
`estudiante_service.py:87-108`, `evaluacion_service.py:90-111`, y cuatro más). Cualquier
arreglo transversal hay que hacerlo siete veces.

**Las escrituras de auditoría fallan en silencio.** Varias van envueltas en
`except Exception: pass` con el comentario "la auditoría no debe bloquear la operación de
UI" (`session_context.py:320-322`, `auditoria_service.py:49-50`). No bloquear es correcto;
perder el aviso no: la bitácora puede llevar meses sin escribir sin que nadie lo note.

**`ON CONFLICT REPLACE` destruye la huella anterior.** En diez tablas (`notas`,
`puntos_extra`, `control_diario`, `cierres_periodo`, `cierres_anio`, `promocion_anual`,
`notas_corte_plan`, `notas_actividad_plan`, `notas_nivelacion`,
`nota_comportamiento_periodo`) un INSERT duplicado borra la fila previa —con su
`usuario_registro_id` y su `fecha_registro`— sin dejar rastro en `audit_log`.

### 2.3 Código implementado sin consumidor

- `resumen_uso()` y `ResumenUsoDTO` — KPIs de uso escritos "para el dashboard de admin";
  el refactor de `inicio.py` a `_ADMIN_CARDS` dejó el consumidor por el camino.
- `contar_fallos_recientes()` y `get_ultimo_login()` — solo se ejercitan en tests; el
  throttle real usa un diccionario en memoria.
- `verify_db_integrity()` y `get_db_stats()` — exportados y nunca invocados.

---

## 3. Logging y observabilidad

### Configuración

Centralizada y correcta en `config.py:265-286` (`configure_logging()`), invocada una sola
vez desde `main.py:311`. A partir de ahí:

| Aspecto | Estado |
|---|---|
| Formato | Texto plano `asctime \| levelname \| name \| message`. No estructurado. |
| Destino | **Solo consola.** `LOG_FILE` por defecto `None`, y no aparece en `.env.example` (que solo trae `LOG_LEVEL`). |
| Rotación | **No existe.** Usa `logging.FileHandler`, no `RotatingFileHandler`. |
| Retención | No existe. |
| Estructurado | Sin `structlog` ni `loguru`. |
| Manejador global | **No existe** `sys.excepthook` ni hook de NiceGUI/FastAPI. |

### Cobertura, muy asimétrica

- **Interfaz**: ~30 de 35 páginas tienen logger. Es la capa mejor instrumentada.
- **Servicios**: **3 de 35**. Sin instrumentar quedan `usuario_service`,
  `evaluacion_service`, `cierre_service`, `convivencia_service`, `asistencia_service` y
  veintitantos más.
- **Repositorios**: **0 de 21**. Además no pasan por `queries.py` (usan `conn.execute`
  directo), así que sus consultas no se loguean en ningún sitio.
- **Autenticación**: `bcrypt_auth_service.py` y `jwt_handler.py` no loguean nada.

### Calidad de las llamadas

`logger.exception()` aparece **4 veces en todo el repositorio**. De unas 450 llamadas de
log, la inmensa mayoría registra solo `str(exc)` sin traza: un `AttributeError` en un
servicio aparece como una línea suelta, sin stack. Hay **31 bloques `except Exception:`
seguidos de `pass`** sin registro alguno.

Nota positiva: la notificación al usuario sí está unificada — 674 llamadas a `toast_*`
frente a 6 `ui.notify` directos.

### Observabilidad de sistema

- `/health` (`main.py:80-82`) devuelve `{"status": "ok", "version": ...}` **estático**:
  responde 200 aunque la base esté corrupta o el Container roto.
- `Container.diagnostico()` instancia los 30 servicios y reporta OK/ERROR — pero solo se
  ejecuta `if settings.is_development`.
- `/diagnostico` muestra ese snapshot al admin.
- `init_db()` ejecuta `PRAGMA integrity_check` al arrancar.
- Sin métricas, sin APM, sin alertas operacionales, sin correlación petición↔log.

### Ya estaba especificado

`specs/seguridad_web_09_logging_alertas/requirements.md` existe con R1–R7 completos (log
JSON de eventos de seguridad, prohibición de secretos, alertas por IP, rotación con
retención de 90 días, módulo separado, append-only por permisos del SO, y test de que un
login fallido no filtra el password). Está clasificado **N1 — primer mes en producción** y
**no está implementado** ni presente en `step_list.json`.

---

## 4. Rol admin e informes

### Lo que está bien resuelto

El admin tiene cuatro rutas: `/admin/usuarios`, `/admin/instituciones`, `/admin/auditoria`
y `/diagnostico`. Es coherente con la decisión "admin = auditor técnico, no edita": la
impersonación ("Ver como") fuerza `solo_lectura = True`, y el bloqueo vive en la **capa de
servicios** vía ContextVar, no página a página. El route guard es deny-by-default con
registro único de rutas y una matriz golden testeada. El RBAC limita al admin a gestionar
únicamente directores.

### Deudas

**`src/interface/pages/admin/` es un nombre histórico, no un rol.** De sus once páginas el
admin solo entra a cuatro; las otras siete pertenecen a director, coordinador o profesor, y
**sus docstrings mienten** sobre el rol de acceso — resto del refactor `paso_35`, cuando los
guards pasaron de estar por página a estar en el registro central.

**`/admin/auditoria` está incompleta**: no expone filtro por institución (el
`FiltroAuditoriaDTO` lo tiene y el repositorio lo soporta; el presenter nunca lo asigna), y
no pagina de verdad — `_POR_PAGINA = 100` es un techo silencioso y `set_pagina()` existe sin
controles en la UI. Con huella universal esto pasa de incómodo a inutilizable.

**El admin no tiene KPIs de uso** (§2.3), **ni visor de logs, ni vista de estado de la base,
ni backup/restore.**

### Informes: lo que existe

Cinco páginas más el tablero estadístico; nueve tipos de estadístico con vista previa y
exportación; boletín de periodo, acumulado y anual, individual y masivo (PDF fusionado con
`pypdf`, Excel con hoja por estudiante); consolidados de notas y asistencia; observador del
estudiante y reporte de convivencia por grupo. El exportador degrada en cuatro niveles
(WeasyPrint → ReportLab → openpyxl → CSV).

### Informes: el bug multi-tenant

**El boletín PDF hardcodea la institución.** Literal `"INSTITUCIÓN EDUCATIVA ZECI"` en
`boletin_pdf.py:207`, `pdf_exporter.py:150` y `openpyxl_exporter.py:195`, con el logo como
celda vacía. `InformeService.get_informacion_institucional()` se escribió justo para esto
(R16 de `datos_06_identidad_institucional`), está probado y **no tiene ni un llamador**.
Consecuencia: todo colegio recibe boletines con el membrete de otro.

Contraste útil: `observador_pdf.py:143-177` **sí** usa la identidad real (nombre, DANE,
rector, municipio, dirección, teléfono, resolución). El patrón correcto ya existe en el
repositorio; solo hay que aplicarlo al boletín.

Otras carencias menores: no hay sistema de plantillas (el HTML se construye por
concatenación de f-strings), no hay botón CSV en la UI —lo que deja inservible el fallback
`NullExporter`—, la generación masiva es síncrona sin progreso ni cancelación, y
`openpyxl`, `weasyprint`, `pypdf` y `pandas` están en `requirements.txt` pero **no en
`pyproject.toml`** (`nicegui` además está sin pinear).

---

## 5. Persistencia

### Estado sano

SQLite puro de la stdlib. `data/app.db`, 8,74 MB, fuera de git. **64 tablas, 110 índices
explícitos y 6 triggers: la base viva coincide exactamente con `schema.py`, sin drift.**
PRAGMAs correctos: `journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`,
`cache_size=-64000`, `check_same_thread=False`.

Arquitectura limpia: 21 puertos `I*Repository` y 21 adaptadores `Sqlite*Repository`,
instanciados solo en `container.py`. Mapeo fila→modelo Pydantic explícito. **Cero usos de
`.dict()`**. `scripts/check_enums.py` en verde: 35 pares enum↔CHECK alineados, 0
divergencias, 5 deudas declaradas y 2 exenciones.

Estado del proyecto: `step_list.json` con 15 pasos, todos `done`; `progress/current.md`
vacío. SQLAlchemy **no ha empezado** — cero imports en `src/`, y ninguna spec `backend_*`
redactada todavía.

### 5.1 Entradas obligatorias para `backend_04_metadata_schema`

Por decisión de arquitectura (CLAUDE.md: sin migraciones; los `CHECK` se generan en
`backend_04`), estos defectos **no se corrigen ahora**. Se registran aquí para que
`backend_04` los resuelva de raíz.

| # | Hallazgo | Evidencia | Impacto |
|---|---|---|---|
| **D1** | El orden declarado de `SCHEMA` viola su propio docstring ("una tabla solo aparece después de las que referencia"): `grupos` (L211) referencia `usuarios` (L245); `observaciones_periodo` (L860) referencia `registro_comportamiento` (L889). Verificado que **no** es un ciclo. | `schema.py:3-5, 226, 879` | SQLite tolera FKs adelantadas. **Un replay del DDL en el orden declarado sobre PostgreSQL falla.** `create_all()` ordena solo, pero el contrato del fichero es falso. |
| **D2** | `grupos.sala_id` es una **FK fantasma**: columna declarada sin `FOREIGN KEY`. Confirmado en la base viva: `grupos` tiene 2 FKs, ninguna a `salas`. Igual `horarios.sala` (TEXT libre) y los `grado` sueltos. | `schema.py:219` | Un `sala_id` huérfano no lo detecta nadie. Al declarar `MetaData` hay que decidir si la relación existe. |
| **D3** | **`ON CONFLICT REPLACE` en 10 tablas.** | `schema.py:516, 535, 557, 585, 606, 696, 732, 767, 851, 937` | **No existe en PostgreSQL**: `backend_07` reescribirá los 10 casos como upsert. Además destruye la huella anterior (§2.2). |
| **D4** | 5 enumeraciones sin `CHECK`: `AccionCambio`, `Calendario`, `CategoriaPreferencia`, `JornadaPrincipal`, `TipoInstitucion`. | `scripts/check_enums.py:62-68` | Ya registradas como deuda. Es donde CLAUDE.md dice que se resuelven. |
| **D5** | **`institucion_id` es NULLABLE en 13 de las 15 tablas con scope**; 49 de 64 tablas no lo tienen, incluidas las de mayor volumen (`notas`, `control_diario`, `asignaciones`, `horarios`). | `schema.py:266-269, 314, 1064, 1085` | Una fila con NULL no la devuelve ningún `WHERE institucion_id = ?` ni la deduplica ningún `UNIQUE(institucion_id, X)`: dato huérfano invisible. Enlaza con `tenant_05` y `tenant_06`, pendientes. |
| **D6** | **Sin transacciones compuestas.** 20 de 21 repositorios: 0 `rollback`, 0 `BEGIN`; commit por método. | `sqlite_infraestructura_repo.py` (57 commits) | Un cierre de periodo, una promoción anual o un aprovisionamiento que falle a mitad deja la base inconsistente. Y **el registro de auditoría y el cambio que describe no son atómicos**. |
| **D7** | `sqlite_plan_mejoramiento_repo.py` abre `sqlite3.connect()` a mano: sin `check_same_thread=False` (riesgo de `ProgrammingError` en NiceGUI multihilo), sin WAL ni timeout, y **sin `conn` inyectable**, así que sus tests de integración golpean `data/app.db` real. | `sqlite_plan_mejoramiento_repo.py:27-38` | Único repositorio desviado del patrón. Normalizarlo antes de migrarlo. |
| **D8** | `queries.py` traga toda excepción y devuelve valores benignos: `fetch_df`→DataFrame vacío, `fetch_one`→`None`, `fetch_all`→`[]`, **`execute`→`False`**. Además ignoran la conexión inyectada. | `queries.py:66, 100, 137, 176, 233` | Una escritura fallida (FK, CHECK, disco lleno) devuelve `False` y solo deja un `logger.error`. Si el llamador no comprueba el retorno, la pérdida de datos es silenciosa. |
| **D9** | **9 funciones `_migrate_*` con `ALTER TABLE ADD COLUMN` viven en `seed.py`**, y solo corren dentro de `seed_base`/`seed_dev`, que `main.py` solo invoca si la base está vacía de grupos. | `seed.py:459, 556, 595, 608, 621, 635, 648, 1905, 1922` | Contradice "sin migraciones" y explica desfases silenciosos: una base de desarrollo poblada nunca recibe columnas nuevas. |
| **D10** | `tg_proteger_nota_periodo_cerrado` es solo `BEFORE INSERT`. | `schema.py:1452` | Un `UPDATE notas SET valor` en un periodo cerrado pasa sin bloqueo. |
| **D11** | **Cero tests de esquema.** Ninguno compara `SCHEMA` contra `sqlite_master`, ni verifica FKs, índices, triggers u orden de creación. | `tests/conftest.py:81-190` solo *aplica* el DDL | D1 y D2 llevaban meses ocultos precisamente por esto. Sin esto, `backend_04` migra a ciegas. |
| **D12** | Higiene: `init_db(db_path=...)` ignora su parámetro (`schema.py:1508` vs `:1527`); `DB_TIMEOUT`/`DB_JOURNAL_MODE` de `config.py` no se consumen (`connection.py` los hardcodea); `RESTRICCIONES_DEUDA` quedó con 5 entradas muertas tras `datos_05`; `check_enums` empareja por conjunto de valores, lo que produce falsos positivos (`boletines_emitidos.tipo` ↔ `TipoHabilitacion`). | varias | Ruido que conviene limpiar antes de la migración; el punto de `RESTRICCIONES_DEUDA` puede enmascarar regresiones futuras. |

### 5.2 Campos de auditoría en las tablas

**No existe convención.** `creado_en`, `actualizado_en` y `creado_por` no aparecen en
ningún sitio. Lo que hay es un mosaico: `fecha_creacion` en 2 tablas, `created_at` en 3,
`updated_at` en **1 sola**, `fecha_registro` en 3, `usuario_registro_id` en 6, y unas 15
columnas `usuario_*_id` dispersas.

**Ninguna tabla tiene el trío completo. 56 de 64 tablas no tienen marca de creación.**
El soft-delete se hace con un flag `activo`/`activa`, que es estado, no borrado auditado:
no guarda quién ni cuándo desactivó.

---

## 6. Plan de corrección

Registrado en `step_list.json` como ocho pasos en `spec_ready`. Los tres primeros tienen
spec redactada.

| # | ID | Qué resuelve |
|---|---|---|
| 1 | `obs_01_huella_actor` | §2.1 y §2.2: cableado, actor en contexto, helper único, eventos que faltan. |
| 2 | `obs_02_puerta_huella` | Puerta `check_auditoria.py` con lista de deuda: convierte la cobertura en invariante. |
| 3 | `obs_03_security_logger` | §3: implementa S09 (log JSON, rotación, alertas), más `/health` real. |
| 4–6 | `obs_04a/b/c_huella_*` | §1: los ~118 métodos sin huella, en tres tramos por riesgo. |
| 7 | `informes_01_identidad_boletin` | §4: el bug multi-tenant del membrete. |
| 8 | `obs_05_admin_auditoria_ui` | §4: filtro por institución, paginación real, KPIs de uso. |

Fuera de alcance y registrado: auditoría de lecturas (`AccionCambio.READ`), acotada a datos
sensibles; Sentry/OpenTelemetry; visor de logs en la UI; backups (spec S10, ya existe);
archivado de la bitácora —con huella universal `audit_log` crecerá decenas de miles de filas
al año y borrar rompería la cadena SHA-256, así que es entrada de `backend_04`—; y los
doce puntos de §5.1.
