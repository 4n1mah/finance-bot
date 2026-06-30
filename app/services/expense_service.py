from sqlalchemy.orm import Session
from app.repositories.usuario_repository import crear_usuario, obtener_usuario_por_numero
from app.repositories.gasto_repository import crear_gasto
from app.integrations.groq_client import extraer_gasto, extraer_consulta
from app.services.intent_router import detectar_intencion, Intencion
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
        f"✅ Gasto registrado: {gasto.monto} en {gasto.categoria.value} "
        f"({gasto.descripcion})"
    )

def procesar_mensaje(db: Session, numero_whatsapp: str, texto: str, nombre: str = "Usuario") -> str:
    intencion = detectar_intencion(texto)
    usuario = _resolver_usuario(db, numero_whatsapp, nombre)

    if intencion == Intencion.PREGUNTA:
        consulta = extraer_consulta(texto)
        return responder_consulta(db, usuario.id, consulta)

    extraccion = extraer_gasto(texto)
    if extraccion.monto is None:
        return "⚠️ No pude identificar el monto. Intenta con algo como 'gasté 200 en comida'."

    gasto = crear_gasto(
        db,
        usuario_id=usuario.id,
        monto=extraccion.monto,
        categoria=extraccion.categoria,
        descripcion=extraccion.descripcion,
    )
    return _formatear_confirmacion(gasto)