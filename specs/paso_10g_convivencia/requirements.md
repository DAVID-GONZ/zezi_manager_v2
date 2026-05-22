# Requirements — paso_10g_convivencia
## Módulo: Convivencia (observaciones, comportamiento, notas)
**Notación:** EARS (Event-Action-Response System)

---

## Módulo observaciones.py (`/convivencia/observaciones`)

**R1** WHILE el usuario no está autenticado, WHEN carga `/convivencia/observaciones`, THE SYSTEM SHALL redirigir a `/login` sin renderizar contenido.

**R2** WHEN la página carga con un usuario autenticado, THE SYSTEM SHALL obtener el `grupo_id` y `periodo_id` del `SessionContext` y preseleccionarlos en los selectores de filtro.

**R3** WHEN el usuario selecciona un estudiante del grupo activo y un periodo, THE SYSTEM SHALL llamar a `ConvivenciaService.listar_observaciones(estudiante_id, periodo_id, solo_publicas)` y mostrar las observaciones en una tabla `ui.aggrid`.

**R4** IF el rol del usuario es `admin` o `director`, THE SYSTEM SHALL mostrar tanto observaciones públicas como privadas. IF el rol es `profesor`, THE SYSTEM SHALL mostrar solo las observaciones públicas de otros docentes y todas las propias.

**R5** WHEN el usuario hace clic en "Nueva observación", THE SYSTEM SHALL abrir un `form_dialog` con campos: estudiante (select), periodo (select), texto (textarea, max 2000 chars), es_publica (checkbox). Al confirmar, llamar a `ConvivenciaService.registrar_observacion(dto, usuario_id)`.

**R6** WHEN la creación de observación es exitosa, THE SYSTEM SHALL llamar a `refresh()` del `@ui.refreshable` y mostrar `ui.notify` de éxito. IF falla, THE SYSTEM SHALL mostrar `ui.notify` de error con el mensaje exacto de la excepción.

**R7** WHEN el usuario hace clic en "Hacer pública" en una fila privada, THE SYSTEM SHALL actualizar `es_publica=True` vía servicio y refrescar la tabla. WHEN hace clic en "Hacer privada" en una fila pública, THE SYSTEM SHALL actualizar `es_publica=False`.

**R8** WHEN el usuario hace clic en "Eliminar" en una fila, THE SYSTEM SHALL mostrar un `confirm_dialog` con mensaje de advertencia. Solo si el usuario confirma, llamar a `ConvivenciaService.eliminar_observacion(observacion_id)` y refrescar.

**R9** IF el periodo asociado a la observación está cerrado (verificado vía `PeriodoService`), THE SYSTEM SHALL deshabilitar los botones de edición y eliminación para esa fila.

---

## Módulo comportamiento.py (`/convivencia/comportamiento`)

**R10** WHILE el usuario no está autenticado, WHEN carga `/convivencia/comportamiento`, THE SYSTEM SHALL redirigir a `/login`.

**R11** WHEN la página carga, THE SYSTEM SHALL construir un `FiltroConvivenciaDTO` con `grupo_id` del contexto y llamar a `ConvivenciaService.listar_registros(filtro)` para poblar la tabla.

**R12** WHEN el usuario ajusta los filtros (grupo, periodo, tipo de registro, solo negativos), THE SYSTEM SHALL actualizar el `FiltroConvivenciaDTO` y reejecutar `listar_registros` sin recargar la página completa.

**R13** WHEN el usuario hace clic en "Nuevo registro", THE SYSTEM SHALL abrir un `form_dialog` con campos: estudiante (select del grupo), tipo (select con opciones de `_TIPOS_DISPLAY`), descripción (textarea, max 1000 chars), requiere_firma (checkbox), fecha (text tipo date, valor por defecto hoy). Al confirmar, llamar a `ConvivenciaService.registrar_comportamiento(dto, usuario_id, anio_id)`.

**R14** WHEN `registrar_comportamiento` retorna exitoso, THE SYSTEM SHALL refrescar la tabla. El servicio llama internamente a `detectar_alertas()` para registros negativos — la página no lo invoca directamente.

**R15** IF un registro tiene `requiere_firma=True` y `acudiente_notificado=False`, THE SYSTEM SHALL mostrar un botón "Notificar acudiente" en la fila. WHEN se hace clic, llamar a `ConvivenciaService.notificar_acudiente(registro_id)` y refrescar.

**R16** WHEN el usuario hace clic en "Agregar seguimiento" en una fila, THE SYSTEM SHALL abrir un `form_dialog` de una sola campo textarea. Al confirmar, llamar a `ConvivenciaService.agregar_seguimiento(registro_id, texto)` y refrescar.

**R17** WHEN el usuario hace clic en "Eliminar" en una fila, THE SYSTEM SHALL mostrar `confirm_dialog`. Solo si confirma, llamar a `ConvivenciaService.eliminar_registro(registro_id)` y refrescar.

**R18** THE SYSTEM SHALL mostrar un badge visual por tipo de registro en la columna Tipo de la tabla aggrid, usando clases CSS definidas en `styles.css` (no `style=` inline): FORTALEZA→`badge-fortaleza`, DIFICULTAD→`badge-dificultad`, COMPROMISO→`badge-compromiso`, CITACION_ACUDIENTE→`badge-citacion`, DESCARGO→`badge-descargo`.

**R19** IF el periodo está cerrado, THE SYSTEM SHALL deshabilitar el botón "Nuevo registro" y las acciones de eliminación.

---

## Módulo notas_convivencia.py (`/convivencia/notas`)

**R20** WHILE el usuario no está autenticado, WHEN carga `/convivencia/notas`, THE SYSTEM SHALL redirigir a `/login`.

**R21** WHEN la página carga, THE SYSTEM SHALL obtener `grupo_id` y `periodo_id` del contexto y llamar a `ConvivenciaService.listar_notas_grupo(grupo_id, periodo_id)` para poblar la grilla.

**R22** WHEN el usuario selecciona un grupo y periodo distintos, THE SYSTEM SHALL recargar la grilla con las notas correspondientes.

**R23** THE SYSTEM SHALL mostrar una `ui.aggrid` con columnas: Estudiante, Nota (editable, 0-100), Observación (editable, texto libre), Desempeño (calculado si existe `desempeno_id`, de lo contrario vacío). La columna Nota tendrá `editable: true` en la definición de columna aggrid.

**R24** WHEN el usuario edita la nota de un estudiante y hace clic en "Guardar fila", THE SYSTEM SHALL construir un `NuevaNotaComportamientoDTO` y llamar a `ConvivenciaService.registrar_nota_comportamiento(dto, usuario_id)`. Si ya existía nota, el servicio la actualiza.

**R25** WHEN el usuario hace clic en "Guardar todo", THE SYSTEM SHALL iterar todas las filas con cambios pendientes y llamar al servicio por cada estudiante. Al finalizar, mostrar resumen de éxitos y errores via `ui.notify`.

**R26** IF el periodo está cerrado, THE SYSTEM SHALL establecer `editable: false` en todas las columnas de la aggrid y ocultar los botones de guardado.

**R27** IF `ConvivenciaService.get_nota_comportamiento(estudiante_id, periodo_id)` retorna `None` para un estudiante, THE SYSTEM SHALL mostrar la celda Nota vacía, permitiendo registrar por primera vez.
