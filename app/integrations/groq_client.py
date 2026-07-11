from groq import Groq
from app.core.config import settings
from app.schemas.gasto_schema import (
    ExtraccionGasto, 
    ConsultaGasto, 
    TipoConsulta, 
    ExtraccionGastoFijo,
    ConsultaGastoFijo
)
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
    Analiza una pregunta y extrae tipo, categoria y periodo de tiempo.
    """

    prompt_sistema = """Eres un asistente que analiza preguntas sobre gastos personales.
    Extrae la intención de la pregunta y devuelve SOLO este JSON sin texto adicional:
    {
    "tipo": "total_general" | "por_categoria" | "desglose",
    "categoria": "comida" | "pasaje" | "cuidado_personal" | "servicios" | "salud" | "salidas" | "ahorros" | "pedidos" | "pagos" | "otros" | null,
    "periodo": "hoy" | "ayer" | "esta_semana" | "semana_pasada" | "este_mes" | "mes_pasado",
    "dia_especifico": <numero del 1 al 31, o null> 
    }

    Reglas para "tipo":
    - Categoria especifica: ("Cuanto gaste en comida?") -> "por_categoria" y categoria = esa categoria
    - Desglose/detalle de UNA categoria especifica ("desglosame cuanto gaste en salud", "detalle de mis gastos en comida", "que son esos gastos de servicios") -> "desglose_categoria" y categoria = esa categoria 
    - Total sin categoria ("Cuanto gaste?") -> "total_general" y categoria = null
    - Resumen/desglose ("en que gaste?", "resumen") -> "desglose" y categoria = null

    Reglas para "periodo"
    - Si NO menciona ningun periodo ni dia especifico -> "este_mes"
    - "hoy" -> "hoy"
    - "ayer" -> "ayer"
    - "esta semana" / "en la semana" -> "esta_semana"
    - "la semana pasada" -> "semana_pasada"
    - "este mes" / "en el mes" -> "este_mes"
    - "el mes pasado" -> "mes_pasado"
    - SI NO menciona ningun periodo -> "este_mes"

    Reglas para "dia_especifico"
    - Si menciona un dia puntual del mes ("el 15", "el dia 3", "el 20 de este mes") -> dia_especifico = ese numero
    - Si el mensaje NO menciona un dia puntual -> "dia_especifico" = null
    - Si menciona un dia, ignora "periodo" (deja "este_mes" por defecto), dia_especifico manda
    """

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

def extraer_gastos(texto_usuario: str) -> list[ExtraccionGasto]:
    """
    Util para extraer multiples gastos, el prompt le pide a Groq un array JSON con todos los gastos detectados.
    """
    prompt_sistema = """
    Eres un extractor de datos de gastos. Dado un mensaje de WhatsApp, extrae TODOS los gastos mencionados y devuelve SOLO este JSON sin
    texto adicional: {"gastos": [{"monto": <numero>}, "categoria":"<categoria>", "descripcion": "<texto breve>"]}

    Si solo hay un gasto, devuelve un array de un elemento. Las categorias validas son exactamente: comida, pasaje,
    cuidado_personal, servicios, salud, salidas, ahorros, pedidos, pagos, otros.
    Si no puedes identificar el monto de algun gasto, usa null.
    """

    messages = [
        ChatCompletionSystemMessageParam(role="system", content=prompt_sistema),
        ChatCompletionUserMessageParam(role="user", content=texto_usuario),
    ]

    respuesta = client.chat.completions.create(model="llama-3.3-70b-versatile",
                                               messages=messages,
                                               response_format={"type":"json_object"}
                                               )
    
    datos = json.loads(respuesta.choices[0].message.content)

    return [ExtraccionGasto(**g) for g in datos["gastos"]]

def extraer_gasto_fijo(texto_usuario: str) -> ExtraccionGastoFijo:
    """
    Extrae un pago recurrente: "Netflix los 12 de cada mes por $10."
    """
    prompt_sistema = """
    Eres un extractor de gastos fijos recurrentes (suscripciones, prestamos, alquiler).
    Devuelve SOLO este JSON sin texto adicional:
    {
    "monto": <numero>,
    "categoria": "comida" | "pasaje" | "cuidado_personal" | "servicios" | "salud" | "salidas" | "ahorros" | "pedidos" | "pagos" | "otros",
    "descripcion": "<nombre corto del pago, ej: 'Netflix', 'Prestamo BHD' >",
    "dia_mes": <numero del 1 al 31>
    }

    Reglas:
    - "dia_mes" es el dia del mes en que se cobra. "los 12 de cada mes" -> 12. "el 4 de cadames" -> 4.
    - Ignora simbolos de monera y separadores de miles. "RD$2,000" -> 2000.
    - Prestamos, tarjetas y cuotas -> categoria "pagos".
    - Suscripciones digitales (Netflix, Spotify) -> categoria "servicios".
    - La descripcion debe ser corta y sin el monto ni la fecha
"""

    messages = [
        ChatCompletionSystemMessageParam(role="system", content=texto_usuario),
        ChatCompletionUserMessageParam(role="user", content=prompt_sistema)
    ]

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        response_format={"type": "json_object"},
    )

    datos = json.loads(respuesta.choices[0].message.content)
    return ExtraccionGastoFijo.model_validate_json(respuesta.choices[0].message.content)

def extraer_consulta_gasto_fijo(texto_usuario: str) -> ConsultaGastoFijo:
    """
    Analiza 'cuando debo pagar el prestamo del BHD? -> termino = BHD.
    """

    prompt_sistema = """
    Analizas preguntas sobre pagos fijos ya registrados. 
    Devuelve SOLO este JSON sin texto adicional:
    {
    "termino": "<palabra clave del pago que busca, o null>",
    "categoria": "comida" | "pasaje" | "cuidado_personal" | "servicios" | "salud" | "salidas" | "ahorros" | "pedidos" | "pagos" | "otros" | null
    }

    Reglas:
    - "termino" es la palabra mas distintiva del pago: "cuando pago el prestamo del BHD" -> "bhd". "cuando se cobra Netflix" -> "netflix".
    - Si la pregunta es general ("cuales son mis pagos fijos?", "que debo pagar este mes?") -> termino = null y categoria = null.
    - Si pregunta por un grupo ("mis suscripciones", "mis pagos") -> termino = null y categoria = esa categoria.
    - NUNCA inventes un termino si el usuario no nombro nada especifico."""

    messages = [
        ChatCompletionSystemMessageParam(role="system", content=texto_usuario),
        ChatCompletionUserMessageParam(role="user", content=prompt_sistema)
    ]

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        response_format={"type": "json_object"},
    )

    datos = json.loads(respuesta.choices[0].message.content)
    return ConsultaGastoFijo(**datos)
