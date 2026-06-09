# Diseño — paso_12e_menu_ia

## 1. NAV_ITEMS completo final

```python
NAV_ITEMS: list[dict] = [
    {
        "label": "Inicio",
        "icon":  "home",
        "ruta":  "/inicio",
        "rol":   ["*"],
    },
    {
        "label": "Aula",
        "icon":  "co_present",
        "rol":   ["admin", "director", "coordinador", "profesor"],
        "children": [
            {"label": "Planilla de Notas", "icon": "table_chart",
             "ruta": "/evaluacion/planilla",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Asistencia",        "icon": "fact_check",
             "ruta": "/asistencia",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Observaciones",     "icon": "comment",
             "ruta": "/convivencia/observaciones",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Comportamiento",    "icon": "rule",
             "ruta": "/convivencia/comportamiento",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Seguimiento",       "icon": "assignment",
             "ruta": "/convivencia/notas",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
        ],
    },
    {
        "label": "Académico",
        "icon":  "school",
        "rol":   ["admin", "director", "coordinador", "profesor"],
        "children": [
            {"label": "Estudiantes",   "icon": "person",
             "ruta": "/estudiantes",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Grupos",        "icon": "group",
             "ruta": "/admin/grupos",
             "rol":  ["admin", "director"]},
            {"label": "Asignaturas",   "icon": "book",
             "ruta": "/admin/asignaturas",
             "rol":  ["admin", "director"]},
            {"label": "Asignaciones",  "icon": "assignment_ind",
             "ruta": "/admin/asignaciones",
             "rol":  ["admin", "director"]},
            {"label": "Horarios",      "icon": "calendar_today",
             "ruta": "/horarios",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
        ],
    },
    {
        "label": "Evaluación",
        "icon":  "grading",
        "rol":   ["admin", "director", "coordinador", "profesor"],
        "children": [
            {"label": "Configuración SIE",      "icon": "tune",
             "ruta": "/evaluacion/configuracion",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Habilitaciones",         "icon": "assignment_return",
             "ruta": "/evaluacion/habilitaciones",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Planes de Mejoramiento", "icon": "trending_up",
             "ruta": "/evaluacion/planes",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Cierre de Periodo",      "icon": "lock",
             "ruta": "/evaluacion/cierre-periodo",
             "rol":  ["admin", "director", "coordinador"]},
            {"label": "Cierre de Año",          "icon": "lock_clock",
             "ruta": "/evaluacion/cierre-anio",
             "rol":  ["admin", "director", "coordinador"]},
        ],
    },
    {
        "label": "Informes",
        "icon":  "summarize",
        "rol":   ["admin", "director", "coordinador", "profesor"],
        "children": [
            {"label": "Tablero",                    "icon": "dashboard",
             "ruta": "/academico/tablero",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Boletín de Periodo",         "icon": "description",
             "ruta": "/informes/boletin-periodo",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Boletín Anual",              "icon": "description",
             "ruta": "/informes/boletin-anual",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Consolidado de Notas",       "icon": "bar_chart",
             "ruta": "/informes/consolidado-notas",
             "rol":  ["admin", "director", "coordinador"]},
            {"label": "Consolidado de Asistencia",  "icon": "event_note",
             "ruta": "/informes/consolidado-asistencia",
             "rol":  ["admin", "director", "coordinador"]},
            {"label": "Estadísticos",               "icon": "analytics",
             "ruta": "/informes/estadisticos",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
        ],
    },
    {
        "divider": True,
        "rol":     ["admin", "director"],
    },
    {
        "label": "Administración",
        "icon":  "settings",
        "rol":   ["admin", "director"],
        "children": [
            {"label": "Usuarios",                   "icon": "badge",
             "ruta": "/admin/usuarios",
             "rol":  ["admin", "director"]},
            {"label": "Información Institucional",  "icon": "business",
             "ruta": "/admin/configuracion-institucion",
             "rol":  ["admin", "director"]},
        ],
    },
]
```

## 2. Diferencias vs NAV_ITEMS actual

| Cambio | Antes | Después |
|---|---|---|
| Item raíz "Dashboard" eliminado | `/inicio` raíz | "Inicio" raíz (rename) |
| Item raíz "Estudiantes" → bajo Académico | raíz | Académico → Estudiantes |
| Item raíz "Asistencia" → bajo Aula | raíz | Aula → Asistencia |
| Item raíz "Horarios" → bajo Académico | raíz | Académico → Horarios |
| Item raíz "Tablero" → bajo Informes | raíz | Informes → Tablero |
| Grupo "Calificaciones" → renombrado y partido | Calificaciones (6 hijos) | Aula (parcial) + Evaluación (5) |
| Grupo "Convivencia" → fundido en Aula | Convivencia (3 hijos) | Aula (3 de 5 vienen aquí) |
| Sub "Notas" → renombrado | Convivencia → Notas | Aula → Seguimiento |
| Sub "Config. Evaluación" → renombrado | Calificaciones → Config. Evaluación | Evaluación → Configuración SIE |
| Admin partido: Grupos/Asignaturas/Asignaciones suben a Académico | Admin (6 hijos) | Académico (3 nuevos) + Admin (2 que quedan) |
| Admin queda con 2 hijos: Usuarios, Info Institucional | 6 hijos | 2 hijos |
| Subitem "Config. SIE" eliminado de Admin | Admin → Config. SIE | Movido a Evaluación → Configuración SIE |

