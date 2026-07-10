import re
import unicodedata
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.schemas.gasto_schema import ConsultaGasto, TipoConsulta, PeriodoConsulta
from app.repositories.gasto_repository import (
    obtener_total_general,
    obtener_total_por_categoria_especifica,
    obtener_gastos_detalle,
    obtener_total_por_categoria
)

TZ_LOCAL = timezone(timedelta(hours=-4))
UTC = timezone.utc


def _a_utc_naive(dt_local: datetime) -> datetime:
    """
    Convierte un datetime en zona local a UTC y le quita el tzinfo.
    """
    return dt_local.astimezone(UTC).replace(tzinfo=None)


def _rango_por_periodo(periodo: PeriodoConsulta) -> tuple[datetime, datetime, str]:
    """
    Traduce un PeriodoConsulta a un rango [Inicio, Fin] en UTC + etiqueta legible
    """
    ahora = datetime.now(TZ_LOCAL)
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    if periodo == PeriodoConsulta.HOY:
        inicio, fin, etiqueta = inicio_hoy, inicio_hoy + timedelta(days=1), "hoy"

    elif periodo == PeriodoConsulta.AYER:
        inicio, fin, etiqueta = inicio_hoy - timedelta(days=1), inicio_hoy, "ayer"

    elif periodo == PeriodoConsulta.ESTA_SEMANA:
        inicio = inicio_hoy - timedelta(days=ahora.weekday())
        fin, etiqueta = inicio + timedelta(days=7), "esta semana"

    elif periodo == PeriodoConsulta.SEMANA_PASADA:
        inicio_semana_actual = inicio_hoy - timedelta(days=ahora.weekday())
        inicio = inicio_semana_actual - timedelta(days=7)
        fin, etiqueta = inicio_semana_actual, "la semana pasada"

    elif periodo == PeriodoConsulta.MES_PASADO:
        inicio_mes_actual = inicio_hoy.replace(day=1)
        inicio = (inicio_mes_actual - timedelta(days=1)).replace(day=1)
        fin, etiqueta = inicio_mes_actual, "el mes pasado"

    else:
        inicio = inicio_hoy.replace(day=1)
        if inicio.month == 12:
            fin = inicio.replace(year=inicio.year + 1, month=1)
        else:
            fin = inicio.replace(month=inicio.month + 1)
        etiqueta = "este mes"

    return _a_utc_naive(inicio), _a_utc_naive(fin), etiqueta


def _rango_dia_especifico(dia: int) -> tuple[datetime, datetime, str]:
    """
    Rango [inicio, fin] para un dia puntual del MES ACTUAL, en hora local.
    """
    ahora = datetime.now(TZ_LOCAL)
    try:
        inicio = ahora.replace(day=dia, hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        raise ValueError(f"el dia {dia} no existe en el mes actual")

    fin = inicio + timedelta(days=1)
    etiqueta = f"el {dia} de este mes"
    return _a_utc_naive(inicio), _a_utc_naive(fin), etiqueta

def _normalizar_texto(texto: str) -> str:
    """
    Normaliza texto para comparaciones flexibles: minusculas, sin acentos, sin espacios ni signos de puntuacion
    """
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^a-z0-9]", "", texto)

    return texto

def _normalizar_manteniendo_espacios(texto: str) -> str:
    """
    Normaliza el texto SOLO quitando mayusculas y acentos, pero conservando espacios y signos de puntuacion.
    """
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto

def buscar_total_por_descripcion(db: Session, usuario_id: int, termino_busqueda: str, periodo: PeriodoConsulta = PeriodoConsulta.ESTE_MES) -> Optional[tuple[float, str, list]]:
    """
    Busca gastos cuya descripcion contenga el termino de busqueda (ambos normalizados), dentro de un periodo
    """
    inicio, fin, etiqueta = _rango_por_periodo(periodo)
    gastos = obtener_gastos_detalle(db, usuario_id, inicio, fin)

    termino_normalizado = _normalizar_texto(termino_busqueda)
    coincidencias = [
        g for g in gastos
        if termino_normalizado in _normalizar_texto(g.descripcion)
    ]

    if not coincidencias:
        return None
    
    total = sum(float(g.monto) for g in coincidencias)
    return total, etiqueta, coincidencias

def _a_local(dt_utc: datetime) -> datetime:
    """
    Convierte un datetime naive-UTC a hora local RD
    """
    return dt_utc.replace(tzinfo=UTC).astimezone(TZ_LOCAL)

def responder_consulta(db: Session, usuario_id: int, consulta: ConsultaGasto) -> str:

    if consulta.dia_especifico is not None:
        try:
            inicio, fin, etiqueta = _rango_dia_especifico(consulta.dia_especifico)
        except ValueError as e:
            return f"No pude calcular esa fecha: {e}"
    else:
        inicio, fin, etiqueta = _rango_por_periodo(consulta.periodo)

    if consulta.tipo == TipoConsulta.TOTAL_GENERAL:
        total = obtener_total_general(db, usuario_id, inicio, fin)
        return f"Tu gasto total {etiqueta}: *RD${total:,.2f}*"

    if consulta.tipo == TipoConsulta.POR_CATEGORIA:
        if consulta.categoria is None:
            return "No entendí qué categoría quieres consultar. Intenta con algo como '¿cuánto gasté en comida?'"
        total = obtener_total_por_categoria_especifica(
            db, usuario_id, consulta.categoria, inicio, fin
        )
        return f"Gastaste *RD${total:,.2f}* en {consulta.categoria.value} {etiqueta}"
    
    if consulta.tipo == TipoConsulta.DESGLOSE_CATEGORIA:
        if consulta.categoria is None:
            return "No entendi de que categoria quieres el desglose. Intenta con 'desglosame cuanto gaste en salud'."
        
        gastos = obtener_gastos_detalle(db, usuario_id, inicio, fin, categoria=consulta.categoria)
        if not gastos:
            return f"No tienes gastos en {consulta.categoria.value} {etiqueta}."

        lineas = [
            f"• *{_a_local(g.fecha).strftime('%d/%m/%Y')}*: RD${g.monto:.2f} - _{g.descripcion}_"
            for g in gastos
        ]
        total = sum(float(g.monto) for g in gastos)

        return (
            f"📊 Tu desglose de {consulta.categoria.value} {etiqueta}: \n"
            + "\n".join(lineas)
            + f"\n\n Total: *RD${total:,.2f}*"
        )

    if consulta.tipo == TipoConsulta.DESGLOSE:
        resultados = obtener_total_por_categoria(db, usuario_id, inicio, fin)
        if not resultados:
            return f"No tienes gastos registrados {etiqueta}"

        lineas = []
        for categoria, total in resultados:
            lineas.append(f"•{categoria.value}: *RD${float(total):,.2f}*")
        
        total_general = sum(float(total) for categoria, total in resultados)

        return (
            f"📊 Tu desglose de {etiqueta}:\n"
            + "\n".join(lineas)
            + f"\n\n Total: *RD${total_general:,.2f}*"
        )

    return "No entendí tu pregunta. Intenta con '¿cuánto gasté en comida?' o '¿cuánto gasté en total?'"
