# Requisitos: backend_10_fastapi_mount

> Ambito: montar un APIRouter de FastAPI dentro de la app NiceGUI existente,
> bajo el prefijo `/api/v1`, con documentacion OpenAPI autoservida.
>
> NiceGUI internamente usa FastAPI como servidor ASGI. El objeto `app` que
> `registrar_rutas_internas()` ya recibe en `main.py:75` ES una instancia
> de FastAPI. El paso no crea una app separada: anade un router al mismo
> proceso.

---

## Router montado bajo /api/v1

R1: EL SISTEMA DEBE registrar un `APIRouter` con prefijo `/api/v1` en la
    app FastAPI que NiceGUI expone.

R2: TODOS los endpoints de la API REST DEBEN vivir bajo `/api/v1/`.
    Las rutas NiceGUI (`/login`, `/inicio`, etc.) no se tocan.

R3: EL SISTEMA DEBE exponer la documentacion OpenAPI interactiva en
    `/api/docs` (Swagger UI) y `/api/redoc` (ReDoc).

---

## Estructura de archivos

R4: EL codigo de la API DEBE vivir en `src/api/` (al mismo nivel que
    `src/interface/`, `src/services/`, `src/domain/`):
    - `router.py` — router raiz que incluye sub-routers por modulo.
    - `deps.py` — dependencias FastAPI compartidas (engine, servicios).
    - `schemas/` — esquemas Pydantic de request/response (no reusar
      modelos de dominio directamente como response; ver R8).

    **Justificacion:** `src/interface/` es la capa NiceGUI (pages, presenters,
    design). La API REST es un puerto de entrada independiente; colocarlo como
    hermano facilita el split a `avedra-backend` (copiar `src/api/` tal cual).

R5: EL SISTEMA NO DEBE importar modulos de `src/interface/` desde `src/api/`.
    La API y la UI NiceGUI son puertos de entrada paralelos sin dependencia
    mutua.

---

## Endpoint de salud

R6: EL SISTEMA DEBE exponer `GET /api/v1/health` con:
    - 200 `{"status": "ok", "version": "<APP_VERSION>"}` si la BD responde.
    - 503 `{"status": "error", "version": "<APP_VERSION>"}` si no.

R7: El endpoint `/health` existente en `main.py:87` se conserva. El nuevo
    `/api/v1/health` es independiente y sirve al frontend Vue.

---

## Esquemas de respuesta

R8: CADA endpoint DEBE definir un schema Pydantic de response en
    `src/api/schemas/`. No retornar model_dump() de modelos
    de dominio directamente: la API no debe exponer campos internos
    (password_hash, tokens de sesion, etc.).

R9: TODOS los schemas de response DEBEN incluir `model_config =
    ConfigDict(from_attributes=True)` para hidratacion desde objetos.

---

## Manejo de errores

R10: LA API DEBE devolver errores como JSON con estructura uniforme:
     `{"detail": "<mensaje>", "code": "<codigo_estable>"}`.
     Los codigos estables son los de `AvedraError` (datos_01).

R11: EL SISTEMA DEBE registrar un exception handler para `AvedraError`
     que mapee:
     - `NoEncontradoError` -> 404
     - `ReglaDeNegocioError` -> 422
     - `ConflictoError` -> 409
     - `PermisoDenegadoError` -> 403

---

## CORS

R12: EL SISTEMA DEBE configurar CORS con origenes restringidos:
     - En desarrollo: `["http://localhost:5173"]` (Vite dev server).
     - En produccion: configurable via `CORS_ORIGINS` en config.py.
     NiceGUI ya sirve su propio frontend; CORS es para el futuro Vue.

---

## Fuera de alcance

- Endpoints de negocio (backend_12).
- Autenticacion JWT (backend_11).
- Deploy (backend_13).
