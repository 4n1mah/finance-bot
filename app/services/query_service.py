from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.gasto_schema import ConsultaGasto, TipoConsulta
from app.repositories.gasto_repository import (
    obtener_total_general,
    obtener_total_por_categoria_especifica,
    obtener_gastos_detalle,
)


def _rango_mes_actual():
    """
    Calcula el primer y último momento del mes actual.
    Por qué aquí y no en el repository: el repository solo sabe de BD,
    la decisión de "mes actual" es lógica de negocio — pertenece al service.
    """
    ahora = datetime.now()
    inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Primer día del mes siguiente como fecha_fin (excluido por el filtro <)
    if ahora.month == 12:
        fin = ahora.replace(year=ahora.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        fin = ahora.replace(month=ahora.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return inicio, fin


def responder_consulta(db: Session, usuario_id: int, consulta: ConsultaGasto) -> str:
    inicio, fin = _rango_mes_actual()

    if consulta.tipo == TipoConsulta.TOTAL_GENERAL:
        total = obtener_total_general(db, usuario_id, inicio, fin)
        return f"💰 Tu gasto total de este mes es: {total:.2f}"

    if consulta.tipo == TipoConsulta.POR_CATEGORIA:
        if consulta.categoria is None:
            return "⚠️ No entendí qué categoría quieres consultar. Intenta con algo como '¿cuánto gasté en comida?'"
        total = obtener_total_por_categoria_especifica(db, usuario_id, consulta.categoria, inicio, fin)
        return f"💰 Gastaste {total:.2f} en {consulta.categoria.value} este mes"

    if consulta.tipo == TipoConsulta.DESGLOSE:
        gastos = obtener_gastos_detalle(db, usuario_id, inicio, fin)
        if not gastos:
            return "📭 No tienes gastos registrados este mes."
        lineas = [f"• {g.categoria.value}: {g.monto:.2f} — {g.descripcion}" for g in gastos]
        return "📊 Tus gastos de este mes:\n" + "\n".join(lineas)

    return "⚠️ No entendí tu pregunta. Intenta con '¿cuánto gasté en comida?' o '¿cuánto gasté en total?'"