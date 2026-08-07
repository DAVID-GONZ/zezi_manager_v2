# Requisitos: Hub de gestión institucional (mejora_09)

> **Origen:** Auditoría del módulo de gestión institucional (2026-08-01).
> **Prerrequisito:** mejora_06 (entidad enriquecida) + mejora_08 (preferencias).
> **Estado:** `spec_ready` — pendiente aprobación de David.

## Contexto del problema

La página actual `configuracion_institucion.py` edita campos de
`configuracion_anio`, no de la entidad `Institucion`. No existe UI para:
(a) editar la identidad de la institución como tal, (b) gestionar preferencias
del tenant, (c) visualizar el catálogo de instituciones (solo admin).
El director no tiene un punto central para administrar toda la configuración
institucional que garantice experiencia homogénea para su tenant.

## Requisitos

R1: EL SISTEMA DEBE ofrecer una página hub de gestión institucional accesible
    desde el menú de Administración, con secciones organizadas por tabs o cards:
    Identidad, Preferencias Académicas, Convivencia, Apariencia.

R2: CUANDO el director accede a la sección Identidad, EL SISTEMA DEBE mostrar
    un formulario con todos los campos de identidad de la institución:
    nombre oficial, código DANE, NIT, rector(a), dirección, municipio,
    teléfono, lema, email institucional, tipo de institución, calendario,
    jornada principal, logo. Todos editables.

R3: CUANDO el director guarda cambios de identidad, EL SISTEMA DEBE persistir
    en la entidad `Institucion` y ofrecer la opción de sincronizar el snapshot
    del año activo (para que los boletines futuros reflejen la identidad
    actualizada).

R4: CUANDO el director accede a la sección Preferencias Académicas, EL SISTEMA
    DEBE mostrar los valores por defecto configurables (nota mínima de
    aprobación, escala de notas, número de periodos) con indicación visual de
    que "aplican a años nuevos, no al año activo".

R5: CUANDO el director accede a la sección Convivencia, EL SISTEMA DEBE
    mostrar los toggles de módulos (convivencia activo, alertas activas) con
    advertencia de que desactivar un módulo oculta sus rutas y menús para
    todos los usuarios.

R6: EL SISTEMA DEBE refactorizar la página existente
    `configuracion_institucion.py` (ruta `/admin/configuracion-institucion`)
    para que edite la entidad `Institucion` en vez de `configuracion_anio`,
    manteniendo la ruta y el guard de acceso (admin, director).

R7: MIENTRAS el rol es admin de plataforma, EL SISTEMA DEBE ofrecer una página
    separada de catálogo de instituciones accesible desde Administración:
    listar instituciones, crear nueva, activar/desactivar. Esta página NO es
    el hub del director — es gestión de la plataforma.

R8: EL SISTEMA NO DEBE permitir que un director vea o edite datos de una
    institución distinta de la suya. El aislamiento por tenant se aplica vía
    `verificar_pertenencia()` y el scope del ContextVar.

R9: EL SISTEMA DEBE seguir el design system vigente (Aula Serena) en todas
    las secciones nuevas: `panel-card`, `form_dialog`, `btn_primary/ghost`,
    `toast_*`, `empty_state`, tipografía y paleta existentes.

## Archivos a modificar

- `src/interface/pages/admin/configuracion_institucion.py` — refactorizar para
  editar entidad `Institucion` (hub del director)
- `src/interface/design/layout.py` — agregar items de navegación nuevos
- `main.py` — registrar rutas nuevas

## Archivos a crear

- `src/interface/pages/admin/preferencias_institucion.py` — editor de
  preferencias del tenant (si se separa del hub, o integrado como tab)
- `src/interface/pages/admin/catalogo_instituciones.py` — CRUD de
  instituciones (solo admin)

## Notas de diseño

- El hub del director reutiliza la ruta existente
  `/admin/configuracion-institucion` para no romper bookmarks.
- El catálogo de instituciones (admin) va en ruta nueva:
  `/admin/instituciones`.
- Patrón de tabs dentro del hub: tab de Identidad usa los campos de
  `Institucion`, tabs de Preferencias usan `PreferenciasInstitucionService`.
- El botón "Sincronizar con año activo" llama
  `InstitucionService.sincronizar_con_anio()` (de mejora_06).
