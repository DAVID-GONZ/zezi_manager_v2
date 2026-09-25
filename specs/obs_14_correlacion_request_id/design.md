# Diseño: Correlación por request_id (obs_14)

> **Requisitos:** `requirements.md` de esta misma carpeta.
> **Nivel N3 — diferido.** Se implementa con la API REST de `backend_00`.

## 1. Archivos a crear y modificar

| Archivo | Operación | Responsabilidad |
|---|---|---|
| `src/services/contexto_peticion.py` | crear | `ContextVar` del identificador. Stdlib puro. |
| `main.py` | modificar | Middleware que abre y cierra el contexto; manejador global. |
| `src/interface/context/event_context.py` | modificar | Resincronización en event handlers. |
| `src/domain/models/auditoria.py` | modificar | `request_id` en `EventoSesion` y `RegistroCambio`. |
| `src/infrastructure/db/schema.py` | modificar | Columna en ambas tablas. |
| `src/infrastructure/db/repositories/sqlite_auditoria_repo.py` | modificar | INSERT/SELECT; **fuera** del payload firmado. |
| `src/infrastructure/logging/security_logger.py` | modificar | Campo en la whitelist. |
| `src/services/auditoria_helpers.py` | modificar | Resuelve el identificador del contexto. |
| `src/services/observabilidad_service.py` | modificar | `traza_de(request_id)`. |
| `src/interface/pages/admin/observabilidad.py` | modificar | Búsqueda por identificador. |

## 2. Un contexto más, con el mismo patrón

El proyecto tiene ya tres `ContextVar` neutrales —`contexto_actor`,
`contexto_tenant`, `solo_lectura`— con la misma forma: estado privado, API de
funciones, sin importar interfaz ni infraestructura. `contexto_peticion.py` es
el cuarto y se escribe igual, para que no haya que aprender nada nuevo.

```python
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "zeci_request_id", default=None
)


def abrir_peticion() -> str:
    """Genera y fija un identificador. Único punto de creación (R2)."""
    rid = uuid.uuid4().hex[:16]     # opaco, sin datos personales (R3)
    _request_id.set(rid)
    return rid


def request_id() -> str | None:
    """Identificador de la petición en curso, o None fuera de una."""
    return _request_id.get()
```

`abrir_peticion` no se exporta a los servicios: el único llamador legítimo es
el middleware. Si un servicio necesitara un identificador y no lo hay, el campo
va nulo — inventar uno a mitad de camino produciría una correlación falsa, que
es peor que ninguna.

## 3. Dónde se abre

Con NiceGUI hay dos puertas: la petición HTTP que renderiza la página y el
event handler del websocket. `tenant_01` ya resolvió el segundo caso para los
demás `ContextVar` envolviendo `Client.handle_event`; el identificador se suma
a esa resincronización, con un matiz: cada **evento** abre su propia petición
lógica. Un clic es una unidad de trabajo correlacionable; toda una sesión de
websocket no lo es.

El middleware HTTP cubre el primer caso y es el que `backend_00` necesitará
para R7: si llega una cabecera de correlación bien formada —hexadecimal, 16
caracteres— se adopta; si no, se genera. Validar el formato antes de adoptarla
evita que un cliente inyecte contenido arbitrario en el log.

## 4. Fuera del hash (R9)

```python
@staticmethod
def _payload_cambio(registro: RegistroCambio) -> dict:
    # request_id NO entra: es metadato de correlación, no el hecho auditado.
    # Mismo criterio que institucion_id (mejora_07-T7).
    ...
```

El criterio se escribe en el comentario del DDL junto al de `institucion_id`,
donde ya está el precedente. La distinción es sustantiva: `usuario` e
`ip_address` entraron en el hash en `obs_06` porque falsearlos falsea de quién
fue el hecho; falsear un `request_id` solo estropea una correlación, y
meterlo en el hash obligaría a recrear la base una vez más sin ganar
integridad real.

## 5. Traza unificada

```python
def traza_de(self, request_id: str) -> TrazaDTO:
    """
    Reúne en una sola vista todo lo que compartió esa petición:
    entradas de log, eventos de sesión y cambios de datos, ordenados
    cronológicamente.
    """
```

El lector de log de `obs_13` filtra por el campo; las dos tablas, por columna
indexada. Se añade un índice por `request_id` en ambas: sin él, la búsqueda
sería un escaneo completo sobre la tabla que más crece.

## 6. Respuesta de error (R6)

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    rid = request_id()
    _log_main.exception("Excepcion no capturada [%s]: %s", rid, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno", "referencia": rid},
    )
```

El usuario recibe una referencia que puede comunicar al soporte; el soporte la
busca en el panel y obtiene la traza completa. No se filtra ningún detalle
interno: el identificador es opaco por construcción.

## 7. Alternativa descartada

**Correlacionar por `(usuario_id, marca de tiempo)` sin columna nueva.**
No cuesta nada y funciona a ojo mientras el sistema tenga un usuario activo
cada vez. Se descarta porque falla exactamente cuando hace falta: bajo carga,
con varios usuarios simultáneos y con operaciones que escriben decenas de
filas en el mismo segundo, que es el escenario en el que alguien necesita
reconstruir qué pasó. Una clave explícita es una columna y un índice; la
alternativa es una heurística que se rompe justo el día malo.

## 8. Orden de implementación recomendado

1. `contexto_peticion.py` + test de aislamiento entre tareas concurrentes.
2. Middleware HTTP y enganche en `event_context.py`.
3. Columna, índice, modelos y repositorio (fuera del payload firmado).
4. Whitelist del logger y `auditar_cambio`.
5. Manejador global de excepciones.
6. `traza_de` y la búsqueda en el panel de observabilidad.
