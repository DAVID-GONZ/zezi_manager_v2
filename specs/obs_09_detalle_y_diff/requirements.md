# Requisitos: Detalle del cambio, diff y filtros legibles (obs_09)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgos
> B1, B2, B8 y B10.
> **Depende de:** `obs_06` (la fila ya trae username e IP) y `obs_08` (conteos
> para la paginación).
> **Alcance:** un servicio de diff reutilizable, un catálogo de etiquetas de
> tabla, el presenter y la página de auditoría. No cambia el esquema.

## Los cuatro defectos que este paso cierra

### D1 — El diff se escribe y no se lee nunca

Cada fila de `audit_log` guarda `valor_anterior` y `valor_nuevo` como JSON. La
tabla de la UI muestra `timestamp · acción · tabla · registro · usuario` y
ningún camino de la interfaz abre esos dos campos. Una fila dice que alguien
actualizó `observaciones #123`; no dice qué cambió.

El backend para resolverlo ya existe y no tiene consumidores:

| Método | Puerto | Implementación | Consumidores |
|---|---|---|---|
| `get_cambio(cambio_id)` | `auditoria_repo.py:134` | `sqlite_auditoria_repo.py:332` | **0** |
| `listar_cambios_por_registro(tabla, registro_id)` | `auditoria_repo.py:121` | `sqlite_auditoria_repo.py:316` | **0** |

Es el mismo patrón que `obs_05` encontró con `resumen_uso`: capacidad
construida, probada y sin puerta de entrada.

### D2 — La columna de actor muestra un entero

El encabezado dice literalmente «Usuario ID» y la celda contiene `7`. Con
`obs_06` la fila ya trae el username, pero las filas anteriores y el nombre
completo siguen sin resolverse.

### D3 — Filtrar exige conocer el esquema físico

El filtro de tabla es un `filter_input` de texto libre que el repositorio aplica
con igualdad exacta (`AND tabla = ?`). Para ver los cambios de convivencia hay
que saber que la tabla se llama `observaciones`. No hay filtro por
`registro_id`.

### D4 — El filtro de institución esconde filas

`institucion_id IS NULL` en 116 de 508 eventos. El SQL es `AND institucion_id =
?`, así que al elegir cualquier institución esas filas desaparecen sin aviso y
no hay forma de pedirlas.

---

R1: EL SISTEMA DEBE calcular el diff de un `RegistroCambio` en la **capa de
    servicios**, no en el presenter ni en la página, para que la API REST y el
    futuro fork Vue lo reutilicen.

R2: EL DIFF DEBE producir una lista ordenada de campos con `nombre`,
    `valor_anterior`, `valor_nuevo` y `tipo_cambio` (`añadido`, `modificado`,
    `eliminado`, `sin_cambio`), omitiendo por defecto los campos sin cambio.

R3: EL DIFF NO DEBE exponer campos sensibles. Los nombres de campo que
    coincidan con la lista negra (`password`, `password_hash`,
    `password_temporal`, `token`, `secreto`) se muestran como `«oculto»` sin
    su valor, en ambos lados.

R4: EL SISTEMA DEBE ofrecer un catálogo `tabla física → etiqueta de negocio`
    como fuente única, consultable desde la UI y desde la futura API.

R5: CUANDO una tabla no esté en el catálogo, la UI DEBE mostrar su nombre
    físico en lugar de fallar u ocultar la fila.

R6: LA PÁGINA `/admin/auditoria` DEBE abrir un diálogo de detalle al activar
    una fila de la pestaña Cambios, con: identidad del actor, fecha, acción,
    entidad afectada, IP, institución y el diff campo a campo.

R7: EL DIÁLOGO DE DETALLE DEBE ser solo lectura y no ofrecer ninguna acción de
    escritura, deshacer o reversión.

R8: LA COLUMNA DE ACTOR DEBE mostrar el nombre de la persona. El sistema
    resuelve los identificadores de la página visible en **una sola consulta**,
    no una por fila.

R9: CUANDO no se pueda resolver un identificador de usuario (cuenta eliminada),
    la UI DEBE mostrar el username almacenado en la fila y, si tampoco existe,
    `Usuario #<id>`.

R10: EL FILTRO DE TABLA DEBE ser un desplegable de etiquetas de negocio
     alimentado por el catálogo de R4, no un campo de texto libre.

R11: LA PÁGINA DEBE ofrecer un filtro por `registro_id` que acote la bitácora a
     una entidad concreta.

R12: EL FILTRO DE INSTITUCIÓN DEBE ofrecer la opción «Sin institución», que
     selecciona las filas con `institucion_id IS NULL`.

R13: EL PRESENTER NO DEBE contener reglas de negocio: se limita a mantener el
     estado de filtros y a exponer el view-model. El diff, las etiquetas y la
     resolución de nombres viven en servicios o en dominio.

## Criterio de done

- Activar una fila de Cambios abre un diálogo que muestra qué campos cambiaron,
  con su valor antes y después.
- Un cambio sobre un usuario que incluya `password_hash` muestra ese campo como
  `«oculto»` en ambos lados.
- El filtro de tabla es un desplegable con nombres como «Observaciones de
  convivencia», no `observaciones`.
- Elegir «Sin institución» muestra las filas que el filtro por tenant escondía.
- La columna de actor muestra nombres de persona.
- `python scripts/init.py` completamente verde.
