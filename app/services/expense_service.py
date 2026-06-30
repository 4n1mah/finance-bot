from sqlalchemy.orm import Session
from app.repositories.usuario_repository import crear_usuario, obtener_usuario_por_numero
from app.repositories.gasto_repository import crear_gasto
from app.integrations.groq_client import extraer_gasto, extraer_consulta
from app.services.intent_router import detectar_intenciones, Intencion
from app.services.query_service import responder_consulta
from app.models.usuarios import Usuario
from app.models.gasto import Gasto

def _resolver_usuario(db: Session, numero_whatsapp: str, nombre: str) -> Usuario:
    usuario = obtener_usuario_por_numero(db, numero_whatsapp)
    if usuario is None:
        usuario = crear_usuario(db, nombre=nombre, numero_whatsapp=numero_whatsapp)
    return usuario

def _formatear_confirmacion(gasto: Gasto) -> str:
    return (
        f"✅ Gasto registrado: RD${gasto.monto} en {gasto.categoria.value} "
        f"({gasto.descripcion})"
    )

def procesar_mensaje(db: Session, numero_whatsapp: str, texto: str, nombre: str = "Usuario") -> str:
    intenciones = detectar_intenciones(texto)
    usuario = _resolver_usuario(db, numero_whatsapp, nombre)
    partes = []

    if Intencion.SALUDO in intenciones:
        partes.append("Hola! Como te ayudo hoy?")

    if Intencion.REGISTRAR_GASTO in intenciones and Intencion.PREGUNTA not in intenciones:
        extraccion = extraer_gasto(texto)
        if extraccion.monto is None:
            partes.append("⚠️ No pude identificar el monto. Intenta con algo como 'gasté 200 en comida'.")
        else:
            gasto = crear_gasto(
                db,
                usuario_id=usuario.id,
                monto=extraccion.monto,
                categoria=extraccion.categoria,
                descripcion=extraccion.descripcion,
            )
            partes.append(_formatear_confirmacion(gasto))

    if Intencion.REGISTRAR_GASTO in intenciones and Intencion.PREGUNTA in intenciones:
        extraccion = extraer_gasto(texto)
        if extraccion.monto is None:
            partes.append("⚠️ No pude identificar el monto del gasto.")
        else:
            gasto = crear_gasto(
                db,
                usuario_id=usuario.id,
                monto=extraccion.monto,
                categoria=extraccion.categoria,
                descripcion=extraccion.descripcion,
            )
            partes.append(_formatear_confirmacion(gasto))
        consulta = extraer_consulta(texto)
        partes.append(responder_consulta(db, usuario.id, consulta))

    # PREGUNTA sola (sin gasto)
    elif Intencion.PREGUNTA in intenciones and Intencion.REGISTRAR_GASTO not in intenciones:
        consulta = extraer_consulta(texto)
        partes.append(responder_consulta(db, usuario.id, consulta))

    # Si solo hay SALUDO sin gasto ni pregunta
    if not partes:
        partes.append("👋 ¡Hola! Puedo registrar tus gastos o responder preguntas como '¿cuánto gasté en comida este mes?'")

    return "\n".join(partes)