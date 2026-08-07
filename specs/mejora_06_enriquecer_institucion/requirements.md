# Requisitos: Enriquecimiento de la entidad Institucion (mejora_06)

> **Origen:** Auditoría del módulo de gestión institucional (2026-08-01).
> **Prerrequisito:** ninguno.
> **Estado:** `spec_ready` — pendiente aprobación de David para pasar a `in_progress`.

## Contexto del problema

La identidad de la institución (nombre oficial, código DANE, rector, dirección,
municipio, teléfono, logo, resolución de aprobación) vive exclusivamente en
`configuracion_anio`. Esto obliga a copiar manualmente los datos de un año al
siguiente y genera inconsistencias cuando la institución cambia de rector o
dirección sin actualizar cada año histórico. En un escenario multi-tenant, cada
nuevo año lectivo debería heredar la identidad vigente sin intervención manual.

La entidad `Institucion` actual solo tiene: `nombre`, `nit`, `codigo`, `activa`,
`fecha_creacion` — insuficiente para representar al tenant completo.

## Requisitos

R1: EL SISTEMA DEBE almacenar los datos de identidad institucional (nombre
    oficial, código DANE, rector, dirección, municipio, teléfono, ruta de logo,
    URL de logo, resolución de aprobación) como atributos de la entidad
    Institucion en la tabla `instituciones`.

R2: EL SISTEMA DEBE almacenar atributos adicionales de clasificación
    institucional: lema, email institucional, jornada principal (AM/PM/UNICA),
    tipo de institución (publica/privada), y calendario (A/B).

R3: CUANDO se crea un nuevo año lectivo, EL SISTEMA DEBE copiar los datos de
    identidad vigentes de la institución al snapshot del año en
    `configuracion_anio`, de modo que los boletines reflejen la identidad al
    momento de emisión.

R4: CUANDO el usuario actualiza la identidad de la institución, EL SISTEMA DEBE
    persistir los cambios en la entidad Institucion sin alterar los snapshots
    de años ya cerrados.

R5: EL SISTEMA DEBE conservar los campos de identidad en `configuracion_anio`
    como snapshot histórico de solo lectura, consumido por el generador de
    boletines e informes.

R6: EL SISTEMA DEBE permitir al director actualizar manualmente el snapshot del
    año activo desde los datos vigentes de la institución (sincronización
    explícita).

R7: EL SISTEMA DEBE validar que nombre oficial no sea vacío y no exceda 200
    caracteres, que código DANE tenga formato numérico de 12 dígitos cuando se
    provea, y que jornada principal y calendario usen los valores del enum
    correspondiente.

R8: EL SISTEMA DEBE migrar los datos de identidad de la `configuracion_anio`
    activa al registro de `instituciones` correspondiente durante la primera
    ejecución posterior a la actualización, sin pérdida de datos. La migración
    debe ser idempotente.

R9: EL SISTEMA NO DEBE romper la generación de boletines ni informes existentes
    al mover la fuente de verdad de identidad.

## Archivos clave

- `src/domain/models/institucion.py` — entidad a enriquecer
- `src/domain/ports/institucion_repo.py` — puerto, agregar `actualizar()`
- `src/infrastructure/db/repositories/sqlite_institucion_repo.py` — implementación
- `src/infrastructure/db/schema.py` — ALTER TABLE instituciones
- `src/services/institucion_service.py` — lógica nueva
- `src/services/configuracion_service.py` — `crear_anio` auto-snapshot
- `src/infrastructure/db/seed.py` — migración de datos existentes

## Notas de diseño

- `nombre` en `instituciones` es el nombre corto del catálogo; `nombre_oficial`
  es el nombre completo que aparece en boletines.
- Los campos nuevos son todos opcionales con defaults sensatos para no romper
  la creación de instituciones existente.
- `InformacionInstitucionalDTO.desde_configuracion()` sigue siendo el factory
  para boletines históricos; se agrega `desde_institucion()` para previews.
