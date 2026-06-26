from pydantic_settings import BaseSettings
from pathlib import Path
from typing import ClassVar

class Settings(BaseSettings):
    database_url: str
    groq_api_key: str

    ENV_PATH: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent / ".env"

    model_config = {"env_file": ENV_PATH}

settings = Settings()


