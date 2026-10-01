import hashlib
import re
from typing import Optional


def normalize_text(text: Optional[str]) -> str:
    """
    Normalize text by stripping whitespace, lowercasing, and collapsing multiple spaces.
    """
    if not text:
        return ""
    # Remove HTML tags if any
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace and lower-case
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def generate_content_hash(title: str, content: str, source_url: str = "") -> str:
    """
    Generate deterministic SHA-256 hash for deduplication.
    Uses normalized title + first 250 characters of normalized content + canonical URL.
    """
    norm_title = normalize_text(title)
    norm_content = normalize_text(content)[:250]
    
    # Strip query parameters/fragments from source_url for canonical comparison
    canonical_url = re.sub(r"[?#].*$", "", source_url.strip().lower())
    
    payload = f"{canonical_url}|{norm_title}|{norm_content}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
