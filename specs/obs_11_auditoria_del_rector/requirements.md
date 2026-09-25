# Requisitos: Bitácora institucional para el equipo directivo (obs_11)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgo
> A1, el hueco de producto de la épica.
> **Depende de:** `obs_09` (detalle y diff) y `obs_10` (política
> `rbac_auditoria`).
> **Alcance:** una ruta nueva, su presenter, el scope obligatorio en el
> servicio y la navegación. No cambia el esquema ni la página de admin.

## El defecto que este paso cierra

`/admin/auditoria` está registrada con `roles=_ADMIN` (`main.py:227`) y es la
única vista de auditoría del sistema. El resultado es que **nadie dentro del
colegio puede auditar su propia institución**: ni el rector, que es el
responsable del tratamiento de los datos personales de los estudiantes y el
custodio del libro de convivencia, ni el coordinador, que es quien atiende las
quejas del día a día. La pregunta «¿quién borró esta observación?» solo la
puede contestar hoy el proveedor del software.

Para un producto cuya entrada comercial es convivencia y asistencia, esa
dependencia no es un detalle técnico: es el proveedor convertido en árbitro de
los conflictos disciplinarios de sus clientes.

## Lo que esta vista NO es

No es `/admin/auditoria` con otro guard de rol. El admin es auditor técnico de
plataforma y su pantalla incluye la verificación de la cadena de hashes, el
filtro por institución y el vocabulario del esquema. El rector audita personas
y hechos dentro de su colegio. Compartir la página obligaría a llenarla de
condicionales por rol, que es exactamente el modo de fallo que
`registrar_pagina` y el registro único de rutas eliminaron en `paso_35`.

---

R1: EL SISTEMA DEBE registrar la ruta `/institucion/auditoria` con
    `roles={Rol.DIRECTOR, Rol.COORDINADOR}` mediante `registrar_pagina`.

R2: EL SISTEMA DEBE ampliar `rbac_auditoria.py` con
    `puede_ver_bitacora_institucional(actor_rol)`, cierta para `director` y
    `coordinador`. El admin tiene su propia vista y no se añade aquí.

R3: `AuditoriaService.listar_cambios` y `listar_eventos_sesion` DEBEN recibir
    un `TenantScope` **obligatorio y posicional**, sin valor por defecto, de
    modo que omitirlo sea un `TypeError` en tiempo de llamada.

R4: LA PÁGINA institucional DEBE construir su scope desde la sesión
    (`ctx.institucion_id`) y NUNCA desde un filtro que el usuario pueda
    modificar. El scope no es un criterio de búsqueda, es un límite.

R5: LA PÁGINA institucional NO DEBE ofrecer el filtro por institución, ni el
    botón de verificación de integridad, ni ninguna referencia a la cadena de
    hashes.

R6: LA PÁGINA institucional DEBE ofrecer las dos pestañas —cambios y
    sesiones—, los filtros de fecha, usuario, entidad y acción, el detalle con
    diff de `obs_09` y la paginación con total de `obs_08`.

R7: LA PÁGINA institucional DEBE usar el vocabulario de negocio: etiquetas de
    entidad del catálogo `tablas_auditables`, nombres de persona y textos en
    español, sin nombres de tabla ni identificadores internos como encabezado.

R8: LA PÁGINA DEBE ser de solo lectura. No expone exportación (llega en
    `obs_12`), ni acciones de escritura de ningún tipo.

R9: LA NAVEGACIÓN (`layout.py`) DEBE mostrar la entrada «Auditoría» dentro de
    la sección de Dirección para los roles con acceso, derivando la
    visibilidad del registro central de rutas y no de una lista paralela.

R10: EL SISTEMA DEBE actualizar `ACCESO_ESPERADO` en
     `tests/unit/interface/auth/test_matriz_rutas_completa.py` con la ruta
     nueva y sus roles.

R11: EL SISTEMA DEBE incluir en la suite de aislamiento de `tenant_04` un test
     que verifique que un director de la institución 1 no obtiene ninguna fila
     de la institución 2 por esta vía, ni siquiera manipulando el filtro.

R12: CUANDO la sesión no tenga `institucion_id`, la página NO DEBE mostrar
     datos: muestra un estado vacío explicativo. Sin tenant no hay scope, y sin
     scope no se sirve la bitácora.

## Criterio de done

- Un director entra en `/institucion/auditoria` y ve los cambios y las sesiones
  de su institución, con el detalle y el diff.
- Un profesor que navega a esa URL recibe el aviso de acceso no autorizado y
  vuelve a `/inicio`.
- Un director de la institución 1 no ve ninguna fila de la institución 2,
  tampoco las que tengan `institucion_id` de otro tenant.
- La página no muestra filtro de institución ni verificación de integridad.
- La entrada aparece en el NAV solo para director y coordinador.
- `python scripts/init.py` completamente verde, con la matriz de rutas
  actualizada.
