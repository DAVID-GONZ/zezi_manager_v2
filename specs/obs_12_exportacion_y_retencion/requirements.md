# Requisitos: Exportación verificable y retención de la bitácora (obs_12)

> **Contexto:** `roadmaps/obs_00_roadmap_observabilidad/roadmap.md` — hallazgos
> B6, C7 y A2.
> **Depende de:** `obs_08` (conteos y verificación incremental), `obs_09`
> (diff y etiquetas) y `obs_11` (scope obligatorio).
> **Alcance:** un servicio de exportación, uno de retención, dos métodos de
> repositorio y los controles en las dos páginas de bitácora.

## Los tres defectos que este paso cierra

### D1 — La evidencia no sale del sistema

No hay ninguna forma de exportar la bitácora. Un proceso disciplinario bajo la
Ley 1620, una queja de un acudiente o una visita de la Secretaría exigen
entregar constancia de quién hizo qué y cuándo; hoy la única salida es abrir el
archivo SQLite. Y una copia en texto plano no prueba nada: el valor probatorio
de esta bitácora está en la cadena SHA-256, que un CSV pelado deja atrás.

### D2 — La bitácora crece sin límite ni política

El repositorio no expone purga ni archivado, y el puerto declara la auditoría
como append-only sin excepciones. Con la huella universal de `obs_04` sobre
60 480 notas y 3 920 registros de asistencia, `audit_log` crece de forma
monótona y sin techo. Conservar indefinidamente datos personales de menores no
es un descuido técnico: es lo que la Ley 1581 no permite dejar sin declarar.

### D3 — El admin se audita a sí mismo

El mismo rol que crea directores es el único que lee la bitácora donde consta
que los creó y el único que puede verificar su cadena. La respuesta razonable
con un solo operador no es inventar un rol de auditor sin auditor detrás: es
que la evidencia pueda salir del sistema en un formato comprobable por un
tercero que no confíe en el sistema.

---

R1: EL SISTEMA DEBE exportar el resultado del filtro activo de la bitácora a
    CSV y a PDF, respetando el `TenantScope` de quien exporta.

R2: LA EXPORTACIÓN DEBE incluir una **hoja de verificación** con: rango de
    identificadores y de fechas exportado, número de filas, hash SHA-256 del
    contenido exportado, el `hash_cadena` de la primera y la última fila, y el
    veredicto de integridad del tramo en el momento de exportar.

R3: EL SISTEMA DEBE ofrecer un procedimiento documentado, ejecutable por un
    tercero sin acceso a la aplicación, para recomputar la cadena del tramo
    exportado y confrontarla con la hoja de verificación.

R4: CUANDO la verificación del tramo falle, la exportación DEBE producirse
    igualmente y la hoja de verificación DEBE decirlo. Una bitácora alterada
    es justo la que hay que poder entregar.

R5: LA EXPORTACIÓN DEBE quedar auditada: genera un evento de sesión con el
    actor, el rango exportado, el formato y el número de filas. Exportar la
    bitácora es un hecho de la bitácora.

R6: LA EXPORTACIÓN NO DEBE incluir los campos marcados como sensibles por el
    diff de `obs_09`.

R7: EL SISTEMA DEBE imponer un tope de filas por exportación, configurable,
    y DEBE informar al usuario cuando el filtro activo lo supere, en lugar de
    truncar en silencio.

R8: EL SISTEMA DEBE permitir declarar una **ventana de retención** en meses
    por institución, con un valor por defecto conservador y la posibilidad de
    desactivarla.

R9: LA PURGA DE FILAS antiguas SOLO DEBE ejecutarse después de un archivado
    correcto: primero se escribe el archivo firmado, se verifica su hash, y
    solo entonces se eliminan las filas.

R10: LA PURGA DEBE registrar un evento con el rango eliminado, el número de
     filas, la ruta del archivo y su hash, de modo que la ausencia de esas
     filas quede explicada dentro de la propia bitácora.

R11: LA PURGA DEBE actualizar el punto de control de `obs_08` para que la
     verificación posterior no interprete el hueco como una cadena rota.

R12: LA PURGA NO DEBE ser automática ni silenciosa. Se ejecuta a petición
     explícita de un actor autorizado, con confirmación previa que muestre
     cuántas filas se van a archivar y hasta qué fecha.

R13: SOLO EL ROL `admin` DEBE poder purgar. Director y coordinador exportan;
     no eliminan.

R14: EL SISTEMA DEBE declarar en la documentación del paso la limitación
     conocida que el archivado no resuelve: el truncado del final de la cadena
     no es detectable sin un ancla externa, tal y como ya advierte
     `audit_chain.py`.

## Criterio de done

- Un director exporta a CSV el rango filtrado y obtiene los datos más una hoja
  de verificación con hashes y veredicto.
- Un tercero, siguiendo el procedimiento documentado y sin acceso a la app,
  recomputa la cadena del tramo y obtiene el mismo resultado.
- La exportación deja su propio rastro en la bitácora.
- Un filtro que supere el tope avisa al usuario en lugar de truncar.
- Un admin archiva y purga un tramo antiguo: el archivo existe, su hash cuadra,
  las filas desaparecen, el evento de purga las explica y la verificación de
  integridad posterior sigue en verde.
- Un director no ve el control de purga.
- `python scripts/init.py` completamente verde.
