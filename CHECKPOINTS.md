# CHECKPOINTS.md — Criterios de estado correcto

> El reviewer usa esta lista para decidir si un paso está verdaderamente terminado.
> Cada ítem es verificable con una herramienta o un comando, no con opinión.

---

## Criterios globales (aplican a TODO paso)

- [ ] `python init.py` termina verde (todos los tests pasan).
- [ ] No hay archivos con `print()` de debug que no estaban antes.
- [ ] No hay `TODO` sin contexto de seguimiento en `progress/current.md`.
- [ ] `progress/current.md` está actualizado con lo que se hizo.

---

## Criterios por capa

### Dominio (`src/domain/`)

- [ ] Ningún archivo importa `nicegui`, `sqlite3`, `pandas`, `openpyxl`, ni `bcrypt`.
- [ ] Todos los modelos usan `model_dump()`, nunca `.dict()`.
- [ ] Los modelos con máquina de estado tienen `@field_validator` o `@model_validator` que valida coherencia.
- [ ] Los DTOs de creación tienen `to_<entidad>()`. Los de actualización tienen `aplicar_a(entidad)`.
- [ ] Los puertos en `src/domain/ports/` son `ABC` puros — sin implementación, sin `pass` de lógica.

### Infraestructura (`src/infrastructure/`)

- [ ] Cada repositorio importa **solo** de `src.db.queries` (fetch_df, execute) y del dominio.
- [ ] Ningún repositorio importa de `src/services/` ni de `src/interface/`.
- [ ] El mapeo de filas a entidades usa `Entidad(**df.iloc[0].to_dict())` o `[Entidad(**r) for r in df.to_dict("records")]`.
- [ ] Los adaptadores (auth, context) implementan la interfaz de `service_ports.py` y delegan sin añadir lógica propia.
- [ ] `NullExporter` lanza `RuntimeError` descriptivo si se invoca — no `NotImplementedError` vacío.

### Servicios (`src/services/`)

- [ ] Ningún servicio importa `sqlite3`, `pandas`, `nicegui`, `fetch_df`, ni `execute`.
- [ ] Ningún servicio importa directamente de `src/infrastructure/`.
- [ ] Todos los métodos mutadores terminan con una llamada a `_auditar()`.
- [ ] Los cálculos de métricas no usan `groupby`/`iterrows` de pandas — usan repositorios con `GROUP BY` en SQL.
- [ ] Cada servicio recibe sus dependencias por constructor (inyección), no las instancia internamente.

### Container (`container.py`)

- [ ] No hay variables de clase instanciadas al momento de importar — todo es lazy dentro de métodos `@classmethod`.
- [ ] `Container.reset()` existe y vacía `_cache`.
- [ ] `Container.diagnostico()` existe y se llama en `main.py` si `is_development`.
- [ ] Ningún módulo fuera de `container.py` importa directamente de `src/infrastructure/`.

### Interfaz (`src/interface/`)

- [ ] Ninguna página importa `fetch_df`, `execute`, `sqlite3`, ni `src.db.*`.
- [ ] Ninguna página instancia un repositorio directamente.
- [ ] Todas las llamadas a datos pasan por `Container.<servicio>.<método>()`.
- [ ] No hay colores hexadecimales hardcodeados en Python fuera de `tokens.py` y el bloque `_EC_*`.
- [ ] No hay `cellStyle` con colores inline en ag-Grid — usar `cellClass` y `rowClassRules` con nombres de clase CSS.
- [ ] **Toda página con estado tiene su presenter espejo** en `src/interface/presenters/<mismo_subdir>/<nombre>_presenter.py`; la página hace `_s = presenter.estado` y los handlers llaman a métodos del presenter (no escriben view-state directo).
- [ ] **Ningún módulo de `src/interface/presenters/` importa `nicegui`** (subcapa pura).
- [ ] **Sin lógica de negocio en presenter ni en closures de página**: cálculos, reglas, umbrales y validaciones viven en `services`/`domain` (`docs/conventions.md` §14).

### Tests

- [ ] Los tests unitarios en `tests/unit/` usan `FakeRepository` — sin BD real.
- [ ] Los tests de integración existentes en `tests/integration/` no regresionan.
- [ ] Cada requisito `R<n>` de un spec tiene al menos un test que lo valida explícitamente (comentario `# R<n>`).
- [ ] **Sin tests-tautología**: cada test de UI IMPORTA y LLAMA al código de producción (presenter/servicio); nunca reimplementa la lógica y hace assert sobre la copia.
- [ ] Toda página con estado tiene un test de presenter en `tests/unit/interface/presenters/` que llama al presenter real; `test_presenters_puros.py` sigue verde.
- [ ] Ruta nueva o cambio de roles → `ACCESO_ESPERADO` de `test_matriz_rutas_completa.py` actualizado en el mismo commit; `pytest -m e2e` verde.

---

## Anti-patrones que el reviewer rechaza automáticamente

| Anti-patrón | Regla violada |
|---|---|
| `from src.db.queries import fetch_df` en un servicio o página | Infraestructura no sube a capas superiores |
| `repo = SqliteEstudianteRepository()` en una página | Solo Container instancia repositorios |
| `.dict()` en lugar de `model_dump()` | Pydantic v2 |
| `import nicegui` en `src/domain/` o `src/services/` | Dominio no conoce el framework |
| `import nicegui` en `src/interface/presenters/` | El presenter es subcapa pura (portable al fork Vue) |
| Reglas/cálculos de negocio dentro de un presenter o de un closure de página | Lógica de negocio va a `services`/`domain` (§14) |
| Test que reimplementa la lógica y hace assert sobre su copia (tautología) | El test debe llamar al código de producción |
| Página con estado sin presenter espejo, o handler que escribe view-state directo | Delegar view-state al presenter |
| Test e2e que apunta a `main.py` en vez de `tests/e2e/e2e_app.py` | El fixture `user` ejecutaría `main()` contra la BD real |
| `groupby` o `iterrows` en un servicio | Pandas vive en infraestructura |
| Código nuevo apilado sobre código viejo (duplicate stacking) | Fixes deben ser quirúrgicos (antes/después) |
| `try/except ImportError` en una página | Solo en `container.py` |
| `raise NotImplementedError` vacío en un repositorio concreto | Implementar o documentar el bloqueo |
| `registrar_cambio(tabla=..., accion=...)` con kwargs inexistentes | Verificar firma real del método antes de llamarlo |
