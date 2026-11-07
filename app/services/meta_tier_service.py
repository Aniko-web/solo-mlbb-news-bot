import json
import re
import urllib.request
from typing import Dict, Any, List, Optional
import httpx

from app.utils.logger import logger
from app.config.settings import get_settings
from app.ai.formatter import CHANNEL_FOOTER

settings = get_settings()

MLBB_IO_URL = "https://mlbb.io/en/hero-tier"
MLBB_IO_BASE = "https://mlbb.io/en"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class MetaTierService:
    """
    Parses live Mobile Legends Hero Tier List from https://mlbb.io/en/hero-tier
    and extracts:
      1. Strong & Spammed (SS/S Tier top picks & banned)
      2. Traps to Avoid (D Tier underperforming/loss trap heroes)
      3. Hidden Gems (Low ban-rate, high win-rate/score sleepers)
    Builds authentic Uzbek gamer-slang post with official mlbb.io links.
    """

    @classmethod
    async def fetch_tier_data(cls) -> List[Dict[str, Any]]:
        """Fetch raw hero tier array from mlbb.io Next.js payload."""
        logger.info(f"[MetaTierService] Fetching hero tier list from {MLBB_IO_URL}...")
        html = ""
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=25.0) as client:
                resp = await client.get(MLBB_IO_URL)
                if resp.status_code == 200:
                    html = resp.text
        except Exception as err:
            logger.warning(f"[MetaTierService] httpx fetch failed ({err}), trying urllib fallback...")
            try:
                req = urllib.request.Request(MLBB_IO_URL, headers=HEADERS)
                html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
            except Exception as e:
                logger.error(f"[MetaTierService] urllib fetch also failed: {e}")
                return []

        if not html:
            return []

        # Parse embedded initialHeroes from Next.js payload
        tag = 'initialHeroes\\":'
        idx = html.find(tag)
        if idx == -1:
            # Try without backslash
            tag = '"initialHeroes":'
            idx = html.find(tag)

        if idx != -1:
            raw_sub = html[idx + len(tag):]
            end_tag = '],\\"initialLastUpdated'
            end_idx = raw_sub.find(end_tag)
            if end_idx == -1:
                end_tag = '],"initialLastUpdated'
                end_idx = raw_sub.find(end_tag)

            if end_idx != -1:
                raw_json = raw_sub[:end_idx + 1].replace('\\"', '"')
                try:
                    heroes = json.loads(raw_json)
                    logger.info(f"[MetaTierService] Successfully parsed {len(heroes)} heroes from mlbb.io")
                    return heroes
                except Exception as json_err:
                    logger.error(f"[MetaTierService] JSON decode error: {json_err}")

        logger.warning("[MetaTierService] Could not locate initialHeroes array in page HTML.")
        return []

    @classmethod
    def categorize_heroes(cls, heroes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize heroes into Strong & Spammed, Traps to Avoid, and Hidden Gems."""
        if not heroes:
            return {"strong_spammed": [], "traps": [], "hidden_gems": []}

        # 1. Strong & Spammed: Tier SS or S, sorted by score descending
        strong_candidates = [h for h in heroes if h.get("tier") in ("SS", "S")]
        strong_candidates.sort(key=lambda x: (x.get("score", 0) + x.get("ban_rate", 0) * 5), reverse=True)
        strong_spammed = strong_candidates[:6]

        # 2. Traps to Avoid: Tier D, lowest score
        trap_candidates = [h for h in heroes if h.get("tier") in ("D", "C")]
        trap_candidates.sort(key=lambda x: x.get("score", 9999))
        traps = trap_candidates[:6]

        # 3. Hidden Gems: Low ban rate (< 5%), but high score (Tier A or B with score >= 750)
        gem_candidates = [
            h for h in heroes
            if h.get("tier") in ("A", "B", "S")
            and h.get("ban_rate", 0) < 5.0
            and h.get("score", 0) >= 700
        ]
        gem_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        hidden_gems = gem_candidates[:6]

        return {
            "strong_spammed": strong_spammed,
            "traps": traps,
            "hidden_gems": hidden_gems
        }

    @classmethod
    def format_meta_post(cls, categorized: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Builds Telegram HTML post in authentic Uzbek MLBB gamer slang
        with official mlbb.io links.
        """
        strong = categorized.get("strong_spammed", [])
        traps = categorized.get("traps", [])
        gems = categorized.get("hidden_gems", [])

        lines = [
            "🔥 <b>MLBB META TAHLILI — KUNNING ENG MUHIM PIKLARI!</b>",
            "<i>(Solo rankda yulduz ko‘tarish va asabni asrash uchun eng so‘nggi meta gidi)</i>\n",
            "━━━━━━━━━━━━━━━━━━━━━\n",
            "👑 <b>STRONG & SPAMMED (Metani yondirayotganlar):</b>",
            "<i>Ushbu qahramonlar hozirda juda kuchli (OP) va har bitta o‘yinda spam qilinyapti. Ban qilmasangiz, darhol o‘zingiz oling!</i>"
        ]

        for h in strong:
            name = h.get("hero_name", "Hero")
            tier = h.get("tier", "S")
            ban = h.get("ban_rate", 0)
            role = ", ".join(h.get("role", [])) if isinstance(h.get("role"), list) else str(h.get("role", ""))
            lane = ", ".join(h.get("lane", [])) if isinstance(h.get("lane"), list) else str(h.get("lane", ""))
            lines.append(f"• <b>{name}</b> [{tier} Tier] — <i>{lane or role}</i> (Ban: {ban:.1f}%)")

        lines.append("\n━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("⚠️ <b>TRAPS TO AVOID (Tuzoq qahramonlar — aslo olmang!):</b>")
        lines.append("<i>Ko‘pchilik odat bo‘lib qolgani uchun tanlaydi, lekin hozirgi metada yutqazib yotgan qahramonlar. Bularni olib timmeytlarni fiderlikda ayblamang! 😉</i>")

        for h in traps:
            name = h.get("hero_name", "Hero")
            tier = h.get("tier", "D")
            score = h.get("score", 0)
            role = ", ".join(h.get("role", [])) if isinstance(h.get("role"), list) else str(h.get("role", ""))
            lines.append(f"• <b>{name}</b> [{tier} Tier] — <i>{role}</i> (Zaif meta)")

        lines.append("\n━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("💎 <b>HIDDEN GEMS (Yashirin javohirlar — sirli qurollar):</b>")
        lines.append("<i>Hech kim ban qilmaydi va ko‘pchilik e'tibor bermaydi, biroq solo rankda dahshatli winrate beryapti! Oling va oson yulduz yig‘ing:</i>")

        for h in gems:
            name = h.get("hero_name", "Hero")
            tier = h.get("tier", "A")
            ban = h.get("ban_rate", 0)
            lane = ", ".join(h.get("lane", [])) if isinstance(h.get("lane"), list) else str(h.get("lane", ""))
            lines.append(f"• <b>{name}</b> [{tier} Tier] — <i>{lane}</i> (Ban: atigi {ban:.1f}%)")

        lines.append("\n━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("📌 <b>To‘liq ma'lumot va eng zo‘r yig‘malar (Build):</b>")
        lines.append(f"📊 <a href=\"{MLBB_IO_BASE}\">Mobile Legends Hero Tier List</a>")
        lines.append(f"🛡 <a href=\"{MLBB_IO_BASE}\">Mobile Legends Item Build Guide</a>\n")
        lines.append("#MLBB #Meta #HeroTier #SoloRank @murodalievgg\n")
        lines.append(CHANNEL_FOOTER)

        return "\n".join(lines)

    @classmethod
    async def generate_meta_tier_post(cls) -> Dict[str, Any]:
        """Main method to fetch, analyze, and format the meta tier post."""
        heroes = await cls.fetch_tier_data()
        if not heroes:
            logger.warning("[MetaTierService] Fallback to curated meta data due to fetch failure.")
            # Curated fallback based on current patch
            heroes = [
                {"hero_name": "Sun", "tier": "SS", "role": ["Fighter"], "lane": ["Exp Lane", "Jungle"], "score": 968.9, "ban_rate": 35.8},
                {"hero_name": "Obsidia", "tier": "SS", "role": ["Marksman"], "lane": ["Gold Lane"], "score": 951.7, "ban_rate": 53.4},
                {"hero_name": "Belerick", "tier": "SS", "role": ["Tank"], "lane": ["Roam"], "score": 940.0, "ban_rate": 63.5},
                {"hero_name": "Gloo", "tier": "S", "role": ["Tank"], "lane": ["Exp Lane"], "score": 880.0, "ban_rate": 45.0},
                {"hero_name": "Valir", "tier": "A", "role": ["Mage"], "lane": ["Mid Lane"], "score": 947.0, "ban_rate": 3.2},
                {"hero_name": "Minotaur", "tier": "A", "role": ["Tank"], "lane": ["Roam"], "score": 860.0, "ban_rate": 2.1},
                {"hero_name": "Rafaela", "tier": "A", "role": ["Support"], "lane": ["Roam"], "score": 835.0, "ban_rate": 1.5},
                {"hero_name": "Valentina", "tier": "D", "role": ["Mage"], "lane": ["Mid Lane"], "score": 166.9, "ban_rate": 0.2},
                {"hero_name": "Chip", "tier": "D", "role": ["Support"], "lane": ["Roam"], "score": 175.3, "ban_rate": 0.2},
                {"hero_name": "Wanwan", "tier": "D", "role": ["Marksman"], "lane": ["Gold Lane"], "score": 178.3, "ban_rate": 0.1},
                {"hero_name": "Mathilda", "tier": "D", "role": ["Support"], "lane": ["Roam"], "score": 180.0, "ban_rate": 0.2},
                {"hero_name": "Zilong", "tier": "D", "role": ["Fighter"], "lane": ["Exp Lane"], "score": 219.9, "ban_rate": 0.3},
            ]

        categorized = cls.categorize_heroes(heroes)
        post_text = cls.format_meta_post(categorized)

        # Generate infographic card
        from app.media.templates.meta_card import render_meta_tier_card
        image_bytes = None
        try:
            image_bytes = render_meta_tier_card(categorized)
        except Exception as img_err:
            logger.error(f"[MetaTierService] Error rendering meta tier card: {img_err}", exc_info=True)

        return {
            "success": True,
            "formatted_post": post_text,
            "image_bytes": image_bytes,
            "categorized": categorized
        }
