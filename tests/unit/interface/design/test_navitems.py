"""
test_navitems.py — Verifica que NAV_ITEMS mantiene rutas y respeta roles.

Invariantes:
- Todas las rutas que existían antes del refactor siguen presentes.
- Exactamente 6 grupos raíz no-divider.
- El filtro por rol funciona: profesores no ven Administración.

paso_35 — Fuente única: la visibilidad del NAV se deriva del registro central
`roles_de_ruta`. Estos tests dependen del fixture autouse `registro_rutas`
(tests/unit/interface/conftest.py) que puebla el registro.
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
    """Profesor: Inicio + Aula + Académico + Evaluación + Informes; sin
    Administración."""
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


# ── paso_35: fuente única — sin drift entre NAV y registro ────────────────────

def test_navitems_rutas_existen_en_registro():
    """Cada ruta del NAV debe estar registrada en el guard central (no drift)."""
    from src.interface.auth import roles_de_ruta

    rutas_nav = set(_todas_las_rutas(NAV_ITEMS))
    sin_registro = {r for r in rutas_nav if roles_de_ruta(r) is None}
    assert not sin_registro, f"Rutas del NAV sin registro de guard: {sin_registro}"


def test_navitems_visibilidad_coincide_con_registro():
    """
    Para cada ruta del NAV y cada rol institucional, la visibilidad del NAV
    coincide EXACTAMENTE con la decisión del registro central (deny-by-default,
    sin segunda fuente de verdad que pueda divergir).
    """
    from src.interface.auth import AUTENTICADO, PUBLICO, roles_de_ruta
    from src.interface.design.layout import _rol_permitido_en_ruta

    roles_sistema = ["admin", "director", "coordinador", "profesor"]
    for ruta in _todas_las_rutas(NAV_ITEMS):
        roles = roles_de_ruta(ruta)
        assert roles is not None, f"{ruta} no registrada"
        for rol in roles_sistema:
            esperado = (
                roles in (PUBLICO, AUTENTICADO)
                or rol in {r.value for r in roles}
            )
            assert _rol_permitido_en_ruta(ruta, rol) is esperado, (
                f"Drift NAV↔registro en {ruta} para {rol}"
            )


def test_configuracion_sie_nav_solo_profesor():
    """C reconciliado: la ruta /evaluacion/configuracion es solo profesor; en
    el NAV 'Configuración SIE' se muestra solo a profesor (NAV ↔ ruta)."""
    from src.interface.design.layout import _usuario_puede_ver

    eval_grupo = next(i for i in NAV_ITEMS if i.get("label") == "Evaluación")
    sie = next(
        c for c in eval_grupo["children"]
        if c.get("ruta") == "/evaluacion/configuracion"
    )
    assert _usuario_puede_ver(sie, "profesor") is True
    assert _usuario_puede_ver(sie, "director") is False
    assert _usuario_puede_ver(sie, "coordinador") is False
    assert _usuario_puede_ver(sie, "admin") is False
