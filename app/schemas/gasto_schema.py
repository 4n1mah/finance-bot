from pydantic import BaseModel, Field
from app.models.gasto import CategoriaGasto

class ExtraccionGasto(BaseModel):
    monto: float = Field(description="El mondo gastado, como numero positivo")
    categoria: CategoriaGasto = Field(description="La categoria del gasto")
    descripcion: str = Field(description="Breve descripcion de en que se gasto")

