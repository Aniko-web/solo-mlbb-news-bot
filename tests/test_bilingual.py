import pytest
from app.ai.formatter import PostFormatter
from app.ai.analyzer import AIAnalyzer
from app.ai.translator import UzbekTranslator, RussianTranslator
from app.services.matchday_service import MatchdayService
from app.services.meta_tier_service import MetaTierService
from app.utils.validators import RawCollectedItem, CategoryEnum


def test_bilingual_translator():
    # Test Uzbek translator
    uz = UzbekTranslator.translate_sentence("New Collector Skin 'Astral' for Lunox released on October 5.")
    assert "Lunox" in uz
    assert "Collector" in uz

    # Test Russian translator
    ru = RussianTranslator.translate_sentence("New Collector Skin 'Astral' for Lunox released on October 5.")
    assert "Lunox" in ru
    assert "Collector" in ru
    assert "Октября" in ru


def test_format_news_bilingual():
    post = PostFormatter.format_news(
        title="Yangi qahramon Land of Dawn ga qo‘shilmoqda",
        summary="Ushbu qahramon tez orada o‘yinda paydo bo‘ladi.",
        key_points=["Juda yuqori zarar", "Yangi mexanika"],
        source_url="https://mobilelegends.com"
    )
    assert "🇺🇿 <b>O‘zbekcha:</b>" in post
    assert "🇷🇺 <b>Русский:</b>" in post
    assert "🔥 <b>MLBB YANGILIGI</b> | <b>НОВОСТИ MLBB</b>" in post
    assert "#MLBB #Yangilik #Новости" in post


def test_format_skin_bilingual():
    post = PostFormatter.format_skin(
        hero="Gusion",
        skin_name="Dimension Scourge",
        price="899 Diamonds",
        release_date="November 28",
        description="Ajoyib yangi afsonaviy skin.",
        source_url="https://mobilelegends.com"
    )
    assert "✨ <b>YANGI SKIN</b> | <b>НОВЫЙ СКИН</b>" in post
    assert "🇺🇿 <b>O‘zbekcha:</b>" in post
    assert "🇷🇺 <b>Русский:</b>" in post
    assert "Gusion" in post
    assert "#MLBB #Skin #Скины" in post


def test_format_patch_bilingual():
    post = PostFormatter.format_patch(
        version="1.9.30",
        buffs=["Fanny", "Ling"],
        nerfs=["Saber"],
        adjustments=["Granger"],
        source_url="https://mobilelegends.com",
        summary="Qahramonlar balansi yangilandi."
    )
    assert "🛠 <b>MLBB PATCH NOTES YANGILANISHI</b> | <b>ОБНОВЛЕНИЕ ПАТЧА</b>" in post
    assert "🇺🇿 <b>O‘zbekcha:</b>" in post
    assert "🇷🇺 <b>Русский:</b>" in post
    assert "1.9.30" in post
    assert "Fanny" in post
    assert "Saber" in post


def test_format_matchday_caption_bilingual():
    matches = [
        {"team_a": "RRQ", "team_b": "ONIC", "time": "15:00", "series": "BO3", "is_motd": True}
    ]
    motd_info = {
        "motd_team_a": "RRQ",
        "motd_team_b": "ONIC",
        "hype_text": "Kunning eng kutilgan to‘qnashuvi!"
    }
    caption = MatchdayService.format_matchday_caption(
        league="MPL ID",
        date_str="2026-11-25",
        matches=matches,
        motd_info=motd_info
    )
    assert "BUGUNGI O‘YINLAR DASTURI | РАСПИСАНИЕ МАТЧЕЙ" in caption
    assert "RRQ vs ONIC" in caption
    assert "KUNNING MARKAZIY BAHSI / МАТЧ ДНЯ" in caption
    assert "🎙 🇺🇿" in caption
    assert "🎙 🇷🇺" in caption


def test_format_meta_post_bilingual():
    categorized = {
        "strong_spammed": [{"hero_name": "Sun", "tier": "SS", "ban_rate": 35.8, "lane": ["Exp Lane"]}],
        "traps": [{"hero_name": "Wanwan", "tier": "D", "role": ["Marksman"]}],
        "hidden_gems": [{"hero_name": "Valir", "tier": "A", "ban_rate": 3.2, "lane": ["Mid Lane"]}]
    }
    post = MetaTierService.format_meta_post(categorized)
    assert "MLBB META TAHLILI | АНАЛИЗ МЕТЫ MLBB" in post
    assert "STRONG & SPAMMED" in post
    assert "TRAPS TO AVOID" in post
    assert "HIDDEN GEMS" in post
    assert "Sun" in post
    assert "Wanwan" in post
    assert "Valir" in post


@pytest.mark.asyncio
async def test_ai_analyzer_produces_bilingual_post():
    analyzer = AIAnalyzer()
    raw = RawCollectedItem(
        source_url="https://mobilelegends.com/news/123",
        title="Major MLBB Esports Update",
        raw_content="Moonton Games has officially announced the M6 World Championship tournament.",
        category_hint=CategoryEnum.NEWS,
        source_name="MLBB Official",
        source_type="OFFICIAL_MLBB",
        reliability_score=100
    )
    output = await analyzer.analyze(raw)
    assert "🇺🇿 <b>O‘zbekcha:</b>" in output.formatted_post
    assert "🇷🇺 <b>Русский:</b>" in output.formatted_post
    assert output.title_uz is not None
    assert output.title_ru is not None
    assert output.summary_uz is not None
    assert output.summary_ru is not None
