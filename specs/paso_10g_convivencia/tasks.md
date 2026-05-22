# Tasks — paso_10g_convivencia
## Módulo: Convivencia (observaciones, comportamiento, notas)

Cada tarea produce un artefacto verificable dentro del scope `src/interface/pages/convivencia/`.

---

## T1 — Clases CSS para badges de tipo de registro

**Artefacto:** Bloques CSS en `src/interface/design/styles.css`
**Acción:** Añadir al final de `styles.css` las cinco clases `.badge-fortaleza`, `.badge-dificultad`, `.badge-compromiso`, `.badge-citacion`, `.badge-descargo` usando variables CSS existentes (`--color-success`, `--color-error`, `--color-warning`, `--color-info`, `--color-neutral`). Sin valores hex hardcodeados.

**Comando de verificación:**
```python
python -c "
import re, pathlib
css = pathlib.Path('src/interface/design/styles.css').read_text(encoding='utf-8')
badges = ['badge-fortaleza','badge-dificultad','badge-compromiso','badge-citacion','badge-descargo']
missing = [b for b in badges if f'.{b}' not in css]
assert not missing, f'Faltan clases: {missing}'
hex_in_badges = re.findall(r'badge-[a-z]+\s*\{[^}]*#[0-9a-fA-F]{3,6}', css)
assert not hex_in_badges, f'Colores hex hardcodeados encontrados: {hex_in_badges}'
print('T1 OK')
"
```

---

## T2 — observaciones.py: esqueleto, guard y refreshable

**Artefacto:** `src/interface/pages/convivencia/observaciones.py` con estructura base completa.
**Acción:** Crear el archivo con decorador `@ui.page("/convivencia/observaciones")`, guard de autenticación, dict `_estado`, función `_cargar_estado()` (que llama a `infraestructura_service` y `periodo_service`), decorador `@ui.refreshable` sobre `_contenido()`, y llamada a `app_layout` con `page_titulo`, `page_subtitulo`, `page_icono`, `on_context_change`.

**Comando de verificación:**
```python
python -c "
import ast, pathlib
src = pathlib.Path('src/interface/pages/convivencia/observaciones.py').read_text(encoding='utf-8')
tree = ast.parse(src)
# Verificar que no importa src.db
assert 'src.db' not in src, 'Importa src.db — violacion arquitectura'
# Verificar guard
assert 'navigate.to' in src or 'ui.navigate' in src, 'Falta guard de autenticación'
# Verificar refreshable
assert '@ui.refreshable' in src, 'Falta @ui.refreshable'
# Verificar app_layout
assert 'app_layout' in src, 'Falta app_layout'
# Verificar on_context_change
assert 'on_context_change' in src, 'Falta on_context_change'
print('T2 OK')
"
```

---

## T3 — observaciones.py: tabla aggrid y filtros de estudiante/periodo

**Artefacto:** `src/interface/pages/convivencia/observaciones.py` con selectores y tabla.
**Acción:** Dentro de `_contenido()`, añadir selectores de estudiante y periodo que actualicen `_estado` y llamen a `convivencia_service().listar_observaciones(...)`. Renderizar resultados en `ui.aggrid` con columnas: Estudiante, Texto (truncado a 80 chars), Visibilidad, Fecha registro.

**Comando de verificación:**
```python
python -c "
import ast, pathlib
src = pathlib.Path('src/interface/pages/convivencia/observaciones.py').read_text(encoding='utf-8')
assert 'ui.aggrid' in src, 'Falta ui.aggrid'
assert 'listar_observaciones' in src, 'Falta llamada a listar_observaciones'
assert 'sel_estudiante_id' in src or 'estudiante_id' in src, 'Falta selector de estudiante'
assert 'sel_periodo_id' in src or 'periodo_id' in src, 'Falta selector de periodo'
print('T3 OK')
"
```

---

## T4 — observaciones.py: CRUD crear, toggle visibilidad, eliminar

**Artefacto:** `src/interface/pages/convivencia/observaciones.py` con handlers completos.
**Acción:** Implementar `_crear_observacion(datos)` con `form_dialog`, `_toggle_visibilidad(obs_id, es_publica)`, y `_eliminar_observacion(obs_id)` con `confirm_dialog`. Verificar que no se usan enums de dominio importados directamente (usar strings literales).

