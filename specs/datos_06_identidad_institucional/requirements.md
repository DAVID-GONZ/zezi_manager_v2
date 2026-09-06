# Requisitos: Fuente única de identidad institucional (datos_06_identidad_institucional)

> Operación: modificar.
> Alcance declarado: `src/domain/models/{configuracion,institucion}.py`,
> `src/domain/ports/{configuracion,institucion}_repo.py`,
> `src/infrastructure/db/repositories/sqlite_{configuracion,institucion}_repo.py`,
> `src/services/{configuracion,institucion,informe}_service.py`,
> `tests/unit/services/test_identidad_institucional.py`.

## Contexto

La identidad institucional —nombre oficial, código DANE, rector, dirección,
municipio, teléfono, logo y resolución de aprobación— se guarda en dos registros
distintos: el de la institución y el del año lectivo. Ninguno manda sobre el otro
y no existe ningún mecanismo que los mantenga alineados, de modo que el mismo dato
de negocio puede tener dos valores simultáneos y contradictorios.

Estos requisitos definen un único registro dueño del dato y describen el
comportamiento observable resultante.

---

## Requisitos

R1: EL SISTEMA DEBE tratar el registro de la institución como el único lugar donde
    se almacena la identidad institucional: nombre oficial, código DANE, rector,
    dirección, municipio, teléfono, ruta del logo, dirección del logo y resolución
    de aprobación.

R2: EL SISTEMA NO DEBE escribir ningún dato de identidad institucional al persistir
    la configuración de un año lectivo.

R3: EL SISTEMA NO DEBE leer ningún dato de identidad institucional desde el
    almacenamiento de la configuración del año lectivo.

R4: CUANDO el sistema entrega la configuración de un año lectivo, EL SISTEMA DEBE
    completar sus datos de identidad institucional con los valores registrados en
    la institución dueña de ese año.

R5: MIENTRAS un año lectivo no esté asociado a ninguna institución, EL SISTEMA DEBE
    entregar su configuración con los valores por defecto de identidad y sin fallar.

R6: EL SISTEMA DEBE presentar el nombre "Institución Educativa" y dejar vacíos los
    campos opcionales de identidad en informes y encabezados cuando la institución
    dueña no tiene registrado ese dato.

R7: CUANDO el usuario actualiza la información institucional asociada a un año
    lectivo, EL SISTEMA DEBE registrar el cambio en la institución dueña de ese año.

R8: CUANDO el usuario actualiza la información institucional de un año lectivo que
    no está asociado a ninguna institución, EL SISTEMA DEBE rechazar la operación
    con un mensaje descriptivo.

R9: EL SISTEMA DEBE aplicar la validación de doce dígitos numéricos del código DANE
    a cualquier actualización de identidad institucional, sea cual sea el punto de
    entrada desde el que se solicite.

R10: CUANDO se registra una institución nueva, EL SISTEMA DEBE persistir todos los
     datos de identidad suministrados en el alta, incluido el nombre oficial.

R11: CUANDO cambia la identidad registrada de una institución, EL SISTEMA DEBE
     reflejar el cambio en la información institucional de todos los años lectivos
     de esa institución sin requerir ninguna acción adicional del usuario.

R12: EL SISTEMA NO DEBE ofrecer ninguna operación cuyo efecto sea duplicar la
     identidad institucional dentro del registro del año lectivo.

R13: EL SISTEMA DEBE exponer la dirección del logo institucional con respaldo
     persistente, de forma que el valor entregado a la interfaz sea exactamente el
     registrado en la institución.

R14: EL SISTEMA DEBE construir la información institucional que consumen boletines
     e informes a partir de la institución dueña del año lectivo.

R15: CUANDO falta el código DANE o el rector de la institución, EL SISTEMA DEBE
     rechazar la construcción de la información institucional de boletines con un
     mensaje que indique qué dato completar.

R16: EL SISTEMA DEBE ofrecer un único punto de acceso a la información institucional
     para la generación de informes.
