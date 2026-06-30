from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    """
    Dependency de FastAPI: abre una sesión, la entrega (yield), y la
    cierra automáticamente cuando termina el request. Por qué no usar
    SessionLocal() directo como en tus test scripts: en un endpoint web
    necesitas garantizar que la sesión se cierre SIEMPRE, incluso si
    algo falla a mitad del request. El try/finally con yield hace eso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

