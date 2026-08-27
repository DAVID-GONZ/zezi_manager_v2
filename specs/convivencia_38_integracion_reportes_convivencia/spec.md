# convivencia_38_integracion_reportes_convivencia — Spec

## Contexto

Los specs convivencia_34 (tipos_situacion), convivencia_35 (entradas_seguimiento)
y convivencia_36 (medidas_pedagogicas) agregan datos nuevos al modelo de
convivencia. Los reportes existentes — boletin de periodo, boletin anual,
reporte de convivencia por grupo — no reflejan estos datos nuevos.

Esta spec integra la clasificacion de situaciones y las medidas pedagogicas
en los reportes existentes, y enriquece el reporte de grupo con un desglose
por tipo de situacion.

Scope:
- `src/services/convivencia_service.py` (MODIFICAR — paquetes de boletin
  y reporte de grupo)
- `src/infrastructure/exporters/boletin_pdf.py` (MODIFICAR — renderizado
  de eventos)
- `src/domain/models/convivencia.py` (EXTENDER — DTOs de reporte)
- `tests/` (EXTENDER)

## Requisitos (EARS)

### Paquetes de boletin

- **R1** — `_registros_informables_periodo` DEBE incluir en cada dict de
  registro los campos `tipo_situacion` (nombre del tipo o None) y `medida`
  (nombre de la medida o None), ademas de los existentes `fecha`, `tipo`,
  `descripcion`.
- **R2** — `paquete_boletin_periodo` y `paquete_boletin_anual` DEBEN
  propagar los campos nuevos sin romper la estructura existente.

### PDF del boletin

- **R3** — En la sub-seccion "EVENTOS DE CONVIVENCIA" del PDF del boletin
  (`boletin_pdf._observaciones_y_firmas`), cada evento DEBE mostrarse con
  la clasificacion y medida cuando existan:
  ```
  - 2026-03-15 · Dificultad [Tipo II]: Descripcion del evento.
    Medida: Citacion a acudiente
  ```
  Si no hay tipo_situacion, se omite el corchete. Si no hay medida, se
  omite la linea de medida.

### Reporte de grupo

- **R4** — `ReporteConvivenciaFilaDTO` DEBE incluir un campo opcional
  `desglose_por_tipo: dict[str, int] | None` que contenga el conteo de
  registros negativos desglosado por nombre de tipo_situacion. None si
  no hay tipos configurados.
- **R5** — `reporte_periodo_grupo` DEBE poblar `desglose_por_tipo` para
  cada estudiante.
- **R6** — La exportacion Excel del reporte de grupo DEBE incluir columnas
  adicionales por cada tipo de situacion con el conteo.
- **R7** — La exportacion PDF del reporte de grupo DEBE incluir las
  columnas de desglose si hay datos.

## Diseno

### T1 — Enriquecer `_registros_informables_periodo`

En `convivencia_service.py`, modificar `_registros_informables_periodo`:
- Cargar tipos_situacion y medidas como dicts `{id: nombre}` (una sola
  vez por llamada).
- Al construir cada dict de resultado, agregar:
  ```python
  "tipo_situacion": tipos_map.get(r.tipo_situacion_id, None),
  "medida": medidas_map.get(r.medida_id, None),
  ```
- Si `tipo_situacion_id` o `medida_id` son None → el valor es None.

### T2 — Actualizar `boletin_pdf._observaciones_y_firmas`

En la iteracion de `registros`:
- Construir el texto del evento incluyendo clasificacion:
  ```python
  texto = f"- {ev['fecha']} · {ev['tipo']}"
  if ev.get("tipo_situacion"):
      texto += f" [{ev['tipo_situacion']}]"
  texto += f": {ev['descripcion']}"
  ```
- Si hay medida, agregar un `Paragraph` indentado:
  ```
  Medida: {ev["medida"]}
  ```

### T3 — Extender `ReporteConvivenciaFilaDTO`

Agregar campo:
```python
desglose_por_tipo: dict[str, int] | None = None
```

### T4 — Enriquecer `reporte_periodo_grupo`

En `reporte_periodo_grupo`:
- Cargar tipos_situacion como dict `{id: nombre}`.
- Al iterar registros negativos por estudiante, agrupar por
  `tipo_situacion_id` y resolver nombres.
- Poblar `desglose_por_tipo` en cada fila.

### T5 — Actualizar exportacion del reporte de grupo

En `_fila_a_dict_exportacion`:
- Si `fila.desglose_por_tipo` no es None, agregar una clave por cada tipo
  con el conteo.
- Actualizar `_COLUMNAS_REPORTE_PERIODO` dinamicamente o construir las
  columnas en el metodo de exportacion basandose en los tipos activos.

En `_reporte_periodo_a_html`:
- Agregar columnas de desglose al HTML de la tabla.

### T6 — Tests

- Test de servicio: `_registros_informables_periodo` incluye
  `tipo_situacion` y `medida` cuando existen.
- Test de servicio: `reporte_periodo_grupo` incluye `desglose_por_tipo`.
- Test de PDF: el HTML del reporte incluye columnas de desglose.
- Test de paquete_boletin: los registros tienen los campos nuevos.

## Verificacion

```
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/ -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe init.py
```

Escenarios manuales:
- Registrar evento con tipo II + medida "Citacion a acudiente" →
  generar boletin PDF → el evento muestra "[Tipo II]" y "Medida: Citacion".
- Generar reporte de grupo Excel → columnas "Tipo I", "Tipo II", "Tipo III"
  con conteos por estudiante.
- Evento sin clasificacion → boletin no muestra corchetes vacios.

`init.py` verde.

## Dependencias

- Depende de convivencia_34 (tipos_situacion) — sin ella no hay datos
  de clasificacion que integrar.
- Depende de convivencia_36 (medidas_pedagogicas) — sin ella no hay
  datos de medidas. Puede implementarse parcialmente (solo tipos_situacion)
  si medidas aun no esta lista.
- Depende de convivencia_35 solo indirectamente (las entradas de
  seguimiento NO se muestran en el boletin ni en el reporte de grupo;
  solo en el observador del estudiante).
