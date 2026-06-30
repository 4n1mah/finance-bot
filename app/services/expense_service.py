from sqlalchemy.orm import Session
from app.repositories.usuario_repository import crear_usuario, obtener_usuario_por_numero
from app.repositories.gasto_repository import crear_gasto
from app.integrations.groq_client import extraer_gasto
from app.services.intent_router import detectar_intencion, Intencion
from app.models.usuarios import Usuario
from app.models.gasto import Gasto

def _resolver_usuario(db: Session, numero_whatsapp: str, nombre: str) -> Usuario:
    """
    Paso aislado #1: garantiza que exista un Usuario para este número.
    Por qué separado: esta lógica ("buscar, si no existe crear") es
    reutilizable y testeable sola, sin necesitar Groq ni gastos para nada.
    Si mañana agregas un endpoint de "registro manual", la reusas tal cual.
    """
    usuario = obtener_usuario_por_numero(db, numero_whatsapp)
    if usuario is None:
        usuario = crear_usuario(db, nombre=nombre, numero_whatsapp=numero_whatsapp)
    return usuario


def _formatear_confirmacion(gasto: Gasto) -> str:
    """
    Paso aislado #2: convierte un objeto Gasto en el texto que el usuario
    va a leer en WhatsApp. Separarlo de la lógica de guardado significa
    que puedes cambiar el formato del mensaje sin tocar nada de la BD.
    """
    return (
        f"✅ Gasto registrado: {gasto.monto} en {gasto.categoria.value} "
        f"({gasto.descripcion})"
    )


def procesar_mensaje(db: Session, numero_whatsapp: str, texto: str, nombre: str = "Usuario") -> str:
    """
    Función orquestadora — es la ÚNICA que webhook.py va a llamar.
    Internamente delega cada responsabilidad a una pieza chica, en este orden:
      1. decide qué quiere el usuario (intent_router)
      2. resuelve el usuario en BD
      3. le pide a Groq que extraiga los datos del gasto
      4. guarda el gasto
      5. arma el mensaje de respuesta
    Si algo falla, el traceback te dice exactamente en cuál de estos 5
    pasos fue — eso es lo que ganamos con la Opción B.
    """
    intencion = detectar_intencion(texto)

    # V1 todavía no responde preguntas (eso es V1.1). Avisamos al usuario
    # en vez de mandarle el texto a Groq sin sentido.
    if intencion == Intencion.PREGUNTA:
        return "🤖 Por ahora solo puedo registrar gastos. Pronto podré responder preguntas como esta."

    usuario = _resolver_usuario(db, numero_whatsapp, nombre)

    extraccion = extraer_gasto(texto)

    gasto = crear_gasto(
        db,
        usuario_id=usuario.id,
        monto=extraccion.monto,
        categoria=extraccion.categoria,
        descripcion=extraccion.descripcion,
    )

    return _formatear_confirmacion(gasto)