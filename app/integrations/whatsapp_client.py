import httpx
from app.core.config import settings

GRAPH_API_VERSION = "v21.0"
URL_ENVIO = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{{phone_number_id}}/messages"

def enviar_mensaje_whatsapp(numero_destino: str, texto: str) -> dict:
    """
    Envía un mensaje de texto a un número de WhatsApp usando la API de Meta.
    Por qué un módulo aparte (no meterlo en webhook.py): es una integración
    externa, igual que groq_client.py -- mismo patrón en tu arquitectura
    (integrations/ = "hablar con servicios de afuera").

    numero_destino: el número en formato internacional sin '+' (ej: "18091234567"),
    que es justo el formato que Meta te manda en mensaje["from"] del webhook.
    """
    url = URL_ENVIO.format(phone_number_id=settings.meta_phone_number_id)

    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json",
    }

    # Esta estructura de payload es específica de la API de Meta -- no es
    # negociable, tiene que tener exactamente esta forma o Meta la rechaza.
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto},
    }

    respuesta = httpx.post(url, headers=headers, json=payload)

    # Por qué no usar raise_for_status() y dejar que explote: si Meta
    # rechaza el mensaje (token vencido, número mal formateado, etc.)
    # preferimos loguearlo y seguir, no tumbar el webhook entero --
    # el mensaje del usuario YA se guardó en la BD, perder la respuesta
    # de WhatsApp es mejor que perder el registro del gasto.
    if respuesta.status_code != 200:
        print(f"⚠️ Error enviando WhatsApp a {numero_destino}: {respuesta.status_code} - {respuesta.text}")

    return respuesta.json()