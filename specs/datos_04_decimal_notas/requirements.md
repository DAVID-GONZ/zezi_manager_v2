# Requisitos: Notas en aritmética decimal exacta (datos_04_decimal_notas)

> Ámbito: la representación numérica de toda calificación, umbral de aprobación,
> límite de escala, rango de desempeño y peso de ponderación del sistema académico.

---

## Representación y cuantización

R1: EL SISTEMA DEBE representar las calificaciones, los umbrales de aprobación, los
    límites de la escala, los extremos de los rangos de desempeño y los pesos de
    ponderación como valores decimales de precisión exacta.

R2: EL SISTEMA DEBE cuantizar a exactamente dos decimales toda calificación, todo
    umbral de aprobación, todo límite de escala y todo extremo de rango de desempeño.

R3: EL SISTEMA DEBE cuantizar a exactamente cuatro decimales todo peso de ponderación
    expresado como fracción de la unidad.

R4: EL SISTEMA DEBE resolver todo redondeo con el criterio de mitad hacia arriba, de
    modo que un valor exactamente equidistante entre dos representaciones admisibles
    se resuelva siempre hacia la mayor.

R5: CUANDO el sistema recibe una calificación o un peso con más decimales de los
    admitidos, EL SISTEMA DEBE cuantizarlo según R2 o R3 y aceptarlo, en lugar de
    rechazar el valor.

R6: EL SISTEMA DEBE producir el mismo valor cuantizado para una misma calificación con
    independencia de si se recibió como texto, como entero o como número de coma
    flotante.

R7: EL SISTEMA DEBE mantener una definición única del criterio de cuantización y de
    redondeo, compartida por todos los modelos que representan calificaciones y pesos.

---

## Cálculo

R8: EL SISTEMA DEBE calcular el promedio ponderado de un periodo acumulando los
    productos peso × promedio en precisión decimal, y cuantizar una sola vez el
    resultado final.

R9: EL SISTEMA NO DEBE cuantizar los resultados intermedios de un cálculo ponderado.

R10: MIENTRAS los pesos de las categorías de un periodo suman exactamente la unidad y
     todas las calificaciones del estudiante son iguales al umbral de aprobación,
     EL SISTEMA DEBE producir una nota definitiva exactamente igual a ese umbral.

R11: EL SISTEMA DEBE decidir la aprobación comparando la nota definitiva cuantizada
     contra el umbral cuantizado, sin márgenes de tolerancia ni correcciones de error
     de coma flotante.

R12: EL SISTEMA NO DEBE usar márgenes de tolerancia arbitrarios para verificar que una
     suma de pesos alcanza la unidad; la comparación DEBE ser exacta sobre los valores
     cuantizados.

R13: EL SISTEMA DEBE calcular la nota definitiva anual, la nota de habilitación, la
     nota de nivelación y la nota de plan de mejoramiento con la misma aritmética
     decimal y la misma regla de cuantización que la nota de periodo.

R14: EL SISTEMA DEBE clasificar una calificación en su nivel de desempeño comparando
     el valor cuantizado contra los extremos cuantizados del rango, de modo que una
     calificación situada exactamente en un extremo se clasifique de forma determinista.

R15: EL SISTEMA DEBE producir una nota definitiva comprendida entre la menor y la mayor
     de las calificaciones que la componen, para cualquier combinación válida de pesos
     que sumen la unidad.

R16: CUANDO una calificación que compone un promedio ponderado aumenta y las demás no
     varían, EL SISTEMA NO DEBE producir una nota definitiva menor que la anterior.

---

## Persistencia

R17: EL SISTEMA NO DEBE fallar al enviar una calificación o un peso decimal al
     almacenamiento.

R18: EL SISTEMA DEBE almacenar las calificaciones y los pesos de forma que el valor
     recuperado sea idéntico al valor cuantizado que se guardó.

R19: CUANDO el sistema recupera una calificación almacenada, EL SISTEMA DEBE
     reconstruirla como valor decimal cuantizado y NO DEBE propagar el ruido de la
     representación binaria del almacenamiento.

R20: EL SISTEMA DEBE producir el mismo valor tras cualquier número de ciclos sucesivos
     de guardado y recuperación de una misma calificación.

---

## Presentación, informes y exportación

R21: EL SISTEMA DEBE entregar las calificaciones a los boletines y a las hojas de
     cálculo como valores numéricos, nunca como texto.

R22: EL SISTEMA DEBE serializar las calificaciones hacia la interfaz sin provocar
     errores de serialización y conservando el valor cuantizado que se mostrará.

R23: EL SISTEMA NO DEBE reconvertir una calificación a coma flotante binaria en ningún
     punto en el que ese valor vuelva a compararse contra un umbral o vuelva a
     acumularse en una suma ponderada.

R24: MIENTRAS un conjunto de calificaciones se manipula como tabla de datos para
     construir un informe, EL SISTEMA DEBE conservar en el resultado final el valor
     cuantizado de cada calificación.

---

## Límites del ámbito

R25: EL SISTEMA NO DEBE representar como decimal exacto los estadísticos agregados de
     solo lectura, los porcentajes de progreso ni los pesos heurísticos del generador
     de horarios, porque ninguno de ellos determina la aprobación de un estudiante.

R26: EL SISTEMA DEBE señalar de forma inmediata y explícita cualquier intento de
     combinar aritméticamente una calificación decimal con un valor de coma flotante,
     en lugar de degradar el resultado en silencio.
