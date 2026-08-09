# Checklist de comercialización — ZECI Manager

> Complementa el roadmap técnico (`roadmap.md`). Estos son los requisitos
> **además de la funcionalidad** para transformar el proyecto en producto comercial.

---

## 1. Bloqueante legal (sin esto no operas)

### Baja dificultad
- [ ] **Política de privacidad y tratamiento de datos** — Ley 1581/2012.
  Documento público: qué datos, para qué, cómo se almacenan, derechos del titular.
  → Plantilla estándar SIC. Servir como `/legal/privacidad`.
- [ ] **Términos de servicio** — Contrato empresa-institución: responsabilidades,
  SLA, destino de datos si dejan de pagar.
  → Plantilla Termly.io/iubenda adaptada a Colombia. Página `/legal/terminos`.
- [ ] **Registro en RNBD** — Toda BD con datos personales se registra ante la SIC.
  → rnbd.sic.gov.co, formulario web gratuito. Después del primer despliegue.

### Media dificultad (requiere código)
- [ ] **Autorización de padres para datos de menores** — Ley 1098, Código de Infancia.
  Consentimiento explícito del acudiente al matricular.
  → Flujo en app: checkbox + tabla `autorizaciones` (fecha, IP, versión documento).
- [ ] **Canal PQRS** — Derechos de consulta, corrección, supresión. Respuesta en
  10 días (consulta) o 15 días (reclamo).
  → Formulario `/legal/pqrs` que crea ticket. O integración Freshdesk/Zendesk.

---

## 2. Bloqueante comercial (sin esto no vendes)

### Baja dificultad
- [ ] **Landing page + demo** — Página pública con precios y botón para probar.
  → Vue+Vite estático en Vercel. Demo = app NiceGUI con seed_demo y usuario
  de solo lectura.
- [ ] **Modelo de precios definido** — ¿Por institución? ¿Por estudiantes?
  → Recomendado: tarifa mensual fija por institución con tiers por tamaño
  (pequeño <200 est, mediano, grande). Prueba gratuita de 30 días.

### Media dificultad (requiere código)
- [ ] **Onboarding guiado de tenant** — Wizard: crear institución, periodos, SIEE,
  importar docentes/estudiantes.
  → Wizard multi-step. Reusar carga masiva Excel. `POST /api/tenants/setup`.
- [ ] **Documentación para usuario final** — Manual por rol (coordinador, profesor,
  director de grupo).
  → MkDocs Material o Docusaurus en `docs.tuapp.com`. Videos cortos Loom/OBS.
- [ ] **Canal de soporte** — WhatsApp es el estándar en colegios colombianos.
  → WhatsApp Business API (Twilio/360dialog) + widget chat (Crisp/Tawk.to gratis).

### Alta dificultad (requiere código)
- [ ] **Pasarela de pago + suscripciones** — Cobro recurrente. Debe soportar PSE.
  → Wompi (Bancolombia, PSE+tarjetas, SDK Python) o ePayco.
  Tabla `suscripciones` + webhook de pago + middleware verifica tenant activo.
  MVP alternativo: cobro manual por transferencia + activación admin.
- [ ] **Facturación electrónica** — Obligatoria DIAN (Resolución 000042/2020).
  → NO desarrollar propio. Integrar con Alegra (API REST, ~$50k COP/mes),
  Siigo, o FacturAPI. Emitir factura automática al recibir webhook de pago.

---

## 3. Bloqueante técnico (sin esto pierdes clientes)

### Baja dificultad (requiere código)
- [ ] **HTTPS obligatorio** — Let's Encrypt gratuito. Railway/Render incluyen TLS.
  Middleware redirección HTTP→HTTPS.
- [ ] **Headers de seguridad** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options.
  → `starlette-security-headers` o `secure.py`. Verificar securityheaders.com.
- [ ] **Backups automatizados PostgreSQL** — Diario + retención 30 días.
  → Railway/Render incluyen backups. Si VPS: `pg_dump` cron + S3/Backblaze B2.
  Probar restauración al menos 1 vez.

### Media dificultad (requiere código)
- [ ] **Observabilidad: errores + métricas** — Saber cuándo algo falla antes que
  el cliente.
  → Sentry (free tier 5k errores/mes, SDK Python). Métricas: PostHog o Plausible.
  Uptime: UptimeRobot gratis.
