"""
Tests unitarios — Evaluacion
=============================
Tests separados por petición explícita. Cubren Categoria, Actividad,
Nota, PuntosExtra y especialmente CalculadorNotas con múltiples
escenarios de cálculo.

Ejecutar:
    pytest tests/unit/domain/test_evaluacion.py -v
"""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from src.domain.models.evaluacion import (
    ActualizarActividadDTO,
    ActualizarCategoriaDTO,
    Actividad,
    CalculadorNotas,
    Categoria,
    EstadoActividad,
    FiltroNotasDTO,
    Nota,
    NuevaActividadDTO,
    NuevaCategoriaDTO,
    PuntosExtra,
    RegistrarNotaDTO,
    TipoPuntosExtra,
)


# =============================================================================
# Fixtures reutilizables
# =============================================================================

def _categoria(id: int, nombre: str, peso: float, asig: int = 1, per: int = 1) -> Categoria:
    return Categoria(id=id, nombre=nombre, peso=peso,
                     asignacion_id=asig, periodo_id=per)


def _actividad(id: int, cat_id: int, nombre: str,
               fecha: date | None = None,
               estado: EstadoActividad = EstadoActividad.PUBLICADA) -> Actividad:
    return Actividad(id=id, nombre=nombre, categoria_id=cat_id,
                     fecha=fecha, estado=estado)


def _nota(est_id: int, act_id: int, valor: float) -> Nota:
    return Nota(estudiante_id=est_id, actividad_id=act_id, valor=valor)


@pytest.fixture
def categorias_3() -> list[Categoria]:
    """Evaluaciones 40%, Trabajos 35%, Participación 25%."""
    return [
        _categoria(1, "Evaluaciones", 0.40),
        _categoria(2, "Trabajos",     0.35),
        _categoria(3, "Participación", 0.25),
    ]


@pytest.fixture
def actividades_6(categorias_3) -> list[Actividad]:
    """2 actividades por categoría."""
    hoy = date.today()
    return [
        # Evaluaciones
        _actividad(1, 1, "Examen 1", hoy - timedelta(days=30)),
        _actividad(2, 1, "Examen 2", hoy - timedelta(days=10)),
        # Trabajos
        _actividad(3, 2, "Taller 1", hoy - timedelta(days=25)),
        _actividad(4, 2, "Taller 2", hoy - timedelta(days=5)),
        # Participación
        _actividad(5, 3, "Quiz 1", hoy - timedelta(days=20)),
        _actividad(6, 3, "Quiz 2", hoy - timedelta(days=1)),
    ]


@pytest.fixture
def notas_completas(actividades_6) -> list[Nota]:
    """Estudiante 1: notas en todas las actividades."""
    return [
        _nota(1, 1, 80.0),  # Examen 1
        _nota(1, 2, 90.0),  # Examen 2  → prom cat1 = 85.0
        _nota(1, 3, 70.0),  # Taller 1
        _nota(1, 4, 80.0),  # Taller 2  → prom cat2 = 75.0
        _nota(1, 5, 95.0),  # Quiz 1
        _nota(1, 6, 85.0),  # Quiz 2    → prom cat3 = 90.0
    ]
    # Definitiva = 85*0.40 + 75*0.35 + 90*0.25 = 34 + 26.25 + 22.5 = 82.75


# =============================================================================
# CATEGORIA
# =============================================================================

class TestCategoria:

    def test_categoria_valida(self):
        cat = Categoria(nombre="Evaluaciones", peso=0.40,
                        asignacion_id=1, periodo_id=1)
        assert cat.peso_porcentaje == 40.0

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            Categoria(nombre="   ", peso=0.40, asignacion_id=1, periodo_id=1)

    def test_peso_cero_falla(self):
        with pytest.raises(ValidationError, match="0 .exclusivo."):
            Categoria(nombre="Cat", peso=0.0, asignacion_id=1, periodo_id=1)

    def test_peso_mayor_1_falla(self):
        with pytest.raises(ValidationError, match="1.0"):
            Categoria(nombre="Cat", peso=1.01, asignacion_id=1, periodo_id=1)

    def test_peso_limite_valido(self):
        cat = Categoria(nombre="Solo", peso=1.0, asignacion_id=1, periodo_id=1)
        assert cat.peso == 1.0

    def test_id_negativo_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Categoria(nombre="Cat", peso=0.5, asignacion_id=-1, periodo_id=1)

    def test_peso_redondeado(self):
        cat = Categoria(nombre="Cat", peso=0.33333, asignacion_id=1, periodo_id=1)
        assert cat.peso == 0.3333

    def test_dto_to_categoria(self):
        dto = NuevaCategoriaDTO(nombre="Evaluaciones", peso=0.40,
                                asignacion_id=1, periodo_id=1)
        cat = dto.to_categoria()
        assert isinstance(cat, Categoria)

    def test_actualizar_dto(self):
        cat = Categoria(nombre="Evaluaciones", peso=0.40,
                        asignacion_id=1, periodo_id=1)
        dto = ActualizarCategoriaDTO(nombre="Exámenes", peso=0.45)
        actualizada = dto.aplicar_a(cat)
        assert actualizada.nombre == "Exámenes"
        assert actualizada.peso == 0.45

    def test_actualizar_peso_invalido_falla(self):
        with pytest.raises(ValidationError):
            ActualizarCategoriaDTO(peso=0.0)