**Comando de verificación:**
```python
python -c "
import pathlib
src = pathlib.Path('src/interface/pages/convivencia/observaciones.py').read_text(encoding='utf-8')
assert 'form_dialog' in src, 'Falta form_dialog para crear observacion'
assert 'confirm_dialog' in src, 'Falta confirm_dialog para eliminar'
assert 'registrar_observacion' in src, 'Falta llamada a registrar_observacion'
assert 'eliminar_observacion' in src, 'Falta llamada a eliminar_observacion'
# No debe importar TipoRegistro (no aplica aquí, pero sí verificar que no importe modelos de dominio)
assert 'from src.domain' not in src, 'Importa dominio directamente — usar strings'
print('T4 OK')
"
```

---

## T5 — comportamiento.py: esqueleto, guard y refreshable

**Artefacto:** `src/interface/pages/convivencia/comportamiento.py` con estructura base.
**Acción:** Crear con decorador `@ui.page("/convivencia/comportamiento")`, guard, dict `_estado` (incluyendo `anio_id`, `filtro_*`), `_cargar_estado()` que obtiene `anio_id` de `configuracion_service().get_activa()`, dict local `_TIPOS_DISPLAY` con las cinco entradas string, `@ui.refreshable` sobre `_contenido()`, y `app_layout`.

**Comando de verificación:**
```python
python -c "
import pathlib
src = pathlib.Path('src/interface/pages/convivencia/comportamiento.py').read_text(encoding='utf-8')
assert 'src.db' not in src, 'Violacion: importa src.db'
assert 'from src.domain' not in src, 'Importa dominio directamente'
assert '_TIPOS_DISPLAY' in src, 'Falta dict _TIPOS_DISPLAY local'
assert '@ui.refreshable' in src, 'Falta @ui.refreshable'
assert 'on_context_change' in src, 'Falta on_context_change en app_layout'
print('T5 OK')
"
```

---

## T6 — comportamiento.py: tabla aggrid con filtros y badges

**Artefacto:** `src/interface/pages/convivencia/comportamiento.py` con tabla y filtros.
**Acción:** Implementar filtros (grupo, periodo, tipo, solo_negativos) que construyan `FiltroConvivenciaDTO` y llamen a `listar_registros(filtro)`. Renderizar en `ui.aggrid` con `cellClass` para la columna Tipo usando las clases CSS de T1.

**Comando de verificación:**
```python
python -c "
import pathlib
src = pathlib.Path('src/interface/pages/convivencia/comportamiento.py').read_text(encoding='utf-8')
assert 'ui.aggrid' in src, 'Falta ui.aggrid'
assert 'listar_registros' in src, 'Falta listar_registros'
assert 'FiltroConvivenciaDTO' in src or 'filtro_convivencia' in src.lower(), 'Falta FiltroConvivenciaDTO'
assert 'cellClass' in src or 'badge-' in src, 'Falta cellClass para badges de tipo'
print('T6 OK')
"
```

---

## T7 — comportamiento.py: crear registro, notificar acudiente, seguimiento, eliminar

**Artefacto:** `src/interface/pages/convivencia/comportamiento.py` con todos los handlers de acción.
**Acción:** Implementar:
- `_crear_registro(datos)` con `form_dialog` (campos: estudiante, tipo como select con `_TIPOS_DISPLAY`, descripción, requiere_firma, fecha). Tipo se pasa como string al DTO.
- `_notificar_acudiente(registro_id)` — botón solo visible si `pendiente_notificacion`.
- `_agregar_seguimiento(registro_id)` con `form_dialog` de un campo textarea.
- `_eliminar_registro(registro_id)` con `confirm_dialog`.

**Comando de verificación:**
```python
python -c "
import pathlib
src = pathlib.Path('src/interface/pages/convivencia/comportamiento.py').read_text(encoding='utf-8')
assert 'registrar_comportamiento' in src, 'Falta registrar_comportamiento'
assert 'notificar_acudiente' in src, 'Falta notificar_acudiente'
assert 'agregar_seguimiento' in src, 'Falta agregar_seguimiento'
assert 'eliminar_registro' in src, 'Falta eliminar_registro'
assert 'confirm_dialog' in src, 'Falta confirm_dialog'
assert 'form_dialog' in src, 'Falta form_dialog'
# El servicio gestiona detectar_alertas internamente — la página NO lo debe llamar
assert 'detectar_alertas' not in src, 'La pagina llama detectar_alertas directamente — debe hacerlo el servicio'
print('T7 OK')
"
```

