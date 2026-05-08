"""
Schema de base de datos — ZECI Manager v2.0
============================================
Todas las tablas siguen el orden de dependencias FK:
una tabla solo aparece después de las tablas a las que referencia.

Módulos:
  1.  Configuración institucional
  2.  Infraestructura académica
  3.  Usuarios y acudientes
  4.  Periodos y asignaciones
  5.  Evaluación
  6.  Cierres y promoción
  7.  Habilitaciones y mejoramiento
  8.  Asistencia y convivencia
  9.  Alertas
  10. Informes y PIAR
  11. Auditoría
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger("DB.SCHEMA")


# =============================================================================
# TABLAS
# =============================================================================

SCHEMA: list[str] = [

    # -------------------------------------------------------------------------
    # 1. CONFIGURACIÓN INSTITUCIONAL
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS configuracion_anio (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        anio                    INTEGER UNIQUE NOT NULL,
        fecha_inicio_clases     DATE,
        fecha_fin_clases        DATE,

        -- Datos institucionales (para boletines e informes)
        nombre_institucion      TEXT    NOT NULL DEFAULT 'Institución Educativa',
        dane_code               TEXT,
        rector                  TEXT,
        direccion               TEXT,
        municipio               TEXT,
        telefono_institucion    TEXT,
        logo_path               TEXT,
        resolucion_aprobacion   TEXT,

        -- Reglas académicas base
        nota_minima_aprobacion  REAL    NOT NULL DEFAULT 60.0
                                CHECK(nota_minima_aprobacion >= 0
                                  AND nota_minima_aprobacion <= 100),

        activo                  BOOLEAN NOT NULL DEFAULT 1
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS niveles_desempeno (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        anio_id     INTEGER NOT NULL,
        nombre      TEXT    NOT NULL,
        rango_min   REAL    NOT NULL CHECK(rango_min >= 0 AND rango_min < 100),
        rango_max   REAL    NOT NULL CHECK(rango_max > 0  AND rango_max <= 100),
        descripcion TEXT,
        orden       INTEGER NOT NULL DEFAULT 0,

        UNIQUE(anio_id, nombre),
        UNIQUE(anio_id, orden),
        CHECK(rango_min < rango_max),
        FOREIGN KEY(anio_id) REFERENCES configuracion_anio(id) ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS configuracion_periodos (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        anio_id         INTEGER NOT NULL UNIQUE,
        numero_periodos INTEGER NOT NULL DEFAULT 4
                        CHECK(numero_periodos BETWEEN 2 AND 6),
        pesos_iguales   BOOLEAN NOT NULL DEFAULT 1,

        FOREIGN KEY(anio_id) REFERENCES configuracion_anio(id) ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS criterios_promocion (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        anio_id                     INTEGER NOT NULL UNIQUE,
        max_asignaturas_perdidas    INTEGER NOT NULL DEFAULT 2,
        permite_condicionada        BOOLEAN NOT NULL DEFAULT 1,
        nota_minima_habilitacion    REAL    NOT NULL DEFAULT 60.0
                                    CHECK(nota_minima_habilitacion >= 0
                                      AND nota_minima_habilitacion <= 100),
        nota_minima_anual           REAL    NOT NULL DEFAULT 60.0
                                    CHECK(nota_minima_anual >= 0
                                      AND nota_minima_anual <= 100),

        FOREIGN KEY(anio_id) REFERENCES configuracion_anio(id) ON DELETE CASCADE
    )
    """,

    # -------------------------------------------------------------------------
    # 2. INFRAESTRUCTURA ACADÉMICA
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS areas_conocimiento (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre  TEXT    NOT NULL UNIQUE,
        codigo  TEXT    UNIQUE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS asignaturas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT    NOT NULL UNIQUE,
        codigo          TEXT    UNIQUE,
        area_id         INTEGER,
        horas_semanales INTEGER NOT NULL DEFAULT 1 CHECK(horas_semanales > 0),

        FOREIGN KEY(area_id) REFERENCES areas_conocimiento(id) ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS grupos (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo           TEXT    NOT NULL UNIQUE,
        nombre           TEXT,
        grado            INTEGER CHECK(grado BETWEEN 1 AND 13),
        jornada          TEXT    NOT NULL DEFAULT 'UNICA'
                         CHECK(jornada IN ('AM', 'PM', 'UNICA')),
        capacidad_maxima INTEGER NOT NULL DEFAULT 40 CHECK(capacidad_maxima > 0)
    )
    """,

    # -------------------------------------------------------------------------
    # 3. USUARIOS Y ACUDIENTES
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario          TEXT    NOT NULL UNIQUE,
        password_hash    TEXT    NOT NULL,
        nombre_completo  TEXT    NOT NULL,
        email            TEXT,
        telefono         TEXT,
        rol              TEXT    NOT NULL
                         CHECK(rol IN ('admin', 'director', 'coordinador',
                                       'profesor', 'estudiante', 'apoderado')),
        activo           BOOLEAN NOT NULL DEFAULT 1,
        fecha_creacion   DATE    NOT NULL DEFAULT CURRENT_DATE,
        ultima_sesion    DATETIME
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS acudientes (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_documento    TEXT    NOT NULL DEFAULT 'CC'
                          CHECK(tipo_documento IN ('CC', 'CE', 'TI', 'PASAPORTE')),
        numero_documento  TEXT    NOT NULL UNIQUE,
        nombre_completo   TEXT    NOT NULL,
        parentesco        TEXT    NOT NULL
                          CHECK(parentesco IN ('padre', 'madre', 'abuelo', 'abuela',
                                               'tio', 'tia', 'hermano', 'hermana',
                                               'tutor_legal', 'otro')),
        celular           TEXT,
        email             TEXT,
        direccion         TEXT,
        activo            BOOLEAN NOT NULL DEFAULT 1,

        -- Nullable: solo si tiene acceso al portal de acudientes (v3.0)
        usuario_id        INTEGER UNIQUE,

        FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS estudiantes (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        id_publico        TEXT    UNIQUE,
        tipo_documento    TEXT    NOT NULL DEFAULT 'TI'
                          CHECK(tipo_documento IN ('TI', 'CC', 'CE', 'NUIP')),
        numero_documento  TEXT    NOT NULL UNIQUE,
        nombre            TEXT    NOT NULL,
        apellido          TEXT    NOT NULL,
        genero            TEXT    CHECK(genero IN ('M', 'F', 'OTRO')),
        grupo_id          INTEGER,
        posee_piar        BOOLEAN NOT NULL DEFAULT 0,
        fecha_nacimiento  DATE,
        direccion         TEXT,
        fecha_ingreso     DATE    NOT NULL DEFAULT CURRENT_DATE,
        estado_matricula  TEXT    NOT NULL DEFAULT 'activo'
                          CHECK(estado_matricula IN ('activo', 'inactivo',
                                                     'retirado', 'graduado')),

        FOREIGN KEY(grupo_id) REFERENCES grupos(id) ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS estudiante_acudiente (
        estudiante_id  INTEGER NOT NULL,
        acudiente_id   INTEGER NOT NULL,
        es_principal   BOOLEAN NOT NULL DEFAULT 0,

        PRIMARY KEY(estudiante_id, acudiente_id),
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
        FOREIGN KEY(acudiente_id)  REFERENCES acudientes(id)  ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS historial_estudiantes (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        grupo_origen_id     INTEGER,
        grupo_destino_id    INTEGER,
        fecha_movimiento    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        tipo_movimiento     TEXT     NOT NULL
                            CHECK(tipo_movimiento IN ('TRASLADO', 'RETIRO',
                                                      'REINGRESO', 'GRADUACION')),
        motivo              TEXT,
        usuario_registro_id INTEGER,

        FOREIGN KEY(estudiante_id)       REFERENCES estudiantes(id) ON DELETE CASCADE,
        FOREIGN KEY(grupo_origen_id)     REFERENCES grupos(id)      ON DELETE SET NULL,
        FOREIGN KEY(grupo_destino_id)    REFERENCES grupos(id)      ON DELETE SET NULL,
        FOREIGN KEY(usuario_registro_id) REFERENCES usuarios(id)    ON DELETE SET NULL
    )
    """,

    # -------------------------------------------------------------------------
    # 4. PERIODOS Y ASIGNACIONES
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS periodos (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        anio_id             INTEGER NOT NULL,
        nombre              TEXT    NOT NULL,
        numero              INTEGER NOT NULL CHECK(numero >= 1),
        fecha_inicio        DATE,
        fecha_fin           DATE,
        peso_porcentual     REAL    NOT NULL DEFAULT 25.0
                            CHECK(peso_porcentual > 0 AND peso_porcentual <= 100),
        activo              BOOLEAN NOT NULL DEFAULT 1,
        cerrado             BOOLEAN NOT NULL DEFAULT 0,
        fecha_cierre_real   DATETIME,

        UNIQUE(anio_id, nombre),
        UNIQUE(anio_id, numero),
        CHECK(fecha_inicio IS NULL OR fecha_fin IS NULL OR fecha_inicio <= fecha_fin),
        FOREIGN KEY(anio_id) REFERENCES configuracion_anio(id) ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS hitos_periodo (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        periodo_id  INTEGER NOT NULL,
        tipo        TEXT    NOT NULL DEFAULT 'general'
                    CHECK(tipo IN ('entrega_notas', 'inicio_habilitaciones',
                                   'fin_habilitaciones', 'entrega_boletines',
                                   'general')),
        descripcion TEXT,
        fecha_limite DATE,

        FOREIGN KEY(periodo_id) REFERENCES periodos(id) ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS asignaciones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        grupo_id        INTEGER NOT NULL,
        asignatura_id   INTEGER NOT NULL,
        usuario_id      INTEGER NOT NULL,
        periodo_id      INTEGER NOT NULL,
        activo          BOOLEAN NOT NULL DEFAULT 1,

        UNIQUE(grupo_id, asignatura_id, usuario_id, periodo_id),
        FOREIGN KEY(grupo_id)      REFERENCES grupos(id)      ON DELETE CASCADE,
        FOREIGN KEY(asignatura_id) REFERENCES asignaturas(id) ON DELETE CASCADE,
        FOREIGN KEY(usuario_id)    REFERENCES usuarios(id)    ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)    REFERENCES periodos(id)    ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS logros (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        asignacion_id   INTEGER NOT NULL,
        periodo_id      INTEGER NOT NULL,
        descripcion     TEXT    NOT NULL,
        orden           INTEGER NOT NULL DEFAULT 0,

        FOREIGN KEY(asignacion_id) REFERENCES asignaciones(id) ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)    REFERENCES periodos(id)     ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS horarios (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        grupo_id        INTEGER NOT NULL,
        asignatura_id   INTEGER NOT NULL,
        usuario_id      INTEGER NOT NULL,
        asignacion_id   INTEGER,
        periodo_id      INTEGER NOT NULL,
        dia_semana      TEXT    NOT NULL
                        CHECK(dia_semana IN ('Lunes', 'Martes', 'Miércoles',
                                             'Jueves', 'Viernes', 'Sábado')),
        hora_inicio     TIME    NOT NULL,
        hora_fin        TIME    NOT NULL,
        sala            TEXT    NOT NULL DEFAULT 'Aula',

        UNIQUE(grupo_id, dia_semana, hora_inicio, periodo_id),
        CHECK(hora_inicio < hora_fin),
        FOREIGN KEY(grupo_id)      REFERENCES grupos(id)       ON DELETE CASCADE,
        FOREIGN KEY(asignatura_id) REFERENCES asignaturas(id)  ON DELETE CASCADE,
        FOREIGN KEY(usuario_id)    REFERENCES usuarios(id)     ON DELETE CASCADE,
        FOREIGN KEY(asignacion_id) REFERENCES asignaciones(id) ON DELETE SET NULL,
        FOREIGN KEY(periodo_id)    REFERENCES periodos(id)     ON DELETE CASCADE
    )
    """,

    # -------------------------------------------------------------------------
    # 5. EVALUACIÓN
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS categorias (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT    NOT NULL,
        peso            REAL    NOT NULL CHECK(peso > 0 AND peso <= 1),
        asignacion_id   INTEGER NOT NULL,
        periodo_id      INTEGER NOT NULL,

        UNIQUE(nombre, asignacion_id, periodo_id),
        FOREIGN KEY(asignacion_id) REFERENCES asignaciones(id) ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)    REFERENCES periodos(id)     ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS actividades (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT    NOT NULL,
        descripcion     TEXT,
        fecha           DATE,
        valor_maximo    REAL    NOT NULL DEFAULT 100.0 CHECK(valor_maximo > 0),
        estado          TEXT    NOT NULL DEFAULT 'borrador'
                        CHECK(estado IN ('borrador', 'publicada', 'cerrada')),
        categoria_id    INTEGER NOT NULL,

        FOREIGN KEY(categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS notas (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        actividad_id        INTEGER NOT NULL,
        valor               REAL    NOT NULL CHECK(valor >= 0 AND valor <= 100),
        usuario_registro_id INTEGER,
        fecha_registro      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(estudiante_id, actividad_id) ON CONFLICT REPLACE,
        FOREIGN KEY(estudiante_id)       REFERENCES estudiantes(id)  ON DELETE CASCADE,
        FOREIGN KEY(actividad_id)        REFERENCES actividades(id)  ON DELETE CASCADE,
        FOREIGN KEY(usuario_registro_id) REFERENCES usuarios(id)     ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS puntos_extra (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        asignacion_id       INTEGER NOT NULL,
        periodo_id          INTEGER NOT NULL,
        tipo                TEXT    NOT NULL DEFAULT 'comportamental'
                            CHECK(tipo IN ('comportamental', 'participacion', 'academico')),
        positivos           INTEGER NOT NULL DEFAULT 0 CHECK(positivos >= 0),
        negativos           INTEGER NOT NULL DEFAULT 0 CHECK(negativos >= 0),
        observacion         TEXT,
        fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(estudiante_id, asignacion_id, periodo_id, tipo) ON CONFLICT REPLACE,
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)   ON DELETE CASCADE,
        FOREIGN KEY(asignacion_id) REFERENCES asignaciones(id)  ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)    REFERENCES periodos(id)       ON DELETE CASCADE
    )
    """,

    # -------------------------------------------------------------------------
    # 6. CIERRES Y PROMOCIÓN
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS cierres_periodo (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        asignacion_id       INTEGER NOT NULL,
        periodo_id          INTEGER NOT NULL,
        nota_definitiva     REAL    NOT NULL
                            CHECK(nota_definitiva >= 0 AND nota_definitiva <= 100),
        desempeno_id        INTEGER,
        logro_id            INTEGER,
        fecha_cierre        DATE    NOT NULL DEFAULT CURRENT_DATE,
        usuario_cierre_id   INTEGER,

        UNIQUE(estudiante_id, asignacion_id, periodo_id) ON CONFLICT REPLACE,
        FOREIGN KEY(estudiante_id)     REFERENCES estudiantes(id)      ON DELETE CASCADE,
        FOREIGN KEY(asignacion_id)     REFERENCES asignaciones(id)     ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)        REFERENCES periodos(id)         ON DELETE RESTRICT,
        FOREIGN KEY(desempeno_id)      REFERENCES niveles_desempeno(id) ON DELETE SET NULL,
        FOREIGN KEY(logro_id)          REFERENCES logros(id)           ON DELETE SET NULL,
        FOREIGN KEY(usuario_cierre_id) REFERENCES usuarios(id)        ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS cierres_anio (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id           INTEGER NOT NULL,
        asignacion_id           INTEGER NOT NULL,
        anio_id                 INTEGER NOT NULL,
        nota_promedio_periodos  REAL    NOT NULL
                                CHECK(nota_promedio_periodos >= 0
                                  AND nota_promedio_periodos <= 100),
        nota_habilitacion       REAL    CHECK(nota_habilitacion >= 0
                                         AND nota_habilitacion <= 100),
        nota_definitiva_anual   REAL    NOT NULL
                                CHECK(nota_definitiva_anual >= 0
                                  AND nota_definitiva_anual <= 100),
        perdio                  BOOLEAN NOT NULL DEFAULT 0,
        desempeno_id            INTEGER,
        fecha_cierre            DATE    NOT NULL DEFAULT CURRENT_DATE,
        usuario_cierre_id       INTEGER,

        UNIQUE(estudiante_id, asignacion_id, anio_id) ON CONFLICT REPLACE,
        FOREIGN KEY(estudiante_id)     REFERENCES estudiantes(id)       ON DELETE CASCADE,
        FOREIGN KEY(asignacion_id)     REFERENCES asignaciones(id)      ON DELETE CASCADE,
        FOREIGN KEY(anio_id)           REFERENCES configuracion_anio(id) ON DELETE RESTRICT,
        FOREIGN KEY(desempeno_id)      REFERENCES niveles_desempeno(id)  ON DELETE SET NULL,
        FOREIGN KEY(usuario_cierre_id) REFERENCES usuarios(id)          ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS promocion_anual (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id           INTEGER NOT NULL,
        anio_id                 INTEGER NOT NULL,
        estado                  TEXT    NOT NULL DEFAULT 'pendiente'
                                CHECK(estado IN ('promovido', 'reprobado',
                                                 'condicional', 'pendiente')),
        asignaturas_perdidas    INTEGER NOT NULL DEFAULT 0,
        observacion             TEXT,
        fecha_decision          DATE,
        usuario_decision_id     INTEGER,

        UNIQUE(estudiante_id, anio_id) ON CONFLICT REPLACE,
        FOREIGN KEY(estudiante_id)      REFERENCES estudiantes(id)        ON DELETE CASCADE,
        FOREIGN KEY(anio_id)            REFERENCES configuracion_anio(id) ON DELETE RESTRICT,
        FOREIGN KEY(usuario_decision_id) REFERENCES usuarios(id)          ON DELETE SET NULL
    )
    """,

    # -------------------------------------------------------------------------
    # 7. HABILITACIONES Y PLANES DE MEJORAMIENTO
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS habilitaciones (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        asignacion_id       INTEGER NOT NULL,
        periodo_id          INTEGER,
        tipo                TEXT    NOT NULL
                            CHECK(tipo IN ('periodo', 'anual')),
        nota_antes          REAL    CHECK(nota_antes >= 0 AND nota_antes <= 100),
        nota_habilitacion   REAL    CHECK(nota_habilitacion >= 0
                                     AND nota_habilitacion <= 100),
        fecha               DATE,
        estado              TEXT    NOT NULL DEFAULT 'pendiente'
                            CHECK(estado IN ('pendiente', 'realizada',
                                             'aprobada', 'reprobada')),
        observacion         TEXT,
        usuario_registro_id INTEGER,

        -- periodo_id puede ser NULL solo si tipo = 'anual'
        CHECK(tipo != 'periodo' OR periodo_id IS NOT NULL),
        FOREIGN KEY(estudiante_id)       REFERENCES estudiantes(id)   ON DELETE CASCADE,
        FOREIGN KEY(asignacion_id)       REFERENCES asignaciones(id)  ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)          REFERENCES periodos(id)      ON DELETE SET NULL,
        FOREIGN KEY(usuario_registro_id) REFERENCES usuarios(id)      ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS planes_mejoramiento (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id           INTEGER NOT NULL,
        asignacion_id           INTEGER NOT NULL,
        periodo_id              INTEGER NOT NULL,
        descripcion_dificultad  TEXT    NOT NULL,
        actividades_propuestas  TEXT    NOT NULL,
        fecha_inicio            DATE    NOT NULL DEFAULT CURRENT_DATE,
        fecha_seguimiento       DATE,
        fecha_cierre            DATE,
        estado                  TEXT    NOT NULL DEFAULT 'activo'
                                CHECK(estado IN ('activo', 'cumplido', 'incumplido')),
        observacion_cierre      TEXT,
        usuario_id              INTEGER,

        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)   ON DELETE CASCADE,
        FOREIGN KEY(asignacion_id) REFERENCES asignaciones(id)  ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)    REFERENCES periodos(id)      ON DELETE CASCADE,
        FOREIGN KEY(usuario_id)    REFERENCES usuarios(id)      ON DELETE SET NULL
    )
    """,

    # -------------------------------------------------------------------------
    # 8. ASISTENCIA Y CONVIVENCIA
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS control_diario (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER NOT NULL,
        grupo_id            INTEGER NOT NULL,
        asignacion_id       INTEGER NOT NULL,
        periodo_id          INTEGER NOT NULL,
        fecha               DATE    NOT NULL,
        estado              TEXT    NOT NULL DEFAULT 'P'
                            CHECK(estado IN ('P', 'FJ', 'FI', 'R', 'E')),
        hora_entrada        TIME,
        hora_salida         TIME,
        uniforme            BOOLEAN NOT NULL DEFAULT 1,
        materiales          BOOLEAN NOT NULL DEFAULT 1,
        observacion         TEXT,
        usuario_registro_id INTEGER,
        fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(estudiante_id, grupo_id, asignacion_id, fecha) ON CONFLICT REPLACE,
        FOREIGN KEY(estudiante_id)       REFERENCES estudiantes(id)   ON DELETE CASCADE,
        FOREIGN KEY(grupo_id)            REFERENCES grupos(id)        ON DELETE CASCADE,
        FOREIGN KEY(asignacion_id)       REFERENCES asignaciones(id)  ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)          REFERENCES periodos(id)      ON DELETE CASCADE,
        FOREIGN KEY(usuario_registro_id) REFERENCES usuarios(id)      ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS observaciones_periodo (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER  NOT NULL,
        asignacion_id   INTEGER  NOT NULL,
        periodo_id      INTEGER  NOT NULL,
        texto           TEXT     NOT NULL,
        es_publica      BOOLEAN  NOT NULL DEFAULT 1,
        fecha_registro  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        usuario_id      INTEGER,

        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)   ON DELETE CASCADE,
        FOREIGN KEY(asignacion_id) REFERENCES asignaciones(id)  ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)    REFERENCES periodos(id)      ON DELETE CASCADE,
        FOREIGN KEY(usuario_id)    REFERENCES usuarios(id)      ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS registro_comportamiento (
        id                      INTEGER  PRIMARY KEY AUTOINCREMENT,
        estudiante_id           INTEGER  NOT NULL,
        grupo_id                INTEGER  NOT NULL,
        periodo_id              INTEGER  NOT NULL,
        fecha                   DATE     NOT NULL DEFAULT CURRENT_DATE,
        tipo                    TEXT     NOT NULL
                                CHECK(tipo IN ('fortaleza', 'dificultad',
                                               'compromiso', 'citacion_acudiente',
                                               'descargo')),
        descripcion             TEXT     NOT NULL,
        seguimiento             TEXT,
        requiere_firma          BOOLEAN  NOT NULL DEFAULT 0,
        acudiente_notificado    BOOLEAN  NOT NULL DEFAULT 0,
        usuario_registro_id     INTEGER,

        FOREIGN KEY(estudiante_id)       REFERENCES estudiantes(id) ON DELETE CASCADE,
        FOREIGN KEY(grupo_id)            REFERENCES grupos(id)      ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)          REFERENCES periodos(id)    ON DELETE CASCADE,
        FOREIGN KEY(usuario_registro_id) REFERENCES usuarios(id)   ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS nota_comportamiento_periodo (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id   INTEGER NOT NULL,
        grupo_id        INTEGER NOT NULL,
        periodo_id      INTEGER NOT NULL,
        valor           REAL    NOT NULL CHECK(valor >= 0 AND valor <= 100),
        desempeno_id    INTEGER,
        observacion     TEXT,
        usuario_id      INTEGER,

        UNIQUE(estudiante_id, grupo_id, periodo_id) ON CONFLICT REPLACE,
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)        ON DELETE CASCADE,
        FOREIGN KEY(grupo_id)      REFERENCES grupos(id)             ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)    REFERENCES periodos(id)           ON DELETE CASCADE,
        FOREIGN KEY(desempeno_id)  REFERENCES niveles_desempeno(id)  ON DELETE SET NULL,
        FOREIGN KEY(usuario_id)    REFERENCES usuarios(id)           ON DELETE SET NULL
    )
    """,

    # -------------------------------------------------------------------------
    # 9. ALERTAS
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS configuracion_alertas (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        anio_id                 INTEGER NOT NULL,
        tipo_alerta             TEXT    NOT NULL
                                CHECK(tipo_alerta IN (
                                    'faltas_injustificadas',
                                    'promedio_bajo',
                                    'materias_en_riesgo',
                                    'plan_mejoramiento_vencido',
                                    'habilitacion_pendiente'
                                )),
        umbral                  REAL    NOT NULL,
        activa                  BOOLEAN NOT NULL DEFAULT 1,
        notificar_docente       BOOLEAN NOT NULL DEFAULT 1,
        notificar_director      BOOLEAN NOT NULL DEFAULT 0,
        notificar_acudiente     BOOLEAN NOT NULL DEFAULT 0,

        UNIQUE(anio_id, tipo_alerta),
        FOREIGN KEY(anio_id) REFERENCES configuracion_anio(id) ON DELETE CASCADE
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS alertas (
        id                      INTEGER  PRIMARY KEY AUTOINCREMENT,
        estudiante_id           INTEGER  NOT NULL,
        tipo_alerta             TEXT     NOT NULL
                                CHECK(tipo_alerta IN (
                                    'faltas_injustificadas',
                                    'promedio_bajo',
                                    'materias_en_riesgo',
                                    'plan_mejoramiento_vencido',
                                    'habilitacion_pendiente'
                                )),
        nivel                   TEXT     NOT NULL DEFAULT 'advertencia'
                                CHECK(nivel IN ('info', 'advertencia', 'critica')),
        descripcion             TEXT     NOT NULL,
        fecha_generacion        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        resuelta                BOOLEAN  NOT NULL DEFAULT 0,
        fecha_resolucion        DATETIME,
        usuario_resolucion_id   INTEGER,
        observacion_resolucion  TEXT,

        FOREIGN KEY(estudiante_id)          REFERENCES estudiantes(id) ON DELETE CASCADE,
        FOREIGN KEY(usuario_resolucion_id)  REFERENCES usuarios(id)   ON DELETE SET NULL
    )
    """,

    # -------------------------------------------------------------------------
    # 10. INFORMES Y PIAR
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS boletines_emitidos (
        id                  INTEGER  PRIMARY KEY AUTOINCREMENT,
        estudiante_id       INTEGER  NOT NULL,
        periodo_id          INTEGER,
        anio_id             INTEGER  NOT NULL,
        tipo                TEXT     NOT NULL
                            CHECK(tipo IN ('periodo', 'anual')),
        fecha_generacion    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fecha_entrega       DATE,
        entregado           BOOLEAN  NOT NULL DEFAULT 0,
        usuario_generador_id INTEGER,

        -- periodo_id es NULL solo en boletines anuales
        CHECK(tipo != 'periodo' OR periodo_id IS NOT NULL),
        FOREIGN KEY(estudiante_id)        REFERENCES estudiantes(id)        ON DELETE CASCADE,
        FOREIGN KEY(periodo_id)           REFERENCES periodos(id)           ON DELETE SET NULL,
        FOREIGN KEY(anio_id)              REFERENCES configuracion_anio(id) ON DELETE CASCADE,
        FOREIGN KEY(usuario_generador_id) REFERENCES usuarios(id)          ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS piar (
        id                      INTEGER  PRIMARY KEY AUTOINCREMENT,
        estudiante_id           INTEGER  NOT NULL,
        anio_id                 INTEGER  NOT NULL,
        descripcion_necesidad   TEXT     NOT NULL,
        ajustes_evaluativos     TEXT,
        ajustes_pedagogicos     TEXT,
        profesionales_apoyo     TEXT,
        fecha_elaboracion       DATE     NOT NULL DEFAULT CURRENT_DATE,
        fecha_revision          DATE,
        usuario_elaboracion_id  INTEGER,

        UNIQUE(estudiante_id, anio_id),
        FOREIGN KEY(estudiante_id)          REFERENCES estudiantes(id)        ON DELETE CASCADE,
        FOREIGN KEY(anio_id)                REFERENCES configuracion_anio(id) ON DELETE CASCADE,
        FOREIGN KEY(usuario_elaboracion_id) REFERENCES usuarios(id)          ON DELETE SET NULL
    )
    """,

    # -------------------------------------------------------------------------
    # 11. AUDITORÍA
    # -------------------------------------------------------------------------

    """
    CREATE TABLE IF NOT EXISTS auditoria (
        id          INTEGER  PRIMARY KEY AUTOINCREMENT,
        usuario     TEXT     NOT NULL,
        usuario_id  INTEGER,
        tipo_evento TEXT     NOT NULL
                    CHECK(tipo_evento IN (
                        'LOGIN_EXITOSO', 'LOGIN_FALLIDO', 'LOGOUT',
                        'CREAR_USUARIO', 'EDITAR_USUARIO', 'RESETEAR_PASSWORD',
                        'CAMBIAR_ROL', 'DESACTIVAR_USUARIO', 'ACTIVAR_USUARIO',
                        'ACCESO_DENEGADO'
                    )),
        ip_address  TEXT,
        fecha_hora  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        detalles    TEXT,

        FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id              INTEGER  PRIMARY KEY AUTOINCREMENT,
        usuario_id      INTEGER,
        accion          TEXT     NOT NULL,
        tabla           TEXT     NOT NULL,
        registro_id     INTEGER,
        valor_anterior  TEXT,
        valor_nuevo     TEXT,
        timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
    )
    """,
]


# =============================================================================
# ÍNDICES
# =============================================================================

INDICES: list[str] = [

    # configuracion_anio
    "CREATE INDEX IF NOT EXISTS idx_config_anio        ON configuracion_anio(anio)",

    # niveles_desempeno
    "CREATE INDEX IF NOT EXISTS idx_niveles_anio        ON niveles_desempeno(anio_id)",

    # asignaturas
    "CREATE INDEX IF NOT EXISTS idx_asig_area           ON asignaturas(area_id)",

    # estudiantes
    "CREATE INDEX IF NOT EXISTS idx_est_grupo           ON estudiantes(grupo_id)",
    "CREATE INDEX IF NOT EXISTS idx_est_estado          ON estudiantes(estado_matricula)",
    "CREATE INDEX IF NOT EXISTS idx_est_documento       ON estudiantes(numero_documento)",

    # acudientes
    "CREATE INDEX IF NOT EXISTS idx_acud_documento      ON acudientes(numero_documento)",

    # periodos
    "CREATE INDEX IF NOT EXISTS idx_periodos_anio       ON periodos(anio_id)",
    "CREATE INDEX IF NOT EXISTS idx_periodos_activo     ON periodos(activo)",

    # asignaciones (tabla pivot crítica)
    "CREATE INDEX IF NOT EXISTS idx_asignac_usuario     ON asignaciones(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_asignac_grupo       ON asignaciones(grupo_id)",
    "CREATE INDEX IF NOT EXISTS idx_asignac_asignatura  ON asignaciones(asignatura_id)",
    "CREATE INDEX IF NOT EXISTS idx_asignac_periodo     ON asignaciones(periodo_id)",

    # logros
    "CREATE INDEX IF NOT EXISTS idx_logros_asignacion   ON logros(asignacion_id)",
    "CREATE INDEX IF NOT EXISTS idx_logros_periodo      ON logros(periodo_id)",

    # horarios
    "CREATE INDEX IF NOT EXISTS idx_horarios_grupo      ON horarios(grupo_id)",
    "CREATE INDEX IF NOT EXISTS idx_horarios_usuario    ON horarios(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_horarios_periodo    ON horarios(periodo_id)",

    # categorias y actividades
    "CREATE INDEX IF NOT EXISTS idx_cats_asignacion     ON categorias(asignacion_id)",
    "CREATE INDEX IF NOT EXISTS idx_cats_periodo        ON categorias(periodo_id)",
    "CREATE INDEX IF NOT EXISTS idx_acts_categoria      ON actividades(categoria_id)",
    "CREATE INDEX IF NOT EXISTS idx_acts_fecha          ON actividades(fecha)",

    # notas
    "CREATE INDEX IF NOT EXISTS idx_notas_estudiante    ON notas(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_notas_actividad     ON notas(actividad_id)",
    "CREATE INDEX IF NOT EXISTS idx_notas_fecha         ON notas(fecha_registro)",

    # cierres_periodo
    "CREATE INDEX IF NOT EXISTS idx_cierres_p_est       ON cierres_periodo(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_cierres_p_per       ON cierres_periodo(periodo_id)",
    "CREATE INDEX IF NOT EXISTS idx_cierres_p_asig      ON cierres_periodo(asignacion_id)",

    # cierres_anio
    "CREATE INDEX IF NOT EXISTS idx_cierres_a_est       ON cierres_anio(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_cierres_a_anio      ON cierres_anio(anio_id)",

    # promocion_anual
    "CREATE INDEX IF NOT EXISTS idx_prom_est            ON promocion_anual(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_prom_anio           ON promocion_anual(anio_id)",
    "CREATE INDEX IF NOT EXISTS idx_prom_estado         ON promocion_anual(estado)",

    # habilitaciones
    "CREATE INDEX IF NOT EXISTS idx_habil_est           ON habilitaciones(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_habil_asig          ON habilitaciones(asignacion_id)",
    "CREATE INDEX IF NOT EXISTS idx_habil_estado        ON habilitaciones(estado)",

    # planes_mejoramiento
    "CREATE INDEX IF NOT EXISTS idx_planes_est          ON planes_mejoramiento(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_planes_periodo      ON planes_mejoramiento(periodo_id)",
    "CREATE INDEX IF NOT EXISTS idx_planes_estado       ON planes_mejoramiento(estado)",

    # control_diario
    "CREATE INDEX IF NOT EXISTS idx_ctrl_fecha          ON control_diario(fecha)",
    "CREATE INDEX IF NOT EXISTS idx_ctrl_estudiante     ON control_diario(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_ctrl_grupo          ON control_diario(grupo_id)",
    "CREATE INDEX IF NOT EXISTS idx_ctrl_asignacion     ON control_diario(asignacion_id)",
    "CREATE INDEX IF NOT EXISTS idx_ctrl_periodo        ON control_diario(periodo_id)",
    "CREATE INDEX IF NOT EXISTS idx_ctrl_estado         ON control_diario(estado)",

    # observaciones_periodo
    "CREATE INDEX IF NOT EXISTS idx_obs_estudiante      ON observaciones_periodo(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_obs_periodo         ON observaciones_periodo(periodo_id)",

    # registro_comportamiento
    "CREATE INDEX IF NOT EXISTS idx_comp_estudiante     ON registro_comportamiento(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_comp_periodo        ON registro_comportamiento(periodo_id)",
    "CREATE INDEX IF NOT EXISTS idx_comp_tipo           ON registro_comportamiento(tipo)",

    # alertas
    "CREATE INDEX IF NOT EXISTS idx_alertas_est         ON alertas(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_alertas_tipo        ON alertas(tipo_alerta)",
    "CREATE INDEX IF NOT EXISTS idx_alertas_resuelta    ON alertas(resuelta)",

    # historial_estudiantes
    "CREATE INDEX IF NOT EXISTS idx_hist_estudiante     ON historial_estudiantes(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_hist_fecha          ON historial_estudiantes(fecha_movimiento)",

    # piar
    "CREATE INDEX IF NOT EXISTS idx_piar_est            ON piar(estudiante_id)",
    "CREATE INDEX IF NOT EXISTS idx_piar_anio           ON piar(anio_id)",

    # auditoría
    "CREATE INDEX IF NOT EXISTS idx_audit_usuario_id    ON auditoria(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_fecha         ON auditoria(fecha_hora)",
    "CREATE INDEX IF NOT EXISTS idx_audit_tipo          ON auditoria(tipo_evento)",
    "CREATE INDEX IF NOT EXISTS idx_auditlog_usuario    ON audit_log(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_auditlog_tabla      ON audit_log(tabla)",
    "CREATE INDEX IF NOT EXISTS idx_auditlog_timestamp  ON audit_log(timestamp)",
]


# =============================================================================
# TRIGGERS
# =============================================================================

TRIGGERS: list[str] = [

    # La suma de pesos de categorías para una asignación+periodo no puede superar 1.0
    """
    CREATE TRIGGER IF NOT EXISTS tg_validar_peso_categorias
    BEFORE INSERT ON categorias
    BEGIN
        SELECT RAISE(ABORT, 'La suma de pesos de las categorías supera el 100%')
        WHERE (
            SELECT COALESCE(SUM(peso), 0)
            FROM   categorias
            WHERE  asignacion_id = NEW.asignacion_id
              AND  periodo_id    = NEW.periodo_id
        ) + NEW.peso > 1.001;
    END
    """,

    # Igual que el anterior pero para UPDATE (cuando se edita el peso)
    """
    CREATE TRIGGER IF NOT EXISTS tg_validar_peso_categorias_update
    BEFORE UPDATE OF peso ON categorias
    BEGIN
        SELECT RAISE(ABORT, 'La suma de pesos de las categorías supera el 100%')
        WHERE (
            SELECT COALESCE(SUM(peso), 0)
            FROM   categorias
            WHERE  asignacion_id = NEW.asignacion_id
              AND  periodo_id    = NEW.periodo_id
              AND  id           != NEW.id
        ) + NEW.peso > 1.001;
    END
    """,

    # Actualiza ultima_sesion en usuarios cuando hay un LOGIN_EXITOSO en auditoria
    """
    CREATE TRIGGER IF NOT EXISTS tg_actualizar_ultima_sesion
    AFTER INSERT ON auditoria
    WHEN NEW.tipo_evento = 'LOGIN_EXITOSO' AND NEW.usuario_id IS NOT NULL
    BEGIN
        UPDATE usuarios
        SET    ultima_sesion = CURRENT_TIMESTAMP
        WHERE  id = NEW.usuario_id;
    END
    """,

    # Impide eliminar un periodo que ya tiene cierres registrados
    """
    CREATE TRIGGER IF NOT EXISTS tg_proteger_periodo_con_cierres
    BEFORE DELETE ON periodos
    BEGIN
        SELECT RAISE(ABORT, 'No se puede eliminar un periodo con cierres de notas registrados')
        WHERE EXISTS (
            SELECT 1 FROM cierres_periodo WHERE periodo_id = OLD.id
        );
    END
    """,

    # Impide modificar notas en un periodo cerrado
    """
    CREATE TRIGGER IF NOT EXISTS tg_proteger_nota_periodo_cerrado
    BEFORE INSERT ON notas
    BEGIN
        SELECT RAISE(ABORT, 'No se pueden registrar notas en un periodo cerrado')
        WHERE EXISTS (
            SELECT 1
            FROM   actividades  act
            JOIN   categorias   cat ON cat.id = act.categoria_id
            JOIN   periodos     per ON per.id = cat.periodo_id
            WHERE  act.id  = NEW.actividad_id
              AND  per.cerrado = 1
        );
    END
    """,

    # Registra automáticamente en historial cuando cambia el grupo de un estudiante
    """
    CREATE TRIGGER IF NOT EXISTS tg_historial_cambio_grupo
    AFTER UPDATE OF grupo_id ON estudiantes
    WHEN OLD.grupo_id IS DISTINCT FROM NEW.grupo_id
    BEGIN
        INSERT INTO historial_estudiantes
            (estudiante_id, grupo_origen_id, grupo_destino_id, tipo_movimiento)
        VALUES
            (NEW.id, OLD.grupo_id, NEW.grupo_id, 'TRASLADO');
    END
    """,

    # Resuelve automáticamente alertas de promedio_bajo cuando se cierra el periodo
    # con nota aprobatoria
    """
    CREATE TRIGGER IF NOT EXISTS tg_resolver_alerta_aprobacion
    AFTER INSERT ON cierres_periodo
    BEGIN
        UPDATE alertas
        SET    resuelta          = 1,
               fecha_resolucion  = CURRENT_TIMESTAMP,
               observacion_resolucion = 'Resuelto automáticamente al aprobar el periodo'
        WHERE  estudiante_id = NEW.estudiante_id
          AND  tipo_alerta   = 'promedio_bajo'
          AND  resuelta      = 0;
    END
    """,
]


# =============================================================================
# INICIALIZACIÓN
# =============================================================================

def _column_exists(conn, table: str, column: str) -> bool:
    """Verifica si una columna existe en una tabla (para micro-migraciones)."""
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r[1] == column for r in rows)
    except Exception:
        return False


def _table_exists(conn, table: str) -> bool:
    """Verifica si una tabla existe."""
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone()
    return bool(row and row[0])


def init_db(db_path: Path | None = None) -> bool:
    """
    Inicializa el esquema completo de la base de datos.

    Ejecuta en orden:
      1. CREATE TABLE IF NOT EXISTS  — idempotente
      2. Micro-migraciones           — ALTER TABLE ADD COLUMN si falta columna
      3. CREATE INDEX IF NOT EXISTS  — idempotente
      4. CREATE TRIGGER IF NOT EXISTS — idempotente
      5. PRAGMA integrity_check

    Args:
        db_path: Ruta opcional a la BD. Si es None usa la configurada en connection.py.

    Returns:
        True si la inicialización fue exitosa.
    """
    from .connection import get_connection

    try:
        with get_connection() as conn:

            # ------------------------------------------------------------------
            # Tablas
            # ------------------------------------------------------------------
            for i, sql in enumerate(SCHEMA, 1):
                try:
                    conn.execute(sql)
                    logger.debug(f"Tabla {i}/{len(SCHEMA)} verificada")
                except Exception as exc:
                    logger.error(f"Error en tabla {i}: {exc}")
                    raise

            # ------------------------------------------------------------------
            # Micro-migraciones (columnas nuevas en tablas ya existentes)
            # Formato: (tabla, columna, DDL de la columna)
            # ------------------------------------------------------------------
            migraciones = [
                # Nada aún en v2.0 — se agregan cuando sea necesario
            ]

            for tabla, columna, ddl in migraciones:
                if not _column_exists(conn, tabla, columna):
                    logger.info(f"Migración: ALTER TABLE {tabla} ADD COLUMN {columna}")
                    conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {ddl}")

            # ------------------------------------------------------------------
            # Índices
            # ------------------------------------------------------------------
            for i, sql in enumerate(INDICES, 1):
                try:
                    conn.execute(sql)
                    logger.debug(f"Índice {i}/{len(INDICES)} verificado")
                except Exception as exc:
                    logger.error(f"Error en índice {i}: {exc}")
                    raise

            # ------------------------------------------------------------------
            # Triggers
            # ------------------------------------------------------------------
            for i, sql in enumerate(TRIGGERS, 1):
                try:
                    conn.execute(sql)
                    logger.debug(f"Trigger {i}/{len(TRIGGERS)} verificado")
                except Exception as exc:
                    logger.error(f"Error en trigger {i}: {exc}")
                    raise

            # ------------------------------------------------------------------
            # Integridad
            # ------------------------------------------------------------------
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                logger.error(f"Integridad de BD fallida: {result[0]}")
                return False

            conn.commit()

            logger.info(
                f"Schema inicializado — "
                f"{len(SCHEMA)} tablas, "
                f"{len(INDICES)} índices, "
                f"{len(TRIGGERS)} triggers"
            )
            return True

    except Exception as exc:
        logger.error(f"Error crítico inicializando schema: {exc}")
        return False


def get_db_stats() -> dict:
    """Retorna conteo de filas por tabla y tamaño de la BD."""
    from .connection import get_connection, DB_PATH

    try:
        with get_connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()

            stats = {t[0]: conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
                     for t in tables}

            if DB_PATH.exists():
                stats["_db_size_mb"] = round(DB_PATH.stat().st_size / (1024 ** 2), 2)

            return stats

    except Exception as exc:
        logger.error(f"Error obteniendo estadísticas: {exc}")
        return {}


__all__ = ["init_db", "get_db_stats", "SCHEMA", "INDICES", "TRIGGERS"]