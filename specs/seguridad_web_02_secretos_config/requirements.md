# Requisitos: Secretos y configuración de producción (seguridad_web_02)

> **Nivel:** N0 — Bloqueante de deploy
> **Dificultad:** Config (mínimo código Python; ya existe bloqueo en `config.py`)
> **Depende de:** ningún otro spec
> **Bloquea a:** S05 (throttle necesita `DATABASE_URL` de Postgres)

## Contexto del problema

`config.py` ya bloquea el arranque si `JWT_SECRET` o `STORAGE_SECRET` conservan su
valor por defecto en `APP_ENV=production`. Con la migración a Postgres aparecen nuevos
secretos (`DATABASE_URL`, credenciales de BD) que deben tratarse con el mismo rigor.
El riesgo principal es que un secreto llegue al repositorio (en código, en un `.env`
commiteado, en logs del CI) o que dos entornos compartan el mismo secreto.

## Requisitos

R1: CADA ENTORNO (dev, staging, prod) DEBE tener secretos distintos e independientes
    para `JWT_SECRET`, `STORAGE_SECRET` y `DATABASE_URL`. Nunca copiar secretos de
    un entorno a otro.

R2: LOS SECRETOS DE PRODUCCIÓN DEBEN provenir de variables de entorno del sistema
    operativo o de un gestor de secretos (AWS Secrets Manager, Vault, etc.), nunca
    de un archivo `.env` en disco en el servidor de producción.

R3: EL ARCHIVO `.env` DEBE existir solo en desarrollo local. `.gitignore` DEBE
    incluir `.env`, `.env.*` y cualquier variante. El historial de git DEBE estar
    limpio de secretos (verificar con `git log -S <patron_secreto>`).

R4: `config.py` DEBE extender su bloqueo de arranque para incluir `DATABASE_URL`
    vacía o con valor de ejemplo en `APP_ENV=production`.

R5: EL PROCESO DE LA APP DEBE correr con un usuario del sistema operativo sin
    privilegios (no root). Los archivos de configuración con secretos deben ser
    legibles únicamente por ese usuario (permisos 600 o equivalente).

R6: LOS LOGS DE LA APP Y DEL CI NUNCA DEBEN contener el valor de un secreto.
    `config.py` DEBE implementar `__repr__` / `model_post_init` que enmascaren
    los campos sensibles al serializar la configuración.

R7: CADA SECRETO DEBE generarse con entropía suficiente. El mínimo aceptable es
    `secrets.token_urlsafe(48)` (ya documentado en `docs/seguridad.md`). El proceso
    de generación DEBE estar documentado en `.env.example`.

R8: LA ROTACIÓN de secretos DEBE ser posible sin downtime: la app DEBE poder
    recibir el nuevo secreto vía recarga de configuración o reinicio rápido, sin
    necesidad de redesplegar el código.

## Criterio de done

- `git log --all -S "JWT_SECRET\|STORAGE_SECRET\|DATABASE_URL" -- "*.env*"` no
  devuelve ningún commit con valores reales.
- `APP_ENV=production python main.py` sin las variables requeridas falla con mensaje
  claro antes de arrancar.
- `config.py` enmascara secretos en repr/logging (test unitario).
- `.env.example` tiene instrucciones de generación y está commiteado sin valores reales.
