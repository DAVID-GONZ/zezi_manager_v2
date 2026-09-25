# Requisitos: Verificación incremental y agregados en SQL (obs_08)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgos
> B9, B7 y C8.
> **Depende de:** `obs_06` (la base se recrea allí; la cadena arranca de nuevo).
> **Alcance:** el puerto `IAuditoriaRepository`, su implementación SQLite, el
> servicio de auditoría y los dos consumidores de KPI. No toca la UI de la
> bitácora más allá de lo que exige mostrar el total.

## Los tres defectos que este paso cierra

### D1 — «Verificar integridad» materializa la tabla entera

`sqlite_auditoria_repo._verificar_cadena` ejecuta
`SELECT * FROM {tabla} WHERE hash_cadena IS NOT NULL ORDER BY id ASC`,
construye en memoria la lista completa de `(payload, hash)` y recalcula la
cadena entera, todo de forma síncrona dentro de la petición HTTP que atiende el
botón de la UI. Hoy no se nota: `audit_log` tiene 6 filas. Con la cobertura
universal de `obs_04` sobre un volumen real —60 480 notas, 3 920 registros de
asistencia— cada pulsación bloquea el hilo y congela la interfaz.

### D2 — No existe ningún conteo

El repositorio no expone ningún `contar_*`. La paginación que introdujo
`obs_05` es look-ahead: sabe si hay página siguiente, no cuántas hay. No se
puede mostrar «Página 3 de 47», ni saltar al final, ni dimensionar una
exportación antes de lanzarla.

### D3 — Los KPIs del dashboard ya son incorrectos

`AuditoriaService.resumen_uso` pide
`FiltroAuditoriaDTO(desde=..., pagina=1, por_pagina=500)` y agrega en Python.
Con 484 denegaciones medidas en nueve días, el techo de 500 ya está tocado: los
tres números que ve el admin se calculan sobre una muestra truncada y no
declarada. Además el cálculo ignora el tenant, aunque hoy solo lo consuma un
rol cross-tenant.

---

R1: `IAuditoriaRepository` DEBE exponer `contar_eventos(filtro)` y
    `contar_cambios(filtro)`, que devuelven el total de filas que satisfacen el
    filtro **ignorando `pagina` y `por_pagina`**.

R2: `IAuditoriaRepository` DEBE exponer `resumen_eventos(desde, hasta,
    institucion_id)`, que devuelve los agregados de uso calculados en SQL:
    conteo por `tipo_evento`, conteo de logins del día en curso y número de
    usuarios distintos con login en la ventana.

R3: LOS MÉTODOS NUEVOS DEBEN ser concretos y no abstractos en el puerto, con un
    valor por defecto neutro, siguiendo el precedente de
    `verificar_cadena_eventos`: los dobles de test existentes los heredan sin
    modificarse.

R4: `AuditoriaService.resumen_uso` DEBE apoyarse en `resumen_eventos` y NO DEBE
    recorrer eventos en Python. El techo de 500 filas desaparece.

R5: `resumen_uso` DEBE aceptar un `TenantScope` explícito y propagarlo al
    repositorio.

R6: LA VERIFICACIÓN DE CADENA DEBE ser incremental: el sistema persiste un
    punto de control por tabla (`ultimo_id_verificado`, `hash_en_ese_punto`,
    `verificado_en`) y reanuda desde él, usando el hash almacenado como
    semilla, en lugar de recalcular desde el primer registro.

R7: LA VERIFICACIÓN DEBE leer por lotes acotados (`LIMIT` por bloque) y NO DEBE
    materializar la tabla completa en memoria en ningún momento.

R8: EL SISTEMA DEBE seguir ofreciendo una verificación completa desde el origen,
    invocable de forma explícita, para el caso en que se sospeche manipulación
    de un tramo ya verificado.

R9: LA VERIFICACIÓN INCREMENTAL DEBE declarar su alcance en la UI: informa de
    qué rango de identificadores cubre y desde cuándo, de modo que nadie
    confunda «íntegra desde el último punto de control» con «íntegra entera».

R10: CUANDO la verificación detecte un eslabón roto, el punto de control NO
     DEBE avanzar. Un fallo no se convierte en el nuevo suelo de confianza.

R11: LA PÁGINA `/admin/auditoria` DEBE mostrar el total de resultados del
     filtro activo junto a los controles de paginación.

R12: EL SISTEMA DEBE incluir un test de rendimiento con al menos 50 000 filas
     sembradas que verifique que una verificación incremental sin cambios
     pendientes responde por debajo de un umbral declarado.

## Criterio de done

- Con 50 000 filas en `audit_log`, pulsar «Verificar integridad» dos veces
  seguidas: la primera recorre la tabla, la segunda responde de inmediato.
- Alterar por SQL una fila anterior al punto de control y lanzar la
  verificación completa → devuelve el `id` roto; el punto de control no avanza.
- El dashboard de admin muestra KPIs calculados sobre toda la ventana, no sobre
  las primeras 500 filas.
- La bitácora muestra «N resultados» acorde al filtro activo.
- `python scripts/init.py` completamente verde.
