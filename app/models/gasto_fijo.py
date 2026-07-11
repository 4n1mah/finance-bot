from app.core.database import Base
from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.gasto import CategoriaGasto

class GastoFijo(Base):
    __tablename__ = "gastos_fijos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    descripcion = Column(String, nullable=False)
    categoria = Column(Enum(CategoriaGasto), nullable=False)
    monto = Column(Numeric(precision=10, scale=2), nullable=False)
    dia_mes = Column(Integer, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    usuario = relationship("Usuario")