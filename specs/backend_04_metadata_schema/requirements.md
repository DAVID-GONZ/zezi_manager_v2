# Requisitos: MetaData schema (backend_04_metadata_schema)

> Ámbito: reescribir el esquema de `schema.py` (1,654 líneas de DDL strings,
> 65 tablas) como `MetaData`/`Table` de SQLAlchemy Core. Fuente única de
> esquema que sirve a SQLite y futuro Postgres. Resuelve D1–D5 y D10–D12
> de la auditoría y absorbe `tenant_05_desnormalizacion_transitivas`.
>
> ⚠️ PUERTA DE APROBACIÓN: este paso toca el esquema → requiere aprobación
> de David antes de pasar a `in_progress`.

---

## Fuente única de esquema

R1: EL SISTEMA DEBE definir toda tabla, columna, constraint, índice y trigger
    como objetos de SQLAlchemy Core (`Table`, `Column`, `Index`, `ForeignKey`,
    `CheckConstraint`, `UniqueConstraint`) en un único `MetaData`.

R2: EL SISTEMA NO DEBE mantener strings DDL de SQLite como fuente de
    esquema. Las listas `SCHEMA`, `INDICES` y `TRIGGERS` de `schema.py`
    se eliminan.

R3: `metadata.create_all(engine)` DEBE generar un esquema equivalente al
    actual en SQLite — mismas tablas, mismas columnas, mismas FKs, mismos
    índices.

---

## Tipos neutros

R4: LOS tipos de columna DEBEN usar tipos genéricos de SQLAlchemy
    (`Integer`, `String`, `Boolean`, `Date`, `DateTime`, `Numeric`, `Text`)
    en lugar de tipos específicos de SQLite (`AUTOINCREMENT`, `REAL`, etc.).

R5: LAS columnas de notas DEBEN usar `Numeric(4, 2)` (no `Float`),
    coherente con la migración a `Decimal` de `datos_04`.

R6: LAS columnas de fecha/hora DEBEN usar `Date` o `DateTime` sin
    `DEFAULT CURRENT_DATE` — los defaults los controla el dominio con
    zona horaria correcta (resuelto en `datos_08`).

---

## Resolución de defectos

R7: EL orden de las tablas en el `MetaData` DEBE respetar las
    dependencias FK. `create_all()` ordena automáticamente, pero la
    organización del código fuente debe ser legible (D1).

R8: `grupos.sala_id` DEBE tener una `ForeignKey` real o eliminarse
    si la relación no existe (D2).

R9: TODA tabla con `ON CONFLICT REPLACE` DEBE reescribirse con
    `UniqueConstraint` estándar. Los upserts se resuelven en los repos
    con `INSERT ... ON CONFLICT DO UPDATE` (D3).

R10: LOS 5 `CHECK` constraints de deuda (`AccionCambio`, `Calendario`,
     `CategoriaPreferencia`, `JornadaPrincipal`, `TipoInstitucion`) DEBEN
     añadirse al `MetaData` (D4).

R11: `institucion_id` DEBE ser `NOT NULL` en las tablas de scope que hoy
     lo tienen nullable, excepto donde haya justificación explícita (D5).

R12: EL trigger `tg_proteger_nota_periodo_cerrado` DEBE cubrir `UPDATE`
     además de `INSERT` (D10).

---

## Compatibilidad

R13: LOS tests de esquema de `backend_02b` DEBEN seguir verdes (ahora sin
     `xfail`) — la verificación contra `sqlite_master` valida la equivalencia.

R14: EL seed (`seed_test`, `seed_dev`) DEBE seguir funcionando tras la
     migración del schema.

R15: LOS repositorios existentes (SQL crudo) DEBEN seguir funcionando
     contra el schema generado por `create_all()`. No se tocan en este paso.

---

## Organización

R16: EL `MetaData` DEBE organizarse por módulo funcional (los mismos 11
     módulos del schema actual: configuración, infraestructura, usuarios,
     periodos, evaluación, cierres, habilitaciones, asistencia/convivencia,
     alertas, informes, auditoría).

R17: CADA tabla DEBE tener un docstring o comentario que indique su módulo
     funcional.
