# seguridad_web_00 — Roadmap de seguridad: deploy web, PostgreSQL, PWA / Tauri / Capacitor

> **Revisión 2026-09-27:** la arquitectura evolucionó de monorepo con "FastAPI montado
> en NiceGUI" a **split en 3 repos** (`avedra-backend`, `avedra-frontend`,
> `avedra-shared-contracts`). NiceGUI pasa a legado. Los controles de seguridad se
> distribuyen entre repos: backend (API, auth, DB, throttle) y frontend (CSP, PWA,
> Tauri, CORS client-side). Ver `repo_split_00_pasos.md`.

## Contexto (David, 2026-07-29, revisado 2026-09-27)

AVEDRA está evolucionando hacia despliegue en la nube con PostgreSQL (SQLAlchemy Core),
API REST (FastAPI standalone en `avedra-backend`) y distribución como PWA / app escritorio
(Tauri v2) / app Android (Capacitor) desde `avedra-frontend`.

Este roadmap cubre **todos** los controles de seguridad necesarios para ese escenario,
desde los bloqueantes de primer deploy hasta la higiene operacional continua.

No es un roadmap de migración: el código de seguridad existente (`seguridad_01..04`) se
mantiene como base. Este roadmap extiende, endurece y complementa lo ya hecho para el
nuevo contexto de producción multi-usuario en la nube.

### Distribución de responsabilidad de seguridad por repo

| Repo | Controles |
| --- | --- |
| `avedra-backend` | Auth (bcrypt, JWT), throttle, RBAC, multi-tenant scope, auditoría, rate limiting API, secrets, TLS/proxy, headers HTTP, backups, logging seguridad |
| `avedra-frontend` | CSP (ajustada a Vue, no a Quasar), service worker seguro, Tauri origen restringido, actualización segura del .exe, CORS client-side |
| `avedra-shared-contracts` | Versionado de contratos (no exponer campos internos en DTOs públicos), validación de schemas |

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
| **N3 — Con PWA/Tauri/Capacitor** | Aplica en Etapa B, cuando `avedra-frontend` esté en producción. |
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
| S08 | Content Security Policy (NiceGUI→Quasar en Etapa A; Vue en Etapa B) | Código-Alto | `seguridad_web_08_csp` |
| S09 | Logging de seguridad y alertas | Código-Bajo | `seguridad_web_09_logging_alertas` |
| S10 | Backups automatizados y plan de rollback | Infra | `seguridad_web_10_backup_rollback` |
| S11 | CI/CD seguro (secrets, gates, builds reproducibles) | Config | `seguridad_web_11_cicd_seguro` |

### Notas N1

- **S08** tiene dificultad Alta. En **Etapa A** (NiceGUI): Quasar inyecta scripts
  inline y conecta WebSocket, la CSP necesita iteración en staging. En **Etapa B**
  (Vue en `avedra-frontend`): la CSP es más simple (sin WebSocket permanente ni scripts
  inline de Quasar), pero debe cubrir el service worker y los CDN de fuentes/iconos.
  Post-split, la CSP se configura en `avedra-backend` (headers del reverse proxy) pero
  debe ajustarse al contenido que sirve `avedra-frontend`.
- **S09** complementa la cadena de auditoría existente con logging de eventos de
  seguridad y alertas operacionales (logins fallidos masivos, operaciones sensibles).
- **S11** asegura que el pipeline de CI nunca exponga secretos y que solo código con
  tests verdes pueda llegar a prod.

---

## N2 — Con la API REST (Fase 3 del backend_00 roadmap → `avedra-backend`)

No aplican antes de que la API REST esté operativa en `avedra-backend`.
Post-split: estos controles viven en `avedra-backend`.

| ID | Nombre | Dificultad | Spec |
| --- | --- | --- | --- |
| S12 | CORS para API REST | Config | `seguridad_web_12_cors_api` |
| S13 | Autenticación de API (JWT / API keys) | Código-Alto | `seguridad_web_13_jwt_api` |
| S14 | Rate limiting de API | Código-Bajo | `seguridad_web_14_ratelimit_api` |

### Notas N2

- **S13** activa el `jwt_handler.py` que ya existe pero hoy no se usa (diferido en B4
  del épico anterior). Debe incluir revocación y rotación de refresh tokens.
- **S12** es rápido pero crítico: un CORS mal configurado expone la API completa
  a cualquier origen. Post-split, `avedra-backend` debe permitir solo el origen de
  `avedra-frontend` (dominio de producción + localhost en desarrollo).
- **S14** es independiente del rate limiting de login (S05); protege endpoints de la
  API REST contra abuso (scraping, fuerza bruta en endpoints no autenticados).

---

## N3 — Con PWA / Tauri / Capacitor (Etapa B → `avedra-frontend`)

No aplican antes de que `avedra-frontend` esté en producción con sus empaquetados.
Post-split: estos controles viven en `avedra-frontend`.

