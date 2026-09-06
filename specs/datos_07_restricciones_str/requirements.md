# Requisitos: Restricciones de longitud y formato en campos de texto (datos_07_restricciones_str)

> Notación EARS. El sujeto de todo requisito es EL SISTEMA.
> Alcance: `src/domain/models/base.py` (tipos de texto restringidos compartidos),
> `usuario.py`, `institucion.py`, `estudiante.py`, `acudiente.py`, `convivencia.py`,
> `configuracion.py`, `infraestructura.py`, y `tests/unit/domain/test_restricciones_str.py`.

---

## Cota declarada de los campos de texto

R1: EL SISTEMA DEBE declarar, para todo campo de texto de una entidad de dominio o de un
    objeto de entrada dentro del alcance, una longitud máxima admisible expresada como
    restricción del propio tipo del campo, de forma que la cota sea legible por
    introspección del modelo sin ejecutar el objeto.

R2: CUANDO EL SISTEMA recibe un valor de texto cuya longitud supera la cota declarada del
    campo, DEBE rechazar la construcción del objeto completo y NO DEBE persistir,
    truncar ni normalizar silenciosamente el valor excedido.

R3: EL SISTEMA DEBE aplicar la cota después de la normalización de espacios en blanco, de
    modo que un valor cuyo exceso de longitud consista únicamente en espacios circundantes
    sea aceptado.

R4: EL SISTEMA DEBE agrupar las cotas en un conjunto cerrado de categorías semánticas
    declaradas en un único lugar, y NO DEBE escribir un número de longitud literal en la
    declaración de un campo individual salvo que ese campo constituya una excepción
    documentada frente a su categoría.

R5: EL SISTEMA DEBE exponer cada categoría de longitud como un tipo de texto reutilizable
    con nombre propio, de manera que el valor de la cota se pueda cambiar en un solo punto
    y quede aplicado a todos los campos de esa categoría.

## Coherencia con las reglas de longitud ya vigentes

R6: MIENTRAS un campo ya disponga de una regla de longitud máxima verificada durante la
    validación, EL SISTEMA DEBE declarar para ese campo exactamente el mismo valor de cota,
    y NO DEBE declarar una cota superior ni inferior a la que esa regla ya exige.

R7: EL SISTEMA NO DEBE alterar el mensaje de error dirigido a la persona usuaria en los
    campos que ya rechazaban un valor por exceso de longitud.

R8: EL SISTEMA DEBE mantener un único origen para el valor de la cota de un campo, de forma
    que no puedan coexistir dos cifras distintas para el mismo campo.

## Preservación de los datos válidos existentes

R9: EL SISTEMA NO DEBE rechazar ningún valor de texto que hoy esté almacenado y sea
    considerado válido por las reglas de negocio vigentes.

R10: EL SISTEMA DEBE verificar, antes de dar el trabajo por terminado, que el valor de texto
     más largo presente en el conjunto de datos de prueba de cada campo cabe dentro de la
     cota declarada para ese campo.

R11: EL SISTEMA DEBE reservar en cada categoría un margen sobre la longitud real observada,
     de forma que la cota nunca quede a menos del doble del valor más largo conocido para
     esa categoría, salvo en los campos cuya longitud es fija por definición externa.

## Campos sin restricción

R12: EL SISTEMA NO DEBE declarar cota de longitud sobre un campo cuyo valor se calcula
     internamente por composición de otros campos ya acotados, porque la suma de las cotas
     de origen puede exceder legítimamente la cota de la categoría del resultado.

R13: EL SISTEMA NO DEBE declarar cota de longitud sobre los campos de los objetos de
     proyección que el dominio produce para lectura y que nunca reciben datos de un cliente.

R14: EL SISTEMA NO DEBE declarar cota de longitud sobre un campo de texto cuyo conjunto de
     valores admisibles esté destinado a quedar cerrado por una enumeración, ni sobre un
     campo de texto destinado a representar una hora o un instante de tiempo.

R15: EL SISTEMA DEBE dejar constancia explícita, para cada campo del alcance que quede sin
     cota, de la razón por la que no la lleva.

## Identificadores de contacto

R16: EL SISTEMA DEBE acotar la longitud de todo campo de correo electrónico al máximo que
     admite una dirección de correo enrutable, sin reducir por debajo de ese máximo.

R17: EL SISTEMA DEBE seguir exigiendo a todo campo de correo electrónico la presencia de
     parte local no vacía, separador y dominio con punto interior, y DEBE conservar la
     normalización a minúsculas y el tratamiento de la cadena vacía como ausencia de valor.

R18: EL SISTEMA NO DEBE incorporar una dependencia externa nueva de ejecución para validar
     el formato de correo electrónico MIENTRAS el manifiesto del proyecto no declare las
     dependencias de ejecución que la aplicación ya necesita para arrancar.

R19: EL SISTEMA DEBE acotar la longitud de todo campo de teléfono o celular a una cifra
     compatible con la numeración internacional más los separadores que la persona usuaria
     pueda escribir.

## Secretos y rutas

R20: EL SISTEMA DEBE acotar la longitud de todo campo que transporte una contraseña al mismo
     máximo que exige la política de contraseñas vigente, y NO DEBE declarar para ellos una
     cota mayor.

R21: EL SISTEMA DEBE acotar por separado los campos que designan una ruta de archivo local y
     los que designan una dirección de recurso remoto, con cotas propias de cada uno.

## Verificación

R22: EL SISTEMA DEBE ofrecer una comprobación automática que recorra por introspección todos
     los modelos del alcance y falle si aparece un campo de texto sin cota declarada que no
     figure en la lista documentada de exclusiones.

R23: EL SISTEMA DEBE ofrecer una comprobación automática que falle si la cota declarada de un
     campo difiere del valor que exige su regla de longitud ya vigente.

R24: CUANDO se añada un campo de texto nuevo a un modelo del alcance, EL SISTEMA DEBE hacer
     fallar la comprobación automática mientras ese campo no reciba cota ni quede registrado
     como exclusión justificada.
