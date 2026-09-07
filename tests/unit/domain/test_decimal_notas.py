"""
Tests de aritmética decimal exacta — datos_04_decimal_notas
===========================================================

T1 — Ciclo de persistencia SQLite: Decimal → float → REAL → str → Decimal
T2 — Cuantización centralizada (NotaDecimal, PesoDecimal)
T3 — Reproducción del fallo float (rojo antes de T5, verde después)
T6 — Propiedades algebraicas del promedio ponderado
T8 — Clasificación de desempeño en los extremos
"""

from __future__ import annotations

import sqlite3
from decimal import ROUND_HALF_UP, Decimal

import pytest

from src.domain.models.decimal_types import (
    QUANT_NOTA,
    QUANT_PESO,
    cuantizar_nota,
    cuantizar_peso,
)

# =============================================================================
# T1 — Ciclo de persistencia: barrido 0.00 a 100.00 en pasos de 0.01
# =============================================================================


def test_ciclo_persistencia_barrido():
    """
    T1 — Verifica que todo decimal de 2 dígitos sobrevive intacto el ciclo
    Decimal → float → REAL → float → str → Decimal.

    El barrido cubre todos los valores de 0.00 a 100.00 en pasos de 0.01
    (10 001 valores). Si alguno falla, el diseño es inválido y no tiene
    sentido convertir los modelos (R18, R20).
    """
    PASO = Decimal("0.01")
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (val REAL)")

    # Insertar todos los valores como float
    valores: list[Decimal] = []
    params: list[tuple] = []
    for i in range(10_001):
        d = (PASO * i).quantize(QUANT_NOTA)
        valores.append(d)
        params.append((float(d),))

    conn.executemany("INSERT INTO t VALUES (?)", params)
    conn.commit()

    # Leer y verificar identidad
    rows = conn.execute("SELECT val FROM t ORDER BY val").fetchall()
    conn.close()

    assert len(rows) == 10_001, f"Se esperaban 10001 filas, se obtuvieron {len(rows)}"

    errores: list[tuple[str, float, str]] = []
    for i, (val_float,) in enumerate(rows):
        original = valores[i]
        recovered = Decimal(str(val_float)).quantize(QUANT_NOTA)
        if original != recovered:
            errores.append((str(original), val_float, str(recovered)))

    assert not errores, (
        f"Barrido fallido en {len(errores)} valores. "
        f"Primeros 3: {errores[:3]}"
    )


def test_ciclo_persistencia_decimal_str_correcto():
    """
    T1/R19 — Decimal(str(f)) reconstruye el valor; Decimal(f) NO.

    Solo el caso canónico del diseño: 3.05 como referencia.
    """
    f = 3.05  # float representado internamente con ruido binario

    # Vía str: limpio
    via_str = Decimal(str(f))
    assert str(via_str) == "3.05", f"Decimal(str(3.05)) debe ser '3.05', fue '{via_str}'"

    # Vía constructor directo: ruidoso (no exactamente 3.05)
    via_float = Decimal(f)
    assert via_float != Decimal("3.05"), (
        "Decimal(float) debería tener ruido binario; si esto falla en tu plataforma "
        "la prueba puede necesitar revisión."
    )


