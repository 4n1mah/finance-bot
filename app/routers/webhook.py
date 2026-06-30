from fastapi import APIRouter, Request, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.services.expense_service import procesar_mensaje
from app.integrations.whatsapp_client import enviar_mensaje_whatsapp

MENSAJES_PROCESADOS: set[str] = set()
router = APIRouter()

@router.get("/webhook")
async def verificar_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """
    Meta llama esto UNA VEZ cuando configuras el webhook en su panel, para
    confirmar que el dueño de esta URL eres tú. Comparamos el token que
    Meta envía contra el que tú definiste, y si coincide devolvemos el
    challenge tal cual -- así Meta sabe que la conexión es legítima.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("/webhook")
async def recibir_mensaje(request: Request, db: Session = Depends(get_db)):
    """
    Meta llama esto cada vez que alguien te escribe. El payload de Meta
    tiene una estructura anidada fija -- navegamos hasta el texto y el
    número del remitente.
    """
    payload = await request.json()

    try:
        valor = payload["entry"][0]["changes"][0]["value"]

        # Si no hay "messages", es un evento de status (entregado/leído),
        # no un mensaje nuevo. Lo ignoramos sin tronar.
        if "messages" not in valor:
            return {"status": "ignorado"}

        mensaje = valor["messages"][0]
        mensaje_id = mensaje["id"]

        if mensaje_id in MENSAJES_PROCESADOS:
            return {"status": "duplicado"}

        MENSAJES_PROCESADOS.add(mensaje_id)

        numero_whatsapp = mensaje["from"]
        texto_usuario = mensaje["text"]["body"]
        nombre_usuario = valor["contacts"][0]["profile"]["name"]

    except (KeyError, IndexError):
        # Forma de payload inesperada (otro tipo de evento) -- ignoramos
        # en vez de devolver un 500 que Meta interprete como webhook caído.
        return {"status": "ignorado"}

    respuesta = procesar_mensaje(db, numero_whatsapp, texto_usuario, nombre=nombre_usuario)

    enviar_mensaje_whatsapp(numero_whatsapp, respuesta)
    return {"status": "recibido"}