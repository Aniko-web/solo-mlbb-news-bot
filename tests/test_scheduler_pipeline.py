from datetime import datetime, timedelta
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.models import Base, Match
from app.scheduler.jobs import NewsJobManager
from app.collectors.base import SourceCollector
from app.utils.validators import RawCollectedItem, CategoryEnum, PostStatus, utc_now
from app.database.repositories import MatchRepository


class MockCollector(SourceCollector):
    def __init__(self, items=None):
        super().__init__(
            name="Mock Collector",
            source_type="OFFICIAL_MLBB",
            base_url="https://mock.com",
            reliability_score=100
        )
        self.mock_items = items or [
            RawCollectedItem(
                source_url="https://mock.com/item1",
                title="Mock MLBB News Title",
                raw_content="This is a verified news item about an upcoming tournament.",
                category_hint=CategoryEnum.NEWS,
                source_name=self.name,
                source_type=self.source_type,
                reliability_score=100,
                published_at=utc_now()
            )
        ]

    async def fetch(self):
        return self.mock_items


class MockMatchCollector(SourceCollector):
    def __init__(self, items):
        super().__init__(
            name="Mock Match Collector",
            source_type="OFFICIAL_MPL",
            base_url="https://mock-mpl.com",
            reliability_score=100
        )
        self.items = items

    async def fetch(self):
        return self.items


@pytest.mark.asyncio
async def test_full_pipeline_deduplication(monkeypatch):
    # Setup test in-memory database
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    from app.database import database
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", session_maker)

    manager = NewsJobManager(bot=None)
    collector = MockCollector()

    # First run: should process 1 new post
    created_count = await manager.process_collector(collector, "Mock")
    assert created_count == 1

    # Second run: duplicate hash must be skipped!
    created_count_again = await manager.process_collector(collector, "Mock")
    assert created_count_again == 0

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_old_news_filtered_out(monkeypatch):
    """Verify that news items older than 24 hours are discarded and never published."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    from app.database import database
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", session_maker)

    manager = NewsJobManager(bot=None)

    # 1 item is fresh (now), 1 item is 3 days old
    old_dt = utc_now() - timedelta(days=3)
    items = [
        RawCollectedItem(
            source_url="https://mock.com/old_news",
            title="Old Patch 1.8 from weeks ago",
            raw_content="This is an outdated patch from earlier in the month.",
            category_hint=CategoryEnum.PATCH,
            source_name="Mock Collector",
            source_type="OFFICIAL_MLBB",
            reliability_score=100,
            published_at=old_dt
        ),
        RawCollectedItem(
            source_url="https://mock.com/fresh_news",
            title="Breaking Fresh Hero Update",
            raw_content="Today's brand new hero update announced just now.",
            category_hint=CategoryEnum.HERO,
            source_name="Mock Collector",
            source_type="OFFICIAL_MLBB",
            reliability_score=100,
            published_at=utc_now()
        )
    ]
    collector = MockCollector(items=items)

    processed_count = await manager.process_news_collector(collector, "MLBB", max_items=5)
    # Only 1 fresh post should be created; the 3-day-old one must be filtered out!
    assert processed_count == 1

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_match_lifecycle_upcoming_and_result(monkeypatch):
    """
    Test user requirement:
    - O'yin boshlanishidan oldin: Send upcoming match card
    - O'yin tugaganidan keyin: Send final match result card
    - No duplicate spam.
    """
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    from app.database import database
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", session_maker)

    manager = NewsJobManager(bot=None)
    today_str = utc_now().strftime("%Y-%m-%d")

    # 1. Match is UPCOMING before game starts
    upcoming_item = RawCollectedItem(
        source_url="https://id-mpl.com/schedule",
        title="MPL ID: RRQ vs ONIC",
        raw_content="Upcoming match between RRQ and ONIC at 15:00 WIB",
        category_hint=CategoryEnum.MPL_ID,
        source_name="MPL ID",
        source_type="OFFICIAL_MPL",
        reliability_score=100,
        published_at=utc_now(),
        metadata={
            "league": "MPL ID",
            "team_a": "RRQ",
            "team_b": "ONIC",
            "date": today_str,
            "time": "15:00",
            "status": "upcoming",
            "series": "BO3",
            "week": "4"
        }
    )
    col_up = MockMatchCollector(items=[upcoming_item])

    # Run check -> should send 1 UPCOMING card
    count_up = await manager.process_match_collector(col_up, "MPL ID")
    assert count_up == 1

    # Immediate second check while still upcoming -> 0 new cards (upcoming_notified is True)
    count_up_repeat = await manager.process_match_collector(col_up, "MPL ID")
    assert count_up_repeat == 0

    # 2. Later, Match FINISHES (2 - 1 score)
    finished_item = RawCollectedItem(
        source_url="https://id-mpl.com/schedule",
        title="MPL ID Result: RRQ 2 - 1 ONIC",
        raw_content="Match concluded. RRQ wins 2 to 1 against ONIC. MVP: Skylar.",
        category_hint=CategoryEnum.MPL_ID,
        source_name="MPL ID",
        source_type="OFFICIAL_MPL",
        reliability_score=100,
        published_at=utc_now(),
        metadata={
            "league": "MPL ID",
            "team_a": "RRQ",
            "team_b": "ONIC",
            "score_a": 2,
            "score_b": 1,
            "date": today_str,
            "time": "15:00",
            "status": "finished",
            "mvp": "Skylar",
            "series": "BO3",
            "week": "4"
        }
    )
    col_fin = MockMatchCollector(items=[finished_item])

    # Run check -> should send 1 FINAL RESULT card
    count_fin = await manager.process_match_collector(col_fin, "MPL ID")
    assert count_fin == 1

    # Immediate subsequent check -> 0 new cards (both upcoming and result are already notified)
    count_fin_repeat = await manager.process_match_collector(col_fin, "MPL ID")
    assert count_fin_repeat == 0

    await test_engine.dispose()
