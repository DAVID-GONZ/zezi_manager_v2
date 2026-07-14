# Registro de decisiones de arquitectura (ADR)

> Bitácora de las decisiones estructurales de ZECI Manager v2.0. Cada entrada
> resume el problema, la decisión y su consecuencia. Complementa
> `docs/architecture.md` (el *qué* vigente) explicando el *por qué*.
> Las decisiones de seguridad puntuales viven en `docs/seguridad.md`.

---

## ADR-001 — Arquitectura Limpia / Puertos y Adaptadores

**Contexto.** v1.0 mezclaba SQL, cálculo de negocio y UI en `pages/`/`modules/`.

**Decisión.** Separar en cuatro capas con dependencia unidireccional
`interface → services → domain ← infrastructure`. El dominio no importa nada
externo; la infraestructura implementa sus puertos (`ABC`).

**Consecuencia.** Testeo aislado por capa; `init.py` incluye un gate de
anti-patrones que falla si un import cruza la frontera. Ver `architecture.md` §1.

---

## ADR-002 — SQLite con SQL crudo (sin ORM)

**Decisión.** Persistencia en SQLite con `sqlite3` y SQL crudo, no un ORM.

**Consecuencia.** Control fino de consultas y agregados (`GROUP BY` en el repo),
menos dependencias. `pandas` queda **confinado a infraestructura**: los repos
mapean `DataFrame → entidad Pydantic`; servicios y páginas nunca ven DataFrames.

---

## ADR-003 — Pydantic v2 en dominio y configuración

**Decisión.** Entidades de dominio y `Settings` (config) como modelos Pydantic v2
(`model_dump()`, `@field_validator`/`@model_validator`, nunca `.dict()`).

**Consecuencia.** Validación estricta en runtime; el reviewer rechaza `.dict()`.

---

## ADR-004 — Container como composition root único

**Decisión.** `container.py` es el único punto de instanciación (singleton lazy
por nombre, imports perezosos). Páginas y servicios nunca instancian repos.

**Consecuencia.** Cableado de dependencias en un solo lugar; `Container.reset()`
para tests y `Container.diagnostico()` para detectar config rota al arrancar.

---

## ADR-005 — Auditoría transversal con cadena hash (M4)

**Decisión.** Todo mutador termina en `_auditar()`. Dos bitácoras append-only
(`auditoria`, `audit_log`). La integridad se protege con encadenamiento por hash
SHA-256 (`domain/policies/audit_chain.py`), calculado/verificado por el repo.

**Consecuencia.** Detectable la edición/inserción/borrado intermedio. El truncado
del final requiere un ancla externa (fuera de alcance, documentado).

---

## ADR-006 — Autorización por ruta deny-by-default (paso_35)

**Contexto.** La autorización opt-in dentro de cada página era frágil (fácil de
olvidar) y duplicaba las listas de rol en el NAV.

**Decisión.** Un guard central: toda página se registra con
`registrar_pagina(ruta, page_fn, roles=...)` donde `roles` es **obligatorio**
(sentinels `PUBLICO`/`AUTENTICADO` o `frozenset[Rol]`). El registro `{ruta:roles}`
es la única fuente de verdad y el NAV deriva de él.

**Consecuencia.** Imposible exponer una ruta sin declarar acceso. `decidir_acceso`
es una función pura testeable sin servidor. Ver `architecture.md` §7.1.

---

## ADR-007 — Modo solo lectura ("Ver como") con ContextVar (paso_21)

**Decisión.** El bloqueo de mutaciones durante la impersonación del admin es
**central** en la capa de servicios (`solo_lectura.py`), sobre un `ContextVar`
(default `False`). Los mutadores usan `@requiere_escritura`/`verificar_escritura()`.

**Consecuencia.** Comportamiento normal y tests existentes intactos (flag apagado
por defecto). El choke point de activación es `SessionContext.desde_storage()`.

---

## ADR-008 — Multi-tenant por scope de servicios (paso_24)

**Contexto.** Se necesita soportar varias instituciones sin reescribir los repos.

**Decisión.** Introducir la entidad `Institucion` (#1 por defecto). El aislamiento
se aplica por **scope de servicios** (`contexto_tenant.py`, `ContextVar`):
admin → sin scope (cross-tenant); otros → su `institucion_id`. Los repos reciben
`institucion_id` por parámetro (no importan de `services/`).
`verificar_pertenencia(id_leído_del_repo)` cierra las operaciones por `id`.

**Consecuencia.** Migración progresiva; el filtro se resuelve en el servicio, no
página por página. Ver `architecture.md` §9.

---

## ADR-009 — Secretos separados y bloqueo de arranque (M1/M3)

**Decisión.** `JWT_SECRET` y `STORAGE_SECRET` son independientes. En producción,
`config.py` bloquea el arranque si conservan su valor por defecto.

**Consecuencia.** La cookie de sesión (firmada con `STORAGE_SECRET`) y los tokens
JWT no comparten secreto. Generación de secretos documentada en `seguridad.md`.

---

## ADR-010 — bcrypt directo + throttle de proceso (A1)

**Decisión.** Hash con `bcrypt` directo (`ROUNDS=12`), no `passlib`. El freno de
fuerza bruta vive aparte, en `login_throttle.py`, con estado de **proceso**
(no `ContextVar`) para ser visible a todas las peticiones (despliegue mono-proceso).

**Consecuencia.** bcrypt encarece cada intento; el throttle lo frena (5 fallos →
bloqueo 300 s). Compatibilidad legacy con hashes `sha256:` del seed antiguo.

---

## ADR-011 — TLS por reverse proxy, JWT diferido a v3 (M2/B4)

**Decisión.** NiceGUI no termina TLS: en producción la app se sirve tras un
reverse proxy HTTPS y escucha solo en loopback. La app de escritorio no consume
JWT para autorizar (sesión en cookie firmada); la revocación de JWT se difiere a
la API REST v3.

**Consecuencia.** `main.py` emite un warning en producción. Config de nginx de
ejemplo y detalle en `seguridad.md`.

---

## ADR-012 — Selección de exportador en cascada

**Decisión.** El `Container` no fija una clase de exportador: `crear_exporter()`
elige el mejor nivel disponible (weasyprint → reportlab → openpyxl → CSV) según
las dependencias instaladas, con catch amplio para libs nativas ausentes.

**Consecuencia.** La app arranca y exporta (al menos CSV) aunque falten libs
pesadas; el nivel activo se registra en el log. Ver `infraestructura.md` §3.
