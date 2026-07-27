# convivencia_04 — RBAC de Comportamiento restringido al director de grupo

> Inicio de la Fase 2 (`convivencia_00_roadmap`). Consume el helper de `convivencia_03`.

## Contexto y decisión (David)

**Comportamiento** (registros) y **Notas de comportamiento** deben poder gestionarse **solo por: director de grupo (de ESE grupo) + director + coordinador**. Hoy `/convivencia/comportamiento` y `/convivencia/notas` están en `_AULA` (cualquier profesor). Como el director de grupo ES un profesor, la restricción no puede hacerse solo por rol en la ruta: es **autorización por objeto** a nivel de página.

**Observaciones NO se toca aquí** (sigue abierto a profesor con asignación; su endurecimiento es Fase 4 / convivencia_11).

**admin:** auditor técnico — NO gestiona en nombre propio; solo por impersonación ("ver como"), momento en que su rol efectivo es director/coordinador/profesor y las reglas de abajo aplican con ese rol. No añadir `admin` a ninguna lista de gestión. (Ver `rbac_convivencia`.)

Estado actual:
- Rutas `/convivencia/comportamiento` y `/convivencia/notas` = `_AULA` (main.py). El grupo activo llega por el chip de contexto (`ctx.grupo_id`), no por un selector en la página.
- Ya existe `CatalogoAcademicoService.puede_gestionar_comportamiento_en_grupo(usuario_rol, usuario_id, grupo_id)` (directivo director/coordinador siempre; profesor solo si dirige el grupo; admin False) — testeado en convivencia_03.

## Tareas

### T1 — Gating en la página de Comportamiento
- En `comportamiento.py`: tras resolver el grupo activo (`ctx.grupo_id`), calcular `autorizado = Container.catalogo_academico_service().puede_gestionar_comportamiento_en_grupo(ctx.usuario_rol, ctx.usuario_id, ctx.grupo_id)`.
- Si NO autorizado: no mostrar acciones de mutación (botón "Nuevo registro", "Notificar acudiente", "Seguimiento", "Eliminar") y mostrar un `empty_state`/aviso claro ("Solo el director de grupo, la coordinación o la dirección pueden gestionar el comportamiento de este grupo."). El listado puede permanecer oculto o en modo consulta según sea coherente con el resto de páginas — decisión del implementer, documentarla.
- Si SÍ autorizado: comportamiento actual intacto.
- Sin `grupo_id` en contexto: mensaje de "selecciona un grupo" (comportamiento existente).
- La página NO importa dominio; llama al servicio y pasa primitivos (`ctx.usuario_rol`, `ctx.usuario_id`, `ctx.grupo_id`).

### T2 — Gating en la página de Notas de comportamiento
- En `notas_convivencia.py`: mismo patrón. Si NO autorizado → grilla en solo lectura (o vacía con aviso) y ocultar "Guardar seleccionado"/"Guardar todo". Reutilizar el aviso de T1.

### T3 — Defensa en profundidad en el servicio (si el diseño lo permite sin romper capas)
- Evaluar añadir enforcement en `ConvivenciaService` para las mutaciones (`registrar_comportamiento`, `registrar_nota_comportamiento`, `agregar_seguimiento`, `eliminar_registro`, `notificar_acudiente`): que verifiquen la autorización por objeto además del gating de página.
- Si requiere el rol del actor (hoy los métodos reciben `usuario_id` pero no `rol`), el implementer decide la vía más limpia y coherente con el proyecto (p.ej. proveedor lazy a `CatalogoAcademicoService` + pasar `usuario_rol` desde la página, o diferir a un `convivencia_04b` documentándolo). **NO** cablear rol en `contexto_tenant`. Si añadir enforcement de servicio implica cambios de firma que se salen de un paso pequeño, documenta la decisión de diferirlo y deja el gating de página como control efectivo de este paso (coherente con la autorización central de rutas, paso_35).

### T4 — Verificación
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/check_imports.py --layer interface` (+ `--layer services` si se tocó servicio) en verde.
- `check_design.py --file` para cada página tocada, en verde.
- `pytest tests/unit/ -q` verde (añadir test de servicio si se implementó T3).
- `init.py` VERDE.
- `progress/impl_convivencia_04.md`.

## criterio_done
En `/convivencia/comportamiento` y `/convivencia/notas`, un profesor que NO dirige el grupo activo no puede crear/editar/eliminar (acciones ocultas + aviso); el director de grupo de ese grupo, el coordinador y el director sí; admin nunca en nombre propio. Observaciones sin cambios. check_design/check_imports verdes; `init.py` verde. (Si el enforcement de servicio se difiere, queda documentado como convivencia_04b.)
