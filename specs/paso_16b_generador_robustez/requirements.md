# Requisitos: Robustez de contexto e integración del generador (paso_16b_generador_robustez)

> Contexto: la página de generación exige que el año y el periodo estén fijados
> manualmente en la sesión; si no lo están, redirige en silencio y el usuario
> percibe que "no abre". Además, un escenario recién generado no tiene puente
> hacia la vista de horarios para revisarlo o editarlo. Este paso hace el acceso
> robusto y cierra el ciclo generar → ver/editar.

R1: MIENTRAS exista un año lectivo activo en el sistema, EL SISTEMA DEBE permitir
    el acceso a la generación de horarios derivando el año y el periodo activos,
    aunque no estén fijados manualmente en la sesión.

R2: CUANDO no existe ningún año lectivo activo, EL SISTEMA DEBE mostrar un mensaje
    claro indicando que debe activarse un año lectivo, en lugar de redirigir sin
    explicación.

R3: CUANDO no existe ningún periodo en el año activo, EL SISTEMA DEBE mostrar un
    mensaje claro indicando que debe crearse o activarse un periodo, en lugar de
    redirigir sin explicación.

R4: CUANDO no existe ninguna plantilla horaria, EL SISTEMA DEBE indicar al usuario
    dónde crear una antes de poder configurar una generación.

R5: CUANDO una generación finaliza con una solución válida, EL SISTEMA DEBE
    ofrecer al usuario abrir el escenario generado en la vista de horarios.

R6: CUANDO el usuario elige abrir el escenario generado, EL SISTEMA DEBE mostrar
    la vista de horarios con ese escenario ya seleccionado.

R7: MIENTRAS el usuario tenga rol con permiso de generación, EL SISTEMA DEBE
    permitirle el acceso aunque no haya seleccionado grupo en la sesión.
