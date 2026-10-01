import pytest
from app.collectors import MLBBCollector, MPLIDCollector, MPLPHCollector, EsportsCollector
from app.utils.validators import CategoryEnum


@pytest.mark.asyncio
async def test_mlbb_collector():
    collector = MLBBCollector()
    items = await collector.fetch()
    assert len(items) > 0
    categories = [i.category_hint for i in items]
    assert CategoryEnum.PATCH in categories or CategoryEnum.SKIN in categories or CategoryEnum.HERO in categories
    assert all(i.reliability_score == 100 for i in items)
    assert all(len(i.title) > 0 for i in items)


@pytest.mark.asyncio
async def test_mpl_id_collector():
    collector = MPLIDCollector()
    items = await collector.fetch()
    assert len(items) > 0
    assert all(i.category_hint == CategoryEnum.MPL_ID for i in items)
    assert all(i.reliability_score == 100 for i in items)


@pytest.mark.asyncio
async def test_mpl_ph_collector():
    collector = MPLPHCollector()
    items = await collector.fetch()
    assert len(items) > 0
    assert all(i.category_hint == CategoryEnum.MPL_PH for i in items)
    assert all(i.reliability_score == 100 for i in items)


@pytest.mark.asyncio
async def test_esports_collector():
    collector = EsportsCollector()
    items = await collector.fetch()
    assert len(items) > 0
    assert all(i.category_hint in [CategoryEnum.ESPORTS, CategoryEnum.TOURNAMENT] for i in items)