| ID | Nombre | Dificultad | Spec |
| --- | --- | --- | --- |
| S15 | PWA service worker seguro | Código-Bajo | `seguridad_web_15_pwa_sw` |
| S16 | Tauri: origen restringido y APIs nativas | Código-Bajo | `seguridad_web_16_tauri` |
| S17 | Actualización segura del .exe (Tauri updater) | Código-Alto | `seguridad_web_17_exe_actualizacion` |
| S17b | Capacitor: permisos Android y almacenamiento seguro | Código-Bajo | `seguridad_web_17b_capacitor` |

### Notas N3

- **S15** impide que el service worker cachee tokens o datos sensibles, que quedarían
  expuestos si otra app del mismo origen accede al cache.
- **S16** cambia de WebView2 directo a **Tauri v2** (que usa WebView2 internamente).
  Tauri tiene su propio modelo de permisos (`capabilities` en `tauri.conf.json`) que
  restringe qué APIs nativas puede invocar el frontend. Configurar deny-by-default.
- **S17** es lo más complejo: Tauri v2 incluye un updater nativo que verifica firma
  del paquete antes de instalar. Configurar con clave pública embebida en el binario.
- **S17b** (nuevo): Capacitor en Android necesita: permisos mínimos en `AndroidManifest.xml`,
  almacenamiento seguro para tokens (`@capacitor/preferences` con cifrado), y validación
  de certificado SSL (certificate pinning opcional).

---

## N4 — Continuo / Operacional

No tienen fecha de "done"; son prácticas que se mantienen indefinidamente.

| ID | Nombre | Dificultad | Spec |
| --- | --- | --- | --- |
| S18 | Rotación periódica de secretos | Proceso | `seguridad_web_18_rotacion_secretos` |
| S19 | Pen testing y auditoría externa | Externo | `seguridad_web_19_pentest_auditoria` |

---

## Dependencias entre specs, repos y el backend_00 roadmap

```
avedra-backend — backend_00 Fase 2 (SQLAlchemy + Postgres)
    └── S05 (throttle persistente) — necesita Postgres disponible
    └── S07 (multi-tenant en Postgres) — verifica que scope funciona en SQLAlchemy

avedra-backend — backend_00 Fase 3 (API REST standalone)
    └── S12 CORS — configurar orígenes permitidos (dominio de avedra-frontend)
    └── S13 JWT / API keys — auth para la API que avedra-frontend consume
    └── S14 rate limiting API

avedra-frontend — Etapa B (PWA + Tauri + Capacitor)
    └── S15 service worker seguro
    └── S16 Tauri origen restringido
    └── S17 actualización segura del .exe
    └── S17b Capacitor permisos Android

Cross-repo (avedra-shared-contracts)
    └── No exponer campos internos (password_hash, audit_chain) en DTOs públicos
    └── Validar que el OpenAPI spec no filtra modelos de infraestructura
```

Los ítems N0 (S01–S07) son **independientes** del roadmap de backend: pueden
completarse en paralelo a las Fases 0 y 1 del backend. Post-split, todos
los N0 viven en `avedra-backend`.

---

## Orden recomendado de arranque

**En `avedra-backend` (Etapa A):**

1. **S01 + S02 + S04** en paralelo (pura infra/config, cero riesgo de regresión).
2. **S06** (pip audit) antes de cualquier deploy; toma < 30 minutos.
3. **S03 + S07** una vez que el harness SQLAlchemy esté verde (Fase 1 backend).
4. **S05** al migrar a Postgres (depende de Fase 2 backend).
5. **S08 + S09 + S10 + S11** en las primeras semanas en producción.
6. **S12–S14** cuando la API REST esté standalone en `avedra-backend`.

**En `avedra-frontend` (Etapa B, post-split):**

7. **S08** (revisitar CSP para Vue — más simple que para NiceGUI/Quasar).
8. **S15–S17** cuando PWA + Tauri estén listos.
9. **S17b** cuando Capacitor Android esté listo.

**Continuo (ambos repos):**

10. **S18 + S19** desde el primer día de producción, sin fin.

---

## Estimación de esfuerzo

| Fase | Esfuerzo neto | Observaciones |
| --- | --- | --- |
| N0 (S01–S07) | 2–4 días | S01/S02/S04/S06 son horas; S05 es el más costoso |
| N1 (S08–S11) | 3–6 días | S08 puede llevar más por iteración en CSP |
| N2 (S12–S14) | 2–4 días | Depende de alcance de la API |
| N3 (S15–S17b) `avedra-frontend` | 4–6 días | S17 la más compleja; S17b es nuevo (Capacitor) |
| N4 (S18–S19) | Continuo | S19 puede requerir presupuesto externo |
| **Total** | **~11–21 días** | Distribuidos entre `avedra-backend` (N0–N2) y `avedra-frontend` (N3) |