# Tareas: backend_13_deploy_cloud

> SCOPE — archivos que pueden editarse:
> `Dockerfile` (crear), `render.yaml` (crear), `docs/deploy.md` (crear),
> `main.py` (ajustes menores de PORT si necesario), `.env.example`.
>
> Fuera de scope: servicios, repositorios, schema, interfaz.
>
> DEPENDE de backend_10, backend_11, backend_12 (API funcional).

---

## T1 — Dockerfile

Crear `Dockerfile` segun D1. Verificar build local:

```
docker build -t avedra .
docker run -e APP_ENV=development -p 8080:8080 avedra
```

Si Docker no esta disponible, verificar que el Dockerfile es
sintacticamente correcto con `hadolint` online.

---

## T2 — render.yaml

Crear `render.yaml` segun D2. Verificar estructura YAML valida.

---

## T3 — Crear base de datos en Neon

1. Registrar cuenta en neon.tech (free tier, sin tarjeta).
2. Crear proyecto "avedra-demo".
3. Copiar connection string.
4. Verificar conexion local:
   ```
   DB_BACKEND=postgres DATABASE_URL="postgresql+psycopg://..." python -c "
   from container import Container
   e = Container.engine()
   with e.connect() as c:
       print(c.execute(__import__('sqlalchemy').text('SELECT 1')).scalar())
   "
   ```

---

## T4 — Verificar schema en Postgres real

Ejecutar `metadata.create_all()` contra la base Neon:

```
DB_BACKEND=postgres DATABASE_URL="..." python -c "
from src.infrastructure.db.schema import metadata
from container import Container
metadata.create_all(Container.engine())
print('Schema creado OK')
"
```

Verificar que las 65 tablas se crean sin error.

---

## T5 — Verificar seed_base en Postgres

```
DB_BACKEND=postgres DATABASE_URL="..." APP_ENV=production python main.py
```

Debe arrancar, crear schema, ejecutar seed_base y servir.

---

## T6 — Documentacion docs/deploy.md

Escribir la guia de deploy segun D5. Incluir:
- Pasos con capturas textuales.
- Variables de entorno obligatorias.
- Como generar secretos seguros (`python -c "import secrets; print(secrets.token_urlsafe(32))"`).
- Verificacion post-deploy.

---

## T7 — Deploy en Render (si acceso disponible)

Si el repo esta en GitHub y se tiene cuenta Render:
1. Conectar repo.
2. Configurar env vars.
3. Deploy.
4. Verificar `/api/v1/health` desde internet.

Si no hay acceso, documentar los pasos y marcar como verificable
cuando David decida desplegar.

---

## T8 — Actualizar .env.example

Documentar las variables necesarias para deploy en la nube.

---

## T9 — Verificacion de no regresion y cierre

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE localmente. La app sigue funcionando en SQLite.

**Artefacto:** `progress/impl_backend_13.md`.
