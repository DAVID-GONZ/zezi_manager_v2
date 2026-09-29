# Requisitos: backend_12_endpoints_crud

> Ambito: endpoints CRUD que exponen los servicios existentes como API REST.
> Los servicios no se modifican: los endpoints son una capa delgada que
> valida input, llama al servicio y serializa el resultado.
>
> DEPENDE de backend_10 (router montado) y backend_11 (auth JWT).
>
> Magnitud: 34 servicios, ~500 metodos. Se implementan en 3 olas por
> prioridad de negocio, empezando por lo que el frontend Vue necesita
> primero.

---

## Principio de diseno

R1: CADA endpoint DEBE ser una capa delgada: validar request -> llamar
    a `Container.*_service().metodo()` -> serializar response. No
    duplicar logica de negocio en la API.

R2: LOS endpoints DEBEN reusar los servicios tal cual, a traves de
    `Container`. Los servicios ya manejan TenantScope, auditoria y
    validaciones de dominio.

R3: CADA modulo de negocio DEBE tener su propio router en
    `src/api/routes/<modulo>.py` y sus schemas en
    `src/api/schemas/<modulo>.py`.

---

## Ola 1 — Core (bloqueante para el frontend Vue)

R4: Endpoints de **autenticacion** (ya en backend_11):
    - `POST /auth/login`

R5: Endpoints de **usuarios** (admin):
    - `GET /usuarios` — listar (paginado, filtro por rol/institucion)
    - `GET /usuarios/{id}` — detalle
    - `POST /usuarios` — crear
    - `PUT /usuarios/{id}` — actualizar
    - `PATCH /usuarios/{id}/password` — resetear password
    - `PATCH /usuarios/{id}/toggle-activo` — activar/desactivar

R6: Endpoints de **estudiantes**:
    - `GET /estudiantes` — listar (paginado, filtro por grupo)
    - `GET /estudiantes/{id}` — detalle con acudientes
    - `POST /estudiantes` — crear
    - `PUT /estudiantes/{id}` — actualizar
    - `POST /estudiantes/carga-masiva` — Excel (multipart)
    - `DELETE /estudiantes/{id}` — desactivar (soft delete)

R7: Endpoints de **contexto academico** (configuracion, periodos, grupos):
    - `GET /instituciones/actual` — datos de la institucion del tenant
    - `GET /periodos` — listar periodos del anio activo
    - `GET /grupos` — listar grupos (filtro por nivel/jornada)
    - `GET /asignaturas` — listar asignaturas del plan
    - `GET /asignaciones` — listar (filtro por profesor/grupo/asignatura)

---

## Ola 2 — Modulos de negocio criticos

R8: Endpoints de **asistencia**:
    - `GET /asistencia/control-diario` — estado del dia por grupo
    - `POST /asistencia/registrar` — registrar/actualizar (lote)
    - `GET /asistencia/resumen` — resumen por grupo/periodo

R9: Endpoints de **convivencia**:
    - `GET /convivencia/observaciones` — listar (paginado)
    - `POST /convivencia/observaciones` — crear
    - `PUT /convivencia/observaciones/{id}` — actualizar
    - `GET /convivencia/seguimiento/{estudiante_id}` — perfil 360
    - `GET /convivencia/comportamiento/{grupo_id}` — por grupo/periodo
    - `GET /convivencia/notas/{grupo_id}` — notas de convivencia

R10: Endpoints de **evaluacion**:
     - `GET /evaluacion/planilla` — planilla por grupo/asignatura/periodo
     - `POST /evaluacion/notas` — guardar notas (lote)
     - `GET /evaluacion/cierre-periodo` — estado del cierre
     - `POST /evaluacion/cierre-periodo/ejecutar` — cerrar periodo

---

## Ola 3 — Informes, configuracion y admin

R11: Endpoints de **informes**:
     - `GET /informes/boletin-periodo/{estudiante_id}` — PDF (stream)
     - `GET /informes/boletin-anual/{estudiante_id}` — PDF (stream)
     - `GET /informes/consolidado-notas` — Excel (stream)
     - `GET /informes/consolidado-asistencia` — Excel (stream)

R12: Endpoints de **configuracion**:
     - `GET /configuracion/siee` — configuracion del SIEE
     - `PUT /configuracion/siee` — actualizar SIEE
     - `GET /configuracion/anio` — configuracion del anio
     - `GET /configuracion/preferencias` — preferencias de la institucion
     - `PUT /configuracion/preferencias` — actualizar

R13: Endpoints de **auditoria** (admin/director):
     - `GET /auditoria/eventos` — listar eventos (paginado)
     - `GET /auditoria/cambios` — listar cambios (paginado)
     - `GET /auditoria/integridad` — verificar cadena
     - `POST /auditoria/exportar` — exportar (stream CSV)

---

## Schemas de response

R14: LOS schemas de response NO DEBEN exponer campos sensibles:
     `password_hash`, `password_temporal`, `storage_secret`, ni
     campos internos de infraestructura.

R15: LOS schemas DEBEN usar campos snake_case, consistentes con el
     dominio Python. El frontend Vue adapta a camelCase en su capa.

R16: LAS listas paginadas DEBEN retornar:
     `{"items": [...], "total": N, "page": P, "per_page": PP}`.

---

## Lotes y offline

R17: LOS endpoints de escritura criticos (asistencia, notas,
     observaciones) DEBEN aceptar arrays de registros con timestamp
     para futura sincronizacion offline. Formato:
     `{"registros": [{"...": "...", "timestamp_local": "ISO8601"}]}`.

R18: EL backend DEBE idempotizar por clave natural
     (estudiante_id + fecha + asignatura_id para notas/asistencia)
     cuando recibe un lote con registros potencialmente duplicados.

---

## OpenAPI

R19: AL cerrar el paso, `GET /api/openapi.json` DEBE retornar un
     spec OpenAPI 3.1 valido con todos los endpoints, schemas y
     ejemplos. Este spec es la entrada de `avedra-shared-contracts`.

---

## Fuera de alcance

- Horarios (modulo complejo con generador; postergar a ola 4).
- Portal (consume providers internos; postergar).
- Deploy ni base de datos (backend_13).
