import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name: str = os.getenv("APP_NAME", "OntoForge API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    upload_dir: Path = data_dir / "uploads"
    ui_dir: Path = Path(__file__).resolve().parents[1] / "static"
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{(data_dir / 'app.db').as_posix()}")
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    object_storage_endpoint: str | None = os.getenv("OBJECT_STORAGE_ENDPOINT")
    search_url: str | None = os.getenv("SEARCH_URL")
    llm_provider: str = os.getenv("LLM_PROVIDER", "none")

    neo4j_uri: str | None = os.getenv("NEO4J_URI")
    neo4j_user: str | None = os.getenv("NEO4J_USER")
    neo4j_password: str | None = os.getenv("NEO4J_PASSWORD")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")

    @property
    def neo4j_enabled(self) -> bool:
        return bool(self.neo4j_uri and self.neo4j_user and self.neo4j_password)


settings = Settings()
