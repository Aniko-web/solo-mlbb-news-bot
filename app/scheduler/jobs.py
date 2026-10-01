import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from app.config.settings import get_settings
from app.utils.logger import logger
from app.utils.hashing import generate_content_hash
from app.utils.validators import (
    RawCollectedItem,
    PostStatus,
    MatchItem,
    is_fresh_news,
    utc_now
)
from app.database.database import get_session
from app.database.repositories import (
    PostRepository,
    SourceRepository,
    SystemLogRepository,
    MatchRepository
)
from app.collectors import (
    SourceCollector,
    MLBBCollector,
    MPLIDCollector,
    MPLPHCollector,
    EsportsCollector
)
from app.ai.analyzer import AIAnalyzer
from app.ai.fun_generator import FunContentGenerator
from app.ai.formatter import PostFormatter
from app.media.image_processor import ImageProcessor
from app.media.renderer import render_match_upcoming, render_match_result
from app.telegram.publisher import TelegramPublisher
from app.telegram.admin import AdminNotifier
from app.telegram.bot import STATE
from app.services.matchday_service import MatchdayService

settings = get_settings()


class NewsJobManager:
    """
    Coordinates data collectors, AI analyzer, duplicate checking,
    admin approvals, and scheduled jobs:
    1. Daily morning MLBB news check (05:00 AM Tashkent time, max 5 fresh items).
    2. Frequent live match monitoring (Upcoming match cards before match, Result cards after final whistle).
    """

    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.analyzer = AIAnalyzer()
        self.publisher = TelegramPublisher(bot=bot)
        self.admin_notifier = AdminNotifier(bot=bot)

        # Registered collectors
        self.mlbb_collector = MLBBCollector()
        self.mpl_id_collector = MPLIDCollector()
        self.mpl_ph_collector = MPLPHCollector()
        self.esports_collector = EsportsCollector()
        self.fun_generator = FunContentGenerator()

    async def process_news_collector(
        self,
        collector: SourceCollector,
        key_label: str,
        max_items: int = 5
    ) -> int:
        """
        Process general news (MLBB, Esports, Patches, Skins):
        - Filters out news older than NEWS_MAX_AGE_HOURS (24 hours).
        - Limits to at most max_items to prevent channel flooding.
        - Translates to natural Uzbek and creates visual graphics.
        """
        if STATE.get("is_paused", False):
            logger.info(f"Skipping {collector.name} news collection: System is paused.")
            return 0

        now = utc_now()
        STATE["last_checks"][key_label] = now
        processed_count = 0

        logger.info(f"Starting news check for {collector.name} (max fresh items: {max_items})...")

        try:
            items: List[RawCollectedItem] = await collector.fetch()
            async with get_session() as session:
                await SourceRepository.record_success(
                    session=session,
                    name=collector.name,
                    url=collector.base_url,
                    source_type=collector.source_type,
                    reliability_score=collector.reliability_score
                )
        except Exception as e:
            error_time_str = now.strftime("%H:%M")
            logger.error(f"Source {collector.name} unavailable: {e}")
            async with get_session() as session:
                await SourceRepository.record_error(
                    session=session,
                    name=collector.name,
                    url=collector.base_url,
                    error_msg=str(e)
                )
                await SystemLogRepository.log_event(
                    session=session,
                    level="ERROR",
                    component="COLLECTOR",
                    message=f"{collector.name} unavailable: {e}"
                )
            await self.admin_notifier.send_source_error_alert(collector.name, error_time_str)
            return 0

        for item in items:
            if processed_count >= max_items:
                logger.info(f"[{collector.name}] Reached limit of {max_items} fresh items for this run.")
                break

            # 1. Freshness Verification: Strictly reject old or unverified news
            if not is_fresh_news(item, max_age_hours=settings.NEWS_MAX_AGE_HOURS):
                logger.info(f"[{collector.name}] ⏩ Skipped stale/unverified news [{item.published_at}]: {item.title[:45]}")
                continue

            logger.info(f"[{collector.name}] 🌟 VERIFIED FRESH NEWS [{item.published_at}]: {item.title[:45]}")

            content_hash = generate_content_hash(
                title=item.title,
                content=item.raw_content,
                source_url=item.source_url
            )

            async with get_session() as session:
                # 2. Duplicate Verification
                already_exists = await PostRepository.exists_by_hash(session, content_hash)
                if already_exists:
                    logger.debug(f"Skipping duplicate post [{content_hash[:8]}]: {item.title[:40]}")
                    continue

                # 3. AI Analysis & Uzbek Post Generation
                ai_output = await self.analyzer.analyze(item)

                # 4. Media / Graphic Generation if needed
                # 4. Media: For PATCH updates, prioritize the GosuGamers recap infographic
                image_bytes: Optional[bytes] = None
                if ai_output.category.value == "PATCH":
                    recap_data = item.metadata.get("patch_recap_data")
                    if not recap_data:
                        from app.utils.hero_matcher import extract_heroes_from_text
                        recap_data = extract_heroes_from_text(item.raw_content, item.title)
                        item.metadata["patch_recap_data"] = recap_data
                    try:
                        image_bytes = ImageProcessor.render_patch_recap(recap_data)
                    except Exception as err:
                        logger.error(f"Failed to render patch recap infographic: {err}")

                # If not patch or patch rendering failed, try downloading online image
                if not image_bytes and item.image_url:
                    try:
                        image_bytes = await ImageProcessor.download_and_optimize(item.image_url)
                    except Exception as img_err:
                        logger.warning(f"Failed to download image from {item.image_url[:50]}: {img_err}")

                # If still no image, generate news card fallback
                if not image_bytes:
                    image_bytes = ImageProcessor.generate_news_graphic(
                        title=item.title,
                        category=ai_output.category.value,
                        summary=ai_output.summary_uz,
                        highlights=ai_output.key_points
                    )

                # 5. Save to Database
                db_post = await PostRepository.create_post(
                    session=session,
                    source_url=item.source_url,
                    title=item.title,
                    category=ai_output.category.value,
                    content_hash=content_hash,
                    status=PostStatus.PENDING.value,
                    raw_content=item.raw_content,
                    formatted_post=ai_output.formatted_post,
                    image_url=item.image_url,
                    reliability_score=item.reliability_score,
                    confidence_score=ai_output.confidence
                )
                post_id = db_post.id

            # 6. Dispatch: Auto Mode vs Approval Mode
            if settings.AUTO_PUBLISH and not ai_output.needs_review:
                await self.publisher.publish_post(
                    post_id=post_id,
                    formatted_text=ai_output.formatted_post,
                    image_bytes=image_bytes,
                    image_url=item.image_url
                )
            else:
                await self.admin_notifier.send_approval_request(
                    post_id=post_id,
                    category=ai_output.category.value,
                    formatted_post=ai_output.formatted_post,
                    image_bytes=image_bytes,
                    image_url=item.image_url
                )

            processed_count += 1

        logger.info(f"[{collector.name}] Finished news check. {processed_count} new posts dispatched.")
        return processed_count

    async def process_match_collector(
        self,
        collector: SourceCollector,
        key_label: str
    ) -> int:
        """
        Timely match monitoring:
        1. O'yin boshlanishidan oldin: If upcoming and not yet notified, send upcoming graphic + caption.
        2. O'yin tugaganidan keyin: If match is finished and not yet notified, send final score card + caption.
        """
        if STATE.get("is_paused", False):
            logger.info(f"Skipping {collector.name} match check: System is paused.")
            return 0

        now = utc_now()
        STATE["last_checks"][key_label] = now
        processed_count = 0

        logger.info(f"Checking live matches for {collector.name}...")

        try:
            items: List[RawCollectedItem] = await collector.fetch()
            async with get_session() as session:
                await SourceRepository.record_success(
                    session=session,
                    name=collector.name,
                    url=collector.base_url,
                    source_type=collector.source_type,
                    reliability_score=collector.reliability_score
                )
        except Exception as e:
            logger.error(f"Source {collector.name} match error: {e}")
            return 0

        today_str = now.strftime("%Y-%m-%d")

        for item in items:
            meta = item.metadata
            if not meta or "team_a" not in meta or "team_b" not in meta:
                continue

            league = meta.get("league", key_label)
            team_a = meta.get("team_a")
            team_b = meta.get("team_b")
            match_date = meta.get("date", today_str)
            match_time = meta.get("time", "15:00")
            raw_status = str(meta.get("status", "upcoming")).lower()
            score_a = meta.get("score_a")
            score_b = meta.get("score_b")
            mvp = meta.get("mvp")
            week = meta.get("week", "4")
            season = meta.get("season", "Season 14")
            series = meta.get("series", "BO3")

            is_finished = (
                raw_status in ["finished", "final"] or
                (score_a is not None and score_b is not None and (score_a >= 2 or score_b >= 2))
            )
            match_status = "finished" if is_finished else "upcoming"

            # Timely date filtering:
            # - For upcoming matches: only announce matches happening today or in next 2 days
            # - For finished matches: only announce matches that finished in the last 3 days
            try:
                m_dt = datetime.strptime(match_date, "%Y-%m-%d")
                days_diff = (m_dt.date() - now.date()).days
            except Exception:
                days_diff = 0

            if match_status == "upcoming":
                if days_diff != 0:
                    continue
            elif match_status == "finished":
                if not (-1 <= days_diff <= 0):
                    continue

            match_item = MatchItem(
                league=league,
                team_a=team_a,
                team_b=team_b,
                date=match_date,
                time=match_time,
                season=str(season),
                week=str(week),
                score_a=score_a,
                score_b=score_b,
                status=match_status,
                mvp=mvp,
                series=series,
                source_url=item.source_url
            )

            async with get_session() as session:
                db_match = await MatchRepository.upsert_match(session, match_item)

                match_dict: Dict[str, Any] = {
                    "league": league,
                    "team_a": team_a,
                    "team_b": team_b,
                    "score_a": score_a,
                    "score_b": score_b,
                    "status": "FINAL" if match_status == "finished" else "UPCOMING",
                    "mvp": mvp,
                    "date": meta.get("date_display") or match_date,
                    "date_display": meta.get("date_display") or match_date,
                    "time": match_time,
                    "week": week,
                    "season": season,
                    "series": series,
                    "countdown_str": meta.get("countdown_str")
                }

                # 1. UPCOMING MATCH ANNOUNCEMENT (Schedule Post)
                if match_status == "upcoming" and not getattr(db_match, "upcoming_notified", False):
                    image_bytes = render_match_upcoming(match_dict)
                    formatted_post = PostFormatter.format_match_upcoming_from_data(match_dict, source_url=item.source_url)
                    content_hash = generate_content_hash(
                        title=f"UPCOMING:{league}:{team_a}vs{team_b}:{match_date}",
                        content=formatted_post,
                        source_url=item.source_url
                    )

                    already_exists = await PostRepository.exists_by_hash(session, content_hash)
                    if not already_exists:
                        # Save card image to disk
                        generated_dir = os.path.join(os.getcwd(), "assets", "generated")
                        os.makedirs(generated_dir, exist_ok=True)
                        card_path = os.path.join(generated_dir, f"match_up_{db_match.id}_{int(datetime.now().timestamp())}.png")
                        with open(card_path, "wb") as f:
                            f.write(image_bytes)

                        db_post = await PostRepository.create_post(
                            session=session,
                            source_url=item.source_url,
                            title=f"Kutilayotgan o'yin: {team_a} vs {team_b}",
                            category="MPL_ID" if "ID" in league else "MPL_PH",
                            content_hash=content_hash,
                            status=PostStatus.PENDING.value,
                            raw_content=item.raw_content,
                            formatted_post=formatted_post,
                            image_url=card_path,
                            reliability_score=item.reliability_score,
                            confidence_score=1.0
                        )

                        if settings.AUTO_PUBLISH:
                            await self.publisher.publish_post(
                                post_id=db_post.id,
                                formatted_text=formatted_post,
                                image_bytes=image_bytes
                            )
                        else:
                            await self.admin_notifier.send_approval_request(
                                post_id=db_post.id,
                                category="MPL_ID" if "ID" in league else "MPL_PH",
                                formatted_post=formatted_post,
                                image_bytes=image_bytes
                            )

                    await MatchRepository.mark_upcoming_notified(session, db_match.id)
                    logger.info(f"[{league}] Sent UPCOMING match announcement: {team_a} vs {team_b}")
                    processed_count += 1

                # 2. MATCH RESULT (Result Post)
                elif match_status == "finished" and not getattr(db_match, "result_notified", False):
                    image_bytes = render_match_result(match_dict)
                    formatted_post = PostFormatter.format_match_result_from_data(match_dict, source_url=item.source_url)
                    content_hash = generate_content_hash(
                        title=f"RESULT:{league}:{team_a}{score_a}-{score_b}{team_b}:{match_date}",
                        content=formatted_post,
                        source_url=item.source_url
                    )

                    already_exists = await PostRepository.exists_by_hash(session, content_hash)
                    if not already_exists:
                        # Save card image to disk
                        generated_dir = os.path.join(os.getcwd(), "assets", "generated")
                        os.makedirs(generated_dir, exist_ok=True)
                        card_path = os.path.join(generated_dir, f"match_res_{db_match.id}_{int(datetime.now().timestamp())}.png")
                        with open(card_path, "wb") as f:
                            f.write(image_bytes)

                        db_post = await PostRepository.create_post(
                            session=session,
                            source_url=item.source_url,
                            title=f"Natija: {team_a} {score_a} - {score_b} {team_b}",
                            category="MPL_ID" if "ID" in league else "MPL_PH",
                            content_hash=content_hash,
                            status=PostStatus.PENDING.value,
                            raw_content=item.raw_content,
                            formatted_post=formatted_post,
                            image_url=card_path,
                            reliability_score=item.reliability_score,
                            confidence_score=1.0
                        )

                        if settings.AUTO_PUBLISH:
                            await self.publisher.publish_post(
                                post_id=db_post.id,
                                formatted_text=formatted_post,
                                image_bytes=image_bytes
                            )
                        else:
                            await self.admin_notifier.send_approval_request(
                                post_id=db_post.id,
                                category="MPL_ID" if "ID" in league else "MPL_PH",
                                formatted_post=formatted_post,
                                image_bytes=image_bytes
                            )

                    await MatchRepository.mark_result_notified(session, db_match.id)
                    logger.info(f"[{league}] Sent FINAL match result: {team_a} {score_a} - {score_b} {team_b}")
                    processed_count += 1

        logger.info(f"[{collector.name}] Finished match check. {processed_count} match cards dispatched.")
        return processed_count

    async def process_collector(self, collector: SourceCollector, key_label: str) -> int:
        """Unified collector dispatcher."""
        if "MPL" in key_label:
            return await self.process_match_collector(collector, key_label)
        return await self.process_news_collector(collector, key_label, max_items=settings.MAX_DAILY_NEWS_COUNT)

    # Scheduled handlers
    async def job_daily_morning_news(self):
        """
        Scheduled daily at 05:00 AM (Tashkent time):
        Collects MLBB official updates and esports news, filtered to last 24h, capped at 5 posts.
        """
        logger.info(f"=== Starting Daily Morning News ({settings.DAILY_NEWS_HOUR:02d}:{settings.DAILY_NEWS_MINUTE:02d}) ===")
        total_processed = 0
        limit_left = settings.MAX_DAILY_NEWS_COUNT

        for collector, label in [(self.mlbb_collector, "MLBB"), (self.esports_collector, "Esports")]:
            if limit_left <= 0:
                break
            count = await self.process_news_collector(collector, label, max_items=limit_left)
            total_processed += count
            limit_left -= count

        logger.info(f"=== Daily Morning News completed: {total_processed} fresh posts dispatched ===")

    async def job_check_matches(self):
        """
        Scheduled every few minutes (timely match updates):
        1. Alerts before match starts, posts final card once match finishes.
        2. Daily matchday announcement if today is a matchday.
        """
        await self.process_match_collector(self.mpl_id_collector, "MPL ID")
        await self.process_match_collector(self.mpl_ph_collector, "MPL PH")
        await self.job_check_matchday_schedules()

    async def job_check_matchday_schedules(self):
        """
        Daily Matchday Schedule Announcement:
        If today has matches scheduled for MPL ID or MPL PH:
        - Renders high-impact broadcast Matchday Card with all today's matches.
        - Identifies Match of the Day (Kunning eng muhim o'yini).
        - Generates exciting AI hype commentary.
        - Dispatches via auto-publish or admin approval.
        """
        if STATE.get("is_paused", False):
            return

        today = MatchdayService.get_current_date_tashkent()
        for league in ["MPL ID", "MPL PH"]:
            try:
                date_str, matches, is_rest_day, next_matchday = await MatchdayService.get_matches_for_day(league=league, target_date=today)
                if date_str != today:
                    continue

                prefix = "RESTDAY" if is_rest_day else "MATCHDAY"
                content_hash = generate_content_hash(
                    title=f"{prefix}:{league}:{today}",
                    content=f"{prefix.lower()}_{league}_{today}"
                )

                async with get_session() as session:
                    already_posted = await PostRepository.exists_by_hash(session, content_hash)
                    if already_posted:
                        continue

                    post_payload = await MatchdayService.generate_matchday_post(
                        league=league,
                        target_date=today,
                        analyzer=self.analyzer
                    )
                    if not post_payload.get("success"):
                        continue

                    image_bytes = post_payload.get("image_bytes")
                    caption = post_payload["caption"]

                    card_path = None
                    if image_bytes:
                        generated_dir = os.path.join(os.getcwd(), "assets", "generated")
                        os.makedirs(generated_dir, exist_ok=True)
                        league_slug = "mpl_id" if "ID" in league else "mpl_ph"
                        card_filename = f"matchday_{league_slug}_{today}.png"
                        card_path = os.path.join(generated_dir, card_filename)
                        with open(card_path, "wb") as f:
                            f.write(image_bytes)

                    status = PostStatus.PUBLISHED.value if settings.AUTO_PUBLISH else PostStatus.PENDING.value
                    category = "MPL_ID" if "ID" in league else "MPL_PH"
                    post_title = f"Bugun dam olish kuni: {league} ({today})" if is_rest_day else f"Bugungi o'yinlar dasturi: {league} ({today})"

                    db_post = await PostRepository.create_post(
                        session=session,
                        source_url="https://liquipedia.net/mobilelegends/",
                        title=post_title,
                        category=category,
                        content_hash=content_hash,
                        status=status,
                        raw_content=f"Matchday schedule for {league} on {today}",
                        formatted_post=caption,
                        image_url=card_path,
                        reliability_score=100,
                        confidence_score=1.0,
                        published_at=datetime.utcnow() if settings.AUTO_PUBLISH else None
                    )

                    if settings.AUTO_PUBLISH:
                        msg_id = await self.publisher.publish_post(
                            post_id=db_post.id,
                            formatted_text=caption,
                            image_bytes=image_bytes
                        )
                        if msg_id:
                            await PostRepository.update_status(
                                session=session,
                                post_id=db_post.id,
                                status=PostStatus.PUBLISHED.value,
                                telegram_message_id=msg_id
                            )
                            logger.info(f"[{league}] Matchday schedule auto-published to channel (Msg ID: {msg_id})")
                    else:
                        await self.admin_notifier.send_approval_request(
                            post_id=db_post.id,
                            category=category,
                            formatted_post=caption,
                            image_bytes=image_bytes
                        )
                        logger.info(f"[{league}] Matchday schedule dispatched to admins for approval.")
            except Exception as e:
                logger.error(f"Error checking/dispatching matchday schedule for {league}: {e}", exc_info=True)

    async def job_mlbb_official(self) -> int:
        return await self.process_news_collector(self.mlbb_collector, "MLBB", max_items=settings.MAX_DAILY_NEWS_COUNT)

    async def job_mpl_id(self) -> int:
        return await self.process_match_collector(self.mpl_id_collector, "MPL ID")

    async def job_mpl_ph(self) -> int:
        return await self.process_match_collector(self.mpl_ph_collector, "MPL PH")

    async def job_esports(self) -> int:
        return await self.process_news_collector(self.esports_collector, "Esports", max_items=settings.MAX_DAILY_NEWS_COUNT)

    async def job_mlbb_fun_content(self) -> int:
        """
        Scheduled every FUN_POSTS_INTERVAL_HOURS (default 5 hours):
        Generates engaging MLBB fact, joke, meme, lore or pro tip with visual card.
        """
        if STATE.get("is_paused", False):
            logger.info("Skipping MLBB fun post: System is paused.")
            return 0

        logger.info("=== Generating MLBB Fun/Lore/Joke Post (Every 5 Hours) ===")
        try:
            data = await self.fun_generator.generate_fun_post()
            content_hash = generate_content_hash(data["title"], data["content"])

            # Save card to disk
            generated_dir = os.path.join(os.getcwd(), "assets", "generated")
            os.makedirs(generated_dir, exist_ok=True)
            card_filename = f"fun_{int(datetime.now().timestamp())}.png"
            card_path = os.path.join(generated_dir, card_filename)
            with open(card_path, "wb") as f:
                f.write(data["image_bytes"])

            async with get_session() as session:
                if await PostRepository.exists_by_hash(session, content_hash):
                    logger.info("Generated fun content is already in database, skipping duplicate.")
                    return 0

                auto_publish = settings.FUN_POSTS_AUTO_PUBLISH or settings.AUTO_PUBLISH
                status = PostStatus.PUBLISHED.value if auto_publish else PostStatus.PENDING.value

                post = await PostRepository.create_post(
                    session=session,
                    source_url="https://m.mobilelegends.com",
                    title=data["title"],
                    category=data["topic_type"],
                    content_hash=content_hash,
                    status=status,
                    raw_content=data["content"],
                    formatted_post=data["formatted_caption"],
                    image_url=card_path,
                    reliability_score=100,
                    confidence_score=1.0,
                    published_at=datetime.utcnow() if auto_publish else None
                )

                if auto_publish:
                    msg_id = await self.publisher.publish_post(
                        post_id=post.id,
                        formatted_text=data["formatted_caption"],
                        image_bytes=data["image_bytes"]
                    )
                    if msg_id:
                        await PostRepository.update_status(
                            session=session,
                            post_id=post.id,
                            status=PostStatus.PUBLISHED.value,
                            telegram_message_id=msg_id
                        )
                        logger.info(f"MLBB Fun post #{post.id} auto-published to channel (msg_id: {msg_id})")
                else:
                    await self.admin_notifier.send_approval_request(
                        post_id=post.id,
                        category=f"MLBB {data['topic_type']}",
                        formatted_post=data["formatted_caption"],
                        image_bytes=data["image_bytes"]
                    )
                    logger.info(f"MLBB Fun post #{post.id} dispatched to admins for approval.")
            return 1
        except Exception as e:
            logger.error(f"Error generating or dispatching MLBB fun post: {e}", exc_info=True)
            return 0

    async def job_check_pending_approval_timeouts(self):
        """
        Checks for posts that have been in PENDING status for more than APPROVAL_TIMEOUT_MINUTES
        (default: 30 minutes) without admin intervention, and automatically publishes them to the channel.
        """
        if STATE.get("is_paused", False):
            return

        timeout_min = getattr(settings, "APPROVAL_TIMEOUT_MINUTES", 30)
        try:
            async with get_session() as session:
                expired_posts = await PostRepository.get_expired_pending_posts(session, older_than_minutes=timeout_min)

            if not expired_posts:
                return

            logger.info(f"Found {len(expired_posts)} pending post(s) older than {timeout_min}m. Auto-publishing to channel...")

            for post in expired_posts:
                try:
                    async with get_session() as session:
                        current_post = await PostRepository.get_by_id(session, post.id)
                        if not current_post or current_post.status != PostStatus.PENDING.value:
                            continue
                        post_id = current_post.id
                        formatted_text = current_post.formatted_post or current_post.title
                        image_url = current_post.image_url
                        category = current_post.category
                        title = current_post.title

                    # Publish to channel (handles DB status update internally)
                    msg_id = await self.publisher.publish_post(
                        post_id=post_id,
                        formatted_text=formatted_text,
                        image_url=image_url
                    )

                    if msg_id:
                        logger.info(f"Post #{post_id} auto-published to channel after {timeout_min}m timeout (Msg ID: {msg_id})")

                        # Send alert to admins that post was auto-forwarded
                        await self.admin_notifier.send_auto_published_alert(
                            post_id=post_id,
                            category=category,
                            title=title,
                            msg_id=msg_id
                        )
                except Exception as inner_err:
                    logger.error(f"Error auto-publishing post #{post.id}: {inner_err}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in approval timeout monitor job: {e}", exc_info=True)

    def start(self):
        """Register daily morning cron and live match polling intervals."""
        # 1. Daily Morning News Job (05:00 AM Tashkent time, max 5 fresh items)
        try:
            self.scheduler.add_job(
                self.job_daily_morning_news,
                CronTrigger(
                    hour=settings.DAILY_NEWS_HOUR,
                    minute=settings.DAILY_NEWS_MINUTE,
                    timezone=settings.DAILY_NEWS_TIMEZONE
                ),
                id="daily_morning_news_job",
                replace_existing=True
            )
            logger.info(f"Daily morning news job scheduled for {settings.DAILY_NEWS_HOUR:02d}:{settings.DAILY_NEWS_MINUTE:02d} ({settings.DAILY_NEWS_TIMEZONE}).")
        except Exception as e:
            logger.warning(f"Timezone '{settings.DAILY_NEWS_TIMEZONE}' fallback to local: {e}")
            self.scheduler.add_job(
                self.job_daily_morning_news,
                CronTrigger(hour=settings.DAILY_NEWS_HOUR, minute=settings.DAILY_NEWS_MINUTE),
                id="daily_morning_news_job",
                replace_existing=True
            )

        # 2. Frequent Live Match Monitoring (every 5 minutes)
        self.scheduler.add_job(
            self.job_check_matches,
            "interval",
            minutes=settings.CHECK_INTERVAL_MPL_ID_MIN,
            id="mpl_matches_live_job",
            replace_existing=True,
            next_run_time=datetime.now()  # run immediately on startup
        )
        logger.info(f"MPL Match live monitoring scheduled every {settings.CHECK_INTERVAL_MPL_ID_MIN} minutes.")

        # 3. Regular MLBB Patch & Game News Monitoring (Patch notes, skins, events)
        self.scheduler.add_job(
            self.job_mlbb_official,
            "interval",
            minutes=settings.CHECK_INTERVAL_MLBB_MIN,
            id="mlbb_news_regular_job",
            replace_existing=True,
            next_run_time=datetime.now()
        )
        logger.info(f"MLBB Patch & Game news monitoring scheduled every {settings.CHECK_INTERVAL_MLBB_MIN} minutes.")

        # 4. MLBB Fun Facts, Memes & Lore Schedule (every 5 hours)
        if settings.FUN_POSTS_ENABLED:
            self.scheduler.add_job(
                self.job_mlbb_fun_content,
                "interval",
                hours=settings.FUN_POSTS_INTERVAL_HOURS,
                id="mlbb_fun_content_job",
                replace_existing=True
            )
            logger.info(f"MLBB Fun & Lore job scheduled every {settings.FUN_POSTS_INTERVAL_HOURS} hours.")

        # 5. Pending Approval Timeout Monitor (checks every 1 minute)
        self.scheduler.add_job(
            self.job_check_pending_approval_timeouts,
            "interval",
            minutes=1,
            id="approval_timeout_monitor_job",
            replace_existing=True,
            next_run_time=datetime.now()
        )
        logger.info(f"Pending approval timeout monitor scheduled (every 1 minute, timeout: {settings.APPROVAL_TIMEOUT_MINUTES}m).")

        self.scheduler.start()
        logger.info("APScheduler initialized and started successfully.")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("APScheduler stopped.")
