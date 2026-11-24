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
from app.ai.translator import UzbekTranslator, RussianTranslator

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
            "VAZIFA: Taqdim etilgan yangilikni tahlil qilib, BITTA postda IKKI TILDA: O'ZBEK VA RUS (Bilingual) tillarida jozibali, professional va ixcham post yaratish.\n\n"
            "QAT'IY TALABLAR:\n"
            "1. IKKI TILDA (O'zbek va Rus): Har bir xabar bitta post ichida o'zbekcha (O‘zbekcha) va ruscha (Русский) bo'limlaridan iborat bo'ladi.\n"
            "   - O'zbekcha qismi: 100% ravon va tabiiy o'zbek tilida, MLBB atamalari bilan.\n"
            "   - Ruscha qismi: 100% грамотный, живой русский язык для MLBB комьюнити.\n"
            "2. IXCHAMLIK (Conciseness): Har bir tildagi tavsif 2-3 ta asosiy gapdan iborat bo'lsin. Ortiqcha gaplar va takrorlanishlar bo'lmasin.\n"
            "3. MLBB COMMUNITY TERMINOLOGIYASI:\n"
            "   - UZ: kuchaytirildi (buff), zaiflashtirildi (nerf), moslashtirildi (adj), qayta tiklanish vaqti (cd), zarar (dmg), olmoslar (dm).\n"
            "   - RU: усилен (бафф), ослаблен (нерф), скорректирован, перезарядка (кд), урон, алмазы.\n"
            "4. NO SOURCE = NO CLAIM: Manbada mavjud bo'lmagan hisoblar, o'yinchi ismlari, narxlar yoki sanalarni aslo o'ylab topma. Manbada bo'lmasa, uni ko'rsatma yoki 'Noma'lum' deb belgilash.\n"
            "5. QAYTARILADIGAN JSON FORMATI (Faqat toza JSON qaytar):\n"
            "{\n"
            '  "category": "NEWS" | "PATCH" | "HERO" | "SKIN" | "EVENT" | "MPL_ID" | "MPL_PH" | "MPL_MY" | "ESPORTS" | "TOURNAMENT" | "OTHER",\n'
            '  "title_uz": "O\'zbek tilidagi sarlavha",\n'
            '  "title_ru": "Заголовок на русском языке",\n'
            '  "summary_uz": "Yangilikning o\'zbek tilidagi 2-3 gaplik qisqa va tushunarli tavsifi",\n'
            '  "summary_ru": "Краткое описание новости на русском языке (2-3 предложения)",\n'
            '  "key_points_uz": ["O\'zbek tilidagi 1-muhim nuqta", "2-muhim nuqta"],\n'
            '  "key_points_ru": ["Ключевой пункт 1 на русском", "Ключевой пункт 2"],\n'
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

        # Normalize bilingual titles & summaries
        title_uz = parsed.get("title_uz") or parsed.get("title") or UzbekTranslator.translate_sentence(item.title)
        title_ru = parsed.get("title_ru") or RussianTranslator.translate_sentence(item.title)
        summary_uz = parsed.get("summary_uz") or ""
        summary_ru = parsed.get("summary_ru") or RussianTranslator.translate_sentence(summary_uz)
        points_uz = parsed.get("key_points_uz") or parsed.get("key_points", [])
        points_ru = parsed.get("key_points_ru") or [RussianTranslator.translate_sentence(p) for p in points_uz]

        parsed["title_uz"] = title_uz
        parsed["title_ru"] = title_ru
        parsed["summary_uz"] = summary_uz
        parsed["summary_ru"] = summary_ru
        parsed["key_points_uz"] = points_uz
        parsed["key_points_ru"] = points_ru

        # Build fully Bilingual (UZ + RU) formatted post
        formatted_post = self._build_post(category, parsed, verified, item)

        return AIPostOutput(
            category=category,
            title=title_uz,
            title_uz=title_uz,
            title_ru=title_ru,
            summary_uz=summary_uz,
            summary_ru=summary_ru,
            formatted_post=formatted_post,
            confidence=confidence,
            image_url=item.image_url,
            source_url=item.source_url,
            key_points=points_uz,
            key_points_uz=points_uz,
            key_points_ru=points_ru,
            needs_review=(confidence < settings.MIN_CONFIDENCE_SCORE or item.reliability_score < settings.MIN_RELIABILITY_SCORE)
        )

    def _analyze_deterministic(self, item: RawCollectedItem) -> AIPostOutput:
        """
        High quality rule-based analyzer when no Gemini API key is present.
        Ensures 100% natural Bilingual (Uzbek + Russian) translation.
        """
        category = item.category_hint or self._classify(item.title, item.raw_content)
        title_uz = UzbekTranslator.translate_sentence(item.title)
        title_ru = RussianTranslator.translate_sentence(item.title)
        summary, bullets = Summarizer.extract_summary_and_bullets(item.raw_content)

        # Localize into Uzbek & Russian
        summary_uz = UzbekTranslator.translate_sentence(summary)
        summary_ru = RussianTranslator.translate_sentence(summary)
        cleaned_bullets_uz = [UzbekTranslator.translate_sentence(b) for b in bullets]
        cleaned_bullets_ru = [RussianTranslator.translate_sentence(b) for b in bullets]

        extracted = dict(item.metadata)
        verified = verify_no_source_no_claim(item.raw_content, extracted)

        # If PATCH, extract structured hero changes automatically
        if category == CategoryEnum.PATCH and not item.metadata.get("patch_recap_data"):
            from app.utils.hero_matcher import extract_heroes_from_text
            item.metadata["patch_recap_data"] = extract_heroes_from_text(item.raw_content, item.title)

        parsed_mock = {
            "title": title_uz,
            "title_uz": title_uz,
            "title_ru": title_ru,
            "summary_uz": summary_uz,
            "summary_ru": summary_ru,
            "key_points": cleaned_bullets_uz,
            "key_points_uz": cleaned_bullets_uz,
            "key_points_ru": cleaned_bullets_ru
        }

        formatted = self._build_post(category, parsed_mock, verified, item)

        confidence = 0.95 if item.reliability_score >= 85 else 0.75

        return AIPostOutput(
            category=category,
            title=title_uz,
            title_uz=title_uz,
            title_ru=title_ru,
            summary_uz=summary_uz,
            summary_ru=summary_ru,
            formatted_post=formatted,
            confidence=confidence,
            image_url=item.image_url,
            source_url=item.source_url,
            key_points=cleaned_bullets_uz,
            key_points_uz=cleaned_bullets_uz,
            key_points_ru=cleaned_bullets_ru,
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
        title_uz = parsed.get("title_uz") or UzbekTranslator.translate_sentence(parsed.get("title", item.title))
        title_ru = parsed.get("title_ru") or RussianTranslator.translate_sentence(parsed.get("title", item.title))
        summary_uz = parsed.get("summary_uz") or UzbekTranslator.translate_sentence(parsed.get("summary", ""))
        summary_ru = parsed.get("summary_ru") or RussianTranslator.translate_sentence(summary_uz)
        points_uz = parsed.get("key_points_uz") or [UzbekTranslator.translate_sentence(p) for p in parsed.get("key_points", [])]
        points_ru = parsed.get("key_points_ru") or [RussianTranslator.translate_sentence(p) for p in points_uz]

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
            if not summary_uz or len(summary_uz) < 15:
                summary_uz = (
                    f"Mobile Legends: Bang Bang da {version} versiyasi e'lon qilindi! "
                    "Ushbu yangilanishda qahramonlar ko‘nikmalari muvozanatlashtirildi, qator qahramonlar kuchaytirildi va zaiflashtirildi."
                )
                summary_ru = (
                    f"В Mobile Legends: Bang Bang вышло обновление {version}! "
                    "В этом патче скорректирован баланс навыков героев, ряд персонажей получили усиления и ослабления."
                )

            return PostFormatter.format_patch(
                version=version,
                buffs=buffs,
                nerfs=nerfs,
                adjustments=adjustments,
                source_url=item.source_url,
                summary=summary_uz,
                summary_ru=summary_ru,
                revamps=revamps
            )

        elif category == CategoryEnum.SKIN:
            hero = verified.get("hero") or "Noma'lum"
            skin_name = verified.get("skin_name") or title_uz
            raw_price = verified.get("price") or "Noma'lum (Tadbir orqali)"
            price = UzbekTranslator.translate_sentence(raw_price)
            raw_date = verified.get("date") or "Tez kunda"
            date_val = UzbekTranslator.translate_sentence(raw_date)

            return PostFormatter.format_skin(
                hero=hero,
                skin_name=skin_name,
                price=price,
                release_date=date_val,
                description=summary_uz,
                source_url=item.source_url,
                description_ru=summary_ru
            )

        elif category == CategoryEnum.HERO:
            hero_name = verified.get("hero") or item.metadata.get("hero") or title_uz
            role = verified.get("role") or item.metadata.get("role") or "Qahramon"
            role_uz = UzbekTranslator.translate_sentence(role)
            return PostFormatter.format_hero(
                hero_name=hero_name,
                role=role_uz,
                description=summary_uz,
                skills=points_uz,
                source_url=item.source_url,
                description_ru=summary_ru,
                skills_ru=points_ru
            )

        elif category == CategoryEnum.EVENT:
            duration = verified.get("duration") or item.metadata.get("date") or "Hozirda faol"
            duration_uz = UzbekTranslator.translate_sentence(duration)
            return PostFormatter.format_event(
                title=title_uz,
                description=summary_uz,
                rewards=points_uz,
                duration=duration_uz,
                source_url=item.source_url,
                title_ru=title_ru,
                description_ru=summary_ru,
                rewards_ru=points_ru
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
            return PostFormatter.format_news(
                title=title_uz,
                summary=summary_uz,
                key_points=points_uz,
                source_url=item.source_url,
                title_ru=title_ru,
                summary_ru=summary_ru,
                key_points_ru=points_ru
            )

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
            return PostFormatter.format_news(
                title=title_uz,
                summary=summary_uz,
                key_points=points_uz,
                source_url=item.source_url,
                title_ru=title_ru,
                summary_ru=summary_ru,
                key_points_ru=points_ru
            )

        elif category == CategoryEnum.MPL_MY:
            score_a = verified.get("score_a") if verified.get("score_a") is not None else item.metadata.get("score_a")
            score_b = verified.get("score_b") if verified.get("score_b") is not None else item.metadata.get("score_b")
            is_finished = (
                verified.get("status") == "finished"
                or item.metadata.get("status") == "finished"
                or (score_a is not None and score_b is not None)
            )
            if is_finished and score_a is not None and score_b is not None:
                return PostFormatter.format_mpl_my_result(
                    team_a=verified.get("team_a") or item.metadata.get("team_a", "Team A"),
                    score_a=score_a,
                    score_b=score_b,
                    team_b=verified.get("team_b") or item.metadata.get("team_b", "Team B"),
                    date_str=verified.get("date") or item.metadata.get("date", "Bugun"),
                    week=UzbekTranslator.translate_sentence(verified.get("week") or item.metadata.get("week") or ""),
                    mvp=verified.get("mvp") or item.metadata.get("mvp"),
                    source_url=item.source_url
                )
            return PostFormatter.format_news(
                title=title_uz,
                summary=summary_uz,
                key_points=points_uz,
                source_url=item.source_url,
                title_ru=title_ru,
                summary_ru=summary_ru,
                key_points_ru=points_ru
            )

        elif category in [CategoryEnum.ESPORTS, CategoryEnum.TOURNAMENT]:
            return PostFormatter.format_esports(
                title=title_uz,
                summary=summary_uz,
                tournament=verified.get("tournament"),
                source_url=item.source_url,
                title_ru=title_ru,
                summary_ru=summary_ru
            )

        # Default NEWS
        return PostFormatter.format_news(
            title=title_uz,
            summary=summary_uz,
            key_points=points_uz,
            source_url=item.source_url,
            title_ru=title_ru,
            summary_ru=summary_ru,
            key_points_ru=points_ru
        )

    TEAM_POWER_RATINGS: Dict[str, int] = {
        # MPL ID
        "ONIC ID": 95,
        "RRQ HOSHI": 91,
        "TEAM LIQUID ID": 89,
        "BIGETRON ALPHA": 88,
        "GEEK FAM": 82,
        "ALTER EGO": 80,
        "EVOS GLORY": 79,
        "DEWA UNITED": 75,
        "REBELLION ESPORTS": 72,
        # MPL PH
        "AP.BREN": 96,
        "ONIC PH": 94,
        "TEAM LIQUID PH": 91,
        "TEAM FALCONS": 90,
        "AURORA GAMING": 86,
        "SMART OMEGA": 82,
        "BLACKLIST INT.": 80,
        "TWISTED MINDS": 78,
        "TNC PRO TEAM": 75,
        # MPL MY
        "SELANGOR RED GIANTS": 95,
        "TEAM VAMOS": 91,
        "HOMEBOIS": 88,
        "TODAK": 86,
        "MONSTER VICIOUS": 83,
        "TEAM HAQ": 82,
        "JP NINERS": 80,
        "TEAM REY": 78,
        "CG ESPORTS": 77,
        "AERO ESPORTS": 76,
        "UNTITLED ESPORTS": 75,
        "GAMESMY KELANTAN": 74,
    }

    async def predict_match(
        self,
        league: str,
        team_a: str,
        team_b: str,
        season: str = "Season 14",
        week: str = "1",
        series: str = "BO3"
    ) -> Dict[str, Any]:
        """
        Generates AI-powered match prediction, win probabilities, and PREDICTED SCORE (Taxminiy hisob)
        for upcoming matches before they take place (bilingual commentary).
        """
        if self.client:
            try:
                system_prompt = (
                    "Sen Mobile Legends: Bang Bang (MLBB) bo'yicha professional tahlilchisan.\n"
                    "VAZIFA: Bo'lib o'tadigan o'yin uchun AI TAXMINIY HISOB (Prediction), g'alaba ehtimoli va BITTA post uchun o'zbekcha hamda ruscha qisqa sharh tayyorla.\n"
                    "QAT'IY QOIDALAR:\n"
                    "1. BO3 seriyasi uchun taxminiy hisob faqat 2-0, 2-1, 1-2 yoki 0-2 bo'lishi shart.\n"
                    "2. G'alaba ehtimolini foizda ko'rsat (prob_a + prob_b = 100).\n"
                    "3. commentary_uz: 1-2 ta qisqa va qiziqarli o'zbekcha jumla (draft, o'yin sur'ati, jamoaviy harakatlar haqida).\n"
                    "4. commentary_ru: 1-2 кратких предложения на русском языке о предстоящей игре.\n"
                    "5. Faqat quyidagi JSON formatida javob ber:\n"
                    "{\n"
                    '  "predicted_score_a": 2,\n'
                    '  "predicted_score_b": 1,\n'
                    '  "prob_a": 60,\n'
                    '  "prob_b": 40,\n'
                    '  "commentary_uz": "...",\n'
                    '  "commentary_ru": "..."\n'
                    "}"
                )
                user_prompt = f"Musobaqa: {league} ({season}, {week})\nJamoalar: {team_a} vs {team_b} [{series}]"
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=220
                )
                raw_text = response.choices[0].message.content.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw_text)
                sa = int(parsed.get("predicted_score_a", 2))
                sb = int(parsed.get("predicted_score_b", 1))
                pa = int(parsed.get("prob_a", 55))
                pb = int(parsed.get("prob_b", 45))
                comm_uz = str(parsed.get("commentary_uz", "")).strip()
                comm_ru = str(parsed.get("commentary_ru", "")).strip()
                if not comm_uz:
                    fav = team_a if sa > sb else team_b
                    comm_uz = f"{fav} ushbu bahsda jamoaviy o'yin va draft ustunligi evaziga g'alaba qozonishi kutilmoqda."
                if not comm_ru:
                    comm_ru = RussianTranslator.translate_sentence(comm_uz)

                return {
                    "predicted_score_a": sa,
                    "predicted_score_b": sb,
                    "prob_a": pa,
                    "prob_b": pb,
                    "commentary_uz": comm_uz,
                    "commentary_ru": comm_ru
                }
            except Exception as e:
                logger.warning(f"AI match prediction via LLM failed, using deterministic rating model: {e}")

        # Deterministic fallback model
        clean_a = team_a.upper().strip()
        clean_b = team_b.upper().strip()
        r_a = self.TEAM_POWER_RATINGS.get(clean_a, 80)
        r_b = self.TEAM_POWER_RATINGS.get(clean_b, 80)
        diff = r_a - r_b

        if diff >= 12:
            sa, sb, pa, pb = 2, 0, 72, 28
        elif diff >= 4:
            sa, sb, pa, pb = 2, 1, 58, 42
        elif -3 <= diff <= 3:
            sa, sb, pa, pb = 2, 1, 53, 47
        elif diff <= -12:
            sa, sb, pa, pb = 0, 2, 28, 72
        else:
            sa, sb, pa, pb = 1, 2, 42, 58

        fav = team_a if sa > sb else team_b
        und = team_b if sa > sb else team_a

        if ("ONIC" in clean_a or "ONIC" in clean_b) and ("RRQ" in clean_a or "RRQ" in clean_b):
            comm_uz = f"Klassik Royal Derby! Har ikki gigant yuqori formada, biroq {fav}ning so'nggi patchdagi barqarorligi sababli 2-1 hisobida g'alaba qozonishi kutilmoqda."
            comm_ru = f"Классическое Royal Derby! Оба гранда в отличной форме, но за счет стабильности {fav} ожидается их победа со счетом 2-1."
        elif abs(diff) <= 3:
            comm_uz = f"Teng kuchlilar to'qnashuvi! {und} kamida bitta xaritani ilib ketishi aniq, biroq hal qiluvchi xaritada {fav} tajriba evaziga ustun kelishi taxmin qilinmoqda."
            comm_ru = f"Битва равных соперников! {und} наверняка заберет одну карту, но на решающей карте {fav} должен взять верх на опыте."
        elif (sa == 2 and sb == 0) or (sa == 0 and sb == 2):
            comm_uz = f"{fav} hozirgi metada yuqori bosim o'tkazmoqda va {und}ga imkoniyat qoldirmasdan 2-0 hisobida g'alaba qozonishi ehtimoli yuqori."
            comm_ru = f"{fav} доминирует в текущей мете и имеет высокие шансы закрыть серию со счетом 2-0."
        else:
            comm_uz = f"Shiddatli jang kutilmoqda! {fav} draft afzalligi va yaxshiroq rotatsiya evaziga 2-1 hisobida g'alaba qozonishi kutilmoqda."
            comm_ru = f"Ожидается напряженная борьба! {fav} имеет преимущество по драфту и ротациям для победы 2-1."

        return {
            "predicted_score_a": sa,
            "predicted_score_b": sb,
            "prob_a": pa,
            "prob_b": pb,
            "commentary_uz": comm_uz,
            "commentary_ru": comm_ru
        }
