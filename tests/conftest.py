import os

# Settings() se construye al importar app.core.config y exige estas variables.
# Se fijan ANTES de importar cualquier modulo de app/ para que los tests nunca
# lean el .env real: asi no tocan la base de produccion ni gastan la API de Groq.
# URL de Postgres falsa: database.py crea el engine al importarse, pero nunca se
# conecta a ella; los tests usan la sesion SQLite del fixture 'db'.
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["META_VERIFY_TOKEN"] = "test-verify-token"
os.environ["META_ACCESS_TOKEN"] = "test-access-token"
os.environ["META_PHONE_NUMBER_ID"] = "123456"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base

# Importar los modelos los registra en Base.metadata (igual que en main.py).
from app.models.usuarios import Usuario  # noqa: F401
from app.models.gasto import Gasto  # noqa: F401
from app.models.gasto_fijo import GastoFijo  # noqa: F401


@pytest.fixture
def db():
    """
    Una base SQLite en memoria nueva para cada test. StaticPool hace que todas
    las conexiones compartan la misma memoria; sin eso cada conexion veria una
    base vacia distinta.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def usuario(db):
    from app.repositories.usuario_repository import crear_usuario
    return crear_usuario(db, nombre="Ana", numero_whatsapp="18091234567")
