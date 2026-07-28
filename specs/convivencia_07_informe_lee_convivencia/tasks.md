# convivencia_07_informe_lee_convivencia — Tasks

## Objetivo
`InformeService.generar_boletin_periodo()` incluye datos de convivencia
(nota cuantitativa + observaciones públicas del periodo) en el dict que
se pasa a `boletin_pdf`. El PDF ya muestra la caja "OBSERVACIONES Y
RECOMENDACIONES" pero la deja vacía — este paso la alimenta con datos reales.

## Scope
```
src/services/informe_service.py
container.py
tests/unit/services/test_informe_service.py
```
**Nada más.** El llenado visual del PDF es `convivencia_08`.

## Diseño

### Inyección
`InformeService.__init__` recibe un parámetro opcional:
```python
convivencia_repo: "IConvivenciaRepository | None" = None
```
(igual que `estudiante_repo` ya existente). Se usa el string-annotation
para evitar importación directa del puerto en tiempo de carga.

### Método nuevo
```python
def convivencia_boletin(
    self,
    estudiante_id: int,
    periodo_id: int,
) -> dict:
    """
    Retorna dict con claves:
      nota: float | None
      nota_observacion: str | None  (campo NotaComportamiento.observacion)
      observaciones: list[str]      (ObservacionPeriodo.texto donde es_publica=True)
    Si no hay convivencia_repo inyectado → retorna dict con None / [].
    """
```

### Integración en generar_boletin_periodo
En la rama PDF de `generar_boletin_periodo`, ANTES de llamar a
`_boletin_mod.generar_boletin_acumulado_pdf(datos)`, añadir:
```python
datos["convivencia"] = self.convivencia_boletin(estudiante_id, periodo_id)
```

En la rama Excel (tabla plana), añadir columnas "Nota Convivencia" y
"Observaciones" solo si hay datos.

### container.py
```python
# en informe_service():
lambda: InformeService(
    estadisticos_repo=cls.estadisticos_repo(),
    exporter=cls.exporter_service(),
    estudiante_repo=cls.estudiante_repo(),
    convivencia_repo=cls.convivencia_repo(),   # <-- añadir
),
```

## Tareas

### T1 — `InformeService`: inyectar convivencia_repo + método convivencia_boletin
**Archivo**: `src/services/informe_service.py`

1. En `__init__`, añadir parámetro `convivencia_repo=None` (tipo anotado
   como string para evitar import circular).
2. Guardar como `self._convivencia_repo = convivencia_repo`.
3. Implementar método `convivencia_boletin(estudiante_id, periodo_id) -> dict`:
   - Si `self._convivencia_repo is None` → retornar
     `{"nota": None, "nota_observacion": None, "observaciones": []}`.
   - Llamar `self._convivencia_repo.get_nota(estudiante_id, periodo_id)` → `NotaComportamiento | None`.
   - Llamar `self._convivencia_repo.listar_observaciones_por_estudiante(
       estudiante_id, periodo_id, solo_publicas=True)` → `list[ObservacionPeriodo]`.
   - Retornar dict con los valores extraídos.

**Verificación**:
```
.venv/Scripts/python.exe scripts/check_imports.py --layer services
```
Debe pasar sin nuevas violaciones.

### T2 — Integrar en `generar_boletin_periodo` y `generar_boletin_acumulado_pdf`
**Archivo**: `src/services/informe_service.py`

En la rama PDF de `generar_boletin_periodo`:
```python
datos = self._estadisticos_repo.boletin_datos_acumulado(...)
datos["convivencia"] = self.convivencia_boletin(estudiante_id, periodo_id)
return _boletin_mod.generar_boletin_acumulado_pdf(datos)
```

En la rama Excel: añadir columnas "Nota Conv." (valor numérico) y
"Observaciones" (observaciones unidas por " | ") a las filas.

**Verificación**:
```
.venv/Scripts/python.exe scripts/check_imports.py --layer services
```

### T3 — Cablear en `container.py`
**Archivo**: `container.py`

Añadir `convivencia_repo=cls.convivencia_repo()` al constructor de
`InformeService` en `informe_service()`.

**Verificación**:
```
.venv/Scripts/python.exe -c "from container import Container; s = Container.informe_service(); print('OK')"
```

### T4 — Tests
**Archivo**: `tests/unit/services/test_informe_service.py`

Añadir clase `FakeConvivenciaRepo` mínima con:
- `get_nota(est_id, per_id)` → puede retornar `NotaComportamiento | None`
- `listar_observaciones_por_estudiante(est_id, per_id, solo_publicas)` → `list[ObservacionPeriodo]`

Casos de test:
- **T4a** `test_convivencia_boletin_sin_repo`: sin convivencia_repo inyectado → dict con None y [].
- **T4b** `test_convivencia_boletin_con_nota`: repo retorna nota + obs pública → dict correcto.
- **T4c** `test_convivencia_boletin_sin_nota`: repo retorna None para nota + obs vacía → dict correcto.
- **T4d** `test_convivencia_boletin_solo_obs`: nota None pero hay observaciones públicas → lista con textos.

**Verificación**:
```
.venv/Scripts/python.exe -m pytest tests/unit/services/test_informe_service.py -v
```

## criterio_done
- [ ] `convivencia_boletin()` existe en `InformeService` y retorna dict con las 3 claves.
- [ ] `datos["convivencia"]` se inyecta antes de llamar a `generar_boletin_acumulado_pdf`.
- [ ] `container.py` pasa `convivencia_repo=cls.convivencia_repo()`.
- [ ] 4 tests T4a..T4d verdes.
- [ ] `python scripts/check_imports.py --layer services` verde.
- [ ] `.venv/Scripts/python.exe init.py --quick` verde (ENTORNO OK).
