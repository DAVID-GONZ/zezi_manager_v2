# Requisitos: Descomposición de InfraestructuraService/Repo (mejora_01_refactor_infraestructura)

> **Origen:** `docs/analisis_arquitectura.md` §6 (hallazgo #6 — objeto-Dios).
> **Tipo:** MOVER (refactor sin cambio de comportamiento). No crea capacidades
> nuevas: reorganiza responsabilidades preservando todos los contratos y tests.

## Contexto del problema

`InfraestructuraService` expone **75 métodos públicos** e `IInfraestructuraRepository`
**100 métodos**, concentrando escenarios, plantillas/franjas, áreas, asignaturas,
grupos, salas, horarios, disponibilidad, configuración de generación y
restricciones. Viola el Principio de Responsabilidad Única y dificulta el
mantenimiento y el testeo.

## Requisitos

R1: EL SISTEMA DEBE conservar, tras el refactor, todas las capacidades de gestión
    de infraestructura académica existentes (escenarios, plantillas/franjas, áreas,
    asignaturas, grupos, salas, horarios, disponibilidad, configuración de
    generación y restricciones) sin cambios observables para el usuario.

R2: EL SISTEMA DEBE agrupar esas capacidades en servicios cohesivos, cada uno
    responsable de un único subdominio, de modo que ningún servicio de
    infraestructura académica supere ~25 métodos públicos.

R3: EL SISTEMA DEBE exponer cada servicio resultante a través del `Container`
    mediante un método de fábrica propio, manteniendo la instanciación única.

R4: MIENTRAS exista consumo desde la capa de interfaz de la API previa, EL SISTEMA
    DEBE seguir resolviendo esas llamadas (compatibilidad hacia atrás durante la
    transición, sin romper páginas).

R5: EL SISTEMA NO DEBE alterar la firma, los parámetros ni el tipo de retorno de
    ninguna operación durante el movimiento (es un MOVER, no un rediseño de API).

R6: EL SISTEMA NO DEBE introducir consultas SQL nuevas ni cambiar la lógica de
    negocio; los métodos movidos deben delegar en los mismos puertos de repositorio.

R7: EL SISTEMA DEBE mantener verde la suite completa de tests (`python init.py`)
    después de cada extracción de subdominio, sin regresiones.

R8: EL SISTEMA DEBE resolver el solapamiento actual entre los métodos de horarios
    de `InfraestructuraService` y el `HorarioService` existente, dejando una única
    ubicación canónica para cada operación de bloques horarios.
