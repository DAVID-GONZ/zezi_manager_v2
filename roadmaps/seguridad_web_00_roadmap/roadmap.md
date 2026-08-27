# seguridad_web_00 — Roadmap de seguridad: deploy web, PostgreSQL, PWA / WebView2

## Contexto (David, 2026-07-29)

ZECI Manager está evolucionando hacia despliegue en la nube con PostgreSQL (ORM SQLAlchemy),
API REST (FastAPI montado en NiceGUI) y distribución como PWA/app de escritorio vía WebView2.
Este roadmap cubre **todos** los controles de seguridad necesarios para ese escenario,
desde los bloqueantes de primer deploy hasta la higiene operacional continua.

No es un roadmap de migración: el código de seguridad existente (`seguridad_01..04`) se
mantiene como base. Este roadmap extiende, endurece y complementa lo ya hecho para el
nuevo contexto de producción multi-usuario en la nube.

---

## Lo que ya está resuelto (no se toca, solo se verifica)

| Control | Ubicación | Épico |
| --- | --- | --- |
| Hash bcrypt rounds=12 | `bcrypt_auth_service.py` | seguridad_01 |
| Política de contraseñas | `domain/policies/password_policy.py` | seguridad_01 |
| Cambio forzado de password | `route_guard.py` + `SessionContext` | seguridad_01 |
| Throttle de login (5 fallos / 300s) | `services/login_throttle.py` | seguridad_01 |
| No enumeración de usuarios | `bcrypt_auth_service.autenticar_usuario` | seguridad_01 |
| Secretos independientes JWT / Storage | `config.py` (bloqueo en prod) | seguridad_02 |
| Cadena de auditoría SHA-256 | `domain/policies/audit_chain.py` | seguridad_03 |
| Route guard deny-by-default | `interface/auth/route_guard.py` | seguridad_01 |
| Matriz RBAC | `domain/policies/rbac_usuarios.py` | seguridad_01 |
| Scope multi-tenant (SQLite) | `services/contexto_tenant.py` | seguridad_01 |
| Sync central de ContextVar | `route_guard._pagina_protegida` | seguridad_04 |
| Modo solo lectura ("Ver como") | `services/solo_lectura.py` | seguridad_02 |

---

## Criterio de niveles

| Nivel | Significado |
| --- | --- |
| **N0 — Bloqueante** | Sin esto la app NO puede ir a producción. |
| **N1 — Primer mes** | Sin esto la app es vulnerable poco después de estar live. |
| **N2 — Con API REST** | Aplica cuando se completen las Fases 3–4 del `backend_00` roadmap. |
| **N3 — Con PWA/WebView2** | Aplica cuando se complete la Fase 2 del `backend_00` roadmap. |
| **N4 — Continuo** | Higiene operacional permanente; no tiene fecha de "done". |

## Criterio de dificultad

| Dificultad | Significado |
| --- | --- |
| **Infra** | Solo configuración de servidor/proxy; cero código Python. |
| **Config** | Variables de entorno y arranque; mínimo código Python. |
| **Código-Bajo** | Cambios de código confinados a un módulo; riesgo de regresión bajo. |
| **Código-Alto** | Cambios arquitectónicos o que tocan múltiples capas. |
| **Proceso** | Procedimientos operacionales; sin código. |
| **Externo** | Requiere expertise o herramientas externas. |

---

## N0 — Bloqueante de primer deploy

Sin estos ítems el deploy **no debe ocurrir**.

| ID | Nombre | Dificultad | Spec |
| --- | --- | --- | --- |
| S01 | TLS + reverse proxy | Infra | `seguridad_web_01_tls_proxy` |
| S02 | Secretos y configuración de producción | Config | `seguridad_web_02_secretos_config` |
| S03 | Cookies de sesión seguras | Código-Bajo | `seguridad_web_03_cookies_sesion` |
| S04 | Headers HTTP de seguridad | Infra | `seguridad_web_04_headers_http` |
| S05 | Throttle de login persistente en Postgres | Código-Alto | `seguridad_web_05_throttle_postgres` |
| S06 | Auditoría de dependencias (pip audit) | Proceso | `seguridad_web_06_dependencias` |
| S07 | Verificación multi-tenant en Postgres + ORM | Código-Bajo | `seguridad_web_07_multitenant_postgres` |

### Notas N0

- **S05** es el ítem más crítico de código nuevo: hoy el throttle vive en memoria del
  proceso. En un deploy web con múltiples workers o reinicios, el estado se pierde y un
  atacante puede forzar bruta reiniciando entre intentos. Debe migrar a Postgres.
- **S07** verifica que el scope multi-tenant no dependa de ninguna quirk de SQLite
  al pasar a SQLAlchemy + Postgres. Es una verificación más que desarrollo nuevo.

---

## N1 — Primer mes en producción

Deben completarse dentro del primer mes de estar live.

