# Requisitos: Panel de observabilidad de plataforma (obs_13)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgos
> C2, C4, C5 y C9.
> **Depende de:** `obs_06` (el log de seguridad se escribe y la IP existe) y
> `obs_08` (KPIs en SQL).
> **Alcance:** un servicio de observabilidad, un lector de log en
> infraestructura con su puerto, una página nueva y la exposición de las
> alertas de IP. No toca la bitácora.

## Los cuatro defectos que este paso cierra

### D1 — `/diagnostico` mide instanciación, no salud

`Container.diagnostico()` construye todos los servicios y reporta OK/ERROR por
componente. Eso responde «¿arranca la aplicación?», que es una pregunta de
despliegue, no de operación. No hay tamaño de base, ni último backup, ni
versión, ni uptime, ni errores recientes, ni nada que cambie entre dos
recargas de la página.

### D2 — `/health` está bien hecho y nadie lo ve

Devuelve 503 cuando `verify_db_integrity()` falla. Es correcto y no está
expuesto en ninguna pantalla ni monitorizado: el único consumidor posible hoy
es alguien que conozca la URL y la pida a mano.

### D3 — El log de seguridad es un archivo que nadie abre

`obs_03` produce JSONL estructurado en disco. El destinatario del producto es
el rector de un colegio; ese archivo no lo va a leer nunca. Toda la
observabilidad real vive fuera de la aplicación.

### D4 — Las alertas no llegan a ningún sitio

`alerta_ip` emite un `WARNING` a `zeci.security` cuando una IP acumula cinco
fallos de login en cinco minutos. Ese aviso va al archivo de D3, que además
estaba apagado por defecto hasta `obs_06` y que nunca se disparaba porque la
IP era nula. `obs_06` reactiva la emisión; este paso le da un destinatario.

---

R1: EL SISTEMA DEBE ofrecer la ruta `/admin/observabilidad` con
    `roles={Rol.ADMIN}`, registrada mediante `registrar_pagina`.

R2: LA PÁGINA DEBE mostrar el estado de salud del sistema: veredicto de
    `/health`, versión de la aplicación, tiempo en marcha del proceso, tamaño
    del archivo de base de datos y fecha del último backup conocido.

R3: CUANDO no exista información de backup, la página DEBE decirlo de forma
    explícita («sin backup registrado»), no mostrar un hueco ni un cero.

R4: LA PÁGINA DEBE mostrar los últimos N registros del log de seguridad, con
    filtro por nivel y por tipo de evento, leídos desde el archivo JSONL.

R5: LA LECTURA DEL LOG DEBE hacerse desde infraestructura, tras un puerto de
    dominio (`ILogReader`). Ni el servicio ni la interfaz abren archivos.

R6: LA LECTURA DEL LOG DEBE leer solo la cola del archivo, con un tope de
    bytes, y NO DEBE cargar en memoria un archivo rotado de 10 MB completo.

R7: CUANDO el archivo de log no exista o no sea legible, la página DEBE
    mostrar un estado vacío explicativo indicando la ruta configurada, no un
    error genérico.

R8: LA PÁGINA NO DEBE mostrar ningún campo fuera de la whitelist
    `_CAMPOS_PERMITIDOS` del logger. Si una línea trae campos desconocidos, se
    ignoran.

R9: `alerta_ip` DEBE exponer `alertas_activas()`, que devuelve las IP con
    fallos dentro de la ventana vigente y su conteo, sin mutar el estado.

R10: LA PÁGINA DEBE mostrar las alertas de IP activas con su conteo y el
     tiempo restante de ventana, y DEBE permitir limpiar el estado de una IP
     concreta.

R11: LIMPIAR UNA ALERTA DE IP DEBE quedar auditado: quién la limpió y cuál.

R12: LA PÁGINA DEBE mostrar los KPIs de uso de `obs_08` con su evolución
     diaria en la ventana, no solo el total.

R13: LA PÁGINA DEBE ser fail-open por bloque: si una sección falla —log
     ilegible, base inaccesible— las demás se renderizan igualmente y la
     fallida muestra su propio error.

R14: EL PRESENTER NO DEBE contener reglas de negocio. El cálculo de uptime, el
     tamaño de la base, el parseo del log y la agregación de KPIs viven en el
     servicio o en infraestructura.

R15: LA PÁGINA `/diagnostico` DEBE conservarse tal cual, con su diagnóstico de
     `Container` y el lanzador «Ver como». No se fusiona ni se elimina: son
     dos preguntas distintas.

## Criterio de done

- Un admin abre `/admin/observabilidad` y ve el estado de salud, el tamaño de
  la base, la versión y el uptime, y esos valores cambian entre recargas.
- Corromper la base hace que el bloque de salud pase a rojo y refleje el 503.
- Los últimos eventos de seguridad se listan y se pueden filtrar por nivel.
- Provocar cinco fallos de login desde la misma IP hace aparecer una alerta
  activa en la página; limpiarla la retira y deja rastro en la bitácora.
- Borrar el archivo de log deja esa sección con su estado vacío y no rompe el
  resto de la página.
- `python scripts/init.py` completamente verde.
