# Requisitos: Reparar la ejecución del generador de horarios (paso_16a_fix_generador_timer)

> Contexto: la página de generación muestra el botón «Generar horario», pero al
> pulsarlo el motor nunca se ejecuta y el indicador de carga queda colgado de
> forma permanente. El servicio de generación es correcto; el fallo está en la
> capa de interfaz, que programa el trabajo en un temporizador que ya no está
> vivo cuando el usuario hace clic.

R1: CUANDO el usuario pulsa «Generar horario» con una configuración seleccionada,
    EL SISTEMA DEBE ejecutar el motor de generación sobre esa configuración.

R2: MIENTRAS el motor está en ejecución, EL SISTEMA DEBE mostrar un indicador de
    carga y mantener deshabilitada la acción de generar.

R3: CUANDO el motor termina con una solución válida, EL SISTEMA DEBE ocultar el
    indicador de carga y mostrar las métricas de calidad, las incidencias y la
    vista previa del escenario generado.

R4: CUANDO el motor termina con una solución parcial o inválida, EL SISTEMA DEBE
    ocultar el indicador de carga, mostrar el resultado disponible y advertir al
    usuario de que la generación no fue completa.

R5: CUANDO ocurre un error inesperado durante la generación, EL SISTEMA DEBE
    ocultar el indicador de carga y notificar el error sin dejar la interfaz
    bloqueada.

R6: CUANDO el usuario pulsa «Generar horario» de forma repetida, EL SISTEMA DEBE
    ejecutar cada generación de forma independiente, sin que una corrida previa
    impida las siguientes.
