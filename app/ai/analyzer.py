import json
import re
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI

from app.config.settings import get_settings
from app.utils.logger import logger
from app.utils.validators import (
    RawCollectedItem,
    AIPostOutput,
    CategoryEnum,
    verify_no_source_no_claim
)
from app.ai.formatter import PostFormatter
from app.ai.summarizer import Summarizer
from app.ai.translator import UzbekTranslator

settings = get_settings()


class AIAnalyzer:
    """
    Analyzes raw MLBB news, applies Gemini/OpenAI-based classification,
    100% Uzbek translation and summarization, and strict hallucination protection ("NO SOURCE = NO CLAIM").
    """

    def __init__(self):
        self.api_key = settings.active_ai_key
        self.base_url = settings.AI_BASE_URL
        self.model = settings.AI_MODEL
        self.client: Optional[AsyncOpenAI] = None

        if self.api_key and self.api_key.strip():
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=15.0,
                max_retries=1
            )
            logger.info(f"AI Analyzer initialized with model '{self.model}' (Endpoint: {self.base_url})")
        else:
            logger.info("AI Analyzer running in deterministic rule-based Uzbek translation mode.")

    async def analyze(self, item: RawCollectedItem) -> AIPostOutput:
        """
        Analyze a raw collected item and generate an AIPostOutput with 100% Uzbek text.
        Uses Google Gemini / OpenAI if configured; otherwise gracefully falls back to deterministic NLP analyzer.
        """
        if self.client:
            try:
                return await self._analyze_with_llm(item)
            except Exception as e:
                logger.warning(f"LLM Gemini analysis failed, falling back to deterministic Uzbek analyzer: {e}")

        return self._analyze_deterministic(item)

    async def _analyze_with_llm(self, item: RawCollectedItem) -> AIPostOutput:
        system_prompt = (
            "Sen Mobile Legends: Bang Bang (MLBB) bo'yicha Telegram kanali uchun professional AI muharririsan.\n"
            "VAZIFA: Taqdim etilgan yangilikni tahlil qilib, uni 100% O'ZBEK tiliga tarjima qilish va jozibali post yaratish.\n\n"
            "QAT'IY TALABLAR:\n"
            "1. TO'LIQ O'ZBEK TILI: Barcha matnlar (sarlavha, qisqacha tavsif, punktlar, o'zgarishlar) to'liq, ravon va tabiiy O'ZBEK tilida bo'lishi shart! Hech qanday inglizcha gap yoki qoldiq qolmasin.\n"
            "2. MLBB COMMUNITY USLUBI: O'zbek MLBB o'yinchilari tushunadigan atamalardan foydalan:\n"
            "   - buff -> kuchaytirildi\n"
            "   - nerf -> zaiflashtirildi\n"
            "   - adjustment -> moslashtirildi\n"
            "   - cooldown -> qayta tiklanish vaqti\n"
            "   - damage -> zarari\n"
            "   - energy recovery -> energiya tiklanishi\n"
            "   - basic attack -> asosiy hujum\n"
            "   - passive / ultimate -> passiv qobiliyati / ult qobiliyati\n"
            "   - diamonds -> olmoslar\n"
            "3. NO SOURCE = NO CLAIM: Manbada mavjud bo'lmagan hisoblar, o'yinchi ismlari, narxlar yoki sanalarni aslo o'ylab topma. Manbada bo'lmasa, uni ko'rsatma yoki 'Noma'lum' deb belgilash.\n"
            "4. QAYTARILADIGAN JSON FORMATI (Faqat toza JSON qaytar):\n"
            "{\n"
            '  "category": "NEWS" | "PATCH" | "HERO" | "SKIN" | "EVENT" | "MPL_ID" | "MPL_PH" | "ESPORTS" | "TOURNAMENT" | "OTHER",\n'
            '  "title": "O\'zbek tilidagi sarlavha",\n'
            '  "summary_uz": "Yangilikning o\'zbek tilidagi 2-3 gaplik qisqa va tushunarli tavsifi",\n'
            '  "key_points": ["O\'zbek tilidagi 1-muhim nuqta", "2-muhim nuqta"],\n'
            '  "confidence": 0.95,\n'
            '  "extracted_data": {\n'
            '     "hero": "...", "skin_name": "...", "price": "...", "date": "...",\n'
            '     "team_a": "...", "team_b": "...", "score_a": 2, "score_b": 1, "mvp": "..."\n'
            "  }\n"
            "}"
        )

        user_prompt = (
            f"Manba URL: {item.source_url}\n"
            f"Original Sarlavha: {item.title}\n"
            f"Original Matn: {item.raw_content}\n"
            f"Qo'shimcha ma'lumotlar: {json.dumps(item.metadata, ensure_ascii=False)}"
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        raw_json = response.choices[0].message.content or "{}"
        parsed = json.loads(raw_json)

        cat_str = parsed.get("category", "NEWS").upper()
        try:
            category = CategoryEnum(cat_str)
        except ValueError:
            category = CategoryEnum.NEWS

        confidence = float(parsed.get("confidence", 0.9))
        extracted = parsed.get("extracted_data", {})

        # If PATCH, extract structured hero changes automatically
        if category == CategoryEnum.PATCH:
            patch_data = extracted.get("patch_data")
            if not patch_data or not any(patch_data.get(k) for k in ["buffs", "nerfs", "adjustments", "revamps"]):
                from app.utils.hero_matcher import extract_heroes_from_text
                patch_data = extract_heroes_from_text(item.raw_content, item.title)
            item.metadata["patch_recap_data"] = patch_data

        # Verify claims against source
        verified = verify_no_source_no_claim(item.raw_content, extracted)

        # Build fully Uzbek formatted post
        formatted_post = self._build_post(category, parsed, verified, item)

        return AIPostOutput(
            category=category,
            title=parsed.get("title", UzbekTranslator.translate_sentence(item.title)),
            summary_uz=parsed.get("summary_uz", ""),
            formatted_post=formatted_post,
            confidence=confidence,
            image_url=item.image_url,
            source_url=item.source_url,
            key_points=parsed.get("key_points", []),
            needs_review=(confidence < settings.MIN_CONFIDENCE_SCORE or item.reliability_score < settings.MIN_RELIABILITY_SCORE)
        )

    def _analyze_deterministic(self, item: RawCollectedItem) -> AIPostOutput:
        """
        High quality rule-based analyzer when no Gemini API key is present.
        Ensures 100% natural Uzbek translation.
        """
        category = item.category_hint or self._classify(item.title, item.raw_content)
        title_uz = UzbekTranslator.translate_sentence(item.title)
        summary, bullets = Summarizer.extract_summary_and_bullets(item.raw_content)

        # Localize into Uzbek
        summary_uz = UzbekTranslator.translate_sentence(summary)
        cleaned_bullets = [UzbekTranslator.translate_sentence(b) for b in bullets]

        extracted = dict(item.metadata)
        verified = verify_no_source_no_claim(item.raw_content, extracted)

        # If PATCH, extract structured hero changes automatically
        if category == CategoryEnum.PATCH and not item.metadata.get("patch_recap_data"):
            from app.utils.hero_matcher import extract_heroes_from_text
            item.metadata["patch_recap_data"] = extract_heroes_from_text(item.raw_content, item.title)

        parsed_mock = {
            "title": title_uz,
            "summary_uz": summary_uz,
            "key_points": cleaned_bullets
        }

        formatted = self._build_post(category, parsed_mock, verified, item)

        confidence = 0.95 if item.reliability_score >= 85 else 0.75

        return AIPostOutput(
            category=category,
            title=title_uz,
            summary_uz=summary_uz,
            formatted_post=formatted,
            confidence=confidence,
            image_url=item.image_url,
            source_url=item.source_url,
            key_points=cleaned_bullets,
            needs_review=(confidence < settings.MIN_CONFIDENCE_SCORE or item.reliability_score < settings.MIN_RELIABILITY_SCORE)
        )

    def _classify(self, title: str, content: str) -> CategoryEnum:
        text = f"{title} {content}".lower()
        if "mpl id" in text or "indonesia" in text:
            return CategoryEnum.MPL_ID
        if "mpl ph" in text or "philippines" in text:
            return CategoryEnum.MPL_PH
        if any(w in text for w in ["patch notes", "update 1.", "patch 1."]):
            return CategoryEnum.PATCH
        if any(w in text for w in ["skin", "collector", "starlight", "epic skin"]):
            return CategoryEnum.SKIN
        if any(w in text for w in ["new hero", "revamp", "hero spotlight"]):
            return CategoryEnum.HERO
        if any(w in text for w in ["event", "carnival", "draw", "giveaway"]):
            return CategoryEnum.EVENT
        if any(w in text for w in ["esports", "m6", "m-series", "tournament", "championship"]):
            return CategoryEnum.ESPORTS
        return CategoryEnum.NEWS

    def _build_post(
        self,
        category: CategoryEnum,
        parsed: Dict[str, Any],
        verified: Dict[str, Any],
        item: RawCollectedItem
    ) -> str:
        title = UzbekTranslator.translate_sentence(parsed.get("title", item.title))
        summary = UzbekTranslator.translate_sentence(parsed.get("summary_uz", ""))
        points = [UzbekTranslator.translate_sentence(p) for p in parsed.get("key_points", [])]

        if category == CategoryEnum.PATCH:
            # 1. Prefer structured hero data from metadata if available
            recap_data = item.metadata.get("patch_recap_data") or {}

            def get_names(key: str) -> List[str]:
                entries = recap_data.get(key) or []
                res = []
                for e in entries:
                    if isinstance(e, dict):
                        res.append(e.get("name", ""))
                    elif isinstance(e, str):
                        res.append(e)
                return [r for r in res if r]

            buffs = get_names("buffs")
            nerfs = get_names("nerfs")
            adjustments = get_names("adjustments")
            revamps = get_names("revamps")

            # Intelligent automatic hero extraction fallback
            if not (buffs or nerfs or adjustments or revamps):
                from app.utils.hero_matcher import extract_heroes_from_text
                auto_patch = extract_heroes_from_text(item.raw_content, item.title)
                buffs = auto_patch.get("buffs", [])
                nerfs = auto_patch.get("nerfs", [])
                adjustments = auto_patch.get("adjustments", [])
                revamps = auto_patch.get("revamps", [])
                if not recap_data:
                    recap_data = auto_patch
                    item.metadata["patch_recap_data"] = auto_patch

            version = recap_data.get("version") or verified.get("version") or item.metadata.get("version") or "1.9.xx"

            # Ensure summary is concise and informative
            if not summary or len(summary) < 15:
                summary = (
                    f"Mobile Legends: Bang Bang da {version} versiyasi e'lon qilindi! "
                    "Ushbu yangilanishda qahramonlar ko‘nikmalari muvozanatlashtirildi, qator qahramonlar kuchaytirildi va zaiflashtirildi."
                )

            return PostFormatter.format_patch(
                version=version,
                buffs=buffs,
                nerfs=nerfs,
                adjustments=adjustments,
                source_url=item.source_url,
                summary=summary,
                revamps=revamps
            )

        elif category == CategoryEnum.SKIN:
            hero = verified.get("hero") or "Noma'lum"
            skin_name = verified.get("skin_name") or title
            raw_price = verified.get("price") or "Noma'lum (Tadbir orqali)"
            price = UzbekTranslator.translate_sentence(raw_price)
            raw_date = verified.get("date") or "Tez kunda"
            date_val = UzbekTranslator.translate_sentence(raw_date)

            return PostFormatter.format_skin(
                hero=hero,
                skin_name=skin_name,
                price=price,
                release_date=date_val,
                description=summary,
                source_url=item.source_url
            )

        elif category == CategoryEnum.HERO:
            hero_name = verified.get("hero") or item.metadata.get("hero") or title
            role = verified.get("role") or item.metadata.get("role") or "Qahramon"
            role_uz = UzbekTranslator.translate_sentence(role)
            return PostFormatter.format_hero(
                hero_name=hero_name,
                role=role_uz,
                description=summary,
                skills=points,
                source_url=item.source_url
            )

        elif category == CategoryEnum.EVENT:
            duration = verified.get("duration") or item.metadata.get("date") or "Hozirda faol"
            duration_uz = UzbekTranslator.translate_sentence(duration)
            return PostFormatter.format_event(
                title=title,
                description=summary,
                rewards=points,
                duration=duration_uz,
                source_url=item.source_url
            )

        elif category == CategoryEnum.MPL_ID:
            if "matches_schedule" in item.metadata:
                return PostFormatter.format_mpl_id_schedule(
                    date_str=item.metadata.get("date", "Bugun"),
                    matches=item.metadata["matches_schedule"]
                )
            score_a = verified.get("score_a") if verified.get("score_a") is not None else item.metadata.get("score_a")
            score_b = verified.get("score_b") if verified.get("score_b") is not None else item.metadata.get("score_b")
            is_finished = (
                verified.get("status") == "finished"
                or item.metadata.get("status") == "finished"
                or (score_a is not None and score_b is not None)
            )
            if is_finished and score_a is not None and score_b is not None:
                return PostFormatter.format_mpl_id_result(
                    team_a=verified.get("team_a") or item.metadata.get("team_a", "Team A"),
                    score_a=score_a,
                    score_b=score_b,
                    team_b=verified.get("team_b") or item.metadata.get("team_b", "Team B"),
                    date_str=verified.get("date") or item.metadata.get("date", "Bugun"),
                    week=UzbekTranslator.translate_sentence(verified.get("week") or item.metadata.get("week") or ""),
                    mvp=verified.get("mvp") or item.metadata.get("mvp"),
                    source_url=item.source_url
                )
            return PostFormatter.format_news(title, summary, points, item.source_url)

        elif category == CategoryEnum.MPL_PH:
            score_a = verified.get("score_a") if verified.get("score_a") is not None else item.metadata.get("score_a")
            score_b = verified.get("score_b") if verified.get("score_b") is not None else item.metadata.get("score_b")
            is_finished = (
                verified.get("status") == "finished"
                or item.metadata.get("status") == "finished"
                or (score_a is not None and score_b is not None)
            )
            if is_finished and score_a is not None and score_b is not None:
                return PostFormatter.format_mpl_ph_result(
                    team_a=verified.get("team_a") or item.metadata.get("team_a", "Team A"),
                    score_a=score_a,
                    score_b=score_b,
                    team_b=verified.get("team_b") or item.metadata.get("team_b", "Team B"),
                    date_str=verified.get("date") or item.metadata.get("date", "Bugun"),
                    week=UzbekTranslator.translate_sentence(verified.get("week") or item.metadata.get("week") or ""),
                    mvp=verified.get("mvp") or item.metadata.get("mvp"),
                    source_url=item.source_url
                )
            return PostFormatter.format_news(title, summary, points, item.source_url)

        elif category in [CategoryEnum.ESPORTS, CategoryEnum.TOURNAMENT]:
            return PostFormatter.format_esports(
                title=title,
                summary=summary,
                tournament=verified.get("tournament"),
                source_url=item.source_url
            )

        # Default NEWS
        return PostFormatter.format_news(
            title=title,
            summary=summary,
            key_points=points,
            source_url=item.source_url
        )
