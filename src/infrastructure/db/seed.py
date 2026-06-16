"""
Seed de base de datos — ZECI Manager v2.0
==========================================

Tres modos de uso:

  seed_base(conn)
      Datos mínimos que toda instalación DEBE tener: usuario admin,
      configuración del año activo, niveles de desempeño por defecto,
      áreas de conocimiento y alertas base. Seguro en producción.

  seed_dev(conn, total_estudiantes)
      Dataset completo para desarrollo: grupos, profesores, estudiantes,
      acudientes, asignaciones, categorías, actividades, notas,
      asistencias y observaciones. Solo para entornos de desarrollo.

  seed_test(conn)
      Dataset mínimo y determinista para tests de integración.
      Siempre recibe una conexión explícita (en memoria o temporal).
      Sin randomización — los IDs y valores son predecibles.

Todas las funciones _seed_* son idempotentes: no fallan ni duplican
si los datos ya existen. No hacen commit — la gestión de transacciones
es responsabilidad del llamador.
"""

from __future__ import annotations

import hashlib
import logging
import random
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from src.domain.scheduling import colorear_aristas_bipartito

logger = logging.getLogger("DB.SEED")

# ---------------------------------------------------------------------------
# Tipo para la función de hash de contraseñas (inyectable en tests)
# ---------------------------------------------------------------------------
PasswordHasher = Callable[[str], str]


def _default_hasher(password: str) -> str:
    """
    Usa bcrypt si está disponible; cae a SHA-256 con prefijo en caso contrario.
    El prefijo 'sha256:' permite que el servicio de auth detecte el algoritmo.
    """
    try:
        import bcrypt  # noqa: PLC0415
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    except ImportError:
        digest = hashlib.sha256(password.encode()).hexdigest()
        return f"sha256:{digest}"


def _fast_hasher(password: str) -> str:
    """
    Hash rápido para tests — evita el coste de bcrypt en suites de CI.
    Nunca usar en producción.
    """
    digest = hashlib.sha256(password.encode()).hexdigest()
    return f"sha256:{digest}"


# ---------------------------------------------------------------------------
# Resultado estructurado del seed
# ---------------------------------------------------------------------------

@dataclass
class SeedResult:
    """
    Contiene todos los IDs creados por el seed.
    Permite que los tests accedan a datos concretos sin hacer queries.
    """
    anio_id:        int                  = 0
    periodo_ids:    list[int]            = field(default_factory=list)
    grupo_ids:      list[int]            = field(default_factory=list)
    usuario_ids:    dict[str, int]       = field(default_factory=dict)  # usuario → id
    asignatura_ids: dict[str, int]       = field(default_factory=dict)  # codigo → id
    area_ids:       dict[str, int]       = field(default_factory=dict)  # nombre → id
    asignacion_ids: list[int]            = field(default_factory=list)
    estudiante_ids: list[int]            = field(default_factory=list)
    acudiente_ids:  list[int]            = field(default_factory=list)
    nivel_ids:      list[int]            = field(default_factory=list)
    counts:         dict[str, int]       = field(default_factory=dict)

    def log_resumen(self) -> None:
        logger.info("Resumen del seed:")
        for k, v in self.counts.items():
            logger.info(f"  {k:<28s} {v:>5d}")


# ---------------------------------------------------------------------------
# Datos de referencia
# ---------------------------------------------------------------------------

_NOMBRES_M = [
    "Santiago", "Sebastián", "Matías", "Nicolás", "Alejandro",
    "Diego", "Samuel", "Daniel", "Leonardo", "Felipe",
    "Tomás", "Martín", "Lucas", "Joaquín", "Gabriel",
]

_NOMBRES_F = [
    "Sofía", "Mariana", "Valentina", "Isabella", "Camila",
    "Valeria", "Daniela", "Victoria", "Martina", "Salomé",
    "Ximena", "Lucía", "Sara", "Antonella", "Renata",
]

_APELLIDOS = [
    "González", "Rodríguez", "Gómez", "Fernández", "López",
    "Díaz", "Martínez", "Pérez", "García", "Sánchez",
    "Moreno", "Jiménez", "Ruiz", "Hernández", "Torres",
]

# (nombre, codigo, color_hex)
_AREAS = [
    ("Ciencias Naturales y Educación Ambiental", "CNAT", "#2E7D32"),
    ("Ciencias Sociales",                        "CSOC", "#C62828"),
    ("Educación Artística y Cultural",            "ARTE", "#AD1457"),
    ("Educación Ética y en Valores Humanos",      "ETIC", "#6A1B9A"),
    ("Educación Física, Recreación y Deportes",   "EFIS", "#1565C0"),
    ("Educación Religiosa",                       "RELI", "#4527A0"),
    ("Humanidades, Lengua Castellana e Idiomas",  "HUMA", "#EF6C00"),
    ("Matemáticas",                               "MATE", "#00838F"),
    ("Tecnología e Informática",                  "TINF", "#37474F"),
    ("Filosofía",                                 "FILO", "#5D4037"),
]

# (nombre, codigo, area_nombre, horas_semanales)
_ASIGNATURAS = [
    ("Ciencias Naturales",   "CNT", "Ciencias Naturales y Educación Ambiental", 4),
    ("Biología",             "BIO", "Ciencias Naturales y Educación Ambiental", 3),
    ("Química",              "QUI", "Ciencias Naturales y Educación Ambiental", 3),
    ("Física",               "FIS", "Ciencias Naturales y Educación Ambiental", 3),
    ("Ciencias Sociales",    "CSO", "Ciencias Sociales",                        4),
    ("Historia",             "HIS", "Ciencias Sociales",                        2),
    ("Geografía",            "GEO", "Ciencias Sociales",                        2),
    ("Artística",            "ART", "Educación Artística y Cultural",            2),
    ("Ética",                "ETI", "Educación Ética y en Valores Humanos",      1),
    ("Educación Física",     "EDF", "Educación Física, Recreación y Deportes",  2),
    ("Religión",             "REL", "Educación Religiosa",                       1),
    ("Lengua Castellana",    "LEN", "Humanidades, Lengua Castellana e Idiomas", 5),
    ("Inglés",               "ING", "Humanidades, Lengua Castellana e Idiomas", 3),
    ("Francés",              "FRA", "Humanidades, Lengua Castellana e Idiomas", 2),
    ("Matemáticas",          "MAT", "Matemáticas",                              5),
    ("Estadística",          "EST", "Matemáticas",                              2),
    ("Tecnología",           "TEC", "Tecnología e Informática",                 2),
    ("Informática",          "INF", "Tecnología e Informática",                 2),
    ("Filosofía",            "FIL", "Filosofía",                                1),
]

# (codigo, nombre, grado, jornada, capacidad)
_GRUPOS_DEV = [
    ("601",  "Sexto A",    6,  "UNICA", 40),
    ("602",  "Sexto B",    6,  "UNICA", 40),
    ("701",  "Séptimo A",  7,  "UNICA", 40),
    ("702",  "Séptimo B",  7,  "UNICA", 40),
    ("801",  "Octavo A",   8,  "UNICA", 40),
    ("802",  "Octavo B",   8,  "UNICA", 40),
    ("901",  "Noveno A",   9,  "UNICA", 40),
    ("902",  "Noveno B",   9,  "UNICA", 40),
    ("1001", "Décimo A",   10, "UNICA", 40),
    ("1002", "Décimo B",   10, "UNICA", 40),
    ("1101", "Once A",     11, "UNICA", 40),
    ("1102", "Once B",     11, "UNICA", 40),
]

# (usuario, password, nombre_completo, email, rol)
_USUARIOS_BASE = [
    ("admin",       "Admin2025*",    "Carlos Alberto Administrador", "admin@zeci.edu.co",       "admin"),
]