| ID | Nombre | Dificultad | Spec |
| --- | --- | --- | --- |
| S08 | Content Security Policy ajustada a NiceGUI/Quasar | Código-Alto | `seguridad_web_08_csp_nicegui` |
| S09 | Logging de seguridad y alertas | Código-Bajo | `seguridad_web_09_logging_alertas` |
| S10 | Backups automatizados y plan de rollback | Infra | `seguridad_web_10_backup_rollback` |
| S11 | CI/CD seguro (secrets, gates, builds reproducibles) | Config | `seguridad_web_11_cicd_seguro` |

### Notas N1

- **S08** tiene dificultad Alta porque NiceGUI + Quasar inyectan scripts inline y
  conectan WebSocket. La CSP necesita iteración en staging antes de activarse en prod.
- **S09** complementa la cadena de auditoría existente con logging de eventos de
  seguridad y alertas operacionales (logins fallidos masivos, operaciones sensibles).
- **S11** asegura que el pipeline de CI nunca exponga secretos y que solo código con
  tests verdes pueda llegar a prod.

---

## N2 — Con la API REST (Fase 3 del backend_00 roadmap)

No aplican antes de que exista `backend_12_fastapi_mount` completado.

| ID | Nombre | Dificultad | Spec |
| --- | --- | --- | --- |
| S12 | CORS para API REST | Config | `seguridad_web_12_cors_api` |
| S13 | Autenticación de API (JWT / API keys) | Código-Alto | `seguridad_web_13_jwt_api` |
| S14 | Rate limiting de API | Código-Bajo | `seguridad_web_14_ratelimit_api` |

### Notas N2

- **S13** activa el `jwt_handler.py` que ya existe pero hoy no se usa (diferido en B4
  del épico anterior). Debe incluir revocación y rotación de refresh tokens.
- **S12** es rápido pero crítico: un CORS mal configurado expone la API completa
  a cualquier origen.
- **S14** es independiente del rate limiting de login (S05); protege endpoints de la
  API REST contra abuso (scraping, fuerza bruta en endpoints no autenticados).

---

## N3 — Con PWA / WebView2 (Fase 2 del backend_00 roadmap)

No aplican antes de que exista `backend_10_nicegui_native` completado.

| ID | Nombre | Dificultad | Spec |
| --- | --- | --- | --- |
| S15 | PWA service worker seguro | Código-Bajo | `seguridad_web_15_pwa_sw` |
| S16 | WebView2: origen restringido y APIs nativas | Código-Bajo | `seguridad_web_16_webview2` |
| S17 | Actualización segura del .exe | Código-Alto | `seguridad_web_17_exe_actualizacion` |

### Notas N3

- **S15** impide que el service worker cachee tokens o datos sensibles, que quedarían
  expuestos si otra app del mismo origen accede al cache.
- **S17** es lo más complejo de esta fase: el binario debe verificar la firma del
  paquete de actualización antes de instalarlo para prevenir supply chain attacks.

---

## N4 — Continuo / Operacional

No tienen fecha de "done"; son prácticas que se mantienen indefinidamente.

| ID | Nombre | Dificultad | Spec |
| --- | --- | --- | --- |
| S18 | Rotación periódica de secretos | Proceso | `seguridad_web_18_rotacion_secretos` |
| S19 | Pen testing y auditoría externa | Externo | `seguridad_web_19_pentest_auditoria` |

---

## Dependencias entre specs y el backend_00 roadmap

```
backend_00 Fase 1 (SQLAlchemy + Postgres)
    └── S05 (throttle persistente) — necesita Postgres disponible
    └── S07 (multi-tenant en Postgres) — verifica que ORM respeta scope

backend_00 Fase 3 (FastAPI montado)
    └── S12 CORS
    └── S13 JWT / API keys
    └── S14 rate limiting API

backend_00 Fase 2 (.exe / WebView2)
    └── S15 service worker
    └── S16 WebView2 origen
    └── S17 actualización segura
```

Los ítems N0 (S01–S07) son **independientes** del roadmap de backend: pueden
completarse en paralelo a las Fases 0 y 1 del backend.

---

## Orden recomendado de arranque

1. **S01 + S02 + S04** en paralelo (pura infra/config, cero riesgo de regresión).
2. **S06** (pip audit) antes de cualquier deploy; toma < 30 minutos.
3. **S03 + S07** una vez que el harness SQLAlchemy esté verde (Fase 1 backend).
4. **S05** al migrar a Postgres (depende de Fase 1 backend).
5. **S08 + S09 + S10 + S11** en las primeras semanas en producción.
6. **S12–S14** cuando la API REST esté lista.
7. **S15–S17** cuando el empaquetado de escritorio esté listo.
8. **S18 + S19** desde el primer día de producción, sin fin.

---

## Estimación de esfuerzo

| Fase | Esfuerzo neto | Observaciones |
| --- | --- | --- |
| N0 (S01–S07) | 2–4 días | S01/S02/S04/S06 son horas; S05 es el más costoso |
| N1 (S08–S11) | 3–6 días | S08 puede llevar más por iteración en CSP |
| N2 (S12–S14) | 2–4 días | Depende de alcance de la API |
| N3 (S15–S17) | 3–5 días | S17 es la parte más compleja |
| N4 (S18–S19) | Continuo | S19 puede requerir presupuesto externo |
| **Total** | **~10–19 días** | Distribuidos a lo largo del roadmap backend |