# Requisitos: Scoping completo de tablas globales (mejora_07)

> **Origen:** Auditoría del módulo de gestión institucional (2026-08-01).
> **Prerrequisito:** mejora_06 (entidad Institucion enriquecida).
> **Subsume:** mejora_02_multitenant_datos — que se descarta como spec
> independiente y se integra aquí como fase de verificación inicial.
> **Estado:** `spec_ready` — pendiente aprobación de David.

## Contexto del problema

Tras los pasos 24-37, las 8 tablas raíz ya tienen `institucion_id`. Pero varios
catálogos y tablas auxiliares siguen siendo globales sin aislamiento por tenant:
`areas_conocimiento`, `grados`, `plan_estudios`, `categorias_observacion`,
`plantillas_observacion`, `acudientes`, `franjas_reunion`, `auditoria` y
`audit_log`. En multi-tenant real, dos instituciones compartirían estos datos
sin separación.

**Decisión de David:** catálogos 100% por institución. Cada institución tiene
sus propios registros; no hay catálogo global compartido ni flag `is_default`.
Al crear una institución se siembran los catálogos estándar colombianos como
registros propios de esa institución.

## Requisitos

R1: EL SISTEMA DEBE mantener `grados` como catálogo global compartido (números
    1-13 del estándar colombiano) y DEBE crear una tabla puente
    `configuracion_grado_institucion` para configuraciones por institución
    (min/max estudiantes, horas semanales).

R2: EL SISTEMA DEBE agregar `institucion_id` a `areas_conocimiento` y cambiar
    la restricción de unicidad a UNIQUE(institucion_id, nombre). Cada
    institución tiene su propio catálogo de áreas.

R3: EL SISTEMA DEBE agregar `institucion_id` a `plan_estudios` y cambiar la
    restricción de unicidad a UNIQUE(institucion_id, grado, asignatura_id).

R4: EL SISTEMA DEBE agregar `institucion_id` a `categorias_observacion` y
    `plantillas_observacion`, cambiando sus restricciones de unicidad. Cada
    institución define sus propias categorías y plantillas.

R5: EL SISTEMA DEBE agregar `institucion_id` a `acudientes` y cambiar la
    restricción de unicidad de `numero_documento` a
    UNIQUE(institucion_id, numero_documento).

R6: EL SISTEMA DEBE agregar `institucion_id` a `franjas_reunion` para
    particionar las franjas de reunión por institución.

R7: EL SISTEMA DEBE agregar `institucion_id` a las tablas `auditoria` y
    `audit_log` para partición de auditoría por tenant. Este campo es
    informacional y NO debe afectar la cadena de integridad de hash.

R8: CUANDO se crea una institución nueva, EL SISTEMA DEBE sembrar los catálogos
    estándar colombianos como registros propios de esa institución:
    - Áreas de conocimiento estándar (Matemáticas, Ciencias Naturales,
      Ciencias Sociales, Lenguaje, Educación Física, Educación Artística,
      Tecnología e Informática, Educación Ética, Educación Religiosa,
      Filosofía, Ciencias Económicas y Políticas, Idioma Extranjero)
    - Categorías de observación base

R9: EL SISTEMA DEBE migrar todos los registros globales existentes a la
    institución por defecto (#1) sin pérdida de datos.

R10: MIENTRAS la sesión tiene scope de institución activo, EL SISTEMA DEBE
     limitar los catálogos (áreas, plan de estudios, categorías, plantillas,
     acudientes, franjas de reunión) a los de esa institución.

R11: MIENTRAS el rol efectivo es admin de plataforma, EL SISTEMA DEBE permitir
     la visualización cross-tenant de los catálogos.

R12: EL SISTEMA DEBE conservar verde la suite completa de tests tras cada tabla
     migrada. Una tabla por task, suite verde entre cada una.

R13: (ex mejora_02 R1-R8) EL SISTEMA DEBE verificar que las 8 tablas raíz ya
     scopeadas (`configuracion_anio`, `usuarios`, `estudiantes`, `grupos`,
     `asignaturas`, `plantillas_franja`, `salas`) tengan cobertura completa de
     `verificar_pertenencia()` en todos sus servicios y que los repos filtren
     consistentemente por `institucion_id`.

## Orden de implementación

1. Verificación de tablas raíz existentes (R13)
2. `areas_conocimiento` (R2)
3. `plan_estudios` (R3)
4. `categorias_observacion` + `plantillas_observacion` (R4)
5. `acudientes` (R5)
6. `franjas_reunion` (R6)
7. `configuracion_grado_institucion` tabla puente (R1)
8. `auditoria` + `audit_log` (R7)
9. Seed de catálogos para nuevas instituciones (R8)

## Archivos clave

- `src/infrastructure/db/schema.py` — ALTERs y tabla puente nueva
- Repos de cada tabla afectada — agregar filtro `institucion_id` a queries
- Servicios de cada tabla — agregar `_resolver_institucion()` donde falte
- `src/infrastructure/db/seed.py` — función `_seed_catalogos_institucion()`
- `specs/mejora_02_multitenant_datos/` — marcar como subsumido

## Notas de diseño

- Patrón uniforme: ALTER TABLE ADD COLUMN + UPDATE SET institucion_id = 1 WHERE
  NULL + recrear UNIQUE constraints como compound con institucion_id.
- `grados` NO se altera; la personalización por institución va en la tabla puente.
- Catálogos 100% propios: NO hay flag `is_default` ni registros compartidos.
- Auditoría: `institucion_id` es denormalizado desde la sesión del usuario
  actuante; no entra en el payload del hash de integridad.