_USUARIOS_DEV = [
    ("director",    "Director2025*", "María Elena Directora",   "director@zeci.edu.co",    "director"),
    ("coordinador", "Coord2025*",    "Jorge Iván Coordinador",  "coordinador@zeci.edu.co", "coordinador"),
    ("rgomez",      "Pass2025*",     "Ricardo Gómez Ríos",      "rgomez@zeci.edu.co",      "profesor"),
    ("cmoreno",     "Pass2025*",     "Claudia Moreno Díaz",     "cmoreno@zeci.edu.co",     "profesor"),
    ("jvargas",     "Pass2025*",     "Javier Vargas Peña",      "jvargas@zeci.edu.co",     "profesor"),
    ("amartinez",   "Pass2025*",     "Ana Martínez Soto",       "amartinez@zeci.edu.co",   "profesor"),
    ("pjimenez",    "Pass2025*",     "Paula Jiménez Lara",      "pjimenez@zeci.edu.co",    "profesor"),
    ("dortiz",      "Pass2025*",     "Diego Ortiz Cano",        "dortiz@zeci.edu.co",      "profesor"),
    ("lcastro",     "Pass2025*",     "Laura Castro Mejía",      "lcastro@zeci.edu.co",     "profesor"),
    ("fherrera",    "Pass2025*",     "Felipe Herrera Gil",      "fherrera@zeci.edu.co",    "profesor"),
    ("mrojas",      "Pass2025*",     "Marcela Rojas Niño",      "mrojas@zeci.edu.co",      "profesor"),
    ("gsalazar",    "Pass2025*",     "Gloria Salazar Ruiz",     "gsalazar@zeci.edu.co",    "profesor"),
    ("hmedina",     "Pass2025*",     "Héctor Medina Pardo",     "hmedina@zeci.edu.co",     "profesor"),
    ("swhite",      "Pass2025*",     "Sarah White Jones",       "swhite@zeci.edu.co",      "profesor"),
    ("ablack",      "Pass2025*",     "Andrés Black Mora",       "ablack@zeci.edu.co",      "profesor"),
    ("nrivera",     "Pass2025*",     "Natalia Rivera Lozano",   "nrivera@zeci.edu.co",     "profesor"),
    ("ocastano",    "Pass2025*",     "Oscar Castaño Vélez",     "ocastano@zeci.edu.co",    "profesor"),
    ("vmolina",     "Pass2025*",     "Valentina Molina Cruz",   "vmolina@zeci.edu.co",     "profesor"),
    ("tbeltran",    "Pass2025*",     "Tomás Beltrán Acosta",    "tbeltran@zeci.edu.co",    "profesor"),
]

# (profesor_usuario, [codigos_asignatura])
_ASIGNACIONES_DEV = [
    ("lopez",      ["BIO", "CNT"]),
    ("garcia",     ["MAT", "EST"]),
    ("martin",     ["LEN", "FIL"]),
    ("rodriguez",  ["ING", "FRA"]),
    ("gomez",      ["EDF", "ETI"]),
    ("torres",     ["TEC", "INF", "ART"]),
]


# Niveles de desempeño según modelo típico del Decreto 1290
_NIVELES_DEFAULT = [
    ("Bajo",     0.0,  59.9, "Desempeño insuficiente. Requiere actividades de recuperación.", 1),
    ("Básico",   60.0, 69.9, "Desempeño mínimo esperado. Cumple parcialmente los logros.",   2),
    ("Alto",     70.0, 84.9, "Desempeño superior al básico. Cumple satisfactoriamente.",      3),
    ("Superior", 85.0, 100.0,"Desempeño sobresaliente. Supera los logros propuestos.",        4),
]

_TIPOS_ALERTAS = [
    ("faltas_injustificadas",    3.0,  True,  False, False),
    ("promedio_bajo",           55.0,  True,  False, False),
    ("materias_en_riesgo",       2.0,  True,  True,  False),
    ("plan_mejoramiento_vencido",1.0,  True,  True,  False),
    ("habilitacion_pendiente",   1.0,  True,  False, False),
]

_CATEGORIAS_EVALUACION = [
    ("Evaluaciones",  0.40),
    ("Trabajos",      0.35),
    ("Participación", 0.25),
]

# Categorías institucionales para el modo MIXTO_SUBCATEGORIAS del dev seed.
# Formato: (nombre, peso, permite_subcategorias)
# Ser + Saber + Hacer = 1.0
_CATEGORIAS_INSTITUCIONALES_DEV = [
    ("Ser",   0.10, False),  # actitudinal — fijo, sin sub-categorías
    ("Saber", 0.40, False),  # cognitivo — fijo
    ("Hacer", 0.50, True),   # procedimental — docente puede sub-categorizar
]

_HORARIOS_BASE = [
    ("Lunes",     "07:00", "07:55"),
    ("Lunes",     "07:55", "08:50"),
    ("Martes",    "07:00", "07:55"),
    ("Martes",    "07:55", "08:50"),
    ("Miércoles", "07:00", "07:55"),
    ("Miércoles", "07:55", "08:50"),
    ("Jueves",    "07:00", "07:55"),
    ("Jueves",    "07:55", "08:50"),
    ("Viernes",   "07:00", "07:55"),
    ("Viernes",   "07:55", "08:50"),
]

# Días y franjas lectivas para el constructor determinista del horario base
# completo de seed_dev. Las franjas coinciden con la plantilla "Jornada única"
# (órdenes lectivos 1,2,3,5,6,7 — el 4 es recreo).
_DIAS_LECTIVOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
_FRANJAS_LECTIVAS_DEV = [
    (1, "07:00", "07:55"), (2, "07:55", "08:50"), (3, "08:50", "09:45"),
    (5, "10:15", "11:10"), (6, "11:10", "12:05"), (7, "12:05", "13:00"),
    (8, "13:00", "13:55"),
]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_or_insert(
    conn: sqlite3.Connection,
    select_sql: str,
    select_params: tuple,
    insert_sql: str,
    insert_params: tuple,
) -> int:
    """
    Busca un registro; si no existe lo inserta.
    Retorna el id en ambos casos.
    """
    row = conn.execute(select_sql, select_params).fetchone()
    if row:
        return int(row[0])
    conn.execute(insert_sql, insert_params)
    row = conn.execute(select_sql, select_params).fetchone()
    return int(row[0])


def _nombre_aleatorio() -> tuple[str, str, str]:
    genero = random.choice(("M", "F"))
    nombre = random.choice(_NOMBRES_M if genero == "M" else _NOMBRES_F)
    apellido = f"{random.choice(_APELLIDOS)} {random.choice(_APELLIDOS)}"
    return nombre, apellido, genero


def _fecha_nacimiento(edad_min: int = 11, edad_max: int = 17) -> date:
    hoy = date.today()
    edad = random.randint(edad_min, edad_max)
    return date(hoy.year - edad, random.randint(1, 12), random.randint(1, 28))


def _celular() -> str:
    return f"3{random.randint(100_000_000, 199_999_999)}"


def _documento_ti() -> str:
    return str(random.randint(1_000_000_000, 1_099_999_999))


# ---------------------------------------------------------------------------
# Seeders atómicos — no hacen commit, reciben conn
# ---------------------------------------------------------------------------

def _seed_configuracion(conn: sqlite3.Connection, anio: int) -> int:
    """Crea o recupera la configuración del año. Retorna anio_id."""
    return _get_or_insert(
        conn,
        "SELECT id FROM configuracion_anio WHERE anio = ?", (anio,),
        """
        INSERT INTO configuracion_anio (
            anio, fecha_inicio_clases, fecha_fin_clases,
            nota_minima_aprobacion,
            nombre_institucion, activo
        ) VALUES (?, ?, ?, ?, ?, 1)
        """,
        (anio, f"{anio}-01-20", f"{anio}-12-15", 60.0, "Institución Educativa ZECI"),
    )


def _seed_configuracion_periodos(conn: sqlite3.Connection, anio_id: int) -> None:
    existing = conn.execute(
        "SELECT id FROM configuracion_periodos WHERE anio_id = ?", (anio_id,)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO configuracion_periodos (anio_id, numero_periodos, pesos_iguales) "
            "VALUES (?, 4, 1)",
            (anio_id,),
        )


def _seed_criterios_promocion(conn: sqlite3.Connection, anio_id: int) -> None:
    existing = conn.execute(
        "SELECT id FROM criterios_promocion WHERE anio_id = ?", (anio_id,)
    ).fetchone()
    if not existing:
        conn.execute(
            """
            INSERT INTO criterios_promocion (
                anio_id, max_asignaturas_perdidas, permite_condicionada,
                nota_minima_habilitacion, nota_minima_anual
            ) VALUES (?, 2, 1, 60.0, 60.0)
            """,
            (anio_id,),
        )


