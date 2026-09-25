"""
src/domain/tablas_auditables.py
================================
Catálogo: nombre físico de tabla → etiqueta de negocio legible.

Fuente única de verdad (R4). Patrón análogo a ``src/domain/modulos.py``.

Regla: **toda clave de ``ETIQUETAS_TABLA`` debe existir como tabla física en
``src/infrastructure/db/schema.py``**. El test ``test_tablas_auditables.py``
lo verifica automáticamente para evitar entradas muertas.

Las tablas auditadas que no estén en el catálogo se muestran con su nombre
físico como fallback (R5).
"""
from __future__ import annotations

# ─── Catálogo ─────────────────────────────────────────────────────────────────
# Ordenado alfabéticamente por clave para facilitar búsquedas visuales.
# Solo se incluyen tablas que existen en SCHEMA (verificado por el test).

ETIQUETAS_TABLA: dict[str, str] = {
    "actividades": "Actividades de evaluación",
    "actividades_nivelacion": "Actividades de nivelación",
    "actividades_plan": "Actividades de plan de mejoramiento",
    "alertas": "Alertas del sistema",
    "areas_conocimiento": "Áreas de conocimiento",
    "asignaciones": "Asignaciones docentes",
    "asignaturas": "Asignaturas",
    "bloques_anclados": "Bloques anclados en horario",
    "categorias": "Categorías de evaluación",
    "categorias_observacion": "Categorías de observación",
    "cierres_nivelacion": "Cierres de nivelación",
    "cierres_periodo": "Cierres de periodo",
    "config_generacion": "Configuración de generación de horario",
    "configuracion_alertas": "Configuración de alertas",
    "configuracion_anio": "Configuración del año escolar",
    "configuracion_siee": "Configuración SIEE",
    "control_diario": "Registro de asistencia",
    "cortes_plan": "Cortes de plan de mejoramiento",
    "criterios_promocion": "Criterios de promoción",
    "disponibilidad_docente": "Disponibilidad docente",
    "entradas_seguimiento": "Entradas de seguimiento",
    "escenarios_horario": "Escenarios de horario",
    "estudiantes": "Estudiantes",
    "franjas": "Franjas horarias",
    "franjas_reunion": "Franjas de reunión docente",
    "grados": "Grados",
    "grupos": "Grupos",
    "habilitaciones": "Habilitaciones",
    "horarios": "Horarios",
    "instituciones": "Instituciones",
    "limites_docente": "Límites de carga docente",
    "niveles_desempeno": "Niveles de desempeño",
    "nota_comportamiento_periodo": "Notas de comportamiento",
    "notas": "Notas",
    "notas_corte_plan": "Notas de corte de plan",
    "notas_nivelacion": "Notas de nivelación",
    "observaciones_periodo": "Observaciones de convivencia",
    "periodos": "Periodos académicos",
    "piar": "PIAR",
    "plan_estudios": "Plan de estudios",
    "planes_mejoramiento": "Planes de mejoramiento",
    "plantillas_franja": "Plantillas de franja horaria",
    "plantillas_observacion": "Plantillas de observación",
    "promocion_anual": "Promoción anual",
    "registro_comportamiento": "Registros de comportamiento",
    "salas": "Salas",
    "tipos_situacion": "Tipos de situación de convivencia",
    "usuarios": "Cuentas de usuario",
    "ventanas_grupo": "Ventanas de grupo",
}


def etiqueta_de_tabla(tabla: str) -> str:
    """Etiqueta legible para la tabla, o el nombre físico si no está catalogada (R5)."""
    return ETIQUETAS_TABLA.get(tabla, tabla)


__all__ = ["ETIQUETAS_TABLA", "etiqueta_de_tabla"]
