from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_ORIGINS: str = 'http://localhost:5173'
    RESOURCE_DIR: str = 'rag/knowledge_base/raw'
    MAX_RESOURCE_MB: int = 20
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    # Added RAG Settings
    RAG_CHROMA_DIR: str = 'rag/chroma_store'
    RAG_MODEL_CACHE: str = 'models/embedding_cache'
    RAG_EMBEDDING_MODEL: str = 'sentence-transformers/all-MiniLM-L6-v2'
    RAG_MIN_RELEVANCE: float = 0.20
    #Password Recovery Setting
        # Password recovery / SMTP
    SMTP_HOST: str = ''
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ''
    SMTP_PASSWORD: str = ''
    SMTP_FROM_EMAIL: str = ''
    SMTP_USE_TLS: bool = True
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    FRONTEND_BASE_URL: str = 'http://localhost:5173'
settings = Settings()

def allowed_origins() -> list[str]:
    return [x.strip() for x in settings.FRONTEND_ORIGINS.split(',') if x.strip()]
