# Análisis de Arquitectura — ZECI Manager v2.0

> **Fecha:** 2026-07-11 · **Tipo:** Auditoría integral del estado construido.
> Snapshot en el tiempo (no doc vivo). La referencia vigente es
> `docs/architecture.md`; la referencia por método,
> `docs/api_reference.md`. Reemplaza a la auditoría de mayo-2026 (obsoleta).

---

## 1. Veredicto ejecutivo

Sistema de gestión académica **maduro y bien arquitecturado**, en fase de
**cierre de migración**: **94 de 95 pasos** del roadmap están `done` (~99%); el
único pendiente es `audit_design_system`. La
Arquitectura Limpia no es decorativa — está **enforced por tooling** (`init.py`
con gate de anti-patrones, guard de rutas deny-by-default, `Container` como único
punto de instanciación). La deuda restante es de *afinado y saneamiento*, no
estructural.

| Dimensión | Madurez | Nota |
|---|---|---|
| Arquitectura / separación de capas | 🟢 Excelente | Regla de dependencias verificada por tooling; dominio puro |
| Cobertura funcional | 🟢 Alta | Evaluación, asistencia, convivencia, horarios, informes, admin |
| Seguridad | 🟢 Sólida | Épico A1–A2 / M1–M4 / B1–B4 cerrado en código + decisiones |
| Testing | 🟢 Fuerte | ~1.276 tests; ratio test/código sano |
| Documentación | 🟢 Completa | Narrativa + referencia por método auto-generada |
| Multi-tenant | 🟡 Inicial | Solo "primer ladrillo" (scope por servicio, sin aislamiento total) |
| Salud del entorno/CI | 🟡 Con fricciones | 1 test roto; drift de bookkeeping |

## 2. Métricas del sistema

| | Valor |
|---|---|
| Código fuente | ~48.500 líneas (`domain` 13k · `services` 10k · `infrastructure` 14k · `interface` 22k) |
| Tests | ~19.400 líneas, **1.276 tests** (`tests/unit` + `tests/integration`) |
| Capas de dominio | 19 modelos · 20 puertos · 3 políticas · ~23 servicios (+3 mecanismos) · 19 repos SQLite · ~30 páginas |
| Superficie de API | 484 métodos de modelo · 364 de puerto · 351 de servicio · 429 de infra |
| Base de datos | SQLite, **60 tablas**, WAL |
| Roadmap | 95 pasos: **94 done**, 1 pending (`audit_design_system`) |

## 3. Fortalezas (lo bien construido)

1. **Disciplina de capas real, no aspiracional.** El dominio no importa nada
   externo; los servicios no ven SQL ni NiceGUI; `pandas` confinado a
   infraestructura. Un **gate automático** (`init.py`) rompe el build si alguien
   cruza la frontera.
2. **Composition root único** (`container.py`) con singleton lazy y `diagnostico()`
   que instancia todo al arrancar para detectar config rota antes de servir.
3. **Seguridad como mecanismos transversales, no parches por página**:
   autorización deny-by-default centralizada (`registrar_pagina`), políticas de
   dominio puras (RBAC, contraseñas, cadena hash) como fuente de verdad para
   servicio *y* vista, y `ContextVar` para solo-lectura ("Ver como") y scope de
   tenant.
4. **Auditoría con integridad criptográfica** (cadena SHA-256 append-only).
5. **Testing serio**: 1.276 tests, trazabilidad requisito↔test, BD en memoria.
6. **Documentación completa y sostenible**: narrativa + referencia por método
   **generada desde el código** (`tools/gen_api_reference.py`).

## 4. Cobertura funcional construida

Académico: matrícula/estudiantes + PIAR · evaluación (categorías, actividades,
planilla en vivo, SIEE) · cierre de periodo/año con **decisiones de promoción** ·
habilitaciones · **nivelación** y **planes de mejoramiento** (Decreto 1290) ·
asistencia con alertas automáticas · convivencia · **generador automático de
horarios** (backtracking + restricciones) · informes/boletines (Excel/PDF/CSV con
degradación en cascada) · administración (usuarios, roles, auditoría, config
institucional) · 6 roles.

## 5. Seguridad — estado

Épico cerrado: bcrypt(12) + política de contraseñas + throttle (A1), cambio
forzado (A2), secretos independientes con bloqueo de arranque (M1/M3), cadena hash
de auditoría (M4), sync central de contexto (B1). Diferido explícitamente: TLS por
reverse proxy (M2), revocación JWT a v3 (B4), `check_same_thread` aceptado (B3). No
enumeración de usuarios en login. Modelo coherente y documentado (`docs/seguridad.md`).