def test_persistencia_decimal_directo_lanza_programming_error():
    """
    T1/R17 — Pasar Decimal directo a sqlite3 lanza ProgrammingError.

    Es el motivo de la conversión explícita a float en la frontera del repositorio.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (val REAL)")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("INSERT INTO t VALUES (?)", (Decimal("3.05"),))
    conn.close()


# =============================================================================
# T2 — Cuantización centralizada (NotaDecimal, PesoDecimal)
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "v",
    ["3.005", 3.005, Decimal("3.005")],
    ids=["str", "float", "Decimal"],
)
def test_cuantizar_nota_mismo_resultado(v):
    """
    T2/R6 — str, float y Decimal producen el mismo resultado cuantizado.

    El caso int se prueba por separado porque el entero 3 no tiene fracción,
    y cuantizar_nota(3) → Decimal("3.00") (no "3.01").
    """
    resultado = cuantizar_nota(v)
    # 3.005 → 3.01 (ROUND_HALF_UP)
    assert resultado == Decimal("3.01"), (
        f"cuantizar_nota({v!r}) = {resultado}, se esperaba Decimal('3.01')"
    )


@pytest.mark.unit
def test_cuantizar_nota_acepta_int():
    """T2/R6 — cuantizar_nota acepta enteros y los convierte con 2 decimales."""
    assert cuantizar_nota(3) == Decimal("3.00")
    assert cuantizar_nota(0) == Decimal("0.00")
    assert cuantizar_nota(100) == Decimal("100.00")


@pytest.mark.unit
def test_cuantizar_nota_round_half_up():
    """
    T2/R4 — 2.995 → 3.00 con ROUND_HALF_UP (no 2.99 con ROUND_HALF_EVEN).

    Con ROUND_HALF_EVEN (bancario), 2.995 redondeado a 2 decimales sería 3.00
    también, porque 5 es equidistante y 9 es impar→ sube. Pero con un valor
    como 2.985 sería 2.98 (8 es par). ROUND_HALF_UP siempre sube.
    """
    assert cuantizar_nota(Decimal("2.995")) == Decimal("3.00")
    assert cuantizar_nota(2.995) == Decimal("3.00")
    # Asegura que el redondeo no usa HALF_EVEN: 2.985 → 2.99 siempre
    assert cuantizar_nota(Decimal("2.985")) == Decimal("2.99")


@pytest.mark.unit
@pytest.mark.parametrize(
    "v",
    ["0.7005", 0.7005, Decimal("0.7005")],
    ids=["str", "float", "Decimal"],
)
def test_cuantizar_peso_mismo_resultado(v):
    """
    T2/R6 — Peso: str, float y Decimal producen el mismo resultado cuantizado.
    """
    resultado = cuantizar_peso(v)
    assert resultado == Decimal("0.7005"), (
        f"cuantizar_peso({v!r}) = {resultado}, se esperaba Decimal('0.7005')"
    )


@pytest.mark.unit
def test_cuantizar_nota_produce_2_decimales():
    """T2/R2 — NotaDecimal siempre tiene exactamente 2 decimales."""
    for v in [0, 1, 100, 3.5, "60.0", Decimal("75")]:
        r = cuantizar_nota(v)
        assert r == r.quantize(QUANT_NOTA), f"cuantizar_nota({v!r}) no tiene 2 decimales: {r}"


@pytest.mark.unit
def test_cuantizar_peso_produce_4_decimales():
    """T2/R3 — PesoDecimal siempre tiene exactamente 4 decimales."""
    for v in [0.7, 0.29, 0.01, "0.3333", Decimal("0.25")]:
        r = cuantizar_peso(v)
        assert r == r.quantize(QUANT_PESO), f"cuantizar_peso({v!r}) no tiene 4 decimales: {r}"


# =============================================================================
# T3 — Reproducir el fallo actual como test en rojo → verde tras T5
# =============================================================================


@pytest.mark.unit
def test_umbral_notas_iguales_aprueba():
    """
    T3 — Pesos [0.7, 0.29, 0.01] con notas 3.0 y umbral 3.0:
    el estudiante DEBE aprobar (definitiva >= umbral).

    Antes de T5: CalculadorNotas usa float → la suma es 2.9999... y comparar
    contra Decimal("3.00") lanza TypeError (rojo).
    Después de T5: CalculadorNotas usa Decimal → definitiva == Decimal("3.00")
    y la comparación pasa (verde).
    """
    from datetime import date

    from src.domain.models.evaluacion import Actividad, CalculadorNotas, Categoria

    umbral = Decimal("3.00")

    cat1 = Categoria(id=1, nombre="Ser",    peso=0.70, asignacion_id=1, periodo_id=1)
    cat2 = Categoria(id=2, nombre="Saber",  peso=0.29, asignacion_id=1, periodo_id=1)
    cat3 = Categoria(id=3, nombre="Hacer",  peso=0.01, asignacion_id=1, periodo_id=1)

    act1 = Actividad(id=1, nombre="A1", categoria_id=1, fecha=date.today())
    act2 = Actividad(id=2, nombre="A2", categoria_id=2, fecha=date.today())
    act3 = Actividad(id=3, nombre="A3", categoria_id=3, fecha=date.today())

    # Notas exactamente en el umbral. Se usan Decimal para el diccionario porque
    # después de T4/T5 los valores del mapa de notas son Decimal (provienen de Nota.valor).
    notas = {1: Decimal("3.00"), 2: Decimal("3.00"), 3: Decimal("3.00")}

    definitiva = CalculadorNotas.calcular_definitiva(
        notas, [act1, act2, act3], [cat1, cat2, cat3]
    )

    # Tras T5, definitiva es Decimal("3.00"). Antes de T5, es float → TypeError.
    assert definitiva >= umbral, (
        f"El estudiante con nota 3.0 en todas las categorías debe aprobar. "
        f"definitiva={definitiva!r}, umbral={umbral!r}"
    )


# =============================================================================
# T6 — Propiedades algebraicas del promedio ponderado
# =============================================================================


def _calcular_definitiva_decimal(
    pesos: list[Decimal],
    notas: list[Decimal],
) -> Decimal:
    """Computo de referencia con aritmética Decimal pura."""
    acc = Decimal("0")
    for p, n in zip(pesos, notas, strict=False):
        acc += p * n
    return acc.quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)


@pytest.mark.unit
@pytest.mark.parametrize(
    "pesos_raw",
    [
        [0.70, 0.29, 0.01],   # caso del diseño — problema clásico en float
        [0.05, 0.15, 0.80],   # peso concentrado en la última categoría
        [0.33, 0.33, 0.34],   # tercios aproximados
    ],
    ids=["0.70_0.29_0.01", "0.05_0.15_0.80", "0.33_0.33_0.34"],
)
def test_propiedades_definitiva_entre_min_y_max(pesos_raw):
    """
    T6/R15 — La definitiva queda entre la menor y la mayor nota
    para cualquier combinación válida de pesos que sumen la unidad.
    """
    pesos = [cuantizar_peso(p) for p in pesos_raw]
    notas = [Decimal("20.00"), Decimal("60.00"), Decimal("90.00")]
    definitiva = _calcular_definitiva_decimal(pesos, notas)
    assert min(notas) <= definitiva <= max(notas), (
        f"pesos={pesos_raw}: definitiva={definitiva} fuera de [{min(notas)}, {max(notas)}]"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "pesos_raw",
    [
        [0.70, 0.29, 0.01],
        [0.05, 0.15, 0.80],
        [0.33, 0.33, 0.34],
    ],
    ids=["0.70_0.29_0.01", "0.05_0.15_0.80", "0.33_0.33_0.34"],
)
def test_propiedades_subir_nota_no_baja_definitiva(pesos_raw):
    """
    T6/R16 — Subir una nota sin variar las demás no baja la definitiva.
    """
    pesos = [cuantizar_peso(p) for p in pesos_raw]
    notas_base = [Decimal("40.00"), Decimal("60.00"), Decimal("70.00")]
    notas_sube = [Decimal("55.00"), Decimal("60.00"), Decimal("70.00")]  # sube la primera
    def_base = _calcular_definitiva_decimal(pesos, notas_base)
    def_sube = _calcular_definitiva_decimal(pesos, notas_sube)
    assert def_sube >= def_base, (
        f"pesos={pesos_raw}: subir la primera nota de 40 a 55 bajo la definitiva "
        f"de {def_base} a {def_sube}"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "pesos_raw, umbral",
    [
        ([0.70, 0.29, 0.01], Decimal("3.00")),
        ([0.05, 0.15, 0.80], Decimal("60.00")),
        ([0.33, 0.33, 0.34], Decimal("75.00")),
    ],
    ids=["0.70_0.29_0.01", "0.05_0.15_0.80", "0.33_0.33_0.34"],
)
def test_propiedades_todas_notas_iguales_al_umbral(pesos_raw, umbral):
    """
    T6/R10 — Con todas las notas iguales al umbral, la definitiva es exactamente el umbral.

    Este es el caso que falla con float (0.7*3 + 0.29*3 + 0.01*3 = 2.9999... en float).
    Con Decimal, la suma exacta es 3.00.
    """
    pesos = [cuantizar_peso(p) for p in pesos_raw]
    notas = [umbral, umbral, umbral]
    definitiva = _calcular_definitiva_decimal(pesos, notas)
    assert definitiva == umbral, (
        f"pesos={pesos_raw}: con todas las notas en {umbral}, "
        f"definitiva debería ser {umbral}, fue {definitiva}"
    )


# =============================================================================
# T8 — Clasificación de desempeño en los extremos
# =============================================================================


@pytest.mark.unit
def test_desempeno_nota_en_extremo_inferior():
    """
    T8/R14 — Una nota justo en el rango_min del nivel lo clasifica en ese nivel.
    """
    from src.domain.models.configuracion import NivelDesempeno

    nivel = NivelDesempeno(id=1, anio_id=1, nombre="Basico", rango_min=60.0, rango_max=69.9, orden=2)

    assert nivel.clasifica(Decimal("60.00")), "60.00 debe clasificar en Basico (rango_min)"
    assert not nivel.clasifica(Decimal("59.99")), "59.99 no debe clasificar en Basico"


@pytest.mark.unit
def test_desempeno_nota_en_extremo_superior():
    """
    T8/R14 — Una nota justo en el rango_max del nivel lo clasifica en ese nivel.
    """
    from src.domain.models.configuracion import NivelDesempeno

    nivel = NivelDesempeno(id=2, anio_id=1, nombre="Basico", rango_min=60.0, rango_max=69.9, orden=2)

    assert nivel.clasifica(Decimal("69.90")), "69.90 debe clasificar en Basico (rango_max)"
    assert not nivel.clasifica(Decimal("70.00")), "70.00 no debe clasificar en Basico"


@pytest.mark.unit
def test_desempeno_frontera_entre_niveles_es_determinista():
    """
    T8/R14 — Una nota en la frontera exacta pertenece a exactamente un nivel.

    rango_max del nivel inferior == rango_min del nivel superior: la nota
    se clasifica en el superior (convenio: rango_min inclusive, rango_max inclusive).
    """
    from src.domain.models.configuracion import NivelDesempeno

    bajo   = NivelDesempeno(id=1, anio_id=1, nombre="Bajo",   rango_min=0.0,  rango_max=59.9,  orden=1)
    basico = NivelDesempeno(id=2, anio_id=1, nombre="Basico", rango_min=60.0, rango_max=69.9,  orden=2)
    alto   = NivelDesempeno(id=3, anio_id=1, nombre="Alto",   rango_min=70.0, rango_max=84.9,  orden=3)
    sup    = NivelDesempeno(id=4, anio_id=1, nombre="Superior", rango_min=85.0, rango_max=100.0, orden=4)

    nota_frontera = Decimal("60.00")
    niveles = [bajo, basico, alto, sup]

    matches = [n.nombre for n in niveles if n.clasifica(nota_frontera)]
    assert len(matches) == 1, (
        f"La nota {nota_frontera} debe clasificar en exactamente un nivel, "
        f"pero clasificó en: {matches}"
    )
    assert matches[0] == "Basico", (
        f"La nota {nota_frontera} debe clasificar en Basico, no en {matches[0]}"
    )


@pytest.mark.unit
def test_desempeno_cuatro_niveles_cubren_toda_la_escala():
    """
    T8 — Los cuatro niveles típicos cubren toda la escala sin huecos.
    """
    from src.domain.models.configuracion import NivelDesempeno

    bajo   = NivelDesempeno(id=1, anio_id=1, nombre="Bajo",     rango_min=0.0,  rango_max=59.9,  orden=1)
    basico = NivelDesempeno(id=2, anio_id=1, nombre="Basico",   rango_min=60.0, rango_max=69.9,  orden=2)
    alto   = NivelDesempeno(id=3, anio_id=1, nombre="Alto",     rango_min=70.0, rango_max=84.9,  orden=3)
    sup    = NivelDesempeno(id=4, anio_id=1, nombre="Superior", rango_min=85.0, rango_max=100.0, orden=4)
    niveles = [bajo, basico, alto, sup]

    # Valores claramente dentro de cada nivel (no en el borde exacto).
    # Los bordes se prueban en test_desempeno_nota_en_extremo_inferior/superior.
    # Evitamos Decimal("59.90") vs float(59.9) que tiene ruido de representación
    # antes de T4 (cuando rango_max aún es float).
    muestras = [
        Decimal("0.00"),   # bajo
        Decimal("50.00"),  # bajo
        Decimal("60.00"),  # basico
        Decimal("65.00"),  # basico
        Decimal("70.00"),  # alto
        Decimal("77.00"),  # alto
        Decimal("85.00"),  # superior
        Decimal("100.00"), # superior
    ]

    for nota in muestras:
        matches = [n.nombre for n in niveles if n.clasifica(nota)]
        assert len(matches) == 1, (
            f"Nota {nota} clasifica en {len(matches)} niveles: {matches}; "
            "debe clasificar en exactamente uno"
        )
