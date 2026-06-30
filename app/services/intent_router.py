from enum import Enum

class Intencion(str, Enum):
    """
    Representa qué quiere hacer el usuario con su mensaje.
    Por qué Enum: igual que CategoriaGasto, evita strings sueltos
    regados por el código ("registrar_gasto" escrito a mano en 3 lugares
    distintos = bug esperando a pasar si te equivocas en uno).
    """
    REGISTRAR_GASTO = "registrar_gasto"
    PREGUNTA = "pregunta"
    SALUDO = "saludo"

PALABRAS_PREGUNTA = [
    "cuanto", "cuánto", "cuanta", "cuánta",
    "cual", "cuál",
    "total", "resumen", "balance",
    "gaste en", "gasté en",  # "cuánto gasté en comida" usa esto
]

PALABRAS_SALUDO = [
    "hola", "hey", "buenas", "hi", "hello",
    "buen dia", "buenos dias", "buenas tardes", "buenas noches", "holi", "oye"
]

def detectar_intencion(texto_usuario: str) -> Intencion:
    """
    Aplica reglas léxicas simples (no ML, no LLM) para decidir si el
    mensaje es una pregunta o un registro de gasto.

    Por qué reglas y no Groq: es una decisión barata y rápida (microsegundos,
    sin costo de API) que no necesita razonamiento complejo. Reservamos el
    LLM para la parte que sí lo justifica: extraer monto/categoría/descripción
    de texto libre.

    Estrategia: "innocent until proven question" — si el texto NO contiene
    ninguna señal de pregunta, asumimos que es un registro de gasto.
    Esto es seguro para V1 porque V1 solo procesa gastos de todas formas.
    """
    texto_normalizado = texto_usuario.lower().strip()

    if "?" in texto_normalizado:
        return Intencion.PREGUNTA

    for palabra in PALABRAS_PREGUNTA:
        if palabra in texto_normalizado:
            return Intencion.PREGUNTA

    for palabra in PALABRAS_SALUDO:
        if palabra in texto_normalizado:
            return Intencion.SALUDO

    return Intencion.REGISTRAR_GASTO

if __name__ == "__main__":
    pruebas = [
        "gasté 200 en comida hoy",
        "¿cuánto gasté en comida este mes?",
        "cuanto llevo gastado",
        "pague 500 de luz",
    ]
    for texto in pruebas:
        print(f"{texto!r} -> {detectar_intencion(texto)}")