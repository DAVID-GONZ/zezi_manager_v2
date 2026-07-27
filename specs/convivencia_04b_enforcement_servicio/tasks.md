# convivencia_04b — Defensa en profundidad: enforcement en ConvivenciaService

> Parche de la Fase 2, complementa `convivencia_04` (gating de página).
> Diferido documentado en `progress/impl_convivencia_04.md`.

## Contexto y decisión (David)

El gating de `convivencia_04` está en la vista (comportamiento.py / notas_convivencia.py). Si alguien invoca `ConvivenciaService` desde otro sitio (script, futuro endpoint, subagente), las mutaciones no verifican autorización. Regla del proyecto (paso_35): **defensa en profundidad** — servicio y vista consultan la misma política.

**admin nunca gestiona en nombre propio** (`rbac_convivencia` ya lo maneja: `False`). No añadir admin a ninguna lista.

Estado actual:
- Política pura `rbac_convivencia.puede_gestionar_comportamiento(usuario_rol, es_director_de_grupo)` ✅
- `CatalogoAcademicoService.puede_gestionar_comportamiento_en_grupo(usuario_rol, usuario_id, grupo_id)` ✅
- Mutaciones de `ConvivenciaService`: `registrar_comportamiento`, `agregar_seguimiento`, `notificar_acudiente`, `eliminar_registro`, `registrar_nota_comportamiento`. Reciben `usuario_id` pero NO `usuario_rol`.

## Tareas

### T1 — Inyectar CatalogoAcademicoService a ConvivenciaService
- Añadir en `ConvivenciaService.__init__` un parámetro nuevo `catalogo_academico_svc_provider: Callable[[], CatalogoAcademicoService] | None = None` (lazy provider, mismo patrón que ya usa `CatalogoAcademicoService` para asignaciones). `None` = enforcement desactivado (compat retro: seed/scripts/tests existentes siguen funcionando).
- Cablearlo en `container.py`: `Container.convivencia_service()` pasa una lambda que devuelva `Container.catalogo_academico_service()`. Verifica el patrón exacto que ya usan otros servicios inyectados en `container.py`.

### T2 — Enforcement en las mutaciones
- Añadir un helper privado `_verificar_autorizacion(self, usuario_rol, usuario_id, grupo_id)` en `ConvivenciaService`: si el provider es None → no hace nada (compat); si no → llama `puede_gestionar_comportamiento_en_grupo(...)` y si es False lanza `PermissionError` con mensaje claro.
- Ampliar firmas de las mutaciones con parámetro nuevo `usuario_rol: str | None = None` (default None para compat; las páginas SIEMPRE lo pasan tras este paso):
  - `registrar_comportamiento(dto, usuario_id=None, anio_id=None, usuario_rol=None)` — grupo desde `dto.grupo_id`.
  - `registrar_nota_comportamiento(dto, usuario_id=None, usuario_rol=None)` — grupo desde `dto.grupo_id`.
  - `agregar_seguimiento(registro_id, texto, usuario_id=None, usuario_rol=None)` — resuelve `grupo_id` releyendo el registro (ya lo hace vía `_get_registro_o_lanzar`).
  - `notificar_acudiente(registro_id, usuario_id=None, usuario_rol=None)` — igual.
  - `eliminar_registro(registro_id, usuario_id=None, usuario_rol=None)` — igual.
- Llamada al helper al inicio de cada mutación (después de resolver el grupo si aplica).

### T3 — Actualizar las páginas para pasar el rol
- `comportamiento.py`: en las 4 llamadas a mutaciones (`registrar_comportamiento`, `notificar_acudiente`, `agregar_seguimiento`, `eliminar_registro`), pasar `usuario_rol=ctx.usuario_rol`.
- `notas_convivencia.py`: en `registrar_nota_comportamiento` (usada por `_guardar_nota` y `_guardar_todo`), pasar `usuario_rol=ctx.usuario_rol`.
- No otra lógica: el gating de página sigue siendo el control principal; esto es la red de seguridad.

### T4 — Tests de servicio
- Crear/ampliar `tests/unit/services/test_convivencia_service.py`:
  - Con provider inyectado que devuelve `False` (mock/stub): una mutación cualquiera lanza `PermissionError` y NO persiste.
  - Con provider que devuelve `True`: la mutación funciona.
  - Sin provider (None): la mutación funciona (compat retro).

### T5 — Verificación
- `check_imports.py --layer services` + `--layer interface` en verde.
- `check_design.py --file` sobre las 2 páginas tocadas.
- `pytest tests/unit/services/ tests/unit/interface/ -q` verde.
- `init.py` VERDE.
- `progress/impl_convivencia_04b.md`.

## criterio_done
Las mutaciones de `ConvivenciaService` verifican autorización cuando hay provider inyectado (rechazan con `PermissionError` si el usuario_rol/usuario_id no pueden gestionar el grupo); las páginas pasan `usuario_rol=ctx.usuario_rol`; sin provider inyectado el servicio sigue funcionando (compat); tests verdes; `init.py` verde.
