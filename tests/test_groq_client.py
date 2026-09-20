import json

import pytest

from app.integrations import groq_client

# Groq retiro llama-3.3-70b-versatile en agosto de 2026 y el bot dejo de
# entender mensajes: la API respondia 404 model_not_found mientras el servicio
# seguia arriba y respondiendo 200. El nombre del modelo estaba repetido en las
# cuatro llamadas, asi que era facil actualizar unas y olvidar otras. Estos
# tests fallan si alguna vuelve a traer el modelo escrito a mano.


class _Mensaje:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Mensaje(content)


class _RespuestaFalsa:
    """Imita lo unico que el codigo usa de la respuesta de Groq."""

    def __init__(self, content):
        self.choices = [_Choice(content)]


# Cada funcion parsea la respuesta contra su propio esquema Pydantic, asi que
# el JSON falso tiene que ser valido para ese esquema en concreto.
CASOS = [
    (
        "extraer_consulta",
        {
            "tipo": "total_general",
            "categoria": None,
            "periodo": "este_mes",
            "dia_especifico": None,
        },
    ),
    (
        "extraer_gastos",
        {"gastos": [{"monto": 350, "categoria": "pasaje", "descripcion": "uber"}]},
    ),
    (
        "extraer_gasto_fijo",
        {
            "monto": 400,
            "categoria": "servicios",
            "descripcion": "Netflix",
            "dia_mes": 12,
        },
    ),
    ("extraer_consulta_gasto_fijo", {"termino": "netflix", "categoria": None}),
]


@pytest.fixture
def espia_groq(monkeypatch):
    """
    Reemplaza la llamada a la API y guarda los kwargs con que se invoco.
    Ningun test de este archivo sale a internet.
    """
    llamadas = []

    def _fabricar(payload):
        def _create(**kwargs):
            llamadas.append(kwargs)
            return _RespuestaFalsa(json.dumps(payload))

        return _create

    def _instalar(payload):
        monkeypatch.setattr(
            groq_client.client.chat.completions, "create", _fabricar(payload)
        )
        return llamadas

    return _instalar


@pytest.mark.parametrize("nombre_funcion, payload", CASOS, ids=[c[0] for c in CASOS])
def test_usa_el_modelo_configurado(espia_groq, nombre_funcion, payload):
    llamadas = espia_groq(payload)

    getattr(groq_client, nombre_funcion)("un mensaje cualquiera")

    assert len(llamadas) == 1
    assert llamadas[0]["model"] == groq_client.MODELO


@pytest.mark.parametrize("nombre_funcion, payload", CASOS, ids=[c[0] for c in CASOS])
def test_pide_respuesta_en_json(espia_groq, nombre_funcion, payload):
    """
    Sin response_format el modelo puede envolver el JSON en texto y el parseo
    revienta, asi que las cuatro llamadas tienen que pedirlo explicitamente.
    """
    llamadas = espia_groq(payload)

    getattr(groq_client, nombre_funcion)("un mensaje cualquiera")

    assert llamadas[0]["response_format"] == {"type": "json_object"}


def test_el_modelo_sale_de_la_configuracion():
    """
    MODELO tiene que venir de settings y no de un string en el modulo: es lo
    que permite cambiar de modelo desde el panel del host sin volver a desplegar.
    """
    from app.core.config import settings

    assert groq_client.MODELO == settings.groq_model