def _seed_niveles_desempeno(
    conn: sqlite3.Connection,
    anio_id: int,
    niveles: list[tuple] | None = None,
) -> list[int]:
    """
    Crea los niveles de desempeño para el año.
    Acepta niveles personalizados para tests.
    Retorna lista de ids creados/existentes.
    """
    datos = niveles or _NIVELES_DEFAULT
    ids = []
    for nombre, rmin, rmax, desc, orden in datos:
        nid = _get_or_insert(
            conn,
            "SELECT id FROM niveles_desempeno WHERE anio_id=? AND nombre=?",
            (anio_id, nombre),
            """
            INSERT INTO niveles_desempeno
                (anio_id, nombre, rango_min, rango_max, descripcion, orden)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (anio_id, nombre, rmin, rmax, desc, orden),
        )
        ids.append(nid)
    return ids


def _seed_alertas_config(conn: sqlite3.Connection, anio_id: int) -> None:
    for tipo, umbral, doc, dir_, acud in _TIPOS_ALERTAS:
        existing = conn.execute(
            "SELECT id FROM configuracion_alertas WHERE anio_id=? AND tipo_alerta=?",
            (anio_id, tipo),
        ).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO configuracion_alertas (
                    anio_id, tipo_alerta, umbral, activa,
                    notificar_docente, notificar_director, notificar_acudiente
                ) VALUES (?, ?, ?, 1, ?, ?, ?)
                """,
                (anio_id, tipo, umbral, int(doc), int(dir_), int(acud)),
            )


def _seed_areas(conn: sqlite3.Connection) -> dict[str, int]:
    """Retorna {nombre_area: id}."""
    area_map: dict[str, int] = {}
    for nombre, codigo, color in _AREAS:
        aid = _get_or_insert(
            conn,
            "SELECT id FROM areas_conocimiento WHERE nombre=?", (nombre,),
            "INSERT INTO areas_conocimiento (nombre, codigo, color) VALUES (?, ?, ?)",
            (nombre, codigo, color),
        )
        area_map[nombre] = aid
    return area_map


def _seed_asignaturas(
    conn: sqlite3.Connection,
    area_map: dict[str, int],
    asignaturas: list[tuple] | None = None,
) -> dict[str, int]:
    """Retorna {codigo_asignatura: id}."""
    datos = asignaturas or _ASIGNATURAS
    asig_map: dict[str, int] = {}
    for nombre, codigo, area_nombre, horas in datos:
        area_id = area_map.get(area_nombre)
        sid = _get_or_insert(
            conn,
            "SELECT id FROM asignaturas WHERE codigo=?", (codigo,),
            "INSERT INTO asignaturas (nombre, codigo, area_id, horas_semanales) VALUES (?,?,?,?)",
            (nombre, codigo, area_id, horas),
        )
        asig_map[codigo] = sid
    return asig_map


def _seed_usuarios(
    conn: sqlite3.Connection,
    usuarios: list[tuple],
    hasher: PasswordHasher,
    carga_horaria_max: int | None = None,
) -> dict[str, int]:
    """
    Retorna {usuario: id}.
    Si carga_horaria_max se provee, lo actualiza para todos los profesores.
    """
    usuario_map: dict[str, int] = {}
    for usuario, password, nombre, email, rol in usuarios:
        uid = _get_or_insert(
            conn,
            "SELECT id FROM usuarios WHERE usuario=?", (usuario,),
            """
            INSERT INTO usuarios (usuario, password_hash, nombre_completo, email, rol, activo)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (usuario, hasher(password), nombre, email, rol),
        )
        usuario_map[usuario] = uid
    # Actualizar carga_horaria_max para los profesores si se pide
    if carga_horaria_max is not None:
        for usuario, _password, _nombre, _email, rol in usuarios:
            if rol == "profesor":
                conn.execute(
                    "UPDATE usuarios SET carga_horaria_max = ? WHERE usuario = ?",
                    (carga_horaria_max, usuario),
                )
    return usuario_map


def _seed_escenarios(
    conn: sqlite3.Connection,
    anio_id: int,
) -> dict[str, int]:
    """
    Crea 'Horario base' (activo=1) y 'Plan alterno' (activo=0) para el año.
    Retorna {nombre: id}.
    """
    escenarios = [
        ("Horario base", None, 1),
        ("Plan alterno", None, 0),
    ]
    esc_map: dict[str, int] = {}
    for nombre, descripcion, activo in escenarios:
        eid = _get_or_insert(
            conn,
            "SELECT id FROM escenarios_horario WHERE anio_id=? AND nombre=?",
            (anio_id, nombre),
            """
            INSERT INTO escenarios_horario (anio_id, nombre, descripcion, activo)
            VALUES (?, ?, ?, ?)
            """,
            (anio_id, nombre, descripcion, activo),
        )
        esc_map[nombre] = eid
    return esc_map


def _seed_plantilla_franjas(conn: sqlite3.Connection) -> int:
    """
    Crea la plantilla de rejilla por defecto 'Jornada única' (UNICA, activa,
    Lunes–Viernes) con 8 franjas (7 lectivas + 1 recreo) = 35 cupos/semana.
    Retorna plantilla_id. Idempotente: si la plantilla ya existe, reutiliza su
    id y no duplica franjas.
    """
    pid = _get_or_insert(
        conn,
        "SELECT id FROM plantillas_franja WHERE nombre=?", ("Jornada única",),
        """
        INSERT INTO plantillas_franja (nombre, jornada, dias_activos, activa)
        VALUES (?, ?, ?, ?)
        """,
        (
            "Jornada única",
            "UNICA",
            "Lunes,Martes,Miércoles,Jueves,Viernes",
            1,
        ),
    )

    # Si ya tiene franjas, no volver a sembrarlas (idempotencia).
    ya = conn.execute(
        "SELECT COUNT(*) FROM franjas WHERE plantilla_id=?", (pid,)
    ).fetchone()[0]
    if ya:
        return pid

    # 7 lectivas + 1 recreo = 35 cupos/semana. Deja holgura sobre las 30 h del
    # plan de estudios para que el generador pueda resolver sin saturar grupos.
    franjas = [
        (pid, 1, "07:00", "07:55", "lectiva",  None),
        (pid, 2, "07:55", "08:50", "lectiva",  None),
        (pid, 3, "08:50", "09:45", "lectiva",  None),
        (pid, 4, "09:45", "10:15", "descanso", "Recreo"),
        (pid, 5, "10:15", "11:10", "lectiva",  None),
        (pid, 6, "11:10", "12:05", "lectiva",  None),
        (pid, 7, "12:05", "13:00", "lectiva",  None),
        (pid, 8, "13:00", "13:55", "lectiva",  None),
    ]
    conn.executemany(
        """
        INSERT INTO franjas
            (plantilla_id, orden, hora_inicio, hora_fin, tipo, etiqueta)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        franjas,
    )
    return pid


def _seed_grupos(
    conn: sqlite3.Connection,
    grupos: list[tuple],
) -> dict[str, int]:
    """Retorna {codigo_grupo: id}."""
    grupo_map: dict[str, int] = {}
    for codigo, nombre, grado, jornada, cap in grupos:
        gid = _get_or_insert(
            conn,
            "SELECT id FROM grupos WHERE codigo=?", (codigo,),
            "INSERT INTO grupos (codigo, nombre, grado, jornada, capacidad_maxima) VALUES (?,?,?,?,?)",
            (codigo, nombre, grado, jornada, cap),
        )
        grupo_map[codigo] = gid
    return grupo_map


