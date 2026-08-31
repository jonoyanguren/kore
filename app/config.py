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
    # Daily driver (tools + chat). Override via OPENROUTER_MODEL.
    openrouter_model: str = "deepseek/deepseek-v4-pro"
    # Heavier model for mega-asks / dream / Gmail drafts. Dogfood: Haiku (~⅓ Sonnet).
    # Alt via env: moonshotai/kimi-k2.5 or anthropic/claude-sonnet-4.6
    openrouter_model_strong: str = "anthropic/claude-haiku-4.5"
    # Speech-to-text (console mic). Same OpenRouter key.
    openrouter_stt_model: str = "openai/whisper-1"
    openrouter_stt_language: str = "es"
    # Optional USD budget for % if /credits fails and the key has no limit.
    openrouter_budget_usd: float = 0.0
    llm_max_tokens: int = 4096
    timezone: str = "Europe/Madrid"

    # ClickUp (personal API token, never expires)
    clickup_api_token: str

    # How the companion refers to itself in chat. Editable anytime via env
    # (or later via prompts/personality.md) — no redeploy of logic needed
    # beyond restart / fly secrets.
    assistant_name: str = "Jone"
    # Owner display name (Day greeting, etc.)
    owner_name: str = "Jon"
    # Email for the bootstrap account that inherits the existing /data home.
    owner_email: str = "jon@kore.local"

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
    # Morning cron Telegram ping. False = UI (vista Día) is the primary channel.
    dream_notify_telegram: bool = False

    # Monthly LLM cap per home (USD, from llm_spend). 0 = no cut.
    # Legacy / dogfood. Paying users get llm_cap_usd from Stripe webhooks.
    pilot_llm_cap_usd: float = 0.5

    # Stripe (Checkout + webhooks). Empty key = billing off (no paywall).
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Monthly plans 5 / 10 / 20 €. Empty 5€ price = billing off (no paywall).
    stripe_price_5: str = ""
    stripe_price_10: str = ""
    stripe_price_20: str = ""
    # Public origin for Checkout success/cancel URLs.
    public_origin: str = "https://kore.fly.dev"

    # Shared secret for web console (/api/*). Empty = console always 401.
    # Cookie kore_console or Authorization: Bearer <secret>.
    console_secret: str = ""

    # Gmail OAuth (Google Cloud OAuth client — Web application).
    # Empty client id/secret = Gmail endpoints disabled (503).
    google_client_id: str = ""
    google_client_secret: str = ""
    # Must match authorized redirect URI in Google Cloud Console.
    # Prod: https://kore.fly.dev/api/gmail/callback
    google_oauth_redirect_uri: str = "https://kore.fly.dev/api/gmail/callback"

    # Also load skills/dev/*.md into the Telegram bot (default: Cursor-only).
    load_dev_skills: bool = False

    log_level: str = "INFO"

    def resolved_vault_root(self) -> str:
        if self.vault_root.strip():
            return self.vault_root.strip()
        from pathlib import Path

        return str(Path(self.storage_db_path).resolve().parent / "vault")


settings = Settings()
