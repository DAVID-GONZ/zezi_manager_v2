# Requisitos: backend_13_deploy_cloud

> Ambito: desplegar la app NiceGUI + API REST en la nube con Postgres,
> usando servicios de tier gratuito o prueba. El objetivo no es produccion
> con SLA sino un entorno de demo/validacion accesible desde internet.
>
> RESTRICCION DE COSTO: no hay presupuesto para servicios pagos en esta
> etapa. El deploy DEBE funcionar en tiers gratuitos. Cuando el tier
> gratuito expire o sea insuficiente, el deploy se migra a un VPS.
>
> DEPENDE de backend_10, backend_11, backend_12 (API funcional).

---

## Infraestructura gratuita

R1: EL SISTEMA DEBE desplegarse usando servicios con tier gratuito:
    - **App (Python/NiceGUI):** Render free tier (750 horas/mes, spin-down
      tras 15 min inactividad) o Fly.io free tier (3 VMs compartidas).
    - **Postgres:** Neon free tier (0.5 GB storage, always-free, serverless)
      o Supabase free tier (500 MB, 2 proyectos).

R2: EL SISTEMA DEBE arrancar con `DB_BACKEND=postgres` y `DATABASE_URL`
    apuntando al servicio de Postgres elegido. La conmutacion ya existe
    (backend_05).

R3: EL SISTEMA DEBE funcionar con el spin-down de Render (cold start
    de ~30 segundos tras inactividad). No se requiere keep-alive.

---

## Configuracion de deploy

R4: EL SISTEMA DEBE incluir un `Dockerfile` minimo que:
    - Use Python 3.11+ slim.
    - Instale solo `requirements.txt`.
    - Exponga el puerto via variable de entorno `PORT`.
    - Ejecute `python main.py`.

R5: EL SISTEMA DEBE incluir un `render.yaml` (o equivalente) con:
    - Servicio web Python.
    - Variables de entorno: `APP_ENV=production`, `DB_BACKEND=postgres`,
      `DATABASE_URL`, `JWT_SECRET`, `STORAGE_SECRET`, `PORT`.
    - Build command: `pip install -r requirements.txt`.
    - Start command: `python main.py`.

R6: EL SISTEMA DEBE incluir documentacion en `docs/deploy.md` con:
    - Instrucciones paso a paso para Render + Neon.
    - Como obtener el `DATABASE_URL` de Neon.
    - Como generar `JWT_SECRET` y `STORAGE_SECRET` seguros.
    - Limitaciones del tier gratuito.
    - Alternativas: Fly.io + Supabase como backup.

---

## Seed de produccion

R7: AL primer arranque contra Postgres, el sistema DEBE ejecutar
    `seed_base()` (no `seed_dev()`), que crea la estructura minima
    sin datos de ejemplo.

R8: EL SISTEMA DEBE verificar que `metadata.create_all()` funciona
    contra Postgres real (no solo SQLite). Los tipos neutros de
    backend_04 lo garantizan; este paso lo verifica en vivo.

---

## HTTPS

R9: HTTPS DEBE estar incluido en el servicio de deploy (Render y
    Fly.io incluyen TLS automatico). No se requiere configuracion
    manual de Let's Encrypt.

R10: EL validador `verificar_binding_produccion` de `config.py`
     DEBE seguir exigiendo `HOST=127.0.0.1` en produccion. El
     servicio de deploy pone un reverse proxy delante.

---

## Limitaciones conocidas del tier gratuito

- **Render free:** spin-down tras 15 min inactividad, 750 h/mes,
  sin disco persistente (no afecta: la BD es Postgres externo).
- **Neon free:** 0.5 GB storage, autoscale a 0 tras 5 min inactividad
  (cold start de ~1 segundo al reconectar), 100 horas de compute/mes.
- **Fly.io free:** 3 VMs compartidas, 160 GB de transferencia.
- **Supabase free:** 500 MB, pausado tras 1 semana de inactividad.

---

## Fuera de alcance

- Dominio personalizado (requiere pago).
- Backups automatizados (el tier gratuito no los incluye; los datos
  son de demo, no de produccion).
- CI/CD automatizado (se hara en split_05).
- Monitoreo/observabilidad en la nube (la app ya tiene panel interno).
