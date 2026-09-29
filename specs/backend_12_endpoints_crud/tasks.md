# Tareas: backend_12_endpoints_crud

> SCOPE — archivos que pueden editarse:
> `src/api/routes/` (crear), `src/api/schemas/` (crear),
> `src/api/deps.py`, `src/api/router.py`,
> `tests/unit/interface/api/`, `scripts/export_openapi.py` (crear).
>
> Fuera de scope: servicios, repositorios, modelos de dominio, paginas NiceGUI.
> Si un servicio necesita un metodo nuevo para la API -> PARAR y reportar.
>
> DEPENDE de backend_10 y backend_11.
>
> SE DIVIDE EN 3 OLAS. Cada ola es autocontenida y se puede marcar done.

---

## OLA 1 — Core (usuarios, estudiantes, contexto academico)

### T1 — Dependencias compartidas (deps.py)

Anadir a `deps.py`:
- `scope_from_user(user) -> TenantScope`
- `PaginationParams` como clase inyectable via `Depends`

**Verificacion:** importar sin errores.

---

### T2 — Schemas de usuarios y estudiantes

Crear `schemas/usuarios.py` y `schemas/estudiantes.py` con los
response models para listado y detalle. Incluir `schemas/contexto.py`
para instituciones, periodos, grupos, asignaturas, asignaciones.

**Verificacion:** cada schema valida con datos de ejemplo del seed_dev.

---

### T3 — Router de usuarios

Crear `routes/usuarios.py` con los 6 endpoints de R5.
Protegido con `require_role("admin")` para escritura,
`require_role("admin", "director")` para lectura.

**Verificacion:** test con TestClient: listar, crear, obtener, actualizar.

---

### T4 — Router de estudiantes

Crear `routes/estudiantes.py` con los 6 endpoints de R6.
Incluye la carga masiva por Excel (multipart).

**Verificacion:** test con TestClient: CRUD completo. La carga masiva
recibe un archivo y retorna el conteo de insertados/errores.

---

### T5 — Router de contexto academico

Crear `routes/contexto.py` con los 5 endpoints de R7 (instituciones,
periodos, grupos, asignaturas, asignaciones). Solo lectura.

**Verificacion:** test con TestClient: cada endpoint retorna datos
del seed_dev con TenantScope aplicado.

---

### T6 — Verificacion Ola 1

Registrar los 3 routers en `router.py`. Ejecutar `scripts/init.py`.
OpenAPI en `/api/docs` muestra todos los endpoints de Ola 1.

---

## OLA 2 — Modulos de negocio (asistencia, convivencia, evaluacion)

### T7 — Schemas de asistencia, convivencia, evaluacion

Crear `schemas/asistencia.py`, `schemas/convivencia.py`,
`schemas/evaluacion.py`. Incluir schemas de lote con `timestamp_local`.

---

### T8 — Router de asistencia

Crear `routes/asistencia.py` con los 3 endpoints de R8.
`POST /registrar` acepta lote segun D7.

**Verificacion:** test: registrar 5 asistencias en lote, releer, verificar.

---

### T9 — Router de convivencia

Crear `routes/convivencia.py` con los 6 endpoints de R9.
Incluye observaciones CRUD y el perfil 360 de seguimiento.

**Verificacion:** test: crear observacion, listar, actualizar, verificar
en seguimiento.

---

### T10 — Router de evaluacion

Crear `routes/evaluacion.py` con los 4 endpoints de R10.
`POST /notas` acepta lote. Cierre de periodo es accion privilegiada.

**Verificacion:** test: guardar notas en lote, releer planilla, verificar.

---

### T11 — Verificacion Ola 2

Registrar routers en `router.py`. `scripts/init.py` verde.
Tests de integracion de los 3 modulos pasan.

---

## OLA 3 — Informes, configuracion, auditoria

### T12 — Schemas de informes, configuracion, auditoria

Crear los schemas restantes.

---

### T13 — Router de informes

Crear `routes/informes.py` con los 4 endpoints de R11.
Retornan StreamingResponse (PDF/Excel).

**Verificacion:** descargar un boletin PDF via curl, verificar que es valido.

---

### T14 — Router de configuracion

Crear `routes/configuracion.py` con los 5 endpoints de R12.

---

### T15 — Router de auditoria

Crear `routes/auditoria.py` con los 4 endpoints de R13.
Solo accesible por admin/director.

---

### T16 — Script export_openapi.py

Crear `scripts/export_openapi.py` segun D8. Ejecutarlo genera
`openapi/avedra-openapi.json` con el spec completo.

**Verificacion:** el JSON es un OpenAPI 3.1 valido (validar con
`openapi-spec-validator` o `python -c "import json; json.load(open(...))"` +
verificacion de estructura).

---

### T17 — Verificacion final y cierre

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. OpenAPI spec exportado. Todos los endpoints documentados.

**Artefacto:** `progress/impl_backend_12.md`.
