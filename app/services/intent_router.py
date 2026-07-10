from enum import Enum
import re

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

PALABRAS_GASTO = [
    "gasté", "gaste", "pagué", "pague",
    "compré", "compre", "costó", "costo",
]

def detectar_intenciones(texto_usuario: str) -> list[Intencion]:
    """
    Ahora devuelve una LISTA de intenciones en vez de una sola.
    Esto permite procesar mensajes como "Hola, gasté 200 en comida.
    ¿Cuánto llevo gastado?" que tienen saludo + gasto + pregunta juntos.
    """
    texto_normalizado = texto_usuario.lower().strip()
    intenciones = []

    for palabra in PALABRAS_SALUDO:
        if palabra in texto_normalizado:
            intenciones.append(Intencion.SALUDO)
            break

    for palabra in PALABRAS_GASTO:
        if palabra in texto_normalizado and bool(re.search(r"\d", texto_normalizado)):
            intenciones.append(Intencion.REGISTRAR_GASTO)
            break

    if "?" in texto_normalizado:
        intenciones.append(Intencion.PREGUNTA)
    else:
        for palabra in PALABRAS_PREGUNTA:
            if palabra in texto_normalizado:
                intenciones.append(Intencion.PREGUNTA)
                break

    return intenciones
