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
from __future__ import annotations

import logging
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime,
    DDL, Float, ForeignKey, Index, Integer, MetaData,
    Numeric, String, Table, Text, UniqueConstraint, event, text,
)

logger = logging.getLogger("DB.SCHEMA")

metadata = MetaData()

# ============================================================
# 1. CONFIGURACIÓN INSTITUCIONAL
# ============================================================

instituciones = Table(
    "instituciones", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("nit", String),
    Column("codigo", String),
    Column("activa", Boolean, nullable=False, server_default="1"),
    Column("fecha_creacion", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("nombre_oficial", String),
    Column("codigo_dane", String),
    Column("rector", String),
    Column("direccion", String),
    Column("pais", String),
    Column("departamento", String),
    Column("municipio", String),
    Column("telefono", String),
    Column("logo_path", String),
    Column("logo_url", String),
    Column("resolucion_aprobacion", String),
    Column("lema", String),
    Column("email_institucional", String),
    Column("jornada_principal", String),
    Column("tipo_institucion", String),
    Column("calendario", String),
    Column("configuracion_inicial_completa", Boolean, nullable=False, server_default="0"),
    UniqueConstraint("nombre"),
    # D4: CHECKs faltantes
    CheckConstraint(
        "jornada_principal IS NULL OR jornada_principal IN ('AM','PM','UNICA')",
        name="ck_instituciones_jornada",
    ),
    CheckConstraint(
        "tipo_institucion IS NULL OR tipo_institucion IN ('publica','privada')",
        name="ck_instituciones_tipo",
    ),
    CheckConstraint(
        "calendario IS NULL OR calendario IN ('A','B')",
        name="ck_instituciones_calendario",
    ),
)

configuracion_anio = Table(
    "configuracion_anio", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio", Integer, nullable=False),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    Column("fecha_inicio_clases", Date),
    Column("fecha_fin_clases", Date),
    Column("nombre_institucion", String, nullable=False, server_default="Institución Educativa"),
    Column("dane_code", String),
    Column("rector", String),
    Column("direccion", String),
    Column("municipio", String),
    Column("telefono_institucion", String),
    Column("logo_path", String),
    Column("resolucion_aprobacion", String),
    Column("nota_minima_aprobacion", Float, nullable=False, server_default="60.0"),
    Column("nota_minima_escala", Float, nullable=False, server_default="0.0"),
    Column("nota_maxima_escala", Float, nullable=False, server_default="100.0"),
    Column("activo", Boolean, nullable=False, server_default="1"),
    UniqueConstraint("institucion_id", "anio"),
    CheckConstraint(
        "nota_minima_aprobacion >= 0 AND nota_minima_aprobacion <= 100",
        name="ck_config_anio_nota_min",
    ),
)

niveles_desempeno = Table(
    "niveles_desempeno", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("nombre", String, nullable=False),
    Column("rango_min", Float, nullable=False),
    Column("rango_max", Float, nullable=False),
    Column("descripcion", String),
    Column("orden", Integer, nullable=False, server_default="0"),
    UniqueConstraint("anio_id", "nombre"),
    UniqueConstraint("anio_id", "orden"),
    CheckConstraint("rango_min >= 0 AND rango_min < 100", name="ck_niveles_rango_min"),
    CheckConstraint("rango_max > 0 AND rango_max <= 100", name="ck_niveles_rango_max"),
    CheckConstraint("rango_min < rango_max", name="ck_niveles_rango"),
)

configuracion_periodos = Table(
    "configuracion_periodos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("numero_periodos", Integer, nullable=False, server_default="4"),
    Column("pesos_iguales", Boolean, nullable=False, server_default="1"),
    UniqueConstraint("anio_id"),
    CheckConstraint("numero_periodos BETWEEN 2 AND 6", name="ck_config_per_numero"),
)

criterios_promocion = Table(
    "criterios_promocion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("max_asignaturas_perdidas", Integer, nullable=False, server_default="2"),
    Column("permite_condicionada", Boolean, nullable=False, server_default="1"),
    Column("nota_minima_habilitacion", Float, nullable=False, server_default="60.0"),
    Column("nota_minima_anual", Float, nullable=False, server_default="60.0"),
    UniqueConstraint("anio_id"),
    CheckConstraint(
        "nota_minima_habilitacion >= 0 AND nota_minima_habilitacion <= 100",
        name="ck_criterios_nota_hab",
    ),
    CheckConstraint(
        "nota_minima_anual >= 0 AND nota_minima_anual <= 100",
        name="ck_criterios_nota_anual",
    ),
)

# ============================================================
# 2. INFRAESTRUCTURA ACADÉMICA
# ============================================================

escenarios_horario = Table(
    "escenarios_horario", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("nombre", String, nullable=False),
    Column("descripcion", String),
    Column("activo", Integer, nullable=False, server_default="0"),
    Column("created_at", String, nullable=False, server_default=text("datetime('now')")),
    UniqueConstraint("anio_id", "nombre"),
)

plantillas_franja = Table(
    "plantillas_franja", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("jornada", String, nullable=False, server_default="UNICA"),
    Column("dias_activos", String, nullable=False, server_default="Lunes,Martes,Miércoles,Jueves,Viernes"),
    Column("activa", Integer, nullable=False, server_default="0"),
    Column("created_at", String, nullable=False, server_default=text("datetime('now')")),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("institucion_id", "nombre"),
    CheckConstraint("jornada IN ('AM', 'PM', 'UNICA')", name="ck_plantillas_jornada"),
)

franjas = Table(
    "franjas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("plantilla_id", Integer, ForeignKey("plantillas_franja.id", ondelete="CASCADE"), nullable=False),
    Column("orden", Integer, nullable=False),
    Column("hora_inicio", String, nullable=False),
    Column("hora_fin", String, nullable=False),
    Column("tipo", String, nullable=False, server_default="lectiva"),
    Column("etiqueta", String),
    UniqueConstraint("plantilla_id", "orden"),
    CheckConstraint("orden >= 1", name="ck_franjas_orden"),
    CheckConstraint("hora_inicio < hora_fin", name="ck_franjas_horas"),
    CheckConstraint("tipo IN ('lectiva', 'descanso', 'almuerzo')", name="ck_franjas_tipo"),
)

areas_conocimiento = Table(
    "areas_conocimiento", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("codigo", String),
    Column("color", String),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("institucion_id", "nombre"),
    UniqueConstraint("institucion_id", "codigo"),
)

asignaturas = Table(
    "asignaturas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("codigo", String),
    Column("area_id", Integer, ForeignKey("areas_conocimiento.id", ondelete="SET NULL")),
    Column("horas_semanales", Integer, nullable=False, server_default="1"),
    Column("tipo_sala_requerido", String),
    Column("bloque_doble", Integer, nullable=False, server_default="0"),
    Column("horas_consecutivas", Integer, nullable=False, server_default="1"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("institucion_id", "nombre"),
    UniqueConstraint("institucion_id", "codigo"),
    CheckConstraint("horas_semanales > 0", name="ck_asig_horas"),
    CheckConstraint("horas_consecutivas >= 1", name="ck_asig_consecutivas"),
)

grados = Table(
    "grados", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("numero", Integer, nullable=False),
    Column("nombre", String),
    Column("min_estudiantes", Integer, nullable=False, server_default="0"),
    Column("max_estudiantes", Integer, nullable=False, server_default="40"),
    Column("horas_semanales", Integer, nullable=False, server_default="0"),
    UniqueConstraint("numero"),
    CheckConstraint("numero BETWEEN 1 AND 13", name="ck_grados_numero"),
    CheckConstraint("min_estudiantes >= 0", name="ck_grados_min_est"),
    CheckConstraint("max_estudiantes >= 1", name="ck_grados_max_est"),
    CheckConstraint("horas_semanales >= 0", name="ck_grados_horas"),
)

salas = Table(
    "salas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("tipo", String, nullable=False, server_default="aula"),
    Column("capacidad", Integer, nullable=False, server_default="30"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("institucion_id", "nombre"),
    CheckConstraint("tipo IN ('aula','laboratorio','computo','ed_fisica','otro')", name="ck_salas_tipo"),
    CheckConstraint("capacidad >= 1", name="ck_salas_capacidad"),
)

# grupos va en módulo 2 aunque referencia usuarios (módulo 3);
# create_all() resuelve el orden por las FKs declaradas como strings.
grupos = Table(
    "grupos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("codigo", String, nullable=False),
    Column("nombre", String),
    Column("grado", Integer),
    Column("jornada", String, nullable=False, server_default="UNICA"),
    Column("capacidad_maxima", Integer, nullable=False, server_default="40"),
    # D2: FK real a salas
    Column("sala_id", Integer, ForeignKey("salas.id", ondelete="SET NULL")),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    Column("director_grupo_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("institucion_id", "codigo"),
    CheckConstraint("grado BETWEEN 1 AND 13", name="ck_grupos_grado"),
    CheckConstraint("jornada IN ('AM', 'PM', 'UNICA')", name="ck_grupos_jornada"),
    CheckConstraint("capacidad_maxima > 0", name="ck_grupos_capacidad"),
)

ventanas_grupo = Table(
    "ventanas_grupo", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("grupo_id", Integer, ForeignKey("grupos.id", ondelete="CASCADE")),
    Column("grado", Integer),
    Column("franjas_permitidas", String, nullable=False, server_default="[]"),
    CheckConstraint("(grupo_id IS NULL) != (grado IS NULL)", name="ck_ventanas_exclusivo"),
)

# bloques_anclados referencia asignaciones (módulo 4) — string FK
bloques_anclados = Table(
    "bloques_anclados", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("escenario_id", Integer, ForeignKey("escenarios_horario.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("dia_semana", String, nullable=False),
    Column("franja_orden", Integer, nullable=False),
    Column("sala_id", Integer, ForeignKey("salas.id", ondelete="SET NULL")),
    UniqueConstraint("escenario_id", "dia_semana", "franja_orden", "asignacion_id"),
    CheckConstraint(
        "dia_semana IN ('Lunes','Martes','Miércoles','Jueves','Viernes','Sábado')",
        name="ck_bloques_dia",
    ),
    CheckConstraint("franja_orden >= 1", name="ck_bloques_franja"),
)

franjas_reunion = Table(
    "franjas_reunion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("docentes_json", String, nullable=False, server_default="[]"),
    Column("dia_semana", String, nullable=False),
    Column("franja_orden", Integer, nullable=False),
    Column("modo", String, nullable=False, server_default="preferente"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    CheckConstraint(
        "dia_semana IN ('Lunes','Martes','Miércoles','Jueves','Viernes','Sábado')",
        name="ck_franjas_reunion_dia",
    ),
    CheckConstraint("franja_orden >= 1", name="ck_franjas_reunion_orden"),
    CheckConstraint("modo IN ('estricta','preferente')", name="ck_franjas_reunion_modo"),
)

# limites_docente y disponibilidad_docente referencian usuarios (módulo 3) — string FK
limites_docente = Table(
    "limites_docente", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
    Column("min_horas_dia", Integer, nullable=False, server_default="0"),
    Column("max_horas_dia", Integer, nullable=False, server_default="8"),
    UniqueConstraint("usuario_id"),
    CheckConstraint("min_horas_dia >= 0", name="ck_limites_min"),
    CheckConstraint("max_horas_dia >= 1", name="ck_limites_max"),
    CheckConstraint("min_horas_dia <= max_horas_dia", name="ck_limites_rango"),
)

disponibilidad_docente = Table(
    "disponibilidad_docente", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
    Column("dia_semana", String, nullable=False),
    Column("franja_orden", Integer, nullable=False),
    Column("disponible", Integer, nullable=False, server_default="1"),
    UniqueConstraint("usuario_id", "dia_semana", "franja_orden"),
    CheckConstraint(
        "dia_semana IN ('Lunes','Martes','Miércoles','Jueves','Viernes','Sábado')",
        name="ck_disp_dia",
    ),
    CheckConstraint("franja_orden >= 1", name="ck_disp_franja"),
)

# config_generacion referencia periodos (módulo 4) — string FK
config_generacion = Table(
    "config_generacion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("plantilla_id", Integer, ForeignKey("plantillas_franja.id", ondelete="CASCADE"), nullable=False),
    Column("estado", String, nullable=False, server_default="borrador"),
    Column("grupos_json", String, nullable=False, server_default="[]"),
    Column(
        "pesos_json", String, nullable=False,
        server_default='{"huecos":1.0,"distribucion":1.0,"compactacion":0.5}',
    ),
    Column("restricciones_json", String, nullable=False, server_default="{}"),
    Column("escenario_destino_id", Integer, ForeignKey("escenarios_horario.id", ondelete="SET NULL")),
    Column("created_at", String, nullable=False, server_default=text("datetime('now')")),
    Column("updated_at", String, nullable=False, server_default=text("datetime('now')")),
    UniqueConstraint("nombre"),
    CheckConstraint("estado IN ('borrador','generado','aplicado')", name="ck_config_gen_estado"),
)

plan_estudios = Table(
    "plan_estudios", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("grado", Integer, nullable=False),
    Column("asignatura_id", Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False),
    Column("horas_semanales", Integer, nullable=False),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("institucion_id", "grado", "asignatura_id"),
    CheckConstraint("grado >= 1 AND grado <= 13", name="ck_plan_est_grado"),
    CheckConstraint("horas_semanales >= 1 AND horas_semanales <= 40", name="ck_plan_est_horas"),
)

configuracion_grado_institucion = Table(
    "configuracion_grado_institucion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("grado_id", Integer, ForeignKey("grados.id", ondelete="CASCADE"), nullable=False),
    Column("institucion_id", Integer, ForeignKey("instituciones.id"), nullable=False),
    Column("min_estudiantes", Integer, nullable=False, server_default="0"),
    Column("max_estudiantes", Integer, nullable=False, server_default="40"),
    Column("horas_semanales", Integer, nullable=False, server_default="0"),
    UniqueConstraint("grado_id", "institucion_id"),
    CheckConstraint("min_estudiantes >= 0", name="ck_cfg_grado_min"),
    CheckConstraint("max_estudiantes >= 1", name="ck_cfg_grado_max"),
    CheckConstraint("horas_semanales >= 0", name="ck_cfg_grado_horas"),
)

preferencias_institucion = Table(
    "preferencias_institucion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("institucion_id", Integer, ForeignKey("instituciones.id", ondelete="CASCADE"), nullable=False),
    Column("categoria", String, nullable=False),
    Column("clave", String, nullable=False),
    Column("valor", String),
    Column("tipo_valor", String, nullable=False, server_default="str"),
    UniqueConstraint("institucion_id", "clave"),
    CheckConstraint("tipo_valor IN ('str','int','float','bool','json')", name="ck_pref_inst_tipo_valor"),
    # D4
    CheckConstraint(
        "categoria IN ('academicas','convivencia','apariencia')",
        name="ck_pref_inst_categoria",
    ),
)

# ============================================================
# 3. USUARIOS Y ACUDIENTES
# ============================================================

usuarios = Table(
    "usuarios", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("usuario", String, nullable=False),
    Column("password_hash", String, nullable=False),
    Column("nombre_completo", String, nullable=False),
    Column("email", String),
    Column("telefono", String),
    Column("rol", String, nullable=False),
    Column("activo", Boolean, nullable=False, server_default="1"),
    Column("debe_cambiar_password", Boolean, nullable=False, server_default="0"),
    Column("fecha_creacion", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("ultima_sesion", DateTime),
    Column("carga_horaria_max", Integer),
    Column("horas_extra", Integer, nullable=False, server_default="0"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("usuario"),
    CheckConstraint(
        "rol IN ('admin', 'director', 'coordinador', 'profesor', 'estudiante', 'apoderado')",
        name="ck_usuarios_rol",
    ),
    CheckConstraint("horas_extra >= 0", name="ck_usuarios_horas_extra"),
)

acudientes = Table(
    "acudientes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tipo_documento", String, nullable=False, server_default="CC"),
    Column("numero_documento", String, nullable=False),
    Column("nombre_completo", String, nullable=False),
    Column("parentesco", String, nullable=False),
    Column("celular", String),
    Column("email", String),
    Column("direccion", String),
    Column("activo", Boolean, nullable=False, server_default="1"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("usuario_id"),
    UniqueConstraint("institucion_id", "numero_documento"),
    CheckConstraint("tipo_documento IN ('CC', 'CE', 'TI', 'PASAPORTE')", name="ck_acud_tipo_doc"),
    CheckConstraint(
        "parentesco IN ('padre', 'madre', 'abuelo', 'abuela', 'tio', 'tia',"
        " 'hermano', 'hermana', 'tutor_legal', 'otro')",
        name="ck_acud_parentesco",
    ),
)

estudiantes = Table(
    "estudiantes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("id_publico", String),
    Column("tipo_documento", String, nullable=False, server_default="TI"),
    Column("numero_documento", String, nullable=False),
    Column("nombre", String, nullable=False),
    Column("apellido", String, nullable=False),
    Column("genero", String),
    Column("grupo_id", Integer, ForeignKey("grupos.id", ondelete="SET NULL")),
    Column("posee_piar", Boolean, nullable=False, server_default="0"),
    Column("fecha_nacimiento", Date),
    Column("direccion", String),
    Column("fecha_ingreso", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("estado_matricula", String, nullable=False, server_default="activo"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("id_publico"),
    UniqueConstraint("institucion_id", "numero_documento"),
    CheckConstraint("tipo_documento IN ('TI', 'CC', 'CE', 'NUIP')", name="ck_est_tipo_doc"),
    CheckConstraint("genero IN ('M', 'F', 'OTRO')", name="ck_est_genero"),
    CheckConstraint(
        "estado_matricula IN ('activo', 'inactivo', 'retirado', 'graduado')",
        name="ck_est_estado",
    ),
)

estudiante_acudiente = Table(
    "estudiante_acudiente", metadata,
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False, primary_key=True),
    Column("acudiente_id", Integer, ForeignKey("acudientes.id", ondelete="CASCADE"), nullable=False, primary_key=True),
    Column("es_principal", Boolean, nullable=False, server_default="0"),
)

historial_estudiantes = Table(
    "historial_estudiantes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("grupo_origen_id", Integer, ForeignKey("grupos.id", ondelete="SET NULL")),
    Column("grupo_destino_id", Integer, ForeignKey("grupos.id", ondelete="SET NULL")),
    Column("fecha_movimiento", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("tipo_movimiento", String, nullable=False),
    Column("motivo", String),
    Column("usuario_registro_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    CheckConstraint(
        "tipo_movimiento IN ('TRASLADO', 'RETIRO', 'REINGRESO', 'GRADUACION')",
        name="ck_hist_tipo",
    ),
)

# ============================================================
# 4. PERIODOS Y ASIGNACIONES
# ============================================================

periodos = Table(
    "periodos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("nombre", String, nullable=False),
    Column("numero", Integer, nullable=False),
    Column("fecha_inicio", Date),
    Column("fecha_fin", Date),
    Column("peso_porcentual", Float, nullable=False, server_default="25.0"),
    Column("activo", Boolean, nullable=False, server_default="1"),
    Column("cerrado", Boolean, nullable=False, server_default="0"),
    Column("fecha_cierre_real", DateTime),
    UniqueConstraint("anio_id", "nombre"),
    UniqueConstraint("anio_id", "numero"),
    CheckConstraint("numero >= 1", name="ck_periodos_numero"),
    CheckConstraint("peso_porcentual > 0 AND peso_porcentual <= 100", name="ck_periodos_peso"),
    CheckConstraint(
        "fecha_inicio IS NULL OR fecha_fin IS NULL OR fecha_inicio <= fecha_fin",
        name="ck_periodos_fechas",
    ),
)

hitos_periodo = Table(
    "hitos_periodo", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("tipo", String, nullable=False, server_default="general"),
    Column("descripcion", String),
    Column("fecha_limite", Date),
    CheckConstraint(
        "tipo IN ('entrega_notas', 'inicio_habilitaciones', 'fin_habilitaciones',"
        " 'entrega_boletines', 'general')",
        name="ck_hitos_tipo",
    ),
)

asignaciones = Table(
    "asignaciones", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("grupo_id", Integer, ForeignKey("grupos.id", ondelete="CASCADE"), nullable=False),
    Column("asignatura_id", Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("activo", Boolean, nullable=False, server_default="1"),
    UniqueConstraint("grupo_id", "asignatura_id", "usuario_id", "periodo_id"),
)

logros = Table(
    "logros", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("descripcion", String, nullable=False),
    Column("orden", Integer, nullable=False, server_default="0"),
)

horarios = Table(
    "horarios", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("grupo_id", Integer, ForeignKey("grupos.id", ondelete="CASCADE"), nullable=False),
    Column("asignatura_id", Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="SET NULL")),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE")),
    Column("escenario_id", Integer, ForeignKey("escenarios_horario.id", ondelete="CASCADE"), nullable=False),
    Column("dia_semana", String, nullable=False),
    Column("hora_inicio", String, nullable=False),
    Column("hora_fin", String, nullable=False),
    Column("sala", String, nullable=False, server_default="Aula"),
    UniqueConstraint("escenario_id", "grupo_id", "dia_semana", "hora_inicio"),
    CheckConstraint(
        "dia_semana IN ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado')",
        name="ck_horarios_dia",
    ),
    CheckConstraint("hora_inicio < hora_fin", name="ck_horarios_horas"),
)

# ============================================================
# 5. EVALUACIÓN
# ============================================================

configuracion_siee = Table(
    "configuracion_siee", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("modo", String, nullable=False, server_default="libre"),
    Column("porcentaje_autonomia_docente", Float),
    UniqueConstraint("anio_id"),
    CheckConstraint(
        "modo IN ('libre', 'institucional_fijo', 'mixto_subcategorias', 'mixto_autonomia')",
        name="ck_siee_modo",
    ),
    CheckConstraint(
        "porcentaje_autonomia_docente IS NULL OR"
        " (porcentaje_autonomia_docente > 0 AND porcentaje_autonomia_docente <= 1)",
        name="ck_siee_pct",
    ),
)

categorias = Table(
    "categorias", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("peso", Float, nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE")),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE")),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE")),
    Column("es_institucional", Integer, nullable=False, server_default="0"),
    Column("permite_subcategorias", Integer, nullable=False, server_default="0"),
    Column("categoria_padre_id", Integer, ForeignKey("categorias.id", ondelete="SET NULL")),
    UniqueConstraint("nombre", "asignacion_id", "periodo_id"),
    CheckConstraint("peso > 0 AND peso <= 1", name="ck_cats_peso"),
    CheckConstraint("es_institucional IN (0,1)", name="ck_cats_institucional"),
    CheckConstraint("permite_subcategorias IN (0,1)", name="ck_cats_subcats"),
    CheckConstraint(
        "(asignacion_id IS NOT NULL AND periodo_id IS NOT NULL AND anio_id IS NULL)"
        " OR (asignacion_id IS NULL AND periodo_id IS NULL AND anio_id IS NOT NULL)",
        name="ck_cats_scope",
    ),
)

actividades = Table(
    "actividades", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("descripcion", String),
    Column("fecha", Date),
    Column("valor_maximo", Float, nullable=False, server_default="100.0"),
    Column("estado", String, nullable=False, server_default="borrador"),
    Column("categoria_id", Integer, ForeignKey("categorias.id", ondelete="CASCADE"), nullable=False),
    CheckConstraint("valor_maximo > 0", name="ck_acts_valor"),
    CheckConstraint("estado IN ('borrador', 'publicada', 'cerrada')", name="ck_acts_estado"),
)

notas = Table(
    "notas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("actividad_id", Integer, ForeignKey("actividades.id", ondelete="CASCADE"), nullable=False),
    Column("valor", Float, nullable=False),
    Column("usuario_registro_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    Column("fecha_registro", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("estudiante_id", "actividad_id"),  # D3: sin ON CONFLICT REPLACE
    CheckConstraint("valor >= 0 AND valor <= 100", name="ck_notas_valor"),
)

puntos_extra = Table(
    "puntos_extra", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("tipo", String, nullable=False, server_default="comportamental"),
    Column("positivos", Integer, nullable=False, server_default="0"),
    Column("negativos", Integer, nullable=False, server_default="0"),
    Column("observacion", String),
    Column("fecha_actualizacion", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("estudiante_id", "asignacion_id", "periodo_id", "tipo"),  # D3
    CheckConstraint("tipo IN ('comportamental', 'participacion', 'academico')", name="ck_puntos_tipo"),
    CheckConstraint("positivos >= 0", name="ck_puntos_pos"),
    CheckConstraint("negativos >= 0", name="ck_puntos_neg"),
)

# ============================================================
# 6. CIERRES Y PROMOCIÓN
# ============================================================

cierres_periodo = Table(
    "cierres_periodo", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False),
    Column("nota_definitiva", Float, nullable=False),
    Column("desempeno_id", Integer, ForeignKey("niveles_desempeno.id", ondelete="SET NULL")),
    Column("logro_id", Integer, ForeignKey("logros.id", ondelete="SET NULL")),
    Column("fecha_cierre", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("usuario_cierre_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("estudiante_id", "asignacion_id", "periodo_id"),  # D3
    CheckConstraint("nota_definitiva >= 0 AND nota_definitiva <= 100", name="ck_cierres_p_nota"),
)

cierres_anio = Table(
    "cierres_anio", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="RESTRICT"), nullable=False),
    Column("nota_promedio_periodos", Float, nullable=False),
    Column("nota_habilitacion", Float),
    Column("nota_definitiva_anual", Float, nullable=False),
    Column("perdio", Boolean, nullable=False, server_default="0"),
    Column("desempeno_id", Integer, ForeignKey("niveles_desempeno.id", ondelete="SET NULL")),
    Column("fecha_cierre", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("usuario_cierre_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("estudiante_id", "asignacion_id", "anio_id"),  # D3
    CheckConstraint(
        "nota_promedio_periodos >= 0 AND nota_promedio_periodos <= 100",
        name="ck_cierres_a_prom",
    ),
    CheckConstraint(
        "nota_habilitacion IS NULL OR (nota_habilitacion >= 0 AND nota_habilitacion <= 100)",
        name="ck_cierres_a_hab",
    ),
    CheckConstraint(
        "nota_definitiva_anual >= 0 AND nota_definitiva_anual <= 100",
        name="ck_cierres_a_def",
    ),
)

promocion_anual = Table(
    "promocion_anual", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="RESTRICT"), nullable=False),
    Column("estado", String, nullable=False, server_default="pendiente"),
    Column("asignaturas_perdidas", Integer, nullable=False, server_default="0"),
    Column("observacion", String),
    Column("fecha_decision", Date),
    Column("usuario_decision_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("estudiante_id", "anio_id"),  # D3
    CheckConstraint(
        "estado IN ('promovido', 'reprobado', 'condicional', 'pendiente')",
        name="ck_prom_estado",
    ),
)

# ============================================================
# 7. HABILITACIONES Y MEJORAMIENTO
# ============================================================

habilitaciones = Table(
    "habilitaciones", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="SET NULL")),
    Column("tipo", String, nullable=False),
    Column("nota_antes", Float),
    Column("nota_habilitacion", Float),
    Column("fecha", Date),
    Column("estado", String, nullable=False, server_default="pendiente"),
    Column("observacion", String),
    Column("usuario_registro_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    CheckConstraint("tipo IN ('periodo', 'anual')", name="ck_habil_tipo"),
    CheckConstraint(
        "nota_antes IS NULL OR (nota_antes >= 0 AND nota_antes <= 100)",
        name="ck_habil_nota_antes",
    ),
    CheckConstraint(
        "nota_habilitacion IS NULL OR (nota_habilitacion >= 0 AND nota_habilitacion <= 100)",
        name="ck_habil_nota",
    ),
    CheckConstraint(
        "estado IN ('pendiente', 'realizada', 'aprobada', 'reprobada')",
        name="ck_habil_estado",
    ),
    CheckConstraint("tipo != 'periodo' OR periodo_id IS NOT NULL", name="ck_habil_periodo_req"),
)

planes_mejoramiento = Table(
    "planes_mejoramiento", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("descripcion_dificultad", String, nullable=False),
    Column("actividades_propuestas", String, nullable=False),
    Column("fecha_inicio", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("fecha_seguimiento", Date),
    Column("fecha_cierre", Date),
    Column("estado", String, nullable=False, server_default="activo"),
    Column("observacion_cierre", String),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    CheckConstraint("estado IN ('activo', 'cumplido', 'incumplido')", name="ck_planes_estado"),
)

cortes_plan = Table(
    "cortes_plan", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("fecha_ejecucion", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("peso_registrado", Float, nullable=False),
    Column("nota_umbral", Float, nullable=False),
    Column("nota_minima_aprobacion", Float, nullable=False, server_default="60.0"),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("asignacion_id", "periodo_id"),
    CheckConstraint("peso_registrado > 0 AND peso_registrado <= 1", name="ck_cortes_peso"),
    CheckConstraint("nota_umbral >= 0", name="ck_cortes_umbral"),
)

notas_corte_plan = Table(
    "notas_corte_plan", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("corte_id", Integer, ForeignKey("cortes_plan.id", ondelete="CASCADE"), nullable=False),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("nota_al_corte", Float, nullable=False),
    Column("nota_definitiva_plan", Float),
    Column("estado", String, nullable=False, server_default="sin_plan"),
    Column("usuario_cierre_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("corte_id", "estudiante_id"),  # D3
    CheckConstraint("nota_al_corte >= 0", name="ck_notas_corte_al_corte"),
    CheckConstraint(
        "nota_definitiva_plan IS NULL OR nota_definitiva_plan >= 0",
        name="ck_notas_corte_def",
    ),
    CheckConstraint(
        "estado IN ('sin_plan', 'en_plan', 'aprobado', 'reprobado')",
        name="ck_notas_corte_estado",
    ),
)

actividades_plan = Table(
    "actividades_plan", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("corte_id", Integer, ForeignKey("cortes_plan.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("nombre", String, nullable=False),
    Column("descripcion", String),
    Column("peso", Float, nullable=False),
    Column("fecha", Date),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    CheckConstraint("peso > 0 AND peso <= 1", name="ck_act_plan_peso"),
)

notas_actividad_plan = Table(
    "notas_actividad_plan", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("actividad_plan_id", Integer, ForeignKey("actividades_plan.id", ondelete="CASCADE"), nullable=False),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("valor", Float),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("actividad_plan_id", "estudiante_id"),  # D3
    CheckConstraint(
        "valor IS NULL OR (valor >= 0 AND valor <= 100)",
        name="ck_nota_act_plan_valor",
    ),
)

actividades_nivelacion = Table(
    "actividades_nivelacion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("nombre", String, nullable=False),
    Column("descripcion", String),
    Column("peso", Float, nullable=False),
    Column("fecha", Date),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    CheckConstraint("peso > 0 AND peso <= 1", name="ck_act_nivel_peso"),
)

notas_nivelacion = Table(
    "notas_nivelacion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("actividad_nivelacion_id", Integer, ForeignKey("actividades_nivelacion.id", ondelete="CASCADE"), nullable=False),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("valor", Float),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("actividad_nivelacion_id", "estudiante_id"),  # D3
    CheckConstraint(
        "valor IS NULL OR (valor >= 0 AND valor <= 100)",
        name="ck_nota_nivel_valor",
    ),
)

cierres_nivelacion = Table(
    "cierres_nivelacion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("fecha_cierre", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("usuario_cierre_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("asignacion_id", "periodo_id"),
)

# ============================================================
# 8. ASISTENCIA Y CONVIVENCIA
# ============================================================

tipos_situacion = Table(
    "tipos_situacion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("nivel", Integer, nullable=False, server_default="1"),
    Column("descripcion", String),
    Column("protocolo", String),
    Column("activa", Boolean, nullable=False, server_default="1"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("institucion_id", "nombre"),
    CheckConstraint("nivel BETWEEN 1 AND 3", name="ck_tipos_sit_nivel"),
)

medidas_pedagogicas = Table(
    "medidas_pedagogicas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("descripcion", String),
    Column("nivel_minimo", Integer, nullable=False, server_default="1"),
    Column("activa", Boolean, nullable=False, server_default="1"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("institucion_id", "nombre"),
    CheckConstraint("nivel_minimo BETWEEN 1 AND 3", name="ck_medidas_nivel"),
)

categorias_observacion = Table(
    "categorias_observacion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, nullable=False),
    Column("es_comportamental", Boolean, nullable=False, server_default="0"),
    Column("activa", Boolean, nullable=False, server_default="1"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    UniqueConstraint("institucion_id", "nombre"),
)

plantillas_observacion = Table(
    "plantillas_observacion", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("texto", String, nullable=False),
    Column("categoria_id", Integer, ForeignKey("categorias_observacion.id", ondelete="SET NULL")),
    Column("uso_count", Integer, nullable=False, server_default="0"),
    Column("activa", Boolean, nullable=False, server_default="1"),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
)

control_diario = Table(
    "control_diario", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("grupo_id", Integer, ForeignKey("grupos.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("fecha", Date, nullable=False),
    Column("estado", String, nullable=False, server_default="P"),
    Column("hora_entrada", String),
    Column("hora_salida", String),
    Column("uniforme", Boolean, nullable=False, server_default="1"),
    Column("materiales", Boolean, nullable=False, server_default="1"),
    Column("observacion", String),
    Column("usuario_registro_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    Column("fecha_actualizacion", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("estudiante_id", "grupo_id", "asignacion_id", "fecha"),  # D3
    CheckConstraint("estado IN ('P', 'FJ', 'FI', 'R', 'E')", name="ck_ctrl_estado"),
)

# registro_comportamiento se declara antes que observaciones_periodo
# porque observaciones_periodo lo referencia
registro_comportamiento = Table(
    "registro_comportamiento", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("grupo_id", Integer, ForeignKey("grupos.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("fecha", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("tipo", String, nullable=False),
    Column("descripcion", String, nullable=False),
    Column("seguimiento", String),
    Column("requiere_firma", Boolean, nullable=False, server_default="0"),
    Column("acudiente_notificado", Boolean, nullable=False, server_default="0"),
    Column("usuario_registro_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    Column("tipo_situacion_id", Integer, ForeignKey("tipos_situacion.id", ondelete="SET NULL")),
    Column("medida_id", Integer, ForeignKey("medidas_pedagogicas.id", ondelete="SET NULL")),
    CheckConstraint(
        "tipo IN ('fortaleza', 'dificultad', 'compromiso', 'citacion_acudiente', 'descargo')",
        name="ck_reg_comp_tipo",
    ),
)

observaciones_periodo = Table(
    "observaciones_periodo", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("asignacion_id", Integer, ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("texto", String, nullable=False),
    Column("es_publica", Boolean, nullable=False, server_default="1"),
    Column("fecha_registro", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    Column("categoria_id", Integer, ForeignKey("categorias_observacion.id", ondelete="SET NULL")),
    Column("origen", String, nullable=False, server_default="libre"),
    Column("registro_comportamiento_id", Integer, ForeignKey("registro_comportamiento.id", ondelete="SET NULL")),
    CheckConstraint("origen IN ('libre', 'plantilla')", name="ck_obs_origen"),
)

entradas_seguimiento = Table(
    "entradas_seguimiento", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("registro_id", Integer, ForeignKey("registro_comportamiento.id", ondelete="CASCADE"), nullable=False),
    Column("fecha", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("texto", String, nullable=False),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
)

nota_comportamiento_periodo = Table(
    "nota_comportamiento_periodo", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("grupo_id", Integer, ForeignKey("grupos.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="CASCADE"), nullable=False),
    Column("valor", Float, nullable=False),
    Column("desempeno_id", Integer, ForeignKey("niveles_desempeno.id", ondelete="SET NULL")),
    Column("observacion", String),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("estudiante_id", "grupo_id", "periodo_id"),  # D3
    CheckConstraint("valor >= 0 AND valor <= 100", name="ck_nota_comp_valor"),
)

# ============================================================
# 9. ALERTAS
# ============================================================

configuracion_alertas = Table(
    "configuracion_alertas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("tipo_alerta", String, nullable=False),
    Column("umbral", Float, nullable=False),
    Column("activa", Boolean, nullable=False, server_default="1"),
    Column("notificar_docente", Boolean, nullable=False, server_default="1"),
    Column("notificar_director", Boolean, nullable=False, server_default="0"),
    Column("notificar_acudiente", Boolean, nullable=False, server_default="0"),
    UniqueConstraint("anio_id", "tipo_alerta"),
    CheckConstraint(
        "tipo_alerta IN ('faltas_injustificadas', 'promedio_bajo', 'materias_en_riesgo',"
        " 'plan_mejoramiento_vencido', 'habilitacion_pendiente', 'seguimiento_requerido')",
        name="ck_cfg_alertas_tipo",
    ),
)

alertas = Table(
    "alertas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("tipo_alerta", String, nullable=False),
    Column("nivel", String, nullable=False, server_default="advertencia"),
    Column("descripcion", String, nullable=False),
    Column("fecha_generacion", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("resuelta", Boolean, nullable=False, server_default="0"),
    Column("fecha_resolucion", DateTime),
    Column("usuario_resolucion_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    Column("observacion_resolucion", String),
    Column("usuario_destino_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    CheckConstraint(
        "tipo_alerta IN ('faltas_injustificadas', 'promedio_bajo', 'materias_en_riesgo',"
        " 'plan_mejoramiento_vencido', 'habilitacion_pendiente', 'seguimiento_requerido')",
        name="ck_alertas_tipo",
    ),
    CheckConstraint("nivel IN ('info', 'advertencia', 'critica')", name="ck_alertas_nivel"),
)

# ============================================================
# 10. INFORMES Y PIAR
# ============================================================

boletines_emitidos = Table(
    "boletines_emitidos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("periodo_id", Integer, ForeignKey("periodos.id", ondelete="SET NULL")),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("tipo", String, nullable=False),
    Column("fecha_generacion", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("fecha_entrega", Date),
    Column("entregado", Boolean, nullable=False, server_default="0"),
    Column("usuario_generador_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    CheckConstraint("tipo IN ('periodo', 'anual')", name="ck_boletines_tipo"),
    CheckConstraint("tipo != 'periodo' OR periodo_id IS NOT NULL", name="ck_boletines_periodo"),
)

piar = Table(
    "piar", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False),
    Column("anio_id", Integer, ForeignKey("configuracion_anio.id", ondelete="CASCADE"), nullable=False),
    Column("descripcion_necesidad", String, nullable=False),
    Column("ajustes_evaluativos", String),
    Column("ajustes_pedagogicos", String),
    Column("profesionales_apoyo", String),
    Column("fecha_elaboracion", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("fecha_revision", Date),
    Column("usuario_elaboracion_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    UniqueConstraint("estudiante_id", "anio_id"),
)

# ============================================================
# 11. AUDITORÍA
# ============================================================

auditoria = Table(
    "auditoria", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("usuario", String, nullable=False),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    Column("tipo_evento", String, nullable=False),
    Column("ip_address", String),
    Column("fecha_hora", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("detalles", String),
    Column("objetivo", String),
    Column("severidad", String, nullable=False, server_default="INFO"),
    Column("hash_cadena", String),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    CheckConstraint(
        "tipo_evento IN ('LOGIN_EXITOSO', 'LOGIN_FALLIDO', 'LOGOUT', 'CREAR_USUARIO',"
        " 'EDITAR_USUARIO', 'RESETEAR_PASSWORD', 'CAMBIAR_ROL', 'DESACTIVAR_USUARIO',"
        " 'ACTIVAR_USUARIO', 'ACCESO_DENEGADO', 'VER_COMO_INICIO', 'VER_COMO_FIN',"
        " 'AUDITORIA_EXPORTADA', 'AUDITORIA_PURGADA')",
        name="ck_auditoria_evento",
    ),
    CheckConstraint(
        "severidad IN ('INFO', 'ADVERTENCIA', 'CRITICA')",
        name="ck_auditoria_severidad",
    ),
)

audit_log = Table(
    "audit_log", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="SET NULL")),
    Column("usuario", String),
    Column("ip_address", String),
    Column("accion", String, nullable=False),
    Column("tabla", String, nullable=False),
    Column("registro_id", Integer),
    Column("valor_anterior", String),
    Column("valor_nuevo", String),
    Column("timestamp", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("hash_cadena", String),
    Column("institucion_id", Integer, ForeignKey("instituciones.id")),
    # D4: CHECK faltante
    CheckConstraint(
        "accion IN ('CREATE','UPDATE','DELETE','READ')",
        name="ck_audit_log_accion",
    ),
)

# Sin FKs — TEXT PRIMARY KEY
verificacion_auditoria = Table(
    "verificacion_auditoria", metadata,
    Column("tabla", String, primary_key=True),
    Column("ultimo_id", Integer, nullable=False),
    Column("ultimo_hash", String, nullable=False),
    Column("verificado_en", DateTime, nullable=False),
)

# ============================================================
# ÍNDICES
# ============================================================

# configuracion_anio
Index("idx_config_anio", configuracion_anio.c.anio)
Index("idx_config_institucion", configuracion_anio.c.institucion_id)
# usuarios
Index("idx_usuarios_institucion", usuarios.c.institucion_id)
# niveles_desempeno
Index("idx_niveles_anio", niveles_desempeno.c.anio_id)
# asignaturas
Index("idx_asig_area", asignaturas.c.area_id)
Index("idx_asig_institucion", asignaturas.c.institucion_id)
# grupos
Index("idx_grupos_institucion", grupos.c.institucion_id)
Index("idx_grupos_director", grupos.c.director_grupo_id)
# estudiantes
Index("idx_est_grupo", estudiantes.c.grupo_id)
Index("idx_est_estado", estudiantes.c.estado_matricula)
Index("idx_est_documento", estudiantes.c.numero_documento)
Index("idx_est_institucion", estudiantes.c.institucion_id)
# acudientes
Index("idx_acud_documento", acudientes.c.numero_documento)
# periodos
Index("idx_periodos_anio", periodos.c.anio_id)
Index("idx_periodos_activo", periodos.c.activo)
# asignaciones
Index("idx_asignac_usuario", asignaciones.c.usuario_id)
Index("idx_asignac_grupo", asignaciones.c.grupo_id)
Index("idx_asignac_asignatura", asignaciones.c.asignatura_id)
Index("idx_asignac_periodo", asignaciones.c.periodo_id)
# logros
Index("idx_logros_asignacion", logros.c.asignacion_id)
Index("idx_logros_periodo", logros.c.periodo_id)
# escenarios_horario — parcial único
Index(
    "idx_escenario_activo_unico",
    escenarios_horario.c.anio_id,
    unique=True,
    sqlite_where=text("activo = 1"),
)
Index("idx_escenarios_anio", escenarios_horario.c.anio_id)
# plantillas_franja / franjas — parcial único multi-tenant
Index(
    "idx_plantilla_activa_jornada",
    plantillas_franja.c.institucion_id,
    plantillas_franja.c.jornada,
    unique=True,
    sqlite_where=text("activa = 1"),
)
Index("idx_franjas_plantilla", franjas.c.plantilla_id)
Index("idx_plantilla_institucion", plantillas_franja.c.institucion_id)
# horarios
Index("idx_horarios_grupo", horarios.c.grupo_id)
Index("idx_horarios_usuario", horarios.c.usuario_id)
Index("idx_horarios_periodo", horarios.c.periodo_id)
Index("idx_horarios_escenario", horarios.c.escenario_id)
# categorias y actividades
Index("idx_cats_asignacion", categorias.c.asignacion_id)
Index("idx_cats_periodo", categorias.c.periodo_id)
Index("idx_acts_categoria", actividades.c.categoria_id)
Index("idx_acts_fecha", actividades.c.fecha)
# notas
Index("idx_notas_estudiante", notas.c.estudiante_id)
Index("idx_notas_actividad", notas.c.actividad_id)
Index("idx_notas_fecha", notas.c.fecha_registro)
# cierres_periodo
Index("idx_cierres_p_est", cierres_periodo.c.estudiante_id)
Index("idx_cierres_p_per", cierres_periodo.c.periodo_id)
Index("idx_cierres_p_asig", cierres_periodo.c.asignacion_id)
# cierres_anio
Index("idx_cierres_a_est", cierres_anio.c.estudiante_id)
Index("idx_cierres_a_anio", cierres_anio.c.anio_id)
# promocion_anual
Index("idx_prom_est", promocion_anual.c.estudiante_id)
Index("idx_prom_anio", promocion_anual.c.anio_id)
Index("idx_prom_estado", promocion_anual.c.estado)
# habilitaciones
Index("idx_habil_est", habilitaciones.c.estudiante_id)
Index("idx_habil_asig", habilitaciones.c.asignacion_id)
Index("idx_habil_estado", habilitaciones.c.estado)
# planes_mejoramiento
Index("idx_planes_est", planes_mejoramiento.c.estudiante_id)
Index("idx_planes_periodo", planes_mejoramiento.c.periodo_id)
Index("idx_planes_estado", planes_mejoramiento.c.estado)
# control_diario
Index("idx_ctrl_fecha", control_diario.c.fecha)
Index("idx_ctrl_estudiante", control_diario.c.estudiante_id)
Index("idx_ctrl_grupo", control_diario.c.grupo_id)
Index("idx_ctrl_asignacion", control_diario.c.asignacion_id)
Index("idx_ctrl_periodo", control_diario.c.periodo_id)
Index("idx_ctrl_estado", control_diario.c.estado)
# tipos_situacion
Index("idx_tipos_situacion_inst", tipos_situacion.c.institucion_id)
# medidas_pedagogicas
Index("idx_medidas_inst", medidas_pedagogicas.c.institucion_id)
# categorias_observacion
Index("ix_categorias_obs_activa", categorias_observacion.c.activa)
# plantillas_observacion
Index("ix_plantillas_obs_categoria", plantillas_observacion.c.categoria_id)
Index("ix_plantillas_obs_activa", plantillas_observacion.c.activa)
# observaciones_periodo
Index("idx_obs_estudiante", observaciones_periodo.c.estudiante_id)
Index("idx_obs_periodo", observaciones_periodo.c.periodo_id)
# registro_comportamiento
Index("idx_comp_estudiante", registro_comportamiento.c.estudiante_id)
Index("idx_comp_periodo", registro_comportamiento.c.periodo_id)
Index("idx_comp_tipo", registro_comportamiento.c.tipo)
Index("idx_comp_tipo_situacion", registro_comportamiento.c.tipo_situacion_id)
# entradas_seguimiento
Index("idx_seg_registro", entradas_seguimiento.c.registro_id)
Index("idx_seg_fecha", entradas_seguimiento.c.fecha)
# alertas
Index("idx_alertas_est", alertas.c.estudiante_id)
Index("idx_alertas_tipo", alertas.c.tipo_alerta)
Index("idx_alertas_resuelta", alertas.c.resuelta)
# historial_estudiantes
Index("idx_hist_estudiante", historial_estudiantes.c.estudiante_id)
Index("idx_hist_fecha", historial_estudiantes.c.fecha_movimiento)
# piar
Index("idx_piar_est", piar.c.estudiante_id)
Index("idx_piar_anio", piar.c.anio_id)
# auditoría
Index("idx_audit_usuario_id", auditoria.c.usuario_id)
Index("idx_audit_fecha", auditoria.c.fecha_hora)
Index("idx_audit_tipo", auditoria.c.tipo_evento)
Index("idx_auditoria_institucion", auditoria.c.institucion_id)
Index("idx_auditlog_usuario", audit_log.c.usuario_id)
Index("idx_auditlog_tabla", audit_log.c.tabla)
Index("idx_auditlog_timestamp", audit_log.c.timestamp)
Index("idx_audit_log_institucion", audit_log.c.institucion_id)
# actividades_nivelacion
Index("idx_act_nivel_asig", actividades_nivelacion.c.asignacion_id)
Index("idx_act_nivel_periodo", actividades_nivelacion.c.periodo_id)
# notas_nivelacion
Index("idx_nota_nivel_act", notas_nivelacion.c.actividad_nivelacion_id)
Index("idx_nota_nivel_est", notas_nivelacion.c.estudiante_id)
Index("idx_nota_nivel_asig", notas_nivelacion.c.asignacion_id)
# cierres_nivelacion
Index("idx_cierre_nivel_asig", cierres_nivelacion.c.asignacion_id)
# cortes_plan / plan de mejoramiento
Index("idx_cortes_plan_asig", cortes_plan.c.asignacion_id)
Index("idx_cortes_plan_per", cortes_plan.c.periodo_id)
Index("idx_notas_corte_corte", notas_corte_plan.c.corte_id)
Index("idx_notas_corte_est", notas_corte_plan.c.estudiante_id)
Index("idx_act_plan_corte", actividades_plan.c.corte_id)
Index("idx_notas_act_plan_act", notas_actividad_plan.c.actividad_plan_id)
Index("idx_notas_act_plan_est", notas_actividad_plan.c.estudiante_id)
# disponibilidad_docente
Index("idx_disponibilidad_docente", disponibilidad_docente.c.usuario_id, disponibilidad_docente.c.dia_semana)
# config_generacion
Index("idx_config_generacion_periodo", config_generacion.c.periodo_id, config_generacion.c.estado)
# salas
Index("idx_salas_tipo", salas.c.tipo)
Index("idx_salas_institucion", salas.c.institucion_id)
Index("idx_ventanas_grupo", ventanas_grupo.c.grupo_id)
Index("idx_ventanas_grado", ventanas_grupo.c.grado)
Index("idx_bloques_anclados_esc", bloques_anclados.c.escenario_id)
Index("idx_franjas_reunion", franjas_reunion.c.dia_semana, franjas_reunion.c.franja_orden)
Index("idx_limites_docente", limites_docente.c.usuario_id)
# plan_estudios
Index("idx_plan_estudios_grado", plan_estudios.c.grado)
# configuracion_grado_institucion
Index("idx_cfg_grado_inst", configuracion_grado_institucion.c.institucion_id)
# preferencias_institucion
Index("idx_pref_inst", preferencias_institucion.c.institucion_id)

# ============================================================
# TRIGGERS
# ============================================================

_tg_validar_peso_categorias = DDL("""
CREATE TRIGGER IF NOT EXISTS tg_validar_peso_categorias
BEFORE INSERT ON categorias
BEGIN
    SELECT RAISE(ABORT, 'La suma de pesos de las categorías supera el 100%%')
    WHERE (
        SELECT COALESCE(SUM(peso), 0)
        FROM   categorias
        WHERE  asignacion_id = NEW.asignacion_id
          AND  periodo_id    = NEW.periodo_id
    ) + NEW.peso > 1.001;
END
""")

_tg_validar_peso_categorias_update = DDL("""
CREATE TRIGGER IF NOT EXISTS tg_validar_peso_categorias_update
BEFORE UPDATE OF peso ON categorias
BEGIN
    SELECT RAISE(ABORT, 'La suma de pesos de las categorías supera el 100%%')
    WHERE (
        SELECT COALESCE(SUM(peso), 0)
        FROM   categorias
        WHERE  asignacion_id = NEW.asignacion_id
          AND  periodo_id    = NEW.periodo_id
          AND  id           != NEW.id
    ) + NEW.peso > 1.001;
END
""")

_tg_actualizar_ultima_sesion = DDL("""
CREATE TRIGGER IF NOT EXISTS tg_actualizar_ultima_sesion
AFTER INSERT ON auditoria
WHEN NEW.tipo_evento = 'LOGIN_EXITOSO' AND NEW.usuario_id IS NOT NULL
BEGIN
    UPDATE usuarios
    SET    ultima_sesion = CURRENT_TIMESTAMP
    WHERE  id = NEW.usuario_id;
END
""")

_tg_proteger_periodo_con_cierres = DDL("""
CREATE TRIGGER IF NOT EXISTS tg_proteger_periodo_con_cierres
BEFORE DELETE ON periodos
BEGIN
    SELECT RAISE(ABORT, 'No se puede eliminar un periodo con cierres de notas registrados')
    WHERE EXISTS (
        SELECT 1 FROM cierres_periodo WHERE periodo_id = OLD.id
    );
END
""")

_tg_proteger_nota_periodo_cerrado = DDL("""
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
""")

# D10: trigger BEFORE UPDATE separado para proteger notas en periodo cerrado
_tg_proteger_nota_periodo_cerrado_update = DDL("""
CREATE TRIGGER IF NOT EXISTS tg_proteger_nota_periodo_cerrado_update
BEFORE UPDATE ON notas
BEGIN
    SELECT RAISE(ABORT, 'No se pueden modificar notas en un periodo cerrado')
    WHERE EXISTS (
        SELECT 1
        FROM   actividades  act
        JOIN   categorias   cat ON cat.id = act.categoria_id
        JOIN   periodos     per ON per.id = cat.periodo_id
        WHERE  act.id  = NEW.actividad_id
          AND  per.cerrado = 1
    );
END
""")

_tg_resolver_alerta_aprobacion = DDL("""
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
""")

event.listen(metadata, "after_create", _tg_validar_peso_categorias.execute_if(dialect="sqlite"))
event.listen(metadata, "after_create", _tg_validar_peso_categorias_update.execute_if(dialect="sqlite"))
event.listen(metadata, "after_create", _tg_actualizar_ultima_sesion.execute_if(dialect="sqlite"))
event.listen(metadata, "after_create", _tg_proteger_periodo_con_cierres.execute_if(dialect="sqlite"))
event.listen(metadata, "after_create", _tg_proteger_nota_periodo_cerrado.execute_if(dialect="sqlite"))
event.listen(metadata, "after_create", _tg_proteger_nota_periodo_cerrado_update.execute_if(dialect="sqlite"))
event.listen(metadata, "after_create", _tg_resolver_alerta_aprobacion.execute_if(dialect="sqlite"))

# ============================================================
# FUNCIONES DE INICIALIZACIÓN
# ============================================================


def create_schema(conn) -> None:
    """Aplica el schema a una conexión SQLite ya abierta. Idempotente."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        creator=lambda: conn,
        poolclass=StaticPool,
    )
    metadata.create_all(engine)


def init_db(db_path=None) -> bool:
    """Inicializa el esquema completo en la BD configurada."""
    from .connection import get_connection

    try:
        with get_connection() as conn:
            create_schema(conn)
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                logger.error(f"Integridad de BD fallida: {result[0]}")
                return False
            conn.commit()
            logger.info(f"Schema inicializado — {len(metadata.tables)} tablas")
            return True
    except Exception as exc:
        logger.error(f"Error crítico inicializando schema: {exc}")
        return False


def get_db_stats() -> dict:
    """Retorna conteo de filas por tabla."""
    from .connection import DB_PATH, get_connection

    try:
        with get_connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            stats = {
                t[0]: conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
                for t in tables
            }
            if DB_PATH.exists():
                stats["_db_size_mb"] = round(DB_PATH.stat().st_size / (1024**2), 2)
            return stats
    except Exception as exc:
        logger.error(f"Error obteniendo estadísticas: {exc}")
        return {}


__all__ = ["metadata", "create_schema", "get_db_stats", "init_db"]
