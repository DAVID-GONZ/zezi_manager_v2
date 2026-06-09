# Tasks — paso_12b_design_components

## Resumen

| ID | Descripción | Archivos | Verificación |
|---|---|---|---|
| T1 | empty_state.py + empty_state.css | 2 archivos nuevos | import + smoke |
| T2 | skeleton_loader.py + skeleton_loader.css | 2 archivos nuevos | import + smoke |
| T3 | toast.py + toast.css | 2 archivos nuevos | import + smoke |
| T4 | Registrar en __init__.py | components/__init__.py | grep |
| T5 | CSS_LOAD_ORDER en theme.py | theme.py | grep |
| T6 | Tests unitarios | tests/unit/interface/design/ | pytest |
| T7 | Verificación final | — | init.py + 718 tests |

---

## T1 — empty_state

Crear `src/interface/design/components/empty_state.py` con el código de design.md §1.
Crear `src/interface/design/styles/components/empty_state.css` con el CSS de design.md §1.

**Verificación:**
```
python -c "from src.interface.design.components.empty_state import empty_state; print(empty_state)"
```

---

## T2 — skeleton_loader

Crear `src/interface/design/components/skeleton_loader.py` con los 3 presets de
design.md §2.
Crear `src/interface/design/styles/components/skeleton_loader.css`.

**Verificación:**
```
python -c "from src.interface.design.components.skeleton_loader import skeleton_table, skeleton_cards, skeleton_form"
```

---

## T3 — toast

Crear `src/interface/design/components/toast.py` con `toast()` + 4 atajos.
Crear `src/interface/design/styles/components/toast.css`.

**Punto delicado:** la firma exacta de `ui.notify(..., actions=...)` en NiceGUI 3.x
debe verificarse antes (la API ha cambiado entre versiones). El implementer:

1. Lee la versión instalada: `pip show nicegui | grep Version`.
2. Confirma el patrón de `actions` revisando un ejemplo en el código actual (si
   existe) o probando con un script de 5 líneas.
3. Si la API real difiere del diseño, ajusta y deja nota en `progress/impl_12b.md`.

**Verificación:**
```
python -c "from src.interface.design.components.toast import toast, toast_success"
```

---

## T4 — __init__.py

Añadir al final de `src/interface/design/components/__init__.py` los nuevos imports
y extender `__all__` según design.md §4.

**Verificación:**
```
python -c "from src.interface.design.components import empty_state, skeleton_table, toast_success"
```

---

## T5 — CSS_LOAD_ORDER

En `src/interface/design/theme.py`, añadir los tres CSS nuevos a la lista
`CSS_LOAD_ORDER`. Posición: en el bloque de componentes (después de cards.css o
chips.css; antes de domain/).

**Verificación:**
```
grep -A 20 CSS_LOAD_ORDER src/interface/design/theme.py | grep -c "empty_state\|skeleton_loader\|toast"
# debe ser 3
```

---

## T6 — Tests

Crear los tres archivos en `tests/unit/interface/design/`:

```
tests/unit/interface/design/
├── test_empty_state.py
├── test_skeleton_loader.py
└── test_toast.py
```

Patrón de cada test (smoke):

```python
# test_empty_state.py
def test_empty_state_importa():
    from src.interface.design.components import empty_state
    assert callable(empty_state)

def test_empty_state_renderiza_sin_error(client):
    """client fixture provista por NiceGUI test utilities."""
    from src.interface.design.components import empty_state
    @client.page("/_test_empty")
    def page():
        empty_state(titulo="Test")
    # cliente.open carga la página; éxito si no lanza excepción
```

Si no existe fixture de NiceGUI en el proyecto, dejar solo el smoke de import.

Para `test_toast.py`, verificar mapeo:

```python
def test_toast_success_usa_tipo_positive(monkeypatch):
    from src.interface.design.components import toast
    capturado = {}
    def fake_notify(msg, **kw):
        capturado["msg"] = msg
        capturado["kw"] = kw
    from nicegui import ui
    monkeypatch.setattr(ui, "notify", fake_notify)
    toast.toast_success("Hola")
    assert capturado["kw"]["type"] == "positive"
    assert capturado["kw"]["position"] == "bottom-right"
```

**Verificación:**
```
pytest tests/unit/interface/design/ -v
```

---

## T7 — Verificación final

```
python init.py                  # verde
pytest tests/ -v                # 718+ tests verdes
```

Smoke manual:
- Crear página throw-away en `src/interface/pages/dev/_demo_components.py` (NO
  rutearla en main.py) que use los 3 componentes. El implementer la ejecuta
  manualmente, valida visualmente, y la **borra antes de cerrar el paso**.

  Importante: este archivo demo NO se commitea. El reviewer verifica que no
  quedó en el árbol.

- Documentar en `progress/impl_12b.md`:
  - Versión NiceGUI usada y API de `ui.notify` confirmada.
  - Captura mental de cada componente renderizado (descripción textual).
  - Cualquier ajuste vs. el diseño original.

El reviewer comprueba:
- Los 3 componentes están exportados desde `components/__init__.py`.
- Los 3 CSS están en `CSS_LOAD_ORDER`.
- Demo throw-away no quedó en el repo.
- Tests pasan.
