"""Application settings, loaded once from the environment."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

#: backend/ - so relative paths in .env resolve the same however the app is started.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Supabase ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # --- LLM ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- vector store ---
    chroma_persist_dir: str = "./.chroma"

    # --- scrapers (app/scrapers/) -----------------------------------------
    # The migrated Daraz scraper reads these. They are the standalone
    # scraper's own defaults, kept verbatim so its timing behaviour is
    # unchanged; only the place they are loaded from has moved here.
    scraper_timeout: int = 25              # requests/HTTP timeout, seconds
    playwright_timeout: int = 60           # browser navigation budget; must exceed the above
    playwright_block_media: bool = True    # abort image/font/media requests for speed
    playwright_serialize: bool = True      # one headless browser at a time
    scraper_enable_playwright: bool = True
    scraper_max_reviews: int = 40
    # Alibaba (app/scrapers/alibaba/): minimum gap between requests to the site,
    # widened automatically if robots.txt declares a longer Crawl-delay, and how
    # many wordings of a product title are searched before giving up.
    alibaba_request_delay_seconds: float = 2.5
    alibaba_max_search_queries: int = 3
    embedding_cache_dir: str = "./.models"

    # --- app ---
    demo_mode: bool = True
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def is_demo(self) -> bool:
        """Demo mode is forced on whenever Supabase is not configured, so a
        fresh clone runs end to end with no external services."""
        return self.demo_mode or not self.has_supabase

    @property
    def embedding_cache_path(self) -> str:
        """Keeps sentence-transformers downloads inside the project rather than
        in the user profile."""
        path = Path(self.embedding_cache_dir)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
