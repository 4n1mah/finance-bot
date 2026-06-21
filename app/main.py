from app.core.config import settings
from fastapi import FastAPI
from app.core.database import Base, engine
from app.models.usuarios import Usuario
from app.models.gasto import Gasto

Base.metadata.create_all(bind=engine)
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

