from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    gemini_provider_1_api_key: str = ""
    gemini_provider_2_api_key: str = ""
    gemini_provider_3_api_key: str = ""
    gemini_provider_4_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    max_llm_attempts: int = 4
    llm_max_output_tokens: int = 400
    llm_timeout_seconds: int = 20

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    rag_top_k: int = 4

    database_url: str = ""
    duckdb_path: str = str(ROOT_DIR / "data" / "geoready.duckdb")

    rag_docs_dir: str = str(ROOT_DIR / "rag" / "documents")
    ml_dir: str = str(ROOT_DIR / "ml")

    data_dir: str = str(ROOT_DIR / "data")


@lru_cache
def get_settings() -> Settings:
    return Settings()
