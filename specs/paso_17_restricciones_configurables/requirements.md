# Requisitos: Restricciones configurables del generador (paso_17_restricciones_configurables)

> Contexto: el motor solo respeta cruces, disponibilidad, carga máxima y horas
> semanales. Disponibilidad y carga no tienen UI; las salas están hardcodeadas a
> "Aula". Este paso añade el modelo, la UI de captura y el soporte en el motor para
> el catálogo de restricciones reales de un colegio, más el manejo de infactibilidad.
> Ver `specs/epic_17_horarios_produccion/epic.md` para el marco completo.

## Captura de restricciones (UI + persistencia)

R1: EL SISTEMA DEBE permitir configurar la **disponibilidad de cada docente** por
    `(día, franja)` desde la interfaz, persistirla y usarla el motor (hoy solo seed).

R2: EL SISTEMA DEBE permitir configurar la **carga horaria máxima semanal** de cada
    docente desde la interfaz y un **mínimo y máximo de horas por día** por docente.

R3: EL SISTEMA DEBE permitir registrar **salas** con nombre, **tipo** (aula, laboratorio,
    cómputo, ed. física, otro) y **capacidad**, y asociar a una asignatura el **tipo de
    sala requerido**.

R4: EL SISTEMA DEBE permitir, por restricción configurable, elegir su **modo**
    (`estricta` = dura | `preferente` = blanda con peso) cuando aplique, de modo que
    David decida qué es inviolable y qué es deseable sin tocar código.

## Restricciones duras en el motor

R5: CUANDO una asignatura requiere un tipo de sala, EL SISTEMA DEBE asignar una sala
    de ese tipo y NO DEBE colocar dos bloques en la misma sala en la misma franja.

R6: CUANDO una asignación se marca como **bloque doble/consecutivo** de N horas, EL
    SISTEMA DEBE colocar esas N horas en franjas contiguas del mismo día o reportarla
    como no colocada.

R7: CUANDO un grupo/grado tiene una **ventana horaria** (franjas permitidas), EL
    SISTEMA NO DEBE colocar bloques de ese grupo fuera de la ventana.

R8: CUANDO existen **bloques anclados** (pre-colocados) para el escenario, EL SISTEMA
    DEBE respetarlos como fijos y construir el resto alrededor de ellos.

R9: CUANDO una restricción híbrida está en modo `estricta` (mín/máx diario docente,
    máx/día por materia, hueco común de reunión), EL SISTEMA DEBE tratarla como dura;
    en modo `preferente`, como término de coste blando.

## Restricciones blandas (coste) en el motor

R10: EL SISTEMA DEBE penalizar el **desbalance de carga diaria del docente** (días con
     muchas horas junto a días con pocas/ninguna) según un peso configurable.

R11: EL SISTEMA DEBE poder **alinear un hueco común** a un conjunto de docentes en una
     franja designada (franja de reunión), premiando que coincida su tiempo libre.

R12: EL SISTEMA DEBE soportar **preferencia de franja por materia** (p. ej. mañana) y
     **día preferido libre por docente** como términos de coste, sin garantizarlos.

## Infactibilidad (exceso de restricciones)

R13: ANTES de resolver, EL SISTEMA DEBE ejecutar un **chequeo de cotas** (demanda vs.
     capacidad por grupo, por docente y por tipo de sala) y, si una cota es imposible,
     DEBE reportar una incidencia accionable sin intentar la búsqueda.

R14: CUANDO el motor no logra una solución completa, EL SISTEMA DEBE relajar primero
     las restricciones `preferente`/blandas en un orden configurable, nunca las duras,
     y DEBE reportar qué se relajó.

R15: CUANDO quedan bloques sin colocar, EL SISTEMA DEBE indicar por bloque la **causa
     probable** (cruce / disponibilidad / tope / sala / consecutividad / ventana) y un
     **resumen agregado** de causas.

## No-regresión

R16: EL SISTEMA DEBE conservar el comportamiento actual por defecto: sin salas
     configuradas ni restricciones nuevas activas, el resultado debe ser equivalente al
     de hoy (modelo de aula fija), y `python init.py` debe quedar verde sin regresiones.

R17: EL SISTEMA NO DEBE modificar el render de la parrilla (`parrilla_widget.py`) ni
     romper la página de horarios existente.
