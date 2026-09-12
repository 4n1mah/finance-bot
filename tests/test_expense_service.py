import pytest
from app.models.categorias import CategoriaGasto
from app.models.gasto import Gasto
from app.models.gasto_fijo import GastoFijo
from app.models.usuarios import Usuario
from app.schemas.gasto_schema import (
    ConsultaGasto,
    ConsultaGastoFijo,
    ExtraccionGasto,
    ExtraccionGastoFijo,
    TipoConsulta,
)
from app.services import expense_service
from app.services.expense_service import procesar_mensaje

NUMERO = "18091234567"


@pytest.fixture
def groq_falso(monkeypatch):
    """
    Reemplaza las llamadas a Groq por respuestas controladas. Ningun test de
    este archivo debe salir a internet; si una funcion no configurada se llama,
    el test falla con un error claro.
    """
    respuestas = {}

    def _falso(nombre):
        def _llamada(texto):
            if nombre not in respuestas:
                raise AssertionError(f"No se esperaba llamar a {nombre}")
            valor = respuestas[nombre]
            if isinstance(valor, Exception):
                raise valor
            return valor
        return _llamada

    for nombre in ["extraer_gastos", "extraer_consulta", "extraer_gasto_fijo", "extraer_consulta_gasto_fijo"]:
        monkeypatch.setattr(expense_service, nombre, _falso(nombre))

    return respuestas


def test_crea_el_usuario_la_primera_vez(db, groq_falso):
    procesar_mensaje(db, NUMERO, "hola", nombre="Ana")
    procesar_mensaje(db, NUMERO, "hola", nombre="Ana")

    usuarios = db.query(Usuario).all()
    assert [(u.nombre, u.numero_whatsapp) for u in usuarios] == [("Ana", NUMERO)]


def test_registra_varios_gastos(db, groq_falso):
    groq_falso["extraer_gastos"] = [
        ExtraccionGasto(monto=250, categoria=CategoriaGasto.COMIDA, descripcion="almuerzo"),
        ExtraccionGasto(monto=1500, categoria=CategoriaGasto.PASAJE, descripcion="uber"),
    ]

    respuesta = procesar_mensaje(db, NUMERO, "gasté 250 en almuerzo y 1500 en uber")

    assert respuesta == (
        "✅ Gasto registrado: *RD$250.00* en comida (almuerzo)\n"
        "✅ Gasto registrado: *RD$1,500.00* en pasaje (uber)"
    )
    assert db.query(Gasto).count() == 2


def test_gasto_sin_monto_avisa_y_no_guarda(db, groq_falso):
    groq_falso["extraer_gastos"] = [
        ExtraccionGasto(monto=None, categoria=CategoriaGasto.OTROS, descripcion="algo"),
    ]

    respuesta = procesar_mensaje(db, NUMERO, "compre 2 cosas")

    assert respuesta == "⚠️ No pude identificar el monto de uno de los gastos"
    assert db.query(Gasto).count() == 0


def test_saludo_mas_gasto_mas_pregunta(db, groq_falso):
    groq_falso["extraer_gastos"] = [
        ExtraccionGasto(monto=200, categoria=CategoriaGasto.COMIDA, descripcion="comida"),
    ]
    groq_falso["extraer_consulta"] = ConsultaGasto(
        tipo=TipoConsulta.POR_CATEGORIA, categoria=CategoriaGasto.COMIDA
    )

    respuesta = procesar_mensaje(db, NUMERO, "Hola, gasté 200 en comida. ¿Cuánto llevo en comida?")

    lineas = respuesta.split("\n")
    assert lineas[0] == "Hola! Como te ayudo hoy?"
    assert lineas[1].startswith("✅ Gasto registrado: *RD$200.00*")
    # La consulta ya incluye el gasto recien guardado.
    assert lineas[2] == "Gastaste *RD$200.00* en comida este mes"


def test_pregunta_con_que_se_convierte_en_desglose_de_categoria(db, groq_falso):
    groq_falso["extraer_consulta"] = ConsultaGasto(
        tipo=TipoConsulta.POR_CATEGORIA, categoria=CategoriaGasto.SALUD
    )

    respuesta = procesar_mensaje(db, NUMERO, "¿qué gasté en salud?")

    # Sin gastos, el desglose por categoria responde con su propio mensaje.
    assert respuesta == "No tienes gastos en salud este mes."


def test_categoria_directa_no_llama_a_groq(db, groq_falso):
    respuesta = procesar_mensaje(db, NUMERO, "comida")

    assert respuesta == "Gastaste *RD$0.00* en comida este mes"


def test_registra_gasto_fijo(db, groq_falso, monkeypatch):
    from datetime import date
    monkeypatch.setattr(expense_service, "calcular_proxima_fecha", lambda dia: date(2026, 9, 12))
    monkeypatch.setattr(expense_service, "dias_restantes", lambda dia: 2)
    groq_falso["extraer_gasto_fijo"] = ExtraccionGastoFijo(
        monto=500, categoria=CategoriaGasto.SERVICIOS, descripcion="Netflix", dia_mes=12
    )

    respuesta = procesar_mensaje(db, NUMERO, "Netflix RD$500 el 12 de cada mes")

    assert respuesta == (
        "📍 Pago fijo registrado: *RD$500.00* - Netflix (servicios)\n"
        "Se paga el *12 de cada mes*. Próximo: 12/09/2026 (faltan 2 días)."
    )
    assert db.query(GastoFijo).count() == 1


def test_gasto_fijo_que_groq_no_entiende(db, groq_falso):
    groq_falso["extraer_gasto_fijo"] = ValueError("json invalido")

    respuesta = procesar_mensaje(db, NUMERO, "algo 500 cada mes")

    assert respuesta.startswith("No pude entender ese pago fijo")
    assert db.query(GastoFijo).count() == 0


def test_pregunta_de_gasto_fijo(db, groq_falso):
    groq_falso["extraer_consulta_gasto_fijo"] = ConsultaGastoFijo(termino="bhd")

    respuesta = procesar_mensaje(db, NUMERO, "cuando pago el prestamo del bhd")

    assert respuesta == "No encontre ningun pago fijo que coincida con 'bhd'."


def test_texto_libre_busca_por_descripcion(db, groq_falso, usuario):
    from app.repositories.gasto_repository import crear_gasto
    crear_gasto(db, usuario.id, 350, CategoriaGasto.SERVICIOS, "Netflix")

    respuesta = procesar_mensaje(db, usuario.numero_whatsapp, "netflix")

    assert respuesta == 'Gastaste *RD$350.00* en: "netflix" este mes'


def test_texto_sin_sentido_devuelve_ayuda(db, groq_falso):
    respuesta = procesar_mensaje(db, NUMERO, "asdfgh")

    assert respuesta.startswith("👋 ¡Hola! Puedo registrar tus gastos")
