# Diseno: backend_13_deploy_cloud

## Punto de partida medido

| Componente | Estado |
|---|---|
| `DB_BACKEND=postgres` | Soportado en config.py y engine factory (backend_05) |
| Schema Postgres | `metadata.create_all()` con tipos neutros (backend_04) |
| Repos SQLAlchemy Core | 20 repos migrados, queries portables (backend_07) |
| Suite Postgres | Conftest parametrizado con `--backend=postgres` (backend_09) |
| Dockerfile | No existe |
| Deploy config | No existe |

## D1 — Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render inyecta PORT como variable de entorno
ENV PORT=8080
ENV APP_ENV=production
ENV HOST=127.0.0.1

EXPOSE ${PORT}

CMD ["python", "main.py"]
```

Nota: `HOST=127.0.0.1` porque Render pone su propio proxy delante.
Render inyecta `PORT` y rutea el trafico HTTPS al contenedor.

## D2 — render.yaml

```yaml
services:
  - type: web
    name: avedra
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: APP_ENV
        value: production
      - key: DB_BACKEND
        value: postgres
      - key: DATABASE_URL
        sync: false  # se configura en el dashboard
      - key: JWT_SECRET
        generateValue: true
      - key: STORAGE_SECRET
        generateValue: true
      - key: PORT
        value: "8080"
      - key: HOST
        value: "127.0.0.1"
```

## D3 — Ajuste de main.py para PORT dinamico

`main.py` ya lee `settings.PORT` que viene de `config.py`. Render
inyecta `PORT` como env var y `Settings` lo recoge automaticamente.

Si NiceGUI no respeta el PORT de settings y usa uno hardcodeado,
ajustar `ui.run(port=settings.PORT)` — ya lo hace (main.py:401).

## D4 — Neon Postgres

1. Crear proyecto en neon.tech (free tier, no requiere tarjeta).
2. Copiar la connection string:
   `postgresql+psycopg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`
3. Pegarla como `DATABASE_URL` en Render.

Nota: Neon usa pooling PgBouncer por defecto. El `pool_pre_ping=True`
del engine factory (backend_05) maneja reconexiones automaticamente.

## D5 — Documentacion (docs/deploy.md)

Estructura del documento:
1. Requisitos previos (cuenta Render, cuenta Neon)
2. Crear base de datos en Neon (3 pasos con capturas)
3. Crear servicio en Render (fork del repo o deploy manual)
4. Configurar variables de entorno
5. Primer arranque y verificacion
6. Limitaciones del tier gratuito
7. Alternativa: Fly.io + Supabase
8. Migracion a VPS/pago cuando sea necesario

## Alternativas evaluadas

| Servicio | Tier gratuito | Limitacion principal | Veredicto |
|---|---|---|---|
| **Render** | 750 h/mes | Spin-down 15 min | Recomendado (simplicidad) |
| **Fly.io** | 3 VMs shared | Config mas compleja (flyctl) | Alternativa |
| **Railway** | $5 credito, luego paga | No es free tier permanente | Descartado |
| **PythonAnywhere** | Free | No soporta WebSocket (NiceGUI) | Descartado |
| **Neon** | 0.5 GB always-free | Suficiente para demo | Recomendado |
| **Supabase** | 500 MB, 2 proyectos | Pausa tras 1 semana | Alternativa |
| **ElephantSQL** | Discontinuado 2025 | N/A | Descartado |
