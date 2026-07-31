# Requisitos: Backups automatizados y plan de rollback (seguridad_web_10)

> **Nivel:** N1 — Primer mes en producción
> **Dificultad:** Infra (configuración del servidor; cero código Python)
> **Depende de:** S01, S02 (servidor de producción operativo)
> **Relacionado con:** S11 (CI/CD define qué versión de código rollbackear)

## Contexto del problema

Un backup que no se ha restaurado nunca no es un backup: es esperanza. Un plan de
rollback que no se ha ensayado no es un plan: es un documento. La pérdida de datos
o la incapacidad de volver a una versión anterior son riesgos de negocio, no solo
técnicos. Este spec exige que ambos mecanismos existan y estén probados antes del
segundo mes en producción.

## Requisitos

### Backups de base de datos

R1: EL SERVIDOR DEBE ejecutar `pg_dump` (o el snapshot del proveedor cloud) de forma
    automática con frecuencia mínima diaria. La retención mínima es de 30 días de
    backups diarios.

R2: LOS BACKUPS DEBEN almacenarse en una ubicación separada del servidor de producción
    (bucket S3, otro VPS, NAS externo). Un fallo del servidor de producción NO debe
    afectar a los backups.

R3: LOS BACKUPS DEBEN estar cifrados en reposo. Si el proveedor cloud cifra el
    almacenamiento, documentar qué clave se usa y quién tiene acceso.

R4: LA RESTAURACIÓN DEBE probarse al menos una vez antes del primer mes en producción
    y luego trimestralmente. Una restauración exitosa significa: levantar la app contra
    la BD restaurada y verificar que los datos son consistentes.

R5: EL TIEMPO DE RECUPERACIÓN OBJETIVO (RTO) debe estar documentado: cuánto tiempo
    tarda restaurar el último backup en una BD nueva. El objetivo recomendado es < 2 horas.

### Rollback de código

R6: CADA DEPLOY A PRODUCCIÓN DEBE estar etiquetado con un tag de git (`git tag`)
    para poder hacer `git checkout <tag>` y redesplegar la versión anterior en minutos.

R7: EL PROCESO DE ROLLBACK DE CÓDIGO DEBE estar documentado paso a paso en
    `docs/operaciones.md` (o equivalente). No debe requerir conocimiento implícito:
    cualquier persona con acceso al servidor debe poder ejecutarlo.

R8: EL ROLLBACK DEBE ser posible en menos de 15 minutos desde la decisión hasta
    tener la versión anterior sirviendo tráfico.

### Alertas de integridad

R9: EL SISTEMA DEBE alertar (email, Slack, o SMS) si el backup diario no se ejecuta
    o falla. Una semana sin backups no debe pasar desapercibida.

R10: LA CADENA DE AUDITORÍA EXISTENTE (`audit_chain.py`) DEBE incluirse en los
     backups. La integridad de la cadena DEBE verificarse automáticamente tras
     cada restauración.

## Criterio de done

- Backup automático diario ejecutándose y almacenado en ubicación externa.
- Restauración exitosa documentada (screenshot o log de la prueba).
- `docs/operaciones.md` tiene el procedimiento de rollback de código paso a paso.
- Alerta configurada para fallo de backup.