## 6. Debilidades, riesgos y deuda técnica

> **Nota de entorno.** El proyecto usa un virtualenv en `.venv/` con las
> dependencias instaladas (`requirements.txt`). Toda verificación debe correrse
> con `.venv/Scripts/python.exe`, no con el Python global. Los hallazgos #1 y #3
> de una versión previa de este análisis resultaron ser artefactos de usar el
> intérprete global (sin `pydantic-settings`), no defectos reales.

| # | Hallazgo | Evidencia | Severidad |
|---|---|---|---|
| 1 | **Dependencias del entorno** instaladas en `.venv/`; la app arranca. Verificar siempre con el intérprete del venv | app OK con `.venv` | ✅ Resuelto |
| 2 | **Off-by-one en throttle**: `login_throttle.estado_bloqueo` devuelve `int(restante)+1`, que puede exceder `BLOQUEO_SEGUNDOS` (301 > 300) con timer grueso de Windows | `test_bloquea_al_alcanzar_el_limite` falla (con `.venv`) | 🟠 Media |
| 3 | ~~Módulo de test no colecta~~ — **falso positivo**: `test_config_secrets.py` pasa (7/7) con el intérprete del `.venv` | 7 passed | ✅ No es defecto |
| 4 | ~~Drift de bookkeeping~~ — **reconciliado**: `seguridad_04` marcado `done` (guardarraíl B1: 18/18 verde, criterio de done cumplido) | `step_list.json` | ✅ Resuelto |
| 5 | **Multi-tenant = primer ladrillo**: aislamiento por *scope de servicio*, pero las tablas académicas aún no llevan `institucion_id`; la separación real entre colegios no está completa | docstring de `institucion.py` | 🟡 Media |
| 6 | **Objeto-Dios en infraestructura académica**: `InfraestructuraService` (75 métodos) e `IInfraestructuraRepository` (100 métodos) violaban SRP. **Fase 1 (`mejora_01`)**: lógica movida a 5 sub-servicios cohesivos. **Fase 2 (`mejora_05`)**: interfaz **100% desacoplada** (0 referencias a la fachada), horarios consolidados en `HorarioService`. La fachada se retiene como **agregador del generador de horarios** (uso legítimo, no deuda). Pendiente opcional: partir `IInfraestructuraRepository` (100 métodos) | conteos de métodos | 🟢 Resuelto (fachada = agregador) |
| 7 | **Generador de horarios**: backtracking/coloreo — mayor complejidad y riesgo de rendimiento/calidad; difícil de testear exhaustivamente | `generador_horario_service.py` | 🟡 Media |
| 8 | **Docstrings de modelos al 28%** (muchos validators/propiedades triviales) | `docs/api_reference/dominio_modelos.md` | 🟢 Baja |
| 9 | `audit_design_system` **pending**: saneamiento del design system sin cerrar | `step_list.json` | 🟢 Baja |

## 7. Recomendaciones priorizadas

**P0 — desbloquear ejecución** ✅ *(hecho: entorno con deps instaladas, la app arranca)*

**P1 — cerrar lo casi-terminado**
- Corregir el off-by-one del throttle (#2): acotar el retorno a
  `(0, BLOQUEO_SEGUNDOS]`.
- Reconciliar `step_list.json` (#4): marcar `seguridad_04` `done` si B1 está
  cerrado y verificado.

**P2 — deuda de mantenibilidad (cuando haya margen)**
- Decidir el rumbo de multi-tenant (#5): si es objetivo real, planificar
  `institucion_id` en tablas académicas; si no, documentarlo como single-tenant
  con catálogo.
- Descomponer `InfraestructuraService`/repo (#6) en sub-servicios cohesivos
  (Escenarios, Franjas, Catálogo académico, Restricciones). **Fase 1 completada en
  `mejora_01`**; fase 2 (re-apuntado + retiro de fachada) en `mejora_05`.
- Backfill de docstrings de modelos con lógica no trivial (#8).
- Planificar `audit_design_system` (#9) como paso propio con su spec.

---

**Síntesis.** Lo construido es un sistema académico completo, con una arquitectura
y una postura de seguridad de calidad poco común para su dominio. Lo que falta es
*higiene de cierre* (1 test, bookkeeping) y dos decisiones de rumbo (multi-tenant y
descomposición del módulo de infraestructura), no reconstrucción.
