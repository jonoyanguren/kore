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
    # Default: Xiaomi MiMo multimodal (images later). Override via OPENROUTER_MODEL.
    openrouter_model: str = "xiaomi/mimo-v2-omni"
    llm_max_tokens: int = 2048
    timezone: str = "Europe/Madrid"

    # ClickUp (personal API token, never expires)
    clickup_api_token: str

    # How the companion refers to itself in chat. Editable anytime via env
    # (or later via prompts/personality.md) — no redeploy of logic needed
    # beyond restart / fly secrets.
    assistant_name: str = "Jone"

    # Storage — local path by default; overridden to the mounted Fly volume
    # path (/data/kore.db) in production so it survives redeploys.
    storage_db_path: str = "data/kore.db"

    log_level: str = "INFO"


settings = Settings()
