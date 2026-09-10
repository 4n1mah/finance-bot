import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import Base, engine

# Estos tres imports parecen sobrar, pero NO los borres: importar el modulo de
# un modelo es lo que lo registra en Base.metadata, y create_all() solo crea las
# tablas que esten registradas ahi. Sin ellos la base se queda vacia.
from app.models.usuarios import Usuario  # noqa: F401
from app.models.gasto import Gasto  # noqa: F401
from app.models.gasto_fijo import GastoFijo  # noqa: F401

from app.routers.webhook import router as webhook_router

logger = logging.getLogger(__name__)

# Crea al arrancar las tablas que falten. Alcanza mientras el esquema no cambie:
# create_all() NO altera tablas que ya existen, asi que el dia que haya que
# agregar o modificar una columna hay que migrar con Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Finance Bot",
    description=(
        "Bot de WhatsApp para registrar y consultar gastos personales "
        "escritos en lenguaje natural."
    ),
    version="1.0.0",
)
app.include_router(webhook_router)


@app.get("/", tags=["estado"])
async def root():
    """
    Identifica el servicio. Sirve para confirmar de un vistazo que el deploy
    quedo arriba y para encontrar la documentacion interactiva.
    """
    return {"servicio": "finance-bot", "estado": "activo", "docs": "/docs"}


@app.get("/health", tags=["estado"])
def health():
    """
    Healthcheck real: que el proceso conteste no significa que el bot funcione,
    porque sin base de datos no puede registrar ni consultar nada. Por eso
    ademas hace un SELECT 1 contra Postgres y devuelve 503 si falla, para que
    Railway lo marque como caido en vez de darlo por sano.

    Por que 'def' y no 'async def': engine.connect() es bloqueante. Declarado
    como sincrono, FastAPI lo corre en un threadpool y no bloquea el event loop.
    """
    try:
        with engine.connect() as conexion:
            conexion.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Se loguea completo pero NO se devuelve al cliente: el mensaje de error
        # de SQLAlchemy suele incluir el host y el usuario de la conexion.
        logger.exception("Healthcheck: la base de datos no responde")
        return JSONResponse(
            status_code=503,
            content={"estado": "degradado", "base_de_datos": "sin conexion"},
        )

    return {"estado": "ok", "base_de_datos": "ok"}
