from pydantic_settings import BaseSettings
from pathlib import Path
from typing import ClassVar

class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    meta_verify_token: str
    meta_access_token: str
    meta_phone_number_id: str

    # Groq retira modelos cada pocos meses y el dia que lo hace la API responde
    # 404 model_not_found: el bot deja de entender mensajes aunque el servicio
    # siga arriba. Con esto el cambio es editar una variable en el panel del
    # host, sin tocar codigo ni volver a desplegar.
    groq_model: str = "openai/gpt-oss-120b"

    ENV_PATH: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent / ".env"

    model_config = {"env_file": ENV_PATH}

settings = Settings()