Nota R: "Config. SIE" existía en Admin con ruta `/admin/configuracion`. La nueva
ruta `Evaluación → Configuración SIE` también apunta a `/evaluacion/configuracion`
(que ya existe). Si la página `/admin/configuracion` y `/evaluacion/configuracion`
son rutas distintas en el código actual, el implementer aclara:

- Si son la **misma página** con dos rutas → preservar ambas en el menú (o
  consolidar a una). Recomendación: dejar solo `/evaluacion/configuracion`.
- Si son **páginas distintas** → mantenerlas separadas, una en cada grupo.

El implementer revisa `main.py` para confirmar.

## 3. Test de invariantes

`tests/unit/interface/design/test_navitems.py` (NUEVO):

```python
"""Verifica que NAV_ITEMS mantiene rutas y respeta roles."""
from src.interface.design.layout import NAV_ITEMS

RUTAS_REQUERIDAS = {
    "/inicio",
    "/estudiantes",
    "/asistencia",
    "/evaluacion/planilla",
    "/evaluacion/configuracion",
    "/evaluacion/habilitaciones",
    "/evaluacion/planes",
    "/evaluacion/cierre-periodo",
    "/evaluacion/cierre-anio",
    "/convivencia/observaciones",
    "/convivencia/comportamiento",
    "/convivencia/notas",
    "/informes/boletin-periodo",
    "/informes/boletin-anual",
    "/informes/consolidado-notas",
    "/informes/consolidado-asistencia",
    "/informes/estadisticos",
    "/horarios",
    "/academico/tablero",
    "/admin/grupos",
    "/admin/asignaturas",
    "/admin/asignaciones",
    "/admin/configuracion-institucion",
    "/admin/usuarios",
}

def _todas_las_rutas(items):
    for it in items:
        if "ruta" in it:
            yield it["ruta"]
        for c in it.get("children", []):
            if "ruta" in c:
                yield c["ruta"]

def test_navitems_preserva_rutas():
    actuales = set(_todas_las_rutas(NAV_ITEMS))
    faltantes = RUTAS_REQUERIDAS - actuales
    assert not faltantes, f"Rutas perdidas: {faltantes}"

def test_navitems_grupos_raiz_seis():
    # 5 items con label + 1 divider + 1 item Administración = 7 entradas
    # pero "grupos visibles" depende del rol; este test cuenta entradas top-level
    # que NO son divider.
    no_dividers = [i for i in NAV_ITEMS if "divider" not in i]
    assert len(no_dividers) == 6, f"Esperados 6 grupos raíz, hay {len(no_dividers)}"

def test_navitems_filtro_profesor():
    """Profesor: Inicio + Aula (5) + Académico (Estudiantes + Horarios) +
    Evaluación (4 visibles, sin Cierre de Año si no aplica — verificar contra
    los roles) + Informes (4 visibles) — sin Administración."""
    from src.interface.design.layout import _usuario_puede_ver

    visibles = [i for i in NAV_ITEMS if _usuario_puede_ver(i, "profesor")]
    labels = [i.get("label") for i in visibles]
    assert "Administración" not in labels
    assert "Inicio" in labels
    assert "Aula" in labels
```

## 4. Alternativa descartada

**Mantener "Calificaciones" como grupo unificado.** Descartada: mezcla operaciones
diarias del docente (Planilla) con operaciones administrativas (Cierre). El
docente entra a "Calificaciones" buscando la Planilla y se encuentra primero con
"Configuración" o "Cierre" en el listado. Separar en Aula (diario) + Evaluación
(config/cierre) alinea con el modelo mental.

**Renombrar a "Profesor / Coordinador / Director"** (rol-based). Descartada:
hace que las labels cambien según quién mira; rompe la regla de URLs estables y
documentación consistente. La filtrado por rol ya hace ese ajuste sin renombrar.

## 5. Orden de tareas

1. T1: reescribir `NAV_ITEMS` en `layout.py`.
2. T2: verificar permisos por rol contra original; corregir desvíos.
3. T3: crear `test_navitems.py`.
4. T4: smoke por rol (admin, director, coordinador, profesor).
5. T5: verificación final.
