# Diseno: backend_12_endpoints_crud

## Punto de partida medido

| Superficie | Cantidad |
|---|---|
| Servicios en Container | 34 |
| Metodos de servicio publicos | ~500 |
| Repos SQLAlchemy Core | 20 |
| Modelos de dominio con computed_field | 123 |
| Excepcion base con codigo estable | AvedraError (datos_01) |

## D1 — Estructura de archivos

```
src/api/
  routes/
    __init__.py
    auth.py           # (ya en backend_11)
    usuarios.py
    estudiantes.py
    contexto.py       # instituciones, periodos, grupos, asignaturas, asignaciones
    asistencia.py
    convivencia.py
    evaluacion.py
    informes.py
    configuracion.py
    auditoria.py
  schemas/
    __init__.py
    auth.py           # (ya en backend_11)
    common.py         # (ya en backend_10)
    usuarios.py
    estudiantes.py
    contexto.py
    asistencia.py
    convivencia.py
    evaluacion.py
    informes.py
    configuracion.py
    auditoria.py
```

## D2 — Patron de endpoint

Cada endpoint sigue el mismo patron:

```python
@router.get("/{id}", response_model=EstudianteResponse)
def obtener_estudiante(
    id: int,
    user: CurrentUserDTO = Depends(get_current_user),
):
    scope = TenantScope.desde_rol(user.rol, user.institucion_id)
    svc = Container.estudiante_service()
    estudiante = svc.obtener(id, scope)
    if estudiante is None:
        raise HTTPException(404)
    return estudiante
```

- Sin logica de negocio.
- TenantScope construido desde el JWT.
- Servicio obtenido de Container.
- El schema de response filtra campos sensibles.

## D3 — TenantScope desde JWT

```python
def scope_from_user(user: CurrentUserDTO) -> TenantScope:
    from src.domain.models.tenant import TenantScope
    if user.rol == "admin":
        return TenantScope.todos()
    return TenantScope(user.institucion_id)
```

Esta funcion vive en `deps.py` y la usan todos los endpoints.

## D4 — Paginacion estandar

```python
class PaginationParams:
    def __init__(self, page: int = 1, per_page: int = 25):
        self.page = max(1, page)
        self.per_page = min(100, max(1, per_page))
        self.offset = (self.page - 1) * self.per_page
```

Todos los endpoints de listado aceptan `page` y `per_page` como query
params y retornan `PaginatedResponse`.

## D5 — Schemas de response por modulo

Los schemas NO son los modelos de dominio. Son proyecciones explicitas:

```python
class EstudianteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombres: str
    apellidos: str
    documento: str
    grupo_nombre: str | None
    edad: int | None  # computed_field del dominio

    # Excluidos: password, campos internos
```

Para hidratacion desde objetos de dominio: `EstudianteResponse.model_validate(obj)`.
Para hidratacion desde dicts: `EstudianteResponse(**dict)`.

## D6 — Streaming de archivos (informes)

```python
from fastapi.responses import StreamingResponse

@router.get("/boletin-periodo/{estudiante_id}")
def boletin_periodo(estudiante_id: int, ...):
    bytes_pdf = Container.informe_service().generar_boletin_periodo(...)
    return StreamingResponse(
        io.BytesIO(bytes_pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=boletin_{estudiante_id}.pdf"},
    )
```

## D7 — Lotes con idempotencia

Para asistencia y notas, el endpoint recibe un array:

```python
class RegistroAsistenciaLote(BaseModel):
    registros: list[RegistroAsistenciaItem]

class RegistroAsistenciaItem(BaseModel):
    estudiante_id: int
    fecha: date
    estado: str
    timestamp_local: datetime | None = None
```

La idempotencia la maneja el servicio existente: `registrar_asistencia`
ya hace upsert por (estudiante_id, fecha) desde backend_07 (D3 del schema).

## D8 — Exportacion del OpenAPI spec

Al cerrar el paso, un script extrae el spec:

```python
# scripts/export_openapi.py
import json
from main import crear_app  # o equivalente
app = crear_app()
spec = app.openapi()
with open("openapi/avedra-openapi.json", "w") as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)
```

## Alternativas descartadas

**GraphQL.** Anade complejidad (schema SDL, resolvers, N+1) sin
beneficio para un equipo de uno. REST con OpenAPI cubre las necesidades
y el spec se genera automaticamente.

**Autogenerar schemas desde modelos.** Los modelos de dominio tienen
123 @computed_field y campos internos. Una proyeccion explicita es mas
segura que un `exclude` que se olvida.
