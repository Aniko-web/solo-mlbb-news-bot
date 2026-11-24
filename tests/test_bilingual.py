import pytest
from app.services.counter_pick_service import CounterPickService
from app.ai.formatter import PostFormatter
from app.ai.analyzer import AIAnalyzer
from app.utils.validators import RawCollectedItem, CategoryEnum


def test_format_counter_message_bilingual():
    """Ensure Counter-Pick Assistant produces rich bilingual (Uzbek + Russian) analysis in one message."""
    data = {
        "hero_name": "Granger",
        "slug": "granger",
        "url": "https://mlbb.io/en/hero/granger/counter",
        "best_pick": "Fanny",
        "best_advantage": "+3.6% win rate advantage",
        "counters": [
            {"name": "Fanny", "advantage": "+3.6%"},
            {"name": "Hilda", "advantage": "+2.8%"},
            {"name": "Mathilda", "advantage": "+1.3%"}
        ],
        "item_counters": "Blade Armor, Antique Cuirass, Wind of Nature"
    }

    formatted = CounterPickService.format_counter_message(data)

    # 1. Header & Best Pick
    assert "<b>mlbb.io</b>" in formatted
    assert "Smart Assistant" in formatted
    assert "Best Pick Against Granger" in formatted
    assert "Fanny" in formatted
    assert "+3.6%" in formatted

    # 2. Uzbek Section
    assert "🇺🇿 <b>O‘zbekcha:</b>" in formatted
    assert "Granger" in formatted
    assert "Top Counterlar" in formatted
    assert "Tavsiya etilgan itemlar" in formatted
    assert "Blade Armor" in formatted

    # 3. Russian Section
    assert "🇷🇺 <b>Русский:</b>" in formatted
    assert "Лучший выбор против" in formatted
    assert "Топ контр-пики" in formatted
    assert "Рекомендуемые предметы" in formatted
    assert "преимущество" in formatted

    # 4. Official mlbb.io link
    assert "https://mlbb.io/en/hero/granger/counter" in formatted


def test_news_remains_uzbek():
    """Ensure regular news posts remain 100% natural Uzbek without Russian sections."""
    post = PostFormatter.format_news(
        title="Yangi qahramon Land of Dawn ga qo‘shilmoqda",
        summary="Ushbu qahramon tez orada o‘yinda paydo bo‘ladi.",
        key_points=["Juda yuqori zarar", "Yangi mexanika"],
        source_url="https://mobilelegends.com"
    )
    assert "🔥 <b>MLBB YANGILIGI</b>" in post
    assert "#MLBB #Yangilik" in post
    assert "🇺🇿" not in post
    assert "🇷🇺" not in post
    assert "Русский" not in post


def test_patch_remains_uzbek():
    """Ensure patch notes posts remain 100% natural Uzbek without Russian sections."""
    post = PostFormatter.format_patch(
        version="1.9.30",
        buffs=["Fanny", "Ling"],
        nerfs=["Saber"],
        adjustments=["Granger"],
        source_url="https://mobilelegends.com",
        summary="Qahramonlar balansi yangilandi."
    )
    assert "🛠 <b>MLBB PATCH NOTES YANGILANISHI</b>" in post
    assert "1.9.30" in post
    assert "Fanny" in post
    assert "Saber" in post
    assert "🇺🇿" not in post
    assert "🇷🇺" not in post
    assert "Русский" not in post


@pytest.mark.asyncio
async def test_ai_analyzer_news_uzbek():
    """Ensure AI Analyzer generates clean Uzbek news post."""
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
    assert output.category == CategoryEnum.NEWS
    assert "🇺🇿" not in output.formatted_post
    assert "🇷🇺" not in output.formatted_post
