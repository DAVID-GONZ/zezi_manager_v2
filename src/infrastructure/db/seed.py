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

_AREAS = [
    ("Ciencias Naturales y Educación Ambiental", "CNAT"),
    ("Ciencias Sociales",                        "CSOC"),
    ("Educación Artística y Cultural",            "ARTE"),
    ("Educación Ética y en Valores Humanos",      "ETIC"),
    ("Educación Física, Recreación y Deportes",   "EFIS"),
    ("Educación Religiosa",                       "RELI"),
    ("Humanidades, Lengua Castellana e Idiomas",  "HUMA"),
    ("Matemáticas",                               "MATE"),
    ("Tecnología e Informática",                  "TINF"),
    ("Filosofía",                                 "FILO"),
]

# (nombre, codigo, area_nombre, horas_semanales)
_ASIGNATURAS = [
    ("Ciencias Naturales",   "CNT", "Ciencias Naturales y Educación Ambiental", 3),
    ("Biología",             "BIO", "Ciencias Naturales y Educación Ambiental", 3),
    ("Química",              "QUI", "Ciencias Naturales y Educación Ambiental", 3),
    ("Física",               "FIS", "Ciencias Naturales y Educación Ambiental", 3),
    ("Ciencias Sociales",    "CSO", "Ciencias Sociales",                        3),
    ("Historia",             "HIS", "Ciencias Sociales",                        2),
    ("Geografía",            "GEO", "Ciencias Sociales",                        2),
    ("Artística",            "ART", "Educación Artística y Cultural",            2),
    ("Ética",                "ETI", "Educación Ética y en Valores Humanos",      1),
    ("Educación Física",     "EDF", "Educación Física, Recreación y Deportes",  2),
    ("Religión",             "REL", "Educación Religiosa",                       1),
    ("Lengua Castellana",    "LEN", "Humanidades, Lengua Castellana e Idiomas", 4),
    ("Inglés",               "ING", "Humanidades, Lengua Castellana e Idiomas", 3),
    ("Francés",              "FRA", "Humanidades, Lengua Castellana e Idiomas", 2),
    ("Matemáticas",          "MAT", "Matemáticas",                              4),
    ("Estadística",          "EST", "Matemáticas",                              2),
    ("Tecnología",           "TEC", "Tecnología e Informática",                 2),
    ("Informática",          "INF", "Tecnología e Informática",                 2),
    ("Filosofía",            "FIL", "Filosofía",                                2),
]

# (codigo, nombre, grado, jornada, capacidad)
_GRUPOS_DEV = [
    ("601", "Sexto A",   6,  "AM", 35),
    ("701", "Séptimo A", 7,  "AM", 35),
    ("801", "Octavo A",  8,  "AM", 35),
    ("901", "Noveno A",  9,  "AM", 40),
    ("1001","Décimo A",  10, "AM", 40),
    ("1101","Once A",    11, "AM", 40),
]

# (usuario, password, nombre_completo, email, rol)
_USUARIOS_BASE = [
    ("admin",       "Admin2025*",    "Carlos Alberto Administrador", "admin@zeci.edu.co",       "admin"),
]

_USUARIOS_DEV = [
    ("director",    "Director2025*", "María Elena Directora",        "director@zeci.edu.co",    "director"),
    ("coordinador", "Coord2025*",    "Jorge Iván Coordinador",       "coordinador@zeci.edu.co", "coordinador"),
    ("lopez",       "Lopez2025*",    "Carlos López García",          "c.lopez@zeci.edu.co",     "profesor"),
    ("garcia",      "Garcia2025*",   "Ana García Pérez",             "a.garcia@zeci.edu.co",    "profesor"),
    ("martin",      "Martin2025*",   "Juan Martín Ruiz",             "j.martin@zeci.edu.co",    "profesor"),
    ("rodriguez",   "Rodriguez2025*","Sofía Rodríguez Torres",       "s.rodriguez@zeci.edu.co", "profesor"),
    ("gomez",       "Gomez2025*",    "Pedro Gómez Vargas",           "p.gomez@zeci.edu.co",     "profesor"),
    ("torres",      "Torres2025*",   "Andrea Torres López",          "a.torres@zeci.edu.co",    "profesor"),
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
    for nombre, codigo in _AREAS:
        aid = _get_or_insert(
            conn,
            "SELECT id FROM areas_conocimiento WHERE nombre=?", (nombre,),
            "INSERT INTO areas_conocimiento (nombre, codigo) VALUES (?, ?)",
            (nombre, codigo),
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
) -> dict[str, int]:
    """Retorna {usuario: id}."""
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
    return usuario_map


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
                "SELECT id FROM horarios WHERE grupo_id=? AND dia_semana=? AND hora_inicio=? AND periodo_id=?",
                (grupo_id, dia, hora_i, periodo_id),
            ).fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO horarios
                        (grupo_id, asignatura_id, usuario_id, asignacion_id,
                         periodo_id, dia_semana, hora_inicio, hora_fin, sala)
                    VALUES (?,?,?,?,?,?,?,?,'Aula')
                    """,
                    (grupo_id, asignatura_id, usuario_id, asig_id,
                     periodo_id, dia, hora_i, hora_f),
                )
                count += 1
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


def seed_dev(
    conn: sqlite3.Connection,
    anio: int | None = None,
    hasher: PasswordHasher = _default_hasher,
    total_estudiantes: int = 60,
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
    result.usuario_ids = _seed_usuarios(conn, todos_usuarios, hasher)

    result.asignatura_ids = _seed_asignaturas(conn, result.area_ids)

    grupo_map = _seed_grupos(conn, _GRUPOS_DEV)
    result.grupo_ids = list(grupo_map.values())

    result.periodo_ids = _seed_periodos(
        conn, result.anio_id, anio or __import__("datetime").datetime.now().year
    )

    result.asignacion_ids = _seed_asignaciones(
        conn,
        result.usuario_ids,
        result.asignatura_ids,
        grupo_map,
        result.periodo_ids,
        _ASIGNACIONES_DEV,
    )

    horarios_count = _seed_horarios(conn, grupo_map, result.periodo_ids)

    result.estudiante_ids = _seed_estudiantes(
        conn, grupo_map, total_estudiantes, rng
    )

    result.acudiente_ids = _seed_acudientes(conn, result.estudiante_ids, rng)

    n_cats, n_acts, actividad_ids = _seed_categorias_actividades(
        conn, result.asignacion_ids, result.periodo_ids
    )

    prof_id = result.usuario_ids.get("lopez", 1)
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
    "SeedResult",
    "_fast_hasher",
    "_default_hasher",
]