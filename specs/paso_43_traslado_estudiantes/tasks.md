# paso_43 — Traslado de estudiantes entre grupos (con historial e regla de grado)

## Contexto y decisiones (David)

Implementar el **traslado de un estudiante entre grupos**, con su movimiento registrado en el historial.

Estado actual:
- Tabla `historial_estudiantes` (estudiante_id, grupo_origen_id, grupo_destino_id, fecha_movimiento, `tipo_movimiento` TRASLADO/RETIRO/REINGRESO/GRADUACION, `motivo`, `usuario_registro_id`). **Existe**, sin modelo/repo/servicio.
- Trigger `tg_historial_cambio_grupo`: AFTER UPDATE OF grupo_id, inserta un historial **TRASLADO sin motivo ni usuario**.
- `estudiante_service.asignar_grupo` cambia `grupo_id` (dispara el trigger).
- **Las notas y demás registros cuelgan de `estudiante_id`** (`UNIQUE(estudiante_id, actividad_id)`, planes, nivelación, asistencia, convivencia, alertas). → **El "historial propio asociado al id único" ya es automático: al trasladar NO se copia ni mueve nada; el estudiante conserva su `id` y todos sus registros lo siguen.** Esto es decisión confirmada: "solo historial" (las notas del grupo anterior quedan como historial; en el grupo nuevo empieza con sus actividades).

Decisiones:
- **Notas:** solo historial (sin copiar). Automático por el diseño de FKs.
- **Regla de grado:** mismo grado = traslado normal sin fricción; **grado distinto = permitido solo con confirmación explícita + motivo** (promoción/repitencia/corrección). Sin confirmación, se bloquea (evita 1101→602 accidental). El grado sale de `grupos.grado`.
- **Rol:** solo `director`/`coordinador` trasladan (vía `actor_rol`, como paso_42).

## Tareas

### T1 — Modelo + repo del historial [x]
- Modelo `MovimientoEstudiante` (o `HistorialEstudiante`) en `src/domain/models/estudiante.py` + enum `TipoMovimiento` (TRASLADO/RETIRO/REINGRESO/GRADUACION) + DTO de lectura (`MovimientoEstudianteInfoDTO` con códigos de grupo origen/destino legibles). Re-export desde `estudiante_service`.
- `sqlite_estudiante_repo` + port: `registrar_movimiento(estudiante_id, grupo_origen_id, grupo_destino_id, tipo, motivo, usuario_registro_id)` y `listar_historial(estudiante_id) -> list[...]` (con join a grupos para los códigos). Mantener scope por institución coherente.

### T2 — Coordinar el trigger (evitar doble registro) [x]
- El trigger `tg_historial_cambio_grupo` registra un TRASLADO sin motivo/usuario en CADA cambio de grupo. Para que el traslado capture motivo/usuario/tipo y NO se dupliquen filas: **eliminar el trigger** y que el **servicio** escriba el historial explícitamente (única fuente de verdad). Como no hay migraciones (paso_34), basta quitarlo de `TRIGGERS` en `schema.py`. Verificar que NINGÚN otro camino cambie `grupo_id` sin registrar historial (matrícula = INSERT, no dispara el trigger AFTER UPDATE; CSV/asignar_grupo: enrutar por el servicio o registrar). Documentar el barrido.

### T3 — Servicio `trasladar` [x]
- `estudiante_service.trasladar(estudiante_id, grupo_destino_id, motivo, usuario_id, actor_rol=None, permitir_cambio_grado=False) -> Estudiante` (`@requiere_escritura`):
  1. RBAC: `_verificar_gestion(actor_rol)` (director/coordinador).
  2. Leer estudiante (verificar_pertenencia institución — paso_36) y su grupo origen; leer grupo destino (`infraestructura` get_grupo). Validar que destino existe y es de la misma institución.
  3. **Regla de grado:** si `grupo_destino.grado != grupo_origen.grado` y NO `permitir_cambio_grado` → `ValueError` accionable ("El grupo destino es de otro grado; confirma el cambio de grado y registra un motivo."). Si es cambio de grado permitido, exigir `motivo` no vacío.
  4. Cambiar `grupo_id` (repo) y `registrar_movimiento(... tipo=TRASLADO, motivo, usuario_registro_id=usuario_id)`. (tipo=TRASLADO + motivo; no es necesario ampliar el enum, salvo que el implementer lo vea más limpio.)
  5. Devolver el estudiante actualizado. (NO copiar notas — siguen por `estudiante_id`.)
- `listar_historial(estudiante_id)` expuesto en el servicio (scopeado).

### T4 — UI en estudiantes.py [x]
- Acción por fila **"Trasladar"** (icono p.ej. `swap_horiz`/`move_up`), visible solo si `puede_gestionar` (director/coordinador) y el estudiante no está retirado.
- Diálogo: select de **grupo destino** (grupos de la institución; mostrar `codigo — grado`), campo **motivo**. Si el grupo elegido es de **otro grado**, mostrar un aviso + **checkbox "Confirmar cambio de grado (promoción/repitencia/corrección)"** y exigir motivo; sin el check, el submit se bloquea con mensaje claro. Llamar `trasladar(..., actor_rol=ctx.usuario_rol, permitir_cambio_grado=<check>)`, toast, refrescar.
- **Vista de Historial** del estudiante: acción por fila "Historial" (visible a todos los que ven la página) que abre un diálogo con `listar_historial(estudiante_id)` (movimientos: fecha, origen→destino, tipo, motivo). Empty state si no hay.

### T5 — Verificación y tests [x]
- `python init.py` VERDE (baseline 1205 passed, 1 skipped; corregir fallout — fakes del repo deben implementar registrar_movimiento/listar_historial; tests que dependían del trigger se ajustan a la escritura por servicio). check_design `--file` estudiantes.py + check_imports en verde.
- Tests: traslado mismo grado OK (historial con motivo/usuario); traslado a otro grado SIN `permitir_cambio_grado` → ValueError; CON confirmación + motivo → OK; profesor (actor_rol) → rechazado; **tras el traslado, las notas/registros del estudiante siguen accesibles por su `estudiante_id`** (prueba de que el historial sigue al estudiante); aislamiento por institución (no trasladar a grupo de otra institución).
- `progress/impl_paso_43.md` (incluye el barrido de caminos que cambian grupo_id).

## criterio_done
Existe `trasladar` (RBAC + regla de grado: mismo grado libre, distinto grado solo con confirmación+motivo) que cambia el grupo y registra el movimiento en `historial_estudiantes` con motivo/usuario/tipo (sin duplicar con el trigger, que se elimina); UI con acción "Trasladar" (confirmación de cambio de grado) y vista de "Historial"; las notas/registros siguen al estudiante por su id (sin copia); `python init.py` verde.
