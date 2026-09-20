from enum import Enum
import re
import unicodedata
from typing import Optional
from app.models.categorias import CategoriaGasto

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


def _normalizar(texto: str) -> str:
    """
    Minúsculas y sin acentos, conservando espacios y signos.

    Antes cada lista tenía que repetir la variante acentuada ("cuando" y
    "cuándo", "gaste" y "gasté"), y bastaba olvidar una para que la intención
    se perdiera en silencio. Quitando los acentos una sola vez, cada palabra
    clave se escribe una vez.
    """
    texto = texto.lower().strip()
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")


PALABRAS_RECURRENCIA = [
    "cada mes", "todos los meses", "mensual", "al mes",
    "cada dia", "suscripcion",
]

# Cualquier pregunta con "cuando" pide una FECHA, y lo único con fecha que el
# bot conoce son los pagos fijos: responder_consulta solo sabe devolver montos.
# Mandarla por el camino de consultas daba siempre una respuesta absurda
# ("cuando es el prestamo?" se contestaba con el total gastado del mes).
# \b evita que "cuanto" entre por aquí, que difiere en una sola letra.
RE_CUANDO = re.compile(r"\bcuando\b")

PALABRAS_PREGUNTA_FIJO = [
    "pagos fijos", "gastos fijos", "mis suscripciones",
    "que debo pagar", "que tengo que pagar",
    "proximo pago", "proximos pagos",
]

PALABRAS_PREGUNTA = [
    "cuanto", "cuanta", "cual",
    "total", "resumen", "balance", "detall", "desglos",
    "gaste en",
]

PALABRAS_SALUDO = [
    "hola", "hey", "buenas", "hi", "hello",
    "buen dia", "buenos dias", "buenas tardes", "buenas noches", "holi", "oye"
]

PALABRAS_GASTO = [
    "gaste", "pague", "compre", "costo",
]

def detectar_intenciones(texto_usuario: str) -> list[Intencion]:
    """
    Devuelve una LISTA de intenciones en vez de una sola.
    Esto permite procesar mensajes como "Hola, gasté 200 en comida.
    ¿Cuánto llevo gastado?" que tienen saludo + gasto + pregunta juntos.
    """
    texto_normalizado = _normalizar(texto_usuario)
    intenciones = []

    for palabra in PALABRAS_SALUDO:
        if palabra in texto_normalizado:
            intenciones.append(Intencion.SALUDO)
            break

    contiene_digito = bool(re.search(r"\d", texto_normalizado))
    tiene_recurrencia = any(p in texto_normalizado for p in PALABRAS_RECURRENCIA)
    es_pregunta_fijo = (
        bool(RE_CUANDO.search(texto_normalizado))
        or any(p in texto_normalizado for p in PALABRAS_PREGUNTA_FIJO)
    )

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
    texto_sin_dias = re.sub(r"\b(el|dia)\s+\d{1,2}\b", "", texto_normalizado)
    contiene_monto = bool(re.search(r"\d", texto_sin_dias))

    if contiene_monto and (tiene_palabra_gasto or not es_pregunta):
        intenciones.append(Intencion.REGISTRAR_GASTO)

    return intenciones

def detectar_categoria_directa(texto_usuario: str) -> Optional[CategoriaGasto]:
    """
    Revisa si el mensaje completo (sin nada mas) es exactamente el nombre de una categoria, ej: "comida".
    """
    texto_normalizado = _normalizar(texto_usuario)
    for categoria in CategoriaGasto:
        if texto_normalizado == categoria.value:
            return categoria
    return None
