from app.core.config import settings
from fastapi import FastAPI
from app.core.database import Base, engine
from app.models.usuarios import Usuario
from app.models.gasto import Gasto
from app.routers.webhook import router as webhook_router

Base.metadata.create_all(bind=engine)
app = FastAPI()
app.include_router(webhook_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

