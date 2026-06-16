# Requisitos: Plantilla integrada y robusta en el generador (paso_16c_generador_plantilla_unificada)

> Contexto: hoy la plantilla horaria (rejilla de franjas) se administra en una
> página separada (`/admin/plantillas-franja`), restringida a admin/director,
> mientras que la generación vive en `/academico/generar-horario` y sólo puede
> seleccionar una plantilla preexistente. Un coordinador con permiso de generar
> no puede crear ni ajustar la plantilla que necesita. Este paso integra la
> gestión de plantillas en el flujo de generación y la hace más robusta.

R1: EL SISTEMA DEBE permitir crear, ver y eliminar plantillas horarias desde la
    propia página de generación de horarios.

R2: CUANDO el usuario crea una plantilla, EL SISTEMA DEBE permitir definir su
    nombre, jornada, días activos y el conjunto de franjas con su tipo (lectiva,
    descanso, almuerzo), orden y horas de inicio y fin.

R3: CUANDO el usuario crea una configuración de generación, EL SISTEMA DEBE
    permitirle seleccionar una plantilla existente o crear una nueva sin salir de
    la página.

R4: EL SISTEMA DEBE mostrar una vista previa de la rejilla de la plantilla
    seleccionada (franjas por días activos) antes de ejecutar la generación.

R5: MIENTRAS una plantilla no tenga al menos una franja lectiva en al menos un día
    activo, EL SISTEMA NO DEBE permitir generar un horario con ella, y DEBE
    explicar el motivo.

R6: MIENTRAS el usuario tenga rol con permiso de generación, EL SISTEMA DEBE
    permitirle gestionar las plantillas necesarias para generar, sin exigir un
    rol administrativo adicional.

R7: CUANDO el usuario intenta eliminar una plantilla referenciada por alguna
    configuración de generación, EL SISTEMA DEBE impedir la eliminación y advertir
    qué configuraciones la usan.

R8: CUANDO el usuario guarda una plantilla con franjas solapadas o con hora de fin
    anterior o igual a la de inicio, EL SISTEMA DEBE rechazar el guardado y
    explicar el error.

R9: EL SISTEMA DEBE conservar el acceso administrativo existente a la gestión de
    plantillas para los roles que ya lo tenían.
