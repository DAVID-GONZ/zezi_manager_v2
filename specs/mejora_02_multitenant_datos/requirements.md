# Requisitos: Aislamiento multi-tenant en datos (mejora_02_multitenant_datos)

> **Origen:** `docs/analisis_arquitectura.md` §6 (hallazgo #5).
> **⚠️ DECISIÓN DE RUMBO REQUERIDA (David).** Este spec solo debe pasar a
> implementación si el multi-tenant real (varias instituciones aisladas) es un
> objetivo del producto. Si el objetivo es single-tenant con catálogo, este spec
> se descarta y se documenta esa decisión en su lugar. **No implementar sin
> aprobación explícita del rumbo.**

## Contexto del problema

Hoy el multi-tenant es "el primer ladrillo": existe la entidad `Institucion` y el
**scope por servicio** (`contexto_tenant`, regla admin→sin scope / resto→su
institución), pero las **tablas académicas** (configuración de año, grupos,
estudiantes, asignaciones, etc.) **no llevan `institucion_id`**. El aislamiento
real entre instituciones no está garantizado a nivel de datos: dos colegios
comparten el mismo espacio de datos académico.

## Requisitos

R1: EL SISTEMA DEBE asociar cada registro académico (año/configuración, grupos,
    estudiantes, asignaciones y sus derivados) a una institución.

R2: MIENTRAS la sesión tiene un scope de institución activo (rol distinto de
    admin), EL SISTEMA DEBE limitar los listados académicos a los registros de esa
    institución.

R3: CUANDO un usuario intenta leer o mutar un registro académico por su
    identificador, EL SISTEMA DEBE rechazar la operación si el registro no
    pertenece a la institución activa de la sesión.

R4: MIENTRAS el rol efectivo es admin de plataforma, EL SISTEMA DEBE permitir la
    operación cross-tenant (sin auto-filtrado), preservando la regla de scope
    actual.

R5: EL SISTEMA DEBE asignar todos los registros académicos preexistentes a la
    institución por defecto (#1) durante la migración, sin pérdida de datos.

R6: EL SISTEMA DEBE crear los registros académicos nuevos con la institución de la
    sesión que los origina.

R7: EL SISTEMA NO DEBE permitir que un usuario no-admin cree, edite o vincule
    registros a una institución distinta de la suya.

R8: EL SISTEMA DEBE conservar verde la suite completa de tests tras la migración,
    incluyendo casos que verifiquen el aislamiento entre dos instituciones.
