# Requisitos: Suite de integración verde y vigilada (harness_01_integracion_en_puerta)

> Ámbito: las pruebas que ejercitan los repositorios contra una base real, y el alcance
> de la comprobación de calidad que decide si el proyecto está en verde.

---

## Correspondencia con las interfaces vigentes

R1: EL SISTEMA DEBE invocar cada método de repositorio con los argumentos que ese método
    exige.

R2: EL SISTEMA DEBE acotar a una institución toda consulta de repositorio que lo requiera,
    también cuando la consulta se realiza para verificar el comportamiento.

R3: EL SISTEMA NO DEBE conservar invocaciones a repositorios que ninguna interfaz vigente
    admita.

---

## Cobertura de la hidratación

R4: EL SISTEMA DEBE verificar que cada entidad se construye correctamente a partir de una
    fila real recuperada del almacenamiento.

R5: EL SISTEMA DEBE verificar la construcción de entidades para todos los repositorios,
    y no solo para aquellos cuya prueba ya existe.

R6: CUANDO una entidad no puede construirse a partir de una fila que el almacenamiento
    contiene, EL SISTEMA DEBE señalarlo como fallo.

---

## Alcance de la comprobación de calidad

R7: EL SISTEMA DEBE incluir las pruebas que ejercitan los repositorios en la comprobación
    de calidad que decide si el proyecto está en verde.

R8: EL SISTEMA NO DEBE declarar verde el proyecto mientras exista una prueba de
    repositorio en fallo.

R9: EL SISTEMA DEBE conservar un modo de ejecución veloz, sin pruebas de repositorio, para
    la verificación frecuente durante el desarrollo.

R10: EL SISTEMA DEBE distinguir en su salida el resultado de cada familia de pruebas, de
     modo que un fallo se atribuya a la familia correcta.

R11: EL SISTEMA DEBE completar la comprobación de calidad en un tiempo que no
     desincentive su ejecución habitual.

---

## Prevención

R12: CUANDO una interfaz de repositorio cambia y una prueba deja de corresponderse con
     ella, EL SISTEMA DEBE señalarlo en la comprobación de calidad siguiente.

R13: EL SISTEMA NO DEBE permitir que una familia completa de pruebas quede excluida de la
     comprobación de calidad sin que ello sea visible.

---

## Preservación del comportamiento

R14: EL SISTEMA NO DEBE alterar el comportamiento verificado por las pruebas al
     actualizarlas.

R15: EL SISTEMA NO DEBE debilitar una comprobación existente para conseguir que una prueba
     pase.
