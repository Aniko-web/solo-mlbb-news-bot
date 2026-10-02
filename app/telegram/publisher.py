import os
from typing import Optional, Union
from aiogram import Bot
from aiogram.types import BufferedInputFile, Message
from app.config.settings import get_settings
from app.utils.logger import logger
from app.database.database import get_session
from app.database.repositories import PostRepository
from app.utils.validators import PostStatus

settings = get_settings()


from app.utils.html_utils import safe_trim_html


def _split_caption(text: str, max_len: int = 1020) -> tuple[str, Optional[str]]:
    """
    Split text cleanly for Telegram's strict 1024 character photo caption limit.
    Ensures all HTML tags (<b>, <i>, <a>, <code>) are safely closed.
    """
    if len(text) <= max_len:
        return text, None
    idx = text.rfind("\n\n", 0, max_len)
    if idx == -1:
        idx = text.rfind("\n", 0, max_len)
    if idx == -1:
        idx = text.rfind(". ", 0, max_len)
    if idx == -1:
        idx = max_len - 3
    caption = safe_trim_html(text[:idx].rstrip(), max_len=max_len)
    rest = text[idx:].lstrip()
    return caption, rest


class TelegramPublisher:
    """
    Publishes verified posts to the target Telegram Channel with photo support.
    """

    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        self.channel_id = settings.channel_chat_id

    async def publish_post(
        self,
        post_id: int,
        formatted_text: str,
        image_bytes: Optional[bytes] = None,
        image_url: Optional[str] = None
    ) -> Optional[int]:
        """
        Publish post to all configured Telegram channels with photo attachment.
        Returns telegram message ID if successful.
        """
        channel_ids = settings.channel_ids
        if not self.bot or not channel_ids:
            logger.warning("Telegram Bot or Channel ID not configured. Simulated publish.")
            async with get_session() as session:
                await PostRepository.update_status(
                    session=session,
                    post_id=post_id,
                    status=PostStatus.PUBLISHED.value,
                    telegram_message_id=999999
                )
            return 999999

        try:
            # Ensure post has channel signature footer at the end if not already present
            if "Telegram sahifamiz" not in formatted_text:
                from app.ai.formatter import CHANNEL_FOOTER
                formatted_text = f"{formatted_text.rstrip()}\n\n{CHANNEL_FOOTER}"

            # 1. If image bytes not passed directly, try loading from local file or downloading from image_url
            if not image_bytes and image_url:
                try:
                    if os.path.exists(image_url):
                        with open(image_url, "rb") as f:
                            image_bytes = f.read()
                    else:
                        from app.media.image_processor import ImageProcessor
                        image_bytes = await ImageProcessor.download_and_optimize(image_url)
                except Exception as dl_err:
                    logger.warning(f"Could not load image {image_url[:60]}: {dl_err}")

            first_msg_id: Optional[int] = None
            successful_channels = []

            for cid in channel_ids:
                # Safety: Check if this ID is the bot's own ID
                if self.bot and str(self.bot.id) in str(cid):
                    logger.warning(f"Skipping channel ID '{cid}': Matches bot's own ID. Channel ID must start with -100.")
                    continue

                sent_msg: Optional[Message] = None
                try:
                    if image_bytes:
                        input_file = BufferedInputFile(image_bytes, filename=f"mlbb_news_{post_id}.jpg")
                        caption_part, rest_part = _split_caption(formatted_text)
                        try:
                            sent_msg = await self.bot.send_photo(
                                chat_id=cid,
                                photo=input_file,
                                caption=caption_part,
                                parse_mode="HTML"
                            )
                            if rest_part:
                                await self.bot.send_message(
                                    chat_id=cid,
                                    text=rest_part,
                                    parse_mode="HTML",
                                    disable_web_page_preview=False
                                )
                        except Exception as photo_err:
                            logger.warning(f"[{cid}] send_photo failed ({photo_err}), falling back to text message")
                            sent_msg = await self.bot.send_message(
                                chat_id=cid,
                                text=formatted_text,
                                parse_mode="HTML",
                                disable_web_page_preview=False
                            )
                    else:
                        sent_msg = await self.bot.send_message(
                            chat_id=cid,
                            text=formatted_text,
                            parse_mode="HTML",
                            disable_web_page_preview=False
                        )

                    if sent_msg:
                        successful_channels.append(cid)
                        if not first_msg_id:
                            first_msg_id = sent_msg.message_id
                        logger.info(f"Post #{post_id} published successfully to channel {cid} (msg_id: {sent_msg.message_id})")

                except Exception as ch_err:
                    logger.error(f"Failed to publish post #{post_id} to channel {cid}: {ch_err}")

            # Mark as PUBLISHED in database if at least one channel received it
            if first_msg_id:
                async with get_session() as session:
                    await PostRepository.update_status(
                        session=session,
                        post_id=post_id,
                        status=PostStatus.PUBLISHED.value,
                        telegram_message_id=first_msg_id
                    )

            return first_msg_id

        except Exception as e:
            logger.error(f"Failed to publish post #{post_id} to Telegram channels: {e}")
            return None