---

## T8 — notas_convivencia.py: esqueleto completo

**Artefacto:** `src/interface/pages/convivencia/notas_convivencia.py` con estructura base.
**Acción:** Crear con decorador `@ui.page("/convivencia/notas")`, guard, dict `_estado` (incluyendo `periodo_cerrado`, `cambios_pendientes`), `_cargar_estado()`, `@ui.refreshable`, y `app_layout` con `page_titulo="Notas de convivencia"`.

**Comando de verificación:**
```python
python -c "
import pathlib
src = pathlib.Path('src/interface/pages/convivencia/notas_convivencia.py').read_text(encoding='utf-8')
assert 'src.db' not in src, 'Violacion: importa src.db'
assert 'from src.domain' not in src, 'Importa dominio directamente'
assert 'periodo_cerrado' in src, 'Falta flag periodo_cerrado en estado'
assert 'cambios_pendientes' in src, 'Falta dict cambios_pendientes'
assert '@ui.refreshable' in src, 'Falta @ui.refreshable'
assert 'on_context_change' in src, 'Falta on_context_change'
print('T8 OK')
"
```

---

## T9 — notas_convivencia.py: aggrid editable y guardado individual/masivo

**Artefacto:** `src/interface/pages/convivencia/notas_convivencia.py` con grilla funcional.
**Acción:** Implementar `ui.aggrid` con columnas Estudiante, Nota (editable 0-100), Observación (editable). Si `periodo_cerrado`, pasar `editable: false` en todas las columnas. Implementar `_guardar_nota(estudiante_id, valor, observacion)` y `_guardar_todo()`. Capturar evento `cellValueChanged` de aggrid para actualizar `cambios_pendientes`.

**Comando de verificación:**
```python
python -c "
import pathlib
src = pathlib.Path('src/interface/pages/convivencia/notas_convivencia.py').read_text(encoding='utf-8')
assert 'ui.aggrid' in src, 'Falta ui.aggrid'
assert 'listar_notas_grupo' in src, 'Falta listar_notas_grupo'
assert 'registrar_nota_comportamiento' in src, 'Falta registrar_nota_comportamiento'
assert 'periodo_cerrado' in src, 'Falta logica de periodo_cerrado'
assert 'cambios_pendientes' in src, 'Falta tracking de cambios_pendientes'
assert 'guardar_todo' in src or '_guardar_todo' in src, 'Falta handler guardar todo'
print('T9 OK')
"
```

---

## T10 — Verificación de imports y arquitectura global

**Artefacto:** Los tres archivos del scope cumplen reglas de arquitectura.
**Acción:** Verificación cruzada — ninguno de los tres archivos importa `src.db`, modelos de dominio directamente, o instancia repositorios fuera del contenedor.

**Comando de verificación:**
```python
python -c "
import pathlib
archivos = [
    'src/interface/pages/convivencia/observaciones.py',
    'src/interface/pages/convivencia/comportamiento.py',
    'src/interface/pages/convivencia/notas_convivencia.py',
]
for ruta in archivos:
    src = pathlib.Path(ruta).read_text(encoding='utf-8')
    assert 'src.db' not in src, f'{ruta}: importa src.db'
    assert 'from src.domain.models' not in src, f'{ruta}: importa modelos de dominio directamente'
    assert 'Repository(' not in src, f'{ruta}: instancia repositorio fuera de Container'
    assert '.dict()' not in src, f'{ruta}: usa .dict() en vez de .model_dump()'
    print(f'OK: {ruta}')
print('T10 OK — Todos los archivos cumplen reglas de arquitectura')
"
```

---

## T11 — Smoke test de importación de los tres módulos

**Artefacto:** Los tres archivos son sintácticamente válidos e importables sin errores de parsing.

**Comando de verificación:**
```python
python -c "
import ast, pathlib
archivos = [
    'src/interface/pages/convivencia/observaciones.py',
    'src/interface/pages/convivencia/comportamiento.py',
    'src/interface/pages/convivencia/notas_convivencia.py',
]
for ruta in archivos:
    src = pathlib.Path(ruta).read_text(encoding='utf-8')
    try:
        ast.parse(src)
        print(f'AST OK: {ruta}')
    except SyntaxError as e:
        raise AssertionError(f'Error de sintaxis en {ruta}: {e}')
print('T11 OK — Sintaxis válida en los tres módulos')
"
```