# =============================================================================
# ACTIVIDAD
# =============================================================================

class TestActividad:

    @pytest.fixture
    def actividad_borrador(self) -> Actividad:
        return Actividad(nombre="Taller 1", categoria_id=1,
                         valor_maximo=100.0)

    def test_actividad_valida(self, actividad_borrador):
        assert actividad_borrador.estado == EstadoActividad.BORRADOR
        assert actividad_borrador.esta_publicada is False
        assert actividad_borrador.acepta_notas is False

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            Actividad(nombre="   ", categoria_id=1)

    def test_valor_maximo_negativo_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Actividad(nombre="Test", categoria_id=1, valor_maximo=-5.0)

    def test_valor_maximo_cero_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Actividad(nombre="Test", categoria_id=1, valor_maximo=0.0)

    def test_publicar(self, actividad_borrador):
        publicada = actividad_borrador.publicar()
        assert publicada.estado == EstadoActividad.PUBLICADA
        assert publicada.esta_publicada is True
        assert publicada.acepta_notas is True
        assert actividad_borrador.estado == EstadoActividad.BORRADOR  # intacto

    def test_publicar_ya_publicada_falla(self, actividad_borrador):
        publicada = actividad_borrador.publicar()
        with pytest.raises(ValueError, match="borrador"):
            publicada.publicar()

    def test_cerrar(self, actividad_borrador):
        cerrada = actividad_borrador.publicar().cerrar()
        assert cerrada.estado == EstadoActividad.CERRADA
        assert cerrada.acepta_notas is False

    def test_cerrar_borrador_falla(self, actividad_borrador):
        with pytest.raises(ValueError, match="publicada"):
            actividad_borrador.cerrar()

    def test_actualizar_cerrada_falla(self, actividad_borrador):
        cerrada = actividad_borrador.publicar().cerrar()
        dto = ActualizarActividadDTO(nombre="Nuevo nombre")
        with pytest.raises(ValueError, match="cerrada"):
            dto.aplicar_a(cerrada)

    def test_dto_to_actividad(self):
        dto = NuevaActividadDTO(nombre="Examen 1", categoria_id=2)
        act = dto.to_actividad()
        assert isinstance(act, Actividad)
        assert act.estado == EstadoActividad.BORRADOR


# =============================================================================
# NOTA
# =============================================================================

class TestNota:

    def test_nota_valida(self):
        nota = Nota(estudiante_id=1, actividad_id=1, valor=75.5)
        assert nota.valor == 75.5

    def test_nota_redondeada(self):
        nota = Nota(estudiante_id=1, actividad_id=1, valor=75.555)
        assert nota.valor == 75.56

    def test_valor_negativo_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            Nota(estudiante_id=1, actividad_id=1, valor=-1.0)

    def test_valor_mayor_100_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            Nota(estudiante_id=1, actividad_id=1, valor=100.01)

    def test_valor_cero_valido(self):
        nota = Nota(estudiante_id=1, actividad_id=1, valor=0.0)
        assert nota.valor == 0.0

    def test_valor_100_valido(self):
        nota = Nota(estudiante_id=1, actividad_id=1, valor=100.0)
        assert nota.valor == 100.0

    def test_id_negativo_falla(self):
        with pytest.raises(ValidationError, match="positivo"):
            Nota(estudiante_id=-1, actividad_id=1, valor=75.0)

    def test_dto_to_nota(self):
        dto = RegistrarNotaDTO(estudiante_id=1, actividad_id=2, valor=88.0)
        nota = dto.to_nota()
        assert isinstance(nota, Nota)
        assert nota.valor == 88.0

    def test_dto_nota_invalida_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            RegistrarNotaDTO(estudiante_id=1, actividad_id=1, valor=105.0)


# =============================================================================
# PUNTOS EXTRA
# =============================================================================