def _seed_periodos(
    conn: sqlite3.Connection,
    anio_id: int,
    anio: int,
) -> list[int]:
    """
    Crea 4 periodos para el año. El primero queda activo, los demás inactivos.
    Retorna lista de ids en orden.
    """
    datos = [
        (1, "Período 1", f"{anio}-01-20", f"{anio}-04-11", 25.0, 1),
        (2, "Período 2", f"{anio}-04-14", f"{anio}-07-04", 25.0, 0),
        (3, "Período 3", f"{anio}-07-07", f"{anio}-10-03", 25.0, 0),
        (4, "Período 4", f"{anio}-10-06", f"{anio}-12-05", 25.0, 0),
    ]
    ids = []
    for numero, nombre, inicio, fin, peso, activo in datos:
        pid = _get_or_insert(
            conn,
            "SELECT id FROM periodos WHERE anio_id=? AND numero=?", (anio_id, numero),
            """
            INSERT INTO periodos
                (anio_id, numero, nombre, fecha_inicio, fecha_fin,
                 peso_porcentual, activo, cerrado)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (anio_id, numero, nombre, inicio, fin, peso, activo),
        )
        ids.append(pid)
    return ids


def _seed_asignaciones(
    conn: sqlite3.Connection,
    usuario_map: dict[str, int],
    asig_map: dict[str, int],
    grupo_map: dict[str, int],
    periodo_ids: list[int],
    asignaciones_data: list[tuple],
) -> list[int]:
    """
    Crea asignaciones para cada combinación docente-asignatura-grupo-periodo.
    Retorna lista de ids.
    """
    ids = []
    for prof_usuario, codigos in asignaciones_data:
        prof_id = usuario_map.get(prof_usuario)
        if not prof_id:
            continue
        for codigo in codigos:
            asignatura_id = asig_map.get(codigo)
            if not asignatura_id:
                continue
            for grupo_id in grupo_map.values():
                for periodo_id in periodo_ids:
                    aid = _get_or_insert(
                        conn,
                        """
                        SELECT id FROM asignaciones
                        WHERE usuario_id=? AND asignatura_id=? AND grupo_id=? AND periodo_id=?
                        """,
                        (prof_id, asignatura_id, grupo_id, periodo_id),
                        """
                        INSERT INTO asignaciones
                            (grupo_id, asignatura_id, usuario_id, periodo_id, activo)
                        VALUES (?, ?, ?, ?, 1)
                        """,
                        (grupo_id, asignatura_id, prof_id, periodo_id),
                    )
                    ids.append(aid)
    return ids


def _seed_horarios(
    conn: sqlite3.Connection,
    grupo_map: dict[str, int],
    periodo_ids: list[int],
    escenario_id: int,
) -> int:
    """Asigna horarios para el primer periodo de cada grupo. Retorna conteo."""
    periodo_id = periodo_ids[0]
    count = 0
    for grupo_id in grupo_map.values():
        asigs = conn.execute(
            """
            SELECT id, usuario_id, asignatura_id
            FROM asignaciones
            WHERE grupo_id=? AND periodo_id=?
            ORDER BY id
            LIMIT 10
            """,
            (grupo_id, periodo_id),
        ).fetchall()

        for idx, (dia, hora_i, hora_f) in enumerate(_HORARIOS_BASE):
            if idx >= len(asigs):
                break
            asig_id, usuario_id, asignatura_id = asigs[idx]
            existing = conn.execute(
                "SELECT id FROM horarios WHERE escenario_id=? AND grupo_id=? AND dia_semana=? AND hora_inicio=?",
                (escenario_id, grupo_id, dia, hora_i),
            ).fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO horarios
                        (grupo_id, asignatura_id, usuario_id, asignacion_id,
                         periodo_id, escenario_id, dia_semana, hora_inicio, hora_fin, sala)
                    VALUES (?,?,?,?,?,?,?,?,?,'Aula')
                    """,
                    (grupo_id, asignatura_id, usuario_id, asig_id,
                     periodo_id, escenario_id, dia, hora_i, hora_f),
                )
                count += 1
    return count


def _seed_asignaciones_desde_plan(
    conn: sqlite3.Connection,
    periodo_ids: list[int],
) -> list[int]:
    """
    Deriva las asignaciones docente-grupo-asignatura DEL PLAN DE ESTUDIOS:
    para cada grupo, cada asignatura de su grado recibe un docente, respetando
    la carga máxima (con las horas del plan). Garantiza que plan ↔ asignaciones
    ↔ carga ↔ generador queden consistentes. Idempotente por combinación.
    Retorna los ids creados/existentes.
    """
    from collections import defaultdict

    profs = conn.execute(
        "SELECT id, COALESCE(carga_horaria_max, 22) AS cap FROM usuarios "
        "WHERE rol='profesor' ORDER BY id"
    ).fetchall()
    teachers = [r["id"] for r in profs]
    cap = {r["id"]: r["cap"] for r in profs}
    if not teachers:
        return []

    grupos = conn.execute("SELECT id, grado FROM grupos WHERE grado IS NOT NULL").fetchall()
    plan_por_grado: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for r in conn.execute("SELECT grado, asignatura_id, horas_semanales FROM plan_estudios"):
        plan_por_grado[r["grado"]].append((r["asignatura_id"], r["horas_semanales"]))

    ids: list[int] = []
    for periodo_id in periodo_ids:
        carga: dict[int, int] = {t: 0 for t in teachers}
        materias_de: dict[int, set] = defaultdict(set)  # teacher -> {asignatura_id}
        # Slots a cubrir, agrupados por asignatura (para continuidad de docente).
        por_asig: dict[int, list[tuple[int, int]]] = defaultdict(list)  # aid -> [(grupo_id, horas)]
        for g in grupos:
            for (aid, horas) in plan_por_grado.get(g["grado"], []):
                por_asig[aid].append((g["id"], horas))

        for aid, slots in por_asig.items():
            for (gid, horas) in slots:
                # Preferir un docente que ya dicte esa asignatura y tenga cupo.
                cand = [t for t in teachers
                        if carga[t] + horas <= cap[t] and aid in materias_de[t]]
                if not cand:
                    cand = [t for t in teachers if carga[t] + horas <= cap[t]]
                if not cand:
                    continue  # sin cupo (no debería con la holgura del seed)
                tid = max(cand, key=lambda t: cap[t] - carga[t])
                carga[tid] += horas
                materias_de[tid].add(aid)
                cur = conn.execute(
                    """INSERT OR IGNORE INTO asignaciones
                           (grupo_id, asignatura_id, usuario_id, periodo_id, activo)
                       VALUES (?, ?, ?, ?, 1)""",
                    (gid, aid, tid, periodo_id),
                )
                if cur.lastrowid:
                    ids.append(cur.lastrowid)
    return ids


