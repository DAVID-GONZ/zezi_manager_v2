# Requisitos: Huella completa y atribuible (obs_01_huella_actor)

> **Contexto:** `docs/auditoria_observabilidad_2026-09-08.md` §2.1 y §2.2.
> **Habilita:** `seguridad_web_09_logging_alertas` (los eventos que S09 debe registrar
> hoy no se emiten) y `obs_02_puerta_huella`.

R1: EL SISTEMA DEBE registrar en la bitácora de cambios toda creación, modificación y
    eliminación de datos que realicen los servicios que ya la utilizan, incluidas las
    habilitaciones.

R2: EL SISTEMA DEBE atribuir cada registro de la bitácora al usuario autenticado que
    originó la operación, sin requerir que la pantalla que la desencadena lo indique.

R3: EL SISTEMA DEBE asociar cada registro de la bitácora a la institución en cuyo
    contexto se produjo la operación.

R4: MIENTRAS un administrador opera suplantando a otro usuario, EL SISTEMA DEBE
    atribuir cualquier registro al administrador real y conservar la identidad
    suplantada como dato complementario.

R5: CUANDO un usuario cierra sesión, EL SISTEMA DEBE registrar el evento de cierre de
    sesión con la identidad que tenía activa en ese momento.

R6: CUANDO el sistema deniega el acceso a una ruta, a los datos de otra institución o a
    una escritura en modo de solo lectura, EL SISTEMA DEBE registrar un evento de acceso
    denegado con la identidad y el recurso involucrados.

R7: EL SISTEMA DEBE registrar la dirección de red de origen en los eventos de sesión.

R8: CUANDO la escritura de un registro de auditoría falla, EL SISTEMA NO DEBE
    interrumpir la operación de negocio en curso, y DEBE dejar constancia del fallo.

R9: EL SISTEMA DEBE preservar la verificabilidad de la cadena de integridad sobre los
    registros escritos con anterioridad a este cambio.

## Criterio de done

- Crear o anular una habilitación produce filas en la bitácora de cambios (hoy produce cero).
- `SELECT COUNT(*) FROM audit_log WHERE usuario_id IS NULL OR institucion_id IS NULL`
  deja de crecer con los cambios nuevos.
- Un cierre de sesión y un acceso denegado aparecen en `/admin/auditoria`.
- Los eventos de sesión muestran dirección de red en lugar de guion.
- El botón "Verificar integridad" sigue reportando la cadena íntegra.
