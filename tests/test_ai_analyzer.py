import pytest
from app.ai.analyzer import AIAnalyzer
from app.ai.formatter import PostFormatter
from app.utils.validators import RawCollectedItem, CategoryEnum, SourceReliability


@pytest.mark.asyncio
async def test_analyzer_patch_post():
    analyzer = AIAnalyzer()
    raw = RawCollectedItem(
        source_url="https://m.mobilelegends.com/en/news/patch-notes-1-9-20",
        title="Patch Notes 1.9.20 Update",
        raw_content=(
            "BUFF: Fanny energy recovery increased. "
            "NERF: Ling Tempest of Blades cooldown increased. "
            "ADJUSTMENT: Granger animation smoothed."
        ),
        category_hint=CategoryEnum.PATCH,
        source_name="MLBB Official",
        source_type="OFFICIAL_MLBB",
        reliability_score=100,
        metadata={"version": "1.9.20"}
    )
    result = await analyzer.analyze(raw)
    assert result.category == CategoryEnum.PATCH
    assert "PATCH NOTES" in result.formatted_post
    assert "1.9.20" in result.formatted_post
    assert "BUFF" in result.formatted_post
    assert "NERF" in result.formatted_post
    assert "#MLBB #Patch" in result.formatted_post


@pytest.mark.asyncio
async def test_analyzer_skin_post():
    analyzer = AIAnalyzer()
    raw = RawCollectedItem(
        source_url="https://m.mobilelegends.com/en/news/lunox-skin",
        title="New Collector Skin: Lunox 'Astral Echo'",
        raw_content="New Collector Skin 'Astral Echo' for Lunox released on October 5 for 4000 Diamonds.",
        category_hint=CategoryEnum.SKIN,
        source_name="MLBB Official",
        source_type="OFFICIAL_MLBB",
        reliability_score=100,
        metadata={"hero": "Lunox", "skin_name": "Astral Echo", "price": "4000 Diamonds", "date": "October 5, 2026"}
    )
    result = await analyzer.analyze(raw)
    assert result.category == CategoryEnum.SKIN
    assert "YANGI SKIN" in result.formatted_post
    assert "Lunox" in result.formatted_post
    assert "#MLBB #Skin" in result.formatted_post


@pytest.mark.asyncio
async def test_analyzer_mpl_id_result_post():
    analyzer = AIAnalyzer()
    raw = RawCollectedItem(
        source_url="https://id-mpl.com/schedule",
        title="MPL ID S14: RRQ vs Bigetron",
        raw_content="MPL Indonesia: RRQ 2 - 1 Bigetron. MVP: Skylar.",
        category_hint=CategoryEnum.MPL_ID,
        source_name="MPL Indonesia",
        source_type="OFFICIAL_MPL",
        reliability_score=100,
        metadata={
            "league": "MPL ID",
            "team_a": "RRQ",
            "team_b": "Bigetron",
            "score_a": 2,
            "score_b": 1,
            "date": "2026-09-29",
            "status": "finished",
            "mvp": "Skylar"
        }
    )
    result = await analyzer.analyze(raw)
    assert result.category == CategoryEnum.MPL_ID
    assert "MPL ID — NATIJA" in result.formatted_post
    assert "RRQ" in result.formatted_post
    assert "2 — 1" in result.formatted_post
    assert "Bigetron" in result.formatted_post
    assert "Skylar" in result.formatted_post
    assert "#MPLID #MLBB" in result.formatted_post
