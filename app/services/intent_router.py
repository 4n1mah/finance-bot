from enum import Enum
import re
from typing import Optional
from app.models.gasto import CategoriaGasto

class Intencion(str, Enum):
    """
    Representa qué quiere hacer el usuario con su mensaje.
    Por qué Enum: igual que CategoriaGasto, evita strings sueltos
    regados por el código ("registrar_gasto" escrito a mano en 3 lugares
    distintos = bug esperando a pasar si te equivocas en uno).
    """
    REGISTRAR_GASTO = "registrar_gasto"
    REGISTRAR_GASTO_FIJO = "registrar_gasto_fijo"
    PREGUNTA_GASTO_FIJO = "pregunta_gasto_fijo"
    PREGUNTA = "pregunta"
    SALUDO = "saludo"

PALABRAS_RECURRENCIA = [
    "cada mes", "todos los meses", "mensual", "al mes", 
    "cada dia", "suscripcion", "suscripción"
]

PALABRAS_PREGUNTA_FIJO = [
    "cuando pago", "cuándo pago", "cuando debo pagar", "cuánto debo pagar", 
    "cuando me toca", "cuándo me toca", "cuando se cobra", "cuándo se cobra",
    "proximo pago", "próximo pago", "pagos fijos", "mis suscripciones", 
    "que debo pagar", "qué debo pagar"
]

PALABRAS_PREGUNTA = [
    "cuanto", "cuánto", "cuanta", "cuánta",
    "cual", "cuál",
    "total", "resumen", "balance", "detall", "desglos",
    "gaste en", "gasté en"
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

    contiene_digito = bool(re.search(r"\d", texto_normalizado))
    tiene_recurrencia = any(p in texto_normalizado for p in PALABRAS_RECURRENCIA)
    es_pregunta_fijo = any(p in texto_normalizado for p in PALABRAS_PREGUNTA_FIJO)

    if es_pregunta_fijo:
        intenciones.append(Intencion.PREGUNTA_GASTO_FIJO)
        return intenciones

    if tiene_recurrencia and contiene_digito:
        intenciones.append(Intencion.REGISTRAR_GASTO_FIJO)
        return intenciones 

    es_pregunta = "?" in texto_normalizado or any(palabra in texto_normalizado for palabra in PALABRAS_PREGUNTA)
    if es_pregunta:
        intenciones.append(Intencion.PREGUNTA)

    tiene_palabra_gasto = any(palabra in texto_normalizado for palabra in PALABRAS_GASTO)

    if contiene_digito and (tiene_palabra_gasto or not es_pregunta):
        intenciones.append(Intencion.REGISTRAR_GASTO)
        
    return intenciones

def detectar_categoria_directa(texto_usuario: str) -> Optional[CategoriaGasto]:
    """
    Revisa si el mensaje completo (sin nada mas) es exactamente el nombre de una categoria, ej: "comida".
    """
    texto_normalizado = texto_usuario.strip().lower()
    for categoria in CategoriaGasto:
        if texto_normalizado == categoria.value:
            return categoria
    return None