def _seed_horarios_completo(
    conn: sqlite3.Connection,
    periodo_id: int,
    escenario_id: int,
) -> int:
    """
    Construye un horario base COMPLETO y sin choques que llena las 30 franjas
    (5 días × 6 franjas lectivas) de cada grupo en el escenario dado.

    Determinista: usa backtracking (DFS) con heurística MRV sobre las lecciones
    derivadas de las asignaciones del periodo. La instancia es factible por
    construcción (cada grupo suma 30h, ningún docente excede 30h).

    Idempotente: si ya hay filas para el escenario, retorna 0 sin hacer nada.
    Retorna el número de filas insertadas.
    """
    # 1. Idempotencia
    ya = conn.execute(
        "SELECT COUNT(*) FROM horarios WHERE escenario_id=?", (escenario_id,)
    ).fetchone()[0]
    if ya:
        return 0

    # 2. Cargar asignaciones del periodo con sus horas del plan (fallback global)
    asignaciones = conn.execute(
        """
        SELECT a.id, a.grupo_id, a.usuario_id, a.asignatura_id,
               COALESCE(pe.horas_semanales, s.horas_semanales) AS horas_semanales
        FROM asignaciones a
        JOIN grupos g       ON g.id = a.grupo_id
        JOIN asignaturas s  ON s.id = a.asignatura_id
        LEFT JOIN plan_estudios pe
               ON pe.grado = g.grado AND pe.asignatura_id = a.asignatura_id
        WHERE a.periodo_id = ? AND a.activo = 1
        """,
        (periodo_id,),
    ).fetchall()

    # 3. Expandir cada asignación en `horas_semanales` lecciones
    #    Cada lección: (asignacion_id, grupo_id, usuario_id, asignatura_id)
    lecciones: list[tuple[int, int, int, int]] = []
    for asig_id, grupo_id, usuario_id, asignatura_id, horas in asignaciones:
        for _ in range(int(horas or 0)):
            lecciones.append((asig_id, grupo_id, usuario_id, asignatura_id))

    if not lecciones:
        return 0

    # 4. Slots disponibles (30 = 5 días × 6 franjas lectivas)
    slots = [
        (dia, orden, hi, hf)
        for dia in _DIAS_LECTIVOS
        for (orden, hi, hf) in _FRANJAS_LECTIVAS_DEV
    ]

    n = len(lecciones)
    n_slots = len(slots)

    # 5. Asignación de slot (color) por lección mediante coloreo propio de
    #    aristas del grafo bipartito grupo<->docente.
    #
    #    Cada lección es una arista entre su grupo y su docente. Por construcción
    #    todo grupo demanda exactamente 30 lecciones y todo docente <= 30, de modo
    #    que el grado máximo del grafo es 30 = n_slots. El teorema de König
    #    garantiza un coloreo propio de aristas con exactamente Δ colores.
    #
    #    Algoritmo (determinista y polinómico): se regulariza el grafo a uno
    #    n_slots-regular añadiendo nodos y aristas "ficticias", y se descompone
    #    en n_slots emparejamientos PERFECTOS (uno por slot) vía caminos
    #    aumentantes de Kuhn. Las aristas reales de cada emparejamiento reciben
    #    el color (slot) correspondiente. Es exacto: siempre coloca las n
    #    lecciones sin choques de grupo ni de docente.
    asignacion_slot: list[tuple | None] = [None] * n
    color_de = colorear_aristas_bipartito(
        [(grupo_id, usuario_id) for (_aid, grupo_id, usuario_id, _sid) in lecciones],
        n_slots,
    )
    for i, color in enumerate(color_de):
        if color is not None:
            asignacion_slot[i] = slots[color]

    colocadas = sum(1 for s in asignacion_slot if s is not None)
    if colocadas != n:
        raise RuntimeError(
            f"_seed_horarios_completo: no se pudo construir el horario completo "
            f"(colocadas={colocadas}, total={n})"
        )

    # 7. Insertar las lecciones colocadas
    count = 0
    for (asig_id, grupo_id, usuario_id, asignatura_id), slot in zip(
        lecciones, asignacion_slot
    ):
        dia, _orden, hi, hf = slot
        conn.execute(
            """
            INSERT INTO horarios
                (grupo_id, asignatura_id, usuario_id, asignacion_id,
                 periodo_id, escenario_id, dia_semana, hora_inicio, hora_fin, sala)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Aula')
            """,
            (grupo_id, asignatura_id, usuario_id, asig_id,
             periodo_id, escenario_id, dia, hi, hf),
        )
        count += 1

    # 8. Verificación final
    assert count == len(lecciones), (
        f"insertadas={count} != lecciones={len(lecciones)}"
    )
    return count


