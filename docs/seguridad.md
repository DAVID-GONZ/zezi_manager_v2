# Seguridad — despliegue y decisiones

> Registro de decisiones de seguridad del épico `seguridad_01..04` y guía de
> despliegue de ZECI Manager v2.0. Complementa `docs/decisions.md`.

## Despliegue con TLS (M2)

NiceGUI (`ui.run`) **no** termina TLS por sí mismo: no expone `ssl_certfile` /
`ssl_keyfile` en el patrón de despliegue de esta app. El patrón correcto es
servir la aplicación **detrás de un reverse proxy** (nginx, Caddy, Traefik) que
termine HTTPS y reenvíe el tráfico ya descifrado a la app local.

Reglas de despliegue en producción:

- **`HOST=127.0.0.1`** — la app escucha solo en loopback, de modo que únicamente
  el reverse proxy de la misma máquina pueda alcanzarla. **Nunca** exponer
  `HOST=0.0.0.0` sin HTTPS por delante: la cookie de sesión de NiceGUI viaja en
  claro y sería interceptable.
- El **reverse proxy** (nginx/Caddy) escucha en `443`, termina TLS con un
  certificado válido (p. ej. Let's Encrypt) y hace `proxy_pass` hacia
  `http://127.0.0.1:8080` (el `PORT` de la app).
- En el arranque, `main()` emite un `logging.warning` cuando `APP_ENV=production`
  recordando este requisito (ver `main.py`).
- Genera cada secreto (`JWT_SECRET`, `STORAGE_SECRET`) con valores aleatorios y
  **distintos** entre sí:

  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

  En producción el arranque se **bloquea** si conservan su valor por defecto
  (ver `config.py`). Detalles en `.env.example`.

Ejemplo mínimo de bloque nginx:

```nginx
server {
    listen 443 ssl;
    server_name zeci.example.org;

    ssl_certificate     /etc/letsencrypt/live/zeci.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/zeci.example.org/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade    $http_upgrade;   # WebSocket de NiceGUI
        proxy_set_header Connection "upgrade";
        proxy_set_header Host       $host;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Checklist de deploy TLS (seguridad_web_01)

Estos pasos son **operacionales** (manuales, se ejecutan en el servidor).
Los marcados con ✅ son obligatorios antes de habilitar la landing pública en producción.

### Emisión del certificado

Con **Certbot + nginx**:
```bash
certbot --nginx -d YOUR_DOMAIN --non-interactive --agree-tos -m admin@YOUR_DOMAIN
```

Con **Caddy** (automático al arrancar):
```bash
caddy start --config deploy/caddy/Caddyfile
# Caddy emite y renueva el cert por sí solo vía Let's Encrypt.
```

### Verificación post-deploy

```bash
# R3: HTTP debe redirigir a HTTPS
curl -I http://YOUR_DOMAIN
# Esperado: HTTP/1.1 301 Moved Permanently + Location: https://...

# R1: HTTPS debe responder 200
curl -I https://YOUR_DOMAIN
# Esperado: HTTP/1.1 200 OK

# R6: Dry-run de renovación automática (certbot)
certbot renew --dry-run
# Esperado: "Congratulations, all simulated renewals succeeded"

# R7: Grado A en testssl.sh
testssl.sh YOUR_DOMAIN
# Verificar: TLS 1.2+, sin ciphers débiles, sin TLS 1.0/1.1.
```

### Verificación de WebSocket (R4)

Abrir la app en el navegador. La barra de dirección debe mostrar `https://`.
En la consola del navegador, `ws://` es un error — debe ver `wss://`.

### Verificación de cookie Secure (R1 + follow-on S03)

```bash
curl -c /dev/null -s -I https://YOUR_DOMAIN/login | grep -i set-cookie
# La cookie de sesión debe incluir el flag `Secure`.
```

> **Gate de deploy:** `portal_36_landing_marketing` no debe ir a producción sin
> este checklist completo + `seguridad_web_02_secretos_config` done.

---

## Mecanismos de seguridad en código (dónde vive cada control)

Mapa rápido de los controles activos y su ubicación. El detalle arquitectónico
está en `docs/architecture.md` §7.

| Control | Ubicación | Nota |
|---|---|---|
| Hash de contraseñas | `src/infrastructure/auth/bcrypt_auth_service.py` | `bcrypt` directo, `ROUNDS=12`; compat legacy `sha256:`. |
| Política de contraseñas (A1) | `src/domain/policies/password_policy.py` | ≥8, letra+dígito, ≠ username. Enforcement en `usuario_service`; textos legibles en la UI. |
| Throttle / lockout de login (A1) | `src/services/login_throttle.py` | 5 fallos → bloqueo 300 s por username (estado de proceso). |
| Cambio forzado de contraseña (A2) | `route_guard.py` + `SessionContext.debe_cambiar_password` | Deny-by-default: fuerza `/cambiar-password` hasta cambiarla. |
| Autorización por ruta (deny by default) | `src/interface/auth/route_guard.py` (`registrar_pagina`) | `roles` obligatorio; registro único ruta→roles; el NAV deriva de él. |
| Matriz RBAC de gestión de usuarios | `src/domain/policies/rbac_usuarios.py` | Fuente de verdad; consultada por servicio (enforcement) y vista (gating). |
| Secretos independientes (M1/M3) | `config.py` | `JWT_SECRET` ≠ `STORAGE_SECRET`; bloqueo de arranque en producción con defaults. |
| Integridad de auditoría (M4) | `src/domain/policies/audit_chain.py` + `SqliteAuditoriaRepository` | Cadena SHA-256 append-only. |
| No enumeración de usuarios | `bcrypt_auth_service.autenticar_usuario` | Errores genéricos; estado de cuenta solo tras verificar la clave. |
| Scope multi-tenant | `src/services/contexto_tenant.py` | admin→sin scope / resto→su institución; `verificar_pertenencia` en ops por id. |
| Modo solo lectura ("Ver como") | `src/services/solo_lectura.py` | `@requiere_escritura` en mutadores; impersonación en `SessionContext`. |
| Sync central del contexto (B1) | `route_guard._pagina_protegida` → `SessionContext.desde_storage()` | Sincroniza los `ContextVar` antes de renderizar. |

> **No enumeración por login (paso_37):** el username es único global, así que el
> login no expone selector de institución ni desambiguación. `autenticar_usuario`
> devuelve mensajes genéricos para no revelar si un usuario existe.

## Decisiones aceptadas / diferidas

### B3 — `check_same_thread=False` (aceptado)

`src/infrastructure/db/connection.py` abre las conexiones SQLite con
`check_same_thread=False`. Es un **requisito de NiceGUI**: el servidor accede a
la conexión desde el pool de hilos de la capa async, por lo que SQLite debe
permitir uso multihilo. **No es una vulnerabilidad**: el acceso sigue
serializado por la lógica de la app y por SQLite. Se acepta como decisión de
arquitectura; sin cambio de código.

### B4 — Revocación de JWT (diferido a la API v3)

`src/.../jwt_handler.py` está preparado para una futura **API REST (v3)** que aún
no existe. La app de escritorio actual **no consume JWT** para autorizar
peticiones (la sesión vive en la cookie firmada de NiceGUI), de modo que hoy no
hay superficie de ataque por tokens no revocables. La lista de revocación /
rotación de JWT se **difiere a v3**, cuando la API exponga endpoints
autenticados por token. Sin cambio de código en v2.

## Gestión de secretos en producción (seguridad_web_02)

### Generación

Cada secreto debe ser una cadena aleatoria de ≥48 caracteres, generada de forma independiente:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Ejecutar el comando **dos veces** para obtener `JWT_SECRET` y `STORAGE_SECRET` distintos.
Nunca reutilizar la misma cadena para ambos.

### Dónde colocarlos en producción (R2)

En producción los secretos **no deben estar en `.env` en disco**. Las opciones:

1. **Variables de entorno del SO** (recomendado para VPS simple):
   ```bash
   export JWT_SECRET="<valor-generado>"
   export STORAGE_SECRET="<valor-generado>"
   ```
   Añadir al `~/.profile` del usuario de servicio, o al `Environment=` de la unit systemd.

2. **Gestor de secretos** (Vault, AWS Secrets Manager, etc.): inyectar como variables de
   entorno al arrancar el proceso.

### Rotación sin downtime (R7)

1. Generar nuevos valores (`secrets.token_urlsafe(48)`).
2. Actualizar las variables de entorno en el sistema (o el gestor de secretos).
3. Reiniciar el proceso: `systemctl restart zeci` (o equivalente).
   El reinicio de NiceGUI es rápido (<5 s); las sesiones activas invalidan sus cookies,
   los usuarios deben hacer login de nuevo.
4. Verificar que la app arranca (`journalctl -u zeci -n 50`).

### Usuario no-root y permisos (R6)

```bash
# Crear usuario de servicio sin shell
useradd --system --no-create-home zeci

# Permisos 600 en archivos de configuración
chmod 600 /etc/zeci/.env
chown zeci:zeci /etc/zeci/.env
```

La app se ejecuta como `zeci`; el reverse proxy (nginx/Caddy) como su propio usuario.
Nunca ejecutar la app como `root`.

### Auditoría de historial git

Ejecutado el **2026-08-17** con:
```bash
git log --all -S "token_urlsafe" -- "*.env*"
git log --all -S "cambia-esta-clave" -- "*.env*"
```
Único hit: commit `96e476b` (`2026-06-25`) que agregó `.env.example` con
**valores placeholder** (`cambia-esta-clave-en-produccion-ahora`), no secretos reales.
**Historial limpio de secretos reales.**

---

## Estado del épico de seguridad

| ID | Hallazgo | Severidad | Tratamiento | Estado |
|----|----------|-----------|-------------|--------|
| A1 | Hash de contraseñas / política de credenciales | Alto | Código (seguridad_01) | Cerrado |
| A2 | Cambio forzado de contraseña (deny-by-default) | Alto | Código (seguridad_01) | Cerrado |
| M1 | Secretos JWT y de sesión independientes | Medio | Código (seguridad_02) | Cerrado |
| M3 | Configuración / carga de secretos endurecida | Medio | Código (seguridad_02) | Cerrado |
| M4 | Integridad de auditoría (cadena hash) | Medio | Código (seguridad_03) | Cerrado |
| B2 | Hallazgo bajo cerrado en código | Bajo | Código (seguridad_01–03) | Cerrado |
| B1 | Fragilidad del ContextVar (sync de contexto) | Bajo | Código (seguridad_04) — sync central en el guard | Cerrado |
| M2 | Sin TLS a nivel de app | Medio | Despliegue — reverse proxy + doc + warning de arranque | Documentado |
| B3 | `check_same_thread=False` | Bajo | Aceptado — requisito de NiceGUI | Documentado |
| B4 | Revocación de JWT | Bajo | Diferido a la API v3 | Documentado |

## Gate de deploy — landing pública (portal_36)

La landing marketing (`/`) es una página **pública** visible para cualquier visitante.
**No publicar a producción** sin que estos pasos estén completados:

- `seguridad_web_01_tls_proxy` — proxy HTTPS (nginx/Caddy/Traefik) terminando TLS.
  Sin esto, la cookie de sesión de NiceGUI viaja en claro.
- `seguridad_web_02_secretos_config` — secretos (JWT_SECRET, STORAGE_SECRET)
  fuera del código fuente y del repositorio.

En desarrollo local esta restricción no aplica (`APP_ENV != production`).

---

### B1 — Sync central del contexto (cerrado en seguridad_04)

El modo solo-lectura ("Ver como") y el scope multi-tenant dependen de que el
contexto de sesión sincronice sus `ContextVar` de servicios
(`solo_lectura` + `institucion`) en cada render. Antes, ese sync dependía de que
**cada página** llamara `SessionContext.desde_storage()`. Ahora el guard central
(`src/interface/auth/route_guard.py`, `_pagina_protegida`) invoca
`SessionContext.desde_storage()` **antes** de renderizar cualquier página
protegida, de modo que toda petición sincroniza el contexto independientemente de
lo que recuerde la página (defensa en profundidad). Un test guardarraíl
(`tests/unit/interface/auth/test_route_guard.py::test_guard_sincroniza_contexto_central`)
verifica vía AST que el guard mantiene esta llamada e impide la regresión.
