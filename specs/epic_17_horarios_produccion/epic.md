# Épico 17 — Horarios listos para producción

> Estado: **propuesta** (pendiente de aprobación de David).
> Objetivo: llevar el generador de horarios de "borrador automático para el modelo
> de aula fija" a "herramienta utilizable en colegios reales", con restricciones
> configurables, una sola página de gestión coherente, y un orden de configuración
> validado de extremo a extremo.

Este documento es el **marco** del épico: el análisis, el catálogo de restricciones,
la descomposición en specs, el grafo de dependencias y la recomendación de orden de
configuración. Cada spec ejecutable vive en su propio directorio:

- `specs/paso_17_restricciones_configurables/` — motor + modelo + UI de restricciones.
- `specs/paso_18_horarios_unificado/` — dedup de funciones + página única con toggles semánticos.
- `specs/paso_19_orden_configuracion/` — orden de configuración y panel de validación ("Preparación").

---

## 0. Diagnóstico de partida (qué hay hoy)

Motor (`src/services/generador_horario_service.py`): backtracking con heurística MRV
+ atajo por coloreo de aristas bipartito (König) + hill-climbing sobre coste blando.
Algorítmicamente sólido.

Restricciones **duras** que ya respeta:
- No cruce de grupo / no cruce de docente.
- Disponibilidad del docente por `(día, franja)` — `DisponibilidadDocente`.
- Carga horaria máxima semanal del docente — `usuarios.carga_horaria_max`.
- Horas semanales por asignatura — `asignaturas.horas_semanales`.
- Franjas no lectivas (recreo/almuerzo) y días activos de la plantilla.

Restricciones **blandas** que optimiza (pesos editables):
- Huecos de grupo y de docente, distribución semanal, compactación del docente.

**Tres carencias estructurales detectadas en el análisis:**

1. **Salas hardcodeadas a `"Aula"`.** El validador (`HorarioService._validar_cruces`)
   ya sabe detectar choque de sala, pero el generador nunca asigna sala real → sin
   contención de laboratorios, sala de cómputo, ed. física, ni capacidad de aula.
2. **Disponibilidad y carga máxima no tienen UI.** Backend completo
   (`bloquear_franjas_docente`, `listar_disponibilidad_docente`, `carga_horaria_max`)
   pero hoy solo se fijan vía `seed`. El motor consume restricciones que el usuario
   no puede editar.
3. **`horas_semanales` es global por materia, no por grado.** No existe un "plan de
   estudios por grado" (Matemáticas 5h en 6° vs 4h en 11°). La carga académica de un
   grupo se infiere de las asignaciones, no de un plan declarado y validable.

---

## 1. Catálogo completo de restricciones (caso de uso → tipo)

Leyenda de tipo: **D** = dura (factibilidad), **B** = blanda (coste/optimización),
**H** = híbrida (configurable como dura o blanda).

### Ya implementadas
| # | Restricción | Tipo | Estado |
|---|---|---|---|
| 1 | No cruce de grupo / docente | D | ✅ |
| 2 | Disponibilidad docente por (día, franja) | D | ✅ backend, ❌ UI |
| 3 | Carga máxima semanal del docente | D | ✅ backend, ❌ UI |
| 4 | Horas semanales por asignatura | D | ✅ (global, no por grado) |
| 5 | Huecos grupo/docente, distribución, compactación | B | ✅ |

### Nuevas — pedidas por David
| # | Restricción | Tipo | Caso de uso |
|---|---|---|---|
| 6 | **Mín. / máx. horas diarias por docente** | H | Evitar días de 6h junto a días de 0h; repartir la jornada. |
| 7 | **Control de huecos del docente** | H | Limitar ventanas vacías para que el docente pueda reunirse / no perder tiempo muerto. |
| 8 | **Hueco común a varios docentes** (franja de reunión) | H | Reservar/alinear una franja libre compartida por un conjunto de docentes (área, comité) para reuniones. |

