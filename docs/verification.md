# Verificación — Criterios de done ejecutables

> Cada paso tiene un criterio de done que puede verificarse con un comando.
> "Parece que funciona" no es suficiente. El comando debe pasar.

---

## Comando base (aplica a todos los pasos)

```bash
./init.sh
```

Si falla, el paso NO está done, sin excepción.

---

## Por paso

### Paso 2 — Modelos de dominio

```bash
python -m pytest tests/unit/domain/ -v
# Debe pasar sin BD real, sin NiceGUI, sin pandas importados
python -c "import src.domain.models.estudiante; import nicegui" 2>&1 | grep -c "nicegui"
# Debe retornar 0 (dominio no importa NiceGUI)
```

### Paso 3 — Puertos

```bash
python -c "
from src.domain.ports.estudiante_repo import IEstudianteRepository
from src.domain.ports.evaluacion_repo import IEvaluacionRepository
from src.domain.ports.service_ports import IAuthenticationService, IExporterService
print('OK')
"
```

### Paso 4 — Repositorios SQLite

```bash
python -m pytest tests/integration/test_repositories.py -v
# Verificar que ningún repositorio importa de src/services/ ni src/interface/
grep -r "from src.services" src/infrastructure/ && echo "ERROR: import prohibido" || echo "OK"
grep -r "from src.interface" src/infrastructure/ && echo "ERROR: import prohibido" || echo "OK"
```

### Paso 5 — Adaptadores

```bash
python -c "
from src.infrastructure.context.appstate_adapter import AppStateContextAdapter
from src.infrastructure.auth.auth_service import AuthenticationService
print('OK')
"
python -m pytest tests/unit/infrastructure/ -v
```

### Paso 7 — Container

```bash
python -c "from container import Container; print('OK')"
python main.py &
sleep 2 && curl -s http://localhost:8080 | head -1
kill %1
```

### Paso 8 — Servicios

```bash
python -m pytest tests/unit/services/ -v
# Verificar que ningún servicio importa infraestructura
grep -r "from src.infrastructure" src/services/ && echo "ERROR" || echo "OK"
grep -r "fetch_df\|execute" src/services/ && echo "ERROR" || echo "OK"
grep -r "import pandas" src/services/ && echo "ERROR" || echo "OK"
```

### Paso 9 — Tests unitarios

```bash
python -m pytest tests/unit/ -v --tb=short
# 100% verde
python -m pytest tests/integration/ -v --tb=short
# Sin regresiones respecto al baseline
```

### Paso 10 — Páginas

```bash
# Sin imports de infraestructura en páginas
grep -r "fetch_df\|execute\|from src.db" src/interface/ && echo "ERROR" || echo "OK"
grep -r "SqliteEstudianteRepository\|SqliteAsistenciaRepository" src/interface/ && echo "ERROR" || echo "OK"
# Tests de integración pasan
python -m pytest tests/ -v --tb=short
```

---

## Cómo verificar trazabilidad R\<n\> ↔ test

Cada requisito en `specs/<paso>/requirements.md` tiene un identificador `R1`, `R2`, etc.
Cada test que cubre ese requisito debe tener un comentario explícito:

```python
def test_matricular_documento_duplicado_falla(service):
    # R3: el sistema rechaza matrícula si el documento ya existe
    dto = NuevoEstudianteDTO(documento="123", nombre="Ana")
    service.matricular(dto)
    with pytest.raises(ValueError):
        service.matricular(dto)
```

El reviewer verifica que ningún `R<n>` del spec quede sin test asociado.

---

## Checklist de cierre de sesión

```bash
# 1. Tests verdes
./init.sh

# 2. Sin archivos temporales
find . -name "*.pyc" -not -path "./.venv/*" | head -5
find . -name "__pycache__" -not -path "./.venv/*" | head -5

# 3. Sin prints de debug (fuera de logging)
grep -r "^[[:space:]]*print(" src/ --include="*.py" | grep -v "# debug-ok"
```
