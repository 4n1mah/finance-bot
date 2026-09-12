import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.routers import webhook

# No se importa app.main: al importarse llama create_all() contra la base real.
# Se monta solo el router en una app de prueba.


@pytest.fixture
def cliente(monkeypatch):
    enviados = []
    procesados = []

    monkeypatch.setattr(webhook, "MENSAJES_PROCESADOS", set())
    monkeypatch.setattr(webhook, "enviar_typing_indicator", lambda mensaje_id: {})
    monkeypatch.setattr(
        webhook, "enviar_mensaje_whatsapp",
        lambda numero, texto: enviados.append((numero, texto)) or {},
    )

    def _procesar(db, numero, texto, nombre="Usuario"):
        procesados.append((numero, texto, nombre))
        return f"eco: {texto}"

    monkeypatch.setattr(webhook, "procesar_mensaje", _procesar)

    app = FastAPI()
    app.include_router(webhook.router)
    app.dependency_overrides[get_db] = lambda: None

    cliente = TestClient(app)
    cliente.enviados = enviados
    cliente.procesados = procesados
    return cliente


def _payload(mensaje_id="wamid.1", texto="gasté 100 en comida"):
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"profile": {"name": "Ana"}}],
                    "messages": [{
                        "id": mensaje_id,
                        "from": "18091234567",
                        "text": {"body": texto},
                    }],
                },
            }],
        }],
    }


def test_verificacion_con_token_correcto_devuelve_challenge(cliente):
    respuesta = cliente.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "test-verify-token",
        "hub.challenge": "4242",
    })

    assert respuesta.status_code == 200
    assert respuesta.json() == 4242


def test_verificacion_con_token_incorrecto_da_403(cliente):
    respuesta = cliente.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "otro",
        "hub.challenge": "4242",
    })

    assert respuesta.status_code == 403


def test_mensaje_se_procesa_y_se_responde(cliente):
    respuesta = cliente.post("/webhook", json=_payload())

    assert respuesta.json() == {"status": "recibido"}
    assert cliente.procesados == [("18091234567", "gasté 100 en comida", "Ana")]
    assert cliente.enviados == [("18091234567", "eco: gasté 100 en comida")]


def test_mensaje_duplicado_no_se_procesa_dos_veces(cliente):
    cliente.post("/webhook", json=_payload(mensaje_id="wamid.X"))
    respuesta = cliente.post("/webhook", json=_payload(mensaje_id="wamid.X"))

    assert respuesta.json() == {"status": "duplicado"}
    assert len(cliente.procesados) == 1


def test_evento_de_status_se_ignora(cliente):
    payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "read"}]}}]}]}

    respuesta = cliente.post("/webhook", json=payload)

    assert respuesta.json() == {"status": "ignorado"}
    assert cliente.procesados == []


def test_mensaje_que_no_es_texto_se_ignora(cliente):
    # Una imagen no trae "text": no debe tumbar el webhook con un 500.
    payload = _payload()
    del payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]

    respuesta = cliente.post("/webhook", json=payload)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ignorado"}
    assert cliente.procesados == []
