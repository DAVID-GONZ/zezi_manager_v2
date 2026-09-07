# Requisitos: Valores derivados en la serialización (datos_03_computed_fields)

> Ámbito: los 123 valores derivados que 46 modelos de `src/domain/models/` exponen hoy
> como propiedades de Python, y su presencia o ausencia en la representación serializada
> de cada modelo.

---

## Regla de negocio en la serialización

R1: EL SISTEMA DEBE incluir en la representación serializada de un modelo todo valor
    derivado que constituya una regla de negocio.

R2: EL SISTEMA DEBE calcular cada valor derivado de negocio en un único lugar, de modo
    que ningún consumidor de la representación serializada necesite reimplementarlo.

R3: EL SISTEMA DEBE producir para cada valor derivado de negocio el mismo resultado al
    consultarlo como atributo y al leerlo de la representación serializada.

R4: EL SISTEMA DEBE declarar el tipo de cada valor derivado que aparece en la
    representación serializada.

---

## Separación de la presentación

R5: EL SISTEMA NO DEBE incluir en la representación serializada los valores derivados
    cuyo único cometido es dar formato a un dato para su lectura por una persona.

R6: EL SISTEMA DEBE mantener accesibles como atributo los valores derivados de formato,
    de modo que la capa de interfaz siga disponiendo de ellos.

R7: EL SISTEMA DEBE distinguir de forma explícita, para cada valor derivado, si expresa
    una regla de negocio o un formato de presentación.

---

## Acceso

R8: EL SISTEMA DEBE permitir consultar todo valor derivado sin invocarlo como función.

R9: EL SISTEMA NO DEBE exigir argumentos para obtener un valor derivado.

---

## Coste de la serialización

R10: EL SISTEMA NO DEBE consultar el almacenamiento ni ningún servicio externo para
     calcular un valor derivado incluido en la representación serializada.

R11: MIENTRAS se serializa un conjunto de modelos, EL SISTEMA DEBE calcular cada valor
     derivado a partir únicamente de los campos del propio modelo.

---

## Valores dependientes de la fecha actual

R12: EL SISTEMA DEBE calcular los valores derivados que dependen del transcurso del
     tiempo en el momento en que se sirve la representación, y no en el momento en que
     se construyó el modelo.

R13: EL SISTEMA DEBE identificar de forma explícita cada valor derivado cuyo resultado
     depende de la fecha actual.

R14: CUANDO se verifica el comportamiento de un valor derivado dependiente de la fecha
     actual, EL SISTEMA DEBE permitir fijar esa fecha, de modo que el resultado sea
     reproducible.

---

## Preservación del comportamiento

R15: EL SISTEMA NO DEBE alterar el resultado de ninguna operación de negocio existente
     como consecuencia de exponer valores derivados en la serialización.

R16: EL SISTEMA NO DEBE romper ningún consumidor que hoy acceda a un valor derivado como
     atributo del modelo.

R17: CUANDO un valor derivado se incorpora a la representación serializada, EL SISTEMA
     NO DEBE admitirlo como dato de entrada al construir el modelo.
