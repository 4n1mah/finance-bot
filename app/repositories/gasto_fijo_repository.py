from sqlalchemy.orm import Session
from app.models.gasto_fijo import GastoFijo
from app.models.gasto import CategoriaGasto

def crear_gasto_fijo(db: Session, usuario_id: int, monto, categoria, descripcion, dia_mes: int):
    nuevo = GastoFijo(
        usuario_id=usuario_id,
        monto=monto,
        categoria=categoria,
        descripcion=descripcion,
        dia_mes=dia_mes,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

def obtener_activos(db: Session, usuario_id: int):
    """
    Todos los gastos fijos vigentes del usuario
    """
    return(
        db.query(GastoFijo)
        .filter(GastoFijo.usuario_id==usuario_id)
        .filter(GastoFijo.activo.is_(True))
        .order_by(GastoFijo.dia_mes)
        .all()
    )

def obtener_activos_por_categoria(db: Session, usuario_id: int, categoria: CategoriaGasto):
    return (
        db.query(GastoFijo)
        .filter(GastoFijo.usuario_id==usuario_id)
        .filter(GastoFijo.categoria==categoria)
        .filter(GastoFijo.activo.is_(True))
        .order_by(GastoFijo.dia_mes)
        .all()
    )

def desactivar_gasto_fijo(db: Session, gasto_fijo_id: int):
    """
    Cancelar suscripcion = marcar inactiva, no borrarla
    """
    gasto_fijo = db.query(GastoFijo).filter(GastoFijo.id == gasto_fijo_id).first()
    if gasto_fijo is None:
        return None
    gasto_fijo.activo = False
    db.commit()
    db.refresh(gasto_fijo)
    return gasto_fijo