### Nuevas — propuestas en el análisis (otros casos de uso reales)
| # | Restricción | Tipo | Caso de uso |
|---|---|---|---|
| 9 | **Salas/aulas reales** (tipo + capacidad) | D | Labs, sala de cómputo, cancha de ed. física: una clase requiere cierto tipo de sala; dos clases no comparten sala a la vez. |
| 10 | **Bloques dobles / consecutivos** | D | Materias que necesitan N horas seguidas (lab, ed. física, taller). |
| 11 | **Máx. horas/día de una materia (duro)** | H | "Máximo 2 de Matemáticas al día" como regla dura, no solo preferencia. |
| 12 | **Ventanas horarias por grupo/grado** | D | Primaria sale a mediodía; jornadas o cortes distintos por grado. |
| 13 | **Preferencia de franja por materia** | B | Materias densas en la mañana; ed. física no a 1.ª/última hora. |
| 14 | **Bloques anclados / fijados** | D | Pre-colocar un bloque (recurso compartido, reunión institucional) y que el motor lo respete. |
| 15 | **Día preferido libre por docente** | B | Preferencia (no garantía) de un día sin clases. |
| 16 | **Desdobles / grupos partidos / co-docencia** | D | Grupo que se divide para inglés; dos grupos que se fusionan. *(El más complejo; fase final.)* |

---

## 2. Estrategia para el exceso de restricciones (infeasibilidad)

Con muchas restricciones duras, el problema puede volverse **infactible**. La regla
de oro: **no fallar en silencio ni colgarse en backtracking exponencial**. Tres capas:

1. **Pre-vuelo (cotas necesarias, O(n), antes de generar).** Detecta imposibilidad
   evidente sin resolver:
   - Por grupo: `Σ horas del plan` ≤ `slots lectivos de su plantilla`.
   - Por docente: `Σ horas asignadas` ≤ `min(carga_max, slots disponibles)`.
   - Por tipo de sala: `Σ horas que requieren tipo T` ≤ `(salas de tipo T) × slots`.
   - Por bloques dobles: existencia de pares de franjas consecutivas suficientes.
   - Cada fallo de cota → incidencia accionable: *"Docente X: 24 h requeridas pero
     solo 20 slots disponibles → ampliar disponibilidad o reducir carga."*

2. **Resolución con presupuesto y relajación ordenada.** Si el pre-vuelo pasa pero el
   motor no encuentra solución completa dentro del presupuesto de iteraciones:
   - Las **duras nunca se rompen**; las **blandas** ya se tratan como coste.
   - Las **híbridas** marcadas como "preferentes" (no "estrictas") se relajan en orden
     configurable (p. ej. primero min/max diario, luego huecos, luego franja preferida).
   - Resultado parcial: se reporta qué quedó sin colocar y **qué restricción lo impidió**.

