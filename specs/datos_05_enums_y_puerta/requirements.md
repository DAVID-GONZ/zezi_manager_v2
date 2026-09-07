# Requisitos: Alineación de enumeraciones y su verificación (datos_05_enums_y_puerta)

> Ámbito: los conjuntos cerrados de valores admisibles del sistema, tal como los declara
> el dominio y tal como los restringe el almacenamiento, y el mecanismo que impide que
> ambas declaraciones diverjan.

---

## Conjuntos cerrados en el dominio

R1: EL SISTEMA DEBE representar como enumeración todo campo cuyo conjunto de valores
    admisibles está cerrado y restringido por el almacenamiento.

R2: CUANDO un modelo recibe para uno de esos campos un valor ajeno al conjunto admisible,
    EL SISTEMA DEBE rechazarlo e identificar el campo y el valor recibido.

R3: EL SISTEMA NO DEBE depender exclusivamente del almacenamiento para rechazar un valor
    ajeno al conjunto admisible.

R4: EL SISTEMA DEBE conservar el valor por omisión de cada uno de esos campos, y ese valor
    por omisión DEBE pertenecer al conjunto admisible.

---

## Correspondencia entre dominio y almacenamiento

R5: EL SISTEMA DEBE mantener, para cada campo de conjunto cerrado, un conjunto de valores
    admisibles idéntico en el dominio y en el almacenamiento.

R6: EL SISTEMA DEBE poder determinar de forma automática, para cada restricción de
    conjunto del almacenamiento, qué enumeración del dominio le corresponde.

R7: EL SISTEMA DEBE registrar de forma explícita y justificada toda enumeración que
    legítimamente carece de restricción en el almacenamiento, y toda restricción que
    legítimamente carece de enumeración.

R8: EL SISTEMA NO DEBE tratar la ausencia de correspondencia como situación normal ni
    resolverla en silencio.

---

## Verificación permanente

R9: EL SISTEMA DEBE verificar la correspondencia entre enumeraciones y restricciones de
    conjunto como parte de su comprobación de calidad habitual.

R10: CUANDO la comprobación detecta una divergencia, EL SISTEMA DEBE identificar el campo
     afectado, los valores que sobran y los que faltan en cada lado.

R11: CUANDO la comprobación detecta una divergencia, EL SISTEMA DEBE terminar señalando
     el fallo, de modo que la divergencia impida dar por buena la comprobación.

R12: EL SISTEMA DEBE completar esta comprobación sin alargar de forma apreciable la
     comprobación de calidad habitual.

R13: EL SISTEMA DEBE emitir el resultado de la comprobación de forma legible con
     independencia de la codificación de caracteres de la consola.

R14: CUANDO se añade una enumeración nueva o una restricción de conjunto nueva sin su
     contraparte, EL SISTEMA DEBE señalarlo sin necesidad de modificar la comprobación.

---

## Preservación del comportamiento

R15: EL SISTEMA NO DEBE alterar el valor almacenado de ninguno de esos campos como
     consecuencia de representarlos mediante enumeraciones.

R16: EL SISTEMA DEBE seguir aceptando, al construir un modelo desde el almacenamiento,
     los valores que hoy contiene para esos campos.
