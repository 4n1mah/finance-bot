from app.core.database import Base
from sqlalchemy import Column, Integer, String

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    numero_whatsapp = Column(String, unique=True, nullable=False)