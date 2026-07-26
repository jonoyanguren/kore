from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": .env also carries DOMAIN, read only by
    # scripts/set_webhook.sh, not by the app.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Telegram
    telegram_bot_token: str
    telegram_webhook_secret: str
    telegram_webhook_path_secret: str
    telegram_allowed_chat_id: int

    # LLM (OpenRouter — OpenAI-compatible endpoint proxying many providers)
    openrouter_api_key: str
    openrouter_model: str = "anthropic/claude-sonnet-5"
    llm_max_tokens: int = 2048

    # ClickUp (personal API token, never expires)
    clickup_api_token: str

    # Storage — local path by default; overridden to the mounted Fly volume
    # path (/data/jornvis.db) in production so it survives redeploys.
    storage_db_path: str = "data/jornvis.db"

    log_level: str = "INFO"


settings = Settings()