def _seed_estudiantes(
    conn: sqlite3.Connection,
    grupo_map: dict[str, int],
    total: int,
    rng: random.Random,
) -> list[int]:
    """
    Distribuye `total` estudiantes entre los grupos.
    Retorna lista de estudiante_ids.
    """
    ids: list[int] = []
    por_grupo = max(1, total // len(grupo_map))
    for idx_g, (codigo_grupo, grupo_id) in enumerate(grupo_map.items()):
        for i in range(por_grupo):
            nombre, apellido, genero = (
                rng.choice(_NOMBRES_M) if (g := rng.choice(("M", "F"))) == "M"
                else rng.choice(_NOMBRES_F),
                f"{rng.choice(_APELLIDOS)} {rng.choice(_APELLIDOS)}",
                g,
            )
            id_publico = f"E{codigo_grupo}{idx_g:02d}{i:03d}"
            numero_doc = str(rng.randint(1_000_000_000, 1_099_999_999))
            fecha_nac = date(
                date.today().year - rng.randint(11, 17),
                rng.randint(1, 12),
                rng.randint(1, 28),
            )
            eid = _get_or_insert(
                conn,
                "SELECT id FROM estudiantes WHERE id_publico=?", (id_publico,),
                """
                INSERT INTO estudiantes (
                    id_publico, tipo_documento, numero_documento,
                    nombre, apellido, genero,
                    grupo_id, fecha_nacimiento, estado_matricula
                ) VALUES (?, 'TI', ?, ?, ?, ?, ?, ?, 'activo')
                """,
                (id_publico, numero_doc, nombre, apellido, genero,
                 grupo_id, fecha_nac.isoformat()),
            )
            ids.append(eid)
    return ids


def _seed_acudientes(
    conn: sqlite3.Connection,
    estudiante_ids: list[int],
    rng: random.Random,
) -> list[int]:
    """
    Crea un acudiente por estudiante (padre o madre, alternando).
    Retorna lista de acudiente_ids.
    """
    ids: list[int] = []
    parentescos = ("padre", "madre")
    for i, est_id in enumerate(estudiante_ids):
        existing = conn.execute(
            "SELECT acudiente_id FROM estudiante_acudiente WHERE estudiante_id=?",
            (est_id,),
        ).fetchone()
        if existing:
            ids.append(existing[0])
            continue

        parentesco = parentescos[i % 2]
        nombre = (
            rng.choice(_NOMBRES_M) if parentesco == "padre"
            else rng.choice(_NOMBRES_F)
        )
        apellido = f"{rng.choice(_APELLIDOS)} {rng.choice(_APELLIDOS)}"
        numero_doc = str(rng.randint(10_000_000, 99_999_999))
        celular = f"3{rng.randint(100_000_000, 199_999_999)}"

        acud_id = _get_or_insert(
            conn,
            "SELECT id FROM acudientes WHERE numero_documento=?", (numero_doc,),
            """
            INSERT INTO acudientes
                (tipo_documento, numero_documento, nombre_completo,
                 parentesco, celular, activo)
            VALUES ('CC', ?, ?, ?, ?, 1)
            """,
            (numero_doc, f"{nombre} {apellido}", parentesco, celular),
        )
        # Vincular si no estaba vinculado ya
        conn.execute(
            """
            INSERT OR IGNORE INTO estudiante_acudiente
                (estudiante_id, acudiente_id, es_principal)
            VALUES (?, ?, 1)
            """,
            (est_id, acud_id),
        )
        ids.append(acud_id)
    return ids


def _seed_categorias_actividades(
    conn: sqlite3.Connection,
    asignacion_ids: list[int],
    periodo_ids: list[int],
    limite_asignaciones: int = 30,
) -> tuple[int, int, list[int]]:
    """
    Crea categorías y actividades para las primeras `limite_asignaciones` asignaciones
    del primer periodo. Retorna (n_categorias, n_actividades, actividad_ids).
    """
    cat_count = 0
    act_count = 0
    actividad_ids: list[int] = []
    periodo_id = periodo_ids[0]

    for asig_id in asignacion_ids[:limite_asignaciones]:
        for cat_nombre, peso in _CATEGORIAS_EVALUACION:
            existing_cat = conn.execute(
                "SELECT id FROM categorias WHERE nombre=? AND asignacion_id=? AND periodo_id=?",
                (cat_nombre, asig_id, periodo_id),
            ).fetchone()

            if existing_cat:
                cat_id = existing_cat[0]
            else:
                conn.execute(
                    "INSERT INTO categorias (nombre, peso, asignacion_id, periodo_id) VALUES (?,?,?,?)",
                    (cat_nombre, peso, asig_id, periodo_id),
                )
                cat_id = conn.execute(
                    "SELECT id FROM categorias WHERE nombre=? AND asignacion_id=? AND periodo_id=?",
                    (cat_nombre, asig_id, periodo_id),
                ).fetchone()[0]
                cat_count += 1

            # 2 actividades por categoría
            for num in range(1, 3):
                act_nombre = f"{cat_nombre} {num}"
                existing_act = conn.execute(
                    "SELECT id FROM actividades WHERE nombre=? AND categoria_id=?",
                    (act_nombre, cat_id),
                ).fetchone()
                if existing_act:
                    actividad_ids.append(existing_act[0])
                else:
                    fecha_act = date.today() - timedelta(days=num * 7)
                    conn.execute(
                        """
                        INSERT INTO actividades
                            (nombre, descripcion, fecha, valor_maximo, estado, categoria_id)
                        VALUES (?, ?, ?, 100.0, 'publicada', ?)
                        """,
                        (act_nombre, f"Actividad {num} de {cat_nombre}",
                         fecha_act.isoformat(), cat_id),
                    )
                    act_id = conn.execute(
                        "SELECT id FROM actividades WHERE nombre=? AND categoria_id=?",
                        (act_nombre, cat_id),
                    ).fetchone()[0]
                    actividad_ids.append(act_id)
                    act_count += 1

    return cat_count, act_count, actividad_ids


def _seed_notas(
    conn: sqlite3.Connection,
    actividad_ids: list[int],
    estudiante_ids: list[int],
    usuario_id: int,
    rng: random.Random,
) -> int:
    """Genera notas aleatorias. Retorna conteo de notas insertadas."""
    count = 0
    for act_id in actividad_ids:
        for est_id in estudiante_ids:
            existing = conn.execute(
                "SELECT id FROM notas WHERE estudiante_id=? AND actividad_id=?",
                (est_id, act_id),
            ).fetchone()
            if not existing:
                # Distribución realista: mayoría entre 55 y 95
                valor = round(rng.triangular(40.0, 100.0, 78.0), 1)
                conn.execute(
                    """
                    INSERT INTO notas (estudiante_id, actividad_id, valor, usuario_registro_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (est_id, act_id, valor, usuario_id),
                )
                count += 1
    return count


def _seed_asistencias(
    conn: sqlite3.Connection,
    estudiante_ids: list[int],
    grupo_map: dict[str, int],
    asignacion_ids: list[int],
    periodo_ids: list[int],
    usuario_id: int,
    dias_atras: int = 20,
    rng: random.Random | None = None,
) -> int:
    """
    Genera registros de asistencia para los últimos `dias_atras` días hábiles.
    Estados válidos: P, FJ, FI, R, E.
    """
    if rng is None:
        rng = random.Random()

    periodo_id = periodo_ids[0]
    grupo_id_por_est = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT id, grupo_id FROM estudiantes WHERE id IN (%s)"
            % ",".join("?" * len(estudiante_ids)),
            estudiante_ids,
        ).fetchall()
    }
    asig_por_grupo: dict[int, int] = {}
    for asig_id in asignacion_ids[:10]:
        row = conn.execute(
            "SELECT grupo_id FROM asignaciones WHERE id=?", (asig_id,)
        ).fetchone()
        if row:
            asig_por_grupo.setdefault(row[0], asig_id)

    count = 0
    hoy = date.today()
    fechas = [
        hoy - timedelta(days=d)
        for d in range(1, dias_atras + 1)
        if (hoy - timedelta(days=d)).weekday() < 5  # lunes a viernes
    ]

    for fecha in fechas:
        for est_id in estudiante_ids:
            grupo_id = grupo_id_por_est.get(est_id)
            asig_id = asig_por_grupo.get(grupo_id) if grupo_id else None
            if not grupo_id or not asig_id:
                continue

            existing = conn.execute(
                """
                SELECT id FROM control_diario
                WHERE estudiante_id=? AND grupo_id=? AND asignacion_id=? AND fecha=?
                """,
                (est_id, grupo_id, asig_id, fecha.isoformat()),
            ).fetchone()
            if existing:
                continue

            p = rng.random()
            if p < 0.87:
                estado = "P"
            elif p < 0.92:
                estado = "FI"
            elif p < 0.96:
                estado = "FJ"
            elif p < 0.98:
                estado = "R"
            else:
                estado = "E"

            conn.execute(
                """
                INSERT INTO control_diario (
                    estudiante_id, grupo_id, asignacion_id, periodo_id,
                    fecha, estado, uniforme, materiales, usuario_registro_id
                ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
                """,
                (est_id, grupo_id, asig_id, periodo_id,
                 fecha.isoformat(), estado, usuario_id),
            )
            count += 1
    return count


def _seed_observaciones(
    conn: sqlite3.Connection,
    asignacion_ids: list[int],
    estudiante_ids: list[int],
    periodo_ids: list[int],
    usuario_id: int,
) -> int:
    """Crea una observación de muestra por estudiante para las primeras asignaciones."""
    periodo_id = periodo_ids[0]
    plantillas = [
        "Muestra interés y participación activa en clase.",
        "Necesita reforzar la puntualidad en la entrega de trabajos.",
        "Excelente desempeño. Apoya a sus compañeros.",
        "Requiere acompañamiento adicional en los temas del periodo.",
        "Avances significativos con relación al periodo anterior.",
    ]
    count = 0
    for i, est_id in enumerate(estudiante_ids[:10]):
        asig_id = asignacion_ids[i % len(asignacion_ids)] if asignacion_ids else None
        if not asig_id:
            continue
        existing = conn.execute(
            "SELECT id FROM observaciones_periodo WHERE estudiante_id=? AND asignacion_id=? AND periodo_id=?",
            (est_id, asig_id, periodo_id),
        ).fetchone()
        if not existing:
            texto = plantillas[i % len(plantillas)]
            conn.execute(
                """
                INSERT INTO observaciones_periodo
                    (estudiante_id, asignacion_id, periodo_id, texto, es_publica, usuario_id)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (est_id, asig_id, periodo_id, texto, usuario_id),
            )
            count += 1
    return count


# ---------------------------------------------------------------------------
# Seeder SIEE
# ---------------------------------------------------------------------------

def _seed_configuracion_siee(
    conn: sqlite3.Connection,
    anio_id: int,
    modo: str = "mixto_subcategorias",
    porcentaje_autonomia_docente: float | None = None,
    categorias_institucionales: list[tuple] | None = None,
) -> int:
    """
    Crea o recupera la configuración SIEE del año y sus categorías institucionales.

    Args:
        conn:                         Conexión SQLite activa.
        anio_id:                      ID del año lectivo.
        modo:                         Modo SIEE ('libre', 'institucional_fijo',
                                      'mixto_subcategorias', 'mixto_autonomia').
        porcentaje_autonomia_docente: Solo para 'mixto_autonomia'.
        categorias_institucionales:   Lista de (nombre, peso, permite_subcategorias).
                                      Si None, usa _CATEGORIAS_INSTITUCIONALES_DEV.

    Returns:
        ID del registro configuracion_siee.
    """
    # Upsert configuración SIEE
    existing = conn.execute(
        "SELECT id FROM configuracion_siee WHERE anio_id = ?", (anio_id,)
    ).fetchone()

    if existing:
        siee_id = existing[0]
        conn.execute(
            """
            UPDATE configuracion_siee
               SET modo = ?, porcentaje_autonomia_docente = ?
             WHERE id = ?
            """,
            (modo, porcentaje_autonomia_docente, siee_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO configuracion_siee
                (anio_id, modo, porcentaje_autonomia_docente)
            VALUES (?, ?, ?)
            """,
            (anio_id, modo, porcentaje_autonomia_docente),
        )
        siee_id = conn.execute(
            "SELECT id FROM configuracion_siee WHERE anio_id = ?", (anio_id,)
        ).fetchone()[0]

    # Categorías institucionales
    cats = categorias_institucionales or _CATEGORIAS_INSTITUCIONALES_DEV
    for nombre, peso, permite_sub in cats:
        existing_cat = conn.execute(
            "SELECT id FROM categorias WHERE nombre = ? AND anio_id = ? AND es_institucional = 1",
            (nombre, anio_id),
        ).fetchone()
        if not existing_cat:
            conn.execute(
                """
                INSERT INTO categorias
                    (nombre, peso, anio_id, es_institucional, permite_subcategorias)
                VALUES (?, ?, ?, 1, ?)
                """,
                (nombre, peso, anio_id, int(permite_sub)),
            )

    return siee_id


# ---------------------------------------------------------------------------
# Seeder config_generacion (paso_15b)
# ---------------------------------------------------------------------------

def _seed_config_generacion(
    conn: sqlite3.Connection,
    periodo_id: int,
    anio_id: int,
    plantilla_id: int,
) -> int:
    """
    Crea una config_generacion de nombre 'Config inicial' en estado 'borrador'.
    Idempotente: si ya existe por nombre, no la duplica.
    Retorna el id creado o existente.
    """
    import json as _json
    existing = conn.execute(
        "SELECT id FROM config_generacion WHERE nombre = ?", ("Config inicial",)
    ).fetchone()
    if existing:
        return int(existing[0])
    conn.execute(
        """
        INSERT INTO config_generacion
            (nombre, periodo_id, anio_id, plantilla_id, estado,
             grupos_json, pesos_json, escenario_destino_id)
        VALUES (?, ?, ?, ?, 'borrador', '[]', ?, NULL)
        """,
        (
            "Config inicial",
            periodo_id,
            anio_id,
            plantilla_id,
            _json.dumps({"huecos": 1.0, "distribucion": 1.0, "compactacion": 0.5}),
        ),
    )
    row = conn.execute(
        "SELECT id FROM config_generacion WHERE nombre = ?", ("Config inicial",)
    ).fetchone()
    return int(row[0])


# ---------------------------------------------------------------------------
# Plan de estudios (paso_19)
# ---------------------------------------------------------------------------

# Plan de estudios realista por banda de grado (suma 30 h/semana, que caben en
# los 30 cupos lectivos de la plantilla "Jornada única": 6 franjas × 5 días).
# (codigo_asignatura, horas_semanales)
_PLAN_BASICA = [  # grados 6–9
    ("MAT", 5), ("LEN", 5), ("CNT", 4), ("CSO", 4), ("ING", 3),
    ("EDF", 2), ("ART", 2), ("TEC", 2), ("ETI", 1), ("REL", 1), ("INF", 1),
]
_PLAN_MEDIA = [   # grados 10–11
    ("MAT", 4), ("LEN", 4), ("BIO", 2), ("QUI", 3), ("FIS", 3), ("CSO", 3),
    ("FIL", 2), ("ING", 3), ("EDF", 2), ("TEC", 1), ("ETI", 1), ("REL", 1),
    ("EST", 1),
]


def _plan_para_grado(grado: int) -> list[tuple]:
    return _PLAN_MEDIA if grado >= 10 else _PLAN_BASICA


def _seed_plan_estudios(
    conn: sqlite3.Connection,
    asignatura_ids: dict[str, int],
    grados: list[int],
    asignaturas: list[tuple] | None = None,
) -> int:
    """
    Inserta filas de plan_estudios (grado × asignatura → horas_semanales).

    - En modo test (`asignaturas` dado), usa las horas globales de esas materias.
    - En desarrollo, usa un plan realista por banda de grado (~30 h/semana),
      no todas las asignaturas en todos los grados.
    Idempotente vía INSERT OR IGNORE. Retorna el número de filas insertadas.
    """
    count = 0
    for grado in grados:
        if asignaturas is not None:
            filas = [(codigo, horas) for _n, codigo, _a, horas in asignaturas]
        else:
            filas = _plan_para_grado(grado)
        for codigo, horas in filas:
            asig_id = asignatura_ids.get(codigo)
            if asig_id is None:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO plan_estudios (grado, asignatura_id, horas_semanales) VALUES (?, ?, ?)",
                (grado, asig_id, horas),
            )
            count += cur.rowcount
    return count


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def seed_base(
    conn: sqlite3.Connection,
    anio: int | None = None,
    hasher: PasswordHasher = _default_hasher,
) -> SeedResult:
    """
    Datos mínimos obligatorios. Seguro en producción.

    Crea:
      - configuracion_anio + configuracion_periodos + criterios_promocion
      - niveles_desempeno (Bajo / Básico / Alto / Superior)
      - areas_conocimiento
      - configuracion_alertas por defecto
      - Usuario admin
    """
    from datetime import datetime
    anio = anio or datetime.now().year
    result = SeedResult()

    result.anio_id = _seed_configuracion(conn, anio)
    _seed_configuracion_periodos(conn, result.anio_id)
    _seed_criterios_promocion(conn, result.anio_id)
    result.nivel_ids = _seed_niveles_desempeno(conn, result.anio_id)
    _seed_alertas_config(conn, result.anio_id)
    result.area_ids = _seed_areas(conn)
    result.usuario_ids = _seed_usuarios(conn, _USUARIOS_BASE, hasher)

    result.counts = {
        "niveles_desempeno": len(result.nivel_ids),
        "areas_conocimiento": len(result.area_ids),
        "usuarios_base": len(result.usuario_ids),
    }
    result.log_resumen()
    return result


def seed_siee(
    conn: sqlite3.Connection,
    anio_id: int,
    modo: str = "mixto_subcategorias",
    porcentaje_autonomia_docente: float | None = None,
    categorias_institucionales: list[tuple] | None = None,
) -> None:
    """
    Configura el SIEE para un año lectivo ya existente.

    Separado de seed_base para que sea explícito: la instalación base arranca
    en modo 'libre' (sin restricciones) y el admin activa el SIEE cuando lo
    decide. En desarrollo se llama desde seed_dev con modo mixto_subcategorias.

    Args:
        conn:                         Conexión SQLite activa.
        anio_id:                      ID del año lectivo.
        modo:                         Modo SIEE.
        porcentaje_autonomia_docente: Solo para 'mixto_autonomia'.
        categorias_institucionales:   Lista de (nombre, peso, permite_subcategorias).
    """
    _seed_configuracion_siee(
        conn, anio_id, modo, porcentaje_autonomia_docente, categorias_institucionales
    )


def seed_dev(
    conn: sqlite3.Connection,
    anio: int | None = None,
    hasher: PasswordHasher = _default_hasher,
    total_estudiantes: int = 336,
    seed_random: int | None = None,
) -> SeedResult:
    """
    Dataset completo para desarrollo.

    Extiende seed_base con grupos, profesores, estudiantes, asignaciones,
    horarios, categorías, actividades, notas, asistencias y observaciones.

    Args:
        conn: Conexión SQLite activa.
        anio: Año lectivo. Por defecto el año en curso.
        hasher: Función de hash de contraseñas.
        total_estudiantes: Total de estudiantes a distribuir entre los grupos.
        seed_random: Semilla para reproducibilidad (útil en CI).
    """
    rng = random.Random(seed_random)

    result = seed_base(conn, anio, hasher)

    todos_usuarios = _USUARIOS_BASE + _USUARIOS_DEV
    result.usuario_ids = _seed_usuarios(conn, todos_usuarios, hasher, carga_horaria_max=22)

    # Ejemplo de docente de media jornada (deja holgura total de capacidad sobre
    # la demanda del plan, para que la derivación de asignaciones cubra todo).
    conn.execute("UPDATE usuarios SET carga_horaria_max=16 WHERE usuario='mrojas'")

    result.asignatura_ids = _seed_asignaturas(conn, result.area_ids)
    _seed_plan_estudios(conn, result.asignatura_ids, list(range(6, 12)))

    # Grados ofrecidos (6–11): rango de estudiantes (norma) + 30 h objetivo.
    _GRADOS_DEV = [
        (6, "Sexto"), (7, "Séptimo"), (8, "Octavo"),
        (9, "Noveno"), (10, "Décimo"), (11, "Once"),
    ]
    for numero, nombre in _GRADOS_DEV:
        conn.execute(
            """INSERT OR IGNORE INTO grados
                   (numero, nombre, min_estudiantes, max_estudiantes, horas_semanales)
               VALUES (?, ?, 20, 40, 30)""",
            (numero, nombre),
        )

    grupo_map = _seed_grupos(conn, _GRUPOS_DEV)
    result.grupo_ids = list(grupo_map.values())

    result.periodo_ids = _seed_periodos(
        conn, result.anio_id, anio or __import__("datetime").datetime.now().year
    )

    # Asignaciones derivadas del plan de estudios (consistentes con el plan,
    # la carga docente y el generador). Reemplaza el plan docente manual.
    result.asignacion_ids = _seed_asignaciones_desde_plan(conn, result.periodo_ids)

    esc_map = _seed_escenarios(conn, result.anio_id)
    escenario_activo_id = esc_map["Horario base"]
    horarios_count = _seed_horarios_completo(
        conn, result.periodo_ids[0], escenario_activo_id
    )

    dev_plantilla_id = _seed_plantilla_franjas(conn)
    _seed_config_generacion(
        conn,
        periodo_id=result.periodo_ids[0],
        anio_id=result.anio_id,
        plantilla_id=dev_plantilla_id,
    )

    result.estudiante_ids = _seed_estudiantes(
        conn, grupo_map, total_estudiantes, rng
    )

    result.acudiente_ids = _seed_acudientes(conn, result.estudiante_ids, rng)

    n_cats, n_acts, actividad_ids = _seed_categorias_actividades(
        conn, result.asignacion_ids, result.periodo_ids
    )

    prof_id = result.usuario_ids.get("rgomez", 1)
    n_notas = _seed_notas(
        conn, actividad_ids, result.estudiante_ids, prof_id, rng
    )

    n_asist = _seed_asistencias(
        conn,
        result.estudiante_ids,
        grupo_map,
        result.asignacion_ids,
        result.periodo_ids,
        prof_id,
        rng=rng,
    )

    n_obs = _seed_observaciones(
        conn,
        result.asignacion_ids,
        result.estudiante_ids,
        result.periodo_ids,
        prof_id,
    )

    # Configuración SIEE: modo mixto_subcategorias con las categorías Ser/Saber/Hacer
    _seed_configuracion_siee(conn, result.anio_id, modo="mixto_subcategorias")

    # Salas especiales compartidas (paso_17)
    _SALAS_ESPECIALES = [
        ("Laboratorio de Ciencias", "laboratorio", 30),
        ("Sala de Cómputo", "computo", 25),
        ("Cancha Polideportiva", "ed_fisica", 100),
    ]
    for nombre_sala, tipo_sala, cap_sala in _SALAS_ESPECIALES:
        conn.execute(
            "INSERT OR IGNORE INTO salas (nombre, tipo, capacidad) VALUES (?, ?, ?)",
            (nombre_sala, tipo_sala, cap_sala),
        )

    # Aula propia (salón base) por grupo: una por grupo, nombrada por su código.
    # Así el visualizador muestra un aula real para cada clase normal.
    for codigo, gid in grupo_map.items():
        conn.execute(
            "INSERT OR IGNORE INTO salas (nombre, tipo, capacidad) VALUES (?, 'aula', 40)",
            (f"Aula {codigo}",),
        )
        srow = conn.execute(
            "SELECT id FROM salas WHERE nombre = ?", (f"Aula {codigo}",)
        ).fetchone()
        if srow:
            conn.execute(
                "UPDATE grupos SET sala_id = ? WHERE id = ?", (srow[0], gid)
            )

    # Nota: NO se siembran límites diarios por docente por defecto. Imponer un
    # tope/mínimo diario a todos desactiva el coloreo óptimo (König) y obliga al
    # motor a empaquetar por backtracking, dejando lecciones sin colocar. Los
    # límites son opt-in: se configuran por docente cuando se necesitan.

    result.counts.update({
        "usuarios_total":     len(result.usuario_ids),
        "grupos":             len(result.grupo_ids),
        "asignaturas":        len(result.asignatura_ids),
        "periodos":           len(result.periodo_ids),
        "asignaciones":       len(result.asignacion_ids),
        "horarios":           horarios_count,
        "estudiantes":        len(result.estudiante_ids),
        "acudientes":         len(result.acudiente_ids),
        "categorias":         n_cats,
        "actividades":        n_acts,
        "notas":              n_notas,
        "asistencias":        n_asist,
        "observaciones":      n_obs,
    })
    result.log_resumen()
    return result


def seed_test(
    conn: sqlite3.Connection,
    anio: int = 2025,
    hasher: PasswordHasher = _fast_hasher,
) -> SeedResult:
    """
    Dataset mínimo y determinista para tests de integración.

    - 1 grupo, 1 periodo activo, 3 estudiantes, 2 profesores
    - 1 asignatura, 1 asignacion, 1 categoria, 2 actividades
    - Notas y asistencias para los 3 estudiantes
    - Sin randomización (seed fijo)

    Siempre recibe una conexión explícita. No hace commit.
    """
    result = SeedResult()
    rng = random.Random(42)  # determinista

    result.anio_id = _seed_configuracion(conn, anio)
    _seed_configuracion_periodos(conn, result.anio_id)
    _seed_criterios_promocion(conn, result.anio_id)
    result.nivel_ids = _seed_niveles_desempeno(conn, result.anio_id)
    _seed_alertas_config(conn, result.anio_id)
    result.area_ids = _seed_areas(conn)

    usuarios_test = [
        ("admin_test",   "pass", "Admin Test",    "admin@test.co",   "admin"),
        ("prof_test",    "pass", "Profesor Test", "prof@test.co",    "profesor"),
        ("director_test","pass", "Director Test", "dir@test.co",     "director"),
    ]
    result.usuario_ids = _seed_usuarios(conn, usuarios_test, hasher)

    result.asignatura_ids = _seed_asignaturas(
        conn,
        result.area_ids,
        [("Matemáticas Test", "MAT_T", "Matemáticas", 4)],
    )
    _seed_plan_estudios(
        conn, result.asignatura_ids, [6],
        [("Matemáticas Test", "MAT_T", "Matemáticas", 4)],
    )

    grupo_map = _seed_grupos(conn, [("T01", "Test A", 6, "AM", 30)])
    result.grupo_ids = list(grupo_map.values())

    result.periodo_ids = _seed_periodos(conn, result.anio_id, anio)

    result.asignacion_ids = _seed_asignaciones(
        conn,
        result.usuario_ids,
        result.asignatura_ids,
        grupo_map,
        result.periodo_ids,
        [("prof_test", ["MAT_T"])],
    )

    esc_map_test = _seed_escenarios(conn, result.anio_id)
    escenario_activo_id_test = esc_map_test["Horario base"]
    _seed_horarios(conn, grupo_map, result.periodo_ids, escenario_activo_id_test)

    # 3 estudiantes con datos fijos y predecibles
    est_ids = []
    for i, (nombre, apellido) in enumerate([
        ("Ana", "García"), ("Luis", "López"), ("María", "Pérez")
    ]):
        eid = _get_or_insert(
            conn,
            "SELECT id FROM estudiantes WHERE id_publico=?", (f"TEST{i:03d}",),
            """
            INSERT INTO estudiantes (
                id_publico, tipo_documento, numero_documento,
                nombre, apellido, genero, grupo_id,
                fecha_nacimiento, estado_matricula
            ) VALUES (?, 'TI', ?, ?, ?, 'F', ?, '2010-06-15', 'activo')
            """,
            (f"TEST{i:03d}", f"100000000{i}", nombre, apellido,
             list(grupo_map.values())[0]),
        )
        est_ids.append(eid)
    result.estudiante_ids = est_ids

    n_cats, n_acts, actividad_ids = _seed_categorias_actividades(
        conn, result.asignacion_ids, result.periodo_ids
    )
    prof_id = result.usuario_ids["prof_test"]
    n_notas = _seed_notas(conn, actividad_ids, est_ids, prof_id, rng)

    plantilla_id = _seed_plantilla_franjas(conn)
    _seed_config_generacion(
        conn,
        periodo_id=result.periodo_ids[0],
        anio_id=result.anio_id,
        plantilla_id=plantilla_id,
    )

    # Sala mínima para tests paso_17
    conn.execute(
        "INSERT OR IGNORE INTO salas (id, nombre, tipo, capacidad) VALUES (1, 'Aula Test', 'aula', 40)"
    )

    result.counts = {
        "usuarios":    len(result.usuario_ids),
        "grupos":      1,
        "periodos":    len(result.periodo_ids),
        "asignaciones":len(result.asignacion_ids),
        "estudiantes": len(est_ids),
        "actividades": n_acts,
        "notas":       n_notas,
    }
    return result


__all__ = [
    "seed_base",
    "seed_dev",
    "seed_test",
    "seed_siee",
    "SeedResult",
    "_fast_hasher",
    "_default_hasher",
    "_seed_config_generacion",
]