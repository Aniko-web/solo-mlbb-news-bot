from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, update, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Post, Match, Source, SystemLog, Hero, Skin, AdminUser, ChannelConfig
from app.utils.validators import MatchItem, PostStatus, CategoryEnum, utc_now
from app.utils.logger import logger


class PostRepository:
    @staticmethod
    async def exists_by_hash(session: AsyncSession, content_hash: str) -> bool:
        query = select(Post.id).where(Post.content_hash == content_hash).limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def create_post(
        session: AsyncSession,
        source_url: str,
        title: str,
        category: str,
        content_hash: str,
        status: str = PostStatus.PENDING.value,
        raw_content: Optional[str] = None,
        formatted_post: Optional[str] = None,
        image_url: Optional[str] = None,
        reliability_score: int = 50,
        confidence_score: float = 1.0,
        published_at: Optional[datetime] = None,
        telegram_message_id: Optional[int] = None
    ) -> Post:
        post = Post(
            source_url=source_url,
            title=title,
            category=category,
            content_hash=content_hash,
            status=status,
            raw_content=raw_content,
            formatted_post=formatted_post,
            image_url=image_url,
            reliability_score=reliability_score,
            confidence_score=confidence_score,
            published_at=published_at,
            telegram_message_id=telegram_message_id
        )
        session.add(post)
        await session.flush()
        return post

    @staticmethod
    async def get_by_id(session: AsyncSession, post_id: int) -> Optional[Post]:
        query = select(Post).where(Post.id == post_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
        session: AsyncSession,
        post_id: int,
        status: str,
        telegram_message_id: Optional[int] = None,
        formatted_post: Optional[str] = None
    ) -> Optional[Post]:
        post = await PostRepository.get_by_id(session, post_id)
        if not post:
            return None
        post.status = status
        if telegram_message_id is not None:
            post.telegram_message_id = telegram_message_id
        if formatted_post is not None:
            post.formatted_post = formatted_post
        if status == PostStatus.PUBLISHED.value and not post.published_at:
            post.published_at = utc_now()
        await session.flush()
        return post

    @staticmethod
    async def get_pending_posts(session: AsyncSession, limit: int = 20) -> List[Post]:
        query = (
            select(Post)
            .where(Post.status == PostStatus.PENDING.value)
            .order_by(desc(Post.created_at))
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_expired_pending_posts(
        session: AsyncSession,
        older_than_minutes: int = 30
    ) -> List[Post]:
        """
        Fetch all posts in PENDING status that were created more than older_than_minutes ago.
        """
        cutoff = utc_now() - timedelta(minutes=older_than_minutes)
        query = (
            select(Post)
            .where(
                and_(
                    Post.status == PostStatus.PENDING.value,
                    Post.created_at <= cutoff
                )
            )
            .order_by(Post.created_at.asc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_today_posts(session: AsyncSession) -> int:
        today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = (
            select(func.count(Post.id))
            .where(and_(Post.status == PostStatus.PUBLISHED.value, Post.published_at >= today_start))
        )
        result = await session.execute(query)
        return result.scalar() or 0

    @staticmethod
    async def get_latest_posts(session: AsyncSession, limit: int = 5) -> List[Post]:
        query = (
            select(Post)
            .order_by(desc(Post.created_at))
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


class MatchRepository:
    @staticmethod
    async def upsert_match(session: AsyncSession, item: MatchItem) -> Match:
        # Check if match already exists by league, teams, date
        query = (
            select(Match)
            .where(
                and_(
                    Match.league == item.league,
                    Match.team_a == item.team_a,
                    Match.team_b == item.team_b,
                    Match.date == item.date
                )
            )
            .limit(1)
        )
        result = await session.execute(query)
        match = result.scalar_one_or_none()

        if match:
            # Update fields
            if item.time:
                match.time = item.time
            if item.score_a is not None:
                match.score_a = item.score_a
            if item.score_b is not None:
                match.score_b = item.score_b
            if item.status:
                match.status = item.status
            if item.mvp:
                match.mvp = item.mvp
            if item.series:
                match.series = item.series
            if item.week:
                match.week = item.week
            if item.season:
                match.season = item.season
            if item.source_url:
                match.source_url = item.source_url
        else:
            match = Match(
                league=item.league,
                team_a=item.team_a,
                team_b=item.team_b,
                date=item.date,
                time=item.time,
                season=item.season,
                week=item.week,
                score_a=item.score_a,
                score_b=item.score_b,
                status=item.status,
                mvp=item.mvp,
                series=item.series,
                source_url=item.source_url
            )
            session.add(match)

        await session.flush()
        return match

    @staticmethod
    async def get_matches_by_date(
        session: AsyncSession,
        league: str,
        match_date: str
    ) -> List[Match]:
        query = (
            select(Match)
            .where(and_(Match.league == league, Match.date == match_date))
            .order_by(Match.time)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def mark_upcoming_notified(session: AsyncSession, match_id: int):
        await session.execute(
            update(Match).where(Match.id == match_id).values(upcoming_notified=True)
        )
        await session.flush()

    @staticmethod
    async def mark_result_notified(session: AsyncSession, match_id: int):
        await session.execute(
            update(Match).where(Match.id == match_id).values(result_notified=True)
        )
        await session.flush()

    @staticmethod
    async def find_match_by_details(
        session: AsyncSession,
        league: str,
        team_a: str,
        team_b: str,
        match_date: str
    ) -> Optional[Match]:
        query = (
            select(Match)
            .where(
                and_(
                    Match.league == league,
                    Match.team_a == team_a,
                    Match.team_b == team_b,
                    Match.date == match_date
                )
            )
            .limit(1)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_matches_by_league(
        session: AsyncSession,
        league: str
    ) -> List[Match]:
        query = (
            select(Match)
            .where(Match.league == league)
            .order_by(Match.date, Match.time)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


class SourceRepository:
    @staticmethod
    async def record_success(
        session: AsyncSession,
        name: str,
        url: str,
        source_type: str,
        reliability_score: int = 100
    ) -> Source:
        query = select(Source).where(Source.name == name).limit(1)
        result = await session.execute(query)
        source = result.scalar_one_or_none()

        if not source:
            source = Source(
                name=name,
                url=url,
                source_type=source_type,
                reliability_score=reliability_score,
                status="ACTIVE",
                last_checked_at=utc_now()
            )
            session.add(source)
        else:
            source.status = "ACTIVE"
            source.last_checked_at = utc_now()
            source.error_count = 0
            source.last_error_message = None

        await session.flush()
        return source

    @staticmethod
    async def record_error(session: AsyncSession, name: str, url: str, error_msg: str) -> Source:
        query = select(Source).where(Source.name == name).limit(1)
        result = await session.execute(query)
        source = result.scalar_one_or_none()

        if not source:
            source = Source(
                name=name,
                url=url,
                source_type="UNKNOWN",
                reliability_score=50,
                status="ERROR",
                last_checked_at=utc_now(),
                error_count=1,
                last_error_message=error_msg
            )
            session.add(source)
        else:
            source.status = "ERROR"
            source.last_checked_at = utc_now()
            source.error_count += 1
            source.last_error_message = error_msg

        await session.flush()
        return source

    @staticmethod
    async def get_source_statuses(session: AsyncSession) -> List[Source]:
        query = select(Source).order_by(Source.name)
        result = await session.execute(query)
        return list(result.scalars().all())


class SystemLogRepository:
    @staticmethod
    async def log_event(
        session: AsyncSession,
        level: str,
        component: str,
        message: str,
        details: Optional[str] = None
    ) -> SystemLog:
        log_entry = SystemLog(
            level=level,
            component=component,
            message=message,
            details=details
        )
        session.add(log_entry)
        await session.flush()
        return log_entry

    @staticmethod
    async def count_errors_today(session: AsyncSession) -> int:
        today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = (
            select(func.count(SystemLog.id))
            .where(
                and_(
                    SystemLog.level.in_(["ERROR", "CRITICAL"]),
                    SystemLog.timestamp >= today_start
                )
            )
        )
        result = await session.execute(query)
        return result.scalar() or 0


class AdminRepository:
    @staticmethod
    async def get_all_admin_ids(session: AsyncSession) -> List[int]:
        query = select(AdminUser.telegram_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def is_admin(session: AsyncSession, user_id: int) -> bool:
        query = select(AdminUser.id).where(AdminUser.telegram_id == user_id).limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def add_admin(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        added_by: Optional[int] = None
    ) -> bool:
        query = select(AdminUser).where(AdminUser.telegram_id == telegram_id).limit(1)
        result = await session.execute(query)
        if result.scalar_one_or_none() is not None:
            return False  # Already exists

        admin = AdminUser(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            added_by=added_by
        )
        session.add(admin)
        await session.flush()
        return True

    @staticmethod
    async def remove_admin(session: AsyncSession, telegram_id: int) -> bool:
        query = select(AdminUser).where(AdminUser.telegram_id == telegram_id).limit(1)
        result = await session.execute(query)
        admin = result.scalar_one_or_none()
        if not admin:
            return False
        await session.delete(admin)
        await session.flush()
        return True

    @staticmethod
    async def list_admins(session: AsyncSession) -> List[AdminUser]:
        query = select(AdminUser).order_by(AdminUser.id)
        result = await session.execute(query)
        return list(result.scalars().all())


class ChannelRepository:
    @staticmethod
    async def get_active_channel_ids(session: AsyncSession) -> List[str]:
        query = select(ChannelConfig.channel_id).where(ChannelConfig.is_active == True)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def add_channel(
        session: AsyncSession,
        channel_id: str,
        title: Optional[str] = None,
        username: Optional[str] = None,
        added_by: Optional[int] = None
    ) -> bool:
        query = select(ChannelConfig).where(ChannelConfig.channel_id == channel_id).limit(1)
        result = await session.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_active = True
            if title:
                existing.title = title
            if username:
                existing.username = username
            await session.flush()
            return False  # Already existed, now reactivated

        chan = ChannelConfig(
            channel_id=channel_id,
            title=title,
            username=username,
            is_active=True,
            added_by=added_by
        )
        session.add(chan)
        await session.flush()
        return True

    @staticmethod
    async def remove_channel(session: AsyncSession, channel_id: str) -> bool:
        query = select(ChannelConfig).where(ChannelConfig.channel_id == channel_id).limit(1)
        result = await session.execute(query)
        chan = result.scalar_one_or_none()
        if not chan:
            return False
        await session.delete(chan)
        await session.flush()
        return True

    @staticmethod
    async def list_channels(session: AsyncSession) -> List[ChannelConfig]:
        query = select(ChannelConfig).order_by(ChannelConfig.id)
        result = await session.execute(query)
        return list(result.scalars().all())

