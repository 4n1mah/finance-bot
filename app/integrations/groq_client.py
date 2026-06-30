from groq import Groq
from app.core.config import settings
from app.schemas.gasto_schema import ExtraccionGasto, ConsultaGasto, TipoConsulta
from groq.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import json

client = Groq(api_key=settings.groq_api_key)

CATEGORIAS_VALIDAS = ", ".join([c.value for c in ExtraccionGasto.model_fields["categoria"].annotation])

def extraer_gasto(texto_usuario: str) -> ExtraccionGasto:
    """
    Recibe el texto crudo que el usuario escribió en WhatsApp
    (ej: "gasté 200 en comida hoy") y devuelve un objeto ExtraccionGasto
    ya validado por Pydantic.
    """
    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            ChatCompletionSystemMessageParam(
                role="system",
                content=(
                    "Eres un extractor de datos de gastos. Dado un mensaje de "
                    "WhatsApp, extrae el monto, la categoria y una descripción breve. "
                    "La categoría debe ser EXACTAMENTE una de estas opciones: "
                    f"{CATEGORIAS_VALIDAS}. Responde ÚNICAMENTE con un JSON con esta estructura exacta:"
                    "{'monto': <número>, 'categoria': '<una de las categorías válidas>', 'descripcion': '<texto breve>'}"
                ),
            ),
            ChatCompletionUserMessageParam(role="user", content=texto_usuario)
        ],
        response_format={"type": "json_object"},
    )

    contenido_json = respuesta.choices[0].message.content

    return ExtraccionGasto.model_validate_json(contenido_json)

def extraer_consulta(texto_usuario: str) -> ConsultaGasto:
    """
    Mismo patrón que extraer_gasto() pero para preguntas.
    Groq decide qué tipo de consulta es y si menciona una categoría.
    """
    from app.schemas.gasto_schema import ConsultaGasto, TipoConsulta

    prompt_sistema = """Eres un asistente que analiza preguntas sobre gastos personales.
Extrae la intención de la pregunta y devuelve SOLO este JSON sin texto adicional:
{
  "tipo": "total_general" | "por_categoria" | "desglose",
  "categoria": "Comida" | "Pasaje" | "Cuidado Personal" | "Servicios" | "Salud" | "Salidas" | "Ahorros" | "Pedidos" | "Pagos" | "Otros" | null
}

Reglas:
- Si pregunta por una categoría específica: tipo = "por_categoria" y categoria = la categoría mencionada
- Si pregunta por el total sin especificar categoría: tipo = "total_general" y categoria = null
- Si pide un resumen o desglose general: tipo = "desglose" y categoria = null"""

    messages = [
        ChatCompletionSystemMessageParam(role="system", content=prompt_sistema),
        ChatCompletionUserMessageParam(role="user", content=texto_usuario),
    ]

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        response_format={"type": "json_object"},
    )

    datos = json.loads(respuesta.choices[0].message.content)
    return ConsultaGasto(**datos)

if __name__ == "__main__":
    resultado = extraer_gasto("gasté 200 pesos en comida hoy")
    print(resultado)