import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.models import Base
from app.database.repositories import PostRepository, MatchRepository, SourceRepository, SystemLogRepository
from app.utils.validators import MatchItem, PostStatus


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_post_creation_and_deduplication(async_session: AsyncSession):
    # Check non-existence
    assert not await PostRepository.exists_by_hash(async_session, "hash_123")

    # Create post
    post = await PostRepository.create_post(
        session=async_session,
        source_url="https://test.com/post1",
        title="Test Post 1",
        category="NEWS",
        content_hash="hash_123",
        status=PostStatus.PENDING.value
    )
    assert post.id is not None
    assert post.status == PostStatus.PENDING.value

    # Check existence
    assert await PostRepository.exists_by_hash(async_session, "hash_123")

    # Update status to published
    updated = await PostRepository.update_status(
        session=async_session,
        post_id=post.id,
        status=PostStatus.PUBLISHED.value,
        telegram_message_id=10101
    )
    assert updated.status == PostStatus.PUBLISHED.value
    assert updated.telegram_message_id == 10101
    assert updated.published_at is not None


@pytest.mark.asyncio
async def test_match_upsert(async_session: AsyncSession):
    match_item = MatchItem(
        league="MPL ID",
        team_a="RRQ",
        team_b="ONIC",
        date="2026-09-29",
        time="15:00",
        score_a=None,
        score_b=None,
        status="upcoming"
    )
    created = await MatchRepository.upsert_match(async_session, match_item)
    assert created.id is not None
    assert created.status == "upcoming"

    # Now update with final score
    match_item.score_a = 2
    match_item.score_b = 1
    match_item.status = "finished"
    match_item.mvp = "Sanz"

    updated = await MatchRepository.upsert_match(async_session, match_item)
    assert updated.id == created.id
    assert updated.score_a == 2
    assert updated.score_b == 1
    assert updated.mvp == "Sanz"
    assert updated.status == "finished"
