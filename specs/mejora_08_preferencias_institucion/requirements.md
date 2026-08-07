# Requisitos: Preferencias de institución (mejora_08)

> **Origen:** Auditoría del módulo de gestión institucional (2026-08-01).
> **Prerrequisito:** mejora_06 (entidad Institucion enriquecida).
> **Estado:** `spec_ready` — pendiente aprobación de David.

## Contexto del problema

La configuración académica actual vive en `configuracion_anio` y se recrea cada
año. Pero existen preferencias de la institución que no cambian de año en año:
la escala de notas por defecto, el número de periodos habitual, los toggles de
módulos (convivencia, alertas, horarios), y las preferencias de apariencia. Hoy
no hay dónde almacenar estas preferencias de forma centralizada a nivel de
tenant, lo que obliga al director a reconfigurar manualmente cada año nuevo.

En un escenario multitenant, las preferencias del tenant son las que garantizan
una experiencia homogénea para todos los usuarios de la institución.

## Requisitos

R1: EL SISTEMA DEBE crear una tabla `preferencias_institucion` con estructura
    clave-valor tipada, vinculada a la institución por `institucion_id`.
    Estructura: `(id, institucion_id FK, categoria, clave, valor, tipo_valor)`.
    `tipo_valor` admite: `str`, `int`, `float`, `bool`, `json`.
    UNIQUE(institucion_id, clave).

R2: EL SISTEMA DEBE definir las siguientes categorías de preferencias:
    - `academicas`: nota_minima_aprobacion_default, nota_minima_escala_default,
      nota_maxima_escala_default, numero_periodos_default
    - `convivencia`: modulo_convivencia_activo, modulo_alertas_activo
    - `apariencia`: color_primario, color_secundario

R3: CUANDO se crea un nuevo año lectivo, EL SISTEMA DEBE proponer los valores
    por defecto de las preferencias de la institución para los campos
    correspondientes de `configuracion_anio` (nota_minima_aprobacion,
    nota_minima_escala, nota_maxima_escala).

R4: CUANDO un director modifica una preferencia de institución, EL SISTEMA DEBE
    persistir el cambio y aplicarlo a toda la experiencia del tenant sin
    requerir reconfiguración por año.

R5: MIENTRAS un módulo está desactivado en las preferencias de la institución
    (`modulo_convivencia_activo = false`, `modulo_alertas_activo = false`),
    EL SISTEMA DEBE ocultar las rutas y menús correspondientes para todos los
    usuarios del tenant.

R6: CUANDO se crea una institución nueva, EL SISTEMA DEBE inicializar todas las
    preferencias con valores por defecto razonables:
    - nota_minima_aprobacion_default: 60.0
    - nota_minima_escala_default: 0.0
    - nota_maxima_escala_default: 100.0
    - numero_periodos_default: 4
    - modulo_convivencia_activo: true
    - modulo_alertas_activo: true
    - color_primario: null (hereda del design system)
    - color_secundario: null (hereda del design system)

R7: EL SISTEMA NO DEBE permitir que un usuario no-admin modifique las
    preferencias de una institución que no es la suya. Admin solo modifica
    vía impersonación ("Ver como").

## Archivos a crear

- `src/domain/models/preferencia_institucion.py` — modelo Pydantic
- `src/domain/ports/preferencias_repo.py` — puerto abstracto
- `src/infrastructure/db/repositories/sqlite_preferencias_repo.py` — implementación
- `src/services/preferencias_institucion_service.py` — servicio

## Archivos a modificar

- `src/infrastructure/db/schema.py` — CREATE TABLE preferencias_institucion
- `container.py` — wiring del nuevo servicio
- `src/services/configuracion_service.py` — `crear_anio` lee preferencias
- `src/interface/design/layout.py` — NAV_ITEMS condicional por toggles
- `src/interface/auth/route_guard.py` — filtro de rutas por módulos activos

## Notas de diseño

- Tabla clave-valor en vez de columnas rígidas: el catálogo de preferencias
  crecerá con cada feature nueva; evita ALTER TABLE por cada preferencia.
- El campo `tipo_valor` permite casting seguro en el servicio.
- `PreferenciasDTO` agrupa por categoría para consumo de la UI.
- Los toggles de módulo afectan navegación (layout) y guard (route_guard),
  pero NO eliminan datos — desactivar convivencia solo oculta la UI.
