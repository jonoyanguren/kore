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
    openrouter_model: str = "xiaomi/mimo-v2.5"
    llm_max_tokens: int = 2048
    timezone: str = "Europe/Madrid"

    # ClickUp (personal API token, never expires)
    clickup_api_token: str

    # How the companion refers to itself in chat. Editable anytime via env
    # (or later via prompts/personality.md) — no redeploy of logic needed
    # beyond restart / fly secrets.
    assistant_name: str = "Jone"
    # Owner display name (Day greeting, etc.)
    owner_name: str = "Jon"

    # Storage — local path by default; overridden to the mounted Fly volume
    # path (/data/kore.db) in production so it survives redeploys.
    storage_db_path: str = "data/kore.db"
    # Markdown vault (memory/diary/agenda/dreams). Empty → sibling of DB
    # (data/vault or /data/vault on Fly).
    vault_root: str = ""

    # Bearer token for POST /internal/cron/* (optional external/manual trigger).
    # Empty = cron endpoints always 403.
    cron_secret: str = ""

    # In-process morning dream at Europe/Madrid (default 09:00). Precise to ~1s.
    dream_cron_enabled: bool = True
    dream_cron_hour: int = 9
    dream_cron_minute: int = 0

    # Shared secret for web console (/api/*). Empty = console always 401.
    # Cookie kore_console or Authorization: Bearer <secret>.
    console_secret: str = ""

    # Also load skills/dev/*.md into the Telegram bot (default: Cursor-only).
    load_dev_skills: bool = False

    log_level: str = "INFO"

    def resolved_vault_root(self) -> str:
        if self.vault_root.strip():
            return self.vault_root.strip()
        from pathlib import Path

        return str(Path(self.storage_db_path).resolve().parent / "vault")


settings = Settings()
