# Requisitos: Correlación por request_id (obs_14)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgo
> C6. **Nivel N3 — diferido.**
> **Depende de:** `obs_06` (el contexto de actor ya transporta datos de
> petición) y, para su activación, de la Fase de API REST de
> `roadmaps/backend_00_roadmap_sqlalchemy_api`.
> **Alcance:** un contexto de petición, su propagación a los tres destinos de
> escritura y el enganche en la UI de observabilidad.

## Por qué está diferido

Un identificador de petición cobra su valor cuando hay peticiones con dueño
claro y un consumidor que las correlacione: una API REST con clientes
distintos, o un colector de logs. Hoy la aplicación es NiceGUI con sesión de
navegador, el manejador global de excepciones ya registra la traza completa y
el volumen de errores es manejable a mano. Implementarlo antes de `backend_00`
sería pagar la complejidad sin cobrar el beneficio.

Se especifica ahora, y no cuando toque, para que las decisiones de `obs_06`
—dónde vive el contexto de petición, qué campos viajan— se tomen sabiendo qué
va a colgar de ellas después.

## El defecto que este paso cierra

Cuando algo falla hoy, hay tres rastros que no se pueden unir:

| Rastro | Dónde | Qué identifica |
|---|---|---|
| Excepción con traza | log de aplicación | el punto del código |
| Evento de sesión | tabla `auditoria` | el actor y el momento |
| Cambio de datos | tabla `audit_log` | la entidad afectada |

No hay ninguna clave común. Reconstruir «este error ocurrió mientras este
usuario guardaba esta observación» se hace hoy correlacionando marcas de
tiempo a ojo.

---

R1: EL SISTEMA DEBE generar un identificador único por petición y ponerlo a
    disposición de todas las capas mediante un `ContextVar`, sin pasarlo por
    parámetro.

R2: EL IDENTIFICADOR DEBE generarse en un único punto de entrada y NO DEBE
    poder crearse a mitad de una petición: si al escribir no hay identificador
    activo, el campo va nulo y no se inventa uno nuevo.

R3: EL IDENTIFICADOR DEBE ser opaco y no derivarse de datos de sesión, de la
    IP ni de nada que identifique a una persona.

R4: EL SISTEMA DEBE escribir el identificador en los tres destinos: el log
    estructurado, la tabla `auditoria` y la tabla `audit_log`.

R5: `_CAMPOS_PERMITIDOS` del logger DEBE incorporar el campo, conservando el
    diseño de whitelist cerrada.

R6: EL MANEJADOR GLOBAL DE EXCEPCIONES DEBE incluir el identificador en la
    respuesta de error, para que un usuario pueda comunicarlo al soporte sin
    exponer ningún detalle interno.

R7: CUANDO la aplicación exponga la API REST, el identificador DEBE aceptarse
    desde una cabecera entrante si viene bien formada, y generarse si no, de
    modo que un cliente pueda correlacionar de extremo a extremo.

R8: LA PÁGINA `/admin/observabilidad` DEBE permitir buscar por identificador y
    mostrar, en una sola vista, las entradas de log, los eventos de sesión y
    los cambios que lo comparten.

R9: EL IDENTIFICADOR NO DEBE participar en el hash de la cadena de auditoría:
    es metadato de correlación, no contenido del hecho auditado, y el criterio
    debe quedar escrito junto al de `institucion_id`, que ya está fuera.

R10: EL SISTEMA DEBE incluir un test que verifique que dos peticiones
     concurrentes no comparten identificador y que ninguna ve el de la otra.

## Criterio de done

- Provocar un error controlado devuelve al usuario un identificador, y
  buscarlo en el panel de observabilidad reúne la traza, el evento de sesión y
  los cambios de esa misma petición.
- Dos peticiones simultáneas producen identificadores distintos y aislados.
- La verificación de integridad de la bitácora sigue en verde tras añadir la
  columna.
- `python scripts/init.py` completamente verde.
