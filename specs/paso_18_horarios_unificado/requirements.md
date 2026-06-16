# Requisitos: Página única de horarios y dedup (paso_18_horarios_unificado)

> Contexto: la gestión de horarios está repartida entre `/horarios` (ver/editar) y
> `/academico/generar-horario` (generar), con lógica duplicada (`_opciones_eje` en
> 3 sitios), código muerto (`_cargar_bloques`) y registro doble de rutas `@ui.page`
> (en el archivo de página y en `main.py`, este último el único con guard de auth).
> Este paso unifica todo en una sola página con toggles semánticos y elimina la
> duplicidad, sin tocar el render de la parrilla.

## Deduplicación

R1: EL SISTEMA DEBE tener **una sola** implementación de `_opciones_eje`, exportada
    desde `parrilla_widget.py` y reutilizada por el resto; las copias locales en
    `horarios.py` y `horario_generar.py` DEBEN eliminarse.

R2: EL SISTEMA DEBE eliminar el código muerto `_cargar_bloques` de `horarios.py`.

R3: CADA ruta de horarios DEBE registrarse **una sola vez** con su guard de
    autenticación; NO DEBE existir un `@ui.page` en el archivo de página y otro en
    `main.py` para la misma ruta. El guard de autenticación DEBE conservarse.

## Página única con toggles semánticos

R4: EL SISTEMA DEBE ofrecer una **única página de horarios** con un control de
    navegación semántico de secciones: **Preparar**, **Generar**, **Visualizar**,
    **Editar**.

R5: La sección **Preparar** DEBE concentrar la configuración previa (disponibilidad,
    límites docente, salas, plantilla, estado de validación) — integra el panel de
    paso_19 y la captura de paso_17.

R6: La sección **Generar** DEBE contener la configuración de generación y la ejecución
    del motor con su resultado (lo que hoy es `/academico/generar-horario`).

R7: La sección **Visualizar** DEBE mostrar la parrilla (Por entidad / Tablero maestro)
    en modo lectura, reutilizando `render_parrilla` / `render_tablero_maestro`.

R8: La sección **Editar** DEBE permitir la edición manual de bloques (lo que hoy hace
    `/horarios` con `puede_escribir`).

R9: El control de secciones DEBE respetar permisos por rol: quien no puede escribir ve
    Visualizar pero no Editar/Generar/Preparar de escritura.

## Compatibilidad

R10: Las rutas antiguas (`/horarios`, `/academico/generar-horario`) DEBEN seguir
     funcionando (redirección a la sección correspondiente de la página única) para no
     romper enlaces existentes (p. ej. "Ver en horarios" con `?escenario=`).

R11: EL SISTEMA NO DEBE modificar `parrilla_widget.py` salvo para exportar
     `_opciones_eje` (R1); el render visual de la parrilla se conserva.

R12: `python init.py` DEBE quedar verde sin regresiones de tests.
