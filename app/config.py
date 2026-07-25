from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Telegram
    telegram_bot_token: str
    telegram_webhook_secret: str
    telegram_webhook_path_secret: str
    telegram_allowed_chat_id: int

    # LLM (OpenRouter — OpenAI-compatible endpoint proxying many providers)
    openrouter_api_key: str
    openrouter_model: str = "anthropic/claude-sonnet-5"
    llm_max_tokens: int = 2048

    log_level: str = "INFO"


settings = Settings()
