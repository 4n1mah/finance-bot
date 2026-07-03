from enum import Enum
from pydantic import BaseModel, Field
from app.models.gasto import CategoriaGasto
from typing import Optional

class ExtraccionGasto(BaseModel):
    monto: Optional[float] = Field(description="El mondo gastado, como numero positivo")
    categoria: CategoriaGasto = Field(description="La categoria del gasto")
    descripcion: str = Field(description="Breve descripcion de en que se gasto")

class TipoConsulta(str, Enum):
    """
    Qué tipo de pregunta está haciendo el usuario.
    - TOTAL_GENERAL: "¿cuánto gasté en total?"
    - POR_CATEGORIA: "¿cuánto gasté en comida?"  (necesita categoría específica)
    - DESGLOSE: "¿en qué gasté?" / "resumen de gastos"
    """
    TOTAL_GENERAL = "total_general"
    POR_CATEGORIA = "por_categoria"
    DESGLOSE = "desglose"

class PeriodoConsulta(str, Enum):
    """
    Periodo de tiempo que el usuario quiere consultar. Groq va a extraer esto del texto libre y devolverlo como String
    """

    HOY = "hoy"
    ESTA_SEMANA = "esta_semana"
    SEMANA_PASADA = "semana_pasada"
    ESTE_MES = "este_mes"

class ConsultaGasto(BaseModel):
    tipo: TipoConsulta
    categoria: Optional[CategoriaGasto] = None
    periodo: PeriodoConsulta = PeriodoConsulta.ESTE_MES



