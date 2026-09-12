import pytest
from app.models.categorias import CategoriaGasto
from app.services.intent_router import (
    Intencion,
    detectar_categoria_directa,
    detectar_intenciones,
)


def test_gasto_simple_es_registrar_gasto():
    assert detectar_intenciones("gasté 500 en comida") == [Intencion.REGISTRAR_GASTO]


def test_monto_sin_palabra_de_gasto_tambien_se_registra():
    # "uber 250" no dice "gasté", pero tiene un numero y no es pregunta.
    assert detectar_intenciones("uber 250") == [Intencion.REGISTRAR_GASTO]


def test_pregunta_sin_numero_es_solo_pregunta():
    assert detectar_intenciones("¿cuánto gasté en comida?") == [Intencion.PREGUNTA]


def test_pregunta_con_dia_no_registra_gasto():
    # El "15" es un dia, no un monto: sin palabra de gasto no debe registrarse nada.
    assert detectar_intenciones("cuanto llevo el 15?") == [Intencion.PREGUNTA]


@pytest.mark.parametrize("texto", [
    "cuanto gaste el 15?",
    "¿cuánto gasté el día 3?",
    "cuanto pague el 20 de este mes",
])
def test_pregunta_por_dia_con_palabra_de_gasto_no_registra_gasto(texto):
    assert detectar_intenciones(texto) == [Intencion.PREGUNTA]


def test_gasto_con_monto_y_dia_se_sigue_registrando():
    intenciones = detectar_intenciones("gasté 500 el 15, cuanto llevo?")

    assert intenciones == [Intencion.PREGUNTA, Intencion.REGISTRAR_GASTO]


def test_saludo_gasto_y_pregunta_en_el_mismo_mensaje():
    intenciones = detectar_intenciones("Hola, gasté 200 en comida. ¿Cuánto llevo?")

    assert intenciones == [Intencion.SALUDO, Intencion.PREGUNTA, Intencion.REGISTRAR_GASTO]


def test_recurrencia_con_numero_es_gasto_fijo():
    intenciones = detectar_intenciones("Netflix 500 el 12 de cada mes")

    assert intenciones == [Intencion.REGISTRAR_GASTO_FIJO]


def test_recurrencia_sin_numero_no_es_gasto_fijo():
    assert Intencion.REGISTRAR_GASTO_FIJO not in detectar_intenciones("tengo una suscripcion")


@pytest.mark.parametrize("texto", [
    "¿Cuándo pago el préstamo?",
    "cuales son mis pagos fijos",
    "que debo pagar este mes",
])
def test_preguntas_de_gasto_fijo(texto):
    assert detectar_intenciones(texto) == [Intencion.PREGUNTA_GASTO_FIJO]


def test_pregunta_de_gasto_fijo_gana_sobre_recurrencia():
    # Tiene "cada mes" y un numero, pero es una pregunta: no debe registrar nada.
    intenciones = detectar_intenciones("cuando pago lo de cada mes del dia 5")

    assert intenciones == [Intencion.PREGUNTA_GASTO_FIJO]


def test_mensaje_sin_nada_reconocible_devuelve_lista_vacia():
    assert detectar_intenciones("netflix") == []


def test_detecta_categoria_ignorando_mayusculas_y_espacios():
    assert detectar_categoria_directa("  Comida ") == CategoriaGasto.COMIDA


def test_categoria_directa_exige_el_mensaje_completo():
    assert detectar_categoria_directa("gasté en comida") is None
