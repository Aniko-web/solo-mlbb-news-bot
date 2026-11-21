import re
import json
import time
from typing import Dict, Any, List, Optional
import httpx

from app.utils.logger import logger

# Base mlbb.io URLs
BASE_URL = "https://mlbb.io/en/hero"
COUNTER_PICK_GUIDE_URL = "https://mlbb.io/en/counter-pick"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://mlbb.io/en/counter-pick",
}

# Special hero slug overrides for mlbb.io
HERO_SLUG_OVERRIDES = {
    "xborg": "xborg",
    "x.borg": "xborg",
    "x-borg": "xborg",
    "change": "change",
    "chang'e": "change",
    "yisunshin": "yi-sun-shin",
    "yi sun shin": "yi-sun-shin",
    "yi sun-shin": "yi-sun-shin",
    "yuzhong": "yu-zhong",
    "yu zhong": "yu-zhong",
    "popol and kupa": "popol-and-kupa",
    "popol kupa": "popol-and-kupa",
    "lapulapu": "lapu-lapu",
    "lapu lapu": "lapu-lapu",
    "lapu-lapu": "lapu-lapu",
    "luoyi": "luo-yi",
    "luo yi": "luo-yi",
    "gatotkaca": "gatotkaca",
    "badang": "badang",
    "aamon": "aamon",
}


