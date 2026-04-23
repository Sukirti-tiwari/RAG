from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    cohere_api_key: str = ""
    groq_api_key: str = ""

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ragdb"
    postgres_user: str = "raguser"
    postgres_password: str = "ragpassword"

    # Vector store
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "rag_documents_local"

    # Cache
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_cache_ttl: int = 3600

    # App
    app_env: str = "development"
    secret_key: str = "change_me"
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # RAG tuning
    chunk_size: int = 512
    chunk_overlap: int = 50
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    top_k_retrieval: int = 20
    top_k_rerank: int = 5
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 2048

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_sync_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
