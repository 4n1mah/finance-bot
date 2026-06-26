from groq import Groq
from app.core.config import settings
from app.schemas.gasto_schema import ExtraccionGasto
from groq.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

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

if __name__ == "__main__":
    resultado = extraer_gasto("gasté 200 pesos en comida hoy")
    print(resultado)