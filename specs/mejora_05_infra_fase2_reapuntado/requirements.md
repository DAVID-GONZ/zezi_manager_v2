# Requisitos: Fase 2 refactor infra — re-apuntado y retiro de fachada (mejora_05_infra_fase2_reapuntado)

> **Origen:** continuación de `mejora_01` (fase 1 entregó los 5 sub-servicios con
> `InfraestructuraService` como fachada por delegación).
> **⚠️ ALTO CUIDADO CON IMPORTS.** Es la fase que se aplazó por riesgo: toca los
> ~60 call sites de la interfaz. Debe hacerse archivo por archivo con verificación
> de imports.

## Contexto

Tras `mejora_01`, la lógica vive en `SalaService`, `FranjaService`,
`EscenarioHorarioService`, `CatalogoAcademicoService` y
`RestriccionGeneracionService`, pero la interfaz (17 archivos / 60 llamadas) sigue
usando `Container.infraestructura_service()`, que delega. Esta fase completa la
descomposición eliminando la fachada.

## Requisitos

R1: EL SISTEMA DEBE permitir que la capa de interfaz consuma cada operación de
    infraestructura académica a través del servicio cohesivo correspondiente, sin
    pasar por una fachada agregadora.

R2: CUANDO se re-apunta un consumidor, EL SISTEMA DEBE seguir importando sin error
    todos los símbolos que ese archivo usaba (incluidos los re-exports de dominio
    `DiaSemana`, `AreaConocimiento`, `Asignatura`, `Grupo`, `Sala`).

R3: EL SISTEMA DEBE ubicar cada operación de bloques de horario en un único
    servicio canónico (`HorarioService`), sin duplicados con la infraestructura.

R4: EL SISTEMA NO DEBE conservar una fachada `InfraestructuraService` con más de ~25
    métodos públicos; si queda, DEBE ser un residuo mínimo justificado.

R5: EL SISTEMA NO DEBE cambiar el comportamiento observable de ninguna página
    durante el re-apuntado (es sustitución de proveedor, no rediseño).

R6: EL SISTEMA DEBE mantener verde `python init.py` después de re-apuntar cada
    archivo de la interfaz (no al final: por archivo).
