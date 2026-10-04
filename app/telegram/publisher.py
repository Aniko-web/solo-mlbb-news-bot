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


from app.utils.html_utils import safe_trim_html, strip_html_tags


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
    Includes multi-stage fallback (HTML -> Plain text) and descriptive error reporting.
    """

    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        if self.bot is None:
            token = get_settings().TELEGRAM_BOT_TOKEN
            if token and len(token) > 10 and ":" in token:
                from aiogram.client.default import DefaultBotProperties
                self.bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
        self.channel_id = get_settings().channel_chat_id
        self.last_errors: dict[str, str] = {}

    def last_error_summary(self) -> str:
        """Return formatted error summary for display in admin messages."""
        if not self.last_errors:
            return "Noma'lum xatolik"
        items = []
        for cid, err in self.last_errors.items():
            err_lower = err.lower()
            if "chat not found" in err_lower:
                desc = "Kanal topilmadi (ID yoki username noto‘g‘ri)"
            elif "not a member" in err_lower or "bot was kicked" in err_lower:
                desc = "Bot kanalda a'zo emas"
            elif "not enough rights" in err_lower or "need administrator rights" in err_lower or "have no rights" in err_lower:
                desc = "Bot kanalda Admin emas yoki xabar chiqarish (Post Messages) huquqi berilmagan"
            elif "can't parse entities" in err_lower:
                desc = "Telegram HTML formati xatosi"
            else:
                desc = err
            items.append(f"• <code>{cid}</code>: {desc}")
        return "\n".join(items)

    async def publish_post(
        self,
        post_id: int,
        formatted_text: str,
        image_bytes: Optional[bytes] = None,
        image_url: Optional[str] = None
    ) -> Optional[int]:
        """
        Publish post to all configured Telegram channels with photo attachment.
        Returns telegram message ID if successful, or None if failed.
        """
        self.last_errors = {}
        current_settings = get_settings()
        channel_ids = current_settings.channel_ids
        if not self.bot or not channel_ids:
            err = (
                f"Cannot publish post #{post_id}: Telegram Bot or Channel ID not configured! "
                f"(bot={bool(self.bot)}, channel_ids={channel_ids})"
            )
            logger.error(err)
            self.last_errors["global"] = ".env faylida TELEGRAM_CHANNEL_ID sozlanmagan yoki bo‘sh"
            return None

        try:
            # Ensure post has channel signature footer at the end if not already present
            if "Telegram sahifamiz" not in formatted_text:
                from app.ai.formatter import CHANNEL_FOOTER
                formatted_text = f"{formatted_text.rstrip()}\n\n{CHANNEL_FOOTER}"

            # 1. Resolve image bytes (supports local file, cross-platform path, or remote URL)
            if not image_bytes and image_url:
                try:
                    resolved_file: Optional[str] = None
                    if os.path.exists(image_url):
                        resolved_file = image_url
                    else:
                        # Check relative to current project working directory or generated assets
                        bname = os.path.basename(image_url)
                        candidates = [
                            os.path.join(os.getcwd(), image_url),
                            os.path.join(os.getcwd(), "assets", "generated", bname),
                            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "generated", bname),
                        ]
                        for c in candidates:
                            if os.path.exists(c):
                                resolved_file = c
                                break

                    if resolved_file and os.path.exists(resolved_file):
                        with open(resolved_file, "rb") as f:
                            image_bytes = f.read()
                    elif str(image_url).startswith(("http://", "https://")):
                        from app.media.image_processor import ImageProcessor
                        image_bytes = await ImageProcessor.download_and_optimize(image_url)
                except Exception as dl_err:
                    logger.warning(f"Could not load image {str(image_url)[:60]}: {dl_err}")

            first_msg_id: Optional[int] = None
            successful_channels = []

            for cid in channel_ids:
                # Safety: Check if this ID is the bot's own ID
                if self.bot and str(self.bot.id) in str(cid):
                    msg = f"Kanal ID '{cid}' botning o‘z ID si bilan bir xil! Kanal ID si -100 bilan boshlanishi kerak."
                    logger.warning(msg)
                    self.last_errors[cid] = msg
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
                        except Exception as photo_html_err:
                            logger.warning(f"[{cid}] send_photo with HTML failed ({photo_html_err}), retrying with plain text caption...")
                            try:
                                sent_msg = await self.bot.send_photo(
                                    chat_id=cid,
                                    photo=input_file,
                                    caption=strip_html_tags(caption_part),
                                    parse_mode=None
                                )
                            except Exception as photo_plain_err:
                                logger.warning(f"[{cid}] send_photo fallback failed ({photo_plain_err}), falling back to send_message...")
                                try:
                                    sent_msg = await self.bot.send_message(
                                        chat_id=cid,
                                        text=formatted_text,
                                        parse_mode="HTML",
                                        disable_web_page_preview=False
                                    )
                                except Exception:
                                    sent_msg = await self.bot.send_message(
                                        chat_id=cid,
                                        text=strip_html_tags(formatted_text),
                                        parse_mode=None,
                                        disable_web_page_preview=False
                                    )

                        # If there is remaining text beyond caption limit, send it
                        if sent_msg and rest_part:
                            try:
                                await self.bot.send_message(
                                    chat_id=cid,
                                    text=rest_part,
                                    parse_mode="HTML",
                                    disable_web_page_preview=False
                                )
                            except Exception:
                                await self.bot.send_message(
                                    chat_id=cid,
                                    text=strip_html_tags(rest_part),
                                    parse_mode=None,
                                    disable_web_page_preview=False
                                )
                    else:
                        try:
                            sent_msg = await self.bot.send_message(
                                chat_id=cid,
                                text=formatted_text,
                                parse_mode="HTML",
                                disable_web_page_preview=False
                            )
                        except Exception as msg_html_err:
                            logger.warning(f"[{cid}] send_message HTML failed ({msg_html_err}), retrying with plain text...")
                            sent_msg = await self.bot.send_message(
                                chat_id=cid,
                                text=strip_html_tags(formatted_text),
                                parse_mode=None,
                                disable_web_page_preview=False
                            )

                    if sent_msg:
                        successful_channels.append(cid)
                        if not first_msg_id:
                            first_msg_id = sent_msg.message_id
                        logger.info(f"Post #{post_id} published successfully to channel {cid} (msg_id: {sent_msg.message_id})")

                except Exception as ch_err:
                    self.last_errors[cid] = str(ch_err)
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
            self.last_errors["global"] = str(e)
            return None

