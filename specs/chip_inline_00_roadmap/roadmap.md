# Épica: Selectores Inline — Eliminar Chip Global de Contexto

> Aprobación de David requerida antes de iniciar chip_01.

## Motivación

El chip global de contexto (topbar) fue diseñado para páginas de aula (docente trabajando en un grupo/asignatura fija). En módulos de directivo, coordinación y convivencia, el chip es redundante o interfiere con los selectores propios de cada página. Además, el `SessionContext` "sangra" valores de periodo/grupo a páginas que tienen sus propios controles, creando una doble fuente de verdad silenciosa.

## Decisión de diseño (David, 2026-07-29)

| Módulo | Selectores | Chip global |
|--------|-----------|-------------|
| Planilla de Notas | Inline: Periodo + Grupo + Asignatura | ❌ Eliminado |
| Registro de Asistencia | Inline: Periodo + Grupo + Asignatura | ❌ Eliminado |
| Observaciones | Inline: Periodo + Grupo + Asignatura | ❌ Eliminado |
| Comportamiento | Inline: Periodo + Grupo + Asignatura | ❌ Eliminado |
| Seguimiento | Inline: Periodo + Grupo + Asignatura | ❌ Eliminado |
| Reporte Periodo Convivencia | Inline: Periodo + Grupo + Asignatura | ❌ Eliminado |
| Tablero Estadísticos | Inline: Periodo + Grupo + Asignatura | ❌ Eliminado |
| **Convivencia Notas** | **Inline: Periodo + Grupo** (grupo dirigido) | ❌ Eliminado |
| Directivo / Coordinación | Ya tienen selectores propios | ❌ Cortar bleeding |

**Regla invariante:** Los periodos cerrados siguen siendo solo lectura. La lógica de `periodo.estado` no se modifica.

## Decisiones de UX (David, 2026-07-29)

- **Estilo visual**: Pills/etiquetas clicables que muestran el valor actual y se despliegan al hacer clic (no dropdowns planos). Cada dimensión es un pill independiente en fila.
- **Pre-selección profesor**: periodo activo/abierto pre-seleccionado automáticamente al cargar la página.
- **Pre-selección directivo/coordinación**: sin preselección — la página arranca vacía, el usuario elige explícitamente.

## Componente central: `inline_selectors`

Nuevo componente reutilizable en `src/interface/design/components/inline_selectors.py`:

```
inline_periodo_grupo_asignatura(s, on_change, usuario_id, preselect_periodo)
inline_periodo_grupo(s, on_change, preselect_periodo)
```

- Cada selector se renderiza como un pill clicable: muestra el nombre actual, con icono `expand_more`. Al hacer clic despliega opciones (menu/popup).
- `preselect_periodo=True` (default para profesor): pre-selecciona el primer periodo abierto del año en curso.
- `preselect_periodo=False` (directivo/coordinación): sin preselección.
- Carga en cascada: periodo → grupo → asignatura (cuando aplica). El grupo y asignatura no cargan hasta que haya periodo seleccionado.
- Solo muestra asignaturas del `usuario_id` activo (para profesor); para directivo/coordinador muestra todas del grupo.
- El componente **no escribe de vuelta a SessionContext**. Cada página maneja su propio estado local `_s`.

## Pasos

### chip_01 — Componente inline_selectors
**Alcance:** `src/interface/design/components/inline_selectors.py` (nuevo archivo).
- Dos funciones públicas: `inline_periodo_grupo_asignatura` e `inline_periodo_grupo`.
- Acepta dict de estado local `s` y callback `on_change`.
- Pre-selección de periodo: carga periodos del año activo, marca primero el que tenga `estado='abierto'` (si hay uno), luego pre-selecciona.
- Cascada grupo: carga grupos del periodo seleccionado, filtrado por `usuario_id` si el rol es `profesor`.
- Cascada asignatura: carga asignaciones del grupo+periodo, filtrado por `usuario_id` si el rol es `profesor`.
- Respeta UI existente (usa `AppSelect` u equivalente del design system).
- Tests unitarios del componente (mocks de repositorios).

### chip_02 — Migrar Notas y Asistencia
**Alcance:** `src/interface/pages/notas/planilla_notas.py` + `src/interface/pages/asistencia/registro_asistencia.py`.
- Eliminar `on_context_change` que referencia el chip.
- Reemplazar cabecera con llamada a `inline_periodo_grupo_asignatura`.
- Verificar que la lógica de guardado/bloqueo por periodo cerrado sigue intacta.

### chip_03 — Migrar Convivencia
**Alcance:** 7 páginas de convivencia.
- `observaciones.py`, `comportamiento.py`, `seguimiento.py`, `reporte_periodo.py`, `tablero_estadisticos.py` → `inline_periodo_grupo_asignatura`.
- `notas_convivencia.py` → `inline_periodo_grupo`.
- Eliminar el `on_context_change` actual en cada página.

### chip_04 — Limpiar layout y bleeding directivo
**Alcance:** `src/interface/design/layout.py` + ~8 páginas de directivo/coordinación.
- `layout.py`: eliminar renderizado del chip (quitar llamada a `context_chip()` en `_topbar()`). El parámetro `mostrar_contexto` puede quedar pero no renderiza nada útil; se puede remover o dejar como noop.
- `context_selector.py`: marcar como módulo interno (no se importa desde páginas). No eliminar aún — el `SessionContext` sigue en uso para identidad y tenant scope.
- Páginas directivo: eliminar líneas `_s["periodo_id"] = ctx.periodo_id` / `_s["grupo_id"] = ctx.grupo_id`. Las páginas arrancan vacías (selectores sin preselección).

## Restricciones

- ❌ No modificar `src/domain/` ni `src/infrastructure/`. Solo `src/interface/`.
- ❌ No modificar `SessionContext` más allá de no llamar `.guardar()` desde las páginas migradas.
- ✅ `periodo.estado == 'cerrado'` debe seguir bloqueando edición en todas las páginas migradas.
- ✅ `init.py` completamente verde al final de cada paso.

## Estado

| Paso | Status |
|------|--------|
| chip_00 (spec) | ✅ Aprobado por David (pendiente confirmación) |
| chip_01 | ⏳ Esperando aprobación |
| chip_02 | ⏳ Esperando chip_01 |
| chip_03 | ⏳ Esperando chip_02 |
| chip_04 | ⏳ Esperando chip_03 |