3. **Diagnóstico por restricción en el resultado.** El `ResultadoGeneracionDTO` se
   enriquece con, por bloque no colocado, la causa probable (cruce / disponibilidad /
   tope / sala / consecutividad) y un resumen agregado ("12 no colocados: 8 por falta
   de sala de cómputo, 4 por tope docente"). Esto convierte "no se pudo" en "esto hay
   que ajustar".

> Mecanismo de configuración: cada restricción híbrida (6, 7, 8, 11) lleva un modo
> **estricta | preferente** y, las blandas, un **peso**. Así David decide, sin tocar
> código, qué es inviolable y qué es deseable.

---

## 3. Orden de configuración recomendado (resumen; detalle en paso_19)

El generador es el **último eslabón** de una cadena de configuración. El orden y sus
puertas de validación:

```
1. Año lectivo activo + Periodos          → gate: 1 año activo, ≥1 periodo abierto
2. Áreas + Asignaturas (horas_semanales)  → gate: cada asignatura con horas ≥ 1
3. Grupos (grado, jornada, capacidad)
   + Plan de estudios por grado            → gate: Σ horas del plan/grupo ≤ slots de su plantilla
4. Docentes: carga_horaria_max + disponib. → gate: Σ carga docentes/área ≥ demanda; disponib ≥ carga
5. Asignaciones (docente×materia×grupo)    → gate: Σ horas/docente ≤ carga_max; plan completo
6. Plantilla de franjas (rejilla)          → gate: slots lectivos ≥ max(horas/grupo)
7. Salas + restricciones de generación     → gate: capacidad por tipo de sala ≥ demanda
8. Config de generación + Generar
```

**Decisiones clave que sustenta el análisis:**
- El **total de horas por grupo** debe declararse (plan de estudios) **antes** de las
  asignaciones; hoy es implícito. Las asignaciones *materializan* ese plan.
- La **carga máxima por docente** debe existir **antes** de asignar, para validar al
  vuelo que ninguna asignación exceda el tope.
- La **disponibilidad** puede capturarse en paralelo, pero **antes de generar**.
- La validación se materializa como un **panel "Preparación del horario"**: ejecuta
  las puertas en orden, marca cada una verde/roja con el motivo y un enlace para
  corregir. El botón "Generar" solo se habilita con todas las puertas duras en verde.

---

## 4. Descomposición en specs y dependencias

```
        paso_19 (orden + panel Preparación)
                 │  define las puertas/validaciones
                 ▼
   paso_17 (restricciones: modelo → UI → motor → infeasibilidad)
                 │  produce datos y motor que la UI unifica
                 ▼
        paso_18 (dedup + página única con toggles)
```

- **paso_19** primero conceptualmente (define qué se valida y en qué orden), pero su
  panel consume piezas de 17. Se puede empezar por el **modelo/validadores de 19** en
  paralelo con el **modelo de 17**.
- **paso_17** es el grueso; su `tasks.md` está fraseado en fases incrementales
  (modelo → UI de captura → duras → blandas → infeasibilidad) entregables una a una.
- **paso_18** va al final: unifica en una sola página lo que para entonces ya existe
  (preparar / generar / visualizar / editar), y limpia la duplicidad.

### Riesgos y regla de oro del épico
- **No tocar `parrilla_widget.py` ni el render de la parrilla** salvo para *extraer*
  `_opciones_eje` (dedup) — el render funcional se conserva.
- Las restricciones nuevas se añaden **detrás de flags por restricción**, de modo que
  el comportamiento actual (aula fija, sin salas) siga siendo el camino por defecto.
- Cada fase debe dejar `python init.py` verde y sin regresiones de tests.

---

## 5. Decisiones aprobadas (2026-06-14)

David aprobó el marco con estas decisiones, ya bakeadas en los specs:

1. **Plan de estudios por GRADO** (no por grupo concreto): todos los grupos de un
   mismo grado comparten plan. (paso_19)
2. **Alcance de paso_17 = todo menos desdobles**: salas, bloques dobles, mín/máx
   diario docente, control de huecos, hueco común, ventanas de grupo, anclados y
   preferencias entran en paso_17. **Desdobles / grupos partidos / co-docencia**
   (catálogo #16) se difieren a un **paso_17g** posterior.
3. **Página única con toggles** (paso_18): Preparar/Generar/Visualizar/Editar en una
   sola página; las rutas viejas quedan como alias.
4. **Modo desarrollo: sin migración.** Los cambios de esquema (tablas/columnas nuevas)
   se aplican editando el DDL en `schema.py` y **recreando la BD con `seed`** — no se
   escribe lógica de migración aditiva ni se requiere respaldo. El `seed` debe poblar
   datos de ejemplo de las entidades nuevas.

Quedan en estado `spec_ready`. **No se implementa nada** hasta el visto bueno para
arrancar la primera fase (recomendado: empezar por el modelo de paso_19 + paso_17
fase A en paralelo). Las preguntas abiertas restantes en cada spec son de detalle de
implementación, no bloquean el arranque.
