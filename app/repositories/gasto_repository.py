from sqlalchemy.orm import Session
from app.models.gasto import Gasto, CategoriaGasto
from datetime import datetime
from sqlalchemy import func

def crear_gasto(db: Session, usuario_id: int, monto, categoria, descripcion):
    nuevo_gasto = Gasto(
        usuario_id=usuario_id,
        monto=monto,
        categoria=categoria,
        descripcion=descripcion
    )
    db.add(nuevo_gasto)
    db.commit()
    db.refresh(nuevo_gasto)
    return nuevo_gasto

def obtener_total_por_categoria(db: Session, usuario_id: int, fecha_inicio: datetime, fecha_fin: datetime):
    resultados = (
        db.query(Gasto.categoria, func.sum(Gasto.monto))
        .filter(Gasto.usuario_id == usuario_id)
        .filter(Gasto.fecha >= fecha_inicio)
        .filter(Gasto.fecha < fecha_fin)
        .group_by(Gasto.categoria)
        .all()
    )
    return resultados

def obtener_total_general(db: Session, usuario_id: int, fecha_inicio: datetime, fecha_fin: datetime):
    total = (
        db.query(func.sum(Gasto.monto))
        .filter(Gasto.usuario_id == usuario_id)
        .filter(Gasto.fecha >= fecha_inicio)
        .filter(Gasto.fecha < fecha_fin)
        .scalar()
    )
    return total or 0

def obtener_total_por_categoria_especifica(db: Session, usuario_id: int, categoria: CategoriaGasto, fecha_inicio: datetime, fecha_fin: datetime):
    total = (
        db.query(func.sum(Gasto.monto))
        .filter(Gasto.usuario_id == usuario_id)
        .filter(Gasto.categoria == categoria)
        .filter(Gasto.fecha >= fecha_inicio)
        .filter(Gasto.fecha < fecha_fin)
        .scalar()
    )
    return total or 0


def obtener_gastos_detalle(db: Session, usuario_id: int, fecha_inicio: datetime, fecha_fin: datetime, categoria: CategoriaGasto = None):
    query = (
        db.query(Gasto)
        .filter(Gasto.usuario_id == usuario_id)
        .filter(Gasto.fecha >= fecha_inicio)
        .filter(Gasto.fecha < fecha_fin)
    )
    if categoria is not None:
        query = query.filter(Gasto.categoria == categoria)
    return query.order_by(Gasto.fecha.desc()).all()