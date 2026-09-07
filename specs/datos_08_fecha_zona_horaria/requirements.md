# Requisitos: Una sola zona horaria para la fecha del sistema (datos_08_fecha_zona_horaria)

> Ámbito: el momento en que el sistema sella una fila con la fecha u hora actual, y el
> momento contra el que compara al validar que una fecha no es futura.

---

## Origen único del instante actual

R1: EL SISTEMA DEBE obtener el instante actual de un único origen, con independencia de
    si el valor lo produce el almacenamiento o el código de dominio.

R2: EL SISTEMA DEBE resolver toda fecha por omisión de una fila y toda comparación con la
    fecha actual en la misma zona horaria.

R3: EL SISTEMA DEBE tratar la zona horaria de referencia como parámetro de configuración
    de la institución, y no como una constante incrustada en el código.

R4: EL SISTEMA NO DEBE derivar la fecha de una fila de la zona horaria en la que se
    encuentre el proceso que atiende la operación.

---

## Sellado de filas

R5: CUANDO el sistema registra una fila sin que se indique su fecha, EL SISTEMA DEBE
    sellarla con la fecha vigente en la zona horaria de referencia en ese momento.

R6: EL SISTEMA NO DEBE sellar una fila con una fecha posterior a la vigente en la zona
    horaria de referencia.

R7: MIENTRAS la hora local está comprendida entre el final de la tarde y la medianoche,
    EL SISTEMA DEBE seguir sellando las filas con la fecha del día en curso.

---

## Validación de fechas futuras

R8: EL SISTEMA DEBE rechazar toda fecha de registro posterior al día vigente en la zona
    horaria de referencia.

R9: EL SISTEMA NO DEBE rechazar una fecha de registro que el propio sistema acaba de
    asignar por omisión.

R10: EL SISTEMA DEBE aplicar el mismo criterio de fecha vigente en todos los validadores
     que comprueban que una fecha no es futura.

---

## Recuperación de filas existentes

R11: CUANDO el sistema recupera una fila cuya fecha quedó sellada por delante del día
     vigente, EL SISTEMA DEBE entregar la fila en lugar de fallar.

R12: EL SISTEMA DEBE permitir localizar las filas cuya fecha quedó sellada por delante
     del día vigente.

---

## Verificación

R13: EL SISTEMA DEBE permitir fijar el instante actual y la zona horaria de referencia al
     verificar su comportamiento, de modo que el resultado sea reproducible.

R14: EL SISTEMA DEBE comportarse de forma idéntica al sellar y al validar una fila con
     independencia de la hora del día en que se ejecute la comprobación.

R15: EL SISTEMA DEBE señalar como defecto la aparición de un nuevo origen de fecha actual
     que no provenga del origen único.