class TestPuntosExtra:

    def test_puntos_validos(self):
        pe = PuntosExtra(estudiante_id=1, asignacion_id=1, periodo_id=1,
                         positivos=5, negativos=2)
        assert pe.balance == 3
        assert pe.tiene_impacto is True

    def test_balance_cero(self):
        pe = PuntosExtra(estudiante_id=1, asignacion_id=1, periodo_id=1)
        assert pe.balance == 0
        assert pe.tiene_impacto is False

    def test_negativos_no_pueden_ser_negativos(self):
        with pytest.raises(ValidationError):
            PuntosExtra(estudiante_id=1, asignacion_id=1, periodo_id=1,
                        negativos=-1)

    def test_tipos(self):
        for tipo in TipoPuntosExtra:
            pe = PuntosExtra(estudiante_id=1, asignacion_id=1, periodo_id=1,
                             tipo=tipo, positivos=1)
            assert pe.tipo == tipo


# =============================================================================
# CALCULADOR NOTAS — calcular_definitiva
# =============================================================================

class TestCalculadorDefinitiva:

    def test_calculo_basico(self, categorias_3, actividades_6, notas_completas):
        """85*0.40 + 75*0.35 + 90*0.25 = 82.75"""
        result = CalculadorNotas.calcular_definitiva(
            notas_completas, actividades_6, categorias_3
        )
        assert result == 82.75

    def test_sin_notas_retorna_cero(self, categorias_3, actividades_6):
        result = CalculadorNotas.calcular_definitiva([], actividades_6, categorias_3)
        assert result == 0.0

    def test_sin_categorias_retorna_cero(self, actividades_6, notas_completas):
        result = CalculadorNotas.calcular_definitiva(notas_completas, actividades_6, [])
        assert result == 0.0

    def test_actividad_sin_nota_cuenta_como_cero(self, categorias_3, actividades_6):
        """Solo el primer examen calificado → prom cat1 = (80+0)/2 = 40"""
        notas_parciales = [
            _nota(1, 1, 80.0),   # Examen 1 → cat1
            _nota(1, 3, 70.0),   # Taller 1 → cat2
            _nota(1, 4, 80.0),   # Taller 2 → cat2
            _nota(1, 5, 95.0),   # Quiz 1   → cat3
            _nota(1, 6, 85.0),   # Quiz 2   → cat3
        ]
        result = CalculadorNotas.calcular_definitiva(
            notas_parciales, actividades_6, categorias_3
        )
        # cat1: (80+0)/2=40 * 0.40 = 16
        # cat2: (70+80)/2=75 * 0.35 = 26.25
        # cat3: (95+85)/2=90 * 0.25 = 22.5
        assert result == 64.75

    def test_categoria_sin_actividades_excluida(self):
        """Una categoría sin actividades no aporta ni quita puntos."""
        cats = [_categoria(1, "A", 0.60), _categoria(2, "B", 0.40)]
        acts = [_actividad(1, 1, "Act A")]  # Solo cat 1 tiene actividades
        notas = [_nota(1, 1, 80.0)]
        result = CalculadorNotas.calcular_definitiva(notas, acts, cats)
        # cat1: 80 * 0.60 = 48.0; cat2: sin actividades → 0
        assert result == 48.0

    def test_nota_perfecta(self, categorias_3, actividades_6):
        notas_100 = [_nota(1, i, 100.0) for i in range(1, 7)]
        result = CalculadorNotas.calcular_definitiva(
            notas_100, actividades_6, categorias_3
        )
        assert result == 100.0

    def test_nota_cero(self, categorias_3, actividades_6):
        notas_0 = [_nota(1, i, 0.0) for i in range(1, 7)]
        result = CalculadorNotas.calcular_definitiva(
            notas_0, actividades_6, categorias_3
        )
        assert result == 0.0

    def test_dos_estudiantes_independientes(self, categorias_3, actividades_6):
        """Las notas de cada estudiante son independientes."""
        notas_est1 = [_nota(1, i, 80.0) for i in range(1, 7)]
        notas_est2 = [_nota(2, i, 60.0) for i in range(1, 7)]

        r1 = CalculadorNotas.calcular_definitiva(notas_est1, actividades_6, categorias_3)
        r2 = CalculadorNotas.calcular_definitiva(notas_est2, actividades_6, categorias_3)
        assert r1 == 80.0
        assert r2 == 60.0

    def test_una_sola_categoria(self):
        cats = [_categoria(1, "Única", 1.0)]
        acts = [_actividad(1, 1, "A1"), _actividad(2, 1, "A2")]
        notas = [_nota(1, 1, 70.0), _nota(1, 2, 90.0)]
        result = CalculadorNotas.calcular_definitiva(notas, acts, cats)
        assert result == 80.0  # (70+90)/2 * 1.0


# =============================================================================
# CALCULADOR NOTAS — calcular_promedio_ajustado
# =============================================================================

