# convivencia_10_categorias_ui — Tasks
> Prerequisito: convivencia_09 DONE.

## Objetivo
Pantalla CRUD de categorías de observación accesible solo a
**coordinador y director**. Permite crear, editar nombre/tipo, y
desactivar categorías. Profesores no acceden.

## Scope
```
src/interface/pages/convivencia/categorias.py   ← crear
src/services/convivencia_service.py
```
Opcionales (si falta wiring):
```
container.py   (solo si convivencia_service no expone métodos de categorías)
```

## Diseño

### RBAC
Solo `Rol.COORDINADOR` y `Rol.DIRECTOR` acceden.
Guard en la página: si `ctx.rol not in (Rol.COORDINADOR, Rol.DIRECTOR)` →
`navigate.to('/inicio')` sin renderizar.

### Métodos nuevos en `ConvivenciaService`
```python
def listar_categorias(self, solo_activas: bool = True) -> list[CategoriaObservacion]
def crear_categoria(self, dto: NuevaCategoriaDTO) -> CategoriaObservacion
def actualizar_categoria(self, categoria_id: int, dto: NuevaCategoriaDTO) -> CategoriaObservacion
def desactivar_categoria(self, categoria_id: int) -> CategoriaObservacion
```
Estos son wrappers directos del repo (sin lógica de negocio compleja).
`desactivar_categoria` pone `activa=False` y llama `actualizar_categoria`.

### UI de la página
Patrón estándar del proyecto:
- `_s` con `categorias: list`, `editando: CategoriaObservacion | None`.
- Un refreshable `_contenido()`.
- Tabla de categorías con columnas: Nombre, Tipo (General / Comportamental), Estado (Activa / Inactiva).
- Fila con badge visual para tipo y estado.
- Botón "Nueva categoría" → `form_dialog` con campos: `nombre` (text), `es_comportamental` (checkbox).
- Botón editar (lápiz) por fila → mismo `form_dialog` con valores precargados.
- Botón desactivar (con `confirm_dialog`) para categorías activas.
- `empty_state` cuando no hay categorías.
- Toasts con `toast_success` / `toast_error`.
- `app_layout` con `page_titulo="Categorías de Observación"`.

### Ruta
Añadir a `main.py`: `/convivencia/categorias` → página.
Añadir a `NAV_ITEMS` en `layout.py` bajo el grupo "Aula" (o "Convivencia"),
con permiso `[Rol.COORDINADOR, Rol.DIRECTOR]`.

## Tareas

### T1 — `ConvivenciaService`: añadir métodos de categorías
**Archivo**: `src/services/convivencia_service.py`

Añadir `listar_categorias`, `crear_categoria`, `actualizar_categoria`, `desactivar_categoria`.
Sin decorador `@requiere_escritura` en `listar_categorias`. Con `@requiere_escritura`
en `crear_categoria`, `actualizar_categoria`, `desactivar_categoria`.

**Verificación**:
```
.venv/Scripts/python.exe scripts/check_imports.py --layer services
```

### T2 — `categorias.py`: implementar la página
**Archivo**: `src/interface/pages/convivencia/categorias.py`

Seguir el patrón de `observaciones.py` (guard → _s → refreshable → app_layout).
Usar únicamente componentes del design system (sin `ui.button().props()`, sin `style=` estático).

**Verificación**:
```
.venv/Scripts/python.exe scripts/check_design.py --file src/interface/pages/convivencia/categorias.py
.venv/Scripts/python.exe scripts/check_imports.py --layer interface
```

### T3 — Registrar ruta y nav
**Archivos**: `main.py`, `src/interface/design/layout.py`

- `main.py`: `app.add_route('/convivencia/categorias', categorias.page)`.
- `layout.py` `NAV_ITEMS`: añadir ítem bajo convivencia con `roles=[Rol.COORDINADOR, Rol.DIRECTOR]`.

### T4 — Test unitario del servicio
**Archivo**: `tests/unit/services/test_convivencia_service.py` (o crear si no existe)

Con `FakeConvivenciaRepo`:
- `test_listar_categorias_delega_al_repo` — verifica que el servicio llama `listar_categorias(solo_activas=True)`.
- `test_crear_categoria_llama_guardar` — servicio crea y retorna la categoría.
- `test_desactivar_categoria_pone_activa_false` — la categoría retornada tiene `activa=False`.

**Verificación**:
```
.venv/Scripts/python.exe -m pytest tests/unit/services/test_convivencia_service.py -v -k "categoria"
```

## criterio_done
- [ ] 4 métodos de categoría en `ConvivenciaService`.
- [ ] Página carga en `/convivencia/categorias` sin errores.
- [ ] `check_design` verde para la página.
- [ ] `check_imports --layer interface` verde.
- [ ] Profesor no accede (guard redirige).
- [ ] 3 tests unitarios del servicio verdes.
- [ ] `init.py --quick` → ENTORNO OK.
