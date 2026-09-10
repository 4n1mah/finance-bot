import enum
from app.core.database import Base
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.models.categorias import CategoriaGasto

class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    categoria = Column(Enum(CategoriaGasto), nullable=False)
    monto = Column(Numeric(precision=10, scale=2), nullable=False)
    fecha = Column(DateTime, default=lambda : datetime.now(UTC),nullable=False)
    descripcion = Column(String, nullable=False)
    usuario = relationship("Usuario")
