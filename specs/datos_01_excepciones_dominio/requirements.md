# Requisitos: Jerarquía de excepciones de dominio (datos_01_excepciones_dominio)

> Notación EARS. El sujeto de todo requisito es EL SISTEMA.
> Alcance: `src/domain/exceptions.py`, los 23 servicios de `src/services/` que
> señalan condiciones de error, los dos mecanismos neutrales de la capa de
> servicios (`solo_lectura.py`, `contexto_tenant.py`) y su test de dominio.

---

## Identidad del error

R1: EL SISTEMA DEBE exponer una jerarquía única de excepciones de dominio con una
    raíz común, de forma que cualquier consumidor pueda capturar con un solo tipo
    toda condición de error originada en las reglas del negocio.

R2: EL SISTEMA DEBE asignar a cada condición de error un código estable, escrito en
    mayúsculas ASCII sin espacios ni acentos, independiente del idioma y de la
    redacción del mensaje dirigido a la persona usuaria.

R3: EL SISTEMA DEBE tomar los códigos de error de un vocabulario cerrado y declarado
    en un único lugar, y NO DEBE aceptar la construcción de una excepción de dominio
    con un código que no pertenezca a ese vocabulario.

R4: EL SISTEMA DEBE garantizar que dos condiciones de error distintas no comparten
    código.

R5: EL SISTEMA NO DEBE usar el texto del mensaje como identificador de la condición
    de error; MIENTRAS el código permanezca igual, una corrección de redacción,
    ortografía o traducción del mensaje NO DEBE alterar el comportamiento de ningún
    consumidor.

R6: CUANDO un consumidor recibe una excepción de dominio, EL SISTEMA DEBE ofrecerle,
    por separado y sin necesidad de analizar texto: el código estable, el mensaje
    legible y un conjunto de detalles estructurados serializables.

R7: EL SISTEMA DEBE incluir en los detalles estructurados los valores que originan la
    violación —identificador solicitado, tipo de recurso, valor recibido, límite
    aplicable— y NO DEBE incluir en ellos contraseñas, hashes de contraseña ni
    ningún otro secreto de autenticación.

---

## Familias de error

R8: EL SISTEMA DEBE clasificar toda condición de error del negocio en exactamente una
    de estas familias: regla de negocio incumplida, recurso no encontrado, conflicto
    con el estado actual, permiso denegado, o dependencia obligatoria no disponible.

R9: CUANDO una operación referencia un recurso inexistente, EL SISTEMA DEBE señalar
    la familia «recurso no encontrado» indicando el tipo de recurso y el
    identificador solicitado.

R10: CUANDO una operación colisiona con un dato ya registrado o con el estado actual
     de una entidad —documento duplicado, período ya cerrado, sala ya ocupada,
     asignación ya existente—, EL SISTEMA DEBE señalar la familia «conflicto».

R11: CUANDO los datos recibidos son sintácticamente aceptables pero incumplen una
     regla del negocio —nota fuera de la escala, suma de pesos superior al 100 %,
     rango de horas inválido, carga docente excedida—, EL SISTEMA DEBE señalar la
     familia «regla de negocio incumplida».

R12: CUANDO la persona que ejecuta la operación no está autorizada a ejecutarla,
     EL SISTEMA DEBE señalar la familia «permiso denegado» y NO DEBE revelar en el
     mensaje datos del recurso protegido.

R13: CUANDO un servicio no dispone de una dependencia obligatoria para completar la
     operación solicitada, EL SISTEMA DEBE señalar la familia «dependencia no
     disponible», distinguible de cualquier error causado por los datos que envía la
     persona usuaria.

---

## Comportamientos de permiso ya vigentes

R14: MIENTRAS la sesión está en modo solo lectura, CUANDO se intenta cualquier
     operación de mutación, EL SISTEMA DEBE rechazarla como permiso denegado con un
     código estable propio y exclusivo de esa causa.

R15: CUANDO se intenta operar por identificador sobre un objeto que no pertenece a la
     institución activa de la sesión, EL SISTEMA DEBE rechazar la operación como
     permiso denegado con un código estable propio y exclusivo de esa causa.

R16: EL SISTEMA DEBE mantener que los rechazos por solo lectura y por institución
     ajena sigan siendo capturables como errores de permiso del lenguaje, para que el
     código que hoy los maneja continúe funcionando sin modificarse.

---

## Compatibilidad y consistencia

R17: EL SISTEMA DEBE mantener el comportamiento observable de los consumidores que
     hoy manejan los errores de validación de los servicios como errores de valor,
     sin exigir que esos consumidores se modifiquen en este alcance.

R18: EL SISTEMA NO DEBE señalar desde la capa de servicios ninguna condición de error
     de negocio mediante un tipo de error genérico del lenguaje carente de código
     estable.

R19: EL SISTEMA DEBE permitir traducir la familia de cada excepción a una categoría
     de respuesta transportable mediante una correspondencia declarada fuera del
     dominio, y el dominio NO DEBE depender de ningún protocolo de transporte,
     códigos numéricos de estado ni biblioteca web.

R20: EL SISTEMA DEBE conservar el efecto de cada rechazo actual: toda operación que
     hoy se rechaza DEBE seguir rechazándose, y ninguna operación hoy aceptada DEBE
     pasar a rechazarse por efecto de esta jerarquía.
