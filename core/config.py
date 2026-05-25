"""
core/config.py
Centralized configuration management using Pydantic Settings.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    exa_api_key: str = ""
    groq_api_key: str = ""

    # LLM Settings
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048

    # Search Agent
    search_top_n: int = 10
    reranker_top_k: int = 5
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Reader Agent
    reader_timeout_seconds: int = 10
    reader_max_concurrent: int = 5

    # Chunking
    chunk_size_tokens: int = 750
    chunk_overlap_tokens: int = 100

    # Embedding + FAISS
    embedding_model: str = "all-MiniLM-L6-v2"
    retriever_top_k: int = 8

    # Refinement Loop
    refinement_max_iterations: int = 2

    # FastAPI
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
