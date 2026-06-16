# Requisitos: Orden de configuración y panel de Preparación (paso_19_orden_configuracion)

> Contexto: el generador es el último eslabón de una cadena (año → periodos → áreas →
> asignaturas → grupos → plan de estudios → docentes → asignaciones → plantilla →
> salas → generar). Hoy esa cadena no está validada de extremo a extremo: el total de
> horas por grupo es implícito, la carga máxima del docente no se valida al asignar, y
> nada impide intentar generar con datos incompletos. Este paso define el **orden
> canónico**, sus **puertas de validación** y un **panel "Preparación del horario"**.

## Plan de estudios por grado (carga académica declarada)

R1: EL SISTEMA DEBE permitir declarar un **plan de estudios por grado**: qué
    asignaturas y cuántas horas semanales tiene cada grado, de modo que el **total de
    horas por grupo** sea explícito y validable (hoy se infiere de las asignaciones, y
    `horas_semanales` es global por materia, no por grado).

R2: CUANDO existe plan de estudios para un grado, EL SISTEMA DEBE poder usar sus horas
    por grado en lugar del `horas_semanales` global de la asignatura.

## Puertas de validación (en orden)

R3: EL SISTEMA DEBE validar, antes de habilitar la generación, en este orden, y
    reportar el primer eslabón que falle con un motivo accionable:
    1. Hay **un año lectivo activo** y **al menos un periodo** utilizable.
    2. Cada **asignatura** del plan tiene `horas_semanales` ≥ 1.
    3. Para cada **grupo**: `Σ horas del plan del grado` ≤ `slots lectivos de su plantilla`.
    4. Cada **docente** involucrado tiene `carga_horaria_max` y disponibilidad
       suficientes para su carga; `disponibilidad ≥ horas asignadas`.
    5. Las **asignaciones** cubren el plan (cada par grado·materia tiene docente) y
       ningún docente excede su `carga_horaria_max`.
    6. La **plantilla** tiene `slots lectivos ≥ max(horas por grupo)`.
    7. La **capacidad de salas** por tipo ≥ demanda de ese tipo (cuando paso_17 esté).

R4: CUANDO se crea o edita una **asignación**, EL SISTEMA DEBE validar al vuelo que el
    docente no supere su `carga_horaria_max` con esa asignación.

## Panel "Preparación del horario"

R5: EL SISTEMA DEBE mostrar un panel que ejecute las puertas de R3 y presente cada una
    como **verde / roja**, con el conteo del desbalance (p. ej. "Grupo 1101: 35 h
    requeridas, 30 slots disponibles") y un **enlace para corregir** la pieza afectada.

R6: EL SISTEMA DEBE deshabilitar la acción **Generar** mientras alguna puerta **dura**
    esté en rojo, y permitirla cuando todas las duras estén en verde.

R7: El panel DEBE distinguir puertas **duras** (bloquean la generación) de
    **advertencias** (no bloquean pero conviene revisar, p. ej. disponibilidad
    holgada pero ajustada).

## No-regresión

R8: EL SISTEMA NO DEBE romper los flujos actuales de asignaciones, grupos, asignaturas
    ni el generador; `python init.py` debe quedar verde sin regresiones.
