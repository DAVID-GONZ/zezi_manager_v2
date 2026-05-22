# Tasks — paso_10f_informes

Cada tarea produce un artefacto verificable antes de pasar a la siguiente.

---

## T1 — Extender InformeService + re-exports

**Archivo:** `src/services/informe_service.py`

**Cambios:**
1. Agregar `generar_boletin_periodo(estudiante_id, grupo_id, periodo_id, formato="pdf") → bytes` según design.md.
2. Agregar `generar_boletin_anual(estudiante_id, grupo_id, anio_id, formato="pdf") → bytes` según design.md.
3. Actualizar `__all__` para re-exportar `InformeNotasDTO`, `InformeAsistenciaDTO`, `FormatoInforme`.

**Verificación:**
```python
python -X utf8 -c "
from src.services.informe_service import InformeService, InformeNotasDTO, InformeAsistenciaDTO, FormatoInforme
import inspect
assert hasattr(InformeService, 'generar_boletin_periodo'), 'falta generar_boletin_periodo'
assert hasattr(InformeService, 'generar_boletin_anual'), 'falta generar_boletin_anual'
assert issubclass(InformeNotasDTO, object)
print('T1 OK')
"
```

---

## T2 — consolidado_notas.py

**Archivo:** `src/interface/pages/informes/consolidado_notas.py`

**Implementar:**
- Ruta `/informes/consolidado-notas`.
- Guard SessionContext.
- Estado `_s` con grupo_id, asignacion_id, periodo_id, fecha_desde, fecha_hasta, formato.
- Filtros encadenados: al cambiar grupo → recarga asignaciones y periodos.
- Botón "Generar" → construye `InformeNotasDTO` → `informe_service.generar_notas()` → `ui.download()`.
- Captura `ValueError` → `ui.notify(..., type="negative")`.
- `app_layout(...)` estándar.

**Verificación:**
```python
python -X utf8 -c "
import importlib, ast, pathlib
src = pathlib.Path('src/interface/pages/informes/consolidado_notas.py').read_text(encoding='utf-8')
tree = ast.parse(src)
names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
assert 'consolidado_notas' not in src or True  # archivo no vacío
assert len(src.strip()) > 100, 'archivo parece vacío'
# Sin imports de dominio
assert 'src.domain' not in src, 'importa desde domain — violación de capa'
print('T2 sintaxis OK — verificar en browser')
"
```

---

## T3 — consolidado_asistencia.py

**Archivo:** `src/interface/pages/informes/consolidado_asistencia.py`

**Implementar:** igual que T2 pero con `InformeAsistenciaDTO` y `generar_asistencia()`.

**Verificación:**
```python
python -X utf8 -c "
import pathlib
src = pathlib.Path('src/interface/pages/informes/consolidado_asistencia.py').read_text(encoding='utf-8')
assert len(src.strip()) > 100
assert 'src.domain' not in src
assert 'generar_asistencia' in src
print('T3 OK')
"
```

---

## T4 — boletin_periodo.py

**Archivo:** `src/interface/pages/informes/boletin_periodo.py`

**Implementar:**
- Ruta `/informes/boletin-periodo`.
- Filtros: grupo + periodo.
- Al seleccionar grupo+periodo → carga `estudiante_service.listar_por_grupo(grupo_id)`.
- Lista de estudiantes; botón por estudiante → `informe_service.generar_boletin_periodo(...)` → `ui.download()`.
- Botón "Generar todos" → itera estudiantes.
- Captura `ValueError`.

**Verificación:**
```python
python -X utf8 -c "
import pathlib
src = pathlib.Path('src/interface/pages/informes/boletin_periodo.py').read_text(encoding='utf-8')
assert len(src.strip()) > 100
assert 'src.domain' not in src
assert 'generar_boletin_periodo' in src
assert 'listar_por_grupo' in src
print('T4 OK')
"
```

---

## T5 — boletin_anual.py

**Archivo:** `src/interface/pages/informes/boletin_anual.py`

**Implementar:** igual que T4 pero usa `anio_id` en lugar de `periodo_id` y llama `generar_boletin_anual()`.

**Verificación:**
```python
python -X utf8 -c "
import pathlib
src = pathlib.Path('src/interface/pages/informes/boletin_anual.py').read_text(encoding='utf-8')
assert len(src.strip()) > 100
assert 'src.domain' not in src
assert 'generar_boletin_anual' in src
print('T5 OK')
"
```

---

## T6 — estadisticos.py

**Archivo:** `src/interface/pages/informes/estadisticos.py`

**Implementar:**
- Ruta `/informes/estadisticos`.
- Bloque `_EC_*` al inicio del módulo (antes de cualquier función).
- Filtros: grupo, asignacion, periodo.
- Al confirmar → llama `estadisticos_service.distribucion_desempenos()`, `comparativo_periodos()`, `ranking_grupo()`.
- Renderiza 3 `ui.echart()` con options copiados de `_EC_*` e inyección de datos reales.
- Tabla de ranking con `ui.aggrid` o lista.

**Verificación:**
```python
python -X utf8 -c "
import pathlib, re
src = pathlib.Path('src/interface/pages/informes/estadisticos.py').read_text(encoding='utf-8')
assert len(src.strip()) > 100
assert 'src.domain' not in src
# Verificar que _EC_* está definido a nivel de módulo
ec_vars = re.findall(r'^_EC_\w+\s*[:=]', src, re.MULTILINE)
assert len(ec_vars) >= 3, f'Se esperan >= 3 vars _EC_*, encontradas: {ec_vars}'
assert 'distribucion_desempenos' in src
assert 'comparativo_periodos' in src
assert 'ranking_grupo' in src
print('T6 OK')
"
```

---

## T7 — Verificación final

```python
python -X utf8 -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

```python
python -X utf8 init.py 2>&1 | tail -10
```

Ambos deben terminar sin errores y con ≥ 607 tests pasando.

```python
python -X utf8 -c "
from container import Container
svc = Container.informe_service()
assert hasattr(svc, 'generar_boletin_periodo')
assert hasattr(svc, 'generar_boletin_anual')
print('Container OK')
"
```
