# Requisitos: Configuración común de los modelos de dominio (datos_02_model_config_base)

> Ámbito: la configuración de validación y serialización de los 180 modelos Pydantic
> de `src/domain/models/`, y la base común de la que todos derivan.

---

## Base común

R1: EL SISTEMA DEBE definir una única clase base de la que derive todo modelo de dominio,
    y esa base DEBE ser el único lugar donde se declara la configuración compartida.

R2: EL SISTEMA DEBE aplicar la configuración compartida a todo modelo de dominio sin
    que ningún módulo la repita.

R3: CUANDO se define un modelo de dominio nuevo que no deriva de la base común,
    EL SISTEMA DEBE señalarlo como defecto de forma automática y reproducible.

R4: EL SISTEMA DEBE distinguir dos categorías de modelo con configuración propia: las
    que representan una entidad persistida y las que transportan datos entre capas.

---

## Hidratación desde el almacenamiento

R5: EL SISTEMA DEBE poder construir cualquier modelo de dominio a partir de un objeto
    que exponga los valores como atributos, y no solo a partir de un diccionario.

R6: EL SISTEMA DEBE producir el mismo modelo, con los mismos valores validados, tanto si
    se construye desde atributos como desde claves.

---

## Campos no reconocidos

R7: CUANDO un modelo destinado a recibir datos externos recibe un campo que no declara,
    EL SISTEMA DEBE rechazar la construcción e identificar el campo no reconocido.

R8: EL SISTEMA NO DEBE descartar en silencio un campo no reconocido en un modelo
    destinado a recibir datos externos.

R9: MIENTRAS un modelo de entidad se construye a partir de una fila del almacenamiento
    que contiene columnas que el modelo no representa, EL SISTEMA DEBE construir la
    entidad sin fallar.

R10: EL SISTEMA DEBE declarar de forma explícita y justificada cada modelo que admite
     campos no reconocidos, en lugar de admitirlos por omisión.

---

## Normalización de texto

R11: EL SISTEMA DEBE eliminar los espacios inicial y final de todo valor de texto que
     recibe un modelo de dominio.

R12: EL SISTEMA DEBE conservar la normalización de texto que hoy realiza cada modelo,
     sin que ningún campo pierda una validación de contenido, longitud o formato al
     retirarse la eliminación de espacios de su validador propio.

R13: EL SISTEMA NO DEBE mantener validadores cuya única función sea eliminar espacios.

---

## Invariantes tras la construcción

R14: CUANDO se asigna un valor a un campo de un modelo de dominio ya construido,
     EL SISTEMA DEBE validar ese valor con las mismas reglas que se aplican al
     construirlo.

R15: CUANDO una asignación posterior a la construcción viola una invariante del modelo,
     EL SISTEMA DEBE rechazarla e identificar el campo y la regla incumplida.

---

## Enumeraciones

R16: EL SISTEMA DEBE conservar los valores de enumeración como miembros de su
     enumeración dentro de los modelos, de modo que sigan comparándose por identidad de
     miembro y no por su representación textual.

---

## Preservación del comportamiento

R17: EL SISTEMA NO DEBE alterar el resultado de ninguna operación de negocio existente
     como consecuencia de la configuración común.

R18: EL SISTEMA DEBE mantener la serialización de cada modelo con los mismos nombres de
     campo y los mismos valores que produce antes de adoptar la configuración común,
     salvo donde un requisito de este documento imponga lo contrario.

R19: CUANDO la adopción de la configuración común revela que un punto del sistema
     construye un modelo con campos que ese modelo no declara, EL SISTEMA DEBE tratarlo
     como un defecto a corregir en el punto de construcción, y no como una excepción a
     la configuración.
