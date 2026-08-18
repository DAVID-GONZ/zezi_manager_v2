# seguridad_web_01_tls_proxy — Spec

## Contexto

Publicar la landing publica en `/` (paso `portal_36`) convierte a ZECI Manager en una
app expuesta a internet: hasta hoy era una herramienta de acceso interno. En cuanto `/`
es accesible sin sesion, la cookie de sesion (`app.storage.user`, firmada con
`STORAGE_SECRET` en `main.py:345`) y los WebSockets de NiceGUI viajan por la red. NiceGUI
**no termina TLS por si mismo** (`main.py:338` `ui.run(host=settings.HOST, ...)`), por lo
que sin un reverse proxy con HTTPS la cookie viaja en claro y es interceptable, y el canal
de tiempo real no puede usar `wss://`.

`HOST` ya tiene default `127.0.0.1` (`config.py:112`), pero no hay ninguna asercion que
impida arrancar en produccion escuchando en `0.0.0.0`. El control esta documentado en
`docs/seguridad.md` §"Despliegue con TLS" pero no formalizado como requisito verificable.

Este paso es el disparador N0 (bloqueante de deploy) que habilita salir a produccion con
la landing publica. Es infraestructura: no toca `src/` salvo una asercion de binding.

Scope: `deploy/nginx/zeci.conf` (nuevo), `deploy/caddy/Caddyfile` (nuevo),
`src/config.py` (asercion de binding en produccion),
`tests/unit/test_config_prod.py` (nuevo), `docs/seguridad.md` (extender).

## Requisitos (EARS)

- **R1** — EL SISTEMA DEBE terminar TLS en un reverse proxy (nginx o Caddy) con
  certificado valido escuchando en 443. La app Python NUNCA expone TLS directamente.
- **R2** — EN PRODUCCION la app DEBE escuchar exclusivamente en `127.0.0.1`. Si
  `settings.is_production` y `HOST` no es loopback, el arranque DEBE abortar con mensaje
  claro (hoy solo hay default, no enforcement).
- **R3** — EL PROXY DEBE redirigir todo HTTP (80) a HTTPS (443) con 301.
- **R4** — EL PROXY DEBE pasar `Upgrade: websocket` y `Connection: upgrade` a la app para
  que los WebSockets de NiceGUI funcionen sobre `wss://`.
- **R5** — EL PROXY DEBE pasar `X-Forwarded-For` y `X-Forwarded-Proto` (necesario para el
  logging de S09 y para reconstruir el esquema real).
- **R6** — EL CERTIFICADO DEBE renovarse automaticamente; su caida DEBE generar alerta, no
  un deploy manual de emergencia.
- **R7** — LA CONFIGURACION DEBE deshabilitar TLS 1.0/1.1 y cifrados debiles; solo TLS 1.2
  y 1.3 son aceptables.
- **R8** — STAGING DEBE tener TLS activo antes que produccion, para verificar cookies y
  WebSockets sobre HTTPS real antes del primer deploy.

## Diseño

### T1 — Plantilla nginx (`deploy/nginx/zeci.conf`, nuevo)

Bloque `server` 443 con `proxy_pass http://127.0.0.1:<port>;`, cabeceras
`proxy_set_header Upgrade $http_upgrade; Connection "upgrade";
X-Forwarded-For $proxy_add_x_forwarded_for; X-Forwarded-Proto $scheme;`,
`ssl_protocols TLSv1.2 TLSv1.3;`, `ssl_ciphers` fuerte, y bloque `server` 80 con
`return 301 https://$host$request_uri;`. Comentado como plantilla (el dominio/puerto son
placeholders del deploy).

### T2 — Alternativa Caddy (`deploy/caddy/Caddyfile`, nuevo)

Caddy gestiona TLS automatico (Let's Encrypt). `reverse_proxy 127.0.0.1:<port>` (Caddy
pasa `Upgrade`/`X-Forwarded-*` por defecto). Documentar cual usar segun el entorno.

### T3 — Enforcement de binding (`src/config.py`)

Extender la validacion existente (`config.py:148-164`, misma funcion que ya bloquea
secretos por defecto): si `self.is_production` y `self.HOST not in {"127.0.0.1","localhost"}`
→ `raise ValueError("HOST debe ser loopback en produccion; el TLS lo termina el proxy")`.
No cambia el comportamiento en dev/test.

### T4 — Documentacion de deploy (`docs/seguridad.md`)

Checklist de deploy TLS: emision de cert, dry-run de renovacion (`certbot renew --dry-run`
o Caddy automatico), verificacion `curl -I`, `testssl.sh`. Los pasos de emision son
operacionales (manuales), marcados como tal.

## Tareas

- [ ] **T1** — Crear `deploy/nginx/zeci.conf` con proxy TLS, redirect 80→443 y passthrough
  de WebSocket + `X-Forwarded-*`.
  Verificacion: `nginx -t -c deploy/nginx/zeci.conf` (manual en servidor) + revision del diff.
- [ ] **T2** — Crear `deploy/caddy/Caddyfile` equivalente con TLS automatico.
  Verificacion: `caddy validate --config deploy/caddy/Caddyfile` (manual).
- [ ] **T3** — Asercion de binding loopback en produccion en `config.py`.
  Verificacion: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/test_config_prod.py -q`
- [ ] **T4** — Extender `docs/seguridad.md` con checklist de deploy TLS y verificacion.
  Verificacion: revision (documento).

## Verificacion final

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/unit/test_config_prod.py -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer interface
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Criterios observables (entorno de deploy, manuales): `curl -I http://<dominio>` → 301 a
https; `curl -I https://<dominio>` → 200 y cookie con `Secure`; `testssl.sh` grado A;
WebSocket sobre `wss://`; `certbot renew --dry-run` exitoso. En CI/local solo se verifica
la asercion de binding (T3) e `init.py` verde.

## Dependencias

Ninguna spec previa. Es **gate de deploy** de `portal_36_landing_marketing` (la landing no
debe publicarse a produccion sin este paso). Follow-on natural: `seguridad_web_03_cookies_sesion`
(flag `Secure`), fuera de alcance de esta ronda.