class CounterPickService:
    """
    Fetches real-time MLBB Counter-Pick recommendations from mlbb.io.
    Provides Best Pick Against <Hero>, win rate advantage, items, and link preview.
    """

    # In-memory cache: slug -> (timestamp, data_dict)
    _CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
    CACHE_TTL_SECONDS = 3600  # 1 hour

    @classmethod
    def slugify_hero_name(cls, name: str) -> str:
        """Converts user input into official mlbb.io hero URL slug."""
        cleaned = name.strip().lower()
        if cleaned in HERO_SLUG_OVERRIDES:
            return HERO_SLUG_OVERRIDES[cleaned]
        s = cleaned.replace("'", "").replace(".", "")
        return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

    @classmethod
    def get_canonical_hero_name(cls, raw_query: str) -> str:
        """Returns clean display name for hero."""
        raw = raw_query.strip()
        slug = cls.slugify_hero_name(raw)

        # Common display name adjustments
        display_map = {
            "yi-sun-shin": "Yi Sun-shin",
            "yu-zhong": "Yu Zhong",
            "xborg": "X.Borg",
            "change": "Chang'e",
            "popol-and-kupa": "Popol and Kupa",
            "lapu-lapu": "Lapu-Lapu",
            "luo-yi": "Luo Yi",
        }
        if slug in display_map:
            return display_map[slug]

        # Default title casing
        return " ".join(word.capitalize() for word in raw.replace("-", " ").split())

    @classmethod
    async def get_counter_data(cls, hero_query: str) -> Optional[Dict[str, Any]]:
        """
        Fetches counter pick data for the requested hero from mlbb.io.
        Returns parsed dictionary or None if hero not found.
        """
        if not hero_query or not hero_query.strip():
            return None

        slug = cls.slugify_hero_name(hero_query)
        hero_display = cls.get_canonical_hero_name(hero_query)

        # 1. Check in-memory cache
        now = time.time()
        if slug in cls._CACHE:
            cached_time, cached_data = cls._CACHE[slug]
            if now - cached_time < cls.CACHE_TTL_SECONDS:
                logger.debug(f"[CounterPickService] Cache hit for hero '{slug}'")
                return cached_data

        target_url = f"{BASE_URL}/{slug}/counter"
        logger.info(f"[CounterPickService] Fetching counter data from {target_url}...")

        html = ""
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
                resp = await client.get(target_url)
                if resp.status_code == 200:
                    html = resp.text
                elif resp.status_code == 404:
                    # Retry with alternate slug without hyphens if applicable
                    alt_slug = slug.replace("-", "")
                    if alt_slug != slug:
                        alt_url = f"{BASE_URL}/{alt_slug}/counter"
                        resp_alt = await client.get(alt_url)
                        if resp_alt.status_code == 200:
                            html = resp_alt.text
                            slug = alt_slug
                            target_url = alt_url
                else:
                    logger.warning(f"[CounterPickService] HTTP {resp.status_code} for {target_url}")
                    return None
        except Exception as e:
            logger.error(f"[CounterPickService] Network error fetching {target_url}: {e}")
            return None

        if not html:
            return None

        # 2. Parse Best Counters and FAQ
        data = cls._parse_counter_html(html, hero_display, slug, target_url)
        if data:
            cls._CACHE[slug] = (now, data)
        return data

    @classmethod
    def _parse_counter_html(
        cls,
        html: str,
        hero_display: str,
        slug: str,
        target_url: str
    ) -> Optional[Dict[str, Any]]:
        """Extracts best counters, percentages, and items from mlbb.io HTML."""
        # 1. Detect Real Hero Name from title or meta tags
        title_match = re.search(r"<title>([A-Za-z0-9'\.\s\-]+?)\s+Counters", html)
        canonical_hero = title_match.group(1).strip() if title_match else hero_display

        # 2. Extract FAQ Answer (Contains top counters + win rate advantage percentages)
        faq_match = re.search(
            r'\"name\":\"Which heroes counter [^\"]+\",\"acceptedAnswer\":\{\"@type\":\"Answer\",\"text\":\"([^\"]+)\"',
            html
        )
        faq_text = faq_match.group(1) if faq_match else ""

        # Example FAQ text:
        # "The strongest counters to Granger right now are Fanny (+3.6% win rate advantage), Hilda (+2.8% win rate advantage), Mathilda (+1.3% win rate advantage)..."
        counters_list: List[Dict[str, str]] = []
        if faq_text:
            matches = re.findall(r'([A-Za-z0-9\'\.\s\-]+?)\s*\(([\+\-][0-9\.]+%)\s*win rate advantage\)', faq_text)
            for name, adv in matches:
                clean_name = re.sub(r'^.*?right now are\s+', '', name, flags=re.IGNORECASE).strip()
                clean_name = re.sub(r'^[,\.\s]+', '', clean_name).strip()
                if clean_name:
                    counters_list.append({"name": clean_name, "advantage": adv.strip()})

        # 3. Extract items counters
        items_match = re.search(
            r'\"acceptedAnswer\":\{\"@type\":\"Answer\",\"text\":\"Against [^,]+, build ([^\.]+)\.',
            html
        )
        item_counters = items_match.group(1).strip() if items_match else ""

        # 4. Extract structured initialCounters array
        initial_counters: List[Dict[str, Any]] = []
        idx = html.find("initialCounters")
        if idx != -1:
            m_arr = re.search(r'initialCounters\\\":(\[.*?\])(?:,\s*\\\"|\}\])', html)
            if not m_arr:
                m_arr = re.search(r'\"initialCounters\":(\[.*?\])(?:,\s*\"|\}\])', html)
            if m_arr:
                try:
                    raw_arr = m_arr.group(1).replace('\\"', '"')
                    initial_counters = json.loads(raw_arr)
                except Exception:
                    pass

        # Identify Best Pick
        best_pick = None
        best_advantage = None

        if counters_list:
            best_pick = counters_list[0]["name"]
            best_advantage = counters_list[0]["advantage"]
        elif initial_counters:
            best_pick = initial_counters[0].get("heroName")
            wr = initial_counters[0].get("winRate")
            if wr:
                best_advantage = f"{wr}% win rate"

        if not best_pick:
            return None

        return {
            "hero_name": canonical_hero,
            "slug": slug,
            "url": target_url,
            "best_pick": best_pick,
            "best_advantage": best_advantage,
            "counters": counters_list,
            "initial_counters": initial_counters,
            "item_counters": item_counters,
            "faq_text": faq_text
        }

    @classmethod
    def format_counter_message(cls, data: Dict[str, Any]) -> str:
        """
        Formats telegram message matching the exact smart assistant visual style.
        Includes mlbb.io link at the bottom so Telegram renders the rich banner preview.
        """
        hero_name = data["hero_name"]
        best_pick = data["best_pick"]
        url = data["url"]

        # Additional top counters bullet points if available
        counters = data.get("counters", [])
        extra_lines = []
        if len(counters) > 1:
            for idx, c in enumerate(counters[:3], 1):
                adv_str = f" ({c['advantage']})" if c.get("advantage") else ""
                extra_lines.append(f"• <b>{c['name']}</b>{adv_str}")

        items = data.get("item_counters")
        items_block = f"\n🛡️ <b>Tavsiya etilgan itemlar:</b> <i>{items}</i>\n" if items else ""

        extra_section = ""
        if extra_lines:
            extra_section = "🔥 <b>Top Counterlar:</b>\n" + "\n".join(extra_lines) + "\n"

        lines = [
            "<b>mlbb.io</b>                                      <code>Smart Assistant</code>",
            f"🛡️ <b>Best Pick Against {hero_name}</b> 🛡️",
            "",
            f"<b>{best_pick}</b>",
            "",
        ]

        if extra_section:
            lines.append(extra_section)
        if items_block:
            lines.append(items_block)

        lines.extend([
            "More counters, matchup reasons, and full details are available on MLBB.io.",
            url
        ])

        return "\n".join(lines)
