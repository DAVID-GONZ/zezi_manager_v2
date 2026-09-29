# Deploy de AVEDRA en la nube (Render + Neon — tier gratuito)

Esta guia cubre el despliegue de AVEDRA sobre los servicios gratuitos de
Render (app) y Neon (Postgres). No requiere tarjeta de credito mientras no
se superen los limites del tier gratuito.

---

## Requisitos previos

- Cuenta en [render.com](https://render.com) (gratuita).
- Cuenta en [neon.tech](https://neon.tech) (gratuita).
- Repositorio de AVEDRA accesible desde Render (GitHub o GitLab).
- Python 3.11+ instalado localmente para generar secretos.

---

## Paso 1 — Crear la base de datos en Neon (free tier)

1. Inicia sesion en <https://console.neon.tech>.
2. Crea un nuevo proyecto (boton **New Project**).
3. Elige la region mas cercana a tus usuarios (p. ej. `us-east-2`).
4. Neon creara automaticamente una rama `main` con una base llamada `neondb`.
5. En **Connection Details**, selecciona el driver **psycopg** y copia la
   cadena de conexion. Tendra este formato:

   ```
   postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

6. **Importante:** AVEDRA usa `psycopg` (v3), no `psycopg2`. Cambia el
   prefijo de la URL antes de usarla:

   ```
   postgresql+psycopg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

   Si Neon ya entrega el prefijo `postgresql+psycopg://`, no hay que cambiar
   nada.

---

## Paso 2 — Preparar el repositorio

Asegurate de que los siguientes archivos esten en la raiz del repositorio y
subidos a la rama que Render va a desplegar:

- `Dockerfile` — imagen minima `python:3.11-slim`.
- `render.yaml` — definicion declarativa del servicio.
- `requirements.txt` — dependencias de Python.

No subas el archivo `.env` real. El `.env.example` sirve de referencia; las
variables sensibles se configuran directamente en el panel de Render (Paso 4).

---

## Paso 3 — Crear el servicio web en Render

1. En el dashboard de Render haz clic en **New > Web Service**.
2. Conecta tu cuenta de GitHub/GitLab y selecciona el repositorio de AVEDRA.
3. Render detectara el `render.yaml` y precargara la configuracion.
   Si no lo detecta, configura manualmente:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Deja el plan en **Free** (0 USD/mes).
5. Haz clic en **Create Web Service**.

---

## Paso 4 — Configurar las variables de entorno

En la pestana **Environment** del servicio en Render, define las siguientes
variables. Las marcadas con `(secreto)` deben generarse de forma segura
(ver instrucciones al final de este documento).

| Variable        | Valor                                          | Notas                          |
|-----------------|------------------------------------------------|--------------------------------|
| `APP_ENV`       | `production`                                   | Activa validaciones de secreto |
| `DB_BACKEND`    | `postgres`                                     | Selecciona el engine Postgres  |
| `DATABASE_URL`  | `postgresql+psycopg://...` (copiada en Paso 1) | (secreto)                      |
| `JWT_SECRET`    | cadena aleatoria ≥ 48 chars                    | (secreto)                      |
| `STORAGE_SECRET`| cadena aleatoria ≥ 48 chars, distinta a JWT    | (secreto)                      |
| `PORT`          | `8080`                                         |                                |
| `HOST`          | `127.0.0.1`                                    | Render gestiona el proxy TLS   |
| `LOG_LEVEL`     | `INFO`                                         | Opcional                       |

> **Render** puede generar `JWT_SECRET` y `STORAGE_SECRET` automaticamente
> si usas el campo `generateValue: true` del `render.yaml`. En ese caso no
> es necesario copiarlos manualmente.

---

## Paso 5 — Primer arranque y verificacion

Una vez guardadas las variables, Render lanzara el primer deploy automaticamente.

1. Espera a que el estado del servicio cambie a **Live** (suele tardar 2-5 min).
2. Verifica que la app responde correctamente en el endpoint de salud:

   ```
   GET https://<tu-app>.onrender.com/api/v1/health
   ```

   Respuesta esperada (HTTP 200):

   ```json
   {"status": "ok", "db": "ok"}
   ```

   Si el DB no esta disponible, el endpoint devuelve HTTP 503 con `"db": "error"`.

3. La primera vez que arranca, `metadata.create_all()` crea las 65 tablas en
   la base Neon. Puedes verificarlo en la consola de Neon bajo **Tables**.

---

## Limitaciones del tier gratuito

### Render (Free Web Service)

| Limite          | Valor                                        |
|-----------------|----------------------------------------------|
| Horas/mes       | 750 h (equivale a 1 servicio siempre activo) |
| Spin-down       | 15 min sin trafico → la primera peticion tarda ~30 s |
| RAM             | 512 MB                                       |
| CPU             | Compartida                                   |
| Dominio         | `*.onrender.com` (HTTPS incluido)            |
| Disco           | Efimero (no persistente entre deploys)       |

> Los archivos generados en disco (exports PDF/Excel, logs) se pierden al
> reiniciar o redesplegar. Si necesitas persistencia, usa un bucket S3/R2 o
> un volumen de pago.

### Neon (Free Tier)

| Limite          | Valor                                        |
|-----------------|----------------------------------------------|
| Almacenamiento  | 0.5 GB                                       |
| Compute         | 0.25 vCPU, 1 GB RAM                          |
| Ramas           | 10                                           |
| Proyectos       | 1                                            |
| Escalado a cero | Si (se suspende tras inactividad)            |

El escalado a cero de Neon puede anadir ~500 ms de latencia en la primera
consulta tras un periodo sin actividad. Esto se combina con el spin-down de
Render, de modo que la primera peticion tras 15 min puede tardar hasta ~30 s.

---

## Alternativa: Fly.io + Supabase

Si los limites de Render/Neon resultan insuficientes, la alternativa mas
sencilla dentro del tier gratuito es:

- **[Fly.io](https://fly.io)** — 3 VM `shared-cpu-1x` (256 MB RAM) gratuitas,
  sin spin-down si se mantiene 1 maquina activa. Se despliega con `flyctl`.
- **[Supabase](https://supabase.com)** — Postgres gestionado, 500 MB
  almacenamiento, pausa automatica tras 7 dias de inactividad (reactivable
  manualmente).

El `Dockerfile` de AVEDRA es compatible con Fly.io sin modificaciones.
Para Supabase, la URL de conexion tambien usa el prefijo `postgresql+psycopg://`.

---

## Generar secretos seguros

Genera cada secreto por separado. Los dos deben ser distintos entre si:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Ejecuta el comando dos veces para obtener `JWT_SECRET` y `STORAGE_SECRET`.
Una cadena `token_urlsafe(48)` tiene 384 bits de entropia, muy por encima
del minimo de 256 bits recomendado para HS256.
