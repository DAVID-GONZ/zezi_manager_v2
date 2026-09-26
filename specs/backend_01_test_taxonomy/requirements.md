# Requisitos: Taxonomía de tests (backend_01_test_taxonomy)

> Ámbito: clasificación de los ~194 archivos de test con markers pytest para
> poder seleccionar tests de repositorio por separado de los agnósticos de BD.

---

## Clasificación

R1: EL SISTEMA DEBE clasificar cada archivo de test en exactamente una de estas
    categorías según su dependencia del backend de base de datos:
    (a) agnóstico — usa FakeRepository o no toca BD;
    (b) repositorio — instancia un repositorio SQLite o importa `sqlite3`.

R2: EL SISTEMA DEBE exponer la clasificación mediante markers de pytest
    (`@pytest.mark.repo`) de modo que `pytest -m repo` seleccione solo los
    tests de categoría (b).

R3: EL SISTEMA NO DEBE requerir decorar cada test a mano: el marcado DEBE
    aplicarse de forma automática según la ubicación del archivo o un
    mecanismo equivalente.

---

## Selección y coexistencia

R4: `pytest -m repo` DEBE seleccionar exclusivamente los tests de la
    categoría (b) — ni más ni menos.

R5: `pytest -m "not repo"` DEBE seguir ejecutando todos los tests de la
    categoría (a) y su resultado DEBE ser idéntico al de antes del paso.

R6: Los markers existentes (`unit`, `integration`, `e2e`, `browser`, `slow`)
    DEBEN coexistir con `repo` sin conflicto: un test puede tener ambos
    (`integration` + `repo`).

R7: EL SISTEMA DEBE registrar el marker `repo` en `pyproject.toml` para
    evitar el warning `PytestUnknownMarkWarning`.

---

## Preservación

R8: EL SISTEMA NO DEBE modificar el contenido de ningún test existente.

R9: La suite completa (`pytest`) DEBE mantener el mismo número de tests
    passed y el mismo número de tests failed que antes del paso.
