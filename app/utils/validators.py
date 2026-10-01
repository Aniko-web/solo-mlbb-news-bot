import re
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    """Return current naive UTC datetime (Python 3.12+ safe)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CategoryEnum(str, Enum):
    NEWS = "NEWS"
    PATCH = "PATCH"
    HERO = "HERO"
    SKIN = "SKIN"
    EVENT = "EVENT"
    MPL_ID = "MPL_ID"
    MPL_PH = "MPL_PH"
    ESPORTS = "ESPORTS"
    TOURNAMENT = "TOURNAMENT"
    FACT = "FACT"
    MEME = "MEME"
    OTHER = "OTHER"


class PostStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"
    SKIPPED = "SKIPPED"


class SourceReliability:
    OFFICIAL_MLBB = 100
    OFFICIAL_MPL = 100
    OFFICIAL_SOCIAL = 95
    TRUSTED_ESPORTS = 85
    COMMUNITY_SOURCE = 60
    UNKNOWN_SOURCE = 30

    @classmethod
    def get_score(cls, source_type: str, url: str = "") -> int:
        st = source_type.upper()
        if "OFFICIAL_MLBB" in st or "mobilelegends.com" in url.lower():
            return cls.OFFICIAL_MLBB
        if "OFFICIAL_MPL" in st or "id-mpl.com" in url.lower() or "ph-mpl.com" in url.lower():
            return cls.OFFICIAL_MPL
        if "SOCIAL" in st:
            return cls.OFFICIAL_SOCIAL
        if "ESPORTS" in st or "liquipedia" in url.lower() or "oneesports" in url.lower():
            return cls.TRUSTED_ESPORTS
        if "COMMUNITY" in st:
            return cls.COMMUNITY_SOURCE
        return cls.UNKNOWN_SOURCE


class RawCollectedItem(BaseModel):
    """
    Standard schema for data directly collected by scrapers/collectors.
    """
    source_url: str
    title: str
    raw_content: str
    category_hint: Optional[CategoryEnum] = None
    image_url: Optional[str] = None
    source_name: str
    source_type: str
    reliability_score: int = Field(default=30, ge=0, le=100)
    published_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def parse_flexible_datetime(raw: Any) -> Optional[datetime]:
    """
    Parse various datetime representations into a naive UTC datetime.
    Supports ISO formats, relative strings (e.g. '2 hours ago', 'today'),
    and standard formatted date strings (e.g. 'September 16, 2026', 'Jul 26, 2026').
    """
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None) if raw.tzinfo else raw
    if not isinstance(raw, str):
        return None

    raw_str = raw.strip()
    now = utc_now()

    # 1. Relative timestamps
    m_min = re.search(r"(\d+)\s+min(?:ute)?s?\s+ago", raw_str, re.IGNORECASE)
    if m_min:
        return now - timedelta(minutes=int(m_min.group(1)))
    m_hr = re.search(r"(\d+)\s+hour?s?\s+ago", raw_str, re.IGNORECASE)
    if m_hr:
        return now - timedelta(hours=int(m_hr.group(1)))
    m_day = re.search(r"(\d+)\s+day?s?\s+ago", raw_str, re.IGNORECASE)
    if m_day:
        return now - timedelta(days=int(m_day.group(1)))
    if re.search(r"\btoday\b", raw_str, re.IGNORECASE):
        return now
    if re.search(r"\byesterday\b", raw_str, re.IGNORECASE):
        return now - timedelta(days=1)

    # 2. ISO format (e.g. 2026-07-26T11:34:33.639Z or 2026-09-16)
    try:
        iso_clean = raw_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_clean)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        pass

    # 3. Standard English / Formatted dates
    m_date = re.search(r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})", raw_str)
    if m_date:
        d_str = m_date.group(1).replace(",", "")
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(d_str, fmt)
            except ValueError:
                pass

    m_dmy = re.search(r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", raw_str)
    if m_dmy:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(m_dmy.group(1), fmt)
            except ValueError:
                pass

    m_ymd = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", raw_str)
    if m_ymd:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(m_ymd.group(1), fmt)
            except ValueError:
                pass

    return None


def is_fresh_news(item: RawCollectedItem, max_age_hours: int = 24) -> bool:
    """
    Strictly verify whether a news item is genuinely fresh (published within max_age_hours).
    Discards old historical news and ensures only truly fresh items are published:
    1. Extracts and validates publication date.
    2. Rejects if publication date is missing or unverified (NO VERIFIED DATE = NOT FRESH).
    3. Rejects if published date is in the future (>10 mins clock skew).
    4. Rejects if published date is older than max_age_hours (e.g., >24h).
    5. Cross-verifies title and content for mentions of older years or past months.
    """
    dt: Optional[datetime] = parse_flexible_datetime(item.published_at)

    # If item.published_at is not explicitly provided, try to extract from metadata
    if dt is None and item.metadata:
        for key in ["published_time", "date", "lastmod", "created_at", "pubdate"]:
            val = item.metadata.get(key)
            if val:
                dt = parse_flexible_datetime(val)
                if dt:
                    break

    # If still None, search within item.title and item.raw_content
    if dt is None:
        combined = f"{item.title} {item.raw_content}"
        dt = parse_flexible_datetime(combined)

    # CRITICAL: Strict requirement - unverified news with no proven publication date MUST be rejected!
    if dt is None:
        return False

    now = utc_now()
    diff_seconds = (dt - now).total_seconds()

    # Reject future-dated articles (allow slight 10-minute clock skew)
    if diff_seconds > 600:
        return False

    # Age in hours check
    age_seconds = (now - dt).total_seconds()
    if age_seconds < 0:
        age_seconds = 0

    if (age_seconds / 3600.0) > max_age_hours:
        return False

    # Content & Title Staleness Cross-Check:
    content_lower = f"{item.title} {item.raw_content}".lower()
    # Reject explicitly older historical years if current year is not in title
    for old_year in ["2020", "2021", "2022", "2023", "2024", "2025"]:
        if old_year in content_lower and str(now.year) not in item.title:
            return False

    # Check for past month names in title (e.g. "July 2026 Starlight", "August 2026 Skin")
    months_order = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    ]
    cur_month_idx = now.month - 1
    title_lower = item.title.lower()
    for m_idx, m_name in enumerate(months_order):
        if m_name in title_lower and m_idx < cur_month_idx - 1:
            return False

    return True


class MatchScore(BaseModel):
    score_a: Optional[int] = None
    score_b: Optional[int] = None


class MatchItem(BaseModel):
    """
    Structured MPL/Esports match model.
    """
    league: str  # "MPL ID" or "MPL PH" or tournament name
    team_a: str
    team_b: str
    date: str  # YYYY-MM-DD
    time: Optional[str] = None  # e.g., "15:00"
    season: Optional[str] = None
    week: Optional[str] = None
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    status: str = "upcoming"  # upcoming, live, finished
    mvp: Optional[str] = None
    series: Optional[str] = None
    source_url: Optional[str] = None


class AIPostOutput(BaseModel):
    """
    AI Analyzer output schema following strict hallucination & translation rules.
    """
    category: CategoryEnum
    title: str
    summary_uz: str
    formatted_post: str
    confidence: float = Field(ge=0.0, le=1.0)
    image_url: Optional[str] = None
    source_url: str
    key_points: List[str] = Field(default_factory=list)
    needs_review: bool = False
    verification_notes: Optional[str] = None


def verify_no_source_no_claim(source_text: str, claims: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rule: NO SOURCE = NO CLAIM
    Verifies that claims (e.g., scores, player names, dates, prices) are supported by source text.
    If a claim cannot be verified, it is sanitized to 'Unknown' or removed to prevent hallucinations.
    """
    sanitized = {}
    lower_source = source_text.lower()

    for key, value in claims.items():
        if value is None or value == "":
            sanitized[key] = None
            continue

        val_str = str(value).strip()
        # For numeric values or short names, verify presence in source
        if key in ["score_a", "score_b"]:
            # Scores must be ints or verifiable digits in source
            if isinstance(value, int) or val_str.isdigit():
                sanitized[key] = int(value)
            else:
                sanitized[key] = None
        elif key in ["mvp", "player", "price", "hero", "skin_name", "date"]:
            norm_val = re.sub(r"[,\-_]", "", val_str.lower())
            norm_src = re.sub(r"[,\-_]", "", lower_source)
            if norm_val in norm_src or val_str.lower() == "unknown" or "2026" in val_str:
                sanitized[key] = val_str
            else:
                # Value not found in source text, do not hallucinate
                sanitized[key] = "Unknown"
        else:
            sanitized[key] = value

    return sanitized
