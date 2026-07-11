from typing import Optional
from sqlalchemy.orm import Session
from app.models.gasto import CategoriaGasto
from app.models.gasto_fijo import GastoFijo
from app.services.query_service import _normalizar_texto
from app.services.date_utils import calcular_proxima_fecha, dias_restantes
from app.repositories.gasto_fijo_repository import(
    obtener_activos,
    obtener_activos_por_categoria
)

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

def _formatear_dias(dias: int) -> str:
    if dias == 0:
        return "*es hoy*"
    if dias == 1:
        return "falta *1 dia*"
    return f"faltan *{dias} dias*"

def _formatear_gasto_fijo(gf: GastoFijo) -> str:
    """
    Una linea legible: descripcion, monto, proxima fecha y dias restantes
    """
    fecha = calcular_proxima_fecha(gf.dia_mes)
    dias = dias_restantes(gf.dia_mes)
    mes = MESES[fecha.month - 1]
    return(
        f"• _{gf.descripcion}_: RD${float(gf.monto):,.2f} "
        f"el *{fecha.day} de {mes}* ({_formatear_dias(dias)})"
    )

def buscar_gastos_fijos_por_descripcion(db: Session, usuario_id: int, termino: str) -> list[GastoFijo]:
    """
    Trae los activos y filtra en python reusando la misma normalizacion que ya se usa para los gastos historicos: asi 'bhd' matchea con 'prestamo bhd'.
    """
    fijos = obtener_activos(db, usuario_id)
    termino_normalizado = _normalizar_texto(termino)

    return [
        gf for gf in fijos
        if termino_normalizado in _normalizar_texto(gf.descripcion)
    ]

def responder_gasto_fijo(
        db: Session,
        usuario_id: int,
        termino: Optional[str] = None,
        categoria: Optional[CategoriaGasto] = None,) -> str:
    """
    Responde preguntas como 'Cuanto debo pagar X?'
    - Si no hay termino de busqueda, filtra por descripcion
    - Si no, pero hay categoria, lista los de esa categoria
    - Si no hay ninguno, lista TODOS los gastos fijos activos
    """
    if termino:
        fijos = buscar_gastos_fijos_por_descripcion(db, usuario_id, termino)
        if not fijos:
            return f"No encontre ningun pago fijo que coincida con '{termino}'."
        titulo = f"📍 Pagos fijos de '{termino}':"
    
    elif categoria is not None:
        fijos = obtener_activos_por_categoria(db, usuario_id, categoria)
        if not fijos:
            return f"No tienes pagos fijos registrados en {categoria.value}."
        titulo = f"📍 Tus pagos fijos de {categoria.value}:"

    else:
        fijos = obtener_activos(db, usuario_id)
        if not fijos:
            return "No tienes pagos fijos registrados todavia."
        titulo = f"📍 Todos tus pagos fijos:"
    
    fijos = sorted(fijos, key=lambda gf: dias_restantes(gf.dia_mes))
    lineas = [_formatear_gasto_fijo(gf) for gf in fijos]
    total = sum(float(gf.monto) for gf in fijos)

    return f"{titulo}\n" + "\n" .join(lineas) + f"\n\nTotal mensual: *RD${total:,.2f}*"