class TestCalculadorPromedioAjustado:

    def test_promedio_ajustado_todas_evaluadas(
        self, categorias_3, actividades_6, notas_completas
    ):
        """Sin corte de fecha → igual que calcular_definitiva."""
        result = CalculadorNotas.calcular_promedio_ajustado(
            notas_completas, actividades_6, categorias_3
        )
        assert result == 82.75

    def test_promedio_ajustado_con_corte_de_fecha(self, categorias_3, actividades_6):
        """
        Corte: hace 15 días. d-N significa "N días atrás".
        Dentro del corte (fecha <= d-15, es decir fecha más antigua):
          Examen 1 (d-30), Taller 1 (d-25), Quiz 1 (d-20) → sí
        Fuera del corte (fecha > d-15, es decir más recientes):
          Examen 2 (d-10), Taller 2 (d-5), Quiz 2 (d-1) → no
        promedio = 80*0.40 + 70*0.35 + 95*0.25 = 80.25
        """
        hoy = date.today()
        corte = hoy - timedelta(days=15)
        notas = [
            _nota(1, 1, 80.0),  # Examen 1 d-30 → dentro (d-30 ≤ d-15)
            _nota(1, 2, 90.0),  # Examen 2 d-10 → fuera  (d-10 > d-15)
            _nota(1, 3, 70.0),  # Taller 1 d-25 → dentro
            _nota(1, 4, 80.0),  # Taller 2 d-5  → fuera
            _nota(1, 5, 95.0),  # Quiz 1 d-20   → dentro
            _nota(1, 6, 85.0),  # Quiz 2 d-1    → fuera
        ]
        result = CalculadorNotas.calcular_promedio_ajustado(
            notas, actividades_6, categorias_3, hasta_fecha=corte
        )
        # Solo cuentan actividades con fecha <= d-15 que tienen nota
        assert result == 80.25

    def test_promedio_ajustado_sin_notas(self, categorias_3, actividades_6):
        result = CalculadorNotas.calcular_promedio_ajustado(
            [], actividades_6, categorias_3
        )
        assert result == 0.0

    def test_promedio_ajustado_renormaliza_pesos(self):
        """
        Si solo hay notas en una categoría de peso 0.40,
        el promedio ajustado usa ese peso renormalizado a 1.0.
        Resultado: promedio_cat × 1.0 = el promedio de esa categoría.
        """
        hoy = date.today()
        cats = [
            _categoria(1, "A", 0.40),
            _categoria(2, "B", 0.60),
        ]
        acts = [
            _actividad(1, 1, "A1", hoy - timedelta(days=5)),
            _actividad(2, 2, "B1", hoy - timedelta(days=5)),
        ]
        # Solo nota en cat A
        notas = [_nota(1, 1, 80.0)]

        result = CalculadorNotas.calcular_promedio_ajustado(
            notas, acts, cats
        )
        # cat A tiene nota, cat B no
        # peso_total = 0.40, peso_ajustado_A = 0.40/0.40 = 1.0
        # promedio = 80 * 1.0 = 80.0
        assert result == 80.0

    def test_promedio_ajustado_sin_categorias_retorna_cero(self, actividades_6):
        result = CalculadorNotas.calcular_promedio_ajustado(
            [_nota(1, 1, 80.0)], actividades_6, []
        )
        assert result == 0.0


# =============================================================================
# CALCULADOR NOTAS — pesos_validos y peso_total
# =============================================================================

class TestCalculadorPesos:

    def test_pesos_validos_suma_1(self, categorias_3):
        assert CalculadorNotas.pesos_validos(categorias_3) is True

    def test_pesos_validos_suma_menor_1(self):
        cats = [_categoria(1, "A", 0.30), _categoria(2, "B", 0.30)]
        assert CalculadorNotas.pesos_validos(cats) is True

    def test_pesos_invalidos_suma_mayor_1(self):
        cats = [_categoria(1, "A", 0.60), _categoria(2, "B", 0.60)]
        assert CalculadorNotas.pesos_validos(cats) is False

    def test_pesos_validos_lista_vacia(self):
        assert CalculadorNotas.pesos_validos([]) is True

    def test_peso_total(self, categorias_3):
        # 0.40 + 0.35 + 0.25 = 1.0
        assert CalculadorNotas.peso_total(categorias_3) == 1.0

    def test_peso_total_lista_vacia(self):
        assert CalculadorNotas.peso_total([]) == 0.0

    def test_margen_flotante(self):
        """La suma 0.40+0.35+0.25 en flotantes puede ser 1.0000000001."""
        cats = [
            _categoria(1, "A", 0.3333),
            _categoria(2, "B", 0.3333),
            _categoria(3, "C", 0.3334),
        ]
        # 0.3333+0.3333+0.3334 = 1.0000 exacto
        assert CalculadorNotas.pesos_validos(cats) is True