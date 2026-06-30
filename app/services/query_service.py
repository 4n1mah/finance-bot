from sqlalchemy.orm import Session
from app.schemas.gasto_schema import ConsultaGasto, TipoConsulta
from app.repositories.gasto_repository import (
    obtener_total_general,
    obtener_total_por_categoria_especifica,
    obtener_gastos_detalle,
)


def responder_consulta(db: Session, usuario_id: int, consulta: ConsultaGasto) -> str:
    """
    Recibe la consulta ya interpretada por Groq y decide cuál método
    del repository llamar. Toda la lógica de decisión está en Python,
    Groq solo extrajo la intención estructurada.
    """
    if consulta.tipo == TipoConsulta.TOTAL_GENERAL:
        total = obtener_total_general(db, usuario_id)
        return f"💰 Tu gasto total registrado es: {total:.2f}"

    if consulta.tipo == TipoConsulta.POR_CATEGORIA:
        if consulta.categoria is None:
            return "⚠️ No entendí qué categoría quieres consultar. Intenta con algo como '¿cuánto gasté en comida?'"
        total = obtener_total_por_categoria_especifica(db, usuario_id, consulta.categoria)
        return f"💰 Gastaste {total:.2f} en {consulta.categoria.value}"

    if consulta.tipo == TipoConsulta.DESGLOSE:
        gastos = obtener_gastos_detalle(db, usuario_id)
        if not gastos:
            return "📭 No tienes gastos registrados todavía."
        lineas = [f"• {g.categoria.value}: {g.monto:.2f} — {g.descripcion}" for g in gastos]
        return "📊 Tus gastos:\n" + "\n".join(lineas)

    return "⚠️ No entendí tu pregunta. Intenta con '¿cuánto gasté en comida?' o '¿cuánto gasté en total?'"