- [ ] **Rate limiting en API** — Proteger contra fuerza bruta y abuso.
  → `slowapi` para FastAPI. Reglas: 5 login/min por IP, 100 req/min por token.
- [ ] **Tests de aislamiento de tenants** — Un colegio NUNCA ve datos de otro.
  → Tests parametrizados: 2 tenants, operar como tenant A, verificar 0 datos
  de tenant B. Cubrir cada endpoint y repo.
- [ ] **Auditoría de acceso completa** — Quién hizo qué, cuándo. Ya existe el
  módulo — asegurar que la API también registra, no solo la UI NiceGUI.

### Alta dificultad
- [ ] **CI/CD pipeline completo** — Tests en cada push, deploy automatizado, rollback.
  → GitHub Actions: ruff + tests SQLite + tests Postgres (services container) +
  deploy webhook Railway/Render. Rollback: mantener 2 releases.
- [ ] **Entorno de staging** — Copia de producción para probar antes de desplegar.
  → Railway environments o VPS separado. Dominio staging.tuapp.com, seed_dev.

---

## 4. Diferenciador (ganas frente a la competencia)

### Baja dificultad (requiere código)
- [ ] **Boletines con identidad del colegio** — Logo, colores personalizables.
  → Campos `logo_url`, `color_primario` en tabla instituciones. Plantilla Jinja2
  que inyecta en el HTML del boletín. Ya tienes exporters PDF.
- [ ] **Notificaciones a acudientes** — Aviso por falta, nota baja, observación.
  → Email transaccional: Resend (free 100/día) o Amazon SES ($0.10/1k).
  Usar event bus de la Fase 4. WhatsApp API como premium (Twilio ~$0.005/msg).

### Media dificultad (requiere código)
- [ ] **Exportación a formatos de Secretarías de Educación** — Reportes en Excel
  con estructura específica que piden las Secretarías.
  → openpyxl/pandas ya disponibles. Investigar formato de la Secretaría del
  municipio piloto. Empezar con consolidado de notas por periodo.
- [ ] **Dashboard analítico para directivos** — Tasa de inasistencia, rendimiento
  por asignatura, tendencias.
  → Ya tienes estadísticos. Agregar resumen ejecutivo con gráficas (Chart.js en
  NiceGUI / Recharts en Vue). KPIs: % asistencia, % aprobación, alertas activas.

### Alta dificultad (requiere código)
- [ ] **Integración SIMAT** — Sistema Integrado de Matrícula del MEN. Importar/
  exportar estudiantes en su formato.
  → No tiene API pública: archivos planos CSV con estructura fija. Investigar
  formato de matrícula. Importar como carga masiva + mapear campos.
  Diferenciador fuerte: pocos competidores lo hacen bien.
- [ ] **Portal de acudientes (solo lectura)** — Padres ven notas, asistencia,
  observaciones. Sin editar.
  → Rol "acudiente" con permisos de solo lectura filtrado a su estudiante.
  Auth: link con token temporal por email/WhatsApp (sin contraseña para el padre).

---

## 5. Formalización empresarial (requisito para facturar)

- [ ] **Constitución de empresa (SAS)** — Cámara de Comercio, 1 día, ~$200k COP.
  RUT ante la DIAN. No necesitas socio.
- [ ] **Cuenta bancaria empresarial** — Requisito de pasarelas de pago.
  Bancolombia/Davivienda empresarial. Wompi acepta cuenta personal al inicio.
- [ ] **Dominio y correo profesional** — tuapp.co + soporte@tuapp.co.
  Dominio .co Namecheap (~$10/año). Email: Google Workspace ($6/mes) o Zoho (gratis 5 usuarios).

---

## Orden sugerido de ejecución

1. **Formalización empresarial** (SAS + dominio) — hacerlo ya, no depende de código.
2. **Bloqueantes legales de baja dificultad** (políticas + TOS) — antes del primer usuario.
3. **Bloqueantes técnicos de baja dificultad** (HTTPS, headers, backups) — al desplegar.
4. **Onboarding + landing + demo** — para conseguir los primeros colegios piloto.
5. **Autorización de padres + PQRS** — antes de que los colegios carguen datos reales.
6. **Observabilidad + rate limiting + aislamiento** — durante los primeros pilotos.
7. **Pasarela de pago + facturación electrónica** — cuando vas a cobrar en serio.
8. **Diferenciadores** — iterativamente según feedback de los pilotos.
