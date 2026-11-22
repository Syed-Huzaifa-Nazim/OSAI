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
    # Groq: used only by the Instagram analysis to label comment mood.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_models: str = ""

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
    #: The team's Daraz review model (two fine-tuned XLM-RoBERTa models + review_analyzer.py).
    daraz_review_model_dir: str = str(BACKEND_DIR.parent / "Daraz_Model" / "model_package")
    # Alibaba (app/scrapers/alibaba/): minimum gap between requests to the site,
    # widened automatically if robots.txt declares a longer Crawl-delay, and how
    # many wordings of a product title are searched before giving up.
    alibaba_request_delay_seconds: float = 2.5
    alibaba_max_search_queries: int = 3
    # Website (app/scrapers/website/): how far a crawl goes from the link the
    # user submitted, and how politely. The standalone scraper's own defaults,
    # with the page budget lowered so a two-site comparison finishes in minutes.
    website_max_pages: int = 12
    website_max_depth: int = 2
    website_request_delay_seconds: float = 1.5
    website_respect_robots_txt: bool = True
    # Below this much text, a page is treated as a JavaScript shell and rendered
    # in the browser instead.
    website_min_http_text_length: int = 500
    # Instagram (app/scrapers/instagram/): scraping runs on Apify's hosted
    # Instagram actor, which does the fetching on their infrastructure and
    # returns JSON. Without a token the platform reports itself unavailable
    # rather than failing halfway through a run.
    apify_api_token: str = ""
    apify_instagram_actor_id: str = "apify/instagram-scraper"
    # Every collected post can be opened on the results screen, and an opened
    # post shows its comments, so the post budget is what bounds the scrape:
    # 12 posts per profile with every post's comments read, rather than 20
    # posts with most of them having nothing to show.
    instagram_posts_limit: int = 30
    # Score each post's picture or video with the models we trained (needs those models trained).
    instagram_score_media: bool = True
    # Topic gaps (app/analysis/instagram/topics.py). Off: the topic model reads English captions only, and its
    # 12 topics come from general business accounts, so it fits Roman Urdu shops poorly.
    instagram_topics: bool = False
    # Posting-time gaps show times in the shop's own time zone (Instagram gives UTC). Pakistan by default.
    instagram_timezone: str = "Asia/Karachi"
    instagram_comments_limit: int = 20
    # Comments are a second actor run and by far the slowest part of a social
    # scrape (~80s for one profile, measured). 0 means every collected post
    # gets its comments; a positive value caps it at that many posts, busiest
    # first. Every post keeps its like and comment counts either way.
    instagram_comment_posts_limit: int = 0
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
    def has_apify(self) -> bool:
        """Instagram scraping goes through Apify, so no token means no Instagram."""
        return bool(self.apify_api_token)

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
