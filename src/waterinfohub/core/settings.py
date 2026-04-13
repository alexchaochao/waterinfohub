from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/waterinfohub"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = "replace-me"
    llm_model: str = "gpt-4.1-mini"
    report_output_dir: Path = BASE_DIR / "data" / "reports"
    worker_timezone: str = "UTC"
    worker_daily_hour: int = 2
    worker_daily_minute: int = 30
    worker_weekly_day_of_week: str = "mon"
    worker_weekly_hour: int = 3
    worker_weekly_minute: int = 0

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")


settings = Settings()
