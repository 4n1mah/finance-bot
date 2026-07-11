import calendar
from datetime import datetime, timedelta, timezone, date

OFFSET_RD = timezone(timedelta(hours=4))

def _dia_efectivo(anio: int, mes: int, dia_mes: int) -> int:
    """
    Si el gasto se paga el 31 pero el mes solo tiene 30 dias (o 28 en febrero), el cobro cae el ultimo dia del mes.
    """
    dias_del_mes = calendar.monthrange(anio, mes)[1]
    return min(dia_mes, dias_del_mes)

def calcular_proxima_fecha(dia_mes: int, hoy: date | None = None) -> date:
    """
    Devuelve la proxima fecha de cobro de un gasto fijo.
    Si el dia de este mes todavia no pasa (o es ese mismo dia), es este mes.
    Si ya paso, es el mes siguiente.
    """ 
    if hoy is None:
        hoy = datetime.now(OFFSET_RD).date()

    dia = _dia_efectivo(hoy.year, hoy.month, dia_mes)
    candidata = date(hoy.year, hoy.month, dia)

    if candidata >= hoy:
        return candidata
    
    if hoy.month == 12:
        anio, mes = hoy.year + 1, 1
    else:
        anio, mes = hoy.year, hoy.month + 1

    return date(anio, mes, _dia_efectivo(anio, mes, dia_mes))

def dias_restantes(dia_mes: int, hoy: date | None = None) -> int:
    """
    Cuantos dias faltan para el proximo pago.
    """
    if hoy is None:
        hoy = datetime.now(OFFSET_RD).date()
    return (calcular_proxima_fecha(dia_mes, hoy) - hoy).days