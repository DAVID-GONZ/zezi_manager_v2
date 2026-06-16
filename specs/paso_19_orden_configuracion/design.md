# Diseño: Orden de configuración y panel de Preparación (paso_19_orden_configuracion)

## 0. Análisis del orden (la respuesta a "qué va primero y cómo se valida")

La cadena de dependencias, de la más fundamental a la más derivada:

```
Año lectivo (activo)
  └─ Periodos
       └─ Áreas → Asignaturas (horas_semanales)
            └─ Grupos (grado, jornada) + PLAN DE ESTUDIOS POR GRADO  ← define total horas/grupo
                 └─ Docentes (carga_horaria_max + disponibilidad)    ← capacidad de oferta
                      └─ Asignaciones (docente×materia×grupo×periodo) ← materializan el plan, consumen carga
                           └─ Plantilla de franjas                   ← define slots disponibles
                                └─ Salas + restricciones (paso_17)
                                     └─ Config de generación → Generar
```

**Por qué este orden (decisiones del análisis):**
- **El total de horas por grupo precede a las asignaciones.** Hoy el total se *infiere*
  sumando asignaciones; eso impide validar "faltan/sobran horas" antes de asignar. Con
  un **plan de estudios por grado** (R1) el total es un dato declarado: las asignaciones
  pasan a *cumplir* el plan, y se puede medir cobertura ("Matemáticas de 6° sin docente").
- **La carga máxima del docente precede a las asignaciones.** Si el tope existe antes,
  cada asignación se valida al vuelo (R4) y se evita el sobrecupo silencioso que el
  motor luego no puede resolver.
- **La disponibilidad puede capturarse en paralelo** pero debe estar **antes de generar**
  (el motor la usa como dura).
- **La plantilla precede a generar** y su nº de slots es el techo de horas/grupo.
- **Las salas (paso_17) son la última capa dura** antes de generar.

**Cómo se valida:** un conjunto de **validadores puros de servicio** (sin UI), uno por
puerta de R3, que devuelven `(ok, mensaje, enlace_fix)`. El panel los ejecuta en orden.

## 1. Plan de estudios por grado (R1, R2)

Modelo nuevo `PlanEstudios(grado, asignatura_id, horas_semanales)` con clave
`(grado, asignatura_id)`, persistido en tabla `plan_estudios`. **Modo desarrollo: sin
migración** — se añade el DDL en `schema.py` y se recrea la BD con `seed` (que debe
poblar un plan de estudios de ejemplo).
- `horas_por_grupo(grupo) = Σ horas del plan del grado del grupo`.
- Si un grado no tiene plan, *fallback* al `horas_semanales` global de la asignatura
  (compatibilidad con el comportamiento actual).
- Servicio `PlanEstudiosService` con CRUD + `horas_por_grado(grado)` / `horas_por_grupo`.

## 2. Validadores (R3) — `PreparacionHorarioService`

Servicio nuevo (lógica pura, sin UI) que expone:

```python
def validar(anio_id, periodo_id, plantilla_id) -> ReportePreparacionDTO
```

`ReportePreparacionDTO = list[PuertaDTO]`, cada `PuertaDTO`:
`{ id, titulo, severidad: "dura"|"advertencia", ok: bool, detalle: str, fix_ruta: str|None }`.

Puertas (una función por eslabón de R3), todas O(n) sobre datos ya cargados:
1. `año_periodo_ok`.
2. `asignaturas_con_horas`.
3. `horas_grupo_vs_slots` (usa plan de estudios + plantilla).
4. `capacidad_docente` (carga_max y disponibilidad ≥ carga).
5. `cobertura_asignaciones` (plan cubierto + sin sobrecupo docente).
6. `plantilla_suficiente`.
7. `salas_suficientes` (solo si paso_17 activo; si no, advertencia neutra).

`puede_generar(reporte) -> bool` = todas las puertas `dura` en `ok`.

## 3. Validación al vuelo de asignaciones (R4)

En `AsignacionService.crear/actualizar`: antes de persistir, calcular
`carga_actual_docente + horas_de_esta_asignacion` y rechazar si supera
`carga_horaria_max` (con `ValueError` accionable). Reutiliza `carga_horaria_max` y la
suma de horas vía plan/asignatura.

## 4. Panel "Preparación" (R5–R7)

Sección/página que llama `PreparacionHorarioService.validar(...)` y pinta una lista de
puertas: ícono verde/rojo (o ámbar para advertencia), título, detalle con el conteo del
desbalance, y un botón "Corregir" que navega a `fix_ruta`. Botón "Generar"
deshabilitado mientras `puede_generar` sea falso (R6). Se integra como sección
**Preparar** de la página única (paso_18); si paso_18 aún no existe, vive como bloque
en el generador.

## 5. Archivos afectados
- `src/domain/models/` — `PlanEstudios`, DTOs de preparación.
- `src/infrastructure/db/schema.py` + repo — tabla `plan_estudios` (DDL directo, sin
  migración; recrear BD con seed).
- `src/services/` — `plan_estudios_service.py`, `preparacion_horario_service.py`;
  ajuste en `asignacion_service.py` (R4).
- `container.py` — registrar los servicios nuevos.
- `src/interface/pages/...` — panel Preparación (reubicable en paso_18).

## 6. Manejo de errores
- Validadores nunca lanzan: devuelven puertas con `ok=False` y detalle.
- R4 sí lanza `ValueError` (es una operación de escritura que debe abortarse).

## 7. Decisiones y preguntas abiertas

**Aprobado:** el plan de estudios es **por grado** (6°, 7°…). Todos los grupos de un
mismo grado comparten plan. La clave del modelo es `(grado, asignatura_id)`.

Pendientes de detalle (no bloquean el arranque):
1. ¿La "carga académica" incluye horas no lectivas del docente (dirección de grupo,
   coordinación) que descuentan de su disponibilidad?
2. ¿El panel Preparación es visible para coordinadores o solo admin/director?
