import os
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ENV = os.path.join(PROJECT_ROOT, ".env")


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ENV, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHANNEL_ID: str = ""
    ADMIN_TELEGRAM_ID: str = ""  # Single ID or list: "123456, 789101, 555555"
    ADMIN_TELEGRAM_IDS: str = "" # Multi-admin alias
    CHANNEL_FOOTER: str = (
        "💬 Telegram sahifamiz: <a href=\"https://t.me/murodalievgg\">Murodalievgg</a>\n"
        "📹 Instagram sahifamiz: <a href=\"https://instagram.com/murodalievgg\">Murodalievgg</a>\n"
        "📹 Youtube sahifamiz: <a href=\"https://youtube.com/@murodalievgg\">Murodalievgg</a>\n"
        "😍 Donat Uchun:  <a href=\"https://t.me/playdomuz_bot\">Playdom</a>"
    )

    # AI Configuration (Google Gemini / OpenAI compatible)
    GEMINI_API_KEY: str = ""
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    AI_MODEL: str = "gemini-3.1-flash-lite"

    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./mlbb_news.db"

    # Source URLs
    MLBB_SOURCE_URL: str = "https://m.mobilelegends.com"
    MPL_ID_SOURCE_URL: str = "https://id-mpl.com"
    MPL_PH_SOURCE_URL: str = "https://ph-mpl.com"
    ESPORTS_SOURCE_URL: str = "https://liquipedia.net/mobilelegends"

    # System Modes
    AUTO_PUBLISH: bool = False  # False = Admin Approval Mode (Recommended for MVP), True = Auto Mode
    APPROVAL_TIMEOUT_MINUTES: int = 30  # Auto-forward to channel if unapproved by admin after 30 mins

    # Daily Morning News Schedule (e.g. 05:00 AM Tashkent time, max 5 news items)
    DAILY_NEWS_HOUR: int = 5
    DAILY_NEWS_MINUTE: int = 0
    DAILY_NEWS_TIMEZONE: str = "Asia/Tashkent"
    MAX_DAILY_NEWS_COUNT: int = 5
    NEWS_MAX_AGE_HOURS: int = 24  # Strict filter to ignore any news older than 24 hours

    # Live Match Check Interval (in minutes, checks frequently for upcoming & finished matches)
    CHECK_INTERVAL_MPL_ID_MIN: int = 5
    CHECK_INTERVAL_MPL_PH_MIN: int = 5
    CHECK_INTERVAL_MLBB_MIN: int = 60
    CHECK_INTERVAL_ESPORTS_MIN: int = 60

    # MLBB Fun Facts, Jokes & Lore Schedule (Every 5 hours)
    FUN_POSTS_ENABLED: bool = True
    FUN_POSTS_INTERVAL_HOURS: int = 5
    FUN_POSTS_AUTO_PUBLISH: bool = False  # False = Admin Approval, True = Auto Publish to channel

    # Verification Thresholds
    MIN_RELIABILITY_SCORE: int = 80
    MIN_CONFIDENCE_SCORE: float = 0.80

    # Retry and Timeout
    HTTP_TIMEOUT_SECONDS: int = 20
    MAX_HTTP_RETRIES: int = 3

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def active_ai_key(self) -> str:
        """Return GEMINI_API_KEY if present, otherwise fallback to AI_API_KEY."""
        return (self.GEMINI_API_KEY or self.AI_API_KEY or "").strip()

    @property
    def channel_ids(self) -> List[str]:
        """
        Return list of configured Telegram channel IDs or usernames.
        Supports single ID ("-1002503816147"), username ("@murodalievgg"), link ("https://t.me/murodalievgg"),
        or comma/space-separated list.
        Automatically normalizes numeric IDs to include the -100 prefix.
        """
        if not self.TELEGRAM_CHANNEL_ID:
            return []
        import re
        tokens = [t.strip() for t in re.split(r"[,;\s]+", str(self.TELEGRAM_CHANNEL_ID)) if t.strip()]
        result: List[str] = []
        for t in tokens:
            cid = t.strip()
            if not cid:
                continue
            # Strip telegram URL prefixes
            cid = re.sub(r"^https?://t\.me/", "@", cid)
            cid = re.sub(r"^t\.me/", "@", cid)

            # Check if it is a positive integer
            if cid.isdigit():
                cid = f"-100{cid}"
            elif cid.startswith("-"):
                digits = cid[1:]
                if digits.isdigit() and not cid.startswith("-100"):
                    cid = f"-100{digits}"
            elif re.match(r"^[a-zA-Z0-9_]{4,}$", cid) and not cid.startswith("@"):
                cid = f"@{cid}"

            if cid not in result:
                result.append(cid)
        return result

    @property
    def channel_chat_id(self) -> str:
        """Primary channel ID (first configured channel) for backwards compatibility."""
        ids = self.channel_ids
        return ids[0] if ids else ""

    @property
    def admin_ids(self) -> List[int]:
        """
        Parse comma-, semicolon-, or space-separated ADMIN_TELEGRAM_ID(s) into integer list.
        Supports single ID ("6534784826") or multiple IDs ("6534784826, 12345678, 98765432").
        """
        import re
        raw_combined = f"{self.ADMIN_TELEGRAM_ID} {self.ADMIN_TELEGRAM_IDS}".strip()
        if not raw_combined:
            return []
        ids: List[int] = []
        for token in re.split(r"[,;\s]+", raw_combined):
            cleaned = token.strip()
            if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
                val = int(cleaned)
                if val not in ids:
                    ids.append(val)
        return ids

    def is_admin(self, user_id: int) -> bool:
        """Check if user_id belongs to registered administrators."""
        return user_id in self.admin_ids


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Clear lru_cache and reload settings from environment and .env."""
    get_settings.cache_clear()
    return get_settings()


def normalize_channel_identifier(cid: str) -> str:
    """Normalize any channel identifier (url, handle, numeric id) into standard format."""
    import re
    cid = str(cid).strip()
    if not cid:
        return ""
    cid = re.sub(r"^https?://t\.me/", "@", cid)
    cid = re.sub(r"^t\.me/", "@", cid)
    if cid.isdigit():
        return f"-100{cid}"
    elif cid.startswith("-"):
        digits = cid[1:]
        if digits.isdigit() and not cid.startswith("-100"):
            return f"-100{digits}"
        return cid
    elif re.match(r"^[a-zA-Z0-9_]{4,}$", cid) and not cid.startswith("@"):
        return f"@{cid}"
    return cid


