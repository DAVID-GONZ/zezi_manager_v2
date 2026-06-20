"""
test_navitems.py — Verifica que NAV_ITEMS mantiene rutas y respeta roles.

Invariantes:
- Todas las rutas que existían antes del refactor siguen presentes.
- Exactamente 6 grupos raíz no-divider.
- El filtro por rol funciona: profesores no ven Administración.
"""
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
    "/admin/auditoria",
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


def test_navitems_admin_es_plataforma():
    """admin es rol de plataforma: NO ve Aula/Académico/Evaluación/Informes;
    SÍ ve Inicio y Administración. Dentro de Administración ve Usuarios y
    Auditoría, pero NO Información Institucional (heredada por director)."""
    from src.interface.design.layout import _usuario_puede_ver

    visibles = [i for i in NAV_ITEMS if _usuario_puede_ver(i, "admin")]
    labels = [i.get("label") for i in visibles]
    assert "Aula" not in labels
    assert "Académico" not in labels
    assert "Evaluación" not in labels
    assert "Informes" not in labels
    assert "Inicio" in labels
    assert "Administración" in labels

    admin_grupo = next(i for i in NAV_ITEMS if i.get("label") == "Administración")
    hijos_admin = [
        c["label"] for c in admin_grupo["children"]
        if _usuario_puede_ver(c, "admin")
    ]
    assert "Usuarios" in hijos_admin
    assert "Auditoría" in hijos_admin
    assert "Información Institucional" not in hijos_admin


def test_navitems_director_hereda_institucional():
    """director conserva acceso institucional/académico y ve Información
    Institucional dentro de Administración; NO ve Auditoría (admin exclusivo)."""
    from src.interface.design.layout import _usuario_puede_ver

    visibles = [i for i in NAV_ITEMS if _usuario_puede_ver(i, "director")]
    labels = [i.get("label") for i in visibles]
    assert "Aula" in labels
    assert "Académico" in labels
    assert "Administración" in labels

    admin_grupo = next(i for i in NAV_ITEMS if i.get("label") == "Administración")
    hijos_dir = [
        c["label"] for c in admin_grupo["children"]
        if _usuario_puede_ver(c, "director")
    ]
    assert "Información Institucional" in hijos_dir
    assert "Usuarios" in hijos_dir
    assert "Auditoría" not in hijos_dir
